"""Admin endpoints for triggering data updates (Airflow DAGs)."""

import asyncio

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


@router.post("/admin/update-prices", status_code=202)
async def update_prices(
    bg: BackgroundTasks,
    _key: str = Depends(require_internal_key),
):
    """Trigger price update for all tickers (background)."""
    from scripts.update_prices import main
    bg.add_task(_run_script, "update_prices", main)
    return {"status": "accepted", "task": "update_prices"}


@router.post("/admin/update-macro")
async def update_macro(
    _key: str = Depends(require_internal_key),
):
    """Trigger macro indicators update (fast, synchronous)."""
    from scripts.update_macro import main
    await main()
    return {"status": "completed", "task": "update_macro"}


@router.post("/admin/update-financials", status_code=202)
async def update_financials(
    bg: BackgroundTasks,
    _key: str = Depends(require_internal_key),
):
    """Trigger financial statements update (background)."""
    from scripts.update_financials import main
    bg.add_task(_run_script, "update_financials", main)
    return {"status": "accepted", "task": "update_financials"}


@router.post("/admin/update-earnings", status_code=202)
async def update_earnings(
    bg: BackgroundTasks,
    _key: str = Depends(require_internal_key),
):
    """Trigger earnings data update (background)."""
    from scripts.update_earnings import main
    bg.add_task(_run_script, "update_earnings", main)
    return {"status": "accepted", "task": "update_earnings"}


@router.post("/admin/update-insider", status_code=202)
async def update_insider(
    bg: BackgroundTasks,
    _key: str = Depends(require_internal_key),
):
    """Trigger insider transactions update (background)."""
    from scripts.update_insider import main
    bg.add_task(_run_script, "update_insider", main)
    return {"status": "accepted", "task": "update_insider"}
