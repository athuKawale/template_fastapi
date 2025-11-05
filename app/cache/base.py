"""Cache connection setup."""

from redis.asyncio import ConnectionPool, Redis

from app.settings import settings

pool = ConnectionPool.from_url(
    url=str(settings.redis_url),
    max_connections=10,
    timeout=5,
)


def get_redis_connection() -> Redis:
    """Get redis connection."""
    return Redis(connection_pool=pool)
