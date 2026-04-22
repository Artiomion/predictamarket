"""
Update prices: fetch latest OHLCV from yfinance → price_history + Redis cache.

Fetches last 5 trading days for each ticker, upserts into price_history,
and caches the latest close in Redis for GET /instruments/{ticker}/price.

Usage:
  PYTHONPATH=backend .venv/bin/python backend/market-data-service/scripts/update_prices.py
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent dirs to path: works both locally (backend/) and in Docker (/app/)
_script_dir = Path(__file__).resolve().parent
for _p in [_script_dir.parent.parent, _script_dir.parent]:
    if (_p / "shared").is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import structlog
import yfinance as yf
from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import async_session_factory
from shared.logging import setup_logging
from shared.models.market import Instrument, PriceHistory
from shared.redis_client import redis_client

setup_logging()
logger = structlog.get_logger()

BATCH_SIZE = 10
PRICE_CACHE_TTL = 300  # 5 min

# Sanity-check threshold: reject any yfinance close that differs from the
# last known DB close by more than this fraction. Previously saw GS get
# corrupted with volume=0 rows at ~$19 when the real price was ~$926
# (delta ~−98%) — yfinance sometimes returns stale / pre-split unadjusted
# data under rate-limit conditions. A >50% move in a liquid S&P 500 name
# in a single day is virtually impossible; treating it as corruption and
# skipping the upsert is the safer default.
BACKFILL_MAX_DELTA = 0.5


async def _get_latest_db_close(session: AsyncSession, ticker: str) -> float | None:
    """Latest stored close for `ticker`, or None if no history."""
    q = await session.execute(
        text("SELECT close FROM market.price_history WHERE ticker = :t "
             "ORDER BY date DESC LIMIT 1"),
        {"t": ticker},
    )
    row = q.first()
    return float(row[0]) if row and row[0] is not None else None


async def update_prices_for_ticker(
    session: AsyncSession,
    instrument_id: str,
    ticker: str,
) -> int:
    """Fetch last 5d OHLCV, upsert into price_history, cache latest price. Returns rows upserted."""
    try:
        yf_ticker = yf.Ticker(ticker)
        hist = await asyncio.to_thread(
            lambda: yf_ticker.history(period="5d", interval="1d", auto_adjust=False)
        )
    except Exception as exc:
        await logger.aerror("yf_price_error", ticker=ticker, error=str(exc))
        return 0

    if hist.empty:
        return 0

    # Sanity check: if the newest yfinance close is wildly off from what we
    # already have for this ticker, treat the whole response as suspect and
    # bail. This matches the same guard in forecast-service's
    # _backfill_fresh_prices and protects against silent corruption.
    try:
        newest_close = float(hist.iloc[-1]["Close"])
        db_close = await _get_latest_db_close(session, ticker)
        if db_close and db_close > 0 and newest_close > 0:
            delta = abs(newest_close / db_close - 1)
            if delta > BACKFILL_MAX_DELTA:
                await logger.aerror(
                    "update_prices_rejected_extreme_delta",
                    ticker=ticker,
                    yf_close=newest_close,
                    db_close=db_close,
                    delta_pct=round(delta * 100, 1),
                )
                return 0
    except Exception as exc:
        # Sanity check shouldn't hard-fail the pipeline — log and continue.
        await logger.awarning("update_prices_sanity_check_failed", ticker=ticker, error=str(exc))

    rows_upserted = 0

    for idx, row in hist.iterrows():
        trade_date = idx.date() if hasattr(idx, "date") else idx
        close_val = float(row["Close"])
        volume_val = int(row["Volume"]) if row["Volume"] == row["Volume"] else None

        stmt = pg_insert(PriceHistory).values(
            instrument_id=instrument_id,
            ticker=ticker,
            date=trade_date,
            open=float(row["Open"]) if row["Open"] == row["Open"] else None,
            high=float(row["High"]) if row["High"] == row["High"] else None,
            low=float(row["Low"]) if row["Low"] == row["Low"] else None,
            close=close_val,
            adj_close=float(row.get("Adj Close", row["Close"])),
            volume=volume_val,
        ).on_conflict_do_update(
            index_elements=["ticker", "date"],
            set_={"close": close_val, "open": float(row["Open"]), "high": float(row["High"]),
                   "low": float(row["Low"]), "volume": volume_val},
        )
        await session.execute(stmt)
        rows_upserted += 1

    # Cache latest price in Redis
    if not hist.empty:
        latest = hist.iloc[-1]
        latest_close = float(latest["Close"])
        prev_row_close = float(hist.iloc[-2]["Close"]) if len(hist) >= 2 else None
        change = round(latest_close - prev_row_close, 2) if prev_row_close else None
        change_pct = round((latest_close - prev_row_close) / prev_row_close * 100, 2) if prev_row_close else None

        price_data = {
            "ticker": ticker,
            "price": latest_close,
            "change": change,
            "change_pct": change_pct,
            "updated_at": str(hist.index[-1].date() if hasattr(hist.index[-1], "date") else hist.index[-1]),
        }
        price_json = json.dumps(price_data)
        # Only publish if price actually changed (avoid redundant WebSocket pushes)
        old = await redis_client.get(f"mkt:price:{ticker}")
        await redis_client.set(f"mkt:price:{ticker}", price_json, ex=PRICE_CACHE_TTL)
        if old != price_json:
            await redis_client.publish("price.updated", price_json)

    return rows_upserted


async def main() -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Instrument.id, Instrument.ticker).where(
                Instrument.is_active.is_(True), Instrument.deleted_at.is_(None)
            ).order_by(Instrument.ticker)
        )
        tickers = result.all()

    await logger.ainfo("update_prices_start", total=len(tickers))

    success = 0
    failed = 0
    total_rows = 0

    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i:i + BATCH_SIZE]
        async with async_session_factory() as session:
            for inst_id, ticker in batch:
                try:
                    n = await update_prices_for_ticker(session, str(inst_id), ticker)
                    total_rows += n
                    success += 1
                except Exception as exc:
                    await logger.aerror("update_price_fail", ticker=ticker, error=str(exc))
                    failed += 1
            await session.commit()

        await logger.ainfo("price_batch_done", batch=f"{i+1}-{min(i+BATCH_SIZE, len(tickers))}", success=success)

    await redis_client.aclose()
    await logger.ainfo("update_prices_complete", success=success, failed=failed, rows=total_rows)


if __name__ == "__main__":
    asyncio.run(main())
