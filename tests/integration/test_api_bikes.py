"""Integration tests for /api/v1/bikes endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_bikes_empty(api_client_with_db: AsyncClient) -> None:
    """GET /api/v1/bikes/ returns empty list when no bikes exist."""
    resp = await api_client_with_db.get("/api/v1/bikes/")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["data"] == []
    assert body["total"] == 0


@pytest.mark.asyncio
async def test_add_component_creates_bike_and_component(
    api_client_with_db: AsyncClient,
) -> None:
    """POST /api/v1/bikes/{name}/components creates bike if missing + adds component."""
    resp = await api_client_with_db.post(
        "/api/v1/bikes/TrailShredder/components",
        json={"component_type": "chain", "brand": "Shimano", "model": "CN-M8100"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    data = body["data"]
    assert data["bike_name"] == "TrailShredder"
    assert data["type"] == "chain"
    assert data["brand"] == "Shimano"
    assert "component_id" in data

    # Now listing bikes should show the new bike with its component
    resp2 = await api_client_with_db.get("/api/v1/bikes/")
    body2 = resp2.json()
    assert body2["total"] == 1
    assert body2["data"][0]["name"] == "TrailShredder"
    assert len(body2["data"][0]["components"]) == 1


@pytest.mark.asyncio
async def test_log_ride(api_client_with_db: AsyncClient) -> None:
    """POST /api/v1/bikes/{name}/rides updates km and wear counters."""
    # First, create the bike with a component
    await api_client_with_db.post(
        "/api/v1/bikes/TestBike/components",
        json={"component_type": "chain", "brand": "SRAM"},
    )

    resp = await api_client_with_db.post(
        "/api/v1/bikes/TestBike/rides",
        json={
            "distance_km": 25.0,
            "duration_hours": 2.0,
            "terrain": "S1",
            "weather": "dry",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    data = body["data"]
    assert data["bike_name"] == "TestBike"
    assert data["distance_km"] == 25.0
    assert data["effective_km"] > 0
    assert data["components_updated"] == 1
    assert isinstance(data["warnings"], list)


@pytest.mark.asyncio
async def test_log_service(api_client_with_db: AsyncClient) -> None:
    """POST /api/v1/bikes/{name}/service resets wear counters."""
    # Create bike + component
    await api_client_with_db.post(
        "/api/v1/bikes/ServiceBike/components",
        json={"component_type": "chain", "brand": "KMC"},
    )

    # Log some rides to build up wear
    await api_client_with_db.post(
        "/api/v1/bikes/ServiceBike/rides",
        json={"distance_km": 100.0, "duration_hours": 5.0},
    )

    # Now service the chain
    resp = await api_client_with_db.post(
        "/api/v1/bikes/ServiceBike/service",
        json={
            "component_type": "chain",
            "service_type": "replace",
            "notes": "New KMC X12 installed",
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    data = body["data"]
    assert data["bike_name"] == "ServiceBike"
    assert data["component_type"] == "chain"
    assert data["service_type"] == "replace"
    assert data["counters_reset"] is True
    assert data["previous_effective_km"] > 0
    assert "service_id" in data


@pytest.mark.asyncio
async def test_service_resets_wear(api_client_with_db: AsyncClient) -> None:
    """After service, the component wear counters should be reset to 0."""
    # Create bike + chain
    await api_client_with_db.post(
        "/api/v1/bikes/WearBike/components",
        json={"component_type": "chain"},
    )

    # Log a ride to add wear
    await api_client_with_db.post(
        "/api/v1/bikes/WearBike/rides",
        json={"distance_km": 500.0, "duration_hours": 20.0},
    )

    # Check maintenance status shows wear
    resp_before = await api_client_with_db.get("/api/v1/bikes/WearBike/maintenance")
    body_before = resp_before.json()
    assert body_before["status"] == "ok"
    chain_before = body_before["data"]["components"][0]
    assert chain_before["effective_km"] > 0

    # Service the chain
    await api_client_with_db.post(
        "/api/v1/bikes/WearBike/service",
        json={"component_type": "chain", "service_type": "replace"},
    )

    # Check maintenance status after — counters should be reset
    resp_after = await api_client_with_db.get("/api/v1/bikes/WearBike/maintenance")
    body_after = resp_after.json()
    chain_after = body_after["data"]["components"][0]
    assert chain_after["effective_km"] == 0.0
    assert chain_after["hours"] == 0.0
    assert chain_after["wear_pct"] < chain_before["wear_pct"]
