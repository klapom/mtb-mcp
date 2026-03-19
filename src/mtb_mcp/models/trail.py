"""Trail data models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from mtb_mcp.models.common import GeoPoint


class MTBScale(str, Enum):
    """Singletrail-Skala (STS) difficulty rating for MTB trails."""

    S0 = "S0"  # Forstweg
    S1 = "S1"  # Leichter Trail
    S2 = "S2"  # Technischer Trail
    S3 = "S3"  # Anspruchsvoll
    S4 = "S4"  # Sehr schwierig
    S5 = "S5"  # Extrem schwierig
    S6 = "S6"  # Nicht fahrbar


class TrailSurface(str, Enum):
    """Trail surface types from OpenStreetMap."""

    asphalt = "asphalt"
    gravel = "gravel"
    dirt = "dirt"
    grass = "grass"
    rock = "rock"
    roots = "roots"
    sand = "sand"


class TrailConditionStatus(str, Enum):
    """Estimated trail condition based on weather data."""

    dry = "dry"
    damp = "damp"
    wet = "wet"
    muddy = "muddy"
    frozen = "frozen"


class Trail(BaseModel):
    """An MTB trail from OpenStreetMap."""

    osm_id: int
    name: str | None = None
    mtb_scale: MTBScale | None = None
    surface: TrailSurface | None = None
    length_m: float | None = None
    geometry: list[GeoPoint] = Field(default_factory=list)


class TrailCondition(BaseModel):
    """Estimated trail condition based on weather analysis."""

    trail_name: str | None = None
    surface: TrailSurface
    estimated_condition: TrailConditionStatus
    confidence: str  # high, medium, low
    rain_48h_mm: float
    hours_since_rain: float | None = None
    reasoning: str
