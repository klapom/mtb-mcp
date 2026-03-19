"""Tests for common data models."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from mtb_mcp.models.common import BoundingBox, DateRange, GeoPoint


class TestGeoPoint:
    """Tests for GeoPoint model."""

    def test_valid_point(self) -> None:
        """Should accept valid coordinates."""
        pt = GeoPoint(lat=49.5964, lon=11.0042, ele=280.0)
        assert pt.lat == 49.5964
        assert pt.lon == 11.0042
        assert pt.ele == 280.0

    def test_without_elevation(self) -> None:
        """Elevation should be optional (None)."""
        pt = GeoPoint(lat=49.59, lon=11.00)
        assert pt.ele is None

    def test_boundary_lat(self) -> None:
        """Should accept boundary latitude values."""
        assert GeoPoint(lat=90.0, lon=0.0).lat == 90.0
        assert GeoPoint(lat=-90.0, lon=0.0).lat == -90.0

    def test_boundary_lon(self) -> None:
        """Should accept boundary longitude values."""
        assert GeoPoint(lat=0.0, lon=180.0).lon == 180.0
        assert GeoPoint(lat=0.0, lon=-180.0).lon == -180.0

    def test_invalid_lat_too_high(self) -> None:
        """Should reject latitude > 90."""
        with pytest.raises(ValidationError):
            GeoPoint(lat=91.0, lon=0.0)

    def test_invalid_lat_too_low(self) -> None:
        """Should reject latitude < -90."""
        with pytest.raises(ValidationError):
            GeoPoint(lat=-91.0, lon=0.0)

    def test_invalid_lon_too_high(self) -> None:
        """Should reject longitude > 180."""
        with pytest.raises(ValidationError):
            GeoPoint(lat=0.0, lon=181.0)

    def test_invalid_lon_too_low(self) -> None:
        """Should reject longitude < -180."""
        with pytest.raises(ValidationError):
            GeoPoint(lat=0.0, lon=-181.0)

    def test_zero_coordinates(self) -> None:
        """Should accept (0, 0) — null island."""
        pt = GeoPoint(lat=0.0, lon=0.0)
        assert pt.lat == 0.0
        assert pt.lon == 0.0

    def test_serialization(self) -> None:
        """Should serialize to dict correctly."""
        pt = GeoPoint(lat=49.59, lon=11.00, ele=300.0)
        data = pt.model_dump()
        assert data == {"lat": 49.59, "lon": 11.00, "ele": 300.0}

    def test_serialization_without_elevation(self) -> None:
        """Should serialize with None elevation."""
        pt = GeoPoint(lat=49.59, lon=11.00)
        data = pt.model_dump()
        assert data == {"lat": 49.59, "lon": 11.00, "ele": None}


class TestBoundingBox:
    """Tests for BoundingBox model."""

    def test_valid_bbox(self) -> None:
        """Should accept a valid bounding box."""
        bb = BoundingBox(south=49.0, west=10.5, north=50.0, east=11.5)
        assert bb.south == 49.0
        assert bb.north == 50.0

    def test_equal_south_north(self) -> None:
        """Should accept south == north (degenerate line)."""
        bb = BoundingBox(south=49.0, west=10.0, north=49.0, east=11.0)
        assert bb.south == bb.north

    def test_south_greater_than_north_fails(self) -> None:
        """Should reject south > north."""
        with pytest.raises(ValidationError, match="south"):
            BoundingBox(south=50.0, west=10.0, north=49.0, east=11.0)

    def test_invalid_lat_fails(self) -> None:
        """Should reject out-of-range latitude."""
        with pytest.raises(ValidationError):
            BoundingBox(south=-91.0, west=0.0, north=0.0, east=1.0)

    def test_invalid_lon_fails(self) -> None:
        """Should reject out-of-range longitude."""
        with pytest.raises(ValidationError):
            BoundingBox(south=0.0, west=-181.0, north=1.0, east=0.0)

    def test_serialization(self) -> None:
        """Should serialize to dict correctly."""
        bb = BoundingBox(south=49.0, west=10.5, north=50.0, east=11.5)
        data = bb.model_dump()
        assert data == {"south": 49.0, "west": 10.5, "north": 50.0, "east": 11.5}


class TestDateRange:
    """Tests for DateRange model."""

    def test_valid_range(self) -> None:
        """Should accept a valid date range."""
        dr = DateRange(start=date(2024, 6, 1), end=date(2024, 6, 30))
        assert dr.start == date(2024, 6, 1)
        assert dr.end == date(2024, 6, 30)

    def test_same_day(self) -> None:
        """Should accept start == end (single day)."""
        d = date(2024, 7, 15)
        dr = DateRange(start=d, end=d)
        assert dr.start == dr.end

    def test_start_after_end_fails(self) -> None:
        """Should reject start > end."""
        with pytest.raises(ValidationError, match="start"):
            DateRange(start=date(2024, 7, 1), end=date(2024, 6, 1))

    def test_serialization(self) -> None:
        """Should serialize to dict correctly."""
        dr = DateRange(start=date(2024, 1, 1), end=date(2024, 12, 31))
        data = dr.model_dump()
        assert data == {"start": date(2024, 1, 1), "end": date(2024, 12, 31)}
