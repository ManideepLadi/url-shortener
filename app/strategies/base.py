from abc import ABC, abstractmethod
from datetime import datetime

from app.models.url import UrlMapping
from app.repositories.url_repository import UrlRepository


class AliasGenerationStrategy(ABC):
    """Strategy for generating automatic short URL aliases."""

    name: str

    @abstractmethod
    async def create_auto_alias(
        self,
        repository: UrlRepository,
        long_url: str,
        *,
        expires_at: datetime | None = None,
    ) -> UrlMapping:
        """Create and persist a URL mapping with a generated alias."""
