# ---------------------------------------------------------------------------
# PostgreSQL + Redis session management (disabled for local dev)
# Uncomment this entire block when PostgreSQL and Redis are available.
# ---------------------------------------------------------------------------
#
# import asyncio
# import logging
# from collections.abc import AsyncGenerator
#
# from redis.asyncio import Redis
# from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
#
# from app.config import masked_database_url, settings
#
# logger = logging.getLogger(__name__)
#
# engine = create_async_engine(
#     settings.database_url,
#     pool_pre_ping=True,
#     echo=settings.app_env == "development",
# )
#
# SessionLocal = async_sessionmaker(
#     bind=engine,
#     class_=AsyncSession,
#     expire_on_commit=False,
#     autoflush=False,
#     autocommit=False,
# )
#
#
# async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
#     session = SessionLocal()
#     try:
#         yield session
#     except Exception:
#         await session.rollback()
#         raise
#     finally:
#         await session.close()
#
#
# async def get_redis_client() -> AsyncGenerator[Redis, None]:
#     client = Redis.from_url(
#         settings.redis_url,
#         decode_responses=True,
#     )
#     try:
#         yield client
#     finally:
#         await client.aclose()
#
#
# async def init_db() -> None:
#     from app.models.url import Base
#
#     last_error: Exception | None = None
#     max_retries = settings.db_init_max_retries
#     retry_delay = settings.db_init_retry_delay_seconds
#
#     for attempt in range(1, max_retries + 1):
#         try:
#             async with engine.begin() as conn:
#                 await conn.run_sync(Base.metadata.create_all)
#             logger.info("Database schema initialized")
#             return
#         except Exception as exc:
#             last_error = exc
#             logger.warning(
#                 "Database connection attempt %s/%s failed: %s",
#                 attempt,
#                 max_retries,
#                 exc,
#             )
#             if attempt < max_retries:
#                 await asyncio.sleep(retry_delay)
#
#     logger.error(
#         "Could not connect to PostgreSQL at %s after %s attempts. "
#         "Start dependencies with: docker compose up -d postgres redis",
#         masked_database_url(settings.database_url),
#         max_retries,
#     )
#     raise RuntimeError(
#         "PostgreSQL is unavailable. Start Postgres before running the API."
#     ) from last_error
#
#
# async def close_db() -> None:
#     await engine.dispose()
#     logger.info("Database connections closed")
