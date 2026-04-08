import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_session

from schemas.market import EarningsCalendarResponse, EarningsResultResponse
from services.earnings_service import get_earnings_history, get_upcoming_earnings

logger = structlog.get_logger()
router = APIRouter()


@router.get("/upcoming", response_model=list[EarningsCalendarResponse])
async def upcoming_earnings(
    days: int = Query(14, ge=1, le=90),
    session: AsyncSession = Depends(get_session),
) -> list[EarningsCalendarResponse]:
    rows = await get_upcoming_earnings(session, days=days)
    return [EarningsCalendarResponse(**r) for r in rows]


@router.get("/{ticker}/history", response_model=list[EarningsResultResponse])
async def earnings_history(
    ticker: str,
    session: AsyncSession = Depends(get_session),
) -> list[EarningsResultResponse]:
    rows = await get_earnings_history(session, ticker)
    return [EarningsResultResponse.model_validate(r) for r in rows]
