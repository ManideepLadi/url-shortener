import logging
import secrets
from datetime import datetime

from app.models.url import UrlMapping
from app.repositories.url_repository import UrlRepository
from app.strategies.base import AliasGenerationStrategy
from app.utils.alias import RESERVED_ALIASES
from app.utils.base62 import encode_base62

logger = logging.getLogger(__name__)


class Base62AliasStrategy(AliasGenerationStrategy):
    """Encode the database record ID as a Base62 alias after insert."""

    name = "base62"

    def __init__(self, *, min_length: int) -> None:
        self._min_length = min_length

    def encode_record_id(self, record_id: int) -> str:
        """Derive a URL-safe alias from a persisted record ID."""
        alias = encode_base62(record_id, min_length=self._min_length)
        suffix = 0

        while alias.lower() in RESERVED_ALIASES:
            suffix += 1
            alias = encode_base62(record_id * 1000 + suffix, min_length=self._min_length)

        return alias

    async def create_auto_alias(
        self,
        repository: UrlRepository,
        long_url: str,
        *,
        expires_at: datetime | None = None,
    ) -> UrlMapping:
        temp_alias = secrets.token_hex(16)
        mapping = await repository.create_and_flush(
            alias=temp_alias,
            long_url=long_url,
            expires_at=expires_at,
        )
        alias = self.encode_record_id(mapping.id)

        try:
            finalized = await repository.finalize_alias(mapping, alias)
        except Exception:
            await repository.discard_pending(mapping)
            raise

        logger.info("Created base62 alias=%s for record_id=%s", alias, mapping.id)
        return finalized
