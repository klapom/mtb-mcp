"""Integration tests for /api/v1/ebike endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_range_check_feasible(api_client: AsyncClient) -> None:
    """POST /api/v1/ebike/range-check with easy route returns can_finish=True."""
    resp = await api_client.post(
        "/api/v1/ebike/range-check",
        json={
            "battery_wh": 625.0,
            "charge_pct": 100.0,
            "distance_km": 30.0,
            "elevation_gain_m": 500.0,
            "rider_kg": 80.0,
            "bike_kg": 23.0,
            "assist_mode": "tour",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    data = body["data"]
    assert data["can_finish"] is True
    assert data["route_distance_km"] == 30.0
    assert data["assist_mode"] == "tour"
    assert data["remaining_pct"] > 0
    assert data["estimated_consumption_wh"] > 0


@pytest.mark.asyncio
async def test_range_check_not_feasible(api_client: AsyncClient) -> None:
    """POST /api/v1/ebike/range-check with extreme route returns can_finish=False."""
    resp = await api_client.post(
        "/api/v1/ebike/range-check",
        json={
            "battery_wh": 400.0,
            "charge_pct": 30.0,
            "distance_km": 120.0,
            "elevation_gain_m": 4000.0,
            "rider_kg": 95.0,
            "bike_kg": 25.0,
            "assist_mode": "turbo",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    data = body["data"]
    assert data["can_finish"] is False
    assert data["remaining_pct"] < 0 or data["remaining_wh"] < 0
    assert data["estimated_consumption_wh"] > data["available_wh"]
