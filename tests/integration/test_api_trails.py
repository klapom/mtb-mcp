"""Integration tests for /api/v1/trails endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.integration.conftest import (
    make_hourly_forecast,
    make_rain_history,
    make_trail_detail,
    make_trail_list,
)


def _patch_overpass(method: str, return_value):
    """Patch OverpassClient as an async context manager."""
    mock_client = AsyncMock()
    getattr(mock_client, method).return_value = return_value
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return patch(
        "mtb_mcp.api.routes.trails.OverpassClient",
        return_value=cm,
    )


def _patch_dwd_for_condition(forecast, history):
    """Patch DWDClient for the trail condition endpoint."""
    mock_client = AsyncMock()
    mock_client.get_rain_history.return_value = history
    mock_client.get_forecast.return_value = forecast
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return patch(
        "mtb_mcp.api.routes.trails.DWDClient",
        return_value=cm,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_trails(api_client: AsyncClient) -> None:
    """GET /api/v1/trails/ returns a paginated list of trails."""
    trails = make_trail_list()

    with _patch_overpass("find_trails", trails):
        resp = await api_client.get(
            "/api/v1/trails/",
            params={"lat": 49.59, "lon": 11.0, "radius_km": 10},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["total"] == 2
    assert len(body["data"]) == 2
    assert body["data"][0]["osm_id"] == 12345
    assert body["data"][0]["name"] == "Flowtrail Erlangen"


@pytest.mark.asyncio
async def test_trail_detail(api_client: AsyncClient) -> None:
    """GET /api/v1/trails/{osm_id} returns trail detail."""
    trail = make_trail_detail()

    with _patch_overpass("get_trail_details", trail):
        resp = await api_client.get("/api/v1/trails/12345")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["data"]["osm_id"] == 12345
    assert body["data"]["name"] == "Flowtrail Erlangen"
    assert body["data"]["mtb_scale"] == "S2"
    assert len(body["data"]["geometry"]) == 3


@pytest.mark.asyncio
async def test_trail_condition(api_client: AsyncClient) -> None:
    """GET /api/v1/trails/{osm_id}/condition returns weather-based condition."""
    trail = make_trail_detail()
    forecast = make_hourly_forecast(hours=3)
    history = make_rain_history()

    with (
        _patch_overpass("get_trail_details", trail),
        _patch_dwd_for_condition(forecast, history),
    ):
        resp = await api_client.get(
            "/api/v1/trails/12345/condition", params={"surface": "dirt"}
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    data = body["data"]
    assert data["osm_id"] == 12345
    assert data["trail_name"] == "Flowtrail Erlangen"
    # The condition algorithm should produce a valid status
    assert data["condition"] in ("dry", "damp", "wet", "muddy", "frozen")
    assert data["confidence"] in ("high", "medium", "low")
    assert "reasoning" in data
    assert "rain_48h_mm" in data
