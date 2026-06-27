import pytest

from app.config import Settings


class TestDatabaseUrlNormalization:
    def test_converts_postgresql_scheme_to_asyncpg(self):
        settings = Settings(
            database_url="postgresql://user:pass@host:25060/db-dev",
        )
        assert settings.database_url.startswith("postgresql+asyncpg://")

    def test_converts_postgres_scheme_to_asyncpg(self):
        settings = Settings(
            database_url="postgres://user:pass@host:25060/db-dev",
        )
        assert settings.database_url.startswith("postgresql+asyncpg://")

    def test_leaves_asyncpg_url_unchanged(self):
        url = "postgresql+asyncpg://user:pass@host:25060/db-dev"
        settings = Settings(database_url=url)
        assert settings.database_url == url
