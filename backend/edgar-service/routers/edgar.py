import uuid

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import require_user_id
from shared.database import get_read_session as get_session

from schemas.edgar import (
    BalanceSheetResponse,
    CashFlowResponse,
    FilingResponse,
    IncomeStatementResponse,
)
from services.edgar_service import (
    get_balance_sheets,
    get_cash_flows,
    get_filings,
    get_income_statements,
)

logger = structlog.get_logger()
router = APIRouter()


EDGAR_ALLOWED_TIERS = {"pro", "premium"}


def _require_pro_tier(x_user_tier: str = Header("free")) -> str:
    """EDGAR data requires Pro or Premium tier."""
    if x_user_tier not in EDGAR_ALLOWED_TIERS:
        raise HTTPException(status_code=403, detail="SEC EDGAR data requires Pro or Premium tier")
    return x_user_tier


@router.get("/{ticker}/filings", response_model=list[FilingResponse])
async def filings_endpoint(
    ticker: str,
    filing_type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    _user: uuid.UUID = Depends(require_user_id),
    _tier: str = Depends(_require_pro_tier),
    session: AsyncSession = Depends(get_session),
) -> list[FilingResponse]:
    rows = await get_filings(session, ticker, filing_type=filing_type, limit=limit)
    return [FilingResponse.model_validate(r) for r in rows]


@router.get("/{ticker}/income", response_model=list[IncomeStatementResponse])
async def income_endpoint(
    ticker: str,
    limit: int = Query(20, ge=1, le=100),
    _user: uuid.UUID = Depends(require_user_id),
    _tier: str = Depends(_require_pro_tier),
    session: AsyncSession = Depends(get_session),
) -> list[IncomeStatementResponse]:
    rows = await get_income_statements(session, ticker, limit=limit)
    return [IncomeStatementResponse.model_validate(r) for r in rows]


@router.get("/{ticker}/balance", response_model=list[BalanceSheetResponse])
async def balance_endpoint(
    ticker: str,
    limit: int = Query(20, ge=1, le=100),
    _user: uuid.UUID = Depends(require_user_id),
    _tier: str = Depends(_require_pro_tier),
    session: AsyncSession = Depends(get_session),
) -> list[BalanceSheetResponse]:
    rows = await get_balance_sheets(session, ticker, limit=limit)
    return [BalanceSheetResponse.model_validate(r) for r in rows]


@router.get("/{ticker}/cashflow", response_model=list[CashFlowResponse])
async def cashflow_endpoint(
    ticker: str,
    limit: int = Query(20, ge=1, le=100),
    _user: uuid.UUID = Depends(require_user_id),
    _tier: str = Depends(_require_pro_tier),
    session: AsyncSession = Depends(get_session),
) -> list[CashFlowResponse]:
    rows = await get_cash_flows(session, ticker, limit=limit)
    return [CashFlowResponse.model_validate(r) for r in rows]
