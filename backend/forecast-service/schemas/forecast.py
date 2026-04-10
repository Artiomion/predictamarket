from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Forecast response (matches CLAUDE.md API output format) ───────────────────

class ForecastHorizon(BaseModel):
    median: float
    lower_80: float
    upper_80: float
    lower_95: float | None = None
    upper_95: float | None = None


class ForecastFactor(BaseModel):
    name: str
    weight: float
    direction: str  # bullish | bearish | neutral
    is_estimated: bool = False


class ForecastResponse(BaseModel):
    ticker: str
    current_close: float
    signal: str  # BUY | SELL | HOLD
    confidence: str  # HIGH | MEDIUM | LOW
    forecast: dict[str, ForecastHorizon | None]
    full_curve: list[float]
    variable_importance: dict[str, list[ForecastFactor]]
    inference_time_s: float
    forecast_date: str
    predicted_return_1d: float | None = None
    predicted_return_1w: float | None = None
    predicted_return_1m: float | None = None
    news_articles_used: int | None = None
    persisted: bool | None = None


class ForecastFromDB(BaseModel):
    id: UUID
    ticker: str
    forecast_date: date
    current_close: float
    signal: str
    confidence: str
    predicted_return_1d: float | None
    predicted_return_1w: float | None
    predicted_return_1m: float | None
    inference_time_s: float | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Top Picks ─────────────────────────────────────────────────────────────────

class TopPickItem(BaseModel):
    ticker: str
    name: str | None = None
    current_close: float
    predicted_return_1m: float | None
    signal: str
    confidence: str

    model_config = {"from_attributes": True}


# ── Batch ─────────────────────────────────────────────────────────────────────

class BatchRequest(BaseModel):
    tickers: list[str] = Field(..., min_length=1, max_length=94)


class BatchJobResponse(BaseModel):
    job_id: str
    status: str  # queued | running | completed | failed
    tickers: list[str]


class BatchJobStatus(BaseModel):
    job_id: str
    status: str
    completed: int
    total: int
    results: list[ForecastResponse] | None = None
