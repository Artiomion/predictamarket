"""
Fetch FRED macro series and upsert into market.macro_history.

Series:
  CPIAUCSL   → cpi              (Consumer Price Index, monthly)
  UNRATE     → unemployment     (Unemployment Rate, monthly)
  DFF        → fed_funds_rate   (Federal Funds Effective, daily)
  T10Y2Y     → yield_curve_spread (10Y-2Y Treasury Spread, daily)
  M2SL       → m2_money_supply  (M2 Money Stock, monthly)
  DCOILWTICO → wti_crude        (WTI Spot Price, daily)
  VIXCLS     → fred_vix         (CBOE VIX, daily)

Run daily (e.g. 06:00 ET via dag_fetch_macro_fred). Idempotent — forward-fills
monthly series across days since last update.
"""

import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

_script_dir = Path(__file__).resolve().parent
for _p in [_script_dir.parent.parent, _script_dir.parent]:
    if (_p / "shared").is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import requests
import structlog
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.config import settings
from shared.database import async_session_factory
from shared.logging import setup_logging
from shared.models.market import MacroHistory

setup_logging()
logger = structlog.get_logger()

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

SERIES_MAP = {
    "CPIAUCSL":   "cpi",
    "UNRATE":     "unemployment",
    "DFF":        "fed_funds_rate",
    "T10Y2Y":     "yield_curve_spread",
    "M2SL":       "m2_money_supply",
    "DCOILWTICO": "wti_crude",
    "VIXCLS":     "fred_vix",
}


def fetch_series_sync(series_id: str, start_date: date) -> list[tuple[date, float]]:
    """Blocking FRED fetch with exponential backoff retry.

    FRED API occasionally 5xx's under load; 3 attempts at 1s/2s/4s cover ~99%
    of transient failures without extending the happy-path latency.
    """
    import time

    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            r = requests.get(FRED_BASE, params={
                "series_id": series_id,
                "api_key": settings.FRED_API_KEY,
                "file_type": "json",
                "observation_start": start_date.isoformat(),
            }, timeout=30)
            r.raise_for_status()
            obs = r.json().get("observations", [])
            out: list[tuple[date, float]] = []
            for o in obs:
                v = o.get("value")
                if v in (None, ".", ""):
                    continue
                try:
                    out.append((date.fromisoformat(o["date"]), float(v)))
                except (ValueError, TypeError):
                    continue
            return out
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
            last_exc = exc
            if attempt < 2:
                time.sleep(2 ** attempt)  # 1s, 2s
    assert last_exc is not None
    raise last_exc


async def main() -> None:
    api_key = getattr(settings, "FRED_API_KEY", None)
    if not api_key:
        await logger.aerror("fred_api_key_missing")
        return

    start = date.today() - timedelta(days=400)  # ~1y window, covers monthly series

    series_data: dict[str, dict[date, float]] = {}
    for series_id, col in SERIES_MAP.items():
        try:
            obs = await asyncio.to_thread(fetch_series_sync, series_id, start)
            series_data[col] = dict(obs)
            await logger.ainfo("fred_fetched", series=series_id, col=col, points=len(obs))
        except (requests.Timeout, requests.ConnectionError, requests.HTTPError, ValueError) as exc:
            # Narrow catches — transient network issues or bad JSON. BaseException,
            # KeyboardInterrupt, asyncio.CancelledError propagate as expected.
            await logger.aerror("fred_fetch_error", series=series_id, error=str(exc))

    if not series_data:
        return

    # Assemble per-date rows. Forward-fill across business days.
    all_dates = sorted({d for obs in series_data.values() for d in obs.keys()})
    last_known: dict[str, float | None] = {c: None for c in SERIES_MAP.values()}

    # Upsert via SQLAlchemy Core — no string interpolation. COALESCE keeps the
    # previously-stored value when the new value is NULL (monthly series may
    # be NULL on daily rows before the next release).
    fred_cols = list(SERIES_MAP.values())

    async with async_session_factory() as session:
        for d in all_dates:
            for col in fred_cols:
                if d in series_data.get(col, {}):
                    last_known[col] = series_data[col][d]
            if all(v is None for v in last_known.values()):
                continue

            values = {"date": d, **{c: last_known[c] for c in fred_cols}}
            stmt = pg_insert(MacroHistory).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["date"],
                set_={
                    c: func.coalesce(stmt.excluded[c], getattr(MacroHistory, c))
                    for c in fred_cols
                } | {"updated_at": func.now()},
            )
            await session.execute(stmt)
        await session.commit()

    await logger.ainfo("fred_update_complete", dates=len(all_dates))


if __name__ == "__main__":
    asyncio.run(main())
