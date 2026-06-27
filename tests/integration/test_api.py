import asyncio

import pytest


@pytest.mark.integration
class TestUrlApiIntegration:
    @pytest.mark.asyncio
    async def test_create_and_redirect(self, client):
        create_response = await client.post(
            "/api/v1/urls",
            json={"long_url": "https://example.com/integration-test"},
        )
        assert create_response.status_code == 201
        payload = create_response.json()
        alias = payload["alias"]
        assert payload["access_count"] == 0
        assert "created_at" in payload

        redirect_response = await client.get(f"/{alias}", follow_redirects=False)
        assert redirect_response.status_code == 307
        assert redirect_response.headers["location"] == "https://example.com/integration-test"

        metadata_response = await client.get(f"/api/v1/urls/{alias}")
        assert metadata_response.status_code == 200
        metadata = metadata_response.json()
        assert metadata["access_count"] == 1

    @pytest.mark.asyncio
    async def test_custom_alias_collision_returns_409(self, client):
        body = {
            "long_url": "https://example.com/a",
            "custom_alias": "shared-alias",
        }
        first = await client.post("/api/v1/urls", json=body)
        assert first.status_code == 201

        second = await client.post(
            "/api/v1/urls",
            json={"long_url": "https://example.com/b", "custom_alias": "shared-alias"},
        )
        assert second.status_code == 409
        assert "already in use" in second.json()["detail"]

    @pytest.mark.asyncio
    async def test_concurrent_custom_alias_creation(self, client):
        body = {
            "long_url": "https://example.com/concurrent",
            "custom_alias": "race-alias",
        }

        responses = await asyncio.gather(
            client.post("/api/v1/urls", json=body),
            client.post("/api/v1/urls", json=body),
        )

        status_codes = sorted(response.status_code for response in responses)
        assert status_codes == [201, 409]

    @pytest.mark.asyncio
    async def test_redirect_unknown_alias_returns_404(self, client):
        response = await client.get("/does-not-exist", follow_redirects=False)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_url_returns_422(self, client):
        response = await client.post(
            "/api/v1/urls",
            json={"long_url": "not-a-url"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_health_check(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "ok"
        assert body["database"] == "ok"
        assert body["cache"] == "in-memory"
