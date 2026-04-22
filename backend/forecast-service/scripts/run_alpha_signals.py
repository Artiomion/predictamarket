"""
Batch alpha-signals: run 3-model ensemble inference for all valid tickers,
store results in forecast.alpha_signals, publish Redis event.

Run hourly via dag_alpha_signals. Pro/Premium tier feature.

Usage:
  PYTHONPATH=backend .venv/bin/python backend/forecast-service/scripts/run_alpha_signals.py
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

_script_dir = Path(__file__).resolve().parent
for _p in [_script_dir.parent.parent, _script_dir.parent]:
    if (_p / "shared").is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
_svc_dir = _script_dir.parent
if str(_svc_dir) not in sys.path:
    sys.path.insert(0, str(_svc_dir))

import structlog
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from shared.database import async_session_factory
from shared.logging import setup_logging
from shared.models.forecast import AlphaSignal
from shared.models.market import Instrument
from shared.redis_client import redis_client

from services.ensemble import run_ensemble
from services.model_loader import artifacts

setup_logging()
logger = structlog.get_logger()

# Signals expire 2 hours after creation (hourly DAG writes fresh ones)
SIGNAL_TTL_HOURS = 2


async def _store_signal(session, inst_id, sector: str | None, forecast_date, result: dict) -> None:
    """Upsert alpha_signal row by (ticker, forecast_date).

    is_latest=TRUE is guaranteed for this row by the unique index on (ticker, forecast_date)
    + our end-of-run cleanup that resets is_latest=FALSE for older forecast_dates.
    Single-statement upsert — no race with concurrent runners.
    """
    ticker = result["ticker"]
    q = result["forecast"]["1d"] or {}

    stmt = pg_insert(AlphaSignal).values(
        instrument_id=inst_id,
        ticker=ticker,
        sector=sector,
        signal=result["signal"],
        confidence=result["confidence"],
        confident_long=bool(result.get("confident_long", False)),
        model_consensus=result["model_consensus"],
        disagreement_score=float(result["disagreement_score"]),
        current_close=float(result["current_close"]),
        median_1d=float(q.get("median") or result["current_close"]),
        lower_80_1d=float(q.get("lower_80") or result["current_close"]),
        upper_80_1d=float(q.get("upper_80") or result["current_close"]),
        predicted_return_1d=result.get("predicted_return_1d"),
        predicted_return_1w=result.get("predicted_return_1w"),
        predicted_return_1m=result.get("predicted_return_1m"),
        ensemble_weights=result.get("ensemble_weights") or [],
        forecast_date=forecast_date,
        is_latest=True,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=SIGNAL_TTL_HOURS),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["ticker", "forecast_date"],
        set_={
            "sector": stmt.excluded.sector,
            "signal": stmt.excluded.signal,
            "confidence": stmt.excluded.confidence,
            "confident_long": stmt.excluded.confident_long,
            "model_consensus": stmt.excluded.model_consensus,
            "disagreement_score": stmt.excluded.disagreement_score,
            "current_close": stmt.excluded.current_close,
            "median_1d": stmt.excluded.median_1d,
            "lower_80_1d": stmt.excluded.lower_80_1d,
            "upper_80_1d": stmt.excluded.upper_80_1d,
            "predicted_return_1d": stmt.excluded.predicted_return_1d,
            "predicted_return_1w": stmt.excluded.predicted_return_1w,
            "predicted_return_1m": stmt.excluded.predicted_return_1m,
            "ensemble_weights": stmt.excluded.ensemble_weights,
            "is_latest": True,
            "expires_at": stmt.excluded.expires_at,
            "updated_at": func.now(),
        },
    )
    await session.execute(stmt)


# Redis status key — Airflow/admin poll this to detect completion
STATUS_KEY = "alpha_signals:status"
STATUS_TTL_SECONDS = 24 * 3600


async def _publish_status(phase: str, **payload) -> None:
    """Publish batch progress to Redis. Never breaks the batch on Redis hiccups.

    A 100-minute ensemble run over 346 tickers is too expensive to abort over
    a transient Redis blip; status reporting is advisory, not critical-path.
    """
    try:
        await redis_client.set(
            STATUS_KEY,
            json.dumps({"phase": phase, "ts": datetime.now(timezone.utc).isoformat(), **payload}),
            ex=STATUS_TTL_SECONDS,
        )
    except Exception as exc:  # noqa: BLE001 — any Redis/network error is non-fatal
        await logger.awarning("alpha_status_publish_failed", phase=phase, error=str(exc))


async def main(only_tickers: list[str] | None = None) -> None:
    """Run Alpha Signals ensemble inference.

    :param only_tickers: if given, process only these tickers (useful for
        targeted re-runs of a specific ticker that was missed by the
        previous batch — e.g. after cleanup of corrupted price data).
        Defaults to the full 346-ticker universe.
    """
    await asyncio.to_thread(artifacts.ensure_loaded)
    await asyncio.to_thread(artifacts.ensure_ensemble_loaded)

    if only_tickers:
        only_set = {t.upper() for t in only_tickers}
        tickers = sorted(only_set & artifacts.valid_tickers)
    else:
        tickers = sorted(artifacts.valid_tickers)
    sectors_map = {
        t.upper(): s for t, s in (artifacts.config.get("sectors") or {}).items()
    }

    await _publish_status("running", total=len(tickers), done=0, failed=0, confident=0)
    await logger.ainfo("alpha_signals_start", total=len(tickers))

    today = datetime.now(timezone.utc).date()
    success = 0
    failed = 0
    confident_count = 0

    async with async_session_factory() as session:
        rows = (await session.execute(
            select(Instrument.ticker, Instrument.id)
            .where(Instrument.ticker.in_(tickers))
        )).all()
        inst_map = {t: i for t, i in rows}

    missing = [t for t in tickers if t not in inst_map]
    if missing:
        await logger.awarning("alpha_missing_instruments", count=len(missing), first_5=missing[:5])

    # ep2-heavy weights (ep2, ep4, ep5) — maximise Consensus WR for Alpha
    # Signals. Back-test: Sharpe 8.04, WR 64.3%, N=28 (vs ENS equal 8.15/63%/27,
    # vs ep5-heavy 2.01/54.3%/35). ConfLong WR is the metric users care about
    # on this surface (high-conviction trades), so we optimise for that
    # instead of raw Sharpe or ranking quality. See docs/MODEL.md §6.
    ALPHA_WEIGHTS = [0.5, 0.3, 0.2]

    for ticker in tickers:
        if ticker not in inst_map:
            continue
        try:
            result = await run_ensemble(ticker, artifacts, weights=ALPHA_WEIGHTS)
            if "error" in result:
                await logger.aerror("alpha_inference_error", ticker=ticker, error=result["error"])
                failed += 1
                continue

            async with async_session_factory() as session:
                await _store_signal(
                    session, inst_map[ticker], sectors_map.get(ticker), today, result,
                )
                await session.commit()

            if result.get("confident_long"):
                confident_count += 1
            success += 1

            if success % 25 == 0:
                await _publish_status(
                    "running",
                    total=len(tickers), done=success, failed=failed, confident=confident_count,
                )
                await logger.ainfo(
                    "alpha_progress", done=success, failed=failed, confident=confident_count,
                )
        except Exception as exc:
            await logger.aexception("alpha_exception", ticker=ticker, error=str(exc))
            failed += 1

    # Cleanup: mark older forecast_dates as not-latest (single atomic UPDATE).
    # Avoids race condition: unique(ticker, forecast_date) + this cleanup replaces
    # the previous per-row "mark stale" pattern that had two statements per ticker.
    async with async_session_factory() as session:
        await session.execute(
            update(AlphaSignal)
            .where(AlphaSignal.is_latest.is_(True), AlphaSignal.forecast_date < today)
            .values(is_latest=False, updated_at=func.now())
        )
        await session.commit()

    await redis_client.publish("alpha_signals.updated", json.dumps({
        "success": success, "failed": failed, "confident": confident_count, "total": len(tickers),
    }))
    await _publish_status(
        "done", total=len(tickers), done=success, failed=failed, confident=confident_count,
    )

    try:
        await redis_client.aclose()
    except Exception:
        pass

    await logger.ainfo(
        "alpha_signals_complete",
        success=success, failed=failed, confident=confident_count, total=len(tickers),
    )


if __name__ == "__main__":
    # Optional CLI arg: comma-separated tickers to limit the run
    # (e.g. `python run_alpha_signals.py GS` to process only GS).
    import sys
    only = sys.argv[1].split(",") if len(sys.argv) > 1 else None
    asyncio.run(main(only_tickers=only))
