"""Portfolio CRUD, positions with weighted average price, analytics."""

import csv
import io
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.market import Instrument
from shared.models.portfolio import Portfolio, PortfolioItem, Transaction
from shared.tier_limits import PORTFOLIO_LIMITS, POSITION_LIMITS

logger = structlog.get_logger()


# ── Ownership check ──────────────────────────────────────────────────────────

async def _get_portfolio_owned(
    session: AsyncSession,
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Portfolio:
# Single query checks both existence AND ownership — no IDOR enumeration
    result = await session.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == user_id,
            Portfolio.deleted_at.is_(None),
        )
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    return portfolio


# ── Portfolio CRUD ────────────────────────────────────────────────────────────

async def create_portfolio(
    session: AsyncSession,
    user_id: uuid.UUID,
    name: str,
    description: str | None,
    tier: str,
) -> Portfolio:
    limit = PORTFOLIO_LIMITS.get(tier, 1)
    count_result = await session.execute(
        select(func.count()).select_from(Portfolio).where(
            Portfolio.user_id == user_id, Portfolio.deleted_at.is_(None)
        )
    )
    count = count_result.scalar() or 0
    if count >= limit:
        raise HTTPException(
            status_code=403,
            detail=f"Portfolio limit reached ({limit} for {tier} tier). Upgrade for more.",
        )

    is_default = count == 0
    portfolio = Portfolio(
        user_id=user_id, name=name, description=description, is_default=is_default,
    )
    session.add(portfolio)
    await session.flush()
    await logger.ainfo("portfolio_created", portfolio_id=str(portfolio.id), user_id=str(user_id))
    return portfolio


async def list_portfolios(session: AsyncSession, user_id: uuid.UUID) -> list[Portfolio]:
    result = await session.execute(
        select(Portfolio).where(
            Portfolio.user_id == user_id, Portfolio.deleted_at.is_(None)
        ).order_by(Portfolio.created_at)
    )
    return list(result.scalars().all())


async def get_portfolio(
    session: AsyncSession, portfolio_id: uuid.UUID, user_id: uuid.UUID,
) -> Portfolio:
    return await _get_portfolio_owned(session, portfolio_id, user_id)


async def delete_portfolio(
    session: AsyncSession, portfolio_id: uuid.UUID, user_id: uuid.UUID,
) -> None:
    portfolio = await _get_portfolio_owned(session, portfolio_id, user_id)
    portfolio.deleted_at = datetime.now(timezone.utc)
    await logger.ainfo("portfolio_deleted", portfolio_id=str(portfolio_id))


# ── Positions ─────────────────────────────────────────────────────────────────

async def add_position(
    session: AsyncSession,
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
    ticker: str,
    quantity: float,
    price: float,
    tier: str,
    notes: str | None = None,
) -> PortfolioItem:
    portfolio = await _get_portfolio_owned(session, portfolio_id, user_id)
    ticker_upper = ticker.upper()

    inst = await session.execute(
        select(Instrument.id).where(Instrument.ticker == ticker_upper)
    )
    instrument_id = inst.scalar_one_or_none()
    if not instrument_id:
        raise HTTPException(status_code=404, detail=f"Ticker {ticker_upper} not found")

    pos_limit = POSITION_LIMITS.get(tier, 10)
    pos_count = await session.execute(
        select(func.count()).select_from(PortfolioItem).where(
            # PortfolioItem.portfolio_id == portfolio_id
        )
    )
    if (pos_count.scalar() or 0) >= pos_limit:
        raise HTTPException(status_code=403, detail=f"Position limit reached ({pos_limit} for {tier} tier)")

    existing = await session.execute(
        select(PortfolioItem).where(
            PortfolioItem.portfolio_id == portfolio_id,
            PortfolioItem.ticker == ticker_upper,
        )
    )
    item = existing.scalar_one_or_none()

    if item:
        total_qty = item.quantity + quantity
        item.avg_buy_price = round(
            (item.quantity * item.avg_buy_price + quantity * price) / total_qty, 4
        )
        item.quantity = total_qty
    else:
        item = PortfolioItem(
            portfolio_id=portfolio_id,
            instrument_id=instrument_id,
            ticker=ticker_upper,
            quantity=quantity,
            avg_buy_price=price,
        )
        session.add(item)

    tx = Transaction(
        portfolio_id=portfolio_id,
        instrument_id=instrument_id,
        ticker=ticker_upper,
        type="buy",
        quantity=quantity,
        price=price,
        total_amount=round(quantity * price, 2),
        notes=notes,
        executed_at=datetime.now(timezone.utc),
    )
    session.add(tx)

    await session.flush()
    await logger.ainfo("position_added", ticker=ticker_upper, qty=quantity, price=price)
    return item


async def get_positions(
    session: AsyncSession, portfolio_id: uuid.UUID, user_id: uuid.UUID,
) -> list[PortfolioItem]:
    await _get_portfolio_owned(session, portfolio_id, user_id)
    result = await session.execute(
        select(PortfolioItem).where(PortfolioItem.portfolio_id == portfolio_id)
        .order_by(PortfolioItem.ticker)
    )
    return list(result.scalars().all())


async def delete_position(
    session: AsyncSession,
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
    ticker: str,
    quantity: float | None = None,
    price: float | None = None,
) -> None:
    await _get_portfolio_owned(session, portfolio_id, user_id)
    ticker_upper = ticker.upper()

    result = await session.execute(
        select(PortfolioItem).where(
            PortfolioItem.portfolio_id == portfolio_id,
            PortfolioItem.ticker == ticker_upper,
        )
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail=f"Position {ticker_upper} not found")

# Clamp sell_qty to actual held quantity
    sell_qty = min(quantity or item.quantity, item.quantity)
    sell_price = price or item.avg_buy_price

    if sell_qty >= item.quantity:
        await session.delete(item)
    else:
        item.quantity -= sell_qty

    inst = await session.execute(select(Instrument.id).where(Instrument.ticker == ticker_upper))
    instrument_id = inst.scalar_one()
    tx = Transaction(
        portfolio_id=portfolio_id,
        instrument_id=instrument_id,
        ticker=ticker_upper,
        type="sell",
        quantity=sell_qty,
        price=sell_price,
        total_amount=round(sell_qty * sell_price, 2),
        executed_at=datetime.now(timezone.utc),
    )
    session.add(tx)
    await logger.ainfo("position_sold", ticker=ticker_upper, qty=sell_qty)


# ── Analytics ─────────────────────────────────────────────────────────────────

async def get_analytics(
    session: AsyncSession, portfolio_id: uuid.UUID, user_id: uuid.UUID,
) -> dict:
    await _get_portfolio_owned(session, portfolio_id, user_id)

    items = await session.execute(
        select(PortfolioItem).where(PortfolioItem.portfolio_id == portfolio_id)
    )
    positions = items.scalars().all()
    if not positions:
        return {"total_value": 0, "total_pnl": 0, "total_pnl_pct": 0,
                "positions_count": 0, "best_position": None, "worst_position": None}

    total_value = sum(p.quantity * (p.current_price or p.avg_buy_price) for p in positions)
    total_cost = sum(p.quantity * p.avg_buy_price for p in positions)
    total_pnl = total_value - total_cost
    total_pnl_pct = round((total_pnl / total_cost * 100), 2) if total_cost else 0

    best = max(positions, key=lambda p: p.pnl_pct or 0)
    worst = min(positions, key=lambda p: p.pnl_pct or 0)

    return {
        "total_value": round(total_value, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pnl_pct": total_pnl_pct,
        "positions_count": len(positions),
        "best_position": best.ticker,
        "worst_position": worst.ticker,
    }


async def get_sector_allocation(
    session: AsyncSession, portfolio_id: uuid.UUID, user_id: uuid.UUID,
) -> list[dict]:
    await _get_portfolio_owned(session, portfolio_id, user_id)

    result = await session.execute(
        select(
            Instrument.sector,
            func.sum(PortfolioItem.quantity * PortfolioItem.avg_buy_price).label("value"),
        )
        .join(Instrument, PortfolioItem.instrument_id == Instrument.id)
        .where(PortfolioItem.portfolio_id == portfolio_id)
        .group_by(Instrument.sector)
    )

    rows = result.all()
    total = sum(r.value or 0 for r in rows)
    return [
        {"sector": r.sector or "Unknown", "value": round(float(r.value), 2),
         "pct": round(float(r.value) / total * 100, 2) if total else 0}
        for r in rows
    ]


async def get_transactions(
    session: AsyncSession,
    portfolio_id: uuid.UUID,
    user_id: uuid.UUID,
    limit: int = 100,
) -> list[Transaction]:
    """FIX #5: Added limit parameter for pagination."""
    await _get_portfolio_owned(session, portfolio_id, user_id)
    result = await session.execute(
        select(Transaction).where(Transaction.portfolio_id == portfolio_id)
        .order_by(Transaction.executed_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


def _sanitize_csv_value(val: str) -> str:
    """Prevent CSV injection: prefix dangerous chars with apostrophe."""
    if val and val[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{val}"
    return val


async def export_transactions_csv(
    session: AsyncSession, portfolio_id: uuid.UUID, user_id: uuid.UUID,
) -> str:
    txs = await get_transactions(session, portfolio_id, user_id, limit=10000)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date", "ticker", "type", "quantity", "price", "total", "notes"])
    for tx in txs:
        writer.writerow([
            tx.executed_at.isoformat(), tx.ticker, tx.type,
            tx.quantity, tx.price, tx.total_amount,
            _sanitize_csv_value(tx.notes or ""),
        ])
    return output.getvalue()
