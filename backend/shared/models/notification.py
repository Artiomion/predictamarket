import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Double, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import BaseModel, SoftDeleteMixin


class Alert(SoftDeleteMixin, BaseModel):
    __tablename__ = "alerts"
    __table_args__ = {"schema": "notification"}

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False, index=True)
    instrument_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("market.instruments.id", ondelete="CASCADE"))
    ticker: Mapped[str | None] = mapped_column(String(10), index=True)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    condition_value: Mapped[float | None] = mapped_column(Double)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    is_triggered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    triggered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    triggers: Mapped[list["AlertTrigger"]] = relationship(back_populates="alert", cascade="all, delete-orphan")


class AlertTrigger(BaseModel):
    __tablename__ = "alert_triggers"
    __table_args__ = {"schema": "notification"}

    alert_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("notification.alerts.id", ondelete="CASCADE"), nullable=False, index=True)
    triggered_value: Mapped[float | None] = mapped_column(Double)
    message: Mapped[str | None] = mapped_column(Text)

    alert: Mapped["Alert"] = relationship(back_populates="triggers")


class NotificationLog(BaseModel):
    __tablename__ = "notification_log"
    __table_args__ = {"schema": "notification"}

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("notification.alerts.id", ondelete="SET NULL"))
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
