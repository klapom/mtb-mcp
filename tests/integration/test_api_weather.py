"""Integration tests for /api/v1/weather endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.integration.conftest import (
    make_hourly_forecast,
    make_rain_history,
    make_rain_radar,
    make_weather_alerts,
)


def _patch_dwd(method: str, return_value):
    """Return a context manager that patches a DWDClient method."""
    return patch(
        "mtb_mcp.api.routes.weather.DWDClient",
        return_value=_make_dwd_cm(method, return_value),
    )


def _make_dwd_cm(method: str, return_value):
    """Build a mock DWDClient that works as an async context manager."""
    mock_client = AsyncMock()
    getattr(mock_client, method).return_value = return_value
    # Support `async with DWDClient() as client:`
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forecast(api_client: AsyncClient) -> None:
    """GET /api/v1/weather/forecast returns envelope with forecast data."""
    forecast = make_hourly_forecast(hours=5)

    with _patch_dwd("get_forecast", forecast):
        resp = await api_client.get(
            "/api/v1/weather/forecast", params={"lat": 49.59, "lon": 11.0, "hours": 3}
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "data" in body
    assert "meta" in body
    # hours should be trimmed to the requested count
    assert len(body["data"]["hours"]) == 3
    assert body["data"]["location_name"] == "Test Station"


@pytest.mark.asyncio
async def test_rain_radar(api_client: AsyncClient) -> None:
    """GET /api/v1/weather/rain-radar returns radar nowcasting."""
    radar = make_rain_radar()

    with _patch_dwd("get_rain_radar", radar):
        resp = await api_client.get(
            "/api/v1/weather/rain-radar", params={"lat": 49.59, "lon": 11.0}
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["data"]["rain_approaching"] is False
    assert len(body["data"]["rain_next_60min"]) == 12


@pytest.mark.asyncio
async def test_alerts(api_client: AsyncClient) -> None:
    """GET /api/v1/weather/alerts returns a list of active alerts."""
    alerts = make_weather_alerts()

    with _patch_dwd("get_alerts", alerts):
        resp = await api_client.get(
            "/api/v1/weather/alerts", params={"lat": 49.59, "lon": 11.0}
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert len(body["data"]["alerts"]) == 1
    assert body["data"]["alerts"][0]["event"] == "THUNDERSTORM"
    assert body["data"]["alerts"][0]["severity"] == "moderate"


@pytest.mark.asyncio
async def test_history(api_client: AsyncClient) -> None:
    """GET /api/v1/weather/history returns precipitation history."""
    history = make_rain_history()

    with _patch_dwd("get_rain_history", history):
        resp = await api_client.get(
            "/api/v1/weather/history", params={"lat": 49.59, "lon": 11.0}
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["data"]["total_mm_48h"] == 2.5
    assert body["data"]["last_rain_hours_ago"] == 12.0
    assert len(body["data"]["hourly_mm"]) == 48
