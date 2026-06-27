from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.in_memory_cache import InMemoryUrlCache
from app.db.session import get_db_session
from app.repositories.url_repository import UrlRepository
from app.services.url_service import UrlService
from app.strategies import get_alias_strategy

_cache = InMemoryUrlCache()


async def get_url_cache() -> InMemoryUrlCache:
    return _cache


async def get_url_repository(
    session: AsyncSession = Depends(get_db_session),
) -> UrlRepository:
    return UrlRepository(session)


async def get_url_service(
    repository: UrlRepository = Depends(get_url_repository),
    cache: InMemoryUrlCache = Depends(get_url_cache),
) -> UrlService:
    return UrlService(
        repository=repository,
        cache=cache,
        alias_strategy=get_alias_strategy(),
    )
