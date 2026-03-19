"""Tests for stub API clients."""

from __future__ import annotations

from mtb_mcp.clients.bosch import BoschClient
from mtb_mcp.clients.mtbproject import MTBProjectClient
from mtb_mcp.clients.trailforks import TrailforksClient
from mtb_mcp.clients.wahoo import WahooClient


class TestTrailforksClient:
    """Tests for the Trailforks stub client."""

    async def test_is_available_returns_false(self) -> None:
        """Trailforks should not be available (no public API)."""
        client = TrailforksClient()
        assert await client.is_available() is False

    async def test_search_trails_returns_empty(self) -> None:
        """search_trails should return an empty list."""
        client = TrailforksClient()
        result = await client.search_trails(lat=49.59, lon=11.00)
        assert result == []

    async def test_search_trails_with_radius(self) -> None:
        """search_trails should accept a custom radius."""
        client = TrailforksClient()
        result = await client.search_trails(lat=49.59, lon=11.00, radius_km=50.0)
        assert result == []


class TestMTBProjectClient:
    """Tests for the MTB Project stub client."""

    async def test_is_available_returns_false(self) -> None:
        """MTB Project should not be available."""
        client = MTBProjectClient()
        assert await client.is_available() is False

    async def test_search_trails_returns_empty(self) -> None:
        """search_trails should return an empty list."""
        client = MTBProjectClient()
        result = await client.search_trails(lat=37.78, lon=-122.42)
        assert result == []

    async def test_search_trails_with_radius(self) -> None:
        """search_trails should accept a custom radius."""
        client = MTBProjectClient()
        result = await client.search_trails(lat=37.78, lon=-122.42, radius_km=10.0)
        assert result == []


class TestWahooClient:
    """Tests for the Wahoo stub client."""

    async def test_is_available_returns_false(self) -> None:
        """Wahoo should not be available."""
        client = WahooClient()
        assert await client.is_available() is False

    async def test_default_init(self) -> None:
        """Should initialize without credentials."""
        client = WahooClient()
        assert client._client_id is None
        assert client._client_secret is None

    async def test_init_with_credentials(self) -> None:
        """Should accept optional credentials."""
        client = WahooClient(client_id="test-id", client_secret="test-secret")
        assert client._client_id == "test-id"
        assert client._client_secret == "test-secret"


class TestBoschClient:
    """Tests for the Bosch eBike stub client."""

    async def test_is_available_returns_false(self) -> None:
        """Bosch should not be available."""
        client = BoschClient()
        assert await client.is_available() is False

    async def test_get_battery_status_returns_none(self) -> None:
        """get_battery_status should return None."""
        client = BoschClient()
        result = await client.get_battery_status()
        assert result is None

    async def test_default_init(self) -> None:
        """Should initialize without credentials."""
        client = BoschClient()
        assert client._client_id is None
        assert client._client_secret is None

    async def test_init_with_credentials(self) -> None:
        """Should accept optional credentials."""
        client = BoschClient(client_id="bosch-id", client_secret="bosch-secret")
        assert client._client_id == "bosch-id"
        assert client._client_secret == "bosch-secret"
