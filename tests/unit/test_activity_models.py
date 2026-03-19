"""Tests for Strava activity data models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from mtb_mcp.models.activity import (
    ActivityDetail,
    ActivitySummary,
    AthleteStats,
    RideTotals,
    SegmentEffort,
    SegmentInfo,
    SportType,
)
from mtb_mcp.models.common import GeoPoint


class TestSportType:
    """Tests for SportType enum."""

    def test_mountain_bike_ride(self) -> None:
        assert SportType.mountain_bike_ride == "MountainBikeRide"
        assert SportType.mountain_bike_ride.value == "MountainBikeRide"

    def test_ride(self) -> None:
        assert SportType.ride.value == "Ride"

    def test_gravel_ride(self) -> None:
        assert SportType.gravel_ride.value == "GravelRide"

    def test_e_bike_ride(self) -> None:
        assert SportType.e_bike_ride.value == "EBikeRide"

    def test_e_mountain_bike_ride(self) -> None:
        assert SportType.e_mountain_bike_ride.value == "EMountainBikeRide"

    def test_from_value(self) -> None:
        assert SportType("MountainBikeRide") == SportType.mountain_bike_ride

    def test_invalid_value(self) -> None:
        with pytest.raises(ValueError):
            SportType("InvalidType")


class TestActivitySummary:
    """Tests for ActivitySummary model."""

    def test_full_activity(self) -> None:
        """Should create a full activity summary with all fields."""
        activity = ActivitySummary(
            id=12345678901,
            name="Morning MTB Ride",
            sport_type="MountainBikeRide",
            distance_km=32.5,
            elevation_gain_m=450.0,
            moving_time_seconds=5400,
            elapsed_time_seconds=6000,
            start_date=datetime(2025, 7, 15, 7, 0, tzinfo=timezone.utc),
            average_speed_kmh=21.67,
            max_speed_kmh=52.2,
            average_heartrate=145.0,
            max_heartrate=172.0,
            average_watts=185.0,
            max_watts=420.0,
            suffer_score=85.0,
            calories=950.0,
            gear_id="b12345",
            start_latlng=GeoPoint(lat=49.596, lon=11.004),
        )
        assert activity.id == 12345678901
        assert activity.name == "Morning MTB Ride"
        assert activity.sport_type == "MountainBikeRide"
        assert activity.distance_km == 32.5
        assert activity.elevation_gain_m == 450.0
        assert activity.moving_time_seconds == 5400
        assert activity.average_heartrate == 145.0
        assert activity.start_latlng is not None
        assert activity.start_latlng.lat == 49.596

    def test_minimal_activity(self) -> None:
        """Should create an activity with only required fields."""
        activity = ActivitySummary(
            id=1,
            name="Test",
            sport_type="Ride",
            distance_km=10.0,
            elevation_gain_m=100.0,
            moving_time_seconds=1800,
            elapsed_time_seconds=2000,
            start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            average_speed_kmh=20.0,
            max_speed_kmh=35.0,
        )
        assert activity.average_heartrate is None
        assert activity.max_heartrate is None
        assert activity.average_watts is None
        assert activity.max_watts is None
        assert activity.suffer_score is None
        assert activity.calories is None
        assert activity.gear_id is None
        assert activity.start_latlng is None

    def test_serialization(self) -> None:
        """Should serialize to dict correctly."""
        activity = ActivitySummary(
            id=1,
            name="Test",
            sport_type="Ride",
            distance_km=10.0,
            elevation_gain_m=100.0,
            moving_time_seconds=1800,
            elapsed_time_seconds=2000,
            start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            average_speed_kmh=20.0,
            max_speed_kmh=35.0,
        )
        data = activity.model_dump()
        assert data["id"] == 1
        assert data["name"] == "Test"
        assert data["distance_km"] == 10.0
        assert data["average_heartrate"] is None


class TestActivityDetail:
    """Tests for ActivityDetail model."""

    def test_activity_detail_with_segments(self) -> None:
        """Should create activity detail with segment efforts."""
        effort = SegmentEffort(
            id=987,
            name="Climb",
            distance_m=1200.0,
            elapsed_time_seconds=360,
            moving_time_seconds=350,
            average_heartrate=165.0,
            average_watts=250.0,
            pr_rank=1,
        )
        detail = ActivityDetail(
            id=123,
            name="MTB Ride",
            sport_type="MountainBikeRide",
            distance_km=32.5,
            elevation_gain_m=450.0,
            moving_time_seconds=5400,
            elapsed_time_seconds=6000,
            start_date=datetime(2025, 7, 15, 7, 0, tzinfo=timezone.utc),
            average_speed_kmh=21.67,
            max_speed_kmh=52.2,
            description="Great ride!",
            average_cadence=78.0,
            average_temp=22.0,
            device_name="Garmin Edge 540",
            segment_efforts=[effort],
        )
        assert detail.description == "Great ride!"
        assert detail.average_cadence == 78.0
        assert detail.average_temp == 22.0
        assert detail.device_name == "Garmin Edge 540"
        assert len(detail.segment_efforts) == 1
        assert detail.segment_efforts[0].name == "Climb"
        assert detail.segment_efforts[0].pr_rank == 1

    def test_activity_detail_default_segments(self) -> None:
        """Should default to empty segment efforts list."""
        detail = ActivityDetail(
            id=1,
            name="Test",
            sport_type="Ride",
            distance_km=10.0,
            elevation_gain_m=100.0,
            moving_time_seconds=1800,
            elapsed_time_seconds=2000,
            start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            average_speed_kmh=20.0,
            max_speed_kmh=35.0,
        )
        assert detail.segment_efforts == []
        assert detail.description is None
        assert detail.average_cadence is None


class TestSegmentEffort:
    """Tests for SegmentEffort model."""

    def test_pr_effort(self) -> None:
        """Should create a PR segment effort."""
        effort = SegmentEffort(
            id=123,
            name="Rathsberg Climb",
            distance_m=1200.0,
            elapsed_time_seconds=360,
            moving_time_seconds=350,
            pr_rank=1,
        )
        assert effort.pr_rank == 1
        assert effort.name == "Rathsberg Climb"
        assert effort.average_heartrate is None
        assert effort.average_watts is None

    def test_effort_with_metrics(self) -> None:
        """Should include heart rate and power data."""
        effort = SegmentEffort(
            id=456,
            name="Valley Sprint",
            distance_m=800.0,
            elapsed_time_seconds=90,
            moving_time_seconds=88,
            average_heartrate=172.0,
            average_watts=320.0,
            pr_rank=2,
        )
        assert effort.average_heartrate == 172.0
        assert effort.average_watts == 320.0
        assert effort.pr_rank == 2

    def test_effort_no_pr(self) -> None:
        """Should allow None pr_rank."""
        effort = SegmentEffort(
            id=789,
            name="Normal Effort",
            distance_m=500.0,
            elapsed_time_seconds=120,
            moving_time_seconds=115,
        )
        assert effort.pr_rank is None


class TestSegmentInfo:
    """Tests for SegmentInfo model."""

    def test_full_segment(self) -> None:
        """Should create a segment with all fields."""
        seg = SegmentInfo(
            id=5550001,
            name="Rathsberg Climb",
            distance_m=1200.0,
            average_grade=6.5,
            maximum_grade=12.0,
            elevation_high=380.0,
            elevation_low=302.0,
            climb_category=1,
            start_latlng=GeoPoint(lat=49.590, lon=11.010),
            end_latlng=GeoPoint(lat=49.595, lon=11.015),
        )
        assert seg.name == "Rathsberg Climb"
        assert seg.climb_category == 1
        assert seg.average_grade == 6.5
        assert seg.start_latlng is not None
        assert seg.end_latlng is not None

    def test_segment_no_category(self) -> None:
        """Should support climb_category 0 (no category)."""
        seg = SegmentInfo(
            id=1,
            name="Flat Trail",
            distance_m=3500.0,
            average_grade=0.5,
            maximum_grade=2.0,
            elevation_high=310.0,
            elevation_low=300.0,
            climb_category=0,
        )
        assert seg.climb_category == 0
        assert seg.start_latlng is None
        assert seg.end_latlng is None

    def test_segment_hc(self) -> None:
        """Should support HC climb category (5)."""
        seg = SegmentInfo(
            id=2,
            name="HC Climb",
            distance_m=10000.0,
            average_grade=8.0,
            maximum_grade=15.0,
            elevation_high=1200.0,
            elevation_low=400.0,
            climb_category=5,
        )
        assert seg.climb_category == 5


class TestRideTotals:
    """Tests for RideTotals model."""

    def test_defaults(self) -> None:
        """Should have sensible defaults."""
        totals = RideTotals()
        assert totals.count == 0
        assert totals.distance_km == 0.0
        assert totals.elevation_gain_m == 0.0
        assert totals.moving_time_seconds == 0

    def test_with_values(self) -> None:
        """Should accept provided values."""
        totals = RideTotals(
            count=85,
            distance_km=3250.0,
            elevation_gain_m=38500.0,
            moving_time_seconds=432000,
        )
        assert totals.count == 85
        assert totals.distance_km == 3250.0


class TestAthleteStats:
    """Tests for AthleteStats model."""

    def test_full_stats(self) -> None:
        """Should create full athlete stats."""
        stats = AthleteStats(
            recent_ride_totals=RideTotals(count=12, distance_km=485.0),
            ytd_ride_totals=RideTotals(count=85, distance_km=3250.0),
            all_ride_totals=RideTotals(count=520, distance_km=18500.0),
        )
        assert stats.recent_ride_totals.count == 12
        assert stats.ytd_ride_totals.distance_km == 3250.0
        assert stats.all_ride_totals.count == 520

    def test_stats_requires_all_totals(self) -> None:
        """Should require all three totals."""
        with pytest.raises(ValidationError):
            AthleteStats(  # type: ignore[call-arg]
                recent_ride_totals=RideTotals(),
            )
