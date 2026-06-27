import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from app.db.session import engine
from app.dependencies import _cache
from app.main import app
from app.models.url import UrlMapping


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: marks integration tests against the running app",
    )


@pytest_asyncio.fixture
async def client():
    async with engine.begin() as conn:
        await conn.execute(delete(UrlMapping))

    _cache._redirects.clear()
    _cache._hits.clear()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
