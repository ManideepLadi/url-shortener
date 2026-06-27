import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.metrics.prometheus import normalize_metrics_path


class TestNormalizeMetricsPath:
    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("/health", "/health"),
            ("/metrics", "/metrics"),
            ("/api/v1/urls", "/api/v1/urls"),
            ("/api/v1/urls/my-link", "/api/v1/urls/{alias}"),
            ("/manideep", "/{alias}"),
            ("/unknown/nested/path", "other"),
        ],
    )
    def test_normalizes_paths(self, path: str, expected: str) -> None:
        assert normalize_metrics_path(path) == expected


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_format() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    assert "http_requests_total" in body
    assert "url_shortener_urls_created_total" in body
    assert "url_shortener_redirects_total" in body


@pytest.mark.asyncio
async def test_metrics_recorded_on_health_request() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.get("/health")
        response = await client.get("/metrics")

    assert response.status_code == 200
    assert 'http_requests_total{method="GET",path="/health",status="200"}' in response.text
