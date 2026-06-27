import asyncio
import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import text

from app.config import masked_database_url, normalize_database_url, settings
from app.db.ssl_context import create_database_ssl_context

logger = logging.getLogger(__name__)

DATABASE_URL = normalize_database_url(settings.database_url)

_engine: AsyncEngine | None = None
_SessionLocal: async_sessionmaker[AsyncSession] | None = None


def _build_connect_args() -> dict:
    if not settings.database_ssl_required:
        return {}
    return {"ssl": create_database_ssl_context()}


def get_engine() -> AsyncEngine:
    global _engine, _SessionLocal
    if _engine is None:
        _engine = create_async_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            echo=settings.app_env == "development",
            connect_args=_build_connect_args(),
        )
        _SessionLocal = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_db() -> None:
    from app.models.url import Base

    engine = get_engine()
    last_error: Exception | None = None
    max_retries = settings.db_init_max_retries
    retry_delay = settings.db_init_retry_delay_seconds

    for attempt in range(1, max_retries + 1):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
                await conn.execute(
                    text(
                        "ALTER TABLE url_mappings "
                        "ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ"
                    )
                )
            logger.info("Database schema initialized")
            return
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Database connection attempt %s/%s failed: %s",
                attempt,
                max_retries,
                exc,
            )
            if attempt < max_retries:
                await asyncio.sleep(retry_delay)

    logger.error(
        "Could not connect to PostgreSQL at %s after %s attempts. "
        "ssl_required=%s ssl_verify_ca=%s ca_cert_configured=%s",
        masked_database_url(DATABASE_URL),
        max_retries,
        settings.database_ssl_required,
        settings.database_ssl_verify_ca,
        bool(settings.database_ca_cert),
    )
    raise RuntimeError(
        "PostgreSQL is unavailable. Check DATABASE_URL, DATABASE_CA_CERT, and network access."
    ) from last_error


async def close_db() -> None:
    global _engine, _SessionLocal
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _SessionLocal = None
        logger.info("Database connections closed")
