import logging
from typing import Any

from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)

REDIRECT_KEY_PREFIX = "redirect:"
HITS_KEY_PREFIX = "hits:"


class UrlCache:
    """Redis-backed cache for redirect targets and hot-link hit counters."""

    def __init__(self, redis: Redis) -> None:
        self._redis = redis
        self._ttl = settings.redirect_cache_ttl_seconds

    def _redirect_key(self, alias: str) -> str:
        return f"{REDIRECT_KEY_PREFIX}{alias}"

    def _hits_key(self, alias: str) -> str:
        return f"{HITS_KEY_PREFIX}{alias}"

    async def get_long_url(self, alias: str) -> str | None:
        try:
            return await self._redis.get(self._redirect_key(alias))
        except Exception:
            logger.exception("Redis GET failed for alias=%s", alias)
            return None

    async def set_long_url(self, alias: str, long_url: str) -> None:
        try:
            await self._redis.setex(
                self._redirect_key(alias),
                self._ttl,
                long_url,
            )
        except Exception:
            logger.exception("Redis SET failed for alias=%s", alias)

    async def invalidate(self, alias: str) -> None:
        try:
            await self._redis.delete(
                self._redirect_key(alias),
                self._hits_key(alias),
            )
        except Exception:
            logger.exception("Redis DELETE failed for alias=%s", alias)

    async def increment_hits(self, alias: str) -> None:
        try:
            await self._redis.incr(self._hits_key(alias))
        except Exception:
            logger.exception("Redis INCR failed for alias=%s", alias)

    async def get_pending_hits(self, alias: str) -> int:
        try:
            value = await self._redis.get(self._hits_key(alias))
            return int(value) if value is not None else 0
        except Exception:
            logger.exception("Redis GET hits failed for alias=%s", alias)
            return 0

    async def reset_pending_hits(self, alias: str) -> int:
        """
        Atomically read and reset pending hit counter.

        Returns the number of hits flushed to the database.
        """
        hits_key = self._hits_key(alias)
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.get(hits_key)
                pipe.delete(hits_key)
                results: list[Any] = await pipe.execute()
            raw_hits = results[0]
            return int(raw_hits) if raw_hits is not None else 0
        except Exception:
            logger.exception("Redis pipeline failed for alias=%s", alias)
            return 0

    async def ping(self) -> bool:
        try:
            return bool(await self._redis.ping())
        except Exception:
            logger.exception("Redis ping failed")
            return False
