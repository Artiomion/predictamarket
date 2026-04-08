from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Portfolios ────────────────────────────────────────────────────────────────

class CreatePortfolioRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class PortfolioResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_default: bool
    total_value: float
    total_pnl: float
    total_pnl_pct: float
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Positions ─────────────────────────────────────────────────────────────────

class AddPositionRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)
    quantity: float = Field(..., gt=0)
    price: float = Field(..., gt=0)
    notes: str | None = None


class PositionResponse(BaseModel):
    id: UUID
    ticker: str
    quantity: float
    avg_buy_price: float
    current_price: float | None
    pnl: float
    pnl_pct: float

    model_config = {"from_attributes": True}


# ── Analytics ─────────────────────────────────────────────────────────────────

class SectorAllocation(BaseModel):
    sector: str
    value: float
    pct: float


class PerformancePoint(BaseModel):
    date: str
    value: float


class CorrelationPair(BaseModel):
    ticker_a: str
    ticker_b: str
    correlation: float


class DividendItem(BaseModel):
    ticker: str
    amount_per_share: float | None
    ex_date: str | None
    projected_annual: float | None


class AnalyticsResponse(BaseModel):
    total_value: float
    total_pnl: float
    total_pnl_pct: float
    positions_count: int
    best_position: str | None
    worst_position: str | None


# ── Transactions ──────────────────────────────────────────────────────────────

class TransactionResponse(BaseModel):
    id: UUID
    ticker: str
    type: str
    quantity: float
    price: float
    total_amount: float
    notes: str | None
    executed_at: datetime

    model_config = {"from_attributes": True}


# ── Watchlists ────────────────────────────────────────────────────────────────

class CreateWatchlistRequest(BaseModel):
    name: str = Field("My Watchlist", min_length=1, max_length=255)


class WatchlistResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AddWatchlistItemRequest(BaseModel):
    ticker: str = Field(..., min_length=1, max_length=10)


class WatchlistItemResponse(BaseModel):
    id: UUID
    ticker: str
    added_at: datetime

    model_config = {"from_attributes": True}


class WatchlistDetailResponse(WatchlistResponse):
    items: list[WatchlistItemResponse] = []
