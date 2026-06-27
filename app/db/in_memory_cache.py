import asyncio
import logging
import time
from datetime import datetime

from app.config import settings
from app.metrics.prometheus import refresh_cache_gauges
from app.utils.expiry import is_link_expired

logger = logging.getLogger(__name__)

RedirectEntry = tuple[str, float, datetime | None]


class InMemoryUrlCache:
    """
    In-process cache for redirect targets and buffered hit counters.

    URL mappings are stored in PostgreSQL. This cache reduces DB reads on
    hot redirects and batches access-count writes until metadata is read.
    """

    def __init__(self) -> None:
        self._redirects: dict[str, RedirectEntry] = {}
        self._hits: dict[str, int] = {}
        self._lock = asyncio.Lock()
        self._ttl = settings.redirect_cache_ttl_seconds

    def _update_metrics(self) -> None:
        if settings.metrics_enabled:
            refresh_cache_gauges(
                redirect_entries=len(self._redirects),
                pending_hits=sum(self._hits.values()),
            )

    async def get_long_url(self, alias: str) -> str | None:
        async with self._lock:
            entry = self._redirects.get(alias)
            if entry is None:
                return None
            long_url, cache_expires_at, link_expires_at = entry
            if time.monotonic() > cache_expires_at or is_link_expired(link_expires_at):
                del self._redirects[alias]
                self._update_metrics()
                return None
            return long_url

    async def set_long_url(
        self,
        alias: str,
        long_url: str,
        *,
        link_expires_at: datetime | None = None,
    ) -> None:
        async with self._lock:
            self._redirects[alias] = (
                long_url,
                time.monotonic() + self._ttl,
                link_expires_at,
            )
            self._update_metrics()

    async def invalidate(self, alias: str) -> None:
        async with self._lock:
            self._redirects.pop(alias, None)
            self._hits.pop(alias, None)
            self._update_metrics()

    async def increment_hits(self, alias: str) -> None:
        async with self._lock:
            self._hits[alias] = self._hits.get(alias, 0) + 1
            self._update_metrics()

    async def get_pending_hits(self, alias: str) -> int:
        async with self._lock:
            return self._hits.get(alias, 0)

    async def reset_pending_hits(self, alias: str) -> int:
        async with self._lock:
            count = self._hits.pop(alias, 0)
            self._update_metrics()
            return count
