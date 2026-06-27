from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.models.url import UrlMapping
from app.strategies.base62_alias_strategy import Base62AliasStrategy
from app.strategies.random_alias_strategy import RandomAliasStrategy
from app.strategies import get_alias_strategy
from app.config import Settings
from app.utils.exceptions import AliasAlreadyExistsError, AliasGenerationError


def _mapping(alias: str = "abc123", record_id: int = 1) -> UrlMapping:
    mapping = UrlMapping(alias=alias, long_url="https://example.com", access_count=0)
    mapping.id = record_id
    mapping.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    return mapping


class TestGetAliasStrategy:
    def test_returns_random_strategy_by_default(self):
        strategy = get_alias_strategy(Settings(auto_alias_strategy="random"))
        assert strategy.name == "random"

    def test_returns_base62_strategy(self):
        strategy = get_alias_strategy(
            Settings(auto_alias_strategy="base62", auto_alias_length=4)
        )
        assert strategy.name == "base62"
        assert isinstance(strategy, Base62AliasStrategy)

    def test_rejects_unknown_strategy(self):
        with pytest.raises(ValueError, match="AUTO_ALIAS_STRATEGY must be"):
            get_alias_strategy(Settings(auto_alias_strategy="hash"))


class TestRandomAliasStrategy:
    @pytest.mark.asyncio
    async def test_creates_mapping_with_generated_alias(self):
        repository = AsyncMock()
        repository.create.return_value = _mapping(alias="random01")

        strategy = RandomAliasStrategy(length=8, max_retries=3)
        result = await strategy.create_auto_alias(repository, "https://example.com")

        assert result.alias == "random01"
        repository.create.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retries_on_collision(self):
        repository = AsyncMock()
        repository.create.side_effect = [
            AliasAlreadyExistsError("x"),
            _mapping(alias="retry01"),
        ]

        strategy = RandomAliasStrategy(length=8, max_retries=3)
        result = await strategy.create_auto_alias(repository, "https://example.com")

        assert result.alias == "retry01"
        assert repository.create.await_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(self):
        repository = AsyncMock()
        repository.create.side_effect = AliasAlreadyExistsError("x")

        strategy = RandomAliasStrategy(length=8, max_retries=2)

        with pytest.raises(AliasGenerationError):
            await strategy.create_auto_alias(repository, "https://example.com")


class TestBase62AliasStrategy:
    def test_encode_record_id(self):
        strategy = Base62AliasStrategy(min_length=3)
        assert strategy.encode_record_id(1) == "001"
        assert strategy.encode_record_id(62) == "010"

    def test_encode_avoids_reserved_aliases(self, monkeypatch):
        strategy = Base62AliasStrategy(min_length=3)
        monkeypatch.setattr(
            "app.strategies.base62_alias_strategy.RESERVED_ALIASES",
            frozenset({"001"}),
        )

        alias = strategy.encode_record_id(1)
        assert alias != "001"

    @pytest.mark.asyncio
    async def test_creates_mapping_from_record_id(self):
        repository = AsyncMock()
        flushed = _mapping(alias="temp", record_id=5)
        finalized = _mapping(alias="005", record_id=5)
        repository.create_and_flush.return_value = flushed
        repository.finalize_alias.return_value = finalized

        strategy = Base62AliasStrategy(min_length=3)
        result = await strategy.create_auto_alias(repository, "https://example.com")

        assert result.alias == "005"
        repository.create_and_flush.assert_awaited_once()
        repository.finalize_alias.assert_awaited_once_with(flushed, "005")

    @pytest.mark.asyncio
    async def test_discards_pending_row_on_finalize_failure(self):
        repository = AsyncMock()
        flushed = _mapping(alias="temp", record_id=2)
        repository.create_and_flush.return_value = flushed
        repository.finalize_alias.side_effect = AliasAlreadyExistsError("005")

        strategy = Base62AliasStrategy(min_length=3)

        with pytest.raises(AliasAlreadyExistsError):
            await strategy.create_auto_alias(repository, "https://example.com")

        repository.discard_pending.assert_awaited_once_with(flushed)
