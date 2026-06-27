import pytest

from app.config import Settings, normalize_database_url


class TestNormalizeDatabaseUrl:
    def test_converts_postgresql_scheme(self):
        url = "postgresql://user:pass@host:25060/db-dev"
        assert normalize_database_url(url) == "postgresql+asyncpg://user:pass@host:25060/db-dev"

    def test_converts_postgres_scheme(self):
        url = "postgres://user:pass@host:25060/db-dev"
        assert normalize_database_url(url) == "postgresql+asyncpg://user:pass@host:25060/db-dev"

    def test_converts_psycopg2_scheme(self):
        url = "postgresql+psycopg2://user:pass@host:25060/db-dev"
        assert normalize_database_url(url) == "postgresql+asyncpg://user:pass@host:25060/db-dev"

    def test_strips_sslmode_query_param(self):
        url = (
            "postgresql://user:pass@host:25060/db-dev?sslmode=require"
        )
        assert normalize_database_url(url) == (
            "postgresql+asyncpg://user:pass@host:25060/db-dev"
        )

    def test_strips_sslmode_from_asyncpg_url(self):
        url = (
            "postgresql+asyncpg://user:pass@host:25060/db-dev?sslmode=require"
        )
        assert normalize_database_url(url) == (
            "postgresql+asyncpg://user:pass@host:25060/db-dev"
        )

    def test_leaves_asyncpg_url_without_query_unchanged(self):
        url = "postgresql+asyncpg://user:pass@host:25060/db-dev"
        assert normalize_database_url(url) == url

    def test_settings_applies_normalization(self):
        settings = Settings(
            database_url="postgresql://user:pass@host:25060/db-dev?sslmode=require",
        )
        assert settings.database_url == "postgresql+asyncpg://user:pass@host:25060/db-dev"
