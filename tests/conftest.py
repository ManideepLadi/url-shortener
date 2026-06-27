import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.dependencies import _cache, _repository
from app.main import app

# ---------------------------------------------------------------------------
# PostgreSQL + Redis test fixtures (disabled — uncomment when ready)
# ---------------------------------------------------------------------------
# import os
# from redis.asyncio import Redis
# from sqlalchemy import text
# from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
#
# from app.db.session import get_db_session, get_redis_client
# from app.models.url import Base
#
# TEST_DATABASE_URL = os.getenv(
#     "TEST_DATABASE_URL",
#     "postgresql+asyncpg://postgres:postgres@localhost:5432/urlshortener_test",
# )
# TEST_REDIS_URL = os.getenv("TEST_REDIS_URL", "redis://localhost:6379/1")


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: marks integration tests against the running app",
    )


@pytest_asyncio.fixture
async def client():
    _repository._store.clear()
    _repository._next_id = 1
    _cache._redirects.clear()
    _cache._hits.clear()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
