import re
import secrets
import string

ALIAS_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")

# Routes reserved for API and infrastructure endpoints.
RESERVED_ALIASES = frozenset(
    {
        "api",
        "docs",
        "health",
        "openapi",
        "redoc",
        "metrics",
        "admin",
    }
)

ALPHABET = string.ascii_letters + string.digits


def generate_random_alias(length: int) -> str:
    """Generate a cryptographically random URL-safe alias."""
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def validate_custom_alias(alias: str) -> str:
    """
    Validate and normalize a custom alias.

    Returns the normalized alias or raises ValueError with a clear message.
    """
    normalized = alias.strip()
    if not ALIAS_PATTERN.match(normalized):
        raise ValueError(
            "Custom alias must be 3-32 characters and contain only "
            "letters, numbers, hyphens, and underscores"
        )
    if normalized.lower() in RESERVED_ALIASES:
        raise ValueError(f"Alias '{normalized}' is reserved and cannot be used")
    return normalized
