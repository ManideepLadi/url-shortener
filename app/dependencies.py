import logging

from app.db.in_memory_cache import InMemoryUrlCache
from app.repositories.in_memory_url_repository import InMemoryUrlRepository
from app.services.url_service import UrlService

# ---------------------------------------------------------------------------
# PostgreSQL + Redis wiring (disabled for local dev — uncomment when ready)
# ---------------------------------------------------------------------------
# from fastapi import Depends
# from redis.asyncio import Redis
# from sqlalchemy.ext.asyncio import AsyncSession
#
# from app.db.redis_client import UrlCache
# from app.db.session import get_db_session, get_redis_client
# from app.repositories.url_repository import UrlRepository
#
#
# async def get_url_cache(
#     redis: Redis = Depends(get_redis_client),
# ) -> UrlCache:
#     return UrlCache(redis)
#
#
# async def get_url_repository(
#     session: AsyncSession = Depends(get_db_session),
# ) -> UrlRepository:
#     return UrlRepository(session)

logger = logging.getLogger(__name__)

_repository = InMemoryUrlRepository()
_cache = InMemoryUrlCache()


async def get_url_repository() -> InMemoryUrlRepository:
    return _repository


async def get_url_cache() -> InMemoryUrlCache:
    return _cache


async def get_url_service() -> UrlService:
    return UrlService(repository=_repository, cache=_cache)
