import logging
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.url import UrlMapping
from app.utils.exceptions import AliasAlreadyExistsError

logger = logging.getLogger(__name__)


class UrlRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        alias: str,
        long_url: str,
        *,
        expires_at: datetime | None = None,
    ) -> UrlMapping:
        mapping = UrlMapping(alias=alias, long_url=long_url, expires_at=expires_at)
        self._session.add(mapping)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            logger.warning("Alias collision on create: alias=%s", alias)
            raise AliasAlreadyExistsError(alias) from exc

        await self._session.refresh(mapping)
        return mapping

    async def create_and_flush(
        self,
        alias: str,
        long_url: str,
        *,
        expires_at: datetime | None = None,
    ) -> UrlMapping:
        """Insert a row and flush so the autoincrement ID is available."""
        mapping = UrlMapping(alias=alias, long_url=long_url, expires_at=expires_at)
        self._session.add(mapping)
        await self._session.flush()
        await self._session.refresh(mapping)
        return mapping

    async def finalize_alias(self, mapping: UrlMapping, alias: str) -> UrlMapping:
        """Replace a temporary alias with the final generated alias."""
        mapping.alias = alias
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            logger.warning("Alias collision on finalize: alias=%s", alias)
            raise AliasAlreadyExistsError(alias) from exc

        await self._session.refresh(mapping)
        return mapping

    async def discard_pending(self, mapping: UrlMapping) -> None:
        """Roll back a flushed-but-not-committed row after failed alias assignment."""
        await self._session.rollback()

    async def get_by_alias(self, alias: str) -> UrlMapping | None:
        result = await self._session.execute(
            select(UrlMapping).where(UrlMapping.alias == alias)
        )
        return result.scalar_one_or_none()

    async def increment_access_count(self, alias: str, delta: int = 1) -> int | None:
        if delta <= 0:
            return None

        result = await self._session.execute(
            update(UrlMapping)
            .where(UrlMapping.alias == alias)
            .values(access_count=UrlMapping.access_count + delta)
            .returning(UrlMapping.access_count)
        )
        await self._session.commit()
        row = result.scalar_one_or_none()
        return row
