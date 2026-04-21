"""Shared atomic rate limiter using Redis Lua script.

The Lua script is check-then-increment: a request that would exceed the limit
does NOT increment the counter. This prevents the "sticky flood" pattern where
an aggressive retry loop inflates the counter indefinitely during the window,
even though each new attempt gets 429. Rejections are free; only successful
admissions cost a slot.
"""

import structlog

from shared.redis_client import redis_client

logger = structlog.get_logger()

# Atomic check-and-increment:
#   1. Peek current value
#   2. If already at/over limit → return current count + TTL, flag rejected=1,
#      do NOT increment (protects abuse retries from extending the damage).
#   3. Otherwise INCR, set EXPIRE on first entry, return new count + TTL, flag 0.
_RATE_LIMIT_LUA = """
local key = KEYS[1]
local window = tonumber(ARGV[1])
local limit = tonumber(ARGV[2])
local current = tonumber(redis.call('GET', key)) or 0
if current >= limit then
    local ttl = redis.call('TTL', key)
    return {current, ttl, 1}
end
local count = redis.call('INCR', key)
if count == 1 then
    redis.call('EXPIRE', key, window)
end
local ttl = redis.call('TTL', key)
return {count, ttl, 0}
"""

_script_sha: str | None = None


async def check_rate_limit(
    key: str, limit: int, window_seconds: int = 60
) -> tuple[int, int, int]:
    """Atomic check-then-INCR via Lua.

    Returns (count, remaining, ttl). When the limit is already exhausted the
    counter is NOT incremented — the caller still gets a truthful `count` so
    `count > limit` can be used to reject, but retries during the ban don't
    accumulate extra counts. `remaining` is clamped at 0.
    """
    global _script_sha
    if _script_sha is None:
        _script_sha = await redis_client.script_load(_RATE_LIMIT_LUA)
    try:
        count, ttl, _rejected = await redis_client.evalsha(
            _script_sha, 1, key, window_seconds, limit,
        )
    except Exception as exc:
        # Script evicted from Redis cache — reload
        logger.warning("rate_limit_lua_reload", error=str(exc))
        _script_sha = None
        _script_sha = await redis_client.script_load(_RATE_LIMIT_LUA)
        count, ttl, _rejected = await redis_client.evalsha(
            _script_sha, 1, key, window_seconds, limit,
        )

    remaining = max(0, limit - int(count))
    return int(count), remaining, int(ttl)
