"""Background tasks: Redis pub/sub listener + price polling for alert checks + email."""

import asyncio
import json

import structlog
import redis.asyncio as aioredis
from sqlalchemy import select

from shared.config import settings
from shared.database import async_session_factory
from shared.models.auth import User

from services.alert_service import check_price_alerts, get_tickers_with_active_alerts
from services.email_service import send_email
from services.websocket import (
    emit_alert_triggered,
    emit_forecast_ready,
    emit_news_high_impact,
    emit_price_update,
)

logger = structlog.get_logger()

_tasks: list[asyncio.Task] = []
_running = True


async def _get_user_email(user_id: str) -> str | None:
    """Look up user email for sending notifications."""
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(User.email).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
    except Exception as exc:
        structlog.get_logger().warning("user_email_lookup_failed", user_id=str(user_id), error=str(exc))
        return None


async def _redis_subscriber() -> None:
    """Subscribe to Redis pub/sub: news.high_impact, forecast.updated."""
    sub_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = sub_client.pubsub()
    await pubsub.subscribe("news.high_impact", "forecast.updated", "price.updated")
    await logger.ainfo("pubsub_subscribed", channels=["news.high_impact", "forecast.updated", "price.updated"])

    try:
        while _running:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message["type"] == "message":
                channel = message["channel"]
                try:
                    data = json.loads(message["data"])
                except (json.JSONDecodeError, TypeError):
                    continue

                if channel == "price.updated":
                    ticker = data.get("ticker", "")
                    if ticker:
                        await emit_price_update(ticker, data)
                        await logger.ainfo("pubsub_price", ticker=ticker, price=data.get("price"))

                elif channel == "news.high_impact":
                    tickers = data.get("tickers", [])
                    await emit_news_high_impact(tickers, data)
                    await logger.ainfo("pubsub_news", tickers=tickers)

                elif channel == "forecast.updated":
                    ticker = data.get("ticker", "")
                    if ticker:
                        await emit_forecast_ready(ticker, data)
                    await logger.ainfo("pubsub_forecast", data=data)

            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe()
        await sub_client.aclose()


async def _price_poller() -> None:
    """Poll Redis prices, check alerts, emit WebSocket events, send emails."""
    price_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    try:
        while _running:
            try:
                async with async_session_factory() as session:
                    alert_tickers = await get_tickers_with_active_alerts(session)

                if not alert_tickers:
                    await asyncio.sleep(15)
                    continue

                # Collect prices from Redis first (no DB needed)
                ticker_prices: list[tuple[str, float, dict]] = []
                for ticker in alert_tickers:
                    raw = await price_client.get(f"mkt:price:{ticker}")
                    if not raw:
                        continue
                    try:
                        data = json.loads(raw)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    price = data.get("price", 0)
                    if not price:
                        continue
                    await emit_price_update(ticker, data)
                    ticker_prices.append((ticker, price, data))

                # Single session for all alert checks
                if ticker_prices:
                    async with async_session_factory() as session:
                        for ticker, price, data in ticker_prices:
                            triggered = await check_price_alerts(session, ticker, price)
                            if triggered:
                                for alert, message in triggered:
                                    user_id_str = str(alert.user_id)
                                    await emit_alert_triggered(
                                        user_id_str,
                                        {"alert_id": str(alert.id), "ticker": ticker,
                                         "message": message, "price": price},
                                    )
                                    email = await _get_user_email(user_id_str)
                                    if email:
                                        asyncio.create_task(send_email(
                                            to_email=email,
                                            subject=f"Price Alert: {ticker}",
                                            title=f"Price Alert: {ticker}",
                                            body=message,
                                            ticker=ticker,
                                        ))
                                    await logger.ainfo(
                                        "alert_triggered", alert_id=str(alert.id),
                                        ticker=ticker, user_id=user_id_str,
                                        email_sent=bool(email),
                                    )
                        await session.commit()

            except Exception as exc:
                await logger.aerror("price_poll_error", error=str(exc))

            await asyncio.sleep(15)
    except asyncio.CancelledError:
        pass
    finally:
        await price_client.aclose()


async def start_background_tasks() -> None:
    global _running
    _running = True
    _tasks.append(asyncio.create_task(_redis_subscriber()))
    _tasks.append(asyncio.create_task(_price_poller()))
    await logger.ainfo("background_tasks_started")


async def stop_background_tasks() -> None:
    global _running
    _running = False
    for task in _tasks:
        task.cancel()
    await asyncio.gather(*_tasks, return_exceptions=True)
    _tasks.clear()
    await logger.ainfo("background_tasks_stopped")
