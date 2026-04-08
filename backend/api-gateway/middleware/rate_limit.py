import sys
import time
from collections import defaultdict
from pathlib import Path

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from shared.rate_limit import check_rate_limit  # noqa: E402
from shared.tier_limits import GATEWAY_RATE_LIMITS  # noqa: E402

logger = structlog.get_logger()

WINDOW_SECONDS = 60

# In-memory fallback when Redis is down (halved limits for safety)
_local_counts: dict[str, list[float]] = defaultdict(list)


def _local_rate_check(key: str, limit: int) -> tuple[int, int]:
    """Simple in-memory sliding window fallback. Returns (count, remaining)."""
    now = time.monotonic()
    window = _local_counts[key]
    # Evict old entries
    _local_counts[key] = [t for t in window if now - t < WINDOW_SECONDS]
    _local_counts[key].append(now)
    count = len(_local_counts[key])
    return count, max(0, limit - count)


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path == "/health":
            return await call_next(request)

        user_id = getattr(request.state, "user_id", None)
        tier = getattr(request.state, "user_tier", None) or "free"

        if user_id:
            key = f"rl:{user_id}"
        else:
            client_ip = request.client.host if request.client else "unknown"
            key = f"rl:ip:{client_ip}"

        limit = GATEWAY_RATE_LIMITS.get(tier, GATEWAY_RATE_LIMITS["free"])

        try:
            count, remaining, ttl = await check_rate_limit(key, limit, WINDOW_SECONDS)
        except Exception as exc:
            # Redis down — use in-memory fallback with halved limits
            await logger.aerror("rate_limit_redis_fallback", error=str(exc))
            fallback_limit = max(1, limit // 2)
            count, remaining = _local_rate_check(key, fallback_limit)
            ttl = WINDOW_SECONDS
            limit = fallback_limit

        if count > limit:
            await logger.awarning(
                "rate_limit_exceeded", key=key, tier=tier, count=count, limit=limit,
            )
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Upgrade your plan for higher limits."},
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(ttl),
                    "Retry-After": str(ttl),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(ttl)
        return response
