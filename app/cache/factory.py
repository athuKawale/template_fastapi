"""Redis factory."""

from redis.asyncio import ConnectionPool, Redis


class RedisFactory:
    """Redis factory."""

    def __init__(self, redis_url: str) -> None:
        self.pool = ConnectionPool.from_url(
            url=redis_url,
            max_connections=10,
            timeout=5,
        )

    def get_connection(self) -> Redis:
        """Get connection."""
        return Redis(connection_pool=self.pool)

    async def close(self) -> None:
        """Close connection."""
        await self.pool.disconnect()
