"""Watchlist CRUD."""

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.market import Instrument
from shared.models.portfolio import Watchlist, WatchlistItem
from shared.tier_limits import WATCHLIST_LIMITS, WATCHLIST_ITEM_LIMITS

logger = structlog.get_logger()


async def _get_watchlist_owned(
    session: AsyncSession, watchlist_id: uuid.UUID, user_id: uuid.UUID,
) -> Watchlist:
# Single query — no IDOR enumeration
    result = await session.execute(
        select(Watchlist).where(
            Watchlist.id == watchlist_id,
            Watchlist.user_id == user_id,
            Watchlist.deleted_at.is_(None),
        )
    )
    wl = result.scalar_one_or_none()
    if not wl:
        raise HTTPException(status_code=404, detail="Watchlist not found")
    return wl


async def create_watchlist(
    session: AsyncSession, user_id: uuid.UUID, name: str, tier: str = "free",
) -> Watchlist:
# Enforce tier limits
    limit = WATCHLIST_LIMITS.get(tier, 1)
    count_result = await session.execute(
        select(func.count()).select_from(Watchlist).where(
            Watchlist.user_id == user_id, Watchlist.deleted_at.is_(None)
        )
    )
    if (count_result.scalar() or 0) >= limit:
        raise HTTPException(
            status_code=403,
            detail=f"Watchlist limit reached ({limit} for {tier} tier). Upgrade for more.",
        )

    wl = Watchlist(user_id=user_id, name=name)
    session.add(wl)
    await session.flush()
    return wl


async def list_watchlists(session: AsyncSession, user_id: uuid.UUID) -> list[Watchlist]:
    result = await session.execute(
        select(Watchlist).where(
            Watchlist.user_id == user_id, Watchlist.deleted_at.is_(None)
        ).order_by(Watchlist.created_at)
    )
    return list(result.scalars().all())


async def get_watchlist_detail(
    session: AsyncSession, watchlist_id: uuid.UUID, user_id: uuid.UUID,
) -> dict:
    wl = await _get_watchlist_owned(session, watchlist_id, user_id)
    items_result = await session.execute(
        select(WatchlistItem).where(WatchlistItem.watchlist_id == watchlist_id)
        .order_by(WatchlistItem.added_at.desc())
    )
    items = items_result.scalars().all()
    return {
        "id": wl.id,
        "name": wl.name,
        "created_at": wl.created_at,
        "items": [
            {"id": i.id, "ticker": i.ticker, "added_at": i.added_at}
            for i in items
        ],
    }


async def add_watchlist_item(
    session: AsyncSession, watchlist_id: uuid.UUID, user_id: uuid.UUID,
    ticker: str, tier: str = "free",
) -> WatchlistItem:
    await _get_watchlist_owned(session, watchlist_id, user_id)
    ticker_upper = ticker.upper()

    inst = await session.execute(
        select(Instrument.id).where(Instrument.ticker == ticker_upper)
    )
    instrument_id = inst.scalar_one_or_none()
    if not instrument_id:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker_upper} not found")

# Enforce item limit
    item_limit = WATCHLIST_ITEM_LIMITS.get(tier, 10)
    item_count = await session.execute(
        select(func.count()).select_from(WatchlistItem).where(
            # WatchlistItem.watchlist_id == watchlist_id
        )
    )
    if (item_count.scalar() or 0) >= item_limit:
        raise HTTPException(status_code=403, detail=f"Watchlist item limit reached ({item_limit} for {tier} tier)")

    existing = await session.execute(
        select(WatchlistItem).where(
            WatchlistItem.watchlist_id == watchlist_id,
            WatchlistItem.ticker == ticker_upper,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"{ticker_upper} already in watchlist")

    item = WatchlistItem(
        watchlist_id=watchlist_id,
        instrument_id=instrument_id,
        ticker=ticker_upper,
        added_at=datetime.now(timezone.utc),
    )
    session.add(item)
    await session.flush()
    return item


async def remove_watchlist_item(
    session: AsyncSession, watchlist_id: uuid.UUID, user_id: uuid.UUID, ticker: str,
) -> None:
    await _get_watchlist_owned(session, watchlist_id, user_id)
    ticker_upper = ticker.upper()

    result = await session.execute(
        select(WatchlistItem).where(
            WatchlistItem.watchlist_id == watchlist_id,
            WatchlistItem.ticker == ticker_upper,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail=f"{ticker_upper} not in watchlist")
    await session.delete(item)
