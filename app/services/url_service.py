import logging

from datetime import datetime

from app.config import settings
from app.db.in_memory_cache import InMemoryUrlCache
from app.models.url import UrlMapping
from app.repositories.url_repository import UrlRepository
from app.schemas.url import CreateUrlRequest, CreateUrlResponse, UrlMetadataResponse
from app.metrics.prometheus import record_metadata_request, record_redirect, record_url_created
from app.strategies.base import AliasGenerationStrategy
from app.utils.exceptions import UrlExpiredError, UrlMappingNotFoundError
from app.utils.expiry import compute_expires_at, is_link_expired

logger = logging.getLogger(__name__)


class UrlService:
    def __init__(
        self,
        repository: UrlRepository,
        cache: InMemoryUrlCache,
        alias_strategy: AliasGenerationStrategy,
    ) -> None:
        self._repository = repository
        self._cache = cache
        self._alias_strategy = alias_strategy
        self._base_url = settings.base_url.rstrip("/")

    def _build_short_url(self, alias: str) -> str:
        return f"{self._base_url}/{alias}"

    def _resolve_ttl_seconds(self, request: CreateUrlRequest) -> int | None:
        if request.ttl_seconds is not None:
            return request.ttl_seconds
        return settings.default_link_ttl_seconds

    def _to_metadata(self, mapping: UrlMapping, access_count: int) -> UrlMetadataResponse:
        return UrlMetadataResponse(
            alias=mapping.alias,
            long_url=mapping.long_url,
            short_url=self._build_short_url(mapping.alias),
            access_count=access_count,
            created_at=mapping.created_at,
            expires_at=mapping.expires_at,
        )

    async def _get_active_mapping(self, alias: str) -> UrlMapping:
        mapping = await self._repository.get_by_alias(alias)
        if mapping is None:
            raise UrlMappingNotFoundError(alias)
        if is_link_expired(mapping.expires_at):
            await self._cache.invalidate(alias)
            raise UrlExpiredError(alias)
        return mapping

    async def create_short_url(self, request: CreateUrlRequest) -> CreateUrlResponse:
        long_url = str(request.long_url)
        expires_at = compute_expires_at(self._resolve_ttl_seconds(request))

        if request.custom_alias:
            mapping = await self._repository.create(
                alias=request.custom_alias,
                long_url=long_url,
                expires_at=expires_at,
            )
            await self._cache.set_long_url(
                mapping.alias,
                mapping.long_url,
                link_expires_at=mapping.expires_at,
            )
            record_url_created(alias_source="custom", strategy="none")
            logger.info("Created custom alias=%s expires_at=%s", mapping.alias, mapping.expires_at)
            return CreateUrlResponse(**self._to_metadata(mapping, mapping.access_count).model_dump())

        mapping = await self._alias_strategy.create_auto_alias(
            self._repository,
            long_url,
            expires_at=expires_at,
        )
        await self._cache.set_long_url(
            mapping.alias,
            mapping.long_url,
            link_expires_at=mapping.expires_at,
        )
        record_url_created(
            alias_source="auto",
            strategy=self._alias_strategy.name,
        )
        logger.info(
            "Created auto alias=%s strategy=%s expires_at=%s",
            mapping.alias,
            self._alias_strategy.name,
            mapping.expires_at,
        )
        return CreateUrlResponse(**self._to_metadata(mapping, mapping.access_count).model_dump())

    async def get_metadata(self, alias: str) -> UrlMetadataResponse:
        record_metadata_request()
        mapping = await self._get_active_mapping(alias)

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
            record_redirect(cache_hit=True)
            logger.debug("Redirect cache hit alias=%s", alias)
            return cached_url

        mapping = await self._get_active_mapping(alias)

        await self._cache.set_long_url(
            mapping.alias,
            mapping.long_url,
            link_expires_at=mapping.expires_at,
        )
        await self._cache.increment_hits(alias)
        record_redirect(cache_hit=False)
        logger.debug("Redirect cache miss alias=%s", alias)
        return mapping.long_url
