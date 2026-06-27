import logging
import secrets

from app.models.url import UrlMapping
from app.repositories.url_repository import UrlRepository
from app.strategies.base import AliasGenerationStrategy
from app.utils.alias import RESERVED_ALIASES, generate_random_alias
from app.utils.exceptions import AliasAlreadyExistsError, AliasGenerationError

logger = logging.getLogger(__name__)


class RandomAliasStrategy(AliasGenerationStrategy):
    """Generate cryptographically random alphanumeric aliases."""

    name = "random"

    def __init__(self, *, length: int, max_retries: int) -> None:
        self._length = length
        self._max_retries = max_retries

    async def create_auto_alias(
        self,
        repository: UrlRepository,
        long_url: str,
    ) -> UrlMapping:
        last_error: AliasAlreadyExistsError | None = None

        for attempt in range(1, self._max_retries + 1):
            alias = generate_random_alias(self._length)
            if alias.lower() in RESERVED_ALIASES:
                continue
            try:
                return await repository.create(alias=alias, long_url=long_url)
            except AliasAlreadyExistsError as exc:
                last_error = exc
                logger.warning(
                    "Random alias collision attempt=%s alias=%s",
                    attempt,
                    alias,
                )

        raise AliasGenerationError() from last_error

    def generate_candidate(self) -> str:
        """Generate a single alias candidate (used by tests and retry loops)."""
        return generate_random_alias(self._length)
