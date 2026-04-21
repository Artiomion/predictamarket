"""Admin endpoints for triggering batch forecast (Airflow DAGs)."""

import json

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends

from shared.internal_auth import require_internal_key
from shared.redis_client import redis_client

logger = structlog.get_logger()
router = APIRouter()


async def _run_script(name: str, coro_fn):
    """Run an async script main() and log result."""
    logger.info("admin_task_started", script=name)
    try:
        await coro_fn()
        logger.info("admin_task_completed", script=name)
    except Exception:
        logger.exception("admin_task_failed", script=name)


@router.post("/admin/run-batch", status_code=202)
async def run_batch_forecast(
    bg: BackgroundTasks,
    _key: str = Depends(require_internal_key),
):
    """Trigger batch TFT forecast for all tickers (background)."""
    from scripts.run_batch_forecast import main
    bg.add_task(_run_script, "run_batch_forecast", main)
    return {"status": "accepted", "task": "run_batch_forecast"}


@router.post("/admin/evaluate")
async def evaluate_forecasts_endpoint(
    _key: str = Depends(require_internal_key),
) -> dict:
    """Evaluate past forecasts against actual prices (synchronous, fast)."""
    from services.evaluation import evaluate_forecasts
    result = await evaluate_forecasts(days_back=30)
    return {"status": "completed", **result}


@router.post("/admin/run-alpha-signals", status_code=202)
async def run_alpha_signals(
    bg: BackgroundTasks,
    _key: str = Depends(require_internal_key),
):
    """Trigger 3-model ensemble inference for all tickers (background).

    Progress is published to Redis `alpha_signals:status`. Poll via
    `GET /admin/alpha-signals-status`.
    """
    from scripts.run_alpha_signals import main
    bg.add_task(_run_script, "run_alpha_signals", main)
    return {"status": "accepted", "task": "run_alpha_signals"}


@router.get("/admin/alpha-signals-status")
async def alpha_signals_status(
    _key: str = Depends(require_internal_key),
) -> dict:
    """Return current batch status: {phase: running|done|idle, done, failed, ...}.

    Used by Airflow DAG to poll until phase=done. Returns phase=idle if no
    recent run (key expired or never set).
    """
    raw = await redis_client.get("alpha_signals:status")
    if not raw:
        return {"phase": "idle"}
    try:
        return json.loads(raw if isinstance(raw, str) else raw.decode())
    except (json.JSONDecodeError, AttributeError):
        return {"phase": "idle"}
