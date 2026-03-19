"""Weather data models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class WeatherCondition(str, Enum):
    """Weather condition categories."""

    clear = "clear"
    cloudy = "cloudy"
    rain = "rain"
    heavy_rain = "heavy_rain"
    snow = "snow"
    thunderstorm = "thunderstorm"
    fog = "fog"


class HourlyForecast(BaseModel):
    """Single hour of weather forecast data."""

    time: datetime
    temp_c: float
    wind_speed_kmh: float
    wind_gust_kmh: float | None = None
    precipitation_mm: float = 0.0
    precipitation_probability: float = Field(default=0.0, ge=0, le=100)
    humidity_pct: float = Field(default=0.0, ge=0, le=100)
    condition: WeatherCondition = WeatherCondition.clear


class WeatherForecast(BaseModel):
    """Multi-hour weather forecast for a location."""

    location_name: str
    lat: float
    lon: float
    hours: list[HourlyForecast]
    generated_at: datetime


class RainRadar(BaseModel):
    """Rain nowcasting data for the next 60 minutes."""

    lat: float
    lon: float
    rain_next_60min: list[float] = Field(
        default_factory=list,
        description="mm per 5min interval (12 values)",
    )
    rain_approaching: bool
    eta_minutes: int | None = None


class WeatherAlert(BaseModel):
    """A severe weather alert."""

    event: str
    severity: str  # minor, moderate, severe, extreme
    headline: str
    description: str
    onset: datetime
    expires: datetime


class RainHistory(BaseModel):
    """Precipitation history for the last 48 hours."""

    lat: float
    lon: float
    total_mm_48h: float
    hourly_mm: list[float] = Field(
        default_factory=list,
        description="Last 48 hours of precipitation, newest first",
    )
    last_rain_hours_ago: float | None = None
