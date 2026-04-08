from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class CreateAlertRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    alert_type: str = Field(..., pattern="^(price_above|price_below|signal_change|earnings|insider|news_high_impact|forecast_update)$")
    condition_value: float | None = None


class AlertResponse(BaseModel):
    id: UUID
    ticker: str | None
    alert_type: str
    condition_value: float | None
    is_active: bool
    is_triggered: bool
    triggered_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationLogResponse(BaseModel):
    id: UUID
    channel: str
    title: str
    body: str | None
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}
