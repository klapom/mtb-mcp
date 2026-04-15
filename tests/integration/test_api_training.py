"""Integration tests for /api/v1/training endpoints."""

from __future__ import annotations

from datetime import date, timedelta

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _future_date(weeks: int = 16) -> str:
    """Return an ISO date string *weeks* weeks in the future."""
    return (date.today() + timedelta(weeks=weeks)).isoformat()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_training_status_no_data(authed_client: AsyncClient) -> None:
    """GET /api/v1/training/status returns has_data=False when no snapshots exist."""
    resp = await authed_client.get("/api/v1/training/status")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["data"]["has_data"] is False
    assert "message" in body["data"]


@pytest.mark.asyncio
async def test_create_goal(authed_client: AsyncClient) -> None:
    """POST /api/v1/training/goals creates a goal and generates a plan."""
    target = _future_date(weeks=16)
    resp = await authed_client.post(
        "/api/v1/training/goals",
        json={
            "name": "Alpencross 2026",
            "goal_type": "alpencross",
            "target_date": target,
            "target_distance_km": 400.0,
            "target_elevation_m": 12000.0,
            "description": "Garmisch to Riva",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    data = body["data"]
    assert data["goal"]["name"] == "Alpencross 2026"
    assert data["goal"]["type"] == "alpencross"
    assert "plan_summary" in data
    assert data["plan_summary"]["weeks"] > 0
    assert "phases" in data["plan_summary"]


@pytest.mark.asyncio
async def test_list_goals(authed_client: AsyncClient) -> None:
    """GET /api/v1/training/goals lists created goals."""
    # Create a goal first
    target = _future_date(weeks=12)
    await authed_client.post(
        "/api/v1/training/goals",
        json={
            "name": "XC Race",
            "goal_type": "xc_race",
            "target_date": target,
        },
    )

    resp = await authed_client.get("/api/v1/training/goals")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["total"] >= 1
    names = [g["name"] for g in body["data"]]
    assert "XC Race" in names


@pytest.mark.asyncio
async def test_training_plan(authed_client: AsyncClient) -> None:
    """GET /api/v1/training/plan returns plan weeks for the active goal."""
    target = _future_date(weeks=14)
    await authed_client.post(
        "/api/v1/training/goals",
        json={
            "name": "Plan Test Goal",
            "goal_type": "marathon",
            "target_date": target,
        },
    )

    # Use goal_name param to avoid picking up goals from other tests
    resp = await authed_client.get(
        "/api/v1/training/plan", params={"goal_name": "Plan Test Goal"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    data = body["data"]
    assert data["goal"]["name"] == "Plan Test Goal"
    assert "weeks" in data
    assert len(data["weeks"]) > 0
    # Each week should have phase, hours, km
    week = data["weeks"][0]
    assert "phase" in week
    assert "planned_hours" in week
    assert "planned_km" in week
    assert "intensity_focus" in week


@pytest.mark.asyncio
async def test_readiness_no_fitness_data(authed_client: AsyncClient) -> None:
    """GET /api/v1/training/readiness returns NO_DATA when no snapshots exist."""
    target = _future_date(weeks=10)
    await authed_client.post(
        "/api/v1/training/goals",
        json={
            "name": "Readiness Goal",
            "goal_type": "xc_race",
            "target_date": target,
        },
    )

    resp = await authed_client.get("/api/v1/training/readiness")

    assert resp.status_code == 200
    body = resp.json()
    # Should return error indicating no fitness data yet
    assert body["status"] == "error"
    assert body["error"]["code"] == "NO_DATA"
