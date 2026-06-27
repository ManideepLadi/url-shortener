import pytest

from app.config import Settings, normalize_ca_cert, normalize_database_url


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


class TestNormalizeCaCert:
    def test_none_and_empty(self):
        assert normalize_ca_cert(None) is None
        assert normalize_ca_cert("") is None
        assert normalize_ca_cert("   ") is None

    def test_unexpanded_app_platform_placeholder(self):
        assert normalize_ca_cert("${db-dev.CA_CERT}") is None

    def test_literal_newlines(self):
        pem = "-----BEGIN CERTIFICATE-----\\nabc\\n-----END CERTIFICATE-----"
        assert normalize_ca_cert(pem) == "-----BEGIN CERTIFICATE-----\nabc\n-----END CERTIFICATE-----"

    def test_strips_surrounding_quotes(self):
        pem = '"-----BEGIN CERTIFICATE-----\nabc\n-----END CERTIFICATE-----"'
        assert normalize_ca_cert(pem).startswith("-----BEGIN CERTIFICATE-----")

    def test_settings_normalizes_ca_cert(self):
        settings = Settings(
            database_ca_cert="-----BEGIN CERTIFICATE-----\\nabc\\n-----END CERTIFICATE-----",
        )
        assert "\nabc\n" in settings.database_ca_cert

    def test_settings_validates_alias_strategy(self):
        settings = Settings(auto_alias_strategy="base62")
        assert settings.auto_alias_strategy == "base62"

        with pytest.raises(ValueError, match="AUTO_ALIAS_STRATEGY"):
            Settings(auto_alias_strategy="invalid")
