from datetime import UTC, datetime, timedelta

import pytest

from app.schemas.url import CreateUrlRequest
from app.utils.expiry import compute_expires_at, is_link_expired


class TestComputeExpiresAt:
    def test_none_means_no_expiry(self):
        assert compute_expires_at(None) is None

    def test_returns_future_timestamp(self):
        before = datetime.now(UTC)
        expires_at = compute_expires_at(3600)
        after = datetime.now(UTC)
        assert expires_at is not None
        assert before + timedelta(seconds=3600) <= expires_at <= after + timedelta(seconds=3600)


class TestIsLinkExpired:
    def test_none_never_expires(self):
        assert is_link_expired(None) is False

    def test_future_expiry_is_active(self):
        future = datetime.now(UTC) + timedelta(hours=1)
        assert is_link_expired(future) is False

    def test_past_expiry_is_expired(self):
        past = datetime.now(UTC) - timedelta(seconds=1)
        assert is_link_expired(past) is True


class TestCreateUrlRequestTtl:
    def test_accepts_valid_ttl(self):
        request = CreateUrlRequest(
            long_url="https://example.com",
            ttl_seconds=3600,
        )
        assert request.ttl_seconds == 3600

    def test_rejects_ttl_above_max(self, monkeypatch):
        monkeypatch.setattr(
            "app.schemas.url.settings.max_link_ttl_seconds",
            100,
        )
        with pytest.raises(ValueError, match="ttl_seconds must be at most"):
            CreateUrlRequest(
                long_url="https://example.com",
                ttl_seconds=101,
            )

    def test_rejects_non_positive_ttl(self):
        with pytest.raises(ValueError):
            CreateUrlRequest(
                long_url="https://example.com",
                ttl_seconds=0,
            )
