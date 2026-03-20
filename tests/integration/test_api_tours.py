"""Integration tests for /api/v1/tours endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.integration.conftest import (
    make_gpstour_detail,
    make_tour_detail,
    make_tour_summaries,
)


def _mock_komoot_cm(method: str, return_value):
    """Build a mock KomootClient async context manager."""
    mock_client = AsyncMock()
    getattr(mock_client, method).return_value = return_value
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _mock_gpstour_cm(method: str, return_value):
    """Build a mock GPSTourClient async context manager."""
    mock_client = AsyncMock()
    getattr(mock_client, method).return_value = return_value
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_tours(api_client: AsyncClient) -> None:
    """GET /api/v1/tours/search aggregates results from Komoot + GPSTour."""
    komoot_results = make_tour_summaries()

    komoot_cm = _mock_komoot_cm("search_tours", komoot_results)
    gpstour_cm = _mock_gpstour_cm("search_tours", [])

    with (
        patch("mtb_mcp.api.routes.tours.KomootClient", return_value=komoot_cm),
        patch("mtb_mcp.api.routes.tours.GPSTourClient", return_value=gpstour_cm),
    ):
        resp = await api_client.get(
            "/api/v1/tours/search",
            params={"lat": 49.59, "lon": 11.0, "radius_km": 30},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["total"] >= 1
    assert body["data"][0]["name"] == "Rund um die Burg"
    assert body["data"][0]["source"] == "komoot"


@pytest.mark.asyncio
async def test_komoot_tour_detail(api_client: AsyncClient) -> None:
    """GET /api/v1/tours/komoot/{tour_id} returns Komoot tour details."""
    detail = make_tour_detail()
    komoot_cm = _mock_komoot_cm("get_tour_details", detail)

    with patch("mtb_mcp.api.routes.tours.KomootClient", return_value=komoot_cm):
        resp = await api_client.get("/api/v1/tours/komoot/1234")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["data"]["name"] == "Rund um die Burg"
    assert body["data"]["distance_km"] == 42.0
    assert body["data"]["description"] == "Schöne Rundtour"


@pytest.mark.asyncio
async def test_gpstour_tour_detail(api_client: AsyncClient) -> None:
    """GET /api/v1/tours/gpstour/{tour_id} returns GPS-Tour.info details."""
    detail = make_gpstour_detail()
    gpstour_cm = _mock_gpstour_cm("get_tour_details", detail)

    with patch("mtb_mcp.api.routes.tours.GPSTourClient", return_value=gpstour_cm):
        resp = await api_client.get("/api/v1/tours/gpstour/5678")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["data"]["name"] == "Altmühltal Classic"
    assert body["data"]["source"] == "gps_tour"
    assert body["data"]["distance_km"] == 35.0


@pytest.mark.asyncio
async def test_komoot_download_gpx(api_client: AsyncClient) -> None:
    """GET /api/v1/tours/komoot/{tour_id}/gpx returns GPX XML content."""
    gpx_bytes = b'<?xml version="1.0"?><gpx><trk><name>Test</name></trk></gpx>'
    komoot_cm = _mock_komoot_cm("download_gpx", gpx_bytes)

    with patch("mtb_mcp.api.routes.tours.KomootClient", return_value=komoot_cm):
        resp = await api_client.get("/api/v1/tours/komoot/1234/gpx")

    assert resp.status_code == 200
    assert "gpx" in resp.headers.get("content-type", "")
    assert b"<gpx>" in resp.content
