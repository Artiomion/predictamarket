import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import get_read_session as get_session

from schemas.market import InsiderTransactionResponse
from services.insider_service import get_insider_transactions

logger = structlog.get_logger()
router = APIRouter()


@router.get("/{ticker}", response_model=list[InsiderTransactionResponse])
async def insider_transactions(
    ticker: str,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[InsiderTransactionResponse]:
    rows = await get_insider_transactions(session, ticker, limit=limit)
    return [InsiderTransactionResponse.model_validate(r) for r in rows]
