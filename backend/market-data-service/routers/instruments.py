import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_session

from schemas.market import (
    CurrentPriceResponse,
    FinancialMetricResponse,
    InstrumentDetailResponse,
    InstrumentListResponse,
    PricePointResponse,
)
from services.instrument_service import (
    get_current_price,
    get_financials,
    get_instrument_detail_cached,
    get_instruments,
    get_price_history,
)

logger = structlog.get_logger()
router = APIRouter()


@router.get("/instruments", response_model=InstrumentListResponse)
async def list_instruments(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    sector: str | None = Query(None),
    search: str | None = Query(None),
    sort_by: str = Query("ticker"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await get_instruments(
        session, page=page, per_page=per_page,
        sector=sector, search=search, sort_by=sort_by, order=order,
    )


@router.get("/instruments/{ticker}", response_model=InstrumentDetailResponse)
async def get_instrument(
    ticker: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await get_instrument_detail_cached(session, ticker)


@router.get("/instruments/{ticker}/history", response_model=list[PricePointResponse])
async def get_instrument_history(
    ticker: str,
    period: str = Query("1y", pattern="^(1m|3m|6m|1y|2y|5y|max)$"),
    interval: str = Query("1d"),
    session: AsyncSession = Depends(get_session),
) -> list[PricePointResponse]:
    rows = await get_price_history(session, ticker, period=period, interval=interval)
    return [PricePointResponse.model_validate(r) for r in rows]


@router.get("/instruments/{ticker}/financials", response_model=list[FinancialMetricResponse])
async def get_instrument_financials(
    ticker: str,
    period: str = Query("quarterly", pattern="^(quarterly|annual)$"),
    session: AsyncSession = Depends(get_session),
) -> list[FinancialMetricResponse]:
    rows = await get_financials(session, ticker, period_type=period)
    return [FinancialMetricResponse.model_validate(r) for r in rows]


@router.get("/instruments/{ticker}/price", response_model=CurrentPriceResponse)
async def get_instrument_price(
    ticker: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await get_current_price(session, ticker)
