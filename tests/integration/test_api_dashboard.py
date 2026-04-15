"""Integration tests for GET /api/v1/dashboard."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from tests.integration.conftest import make_hourly_forecast, make_rain_history


def _make_dwd_cm(forecast, history):
    """Build a DWDClient mock that returns both forecast and rain history."""
    mock_client = AsyncMock()
    mock_client.get_forecast.return_value = forecast
    mock_client.get_rain_history.return_value = history
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


def _make_failing_dwd_cm():
    """Build a DWDClient mock that raises on all calls."""
    mock_client = AsyncMock()
    mock_client.get_forecast.side_effect = Exception("DWD unavailable")
    mock_client.get_rain_history.side_effect = Exception("DWD unavailable")
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dashboard_full(authed_client: AsyncClient) -> None:
    """GET /api/v1/dashboard returns aggregated dashboard data."""
    forecast = make_hourly_forecast(hours=72)
    history = make_rain_history()
    dwd_cm = _make_dwd_cm(forecast, history)

    with patch("mtb_mcp.api.routes.dashboard.DWDClient", return_value=dwd_cm):
        resp = await authed_client.get(
            "/api/v1/dashboard", params={"lat": 49.59, "lon": 11.0}
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    data = body["data"]

    # ride_score should be populated when weather is available
    assert data["ride_score"] is not None
    assert "score" in data["ride_score"]
    assert "verdict" in data["ride_score"]

    # weather_current should have temperature from first forecast hour
    assert data["weather_current"] is not None
    assert "temp_c" in data["weather_current"]

    # trail_condition should be estimated
    assert data["trail_condition"] is not None
    assert data["trail_condition"]["condition"] in (
        "dry", "damp", "wet", "muddy", "frozen",
    )

    # next_service and active_timer may be None (no bikes/timers in test DB)
    # but the keys should be present
    assert "next_service" in data
    assert "active_timer" in data

    # meta envelope
    assert "meta" in body
    assert "request_id" in body["meta"]


@pytest.mark.asyncio
async def test_dashboard_handles_missing_services(
    authed_client: AsyncClient,
) -> None:
    """Dashboard gracefully handles DWD being unreachable."""
    dwd_cm = _make_failing_dwd_cm()

    with patch("mtb_mcp.api.routes.dashboard.DWDClient", return_value=dwd_cm):
        resp = await authed_client.get("/api/v1/dashboard")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    data = body["data"]

    # Weather-dependent sections should be None when DWD fails
    assert data["ride_score"] is None
    assert data["weather_current"] is None
    assert data["trail_condition"] is None
