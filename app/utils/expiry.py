from datetime import UTC, datetime, timedelta


def utc_now() -> datetime:
    return datetime.now(UTC)


def compute_expires_at(ttl_seconds: int | None) -> datetime | None:
    """Return an absolute expiry timestamp from a TTL in seconds."""
    if ttl_seconds is None:
        return None
    return utc_now() + timedelta(seconds=ttl_seconds)


def is_link_expired(expires_at: datetime | None, *, now: datetime | None = None) -> bool:
    """Return True when the link has passed its expiry time."""
    if expires_at is None:
        return False
    current = now or utc_now()
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return current >= expires_at
