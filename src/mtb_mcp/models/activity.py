"""Strava activity data models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field

from mtb_mcp.models.common import GeoPoint


class SportType(str, Enum):
    """Strava cycling sport types."""

    mountain_bike_ride = "MountainBikeRide"
    ride = "Ride"
    gravel_ride = "GravelRide"
    e_bike_ride = "EBikeRide"
    e_mountain_bike_ride = "EMountainBikeRide"


class ActivitySummary(BaseModel):
    """Summary of a Strava activity."""

    id: int
    name: str
    sport_type: str
    distance_km: float
    elevation_gain_m: float
    moving_time_seconds: int
    elapsed_time_seconds: int
    start_date: datetime
    average_speed_kmh: float
    max_speed_kmh: float
    average_heartrate: float | None = None
    max_heartrate: float | None = None
    average_watts: float | None = None
    max_watts: float | None = None
    suffer_score: float | None = None
    calories: float | None = None
    gear_id: str | None = None
    start_latlng: GeoPoint | None = None


class ActivityDetail(ActivitySummary):
    """Detailed Strava activity with segment efforts."""

    description: str | None = None
    average_cadence: float | None = None
    average_temp: float | None = None
    device_name: str | None = None
    segment_efforts: list[SegmentEffort] = Field(default_factory=list)


class SegmentEffort(BaseModel):
    """A single effort on a Strava segment."""

    id: int
    name: str
    distance_m: float
    elapsed_time_seconds: int
    moving_time_seconds: int
    average_heartrate: float | None = None
    average_watts: float | None = None
    pr_rank: int | None = None  # 1=PR, 2=2nd best, 3=3rd best


class SegmentInfo(BaseModel):
    """Information about a Strava segment."""

    id: int
    name: str
    distance_m: float
    average_grade: float
    maximum_grade: float
    elevation_high: float
    elevation_low: float
    climb_category: int  # 0=no cat, 1=4, 2=3, 3=2, 4=1, 5=HC
    start_latlng: GeoPoint | None = None
    end_latlng: GeoPoint | None = None


class RideTotals(BaseModel):
    """Aggregated ride totals."""

    count: int = 0
    distance_km: float = 0.0
    elevation_gain_m: float = 0.0
    moving_time_seconds: int = 0


class AthleteStats(BaseModel):
    """Athlete aggregate statistics from Strava."""

    recent_ride_totals: RideTotals
    ytd_ride_totals: RideTotals
    all_ride_totals: RideTotals
