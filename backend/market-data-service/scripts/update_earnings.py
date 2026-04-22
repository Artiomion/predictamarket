"""
Update earnings: fetch from yfinance earnings_dates → earnings_calendar + earnings_results.

For each ticker:
- Future dates (EPS Estimate only) → earnings.earnings_calendar
- Past dates (Reported EPS + Surprise%) → earnings.earnings_results
  Computes: eps_surprise_pct, beat_estimate

Usage:
  PYTHONPATH=backend .venv/bin/python backend/market-data-service/scripts/update_earnings.py
"""

import asyncio
import sys
from datetime import date
from pathlib import Path

# Add parent dirs to path: works both locally (backend/) and in Docker (/app/)
_script_dir = Path(__file__).resolve().parent
for _p in [_script_dir.parent.parent, _script_dir.parent]:
    if (_p / "shared").is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import structlog
import yfinance as yf
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.database import async_session_factory
from shared.logging import setup_logging
from shared.models.earnings import EarningsCalendar, EarningsResult
from shared.models.market import Instrument

setup_logging()
logger = structlog.get_logger()

BATCH_SIZE = 10


def _safe_float(val: object) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
        return f if f == f else None  # NaN check
    except (ValueError, TypeError):
        return None


async def update_earnings_for_ticker(
    session: AsyncSession,
    instrument_id: str,
    ticker: str,
) -> tuple[int, int]:
    """Fetch earnings_dates → upsert calendar + results. Returns (calendar_count, results_count)."""
    try:
        yf_ticker = yf.Ticker(ticker)
        ed = await asyncio.to_thread(lambda: yf_ticker.earnings_dates)
    except Exception as exc:
        await logger.aerror("yf_earnings_error", ticker=ticker, error=str(exc))
        return 0, 0

    if ed is None or ed.empty:
        return 0, 0

    today = date.today()
    cal_count = 0
    res_count = 0

    for idx, row in ed.iterrows():
        # idx is a Timestamp with timezone
        report_date = idx.date() if hasattr(idx, "date") else idx
        eps_estimate = _safe_float(row.get("EPS Estimate"))
        reported_eps = _safe_float(row.get("Reported EPS"))
        surprise_pct = _safe_float(row.get("Surprise(%)"))

        if report_date >= today:
            # Future → earnings_calendar
            stmt = pg_insert(EarningsCalendar).values(
                instrument_id=instrument_id,
                ticker=ticker,
                report_date=report_date,
                eps_estimate=eps_estimate,
            ).on_conflict_do_update(
                index_elements=["ticker", "report_date"],
                set_={"eps_estimate": eps_estimate},
            )
            await session.execute(stmt)
            cal_count += 1
        else:
            # Past → earnings_results
            beat = None
            if reported_eps is not None and eps_estimate is not None:
                beat = reported_eps > eps_estimate

            # Compute surprise_pct if yfinance didn't provide it
            if surprise_pct is None and reported_eps is not None and eps_estimate is not None and eps_estimate != 0:
                surprise_pct = round((reported_eps - eps_estimate) / abs(eps_estimate) * 100, 2)

            result_obj = EarningsResult(
                instrument_id=instrument_id,
                ticker=ticker,
                report_date=report_date,
                eps_actual=reported_eps,
                eps_estimate=eps_estimate,
                eps_surprise_pct=surprise_pct,
                beat_estimate=beat,
            )

            # Check if already exists (no unique constraint on earnings_results, so check manually)
            existing = await session.execute(
                select(EarningsResult.id).where(
                    EarningsResult.ticker == ticker,
                    EarningsResult.report_date == report_date,
                ).limit(1)
            )
            if not existing.scalar_one_or_none():
                session.add(result_obj)
                res_count += 1

    return cal_count, res_count


async def main() -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Instrument.id, Instrument.ticker).where(
                Instrument.is_active.is_(True), Instrument.deleted_at.is_(None)
            ).order_by(Instrument.ticker)
        )
        tickers = result.all()

    await logger.ainfo("update_earnings_start", total=len(tickers))

    success = 0
    failed = 0
    total_cal = 0
    total_res = 0

    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i:i + BATCH_SIZE]
        async with async_session_factory() as session:
            for inst_id, ticker in batch:
                try:
                    cal, res = await update_earnings_for_ticker(session, str(inst_id), ticker)
                    total_cal += cal
                    total_res += res
                    success += 1
                except Exception as exc:
                    await logger.aerror("update_earnings_fail", ticker=ticker, error=str(exc))
                    failed += 1
            await session.commit()

        await logger.ainfo("earnings_batch_done", batch=f"{i+1}-{min(i+BATCH_SIZE, len(tickers))}", success=success)

    await logger.ainfo("update_earnings_complete", success=success, failed=failed,
                        calendar_rows=total_cal, result_rows=total_res)


if __name__ == "__main__":
    asyncio.run(main())
