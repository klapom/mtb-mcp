"""Tests for trail data models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from mtb_mcp.models.common import GeoPoint
from mtb_mcp.models.trail import (
    MTBScale,
    Trail,
    TrailCondition,
    TrailConditionStatus,
    TrailSurface,
)


class TestMTBScale:
    """Tests for MTBScale enum."""

    def test_all_values(self) -> None:
        """All S0-S6 values should be defined."""
        expected = {"S0", "S1", "S2", "S3", "S4", "S5", "S6"}
        actual = {s.value for s in MTBScale}
        assert actual == expected

    def test_from_string(self) -> None:
        """Should be constructable from string value."""
        assert MTBScale("S2") == MTBScale.S2

    def test_invalid_value(self) -> None:
        """Should reject invalid scale values."""
        with pytest.raises(ValueError):
            MTBScale("S7")

    def test_ordering(self) -> None:
        """Enum members should be ordered S0 through S6."""
        scales = list(MTBScale)
        assert scales[0] == MTBScale.S0
        assert scales[-1] == MTBScale.S6
        assert len(scales) == 7


class TestTrailSurface:
    """Tests for TrailSurface enum."""

    def test_all_values(self) -> None:
        """All expected surface types should be defined."""
        expected = {"asphalt", "gravel", "dirt", "grass", "rock", "roots", "sand"}
        actual = {s.value for s in TrailSurface}
        assert actual == expected

    def test_from_string(self) -> None:
        """Should be constructable from string value."""
        assert TrailSurface("rock") == TrailSurface.rock


class TestTrailConditionStatus:
    """Tests for TrailConditionStatus enum."""

    def test_all_values(self) -> None:
        """All condition statuses should be defined."""
        expected = {"dry", "damp", "wet", "muddy", "frozen"}
        actual = {s.value for s in TrailConditionStatus}
        assert actual == expected


class TestTrail:
    """Tests for Trail model."""

    def test_create_minimal(self) -> None:
        """Should be creatable with just osm_id."""
        trail = Trail(osm_id=12345678)
        assert trail.osm_id == 12345678
        assert trail.name is None
        assert trail.mtb_scale is None
        assert trail.surface is None
        assert trail.length_m is None
        assert trail.geometry == []

    def test_create_full(self) -> None:
        """Should accept all fields."""
        trail = Trail(
            osm_id=12345678,
            name="Tiergarten Singletrail",
            mtb_scale=MTBScale.S2,
            surface=TrailSurface.dirt,
            length_m=1500.0,
            geometry=[
                GeoPoint(lat=49.596, lon=11.004),
                GeoPoint(lat=49.597, lon=11.005),
            ],
        )
        assert trail.name == "Tiergarten Singletrail"
        assert trail.mtb_scale == MTBScale.S2
        assert trail.surface == TrailSurface.dirt
        assert trail.length_m == 1500.0
        assert len(trail.geometry) == 2

    def test_serialization(self) -> None:
        """Should serialize to dict correctly."""
        trail = Trail(
            osm_id=123,
            name="Test Trail",
            mtb_scale=MTBScale.S1,
            surface=TrailSurface.gravel,
        )
        data = trail.model_dump()
        assert data["osm_id"] == 123
        assert data["mtb_scale"] == "S1"
        assert data["surface"] == "gravel"

    def test_invalid_geo_point_in_geometry(self) -> None:
        """Should reject invalid coordinates in geometry."""
        with pytest.raises(ValidationError):
            Trail(
                osm_id=123,
                geometry=[GeoPoint(lat=200.0, lon=11.0)],  # invalid lat
            )


class TestTrailCondition:
    """Tests for TrailCondition model."""

    def test_create(self) -> None:
        """Should accept all required fields."""
        tc = TrailCondition(
            trail_name="Test Trail",
            surface=TrailSurface.dirt,
            estimated_condition=TrailConditionStatus.wet,
            confidence="high",
            rain_48h_mm=15.0,
            hours_since_rain=3.0,
            reasoning="Heavy rain 3 hours ago on dirt surface",
        )
        assert tc.estimated_condition == TrailConditionStatus.wet
        assert tc.confidence == "high"

    def test_without_optional_fields(self) -> None:
        """Should work without optional trail_name and hours_since_rain."""
        tc = TrailCondition(
            surface=TrailSurface.rock,
            estimated_condition=TrailConditionStatus.dry,
            confidence="medium",
            rain_48h_mm=0.0,
            reasoning="No rain, rock surface drains quickly",
        )
        assert tc.trail_name is None
        assert tc.hours_since_rain is None

    def test_serialization(self) -> None:
        """Should serialize correctly."""
        tc = TrailCondition(
            trail_name="Rocky Path",
            surface=TrailSurface.rock,
            estimated_condition=TrailConditionStatus.damp,
            confidence="low",
            rain_48h_mm=5.0,
            hours_since_rain=8.0,
            reasoning="Some rain but rock dries fast",
        )
        data = tc.model_dump()
        assert data["surface"] == "rock"
        assert data["estimated_condition"] == "damp"
