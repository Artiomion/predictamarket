import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Double, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shared.models.base import BaseModel


class ModelVersion(BaseModel):
    __tablename__ = "model_versions"
    __table_args__ = {"schema": "forecast"}

    version: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    checkpoint_path: Mapped[str] = mapped_column(Text, nullable=False)
    metrics: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    trained_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    forecasts: Mapped[list["Forecast"]] = relationship(back_populates="model_version", cascade="all, delete-orphan")


class Forecast(BaseModel):
    __tablename__ = "forecasts"
    __table_args__ = (
        Index("ix_forecasts_ticker_is_latest", "ticker", "is_latest"),
        {"schema": "forecast"},
    )

    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market.instruments.id", ondelete="CASCADE"), nullable=False, index=True)
    model_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("forecast.model_versions.id", ondelete="CASCADE"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    current_close: Mapped[float] = mapped_column(Double, nullable=False)
    signal: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    predicted_return_1d: Mapped[float | None] = mapped_column(Double)
    predicted_return_1w: Mapped[float | None] = mapped_column(Double)
    predicted_return_1m: Mapped[float | None] = mapped_column(Double)
    inference_time_s: Mapped[float | None] = mapped_column(Double)
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)

    model_version: Mapped["ModelVersion"] = relationship(back_populates="forecasts")
    points: Mapped[list["ForecastPoint"]] = relationship(back_populates="forecast", cascade="all, delete-orphan")
    factors: Mapped[list["ForecastFactor"]] = relationship(back_populates="forecast", cascade="all, delete-orphan")


class ForecastPoint(BaseModel):
    __tablename__ = "forecast_points"
    __table_args__ = {"schema": "forecast"}

    forecast_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("forecast.forecasts.id", ondelete="CASCADE"), nullable=False, index=True)
    step: Mapped[int] = mapped_column(Integer, nullable=False)
    horizon_label: Mapped[str | None] = mapped_column(String(10))
    median: Mapped[float] = mapped_column(Double, nullable=False)
    lower_80: Mapped[float | None] = mapped_column(Double)
    upper_80: Mapped[float | None] = mapped_column(Double)
    lower_95: Mapped[float | None] = mapped_column(Double)
    upper_95: Mapped[float | None] = mapped_column(Double)
    q_02: Mapped[float | None] = mapped_column(Double)
    q_10: Mapped[float | None] = mapped_column(Double)
    q_25: Mapped[float | None] = mapped_column(Double)
    q_50: Mapped[float | None] = mapped_column(Double)
    q_75: Mapped[float | None] = mapped_column(Double)
    q_90: Mapped[float | None] = mapped_column(Double)
    q_98: Mapped[float | None] = mapped_column(Double)

    forecast: Mapped["Forecast"] = relationship(back_populates="points")


class ForecastFactor(BaseModel):
    __tablename__ = "forecast_factors"
    __table_args__ = {"schema": "forecast"}

    forecast_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("forecast.forecasts.id", ondelete="CASCADE"), nullable=False, index=True)
    factor_name: Mapped[str] = mapped_column(String(100), nullable=False)
    weight: Mapped[float] = mapped_column(Double, nullable=False)
    direction: Mapped[str | None] = mapped_column(String(20))
    rank: Mapped[int] = mapped_column(Integer, nullable=False)

    forecast: Mapped["Forecast"] = relationship(back_populates="factors")


class ForecastHistory(BaseModel):
    __tablename__ = "forecast_history"
    __table_args__ = {"schema": "forecast"}

    instrument_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market.instruments.id", ondelete="CASCADE"), nullable=False)
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    horizon_days: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_price: Mapped[float] = mapped_column(Double, nullable=False)
    actual_price: Mapped[float | None] = mapped_column(Double)
    error_pct: Mapped[float | None] = mapped_column(Double)
    signal: Mapped[str | None] = mapped_column(String(10))
    was_correct: Mapped[bool | None] = mapped_column(Boolean)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AlphaSignal(BaseModel):
    """Ensemble-generated signals from ep2+ep4+ep5 (3-model consensus).

    Populated by dag_alpha_signals (hourly during market hours).
    Used by Alpha Signals feed — Premium/Pro tier feature.
    """
    __tablename__ = "alpha_signals"
    __table_args__ = (
        Index("ix_alpha_signals_latest_return", "is_latest", "predicted_return_1d"),
        {"schema": "forecast"},
    )

    instrument_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("market.instruments.id", ondelete="CASCADE"), nullable=False,
    )
    ticker: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    sector: Mapped[str | None] = mapped_column(String(50))
    signal: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY / SELL / HOLD
    confidence: Mapped[str] = mapped_column(String(10), nullable=False)
    confident_long: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    model_consensus: Mapped[str] = mapped_column(String(10), nullable=False)
    disagreement_score: Mapped[float] = mapped_column(Double, nullable=False)
    current_close: Mapped[float] = mapped_column(Double, nullable=False)
    median_1d: Mapped[float] = mapped_column(Double, nullable=False)
    lower_80_1d: Mapped[float] = mapped_column(Double, nullable=False)
    upper_80_1d: Mapped[float] = mapped_column(Double, nullable=False)
    predicted_return_1d: Mapped[float | None] = mapped_column(Double)
    predicted_return_1w: Mapped[float | None] = mapped_column(Double)
    predicted_return_1m: Mapped[float | None] = mapped_column(Double)
    ensemble_weights: Mapped[list[float]] = mapped_column(ARRAY(Double), nullable=False)
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    is_latest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
