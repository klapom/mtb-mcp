"""Integration tests for /api/v1/system endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_config(api_client: AsyncClient) -> None:
    """GET /api/v1/system/config returns non-sensitive configuration."""
    resp = await api_client.get("/api/v1/system/config")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    data = body["data"]
    assert "home_lat" in data
    assert "home_lon" in data
    assert "default_radius_km" in data
    assert "log_level" in data
    # Sensitive values should NOT be present
    assert "strava_client_secret" not in data
    assert "komoot_password" not in data


@pytest.mark.asyncio
async def test_api_status_with_services(api_client: AsyncClient) -> None:
    """GET /api/v1/system/api-status reports configured/reachable APIs."""
    # Mock the reachability check to avoid real HTTP calls
    with patch(
        "mtb_mcp.api.routes.system._check_reachable",
        new_callable=AsyncMock,
        return_value=True,
    ):
        resp = await api_client.get("/api/v1/system/api-status")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    apis = body["data"]["apis"]
    assert isinstance(apis, list)

    # Should contain well-known API entries
    api_names = {api["name"] for api in apis}
    assert "dwd" in api_names
    assert "overpass" in api_names
    assert "strava" in api_names
    assert "komoot" in api_names

    # Check that each API entry has the expected fields
    for api in apis:
        assert "name" in api
        assert "configured" in api
        assert "reachable" in api
