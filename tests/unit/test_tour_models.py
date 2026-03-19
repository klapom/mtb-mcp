"""Tests for tour data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mtb_mcp.models.common import GeoPoint
from mtb_mcp.models.tour import (
    TourDetail,
    TourDifficulty,
    TourSearchParams,
    TourSource,
    TourSummary,
)


class TestTourSource:
    """Tests for TourSource enum."""

    def test_enum_values(self) -> None:
        """Should have expected source values."""
        assert TourSource.komoot.value == "komoot"
        assert TourSource.gps_tour.value == "gps_tour"
        assert TourSource.mtb_project.value == "mtb_project"

    def test_string_conversion(self) -> None:
        """Should convert from string."""
        assert TourSource("komoot") == TourSource.komoot
        assert TourSource("gps_tour") == TourSource.gps_tour

    def test_invalid_source(self) -> None:
        """Should reject invalid source."""
        with pytest.raises(ValueError):
            TourSource("invalid")


class TestTourDifficulty:
    """Tests for TourDifficulty enum."""

    def test_enum_values(self) -> None:
        """Should have expected difficulty values."""
        assert TourDifficulty.easy.value == "easy"
        assert TourDifficulty.moderate.value == "moderate"
        assert TourDifficulty.difficult.value == "difficult"
        assert TourDifficulty.expert.value == "expert"

    def test_string_conversion(self) -> None:
        """Should convert from string."""
        assert TourDifficulty("easy") == TourDifficulty.easy
        assert TourDifficulty("expert") == TourDifficulty.expert

    def test_invalid_difficulty(self) -> None:
        """Should reject invalid difficulty."""
        with pytest.raises(ValueError):
            TourDifficulty("impossible")


class TestTourSummary:
    """Tests for TourSummary model."""

    def test_minimal_summary(self) -> None:
        """Should create with required fields only."""
        ts = TourSummary(id="123", source=TourSource.komoot, name="Test Tour")
        assert ts.id == "123"
        assert ts.source == TourSource.komoot
        assert ts.name == "Test Tour"
        assert ts.distance_km is None
        assert ts.elevation_m is None
        assert ts.difficulty is None
        assert ts.region is None
        assert ts.url is None
        assert ts.start_point is None

    def test_full_summary(self) -> None:
        """Should accept all optional fields."""
        ts = TourSummary(
            id="456",
            source=TourSource.gps_tour,
            name="Erlangen Loop",
            distance_km=32.5,
            elevation_m=450.0,
            difficulty=TourDifficulty.moderate,
            region="Mittelfranken",
            url="https://www.gps-tour.info/de/touren/detail.456.html",
            start_point=GeoPoint(lat=49.596, lon=11.004),
        )
        assert ts.distance_km == 32.5
        assert ts.elevation_m == 450.0
        assert ts.difficulty == TourDifficulty.moderate
        assert ts.region == "Mittelfranken"
        assert ts.start_point is not None
        assert ts.start_point.lat == 49.596

    def test_serialization(self) -> None:
        """Should serialize to dict correctly."""
        ts = TourSummary(
            id="789",
            source=TourSource.komoot,
            name="Test",
            distance_km=10.0,
        )
        data = ts.model_dump()
        assert data["id"] == "789"
        assert data["source"] == "komoot"
        assert data["distance_km"] == 10.0

    def test_missing_required_fields(self) -> None:
        """Should require id, source, and name."""
        with pytest.raises(ValidationError):
            TourSummary(id="1", source=TourSource.komoot)  # type: ignore[call-arg]


class TestTourDetail:
    """Tests for TourDetail model."""

    def test_inherits_summary_fields(self) -> None:
        """TourDetail should include all TourSummary fields."""
        td = TourDetail(
            id="100",
            source=TourSource.komoot,
            name="Detail Tour",
            distance_km=25.0,
            description="A great tour",
        )
        assert td.id == "100"
        assert td.name == "Detail Tour"
        assert td.description == "A great tour"

    def test_default_lists(self) -> None:
        """Should have empty lists by default."""
        td = TourDetail(id="101", source=TourSource.gps_tour, name="Test")
        assert td.surfaces == []
        assert td.waypoints == []

    def test_full_detail(self) -> None:
        """Should accept all detail fields."""
        td = TourDetail(
            id="102",
            source=TourSource.komoot,
            name="Full Detail Tour",
            distance_km=32.5,
            elevation_m=450.0,
            difficulty=TourDifficulty.moderate,
            description="Beautiful loop through forests",
            duration_minutes=120,
            surfaces=["gravel", "singletrack", "asphalt"],
            waypoints=[
                GeoPoint(lat=49.596, lon=11.004, ele=280.0),
                GeoPoint(lat=49.598, lon=11.010, ele=310.0),
            ],
            download_count=142,
            rating=4.5,
        )
        assert td.duration_minutes == 120
        assert len(td.surfaces) == 3
        assert len(td.waypoints) == 2
        assert td.download_count == 142
        assert td.rating == 4.5

    def test_serialization(self) -> None:
        """Should serialize with both summary and detail fields."""
        td = TourDetail(
            id="103",
            source=TourSource.komoot,
            name="Serialization Test",
            surfaces=["gravel"],
            rating=3.8,
        )
        data = td.model_dump()
        assert "surfaces" in data
        assert "rating" in data
        assert "source" in data
        assert data["surfaces"] == ["gravel"]


class TestTourSearchParams:
    """Tests for TourSearchParams model."""

    def test_minimal_params(self) -> None:
        """Should create with just coordinates."""
        params = TourSearchParams(lat=49.59, lon=11.00)
        assert params.lat == 49.59
        assert params.lon == 11.00
        assert params.radius_km == 30.0
        assert params.sport_type == "mtb"
        assert params.min_distance_km is None
        assert params.max_distance_km is None
        assert params.difficulty is None

    def test_default_sources(self) -> None:
        """Should default to Komoot and GPS-Tour.info sources."""
        params = TourSearchParams(lat=49.59, lon=11.00)
        assert TourSource.komoot in params.sources
        assert TourSource.gps_tour in params.sources
        assert len(params.sources) == 2

    def test_custom_params(self) -> None:
        """Should accept all custom parameters."""
        params = TourSearchParams(
            lat=49.59,
            lon=11.00,
            radius_km=50.0,
            min_distance_km=10.0,
            max_distance_km=60.0,
            difficulty=TourDifficulty.difficult,
            sport_type="gravel",
            sources=[TourSource.komoot],
        )
        assert params.radius_km == 50.0
        assert params.min_distance_km == 10.0
        assert params.max_distance_km == 60.0
        assert params.difficulty == TourDifficulty.difficult
        assert params.sport_type == "gravel"
        assert len(params.sources) == 1

    def test_serialization(self) -> None:
        """Should serialize to dict correctly."""
        params = TourSearchParams(lat=49.59, lon=11.00)
        data = params.model_dump()
        assert data["lat"] == 49.59
        assert data["lon"] == 11.00
        assert data["radius_km"] == 30.0
        assert data["sources"] == ["komoot", "gps_tour"]
