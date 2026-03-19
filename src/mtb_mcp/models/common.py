"""Common data models used across the application."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, model_validator


class GeoPoint(BaseModel):
    """WGS84 coordinate with optional elevation."""

    lat: float = Field(ge=-90, le=90, description="Latitude in degrees")
    lon: float = Field(ge=-180, le=180, description="Longitude in degrees")
    ele: float | None = Field(default=None, description="Elevation in meters")


class BoundingBox(BaseModel):
    """Geographic bounding box (south, west, north, east)."""

    south: float = Field(ge=-90, le=90)
    west: float = Field(ge=-180, le=180)
    north: float = Field(ge=-90, le=90)
    east: float = Field(ge=-180, le=180)

    @model_validator(mode="after")
    def _check_bounds(self) -> BoundingBox:
        if self.south > self.north:
            msg = f"south ({self.south}) must be <= north ({self.north})"
            raise ValueError(msg)
        return self


class DateRange(BaseModel):
    """Date range for filtering."""

    start: date
    end: date

    @model_validator(mode="after")
    def _check_range(self) -> DateRange:
        if self.start > self.end:
            msg = f"start ({self.start}) must be <= end ({self.end})"
            raise ValueError(msg)
        return self
