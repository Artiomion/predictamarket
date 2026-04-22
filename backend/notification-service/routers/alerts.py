import uuid

import structlog
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import require_user_id
from shared.database import get_read_session, get_session

from schemas.alerts import AlertResponse, CreateAlertRequest, NotificationLogResponse
from services.alert_service import create_alert, delete_alert, get_notification_history, list_alerts

logger = structlog.get_logger()
router = APIRouter()


@router.post("/alerts", response_model=AlertResponse, status_code=201)
async def create_alert_endpoint(
    body: CreateAlertRequest,
    user_id: uuid.UUID = Depends(require_user_id),
    x_user_tier: str = Header("free"),
    session: AsyncSession = Depends(get_session),
) -> AlertResponse:
    alert = await create_alert(
        session, user_id, body.ticker, body.alert_type, body.condition_value, x_user_tier,
    )
    return AlertResponse.model_validate(alert)


@router.get("/alerts", response_model=list[AlertResponse])
async def list_alerts_endpoint(
    limit: int = Query(100, ge=1, le=500),
    user_id: uuid.UUID = Depends(require_user_id),
    session: AsyncSession = Depends(get_read_session),
) -> list[AlertResponse]:
    alerts = await list_alerts(session, user_id, limit=limit)
    return [AlertResponse.model_validate(a) for a in alerts]


@router.delete("/alerts/{alert_id}", status_code=204)
async def delete_alert_endpoint(
    alert_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_user_id),
    session: AsyncSession = Depends(get_session),
) -> None:
    await delete_alert(session, alert_id, user_id)


@router.get("/alerts/history", response_model=list[NotificationLogResponse])
async def alert_history_endpoint(
    limit: int = Query(50, ge=1, le=200),
    user_id: uuid.UUID = Depends(require_user_id),
    session: AsyncSession = Depends(get_read_session),
) -> list[NotificationLogResponse]:
    logs = await get_notification_history(session, user_id, limit=limit)
    return [NotificationLogResponse.model_validate(log) for log in logs]
