"""Integration tests for GET /api/v1/health."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from mtb_mcp.api.main import app


@pytest.fixture
async def client() -> AsyncClient:
    """Lightweight client for the health endpoint (no DB needed)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_health_status_ok(client: AsyncClient) -> None:
    """GET /api/v1/health returns status ok."""
    resp = await client.get("/api/v1/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"


@pytest.mark.asyncio
async def test_health_correct_fields(client: AsyncClient) -> None:
    """GET /api/v1/health returns both 'status' and 'service' fields."""
    resp = await client.get("/api/v1/health")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["service"] == "trailpilot"
    # Timing header set by middleware
    assert "x-duration-ms" in resp.headers
