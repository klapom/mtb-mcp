"""Tests for geographic utility functions."""

from __future__ import annotations

import pytest

from mtb_mcp.utils.geo import bbox_from_center, haversine, midpoint, validate_coordinates


class TestHaversine:
    """Tests for haversine distance calculation."""

    def test_erlangen_to_nuernberg(self) -> None:
        """Erlangen to Nuernberg is approximately 17 km."""
        # Erlangen Schlossplatz
        lat1, lon1 = 49.5964, 11.0042
        # Nuernberg Hauptmarkt
        lat2, lon2 = 49.4539, 11.0775

        distance = haversine(lat1, lon1, lat2, lon2)
        assert 15.0 < distance < 19.0, f"Expected ~17 km, got {distance:.1f} km"

    def test_same_point_zero_distance(self) -> None:
        """Distance from a point to itself should be zero."""
        assert haversine(49.59, 11.00, 49.59, 11.00) == pytest.approx(0.0)

    def test_symmetric(self) -> None:
        """Distance A->B should equal B->A."""
        d1 = haversine(49.59, 11.00, 48.14, 11.58)
        d2 = haversine(48.14, 11.58, 49.59, 11.00)
        assert d1 == pytest.approx(d2)

    def test_equator_one_degree(self) -> None:
        """One degree of longitude at equator is about 111.2 km."""
        distance = haversine(0.0, 0.0, 0.0, 1.0)
        assert 110.0 < distance < 112.0

    def test_poles(self) -> None:
        """North pole to south pole is about half the circumference (~20015 km)."""
        distance = haversine(90.0, 0.0, -90.0, 0.0)
        assert 20000.0 < distance < 20100.0


class TestBboxFromCenter:
    """Tests for bounding box creation from center + radius."""

    def test_creates_valid_bbox(self) -> None:
        """Bounding box should have south < north and west < east."""
        south, west, north, east = bbox_from_center(49.59, 11.00, 10.0)
        assert south < north
        assert west < east

    def test_center_inside_bbox(self) -> None:
        """Center point should be inside the bounding box."""
        lat, lon = 49.59, 11.00
        south, west, north, east = bbox_from_center(lat, lon, 5.0)
        assert south < lat < north
        assert west < lon < east

    def test_small_radius(self) -> None:
        """A 1km radius bbox should be small."""
        south, west, north, east = bbox_from_center(49.59, 11.00, 1.0)
        # ~1 km radius means lat spread is about 0.009 degrees each way
        assert (north - south) < 0.05
        assert (east - west) < 0.05

    def test_large_radius(self) -> None:
        """A 50km radius bbox should be reasonably large."""
        south, west, north, east = bbox_from_center(49.59, 11.00, 50.0)
        # ~50 km radius means lat spread is about 0.45 degrees each way
        assert (north - south) > 0.5
        assert (east - west) > 0.5

    def test_distances_match_radius(self) -> None:
        """Distance from center to edge should approximate the radius."""
        lat, lon, radius = 49.59, 11.00, 10.0
        south, west, north, east = bbox_from_center(lat, lon, radius)

        # Distance from center to north edge
        dist_north = haversine(lat, lon, north, lon)
        assert dist_north == pytest.approx(radius, rel=0.05)


class TestValidateCoordinates:
    """Tests for coordinate validation."""

    @pytest.mark.parametrize(
        ("lat", "lon"),
        [
            (0.0, 0.0),
            (49.59, 11.00),
            (90.0, 180.0),
            (-90.0, -180.0),
            (90.0, -180.0),
            (-90.0, 180.0),
        ],
    )
    def test_valid_coordinates(self, lat: float, lon: float) -> None:
        """Valid coordinates should return True."""
        assert validate_coordinates(lat, lon) is True

    @pytest.mark.parametrize(
        ("lat", "lon"),
        [
            (91.0, 0.0),
            (-91.0, 0.0),
            (0.0, 181.0),
            (0.0, -181.0),
            (100.0, 200.0),
        ],
    )
    def test_invalid_coordinates(self, lat: float, lon: float) -> None:
        """Invalid coordinates should return False."""
        assert validate_coordinates(lat, lon) is False

    def test_boundary_values(self) -> None:
        """Boundary values should be valid."""
        assert validate_coordinates(90.0, 180.0) is True
        assert validate_coordinates(-90.0, -180.0) is True


class TestMidpoint:
    """Tests for geographic midpoint calculation."""

    def test_same_point(self) -> None:
        """Midpoint of a point with itself should be the same point."""
        lat, lon = 49.59, 11.00
        mid_lat, mid_lon = midpoint(lat, lon, lat, lon)
        assert mid_lat == pytest.approx(lat, abs=1e-6)
        assert mid_lon == pytest.approx(lon, abs=1e-6)

    def test_symmetric(self) -> None:
        """Midpoint(A, B) should equal Midpoint(B, A)."""
        m1 = midpoint(49.59, 11.00, 48.14, 11.58)
        m2 = midpoint(48.14, 11.58, 49.59, 11.00)
        assert m1[0] == pytest.approx(m2[0], abs=1e-6)
        assert m1[1] == pytest.approx(m2[1], abs=1e-6)

    def test_equator(self) -> None:
        """Midpoint along the equator should be at the equator."""
        mid_lat, mid_lon = midpoint(0.0, 0.0, 0.0, 10.0)
        assert mid_lat == pytest.approx(0.0, abs=1e-6)
        assert mid_lon == pytest.approx(5.0, abs=1e-6)

    def test_erlangen_nuernberg_midpoint(self) -> None:
        """Midpoint between Erlangen and Nuernberg should be roughly between them."""
        mid_lat, mid_lon = midpoint(49.5964, 11.0042, 49.4539, 11.0775)
        # Should be between the two latitudes
        assert 49.45 < mid_lat < 49.60
        # Should be between the two longitudes
        assert 11.00 < mid_lon < 11.08
