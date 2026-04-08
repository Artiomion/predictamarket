"""Shared health check — verifies DB and Redis connectivity."""

from sqlalchemy import text

from shared.database import async_session_factory
from shared.redis_client import redis_client


async def check_health() -> dict:
    """Returns {"status": "ok"|"degraded", "db": "ok"|"error", "redis": "ok"|"error"}."""
    db_ok = True
    redis_ok = True

    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_ok = False

    try:
        await redis_client.ping()
    except Exception:
        redis_ok = False

    status = "ok" if (db_ok and redis_ok) else "degraded"
    return {"status": status, "db": "ok" if db_ok else "error", "redis": "ok" if redis_ok else "error"}
