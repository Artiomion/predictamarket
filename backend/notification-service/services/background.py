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
    get_subscribed_tickers,
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
            try:
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

                    elif channel == "news.high_impact":
                        tickers = data.get("tickers", [])
                        await emit_news_high_impact(tickers, data)
                        await logger.ainfo("pubsub_news", tickers=tickers)

                    elif channel == "forecast.updated":
                        ticker = data.get("ticker", "")
                        if ticker:
                            await emit_forecast_ready(ticker, data)
                        await logger.ainfo("pubsub_forecast", data=data)

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await logger.aerror("pubsub_error", error=str(exc))

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
                    # Price updates are now delivered via Pub/Sub (_redis_subscriber).
                    # Only collect prices here for alert checking — no duplicate emit.
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


# ── Live price fetcher — yfinance for subscribed tickers ─────────────────────

_LIVE_POLL_INTERVAL = 30  # seconds
_CIRCUIT_BREAKER_THRESHOLD = 3
_CIRCUIT_BREAKER_COOLDOWN = 300  # 5 minutes


async def _live_price_fetcher() -> None:
    """Fetch live prices from yfinance for tickers with WebSocket subscribers.

    Only polls tickers that have at least 1 client in the Socket.IO room.
    Circuit breaker: 3 consecutive failures → 5 min pause.
    """
    redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    consecutive_failures = 0

    try:
        while _running:
            try:
                tickers = get_subscribed_tickers()
                if not tickers:
                    await asyncio.sleep(_LIVE_POLL_INTERVAL)
                    continue

                if consecutive_failures >= _CIRCUIT_BREAKER_THRESHOLD:
                    await logger.awarning(
                        "live_price_circuit_open",
                        failures=consecutive_failures,
                        cooldown=_CIRCUIT_BREAKER_COOLDOWN,
                    )
                    await asyncio.sleep(_CIRCUIT_BREAKER_COOLDOWN)
                    consecutive_failures = 0

                # Fetch all subscribed tickers in one yfinance call (sync → to_thread)
                import yfinance as yf
                ticker_str = " ".join(sorted(tickers))
                multi = len(tickers) > 1
                try:
                    data = await asyncio.to_thread(
                        yf.download,
                        ticker_str,
                        period="2d",
                        interval="1d",
                        progress=False,
                        timeout=10,
                        group_by="ticker" if multi else "column",
                    )
                except Exception as exc:
                    consecutive_failures += 1
                    await logger.awarning("live_price_yf_error", error=str(exc), failures=consecutive_failures)
                    await asyncio.sleep(_LIVE_POLL_INTERVAL)
                    continue

                if data is None or data.empty:
                    consecutive_failures += 1
                    await asyncio.sleep(_LIVE_POLL_INTERVAL)
                    continue

                consecutive_failures = 0  # reset on success

                for ticker in tickers:
                    try:
                        if len(tickers) == 1:
                            df = data
                        else:
                            df = data[ticker] if ticker in data.columns.get_level_values(0) else None
                        if df is None or df.empty or len(df) < 1:
                            continue

                        latest_close = float(df["Close"].iloc[-1])
                        if latest_close != latest_close:  # NaN check
                            continue
                        prev_close = float(df["Close"].iloc[-2]) if len(df) >= 2 else None

                        price_data = {
                            "ticker": ticker,
                            "price": round(latest_close, 2),
                            "change": round(latest_close - prev_close, 2) if prev_close else None,
                            "change_pct": round((latest_close - prev_close) / prev_close * 100, 2) if prev_close else None,
                        }
                        price_json = json.dumps(price_data)

                        # Only publish if price changed
                        old = await redis_client.get(f"mkt:price:{ticker}")
                        await redis_client.set(f"mkt:price:{ticker}", price_json, ex=900)
                        if old != price_json:
                            await redis_client.publish("price.updated", price_json)

                    except Exception as exc:
                        await logger.awarning("live_price_ticker_error", ticker=ticker, error=str(exc))

                await logger.ainfo("live_price_fetched", tickers=sorted(tickers), count=len(tickers))

            except asyncio.CancelledError:
                raise
            except Exception as exc:
                await logger.aerror("live_price_error", error=str(exc))

            await asyncio.sleep(_LIVE_POLL_INTERVAL)
    except asyncio.CancelledError:
        pass
    finally:
        await redis_client.aclose()


async def start_background_tasks() -> None:
    global _running
    _running = True
    _tasks.append(asyncio.create_task(_redis_subscriber()))
    _tasks.append(asyncio.create_task(_price_poller()))
    _tasks.append(asyncio.create_task(_live_price_fetcher()))
    await logger.ainfo("background_tasks_started")


async def stop_background_tasks() -> None:
    global _running
    _running = False
    for task in _tasks:
        task.cancel()
    await asyncio.gather(*_tasks, return_exceptions=True)
    _tasks.clear()
    await logger.ainfo("background_tasks_stopped")
