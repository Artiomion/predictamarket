"""Admin endpoints for triggering batch forecast (Airflow DAGs)."""

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends

from shared.internal_auth import require_internal_key

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
