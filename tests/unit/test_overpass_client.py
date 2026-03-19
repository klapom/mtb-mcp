"""Tests for OSM Overpass API client."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from mtb_mcp.clients.overpass import (
    OverpassClient,
    _calculate_length,
    _parse_mtb_scale,
    _parse_surface,
)
from mtb_mcp.models.trail import MTBScale, TrailSurface

FIXTURES = Path(__file__).parent.parent / "fixtures" / "api_responses"


def _load_fixture(name: str) -> dict[str, object]:
    """Load a JSON fixture file."""
    with open(FIXTURES / name) as f:
        result: dict[str, object] = json.load(f)
        return result


class TestParseSurface:
    """Tests for surface tag parsing."""

    def test_known_surfaces(self) -> None:
        """Should map known OSM surface values."""
        assert _parse_surface("asphalt") == TrailSurface.asphalt
        assert _parse_surface("gravel") == TrailSurface.gravel
        assert _parse_surface("ground") == TrailSurface.dirt
        assert _parse_surface("rock") == TrailSurface.rock
        assert _parse_surface("grass") == TrailSurface.grass

    def test_case_insensitive(self) -> None:
        """Should handle case differences."""
        assert _parse_surface("Asphalt") == TrailSurface.asphalt
        assert _parse_surface("GRAVEL") == TrailSurface.gravel

    def test_unknown_surface(self) -> None:
        """Should return None for unknown surfaces."""
        assert _parse_surface("rubber") is None

    def test_none_input(self) -> None:
        """Should return None for None input."""
        assert _parse_surface(None) is None


class TestParseMTBScale:
    """Tests for mtb:scale tag parsing."""

    def test_integer_scales(self) -> None:
        """Should parse integer scale values."""
        assert _parse_mtb_scale("0") == MTBScale.S0
        assert _parse_mtb_scale("1") == MTBScale.S1
        assert _parse_mtb_scale("2") == MTBScale.S2
        assert _parse_mtb_scale("3") == MTBScale.S3
        assert _parse_mtb_scale("4") == MTBScale.S4
        assert _parse_mtb_scale("5") == MTBScale.S5
        assert _parse_mtb_scale("6") == MTBScale.S6

    def test_plus_minus_variants(self) -> None:
        """Should handle +/- variants (e.g., '2+', '3-')."""
        assert _parse_mtb_scale("2+") == MTBScale.S2
        assert _parse_mtb_scale("3-") == MTBScale.S3
        assert _parse_mtb_scale("0+") == MTBScale.S0

    def test_none_input(self) -> None:
        """Should return None for None input."""
        assert _parse_mtb_scale(None) is None

    def test_invalid_value(self) -> None:
        """Should return None for invalid scale value."""
        assert _parse_mtb_scale("7") is None
        assert _parse_mtb_scale("easy") is None


class TestCalculateLength:
    """Tests for geometry length calculation."""

    def test_two_points(self) -> None:
        """Should calculate distance between two points."""
        # Approx 100m apart
        geometry = [
            {"lat": 49.5960, "lon": 11.0040},
            {"lat": 49.5970, "lon": 11.0040},
        ]
        length = _calculate_length(geometry)
        # ~111m per degree of latitude, 0.001 degrees
        assert 100 < length < 120

    def test_empty_geometry(self) -> None:
        """Should return 0 for empty geometry."""
        assert _calculate_length([]) == 0.0

    def test_single_point(self) -> None:
        """Should return 0 for single point."""
        assert _calculate_length([{"lat": 49.0, "lon": 11.0}]) == 0.0


class TestOverpassClientFindTrails:
    """Tests for OverpassClient.find_trails."""

    @respx.mock
    async def test_find_trails(self) -> None:
        """Should parse Overpass response into Trail objects."""
        fixture = _load_fixture("overpass_trails.json")
        respx.post("https://overpass-api.de/api/interpreter").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with OverpassClient() as client:
            trails = await client.find_trails(49.59, 11.00)

        assert len(trails) == 3

    @respx.mock
    async def test_trail_properties(self) -> None:
        """Should correctly parse trail properties."""
        fixture = _load_fixture("overpass_trails.json")
        respx.post("https://overpass-api.de/api/interpreter").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with OverpassClient() as client:
            trails = await client.find_trails(49.59, 11.00)

        # Find the named trail
        named_trails = [t for t in trails if t.name == "Tiergarten Singletrail"]
        assert len(named_trails) == 1
        trail = named_trails[0]

        assert trail.osm_id == 12345678
        assert trail.mtb_scale == MTBScale.S2
        assert trail.surface == TrailSurface.dirt
        assert trail.length_m is not None
        assert trail.length_m > 0
        assert len(trail.geometry) == 4

    @respx.mock
    async def test_filter_by_min_scale(self) -> None:
        """Should filter trails by minimum difficulty."""
        fixture = _load_fixture("overpass_trails.json")
        respx.post("https://overpass-api.de/api/interpreter").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with OverpassClient() as client:
            trails = await client.find_trails(49.59, 11.00, min_scale=MTBScale.S2)

        # Only S2 and S3 trails should remain (not S1)
        assert len(trails) == 2
        for trail in trails:
            assert trail.mtb_scale is not None
            assert trail.mtb_scale.value in ("S2", "S3")

    @respx.mock
    async def test_sorted_by_name(self) -> None:
        """Named trails should come before unnamed ones."""
        fixture = _load_fixture("overpass_trails.json")
        respx.post("https://overpass-api.de/api/interpreter").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with OverpassClient() as client:
            trails = await client.find_trails(49.59, 11.00)

        # Named trails first, unnamed last
        named_count = sum(1 for t in trails if t.name is not None)
        for i in range(named_count):
            assert trails[i].name is not None
        for i in range(named_count, len(trails)):
            assert trails[i].name is None

    @respx.mock
    async def test_no_results(self) -> None:
        """Should return empty list when no trails found."""
        fixture = _load_fixture("overpass_empty.json")
        respx.post("https://overpass-api.de/api/interpreter").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with OverpassClient() as client:
            trails = await client.find_trails(49.59, 11.00)

        assert trails == []


class TestOverpassClientTrailDetails:
    """Tests for OverpassClient.get_trail_details."""

    @respx.mock
    async def test_get_trail_details(self) -> None:
        """Should return Trail for a valid OSM ID."""
        fixture = _load_fixture("overpass_trail_detail.json")
        respx.post("https://overpass-api.de/api/interpreter").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with OverpassClient() as client:
            trail = await client.get_trail_details(12345678)

        assert trail is not None
        assert trail.osm_id == 12345678
        assert trail.name == "Tiergarten Singletrail"
        assert trail.mtb_scale == MTBScale.S2

    @respx.mock
    async def test_trail_not_found(self) -> None:
        """Should return None for non-existent OSM ID."""
        fixture = _load_fixture("overpass_empty.json")
        respx.post("https://overpass-api.de/api/interpreter").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with OverpassClient() as client:
            trail = await client.get_trail_details(99999999)

        assert trail is None


class TestOverpassClientErrorHandling:
    """Tests for error handling."""

    @respx.mock
    async def test_api_error_propagated(self) -> None:
        """HTTP errors from Overpass should propagate."""
        respx.post("https://overpass-api.de/api/interpreter").mock(
            return_value=httpx.Response(429, text="Too many requests")
        )

        async with OverpassClient() as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.find_trails(49.59, 11.00)
