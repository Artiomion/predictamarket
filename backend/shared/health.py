"""Shared health check — verifies DB and Redis connectivity."""

import structlog
from sqlalchemy import text

from shared.database import async_session_factory
from shared.redis_client import redis_client

logger = structlog.get_logger()


async def check_health() -> dict:
    """Returns {"status": "ok"|"degraded", "db": "ok"|"error", "redis": "ok"|"error"}."""
    db_ok = True
    redis_ok = True

    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception as exc:
        db_ok = False
        await logger.awarning("health_db_error", error=str(exc))

    try:
        await redis_client.ping()
    except Exception as exc:
        redis_ok = False
        await logger.awarning("health_redis_error", error=str(exc))

    status = "ok" if (db_ok and redis_ok) else "degraded"
    return {"status": status, "db": "ok" if db_ok else "error", "redis": "ok" if redis_ok else "error"}
