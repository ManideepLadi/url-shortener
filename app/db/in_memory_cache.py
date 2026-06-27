import asyncio
import logging
import time

from app.config import settings

logger = logging.getLogger(__name__)


class InMemoryUrlCache:
    """In-process cache for local development without Redis."""

    def __init__(self) -> None:
        self._redirects: dict[str, tuple[str, float]] = {}
        self._hits: dict[str, int] = {}
        self._lock = asyncio.Lock()
        self._ttl = settings.redirect_cache_ttl_seconds

    async def get_long_url(self, alias: str) -> str | None:
        async with self._lock:
            entry = self._redirects.get(alias)
            if entry is None:
                return None
            long_url, expires_at = entry
            if time.monotonic() > expires_at:
                del self._redirects[alias]
                return None
            return long_url

    async def set_long_url(self, alias: str, long_url: str) -> None:
        async with self._lock:
            self._redirects[alias] = (
                long_url,
                time.monotonic() + self._ttl,
            )

    async def invalidate(self, alias: str) -> None:
        async with self._lock:
            self._redirects.pop(alias, None)
            self._hits.pop(alias, None)

    async def increment_hits(self, alias: str) -> None:
        async with self._lock:
            self._hits[alias] = self._hits.get(alias, 0) + 1

    async def get_pending_hits(self, alias: str) -> int:
        async with self._lock:
            return self._hits.get(alias, 0)

    async def reset_pending_hits(self, alias: str) -> int:
        async with self._lock:
            return self._hits.pop(alias, 0)

    async def ping(self) -> bool:
        return True
