"""Shared atomic rate limiter using Redis Lua script."""

from shared.redis_client import redis_client

_RATE_LIMIT_LUA = """
local key = KEYS[1]
local window = tonumber(ARGV[1])
local count = redis.call('INCR', key)
if count == 1 then
    redis.call('EXPIRE', key, window)
end
local ttl = redis.call('TTL', key)
return {count, ttl}
"""

_script_sha: str | None = None


async def check_rate_limit(key: str, limit: int, window_seconds: int = 60) -> tuple[int, int, int]:
    """Atomic INCR+EXPIRE via Lua. Returns (count, remaining, ttl)."""
    global _script_sha
    if _script_sha is None:
        _script_sha = await redis_client.script_load(_RATE_LIMIT_LUA)
    try:
        count, ttl = await redis_client.evalsha(_script_sha, 1, key, window_seconds)
    except Exception:
        # Script evicted from Redis cache — reload
        _script_sha = None
        _script_sha = await redis_client.script_load(_RATE_LIMIT_LUA)
        count, ttl = await redis_client.evalsha(_script_sha, 1, key, window_seconds)

    remaining = max(0, limit - count)
    return count, remaining, ttl
