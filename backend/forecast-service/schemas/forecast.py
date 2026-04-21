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


# ── Alpha Signals (ensemble) ──────────────────────────────────────────────────

class AlphaSignalResponse(BaseModel):
    """Ensemble-generated signal (ep2+ep4+ep5 consensus).

    `confident_long=True` = all 3 models agree lower_80 > current_close.
    `model_consensus` = HIGH/MEDIUM/LOW tier derived from disagreement_score.
    """
    ticker: str
    signal: str  # BUY | SELL | HOLD
    confidence: str  # HIGH | MEDIUM | LOW
    confident_long: bool
    model_consensus: str  # HIGH | MEDIUM | LOW
    disagreement_score: float
    current_close: float
    median_1d: float
    lower_80_1d: float
    upper_80_1d: float
    predicted_return_1d: float | None = None
    predicted_return_1w: float | None = None
    predicted_return_1m: float | None = None
    forecast_date: date
    expires_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_row(cls, r) -> "AlphaSignalResponse":
        """Build from a SQLAlchemy Row with explicitly-selected columns."""
        return cls(
            ticker=r.ticker,
            signal=r.signal,
            confidence=r.confidence,
            confident_long=r.confident_long,
            model_consensus=r.model_consensus,
            disagreement_score=round(r.disagreement_score, 4),
            current_close=round(r.current_close, 2),
            median_1d=round(r.median_1d, 2),
            lower_80_1d=round(r.lower_80_1d, 2),
            upper_80_1d=round(r.upper_80_1d, 2),
            predicted_return_1d=r.predicted_return_1d,
            predicted_return_1w=r.predicted_return_1w,
            predicted_return_1m=r.predicted_return_1m,
            forecast_date=r.forecast_date,
            expires_at=r.expires_at,
        )
