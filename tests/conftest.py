from typing import Any, AsyncGenerator

import pytest
from fakeredis import FakeServer
from fakeredis.aioredis import FakeConnection
from fastapi import FastAPI
from httpx import AsyncClient
from redis.asyncio import ConnectionPool
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.application import get_app
from app.cache.factory import RedisFactory
from app.db.dependencies import get_db_session
from app.db.factory import DatabaseFactory
from app.db.meta import meta
from app.db.models import load_all_models


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    """Return asyncio backend for pytest."""
    return "asyncio"


@pytest.fixture(scope="session")
async def _engine() -> AsyncGenerator[AsyncEngine, None]:
    load_all_models()

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(meta.create_all)

    yield engine
    await engine.dispose()


@pytest.fixture
async def dbsession(_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an async SQLAlchemy test session."""
    session_maker = async_sessionmaker(_engine, expire_on_commit=False)
    session = session_maker()
    try:
        yield session
    finally:
        await session.close()


@pytest.fixture
async def fake_redis_pool() -> AsyncGenerator[ConnectionPool, None]:
    """Provide a fake Redis connection pool for tests."""
    server = FakeServer()
    server.connected = True
    pool = ConnectionPool(connection_class=FakeConnection, server=server)
    yield pool
    await pool.disconnect()


class FakeDatabaseFactory(DatabaseFactory):
    """Test database factory that skips real DB engine/echo arguments."""

    def __init__(self, engine: AsyncEngine) -> None:
        # skip parent __init__
        self.engine = engine
        self.session_factory = async_sessionmaker(
            self.engine,
            expire_on_commit=False,
        )

    async def close(self) -> None:
        """No-op."""


class FakeRedisFactory(RedisFactory):
    """Test Redis factory skipping real pool creation."""

    def __init__(self, pool: ConnectionPool) -> None:
        # DO NOT call super().__init__()
        self.pool = pool

    async def close(self) -> None:
        """Override close with a no-op for tests."""


@pytest.fixture
def fastapi_app(
    dbsession: AsyncSession,
    _engine: AsyncEngine,
    fake_redis_pool: ConnectionPool,
) -> FastAPI:
    """Create a FastAPI app with test-specific overrides."""
    app = get_app()
    app.state.db_factory = FakeDatabaseFactory(_engine)
    app.dependency_overrides[get_db_session] = lambda: dbsession
    app.state.redis_factory = FakeRedisFactory(fake_redis_pool)
    return app


@pytest.fixture
async def client(
    fastapi_app: FastAPI,
    anyio_backend: Any,
) -> AsyncGenerator[AsyncClient, None]:
    """Return an HTTP client bound to the test FastAPI app."""
    async with AsyncClient(app=fastapi_app, base_url="http://test") as ac:
        yield ac
