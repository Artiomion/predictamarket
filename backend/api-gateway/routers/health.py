from fastapi import APIRouter
from fastapi.responses import JSONResponse

from shared.redis_client import redis_client

router = APIRouter()


@router.get("/health")
async def health() -> JSONResponse:
    redis_ok = True
    try:
        await redis_client.ping()
    except Exception:
        redis_ok = False
    status = "ok" if redis_ok else "degraded"
    return JSONResponse(
        content={"status": status, "service": "api-gateway", "redis": "ok" if redis_ok else "error"},
        status_code=200 if redis_ok else 503,
    )
