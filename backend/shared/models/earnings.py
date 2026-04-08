import uuid
from datetime import date

from sqlalchemy import Boolean, Date, Double, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from shared.models.base import BaseModel


class EarningsCalendar(BaseModel):
    __tablename__ = "earnings_calendar"
    __table_args__ = (
        UniqueConstraint("ticker", "report_date"),
        {"schema": "earnings"},
    )

    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market.instruments.id", ondelete="CASCADE"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    fiscal_quarter: Mapped[str | None] = mapped_column(String(10))
    fiscal_year: Mapped[int | None] = mapped_column(Integer)
    time_of_day: Mapped[str | None] = mapped_column(String(20))
    eps_estimate: Mapped[float | None] = mapped_column(Double)
    revenue_estimate: Mapped[float | None] = mapped_column(Double)


class EarningsResult(BaseModel):
    __tablename__ = "earnings_results"
    __table_args__ = {"schema": "earnings"}

    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market.instruments.id", ondelete="CASCADE"), nullable=False, index=True)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    report_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    fiscal_quarter: Mapped[str | None] = mapped_column(String(10))
    fiscal_year: Mapped[int | None] = mapped_column(Integer)
    eps_actual: Mapped[float | None] = mapped_column(Double)
    eps_estimate: Mapped[float | None] = mapped_column(Double)
    eps_surprise_pct: Mapped[float | None] = mapped_column(Double)
    revenue_actual: Mapped[float | None] = mapped_column(Double)
    revenue_estimate: Mapped[float | None] = mapped_column(Double)
    revenue_surprise_pct: Mapped[float | None] = mapped_column(Double)
    beat_estimate: Mapped[bool | None] = mapped_column(Boolean)


class EpsEstimate(BaseModel):
    __tablename__ = "eps_estimates"
    __table_args__ = {"schema": "earnings"}

    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market.instruments.id", ondelete="CASCADE"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    fiscal_quarter: Mapped[str | None] = mapped_column(String(10))
    fiscal_year: Mapped[int | None] = mapped_column(Integer)
    analyst_count: Mapped[int | None] = mapped_column(Integer)
    eps_low: Mapped[float | None] = mapped_column(Double)
    eps_high: Mapped[float | None] = mapped_column(Double)
    eps_avg: Mapped[float | None] = mapped_column(Double)
