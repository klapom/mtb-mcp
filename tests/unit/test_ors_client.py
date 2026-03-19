"""Tests for OpenRouteService (ORS) API client."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from mtb_mcp.clients.ors import ORSClient
from mtb_mcp.models.common import GeoPoint

FIXTURES = Path(__file__).parent.parent / "fixtures" / "api_responses"


def _load_json_fixture(name: str) -> dict[str, object]:
    """Load a JSON fixture file."""
    with open(FIXTURES / name) as f:
        result: dict[str, object] = json.load(f)
        return result


ORS_FIXTURE = _load_json_fixture("ors_directions.json")


class TestORSClientPlanRoute:
    """Tests for ORSClient.plan_route."""

    @respx.mock
    async def test_plans_route(self) -> None:
        """Should request route from ORS and parse GeoJSON response."""
        respx.post(
            "https://api.openrouteservice.org/v2/directions/cycling-mountain/geojson"
        ).mock(return_value=httpx.Response(200, json=ORS_FIXTURE))

        async with ORSClient(api_key="test-key") as client:
            route = await client.plan_route(
                start=GeoPoint(lat=49.59, lon=11.00),
                end=GeoPoint(lat=49.62, lon=11.03),
            )

        assert route.summary.source == "ors"
        assert route.summary.distance_km == 4.2
        assert route.summary.duration_minutes == 21.0
        assert len(route.points) == 7

    @respx.mock
    async def test_parses_elevation(self) -> None:
        """Should extract elevation from ORS coordinates."""
        respx.post(
            "https://api.openrouteservice.org/v2/directions/cycling-mountain/geojson"
        ).mock(return_value=httpx.Response(200, json=ORS_FIXTURE))

        async with ORSClient(api_key="test-key") as client:
            route = await client.plan_route(
                start=GeoPoint(lat=49.59, lon=11.00),
                end=GeoPoint(lat=49.62, lon=11.03),
            )

        # First point elevation should be 310.0
        assert route.points[0].ele == 310.0
        # Elevation gain: 15+15+15 = 45
        assert route.summary.elevation_gain_m == 45.0
        # Elevation loss: 5+20+10 = 35
        assert route.summary.elevation_loss_m == 35.0

    @respx.mock
    async def test_sends_auth_header(self) -> None:
        """Should include API key in Authorization header."""
        route_mock = respx.post(
            "https://api.openrouteservice.org/v2/directions/cycling-mountain/geojson"
        ).mock(return_value=httpx.Response(200, json=ORS_FIXTURE))

        async with ORSClient(api_key="my-secret-key") as client:
            await client.plan_route(
                start=GeoPoint(lat=49.59, lon=11.00),
                end=GeoPoint(lat=49.62, lon=11.03),
            )

        request = route_mock.calls[0].request
        assert request.headers.get("Authorization") == "my-secret-key"

    @respx.mock
    async def test_sends_correct_body(self) -> None:
        """Should send coordinates in [lon, lat] format."""
        route_mock = respx.post(
            "https://api.openrouteservice.org/v2/directions/cycling-mountain/geojson"
        ).mock(return_value=httpx.Response(200, json=ORS_FIXTURE))

        async with ORSClient(api_key="test-key") as client:
            await client.plan_route(
                start=GeoPoint(lat=49.59, lon=11.00),
                end=GeoPoint(lat=49.62, lon=11.03),
            )

        request = route_mock.calls[0].request
        body = json.loads(request.content)
        assert body["coordinates"] == [[11.00, 49.59], [11.03, 49.62]]
        assert body["elevation"] is True

    async def test_requires_api_key(self) -> None:
        """Should raise ValueError when no API key provided."""
        async with ORSClient(api_key=None) as client:
            with pytest.raises(ValueError, match="API key is required"):
                await client.plan_route(
                    start=GeoPoint(lat=49.59, lon=11.00),
                    end=GeoPoint(lat=49.62, lon=11.03),
                )

    @respx.mock
    async def test_empty_features_raises(self) -> None:
        """Should raise ValueError when ORS returns no features."""
        respx.post(
            "https://api.openrouteservice.org/v2/directions/cycling-mountain/geojson"
        ).mock(
            return_value=httpx.Response(
                200, json={"type": "FeatureCollection", "features": []}
            )
        )

        async with ORSClient(api_key="test-key") as client:
            with pytest.raises(ValueError, match="No route features"):
                await client.plan_route(
                    start=GeoPoint(lat=49.59, lon=11.00),
                    end=GeoPoint(lat=49.62, lon=11.03),
                )

    @respx.mock
    async def test_http_error_propagated(self) -> None:
        """Should propagate HTTP errors from ORS."""
        respx.post(
            "https://api.openrouteservice.org/v2/directions/cycling-mountain/geojson"
        ).mock(
            return_value=httpx.Response(
                403, json={"error": {"code": 403, "message": "Forbidden"}}
            )
        )

        async with ORSClient(api_key="bad-key") as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.plan_route(
                    start=GeoPoint(lat=49.59, lon=11.00),
                    end=GeoPoint(lat=49.62, lon=11.03),
                )


class TestORSClientIsAvailable:
    """Tests for ORSClient.is_available."""

    async def test_unavailable_without_key(self) -> None:
        """Should return False when no API key configured."""
        async with ORSClient(api_key=None) as client:
            assert await client.is_available() is False

    @respx.mock
    async def test_available_with_key_and_service(self) -> None:
        """Should return True when API key is set and service responds."""
        respx.get("https://api.openrouteservice.org/v2/health").mock(
            return_value=httpx.Response(200, json={"status": "ready"})
        )

        async with ORSClient(api_key="test-key") as client:
            assert await client.is_available() is True

    @respx.mock
    async def test_unavailable_on_connection_error(self) -> None:
        """Should return False on connection error."""
        respx.get("https://api.openrouteservice.org/v2/health").mock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        async with ORSClient(api_key="test-key") as client:
            assert await client.is_available() is False
