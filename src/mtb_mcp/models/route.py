"""Route data models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from mtb_mcp.models.common import GeoPoint


class RouteSegment(BaseModel):
    """A segment of a route with distance and elevation info."""

    points: list[GeoPoint]
    distance_m: float
    elevation_gain_m: float
    elevation_loss_m: float
    surface: str | None = None


class RouteSummary(BaseModel):
    """Summary of a calculated route."""

    distance_km: float
    elevation_gain_m: float
    elevation_loss_m: float
    duration_minutes: float | None = None
    source: str  # "brouter" or "ors"


class Route(BaseModel):
    """A complete calculated route."""

    summary: RouteSummary
    points: list[GeoPoint]
    segments: list[RouteSegment] = Field(default_factory=list)
    gpx: str | None = None  # GPX XML if available


class ElevationPoint(BaseModel):
    """A point with distance from start and elevation."""

    distance_km: float
    elevation_m: float


class ElevationProfile(BaseModel):
    """Elevation profile for a route."""

    points: list[ElevationPoint]
    total_distance_km: float
    total_gain_m: float
    total_loss_m: float
    min_elevation_m: float
    max_elevation_m: float
