"""Tests for route data models."""

from __future__ import annotations

from mtb_mcp.models.common import GeoPoint
from mtb_mcp.models.route import (
    ElevationPoint,
    ElevationProfile,
    Route,
    RouteSegment,
    RouteSummary,
)


class TestRouteSummary:
    """Tests for RouteSummary model."""

    def test_create_brouter_summary(self) -> None:
        """Should create summary with brouter source."""
        summary = RouteSummary(
            distance_km=25.3,
            elevation_gain_m=450.0,
            elevation_loss_m=420.0,
            duration_minutes=135.0,
            source="brouter",
        )
        assert summary.distance_km == 25.3
        assert summary.elevation_gain_m == 450.0
        assert summary.elevation_loss_m == 420.0
        assert summary.duration_minutes == 135.0
        assert summary.source == "brouter"

    def test_create_ors_summary(self) -> None:
        """Should create summary with ors source."""
        summary = RouteSummary(
            distance_km=18.5,
            elevation_gain_m=300.0,
            elevation_loss_m=310.0,
            source="ors",
        )
        assert summary.source == "ors"
        assert summary.duration_minutes is None

    def test_optional_duration(self) -> None:
        """Duration should be optional."""
        summary = RouteSummary(
            distance_km=10.0,
            elevation_gain_m=100.0,
            elevation_loss_m=100.0,
            source="brouter",
        )
        assert summary.duration_minutes is None


class TestRouteSegment:
    """Tests for RouteSegment model."""

    def test_create_segment(self) -> None:
        """Should create a route segment with all fields."""
        segment = RouteSegment(
            points=[
                GeoPoint(lat=49.59, lon=11.00, ele=310.0),
                GeoPoint(lat=49.60, lon=11.01, ele=340.0),
            ],
            distance_m=1500.0,
            elevation_gain_m=30.0,
            elevation_loss_m=0.0,
            surface="gravel",
        )
        assert len(segment.points) == 2
        assert segment.distance_m == 1500.0
        assert segment.surface == "gravel"

    def test_optional_surface(self) -> None:
        """Surface should be optional."""
        segment = RouteSegment(
            points=[GeoPoint(lat=49.59, lon=11.00)],
            distance_m=500.0,
            elevation_gain_m=10.0,
            elevation_loss_m=5.0,
        )
        assert segment.surface is None


class TestRoute:
    """Tests for Route model."""

    def test_create_route_minimal(self) -> None:
        """Should create route with just summary and points."""
        route = Route(
            summary=RouteSummary(
                distance_km=10.0,
                elevation_gain_m=200.0,
                elevation_loss_m=180.0,
                source="brouter",
            ),
            points=[
                GeoPoint(lat=49.59, lon=11.00, ele=310.0),
                GeoPoint(lat=49.60, lon=11.01, ele=340.0),
            ],
        )
        assert route.summary.distance_km == 10.0
        assert len(route.points) == 2
        assert route.segments == []
        assert route.gpx is None

    def test_create_route_with_gpx(self) -> None:
        """Should store GPX XML data."""
        route = Route(
            summary=RouteSummary(
                distance_km=10.0,
                elevation_gain_m=200.0,
                elevation_loss_m=180.0,
                source="brouter",
            ),
            points=[GeoPoint(lat=49.59, lon=11.00)],
            gpx="<gpx>...</gpx>",
        )
        assert route.gpx == "<gpx>...</gpx>"

    def test_default_segments(self) -> None:
        """Segments should default to empty list."""
        route = Route(
            summary=RouteSummary(
                distance_km=5.0,
                elevation_gain_m=50.0,
                elevation_loss_m=50.0,
                source="ors",
            ),
            points=[],
        )
        assert route.segments == []


class TestElevationPoint:
    """Tests for ElevationPoint model."""

    def test_create_point(self) -> None:
        """Should create elevation point."""
        pt = ElevationPoint(distance_km=5.2, elevation_m=450.0)
        assert pt.distance_km == 5.2
        assert pt.elevation_m == 450.0


class TestElevationProfile:
    """Tests for ElevationProfile model."""

    def test_create_profile(self) -> None:
        """Should create a complete elevation profile."""
        profile = ElevationProfile(
            points=[
                ElevationPoint(distance_km=0.0, elevation_m=310.0),
                ElevationPoint(distance_km=2.5, elevation_m=450.0),
                ElevationPoint(distance_km=5.0, elevation_m=380.0),
            ],
            total_distance_km=5.0,
            total_gain_m=140.0,
            total_loss_m=70.0,
            min_elevation_m=310.0,
            max_elevation_m=450.0,
        )
        assert len(profile.points) == 3
        assert profile.total_distance_km == 5.0
        assert profile.total_gain_m == 140.0
        assert profile.total_loss_m == 70.0
        assert profile.min_elevation_m == 310.0
        assert profile.max_elevation_m == 450.0

    def test_flat_profile(self) -> None:
        """Should handle flat terrain with no gain/loss."""
        profile = ElevationProfile(
            points=[
                ElevationPoint(distance_km=0.0, elevation_m=200.0),
                ElevationPoint(distance_km=10.0, elevation_m=200.0),
            ],
            total_distance_km=10.0,
            total_gain_m=0.0,
            total_loss_m=0.0,
            min_elevation_m=200.0,
            max_elevation_m=200.0,
        )
        assert profile.total_gain_m == 0.0
        assert profile.total_loss_m == 0.0
