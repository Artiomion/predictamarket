"""
Update financials: fetch from yfinance info → market.financial_metrics.

Populates P/E, P/B, dividend yield, ROE, ROA, EPS, revenue, net income, etc.
Creates one "latest" row per ticker (period_type='annual' for trailing 12 months).

Usage:
  PYTHONPATH=backend .venv/bin/python backend/market-data-service/scripts/update_financials.py
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
from shared.models.market import FinancialMetric, Instrument

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


async def update_financials_for_ticker(
    session: AsyncSession,
    instrument_id: str,
    ticker: str,
) -> bool:
    """Fetch yfinance info → upsert financial_metrics. Returns True on success."""
    try:
        yf_ticker = yf.Ticker(ticker)
        info = await asyncio.to_thread(lambda: yf_ticker.info)
    except Exception as exc:
        await logger.aerror("yf_financials_error", ticker=ticker, error=str(exc))
        return False

    if not info:
        return False

    today = date.today()

    stmt = pg_insert(FinancialMetric).values(
        instrument_id=instrument_id,
        ticker=ticker,
        period_end=today,
        period_type="annual",
        revenue=_safe_float(info.get("totalRevenue")),
        net_income=_safe_float(info.get("netIncomeToCommon")),
        eps=_safe_float(info.get("trailingEps")),
        pe_ratio=_safe_float(info.get("trailingPE")),
        pb_ratio=_safe_float(info.get("priceToBook")),
        dividend_yield=_safe_float(info.get("dividendYield")),
        debt_to_equity=_safe_float(info.get("debtToEquity")),
        roe=_safe_float(info.get("returnOnEquity")),
        roa=_safe_float(info.get("returnOnAssets")),
        free_cash_flow=_safe_float(info.get("freeCashflow")),
        operating_margin=_safe_float(info.get("operatingMargins")),
        current_ratio=_safe_float(info.get("currentRatio")),
    ).on_conflict_do_update(
        index_elements=["ticker", "period_end", "period_type"],
        set_={
            "revenue": _safe_float(info.get("totalRevenue")),
            "net_income": _safe_float(info.get("netIncomeToCommon")),
            "eps": _safe_float(info.get("trailingEps")),
            "pe_ratio": _safe_float(info.get("trailingPE")),
            "pb_ratio": _safe_float(info.get("priceToBook")),
            "dividend_yield": _safe_float(info.get("dividendYield")),
            "debt_to_equity": _safe_float(info.get("debtToEquity")),
            "roe": _safe_float(info.get("returnOnEquity")),
            "roa": _safe_float(info.get("returnOnAssets")),
            "free_cash_flow": _safe_float(info.get("freeCashflow")),
            "operating_margin": _safe_float(info.get("operatingMargins")),
            "current_ratio": _safe_float(info.get("currentRatio")),
        },
    )
    await session.execute(stmt)
    return True


async def main() -> None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(Instrument.id, Instrument.ticker).where(
                Instrument.is_active.is_(True), Instrument.deleted_at.is_(None)
            ).order_by(Instrument.ticker)
        )
        tickers = result.all()

    await logger.ainfo("update_financials_start", total=len(tickers))

    success = 0
    failed = 0

    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i:i + BATCH_SIZE]
        async with async_session_factory() as session:
            for inst_id, ticker in batch:
                try:
                    ok = await update_financials_for_ticker(session, str(inst_id), ticker)
                    if ok:
                        success += 1
                    else:
                        failed += 1
                except Exception as exc:
                    await logger.aerror("update_financial_fail", ticker=ticker, error=str(exc))
                    failed += 1
            await session.commit()

        await logger.ainfo("financials_batch_done", batch=f"{i+1}-{min(i+BATCH_SIZE, len(tickers))}", success=success)

    await logger.ainfo("update_financials_complete", success=success, failed=failed)


if __name__ == "__main__":
    asyncio.run(main())
