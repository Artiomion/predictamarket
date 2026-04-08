"""
Update insider transactions: fetch from yfinance → insider.insider_transactions.

For each ticker, fetches recent insider trades (buys, sales, option exercises)
and inserts new records (deduplication by ticker + insider_name + filing_date + shares).

Usage:
  PYTHONPATH=backend .venv/bin/python backend/market-data-service/scripts/update_insider.py
"""

import asyncio
import sys
from datetime import date, datetime
from pathlib import Path

# Add parent dirs to path: works both locally (backend/) and in Docker (/app/)
_script_dir = Path(__file__).resolve().parent
for _p in [_script_dir.parent.parent, _script_dir.parent]:
    if (_p / "shared").is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import structlog
import yfinance as yf
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import async_session_factory
from shared.logging import setup_logging
from shared.models.insider import InsiderTransaction
from shared.models.market import Instrument

setup_logging()
logger = structlog.get_logger()

BATCH_SIZE = 10

# Map yfinance transaction text → our enum
TRANSACTION_TYPE_MAP = {
    "sale": "sell",
    "purchase": "buy",
    "option exercise": "option_exercise",
    "gift": "gift",
    "conversion": "option_exercise",
    "automatic sale": "sell",
    "automatic purchase": "buy",
}


def _safe_float(val: object) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        return f if f == f else None
    except (ValueError, TypeError):
        return None


def _parse_date(val: object) -> date | None:
    if val is None:
        return None
    if isinstance(val, date):
        return val
    if isinstance(val, datetime):
        return val.date()
    try:
        return datetime.strptime(str(val), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _map_transaction_type(raw: str | None) -> str:
    if not raw:
        return "sell"
    lower = raw.lower().strip()
    # Check each known type
    for key, val in TRANSACTION_TYPE_MAP.items():
        if key in lower:
            return val
    # Fallback: if "sale" in text → sell, "purchase" → buy
    if "sale" in lower or "sell" in lower:
        return "sell"
    if "buy" in lower or "purchase" in lower:
        return "buy"
    return "sell"


async def update_insider_for_ticker(
    session: AsyncSession,
    instrument_id: str,
    ticker: str,
) -> int:
    """Fetch insider_transactions → insert new records. Returns count inserted."""
    try:
        yf_ticker = yf.Ticker(ticker)
        it = await asyncio.to_thread(lambda: yf_ticker.insider_transactions)
    except Exception as exc:
        await logger.aerror("yf_insider_error", ticker=ticker, error=str(exc))
        return 0

    if it is None or it.empty:
        return 0

    inserted = 0

    for _, row in it.iterrows():
        insider_name = str(row.get("Insider", "")).strip()
        if not insider_name:
            continue

        filing_date = _parse_date(row.get("Start Date"))
        if not filing_date:
            continue

        shares = _safe_float(row.get("Shares"))
        if shares is None:
            continue

        value = _safe_float(row.get("Value"))
        position = str(row.get("Position", "")) or None
        tx_type = _map_transaction_type(row.get("Transaction"))

        # Price per share from value/shares
        price_per_share = round(value / abs(shares), 2) if value and shares and shares != 0 else None

        # Dedup: check if this exact record exists
        existing = await session.execute(
            select(InsiderTransaction.id).where(
                and_(
                    InsiderTransaction.ticker == ticker,
                    InsiderTransaction.insider_name == insider_name,
                    InsiderTransaction.filing_date == filing_date,
                    InsiderTransaction.shares == shares,
                )
            ).limit(1)
        )
        if existing.scalar_one_or_none():
            continue

        tx = InsiderTransaction(
            instrument_id=instrument_id,
            ticker=ticker,
            insider_name=insider_name,
            insider_title=position,
            transaction_type=tx_type,
            shares=abs(shares),
            price_per_share=price_per_share,
            total_value=abs(value) if value else None,
            filing_date=filing_date,
            transaction_date=filing_date,
        )
        session.add(tx)
        inserted += 1

    return inserted


async def main() -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Instrument.id, Instrument.ticker).where(
                Instrument.is_active.is_(True), Instrument.deleted_at.is_(None)
            ).order_by(Instrument.ticker)
        )
        tickers = result.all()

    await logger.ainfo("update_insider_start", total=len(tickers))

    success = 0
    failed = 0
    total_inserted = 0

    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i:i + BATCH_SIZE]
        async with async_session_factory() as session:
            for inst_id, ticker in batch:
                try:
                    n = await update_insider_for_ticker(session, str(inst_id), ticker)
                    total_inserted += n
                    success += 1
                except Exception as exc:
                    await logger.aerror("update_insider_fail", ticker=ticker, error=str(exc))
                    failed += 1
            await session.commit()

        await logger.ainfo("insider_batch_done", batch=f"{i+1}-{min(i+BATCH_SIZE, len(tickers))}", success=success)

    await logger.ainfo("update_insider_complete", success=success, failed=failed, inserted=total_inserted)


if __name__ == "__main__":
    asyncio.run(main())
