"""Tests for trail MCP tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from mtb_mcp.models.common import GeoPoint
from mtb_mcp.models.trail import MTBScale, Trail, TrailSurface
from mtb_mcp.tools.trail_tools import find_trails, trail_details


def _make_trails() -> list[Trail]:
    """Create test Trail objects."""
    return [
        Trail(
            osm_id=12345678,
            name="Tiergarten Singletrail",
            mtb_scale=MTBScale.S2,
            surface=TrailSurface.dirt,
            length_m=1500.0,
            geometry=[
                GeoPoint(lat=49.596, lon=11.004),
                GeoPoint(lat=49.597, lon=11.005),
            ],
        ),
        Trail(
            osm_id=23456789,
            name="Rathsberg Trail",
            mtb_scale=MTBScale.S1,
            surface=TrailSurface.gravel,
            length_m=800.0,
        ),
    ]


class TestFindTrailsTool:
    """Tests for find_trails tool."""

    @patch("mtb_mcp.tools.trail_tools.OverpassClient")
    async def test_returns_formatted_list(self, mock_client_cls: AsyncMock) -> None:
        """Should return formatted trail list."""
        mock_client = AsyncMock()
        mock_client.find_trails.return_value = _make_trails()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await find_trails(lat=49.59, lon=11.00)

        assert "Tiergarten Singletrail" in result
        assert "Rathsberg Trail" in result
        assert "[S2]" in result
        assert "[S1]" in result
        assert "2 trail(s)" in result

    @patch("mtb_mcp.tools.trail_tools.OverpassClient")
    async def test_no_trails_found(self, mock_client_cls: AsyncMock) -> None:
        """Should show message when no trails found."""
        mock_client = AsyncMock()
        mock_client.find_trails.return_value = []
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await find_trails(lat=49.59, lon=11.00)

        assert "No MTB trails found" in result

    @patch("mtb_mcp.tools.trail_tools.OverpassClient")
    @patch("mtb_mcp.tools.trail_tools.get_settings")
    async def test_uses_home_location(
        self, mock_settings: AsyncMock, mock_client_cls: AsyncMock
    ) -> None:
        """Should use home location when no lat/lon provided."""
        mock_settings.return_value.home_lat = 49.59
        mock_settings.return_value.home_lon = 11.00

        mock_client = AsyncMock()
        mock_client.find_trails.return_value = _make_trails()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await find_trails()

        mock_client.find_trails.assert_called_once()
        call_args = mock_client.find_trails.call_args
        assert call_args[0][0] == 49.59  # lat (positional)
        assert call_args[0][1] == 11.00  # lon (positional)

    @patch("mtb_mcp.tools.trail_tools.OverpassClient")
    async def test_invalid_difficulty(self, mock_client_cls: AsyncMock) -> None:
        """Should return error for invalid difficulty filter."""
        result = await find_trails(lat=49.59, lon=11.00, min_difficulty="S7")

        assert "Invalid difficulty" in result

    @patch("mtb_mcp.tools.trail_tools.OverpassClient")
    async def test_includes_osm_id(self, mock_client_cls: AsyncMock) -> None:
        """Should include OSM ID in output for follow-up queries."""
        mock_client = AsyncMock()
        mock_client.find_trails.return_value = _make_trails()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await find_trails(lat=49.59, lon=11.00)

        assert "12345678" in result
        assert "23456789" in result


class TestTrailDetailsTool:
    """Tests for trail_details tool."""

    @patch("mtb_mcp.tools.trail_tools.OverpassClient")
    async def test_returns_details(self, mock_client_cls: AsyncMock) -> None:
        """Should return formatted trail details."""
        mock_client = AsyncMock()
        mock_client.get_trail_details.return_value = Trail(
            osm_id=12345678,
            name="Tiergarten Singletrail",
            mtb_scale=MTBScale.S2,
            surface=TrailSurface.dirt,
            length_m=1500.0,
            geometry=[
                GeoPoint(lat=49.5960, lon=11.0040),
                GeoPoint(lat=49.5975, lon=11.0055),
            ],
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await trail_details(osm_id=12345678)

        assert "Tiergarten Singletrail" in result
        assert "S2" in result
        assert "dirt" in result
        assert "1500" in result
        assert "49.59600" in result

    @patch("mtb_mcp.tools.trail_tools.OverpassClient")
    async def test_trail_not_found(self, mock_client_cls: AsyncMock) -> None:
        """Should show not-found message."""
        mock_client = AsyncMock()
        mock_client.get_trail_details.return_value = None
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await trail_details(osm_id=99999999)

        assert "No trail found" in result
        assert "99999999" in result
