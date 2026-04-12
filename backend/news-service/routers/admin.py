"""Admin endpoints for triggering news fetch (Airflow DAGs)."""

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


@router.post("/admin/fetch-news", status_code=202)
async def fetch_news(
    bg: BackgroundTasks,
    _key: str = Depends(require_internal_key),
):
    """Trigger RSS news fetch + FinBERT sentiment (background)."""
    from scripts.fetch_news import main
    bg.add_task(_run_script, "fetch_news", main)
    return {"status": "accepted", "task": "fetch_news"}
