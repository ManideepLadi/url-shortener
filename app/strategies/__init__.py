from app.config import Settings, settings
from app.strategies.base import AliasGenerationStrategy
from app.strategies.base62_alias_strategy import Base62AliasStrategy
from app.strategies.random_alias_strategy import RandomAliasStrategy

__all__ = [
    "AliasGenerationStrategy",
    "Base62AliasStrategy",
    "RandomAliasStrategy",
    "get_alias_strategy",
]


def get_alias_strategy(config: Settings | None = None) -> AliasGenerationStrategy:
    """Build the configured alias generation strategy."""
    config = config or settings
    strategy_name = config.auto_alias_strategy.lower()

    if strategy_name == "base62":
        return Base62AliasStrategy(min_length=config.auto_alias_length)

    if strategy_name == "random":
        return RandomAliasStrategy(
            length=config.auto_alias_length,
            max_retries=config.auto_alias_max_retries,
        )

    raise ValueError(
        f"Unsupported AUTO_ALIAS_STRATEGY: {config.auto_alias_strategy!r}. "
        "Use 'random' or 'base62'."
    )
