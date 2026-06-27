import logging

from app.config import settings
from app.db.redis_client import UrlCache
from app.models.url import UrlMapping
from app.repositories.url_repository import UrlRepository
from app.schemas.url import CreateUrlRequest, CreateUrlResponse, UrlMetadataResponse
from app.utils.alias import RESERVED_ALIASES, generate_random_alias
from app.utils.exceptions import (
    AliasAlreadyExistsError,
    AliasGenerationError,
    UrlMappingNotFoundError,
)

logger = logging.getLogger(__name__)


class UrlService:
    def __init__(self, repository: UrlRepository, cache: UrlCache) -> None:
        self._repository = repository
        self._cache = cache
        self._base_url = settings.base_url.rstrip("/")

    def _build_short_url(self, alias: str) -> str:
        return f"{self._base_url}/{alias}"

    def _to_metadata(self, mapping: UrlMapping, access_count: int) -> UrlMetadataResponse:
        return UrlMetadataResponse(
            alias=mapping.alias,
            long_url=mapping.long_url,
            short_url=self._build_short_url(mapping.alias),
            access_count=access_count,
            created_at=mapping.created_at,
        )

    async def create_short_url(self, request: CreateUrlRequest) -> CreateUrlResponse:
        long_url = str(request.long_url)

        if request.custom_alias:
            mapping = await self._repository.create(
                alias=request.custom_alias,
                long_url=long_url,
            )
            await self._cache.set_long_url(mapping.alias, mapping.long_url)
            logger.info("Created custom alias=%s", mapping.alias)
            return CreateUrlResponse(**self._to_metadata(mapping, mapping.access_count).model_dump())

        mapping = await self._create_with_generated_alias(long_url)
        await self._cache.set_long_url(mapping.alias, mapping.long_url)
        logger.info("Created auto alias=%s", mapping.alias)
        return CreateUrlResponse(**self._to_metadata(mapping, mapping.access_count).model_dump())

    async def _create_with_generated_alias(self, long_url: str) -> UrlMapping:
        last_error: AliasAlreadyExistsError | None = None

        for attempt in range(1, settings.auto_alias_max_retries + 1):
            alias = generate_random_alias(settings.auto_alias_length)
            if alias.lower() in RESERVED_ALIASES:
                continue
            try:
                return await self._repository.create(alias=alias, long_url=long_url)
            except AliasAlreadyExistsError as exc:
                last_error = exc
                logger.warning(
                    "Auto alias collision attempt=%s alias=%s",
                    attempt,
                    alias,
                )

        raise AliasGenerationError() from last_error

    async def get_metadata(self, alias: str) -> UrlMetadataResponse:
        mapping = await self._repository.get_by_alias(alias)
        if mapping is None:
            raise UrlMappingNotFoundError(alias)

        pending_hits = await self._cache.get_pending_hits(alias)
        total_access_count = mapping.access_count + pending_hits

        if pending_hits > 0:
            flushed = await self._cache.reset_pending_hits(alias)
            if flushed > 0:
                persisted = await self._repository.increment_access_count(alias, flushed)
                if persisted is not None:
                    total_access_count = persisted

        return self._to_metadata(mapping, total_access_count)

    async def resolve_redirect(self, alias: str) -> str:
        cached_url = await self._cache.get_long_url(alias)
        if cached_url:
            await self._cache.increment_hits(alias)
            logger.debug("Redirect cache hit alias=%s", alias)
            return cached_url

        mapping = await self._repository.get_by_alias(alias)
        if mapping is None:
            raise UrlMappingNotFoundError(alias)

        await self._cache.set_long_url(mapping.alias, mapping.long_url)
        await self._cache.increment_hits(alias)
        logger.debug("Redirect cache miss alias=%s", alias)
        return mapping.long_url
