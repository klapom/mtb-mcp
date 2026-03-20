"""Integration tests for /api/v1/safety/timer endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient


def _future_time(hours: int = 3) -> str:
    """Return a datetime string in the future for timer tests."""
    dt = datetime.now(tz=timezone.utc) + timedelta(hours=hours)
    return dt.strftime("%Y-%m-%d %H:%M")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_set_timer(api_client_with_db: AsyncClient) -> None:
    """POST /api/v1/safety/timer creates an active timer."""
    resp = await api_client_with_db.post(
        "/api/v1/safety/timer",
        json={
            "expected_return_time": _future_time(hours=3),
            "ride_description": "Evening loop around the lake",
            "emergency_contact": "+49 170 1234567",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    data = body["data"]
    assert data["status"] == "active"
    assert "timer_id" in data
    assert data["ride_description"] == "Evening loop around the lake"
    assert data["emergency_contact"] == "+49 170 1234567"
    assert "expected_return" in data


@pytest.mark.asyncio
async def test_get_timer(api_client_with_db: AsyncClient) -> None:
    """GET /api/v1/safety/timer returns the active timer after creation."""
    # Create a timer first
    await api_client_with_db.post(
        "/api/v1/safety/timer",
        json={
            "expected_return_time": _future_time(hours=2),
            "ride_description": "Trail ride",
        },
    )

    resp = await api_client_with_db.get("/api/v1/safety/timer")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    data = body["data"]
    assert data["active"] is True
    assert data["status"] == "active"
    assert "timer_id" in data
    assert "expected_return" in data
    assert "minutes_remaining" in data
    assert data["ride_description"] == "Trail ride"


@pytest.mark.asyncio
async def test_cancel_timer(api_client_with_db: AsyncClient) -> None:
    """DELETE /api/v1/safety/timer cancels the active timer."""
    # Create a timer
    create_resp = await api_client_with_db.post(
        "/api/v1/safety/timer",
        json={
            "expected_return_time": _future_time(hours=4),
            "ride_description": "Long ride",
        },
    )
    timer_id = create_resp.json()["data"]["timer_id"]

    # Cancel it
    resp = await api_client_with_db.delete("/api/v1/safety/timer")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["data"]["timer_id"] == timer_id
    assert body["data"]["status"] == "cancelled"

    # Verify GET now shows no active timer
    check_resp = await api_client_with_db.get("/api/v1/safety/timer")
    check_body = check_resp.json()
    assert check_body["data"]["active"] is False
