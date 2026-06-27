from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Redis disabled for now
    # redis_url: str = "redis://localhost:6379/0"

    base_url: str = "http://localhost:8000"
    redirect_cache_ttl_seconds: int = 3600
    auto_alias_length: int = 8
    auto_alias_max_retries: int = 5

    db_init_max_retries: int = 10
    db_init_retry_delay_seconds: float = 2.0


settings = Settings()


def masked_database_url(database_url: str) -> str:
    """Return a log-safe database URL with credentials redacted."""
    if "@" not in database_url:
        return database_url
    prefix, location = database_url.rsplit("@", maxsplit=1)
    scheme = prefix.split("://", maxsplit=1)[0]
    return f"{scheme}://***:***@{location}"
