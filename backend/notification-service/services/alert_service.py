"""Alerts CRUD + trigger check."""

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.market import Instrument
from shared.models.notification import Alert, AlertTrigger, NotificationLog
from shared.tier_limits import ALERT_LIMITS

logger = structlog.get_logger()


async def create_alert(
    session: AsyncSession,
    user_id: uuid.UUID,
    ticker: str,
    alert_type: str,
    condition_value: float | None,
    tier: str,
) -> Alert:
    limit = ALERT_LIMITS.get(tier, 3)
    # Only count non-triggered active alerts
    count_result = await session.execute(
        select(func.count()).select_from(Alert).where(
            Alert.user_id == user_id,
            Alert.is_active.is_(True),
            Alert.is_triggered.is_(False),
            Alert.deleted_at.is_(None),
        )
    )
    if (count_result.scalar() or 0) >= limit:
        raise HTTPException(status_code=403, detail=f"Alert limit reached ({limit} for {tier} tier)")

    ticker_upper = ticker.upper()
    inst = await session.execute(
        select(Instrument.id).where(Instrument.ticker == ticker_upper)
    )
    instrument_id = inst.scalar_one_or_none()
    if not instrument_id:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker_upper} not found")

    alert = Alert(
        user_id=user_id,
        instrument_id=instrument_id,
        ticker=ticker_upper,
        alert_type=alert_type,
        condition_value=condition_value,
    )
    session.add(alert)
    await session.flush()
    await logger.ainfo("alert_created", alert_id=str(alert.id), ticker=ticker_upper, type=alert_type)
    return alert


async def list_alerts(
    session: AsyncSession, user_id: uuid.UUID, limit: int = 100,
) -> list[Alert]:
# Added limit param
    result = await session.execute(
        select(Alert).where(
            Alert.user_id == user_id, Alert.deleted_at.is_(None)
        ).order_by(Alert.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def delete_alert(session: AsyncSession, alert_id: uuid.UUID, user_id: uuid.UUID) -> None:
    result = await session.execute(
        select(Alert).where(Alert.id == alert_id, Alert.user_id == user_id, Alert.deleted_at.is_(None))
    )
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.deleted_at = datetime.now(timezone.utc)


async def get_notification_history(
    session: AsyncSession, user_id: uuid.UUID, limit: int = 50,
) -> list[NotificationLog]:
    result = await session.execute(
        select(NotificationLog).where(NotificationLog.user_id == user_id)
        .order_by(NotificationLog.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def check_price_alerts(
    session: AsyncSession,
    ticker: str,
    current_price: float,
) -> list[tuple[Alert, str]]:
    """Check active alerts for a ticker. Returns list of (alert, message) for triggered ones."""
    result = await session.execute(
        select(Alert).where(
            Alert.ticker == ticker,
            Alert.is_active.is_(True),
            Alert.is_triggered.is_(False),
            Alert.deleted_at.is_(None),
            Alert.alert_type.in_(["price_above", "price_below"]),
        )
    )
    alerts = result.scalars().all()
    triggered: list[tuple[Alert, str]] = []

    for alert in alerts:
        if alert.condition_value is None:
            continue

        should_trigger = False
        message = ""

        if alert.alert_type == "price_above" and current_price >= alert.condition_value:
            should_trigger = True
            message = f"{ticker} reached ${current_price:.2f} (above ${alert.condition_value:.2f})"
        elif alert.alert_type == "price_below" and current_price <= alert.condition_value:
            should_trigger = True
            message = f"{ticker} dropped to ${current_price:.2f} (below ${alert.condition_value:.2f})"

        if should_trigger:
            alert.is_triggered = True
            alert.triggered_at = datetime.now(timezone.utc)

            session.add(AlertTrigger(
                alert_id=alert.id, triggered_value=current_price, message=message,
            ))
            session.add(NotificationLog(
                user_id=alert.user_id, alert_id=alert.id, channel="in_app",
                title=f"Price Alert: {ticker}", body=message,
            ))
            triggered.append((alert, message))

    return triggered


async def get_tickers_with_active_alerts(session: AsyncSession) -> set[str]:
    """FIX #4: Get only tickers that have active price alerts — avoid scanning all prices."""
    result = await session.execute(
        select(Alert.ticker).where(
            Alert.is_active.is_(True),
            Alert.is_triggered.is_(False),
            Alert.deleted_at.is_(None),
            Alert.alert_type.in_(["price_above", "price_below"]),
        ).distinct()
    )
    return {r[0] for r in result.all()}
