"""
Seed script: populate market.instruments + market.price_history + market.company_profiles.

Source:
  - Tickers: models/old_model_sp500_tickers.txt (346 S&P 500 tickers)
  - Sectors: models/config.json -> "sectors" dict
  - Data: yfinance (info, 5y OHLCV history)

Usage:
  PYTHONPATH=backend .venv/bin/python backend/market-data-service/scripts/seed_instruments.py
"""

import asyncio
import json
import sys
from datetime import date
from pathlib import Path

# Allow imports from backend/shared
# Add parent dirs to path: works both locally (backend/) and in Docker (/app/)
_script_dir = Path(__file__).resolve().parent
for _p in [_script_dir.parent.parent, _script_dir.parent]:
    if (_p / "shared").is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import structlog
import yfinance as yf
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import async_session_factory
from shared.logging import setup_logging
from shared.models.market import CompanyProfile, Instrument, PriceHistory

setup_logging()
logger = structlog.get_logger()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TICKERS_FILE = PROJECT_ROOT / "models" / "old_model_sp500_tickers.txt"
CONFIG_FILE = PROJECT_ROOT / "models" / "config.json"


def load_tickers() -> list[str]:
    """Read 346 S&P 500 tickers from file, uppercase them."""
    raw = TICKERS_FILE.read_text().strip().splitlines()
    return [t.strip().upper() for t in raw if t.strip()]


def load_sectors() -> dict[str, str]:
    """Load ticker->sector mapping from config.json."""
    with open(CONFIG_FILE) as f:
        cfg = json.load(f)
    sectors = cfg.get("sectors", {})
    # Normalize keys to uppercase, skip 'nan' values
    return {
        k.upper(): v
        for k, v in sectors.items()
        if v and str(v).lower() != "nan"
    }


async def seed_instrument(
    session: AsyncSession,
    ticker: str,
    sectors: dict[str, str],
) -> bool:
    """Seed a single instrument + profile + 5y price history. Returns True on success."""
    existing_result = await session.execute(
        select(Instrument).where(Instrument.ticker == ticker)
    )
    existing = existing_result.scalar_one_or_none()
    if existing:
        price_count = await session.execute(
            select(func.count()).select_from(PriceHistory).where(PriceHistory.ticker == ticker)
        )
        if (price_count.scalar() or 0) > 0:
            await logger.ainfo("skip_existing", ticker=ticker)
            return True
        # Instrument exists but no price data — backfill below
        await logger.ainfo("backfill_prices", ticker=ticker)

    yf_ticker = yf.Ticker(ticker)

    # Create instrument + profile only if new
    if not existing:
        try:
            info = await asyncio.to_thread(lambda: yf_ticker.info)
        except Exception as exc:
            await logger.aerror("yfinance_info_error", ticker=ticker, error=str(exc))
            return False

        if not info or info.get("regularMarketPrice") is None:
            await logger.awarning("no_yfinance_data", ticker=ticker)
            info = {}

        instrument = Instrument(
            ticker=ticker,
            name=info.get("shortName") or info.get("longName") or ticker,
            sector=sectors.get(ticker) or info.get("sector"),
            industry=info.get("industry"),
            market_cap=info.get("marketCap"),
            exchange=info.get("exchange", "NYSE"),
        )
        session.add(instrument)
        await session.flush()

        profile = CompanyProfile(
            instrument_id=instrument.id,
            ticker=ticker,
            description=info.get("longBusinessSummary"),
            website=info.get("website"),
            logo_url=info.get("logo_url"),
            ceo=None,
            employees=info.get("fullTimeEmployees"),
            headquarters=(
                f"{info.get('city', '')}, {info.get('state', '')}, {info.get('country', '')}"
                if info.get("city") else None
            ),
            founded_year=None,
        )
        session.add(profile)
    else:
        instrument = existing

    # Fetch 5y OHLCV
    try:
        hist = await asyncio.to_thread(
            lambda: yf_ticker.history(period="5y", interval="1d", auto_adjust=False)
        )
    except Exception as exc:
        await logger.aerror("yfinance_history_error", ticker=ticker, error=str(exc))
        return True  # Instrument created, just no price data

    if hist.empty:
        await logger.awarning("empty_history", ticker=ticker)
        return True

    # Bulk insert price history
    rows = []
    for idx, row in hist.iterrows():
        trade_date = idx.date() if hasattr(idx, "date") else idx
        rows.append(PriceHistory(
            instrument_id=instrument.id,
            ticker=ticker,
            date=trade_date,
            open=float(row["Open"]) if row["Open"] == row["Open"] else None,
            high=float(row["High"]) if row["High"] == row["High"] else None,
            low=float(row["Low"]) if row["Low"] == row["Low"] else None,
            close=float(row["Close"]),
            adj_close=float(row.get("Adj Close", row["Close"])),
            volume=int(row["Volume"]) if row["Volume"] == row["Volume"] else None,
        ))

    session.add_all(rows)
    await logger.ainfo("seeded", ticker=ticker, price_rows=len(rows))
    return True


async def main() -> None:
    tickers = load_tickers()
    sectors = load_sectors()
    await logger.ainfo("seed_start", total_tickers=len(tickers))

    success = 0
    failed = 0

    # Process in batches to control memory + commit frequency
    BATCH_SIZE = 5
    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i : i + BATCH_SIZE]
        async with async_session_factory() as session:
            for ticker in batch:
                try:
                    ok = await seed_instrument(session, ticker, sectors)
                    if ok:
                        success += 1
                    else:
                        failed += 1
                except Exception as exc:
                    await logger.aerror("seed_error", ticker=ticker, error=str(exc))
                    failed += 1
            await session.commit()

        await logger.ainfo(
            "batch_done",
            batch=f"{i+1}-{min(i+BATCH_SIZE, len(tickers))}",
            success=success,
            failed=failed,
        )

    await logger.ainfo("seed_complete", success=success, failed=failed, total=len(tickers))


if __name__ == "__main__":
    asyncio.run(main())
