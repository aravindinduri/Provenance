"""
Redis connection pool and health check.
"""

import redis.asyncio as aioredis

from app.config import get_settings

_pool: aioredis.ConnectionPool | None = None


def get_redis_pool() -> aioredis.ConnectionPool:
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = aioredis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=20,
            decode_responses=True,
        )
    return _pool


def get_redis() -> aioredis.Redis:
    return aioredis.Redis(connection_pool=get_redis_pool())


async def check_redis_connection() -> None:
    """Raise if Redis is unreachable (used by /health/ready)."""
    client = get_redis()
    await client.ping()
