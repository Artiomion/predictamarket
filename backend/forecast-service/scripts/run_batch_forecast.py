"""
Batch forecast: run TFT inference for all 94 tickers, store results, publish Redis event.

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

from services.inference import run_inference
from services.forecast_service import store_forecast
from services.model_loader import artifacts

setup_logging()
logger = structlog.get_logger()


async def main() -> None:
    await logger.ainfo("batch_forecast_start", total_tickers=len(artifacts.valid_tickers))

    # Load model (blocking, first time)
    await asyncio.to_thread(artifacts.ensure_loaded)

    success = 0
    failed = 0

    for ticker in sorted(artifacts.valid_tickers):
        try:
            result = await run_inference(ticker, artifacts)
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
