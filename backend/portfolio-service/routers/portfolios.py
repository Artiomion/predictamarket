import uuid

import structlog
from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import require_user_id
from shared.database import get_read_session, get_session

from schemas.portfolio import (
    AddPositionRequest,
    AnalyticsResponse,
    CreatePortfolioRequest,
    PortfolioResponse,
    PositionResponse,
    SectorAllocation,
    TransactionResponse,
)
from services.portfolio_service import (
    add_position,
    create_portfolio,
    delete_portfolio,
    delete_position,
    export_transactions_csv,
    get_analytics,
    get_portfolio,
    get_positions,
    get_sector_allocation,
    get_transactions,
    list_portfolios,
)

logger = structlog.get_logger()
router = APIRouter()


@router.post("/portfolios", response_model=PortfolioResponse, status_code=201)
async def create_portfolio_endpoint(
    body: CreatePortfolioRequest,
    user_id: uuid.UUID = Depends(require_user_id),
    x_user_tier: str = Header("free"),
    session: AsyncSession = Depends(get_session),
) -> PortfolioResponse:
    p = await create_portfolio(session, user_id, body.name, body.description, x_user_tier)
    return PortfolioResponse.model_validate(p)


@router.get("/portfolios", response_model=list[PortfolioResponse])
async def list_portfolios_endpoint(
    user_id: uuid.UUID = Depends(require_user_id),
    session: AsyncSession = Depends(get_read_session),
) -> list[PortfolioResponse]:
    portfolios = await list_portfolios(session, user_id)
    return [PortfolioResponse.model_validate(p) for p in portfolios]


@router.get("/portfolios/{portfolio_id}", response_model=PortfolioResponse)
async def get_portfolio_endpoint(
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_user_id),
    session: AsyncSession = Depends(get_read_session),
) -> PortfolioResponse:
    p = await get_portfolio(session, portfolio_id, user_id)
    return PortfolioResponse.model_validate(p)


@router.delete("/portfolios/{portfolio_id}", status_code=204)
async def delete_portfolio_endpoint(
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_user_id),
    session: AsyncSession = Depends(get_session),
) -> None:
    await delete_portfolio(session, portfolio_id, user_id)


# ── Positions ─────────────────────────────────────────────────────────────────

@router.post("/portfolios/{portfolio_id}/positions", response_model=PositionResponse, status_code=201)
async def add_position_endpoint(
    portfolio_id: uuid.UUID,
    body: AddPositionRequest,
    user_id: uuid.UUID = Depends(require_user_id),
    x_user_tier: str = Header("free"),
    session: AsyncSession = Depends(get_session),
) -> PositionResponse:
    item = await add_position(
        session, portfolio_id, user_id, body.ticker, body.quantity, body.price, x_user_tier, body.notes
    )
    return PositionResponse.model_validate(item)


@router.get("/portfolios/{portfolio_id}/positions", response_model=list[PositionResponse])
async def list_positions_endpoint(
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_user_id),
    session: AsyncSession = Depends(get_read_session),
) -> list[PositionResponse]:
    items = await get_positions(session, portfolio_id, user_id)
    return [PositionResponse.model_validate(i) for i in items]


@router.delete("/portfolios/{portfolio_id}/positions/{ticker}", status_code=204)
async def delete_position_endpoint(
    portfolio_id: uuid.UUID,
    ticker: str,
    quantity: float | None = Query(None),
    price: float | None = Query(None),
    user_id: uuid.UUID = Depends(require_user_id),
    session: AsyncSession = Depends(get_session),
) -> None:
    await delete_position(session, portfolio_id, user_id, ticker, quantity, price)


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/portfolios/{portfolio_id}/analytics", response_model=AnalyticsResponse)
async def analytics_endpoint(
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_user_id),
    session: AsyncSession = Depends(get_read_session),
) -> dict:
    return await get_analytics(session, portfolio_id, user_id)


@router.get("/portfolios/{portfolio_id}/sectors", response_model=list[SectorAllocation])
async def sectors_endpoint(
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_user_id),
    session: AsyncSession = Depends(get_read_session),
) -> list[dict]:
    return await get_sector_allocation(session, portfolio_id, user_id)


# ── Transactions & Export ─────────────────────────────────────────────────────

@router.get("/portfolios/{portfolio_id}/transactions", response_model=list[TransactionResponse])
async def transactions_endpoint(
    portfolio_id: uuid.UUID,
    limit: int = Query(100, ge=1, le=1000),
    user_id: uuid.UUID = Depends(require_user_id),
    session: AsyncSession = Depends(get_read_session),
) -> list[TransactionResponse]:
    txs = await get_transactions(session, portfolio_id, user_id, limit=limit)
    return [TransactionResponse.model_validate(t) for t in txs]


@router.get("/portfolios/{portfolio_id}/export")
async def export_endpoint(
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_user_id),
    session: AsyncSession = Depends(get_read_session),
) -> PlainTextResponse:
    csv_data = await export_transactions_csv(session, portfolio_id, user_id)
    return PlainTextResponse(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=transactions_{portfolio_id}.csv"},
    )
