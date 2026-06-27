import logging

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.url import UrlMapping
from app.utils.exceptions import AliasAlreadyExistsError

logger = logging.getLogger(__name__)


class UrlRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, alias: str, long_url: str) -> UrlMapping:
        mapping = UrlMapping(alias=alias, long_url=long_url)
        self._session.add(mapping)
        try:
            await self._session.commit()
        except IntegrityError as exc:
            await self._session.rollback()
            logger.warning("Alias collision on create: alias=%s", alias)
            raise AliasAlreadyExistsError(alias) from exc

        await self._session.refresh(mapping)
        return mapping

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
