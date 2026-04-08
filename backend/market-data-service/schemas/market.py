from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Pagination ────────────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel):
    total: int
    page: int
    per_page: int


# ── Instruments ───────────────────────────────────────────────────────────────

class InstrumentResponse(BaseModel):
    id: UUID
    ticker: str
    name: str
    sector: str | None
    industry: str | None
    market_cap: int | None
    exchange: str
    is_active: bool

    model_config = {"from_attributes": True}


class InstrumentDetailResponse(InstrumentResponse):
    description: str | None = None
    website: str | None = None
    logo_url: str | None = None
    ceo: str | None = None
    employees: int | None = None
    headquarters: str | None = None
    founded_year: int | None = None


class InstrumentListResponse(PaginatedResponse):
    data: list[InstrumentResponse]


# ── Price History ─────────────────────────────────────────────────────────────

class PricePointResponse(BaseModel):
    date: date
    open: float | None
    high: float | None
    low: float | None
    close: float
    volume: int | None

    model_config = {"from_attributes": True}


class CurrentPriceResponse(BaseModel):
    ticker: str
    price: float
    change: float | None = None
    change_pct: float | None = None
    updated_at: str | None = None


# ── Financial Metrics ─────────────────────────────────────────────────────────

class FinancialMetricResponse(BaseModel):
    period_end: date
    period_type: str
    revenue: float | None
    net_income: float | None
    eps: float | None
    pe_ratio: float | None
    pb_ratio: float | None
    dividend_yield: float | None
    debt_to_equity: float | None
    roe: float | None
    roa: float | None
    free_cash_flow: float | None
    operating_margin: float | None
    current_ratio: float | None

    model_config = {"from_attributes": True}


# ── Earnings ──────────────────────────────────────────────────────────────────

class EarningsCalendarResponse(BaseModel):
    ticker: str
    name: str | None = None
    report_date: date
    fiscal_quarter: str | None
    fiscal_year: int | None
    time_of_day: str | None
    eps_estimate: float | None
    revenue_estimate: float | None

    model_config = {"from_attributes": True}


class EarningsResultResponse(BaseModel):
    ticker: str
    report_date: date
    fiscal_quarter: str | None
    fiscal_year: int | None
    eps_actual: float | None
    eps_estimate: float | None
    eps_surprise_pct: float | None
    revenue_actual: float | None
    revenue_estimate: float | None
    revenue_surprise_pct: float | None
    beat_estimate: bool | None

    model_config = {"from_attributes": True}


# ── Insider ───────────────────────────────────────────────────────────────────

class InsiderTransactionResponse(BaseModel):
    insider_name: str
    insider_title: str | None
    transaction_type: str
    shares: float
    price_per_share: float | None
    total_value: float | None
    shares_owned_after: float | None
    filing_date: date
    transaction_date: date | None

    model_config = {"from_attributes": True}
