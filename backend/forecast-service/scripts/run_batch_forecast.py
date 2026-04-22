"""
Batch forecast: run 3-model ensemble inference with ep5-heavy weights for
all 346 tickers, store results, publish Redis event.

Weighting rationale: ep5-heavy [0.2, 0.3, 0.5] (for ep2, ep4, ep5 in that
order) produces the best back-test Top-20 Sharpe (1.49 vs 1.45 ENS equal
vs 1.36 ep5 alone) — ranking is the value prop for Top Picks, so we
optimise for that. Alpha Signals use a different ensemble (ep2-heavy);
see run_alpha_signals.py.

Usage:
  PYTHONPATH=backend .venv/bin/python backend/forecast-service/scripts/run_batch_forecast.py
"""

import asyncio
import json
import sys
from pathlib import Path

_script_dir = Path(__file__).resolve().parent
for _p in [_script_dir.parent.parent, _script_dir.parent]:
    if (_p / "shared").is_dir() and str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
_svc_dir = _script_dir.parent
if str(_svc_dir) not in sys.path:
    sys.path.insert(0, str(_svc_dir))

import structlog

from shared.database import async_session_factory
from shared.logging import setup_logging
from shared.redis_client import redis_client

from services.ensemble import run_ensemble
from services.forecast_service import store_forecast
from services.model_loader import artifacts

setup_logging()
logger = structlog.get_logger()

# ep5-heavy weights: applied to artifacts.ensemble_models in [ep2, ep4, ep5] order.
# Back-test metrics (post-Oct-2025, 23 days, 9,200 windows):
#   Top-20 Sharpe 1.49 · Return +19.74% · vs S&P 500 +12.01pp alpha
#   MAPE 1d 4.75% · MAPE 22d 12.63%
# See docs/MODEL.md §6 for ensemble selection rationale.
EP5_HEAVY_WEIGHTS = [0.2, 0.3, 0.5]


async def main() -> None:
    await logger.ainfo(
        "batch_forecast_start",
        total_tickers=len(artifacts.valid_tickers),
        weights=EP5_HEAVY_WEIGHTS,
    )

    # Load primary + all 3 ensemble checkpoints. Ensemble reuses ep5 from
    # primary, so total additional RAM is 2× checkpoint (ep2 + ep4).
    await asyncio.to_thread(artifacts.ensure_loaded)
    await asyncio.to_thread(artifacts.ensure_ensemble_loaded)

    success = 0
    failed = 0

    for ticker in sorted(artifacts.valid_tickers):
        try:
            result = await run_ensemble(
                ticker, artifacts,
                weights=EP5_HEAVY_WEIGHTS,
                extract_factors=True,  # forecast.forecast_factors FK needs this
            )
            if "error" in result:
                await logger.aerror("forecast_error", ticker=ticker, error=result["error"])
                failed += 1
                continue

            async with async_session_factory() as session:
                await store_forecast(session, result)
                await session.commit()

            success += 1
            await logger.ainfo(
                "forecast_done", ticker=ticker,
                signal=result["signal"], confidence=result["confidence"],
                return_1m=result.get("predicted_return_1m"),
            )
        except Exception as exc:
            await logger.aerror("forecast_exception", ticker=ticker, error=str(exc))
            failed += 1

    # Publish completion event
    await redis_client.publish("forecast.updated", json.dumps({
        "success": success, "failed": failed, "total": len(artifacts.valid_tickers),
    }))

    await redis_client.aclose()
    await logger.ainfo("batch_forecast_complete", success=success, failed=failed)


if __name__ == "__main__":
    asyncio.run(main())
