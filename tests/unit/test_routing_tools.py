"""Tests for routing MCP tools."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx

from mtb_mcp.models.common import GeoPoint
from mtb_mcp.models.route import (
    ElevationPoint,
    ElevationProfile,
    Route,
    RouteSummary,
)
from mtb_mcp.tools.routing_tools import (
    plan_loop_route,
    plan_route,
    route_elevation_profile,
)


def _make_route(source: str = "brouter") -> Route:
    """Create a test Route."""
    return Route(
        summary=RouteSummary(
            distance_km=25.3,
            elevation_gain_m=450.0,
            elevation_loss_m=420.0,
            duration_minutes=135.0,
            source=source,
        ),
        points=[
            GeoPoint(lat=49.59, lon=11.00, ele=310.0),
            GeoPoint(lat=49.60, lon=11.01, ele=340.0),
            GeoPoint(lat=49.62, lon=11.03, ele=320.0),
        ],
        gpx="<gpx>...</gpx>",
    )


def _make_elevation_profile() -> ElevationProfile:
    """Create a test ElevationProfile."""
    return ElevationProfile(
        points=[
            ElevationPoint(distance_km=0.0, elevation_m=310.0),
            ElevationPoint(distance_km=1.5, elevation_m=340.0),
            ElevationPoint(distance_km=3.0, elevation_m=320.0),
        ],
        total_distance_km=3.0,
        total_gain_m=30.0,
        total_loss_m=20.0,
        min_elevation_m=310.0,
        max_elevation_m=340.0,
    )


class TestPlanRouteTool:
    """Tests for plan_route tool."""

    @patch("mtb_mcp.tools.routing_tools.BRouterClient")
    @patch("mtb_mcp.tools.routing_tools.get_settings")
    async def test_returns_formatted_route(
        self, mock_settings: AsyncMock, mock_brouter_cls: AsyncMock
    ) -> None:
        """Should return a formatted route string from BRouter."""
        mock_settings.return_value.brouter_url = "http://localhost:17777"
        mock_settings.return_value.ors_api_key = None

        mock_client = AsyncMock()
        mock_client.plan_route.return_value = _make_route()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_brouter_cls.return_value = mock_client

        result = await plan_route(
            start_lat=49.59, start_lon=11.00,
            end_lat=49.62, end_lon=11.03,
        )

        assert "BROUTER" in result
        assert "25.3" in result
        assert "450" in result
        assert "420" in result
        assert "GPX data: available" in result

    @patch("mtb_mcp.tools.routing_tools.ORSClient")
    @patch("mtb_mcp.tools.routing_tools.BRouterClient")
    @patch("mtb_mcp.tools.routing_tools.get_settings")
    async def test_falls_back_to_ors(
        self,
        mock_settings: AsyncMock,
        mock_brouter_cls: AsyncMock,
        mock_ors_cls: AsyncMock,
    ) -> None:
        """Should fall back to ORS when BRouter is unavailable."""
        mock_settings.return_value.brouter_url = "http://localhost:17777"
        mock_settings.return_value.ors_api_key = "test-key"

        # BRouter raises connection error
        mock_brouter = AsyncMock()
        mock_brouter.plan_route.side_effect = httpx.ConnectError("Connection refused")
        mock_brouter.__aenter__ = AsyncMock(return_value=mock_brouter)
        mock_brouter.__aexit__ = AsyncMock(return_value=False)
        mock_brouter_cls.return_value = mock_brouter

        # ORS succeeds
        mock_ors = AsyncMock()
        mock_ors.plan_route.return_value = _make_route(source="ors")
        mock_ors.__aenter__ = AsyncMock(return_value=mock_ors)
        mock_ors.__aexit__ = AsyncMock(return_value=False)
        mock_ors_cls.return_value = mock_ors

        result = await plan_route(
            start_lat=49.59, start_lon=11.00,
            end_lat=49.62, end_lon=11.03,
        )

        assert "ORS" in result
        assert "25.3" in result

    @patch("mtb_mcp.tools.routing_tools.BRouterClient")
    @patch("mtb_mcp.tools.routing_tools.get_settings")
    async def test_error_when_no_service(
        self, mock_settings: AsyncMock, mock_brouter_cls: AsyncMock
    ) -> None:
        """Should return error when both services are unavailable."""
        mock_settings.return_value.brouter_url = "http://localhost:17777"
        mock_settings.return_value.ors_api_key = None

        mock_brouter = AsyncMock()
        mock_brouter.plan_route.side_effect = httpx.ConnectError("Connection refused")
        mock_brouter.__aenter__ = AsyncMock(return_value=mock_brouter)
        mock_brouter.__aexit__ = AsyncMock(return_value=False)
        mock_brouter_cls.return_value = mock_brouter

        result = await plan_route(
            start_lat=49.59, start_lon=11.00,
            end_lat=49.62, end_lon=11.03,
        )

        assert "Error" in result
        assert "not available" in result

    @patch("mtb_mcp.tools.routing_tools.BRouterClient")
    @patch("mtb_mcp.tools.routing_tools.get_settings")
    async def test_passes_profile(
        self, mock_settings: AsyncMock, mock_brouter_cls: AsyncMock
    ) -> None:
        """Should pass the profile parameter to BRouter."""
        mock_settings.return_value.brouter_url = "http://localhost:17777"
        mock_settings.return_value.ors_api_key = None

        mock_client = AsyncMock()
        mock_client.plan_route.return_value = _make_route()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_brouter_cls.return_value = mock_client

        await plan_route(
            start_lat=49.59, start_lon=11.00,
            end_lat=49.62, end_lon=11.03,
            profile="trekking",
        )

        mock_client.plan_route.assert_called_once()
        call_kwargs = mock_client.plan_route.call_args
        assert call_kwargs.kwargs["profile"] == "trekking"


class TestPlanLoopRouteTool:
    """Tests for plan_loop_route tool."""

    @patch("mtb_mcp.tools.routing_tools.BRouterClient")
    @patch("mtb_mcp.tools.routing_tools.get_settings")
    async def test_plans_loop_route(
        self, mock_settings: AsyncMock, mock_brouter_cls: AsyncMock
    ) -> None:
        """Should plan loop route via BRouter."""
        mock_settings.return_value.brouter_url = "http://localhost:17777"

        mock_client = AsyncMock()
        mock_client.plan_loop_route.return_value = _make_route()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_brouter_cls.return_value = mock_client

        result = await plan_loop_route(
            start_lat=49.59, start_lon=11.00,
            distance_km=20.0,
        )

        assert "25.3" in result
        assert "BROUTER" in result

    @patch("mtb_mcp.tools.routing_tools.BRouterClient")
    @patch("mtb_mcp.tools.routing_tools.get_settings")
    async def test_uses_home_location(
        self, mock_settings: AsyncMock, mock_brouter_cls: AsyncMock
    ) -> None:
        """Should use home location when no start given."""
        mock_settings.return_value.home_lat = 49.59
        mock_settings.return_value.home_lon = 11.00
        mock_settings.return_value.brouter_url = "http://localhost:17777"

        mock_client = AsyncMock()
        mock_client.plan_loop_route.return_value = _make_route()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_brouter_cls.return_value = mock_client

        await plan_loop_route()

        mock_client.plan_loop_route.assert_called_once()
        call_args = mock_client.plan_loop_route.call_args
        start_point = call_args.args[0]
        assert start_point.lat == 49.59
        assert start_point.lon == 11.00

    @patch("mtb_mcp.tools.routing_tools.BRouterClient")
    @patch("mtb_mcp.tools.routing_tools.get_settings")
    async def test_error_when_brouter_down(
        self, mock_settings: AsyncMock, mock_brouter_cls: AsyncMock
    ) -> None:
        """Should return error when BRouter unavailable (no ORS loop support)."""
        mock_settings.return_value.brouter_url = "http://localhost:17777"

        mock_client = AsyncMock()
        mock_client.plan_loop_route.side_effect = httpx.ConnectError(
            "Connection refused"
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_brouter_cls.return_value = mock_client

        result = await plan_loop_route(start_lat=49.59, start_lon=11.00)

        assert "Error" in result
        assert "BRouter" in result


class TestRouteElevationProfileTool:
    """Tests for route_elevation_profile tool."""

    @patch("mtb_mcp.tools.routing_tools.BRouterClient")
    @patch("mtb_mcp.tools.routing_tools.get_settings")
    async def test_returns_elevation_profile(
        self, mock_settings: AsyncMock, mock_brouter_cls: AsyncMock
    ) -> None:
        """Should return formatted elevation profile from BRouter."""
        mock_settings.return_value.brouter_url = "http://localhost:17777"
        mock_settings.return_value.ors_api_key = None

        mock_client = AsyncMock()
        mock_client.get_elevation_profile.return_value = _make_elevation_profile()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_brouter_cls.return_value = mock_client

        result = await route_elevation_profile(
            start_lat=49.59, start_lon=11.00,
            end_lat=49.62, end_lon=11.03,
        )

        assert "Elevation Profile" in result
        assert "3.0" in result
        assert "310" in result
        assert "340" in result

    @patch("mtb_mcp.tools.routing_tools.ORSClient")
    @patch("mtb_mcp.tools.routing_tools.BRouterClient")
    @patch("mtb_mcp.tools.routing_tools.get_settings")
    async def test_falls_back_to_ors(
        self,
        mock_settings: AsyncMock,
        mock_brouter_cls: AsyncMock,
        mock_ors_cls: AsyncMock,
    ) -> None:
        """Should fall back to ORS route for elevation when BRouter unavailable."""
        mock_settings.return_value.brouter_url = "http://localhost:17777"
        mock_settings.return_value.ors_api_key = "test-key"

        # BRouter down
        mock_brouter = AsyncMock()
        mock_brouter.get_elevation_profile.side_effect = httpx.ConnectError(
            "Connection refused"
        )
        mock_brouter.__aenter__ = AsyncMock(return_value=mock_brouter)
        mock_brouter.__aexit__ = AsyncMock(return_value=False)
        mock_brouter_cls.return_value = mock_brouter

        # ORS succeeds
        mock_ors = AsyncMock()
        mock_ors.plan_route.return_value = _make_route(source="ors")
        mock_ors.__aenter__ = AsyncMock(return_value=mock_ors)
        mock_ors.__aexit__ = AsyncMock(return_value=False)
        mock_ors_cls.return_value = mock_ors

        result = await route_elevation_profile(
            start_lat=49.59, start_lon=11.00,
            end_lat=49.62, end_lon=11.03,
        )

        assert "ORS" in result

    @patch("mtb_mcp.tools.routing_tools.BRouterClient")
    @patch("mtb_mcp.tools.routing_tools.get_settings")
    async def test_error_when_no_service(
        self, mock_settings: AsyncMock, mock_brouter_cls: AsyncMock
    ) -> None:
        """Should return error when both services are unavailable."""
        mock_settings.return_value.brouter_url = "http://localhost:17777"
        mock_settings.return_value.ors_api_key = None

        mock_brouter = AsyncMock()
        mock_brouter.get_elevation_profile.side_effect = httpx.ConnectError(
            "Connection refused"
        )
        mock_brouter.__aenter__ = AsyncMock(return_value=mock_brouter)
        mock_brouter.__aexit__ = AsyncMock(return_value=False)
        mock_brouter_cls.return_value = mock_brouter

        result = await route_elevation_profile(
            start_lat=49.59, start_lon=11.00,
            end_lat=49.62, end_lon=11.03,
        )

        assert "Error" in result
        assert "not available" in result
