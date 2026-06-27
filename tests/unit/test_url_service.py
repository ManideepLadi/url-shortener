from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.models.url import UrlMapping
from app.schemas.url import CreateUrlRequest
from app.services.url_service import UrlService
from app.strategies.random_alias_strategy import RandomAliasStrategy
from app.utils.exceptions import (
    AliasAlreadyExistsError,
    AliasGenerationError,
    UrlMappingNotFoundError,
)


def _mapping(alias: str = "abc123", long_url: str = "https://example.com") -> UrlMapping:
    mapping = UrlMapping(alias=alias, long_url=long_url, access_count=0)
    mapping.id = 1
    mapping.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return mapping


@pytest.fixture
def repository() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def cache() -> AsyncMock:
    mock = AsyncMock()
    mock.get_long_url.return_value = None
    mock.get_pending_hits.return_value = 0
    return mock


@pytest.fixture
def service(repository: AsyncMock, cache: AsyncMock) -> UrlService:
    return UrlService(
        repository=repository,
        cache=cache,
        alias_strategy=RandomAliasStrategy(length=8, max_retries=5),
    )


class TestCreateShortUrl:
    @pytest.mark.asyncio
    async def test_create_with_custom_alias(self, service, repository, cache):
        repository.create.return_value = _mapping(alias="my-link")

        with patch("app.services.url_service.record_url_created") as record:
            result = await service.create_short_url(
                CreateUrlRequest(
                    long_url="https://example.com/path",
                    custom_alias="my-link",
                )
            )

        assert result.alias == "my-link"
        record.assert_called_once_with(alias_source="custom", strategy="none")
        assert result.short_url.endswith("/my-link")
        repository.create.assert_awaited_once_with(
            alias="my-link",
            long_url="https://example.com/path",
        )
        cache.set_long_url.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_auto_alias_retries_on_collision(self, service, repository, cache):
        repository.create.side_effect = [
            AliasAlreadyExistsError("x"),
            _mapping(alias="generated"),
        ]

        result = await service.create_short_url(
            CreateUrlRequest(long_url="https://example.com")
        )

        assert result.alias == "generated"
        assert repository.create.await_count == 2

    @pytest.mark.asyncio
    async def test_create_auto_alias_raises_after_max_retries(self, service, repository):
        repository.create.side_effect = AliasAlreadyExistsError("x")

        with pytest.raises(AliasGenerationError):
            await service.create_short_url(
                CreateUrlRequest(long_url="https://example.com")
            )


class TestResolveRedirect:
    @pytest.mark.asyncio
    async def test_returns_cached_url(self, service, repository, cache):
        cache.get_long_url.return_value = "https://cached.example"

        with patch("app.services.url_service.record_redirect") as record:
            url = await service.resolve_redirect("abc123")

        assert url == "https://cached.example"
        record.assert_called_once_with(cache_hit=True)
        repository.get_by_alias.assert_not_awaited()
        cache.increment_hits.assert_awaited_once_with("abc123")

    @pytest.mark.asyncio
    async def test_loads_from_db_on_cache_miss(self, service, repository, cache):
        repository.get_by_alias.return_value = _mapping()

        with patch("app.services.url_service.record_redirect") as record:
            url = await service.resolve_redirect("abc123")

        assert url == "https://example.com"
        record.assert_called_once_with(cache_hit=False)
        cache.set_long_url.assert_awaited_once()
        cache.increment_hits.assert_awaited_once_with("abc123")

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, service, repository, cache):
        repository.get_by_alias.return_value = None

        with pytest.raises(UrlMappingNotFoundError):
            await service.resolve_redirect("missing")


class TestGetMetadata:
    @pytest.mark.asyncio
    async def test_includes_pending_hits(self, service, repository, cache):
        repository.get_by_alias.return_value = _mapping()
        cache.get_pending_hits.return_value = 5
        cache.reset_pending_hits.return_value = 5
        repository.increment_access_count.return_value = 5

        result = await service.get_metadata("abc123")

        assert result.access_count == 5
        repository.increment_access_count.assert_awaited_once_with("abc123", 5)

    @pytest.mark.asyncio
    async def test_raises_when_not_found(self, service, repository):
        repository.get_by_alias.return_value = None

        with pytest.raises(UrlMappingNotFoundError):
            await service.get_metadata("missing")
