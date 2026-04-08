import uuid

import structlog
from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from shared.auth import require_user_id
from shared.database import get_session

from schemas.portfolio import (
    AddWatchlistItemRequest,
    CreateWatchlistRequest,
    WatchlistDetailResponse,
    WatchlistItemResponse,
    WatchlistResponse,
)
from services.watchlist_service import (
    add_watchlist_item,
    create_watchlist,
    get_watchlist_detail,
    list_watchlists,
    remove_watchlist_item,
)

logger = structlog.get_logger()
router = APIRouter()


@router.post("/watchlists", response_model=WatchlistResponse, status_code=201)
async def create_watchlist_endpoint(
    body: CreateWatchlistRequest,
    user_id: uuid.UUID = Depends(require_user_id),
    x_user_tier: str = Header("free"),
    session: AsyncSession = Depends(get_session),
) -> WatchlistResponse:
    wl = await create_watchlist(session, user_id, body.name, tier=x_user_tier)
    return WatchlistResponse.model_validate(wl)


@router.get("/watchlists", response_model=list[WatchlistResponse])
async def list_watchlists_endpoint(
    user_id: uuid.UUID = Depends(require_user_id),
    session: AsyncSession = Depends(get_session),
) -> list[WatchlistResponse]:
    wls = await list_watchlists(session, user_id)
    return [WatchlistResponse.model_validate(w) for w in wls]


@router.get("/watchlists/{watchlist_id}", response_model=WatchlistDetailResponse)
async def get_watchlist_endpoint(
    watchlist_id: uuid.UUID,
    user_id: uuid.UUID = Depends(require_user_id),
    session: AsyncSession = Depends(get_session),
) -> dict:
    return await get_watchlist_detail(session, watchlist_id, user_id)


@router.post("/watchlists/{watchlist_id}/items", response_model=WatchlistItemResponse, status_code=201)
async def add_item_endpoint(
    watchlist_id: uuid.UUID,
    body: AddWatchlistItemRequest,
    user_id: uuid.UUID = Depends(require_user_id),
    x_user_tier: str = Header("free"),
    session: AsyncSession = Depends(get_session),
) -> WatchlistItemResponse:
    item = await add_watchlist_item(session, watchlist_id, user_id, body.ticker, tier=x_user_tier)
    return WatchlistItemResponse.model_validate(item)


@router.delete("/watchlists/{watchlist_id}/items/{ticker}", status_code=204)
async def remove_item_endpoint(
    watchlist_id: uuid.UUID,
    ticker: str,
    user_id: uuid.UUID = Depends(require_user_id),
    session: AsyncSession = Depends(get_session),
) -> None:
    await remove_watchlist_item(session, watchlist_id, user_id, ticker)
