"""Tour data models for multi-source tour search."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from mtb_mcp.models.common import GeoPoint


class TourSource(str, Enum):
    """Source platforms for tour data."""

    komoot = "komoot"
    gps_tour = "gps_tour"
    mtb_project = "mtb_project"


class TourDifficulty(str, Enum):
    """Unified tour difficulty levels."""

    easy = "easy"
    moderate = "moderate"
    difficult = "difficult"
    expert = "expert"


class TourSummary(BaseModel):
    """Summary of a tour from any source."""

    id: str
    source: TourSource
    name: str
    distance_km: float | None = None
    elevation_m: float | None = None
    difficulty: TourDifficulty | None = None
    region: str | None = None
    url: str | None = None
    start_point: GeoPoint | None = None


class TourDetail(TourSummary):
    """Detailed tour information."""

    description: str | None = None
    duration_minutes: int | None = None
    surfaces: list[str] = Field(default_factory=list)
    waypoints: list[GeoPoint] = Field(default_factory=list)
    download_count: int | None = None
    rating: float | None = None


class TourSearchParams(BaseModel):
    """Parameters for tour search."""

    lat: float
    lon: float
    radius_km: float = 30.0
    min_distance_km: float | None = None
    max_distance_km: float | None = None
    difficulty: TourDifficulty | None = None
    sport_type: str = "mtb"
    sources: list[TourSource] = Field(
        default_factory=lambda: [TourSource.komoot, TourSource.gps_tour]
    )
