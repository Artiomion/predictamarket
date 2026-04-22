import json
import os
from datetime import date, timedelta
from pathlib import Path

import structlog
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from shared.models.market import CompanyProfile, FinancialMetric, Instrument, PriceHistory
from shared.redis_client import redis_client

from schemas.market import (
    InstrumentDetailResponse,
    InstrumentListResponse,
    InstrumentResponse,
)

logger = structlog.get_logger()

CACHE_LIST_TTL = 60       # 1 min
CACHE_DETAIL_TTL = 300    # 5 min
CACHE_PRICE_TTL = 60      # 1 min

# Load ticker blocklist from models/blocklist_tickers.txt. These are tickers
# where post-split / corporate-action data mismatch makes forecasts
# unreliable — we hide them from the catalog and return 404 on direct
# /instruments/{ticker} lookups so they're effectively removed from the
# service. Watchlist / portfolio rows that reference them are left in DB
# but will fail to render (404) — user's data isn't deleted, just the
# ticker is uncovered. Will be re-enabled after a retrain on
# split-adjusted prices.
_MODELS_DIR = Path(os.environ.get("MODELS_DIR", "/models"))
BLOCKLISTED_TICKERS: set[str] = set()
try:
    _bl_file = _MODELS_DIR / "blocklist_tickers.txt"
    if _bl_file.exists():
        BLOCKLISTED_TICKERS = {
            t.strip().upper()
            for t in _bl_file.read_text().strip().splitlines()
            if t.strip() and not t.strip().startswith("#")
        }
        logger.info("blocklist_loaded", n=len(BLOCKLISTED_TICKERS))
except Exception as exc:
    logger.warning("blocklist_load_failed", error=str(exc))


def _escape_like(value: str) -> str:
    """FIX #1: Escape LIKE wildcards to prevent filter bypass."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def _check_instrument_exists(session: AsyncSession, ticker: str) -> None:
    """FIX #2/#3: Lightweight existence check without eager-loading profile."""
    if ticker.upper() in BLOCKLISTED_TICKERS:
        raise HTTPException(status_code=404, detail=f"Instrument {ticker} not currently served.")
    result = await session.execute(
        select(Instrument.id).where(
            Instrument.ticker == ticker,
            Instrument.is_active.is_(True),
            Instrument.deleted_at.is_(None),
        )
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail=f"Instrument {ticker} not found")


async def get_instruments(
    session: AsyncSession,
    page: int = 1,
    per_page: int = 50,
    sector: str | None = None,
    search: str | None = None,
    sort_by: str = "ticker",
    order: str = "asc",
) -> dict:
    """FIX #5: Always return dict — no more tuple[None, dict] for cache hits."""
    cache_key = f"mkt:instruments:{page}:{per_page}:{sector}:{search}:{sort_by}:{order}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    query = select(Instrument).where(
        Instrument.is_active.is_(True),
        Instrument.deleted_at.is_(None),
    )

    # Hide blocklisted tickers from the catalog entirely.
    if BLOCKLISTED_TICKERS:
        query = query.where(Instrument.ticker.not_in(BLOCKLISTED_TICKERS))

    if sector:
        query = query.where(Instrument.sector == sector)
    if search:
        escaped = _escape_like(search)
        pattern = f"%{escaped}%"
        query = query.where(
            (Instrument.ticker.ilike(pattern)) | (Instrument.name.ilike(pattern))
        )

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    # Sort
    allowed_sorts = {"ticker", "name", "sector", "market_cap"}
    col = getattr(Instrument, sort_by if sort_by in allowed_sorts else "ticker")
    query = query.order_by(col.desc() if order == "desc" else col.asc())

    # Paginate
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await session.execute(query)
    instruments = list(result.scalars().all())

    resp = InstrumentListResponse(
        data=[InstrumentResponse.model_validate(i) for i in instruments],
        total=total,
        page=page,
        per_page=per_page,
    )
    data = resp.model_dump(mode="json")
    await redis_client.set(cache_key, json.dumps(data), ex=CACHE_LIST_TTL)
    return data


async def get_instrument_by_ticker(
    session: AsyncSession,
    ticker: str,
) -> Instrument:
    ticker_upper = ticker.upper()

    if ticker_upper in BLOCKLISTED_TICKERS:
        raise HTTPException(
            status_code=404,
            detail=f"Instrument {ticker_upper} is not currently served — see docs/MODEL.md blocklist.",
        )

    result = await session.execute(
        select(Instrument)
        .options(selectinload(Instrument.profile))
        .where(
            Instrument.ticker == ticker_upper,
            Instrument.is_active.is_(True),
            Instrument.deleted_at.is_(None),
        )
    )
    instrument = result.scalar_one_or_none()
    if not instrument:
        raise HTTPException(status_code=404, detail=f"Instrument {ticker_upper} not found")
    return instrument


async def get_instrument_detail_cached(
    session: AsyncSession,
    ticker: str,
) -> dict:
    ticker_upper = ticker.upper()
    cache_key = f"mkt:detail:{ticker_upper}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    instrument = await get_instrument_by_ticker(session, ticker)

    profile = instrument.profile
    resp = InstrumentDetailResponse(
        id=instrument.id,
        ticker=instrument.ticker,
        name=instrument.name,
        sector=instrument.sector,
        industry=instrument.industry,
        market_cap=instrument.market_cap,
        exchange=instrument.exchange,
        is_active=instrument.is_active,
        description=profile.description if profile else None,
        website=profile.website if profile else None,
        logo_url=profile.logo_url if profile else None,
        ceo=profile.ceo if profile else None,
        employees=profile.employees if profile else None,
        headquarters=profile.headquarters if profile else None,
        founded_year=profile.founded_year if profile else None,
    )
    data = resp.model_dump(mode="json")
    await redis_client.set(cache_key, json.dumps(data), ex=CACHE_DETAIL_TTL)
    return data


async def get_price_history(
    session: AsyncSession,
    ticker: str,
    period: str = "1y",
    interval: str = "1d",
) -> list[PriceHistory]:
    ticker_upper = ticker.upper()

# Lightweight check — no profile eager loading
    await _check_instrument_exists(session, ticker_upper)

    # Calendar days (not trading days) — sufficient for date filtering
    period_map = {
        "1m": 30, "3m": 90, "6m": 180,
        "1y": 365, "2y": 730, "5y": 1825, "max": 9999,
    }
    days = period_map.get(period, 365)
    start_date = date.today() - timedelta(days=days)

    query = (
        select(PriceHistory)
        .where(
            PriceHistory.ticker == ticker_upper,
            PriceHistory.date >= start_date,
        )
        .order_by(PriceHistory.date.asc())
    )

    result = await session.execute(query)
    return list(result.scalars().all())


async def get_current_price(session: AsyncSession, ticker: str) -> dict:
    """FIX #9: Fallback to last close from price_history if Redis has no data."""
    ticker_upper = ticker.upper()
    cache_key = f"mkt:price:{ticker_upper}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Fallback: last close from price_history
    result = await session.execute(
        select(PriceHistory.close, PriceHistory.date)
        .where(PriceHistory.ticker == ticker_upper)
        .order_by(PriceHistory.date.desc())
        .limit(2)
    )
    rows = result.all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No price data for {ticker_upper}")

    last_close = rows[0][0]
    last_date = rows[0][1]
    prev_close = rows[1][0] if len(rows) > 1 else None
    change = round(last_close - prev_close, 2) if prev_close else None
    change_pct = round((last_close - prev_close) / prev_close * 100, 2) if prev_close else None

    return {
        "ticker": ticker_upper,
        "price": last_close,
        "change": change,
        "change_pct": change_pct,
        "updated_at": str(last_date),
    }


async def get_financials(
    session: AsyncSession,
    ticker: str,
    period_type: str = "quarterly",
) -> list[FinancialMetric]:
    ticker_upper = ticker.upper()

# Lightweight check
    await _check_instrument_exists(session, ticker_upper)

    query = (
        select(FinancialMetric)
        .where(
            FinancialMetric.ticker == ticker_upper,
            FinancialMetric.period_type == period_type,
        )
        .order_by(FinancialMetric.period_end.desc())
        .limit(20)
    )

    result = await session.execute(query)
    return list(result.scalars().all())
