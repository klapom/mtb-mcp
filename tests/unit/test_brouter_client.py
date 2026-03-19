"""Tests for BRouter routing client."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest
import respx

from mtb_mcp.clients.brouter import BRouterClient, _build_route, _elevation_loss
from mtb_mcp.models.common import GeoPoint

FIXTURES = Path(__file__).parent.parent / "fixtures" / "api_responses"


def _load_gpx_fixture(name: str) -> str:
    """Load a GPX fixture file."""
    return (FIXTURES / name).read_text()


SAMPLE_GPX = _load_gpx_fixture("brouter_route.gpx")


class TestElevationLoss:
    """Tests for the _elevation_loss helper."""

    def test_calculates_loss(self) -> None:
        """Should sum only downhill segments."""
        points = [
            GeoPoint(lat=49.59, lon=11.00, ele=400.0),
            GeoPoint(lat=49.60, lon=11.01, ele=350.0),
            GeoPoint(lat=49.61, lon=11.02, ele=380.0),
            GeoPoint(lat=49.62, lon=11.03, ele=320.0),
        ]
        # Loss: 400→350 = 50, 380→320 = 60, total = 110
        assert _elevation_loss(points) == 110.0

    def test_no_loss_uphill_only(self) -> None:
        """Should return 0 for purely uphill."""
        points = [
            GeoPoint(lat=49.59, lon=11.00, ele=300.0),
            GeoPoint(lat=49.60, lon=11.01, ele=400.0),
            GeoPoint(lat=49.61, lon=11.02, ele=500.0),
        ]
        assert _elevation_loss(points) == 0.0

    def test_handles_none_elevation(self) -> None:
        """Should skip points without elevation."""
        points = [
            GeoPoint(lat=49.59, lon=11.00, ele=400.0),
            GeoPoint(lat=49.60, lon=11.01, ele=None),
            GeoPoint(lat=49.61, lon=11.02, ele=350.0),
        ]
        # 400→350 = 50 (skipping None)
        assert _elevation_loss(points) == 50.0


class TestBuildRoute:
    """Tests for _build_route helper."""

    def test_parses_gpx_into_route(self) -> None:
        """Should create a Route from GPX text."""
        route = _build_route(SAMPLE_GPX)
        assert route.summary.source == "brouter"
        assert route.summary.distance_km > 0
        assert route.summary.elevation_gain_m > 0
        assert route.summary.elevation_loss_m > 0
        assert route.summary.duration_minutes is not None
        assert route.summary.duration_minutes > 0
        assert len(route.points) == 7
        assert route.gpx == SAMPLE_GPX

    def test_elevation_gain_from_fixture(self) -> None:
        """Should calculate correct elevation gain from fixture."""
        route = _build_route(SAMPLE_GPX)
        # Points go 310→325→340→355→350→330→320
        # Gain: 15+15+15 = 45
        assert route.summary.elevation_gain_m == 45.0

    def test_elevation_loss_from_fixture(self) -> None:
        """Should calculate correct elevation loss from fixture."""
        route = _build_route(SAMPLE_GPX)
        # Points go 310→325→340→355→350→330→320
        # Loss: 5+20+10 = 35
        assert route.summary.elevation_loss_m == 35.0

    def test_custom_source(self) -> None:
        """Should respect custom source parameter."""
        route = _build_route(SAMPLE_GPX, source="test")
        assert route.summary.source == "test"


class TestBRouterClientPlanRoute:
    """Tests for BRouterClient.plan_route."""

    @respx.mock
    async def test_plans_simple_route(self) -> None:
        """Should request route from BRouter and parse GPX response."""
        respx.get("http://localhost:17777/brouter").mock(
            return_value=httpx.Response(200, text=SAMPLE_GPX)
        )

        async with BRouterClient() as client:
            route = await client.plan_route(
                start=GeoPoint(lat=49.59, lon=11.00),
                end=GeoPoint(lat=49.62, lon=11.03),
            )

        assert route.summary.source == "brouter"
        assert route.summary.distance_km > 0
        assert len(route.points) == 7

    @respx.mock
    async def test_uses_correct_params(self) -> None:
        """Should send correct lonlats and profile params."""
        route_mock = respx.get("http://localhost:17777/brouter").mock(
            return_value=httpx.Response(200, text=SAMPLE_GPX)
        )

        async with BRouterClient() as client:
            await client.plan_route(
                start=GeoPoint(lat=49.59, lon=11.00),
                end=GeoPoint(lat=49.62, lon=11.03),
                profile="trekking",
            )

        request = route_mock.calls[0].request
        params = request.url.params
        assert params["lonlats"] == "11.0,49.59|11.03,49.62"
        assert params["profile"] == "trekking"
        assert params["format"] == "gpx"

    @respx.mock
    async def test_via_points(self) -> None:
        """Should include via points in lonlats parameter."""
        route_mock = respx.get("http://localhost:17777/brouter").mock(
            return_value=httpx.Response(200, text=SAMPLE_GPX)
        )

        async with BRouterClient() as client:
            await client.plan_route(
                start=GeoPoint(lat=49.59, lon=11.00),
                end=GeoPoint(lat=49.62, lon=11.03),
                via_points=[GeoPoint(lat=49.60, lon=11.01)],
            )

        request = route_mock.calls[0].request
        lonlats = request.url.params["lonlats"]
        # Should contain 3 points: start, via, end
        parts = lonlats.split("|")
        assert len(parts) == 3
        assert parts[0] == "11.0,49.59"
        assert parts[1] == "11.01,49.6"
        assert parts[2] == "11.03,49.62"

    @respx.mock
    async def test_custom_base_url(self) -> None:
        """Should use custom base URL."""
        respx.get("http://brouter:8080/brouter").mock(
            return_value=httpx.Response(200, text=SAMPLE_GPX)
        )

        async with BRouterClient(base_url="http://brouter:8080") as client:
            route = await client.plan_route(
                start=GeoPoint(lat=49.59, lon=11.00),
                end=GeoPoint(lat=49.62, lon=11.03),
            )

        assert route.summary.source == "brouter"

    @respx.mock
    async def test_http_error_propagated(self) -> None:
        """Should propagate HTTP errors from BRouter."""
        respx.get("http://localhost:17777/brouter").mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )

        async with BRouterClient() as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.plan_route(
                    start=GeoPoint(lat=49.59, lon=11.00),
                    end=GeoPoint(lat=49.62, lon=11.03),
                )


class TestBRouterClientLoopRoute:
    """Tests for BRouterClient.plan_loop_route."""

    @respx.mock
    async def test_plans_loop_route(self) -> None:
        """Should plan a loop route returning to start."""
        route_mock = respx.get("http://localhost:17777/brouter").mock(
            return_value=httpx.Response(200, text=SAMPLE_GPX)
        )

        async with BRouterClient() as client:
            route = await client.plan_loop_route(
                start=GeoPoint(lat=49.59, lon=11.00),
                distance_km=20.0,
            )

        assert route.summary.source == "brouter"
        # Should have called BRouter with multiple waypoints
        request = route_mock.calls[0].request
        # Start and end should both be the same point (loop)
        lonlats_param = str(request.url.params.get("lonlats", ""))
        parts = lonlats_param.split("|")
        # Should have: start + 5 via points + end (= start) = 7 points
        assert len(parts) == 7

    @respx.mock
    async def test_loop_uses_profile(self) -> None:
        """Should pass profile parameter."""
        route_mock = respx.get("http://localhost:17777/brouter").mock(
            return_value=httpx.Response(200, text=SAMPLE_GPX)
        )

        async with BRouterClient() as client:
            await client.plan_loop_route(
                start=GeoPoint(lat=49.59, lon=11.00),
                distance_km=30.0,
                profile="trekking",
            )

        request = route_mock.calls[0].request
        assert "profile=trekking" in str(request.url)


class TestBRouterClientElevationProfile:
    """Tests for BRouterClient.get_elevation_profile."""

    @respx.mock
    async def test_gets_elevation_profile(self) -> None:
        """Should return elevation profile from BRouter route."""
        respx.get("http://localhost:17777/brouter").mock(
            return_value=httpx.Response(200, text=SAMPLE_GPX)
        )

        async with BRouterClient() as client:
            profile = await client.get_elevation_profile([
                GeoPoint(lat=49.59, lon=11.00),
                GeoPoint(lat=49.62, lon=11.03),
            ])

        assert profile.total_distance_km > 0
        assert profile.total_gain_m > 0
        assert profile.total_loss_m > 0
        assert profile.min_elevation_m == 310.0
        assert profile.max_elevation_m == 355.0
        assert len(profile.points) == 7

    @respx.mock
    async def test_profile_points_have_cumulative_distance(self) -> None:
        """Should have increasing cumulative distance."""
        respx.get("http://localhost:17777/brouter").mock(
            return_value=httpx.Response(200, text=SAMPLE_GPX)
        )

        async with BRouterClient() as client:
            profile = await client.get_elevation_profile([
                GeoPoint(lat=49.59, lon=11.00),
                GeoPoint(lat=49.62, lon=11.03),
            ])

        distances = [p.distance_km for p in profile.points]
        assert distances[0] == 0.0
        # Each subsequent distance should be >= previous
        for i in range(1, len(distances)):
            assert distances[i] >= distances[i - 1]

    async def test_requires_at_least_two_points(self) -> None:
        """Should raise ValueError with fewer than 2 points."""
        async with BRouterClient() as client:
            with pytest.raises(ValueError, match="at least 2 points"):
                await client.get_elevation_profile([
                    GeoPoint(lat=49.59, lon=11.00),
                ])
