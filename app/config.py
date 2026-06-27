from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# libpq/psycopg2 query params that asyncpg does not accept as connect() kwargs
_UNSUPPORTED_QUERY_PARAMS = frozenset(
    {
        "sslmode",
        "sslrootcert",
        "sslcert",
        "sslkey",
        "sslcrl",
        "sslcompression",
        "requiressl",
        "channel_binding",
    }
)


def normalize_database_url(url: str) -> str:
    """
    Prepare a DATABASE_URL for SQLAlchemy + asyncpg.

    - Converts postgresql:// to postgresql+asyncpg://
    - Strips sslmode and other libpq-only query params (SSL is handled via connect_args)
    """
    normalized = url.strip()
    if "://" not in normalized:
        return normalized

    if normalized.startswith("postgres://"):
        normalized = "postgresql://" + normalized.removeprefix("postgres://")

    parsed = urlparse(normalized)
    scheme = parsed.scheme

    if scheme in {"postgresql", "postgres"}:
        scheme = "postgresql+asyncpg"
    elif scheme.startswith("postgresql+") and scheme != "postgresql+asyncpg":
        scheme = "postgresql+asyncpg"
    elif scheme != "postgresql+asyncpg":
        return normalized

    query_params = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in _UNSUPPORTED_QUERY_PARAMS
    ]

    return urlunparse(
        (
            scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            urlencode(query_params),
            parsed.fragment,
        )
    )


def normalize_ca_cert(value: str | None) -> str | None:
    """
    Normalize a PEM CA certificate from env vars or App Platform injection.

    Handles empty values, surrounding quotes, and literal \\n sequences common
    when PEM is stored as a single-line environment variable.
    """
    if value is None:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    if normalized.startswith("${") and normalized.endswith("}"):
        # Unexpanded App Platform placeholder, e.g. ${db-dev.CA_CERT}
        return None

    normalized = normalized.strip('"').strip("'")
    if "\\n" in normalized:
        normalized = normalized.replace("\\n", "\n")

    return normalized


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    app_name: str = "url-shortener"
    app_env: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://db-dev:password@localhost:5432/db-dev"
    database_ssl_required: bool = True
    database_ssl_verify_ca: bool = True
    database_ca_cert: str | None = None

    base_url: str = "http://localhost:8000"
    redirect_cache_ttl_seconds: int = 3600
    auto_alias_strategy: str = "random"
    auto_alias_length: int = 8
    auto_alias_max_retries: int = 5

    db_init_max_retries: int = 10
    db_init_retry_delay_seconds: float = 2.0

    metrics_enabled: bool = True

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        return normalize_database_url(value)

    @field_validator("database_ca_cert")
    @classmethod
    def validate_database_ca_cert(cls, value: str | None) -> str | None:
        return normalize_ca_cert(value)

    @field_validator("auto_alias_strategy")
    @classmethod
    def validate_auto_alias_strategy(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"random", "base62"}:
            raise ValueError("AUTO_ALIAS_STRATEGY must be 'random' or 'base62'")
        return normalized


settings = Settings()


def masked_database_url(database_url: str) -> str:
    """Return a log-safe database URL with credentials redacted."""
    if "@" not in database_url:
        return database_url
    prefix, location = database_url.rsplit("@", maxsplit=1)
    scheme = prefix.split("://", maxsplit=1)[0]
    return f"{scheme}://***:***@{location}"
