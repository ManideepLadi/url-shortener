import asyncio
import logging
from datetime import UTC, datetime

from app.models.url import UrlMapping
from app.utils.exceptions import AliasAlreadyExistsError

logger = logging.getLogger(__name__)


class InMemoryUrlRepository:
    """In-process URL store for local development without PostgreSQL."""

    def __init__(self) -> None:
        self._store: dict[str, UrlMapping] = {}
        self._lock = asyncio.Lock()
        self._next_id = 1

    async def create(self, alias: str, long_url: str) -> UrlMapping:
        async with self._lock:
            if alias in self._store:
                logger.warning("Alias collision on create: alias=%s", alias)
                raise AliasAlreadyExistsError(alias)

            mapping = UrlMapping(alias=alias, long_url=long_url, access_count=0)
            mapping.id = self._next_id
            self._next_id += 1
            mapping.created_at = datetime.now(UTC)
            self._store[alias] = mapping
            return mapping

    async def get_by_alias(self, alias: str) -> UrlMapping | None:
        async with self._lock:
            return self._store.get(alias)

    async def increment_access_count(self, alias: str, delta: int = 1) -> int | None:
        if delta <= 0:
            return None

        async with self._lock:
            mapping = self._store.get(alias)
            if mapping is None:
                return None
            mapping.access_count += delta
            return mapping.access_count
