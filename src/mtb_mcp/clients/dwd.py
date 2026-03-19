"""DWD OpenData API client via Bright Sky JSON wrapper."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import structlog

from mtb_mcp.clients.base import BaseClient
from mtb_mcp.models.weather import (
    HourlyForecast,
    RainHistory,
    RainRadar,
    WeatherAlert,
    WeatherCondition,
    WeatherForecast,
)

logger = structlog.get_logger(__name__)

# Mapping from Bright Sky icon/condition to our WeatherCondition enum
_CONDITION_MAP: dict[str, WeatherCondition] = {
    "clear-day": WeatherCondition.clear,
    "clear-night": WeatherCondition.clear,
    "partly-cloudy-day": WeatherCondition.cloudy,
    "partly-cloudy-night": WeatherCondition.cloudy,
    "cloudy": WeatherCondition.cloudy,
    "fog": WeatherCondition.fog,
    "wind": WeatherCondition.clear,
    "rain": WeatherCondition.rain,
    "sleet": WeatherCondition.rain,
    "snow": WeatherCondition.snow,
    "hail": WeatherCondition.heavy_rain,
    "thunderstorm": WeatherCondition.thunderstorm,
}


def _parse_condition(icon: str | None) -> WeatherCondition:
    """Convert Bright Sky icon string to WeatherCondition."""
    if icon is None:
        return WeatherCondition.clear
    return _CONDITION_MAP.get(icon, WeatherCondition.clear)


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float, returning default if None."""
    if value is None:
        return default
    return float(value)


class DWDClient(BaseClient):
    """Client for DWD weather data via Bright Sky API.

    Bright Sky (https://brightsky.dev/) is a free, open-source JSON API
    that wraps DWD (Deutscher Wetterdienst) OpenData. No authentication required.
    """

    def __init__(self) -> None:
        super().__init__(
            base_url="https://api.brightsky.dev",
            rate_limit=2.0,  # Be gentle with the free API
        )

    async def get_forecast(self, lat: float, lon: float) -> WeatherForecast:
        """Get multi-day hourly forecast for a location.

        Uses Bright Sky /weather endpoint which returns DWD MOSMIX data.
        """
        now = datetime.now(tz=timezone.utc)
        # Fetch next 3 days of forecast
        end = now + timedelta(days=3)

        data = await self._get(
            "/weather",
            params={
                "lat": str(lat),
                "lon": str(lon),
                "date": now.strftime("%Y-%m-%dT%H:%M"),
                "last_date": end.strftime("%Y-%m-%dT%H:%M"),
            },
        )

        hours: list[HourlyForecast] = []
        for entry in data.get("weather", []):
            hours.append(
                HourlyForecast(
                    time=datetime.fromisoformat(entry["timestamp"]),
                    temp_c=_safe_float(entry.get("temperature")),
                    wind_speed_kmh=_safe_float(entry.get("wind_speed")),
                    wind_gust_kmh=(
                        float(entry["wind_gust_speed"])
                        if entry.get("wind_gust_speed") is not None
                        else None
                    ),
                    precipitation_mm=_safe_float(entry.get("precipitation")),
                    precipitation_probability=_safe_float(
                        entry.get("precipitation_probability")
                    ),
                    humidity_pct=_safe_float(entry.get("relative_humidity")),
                    condition=_parse_condition(entry.get("icon")),
                )
            )

        # Determine location name from sources metadata
        sources = data.get("sources", [])
        location_name = (
            sources[0].get("station_name", f"{lat:.2f},{lon:.2f}")
            if sources
            else f"{lat:.2f},{lon:.2f}"
        )

        return WeatherForecast(
            location_name=location_name,
            lat=lat,
            lon=lon,
            hours=hours,
            generated_at=now,
        )

    async def get_rain_radar(self, lat: float, lon: float) -> RainRadar:
        """Get rain nowcasting for the next 2 hours.

        Uses Bright Sky /current_weather for current conditions and recent
        precipitation to estimate near-term rain.
        """
        data = await self._get(
            "/current_weather",
            params={"lat": str(lat), "lon": str(lon)},
        )

        weather = data.get("weather", {})
        current_precip = _safe_float(weather.get("precipitation_10", 0.0))

        # Estimate next 60 minutes based on current conditions
        # Each interval is 5 minutes, so 12 values
        rain_values: list[float] = []
        rain_approaching = False
        eta: int | None = None

        if current_precip > 0:
            # Currently raining — assume continues at same rate
            per_5min = current_precip / 2.0  # precipitation_10 is per 10min
            rain_values = [per_5min] * 12
            rain_approaching = True
            eta = 0
        else:
            rain_values = [0.0] * 12

        return RainRadar(
            lat=lat,
            lon=lon,
            rain_next_60min=rain_values,
            rain_approaching=rain_approaching,
            eta_minutes=eta,
        )

    async def get_alerts(self, lat: float, lon: float) -> list[WeatherAlert]:
        """Get active weather alerts for the region.

        Uses Bright Sky /alerts endpoint which returns DWD CAP alerts.
        """
        data = await self._get(
            "/alerts",
            params={"lat": str(lat), "lon": str(lon)},
        )

        alerts: list[WeatherAlert] = []
        for alert_data in data.get("alerts", []):
            alerts.append(
                WeatherAlert(
                    event=alert_data.get("event", "Unknown"),
                    severity=alert_data.get("severity", "minor"),
                    headline=alert_data.get("headline", ""),
                    description=alert_data.get("description", ""),
                    onset=datetime.fromisoformat(alert_data["onset"]),
                    expires=datetime.fromisoformat(alert_data["expires"]),
                )
            )

        return alerts

    async def get_rain_history(self, lat: float, lon: float) -> RainHistory:
        """Get precipitation for the last 48 hours.

        Fetches hourly weather data for past 48h and extracts precipitation.
        """
        now = datetime.now(tz=timezone.utc)
        start = now - timedelta(hours=48)

        data = await self._get(
            "/weather",
            params={
                "lat": str(lat),
                "lon": str(lon),
                "date": start.strftime("%Y-%m-%dT%H:%M"),
                "last_date": now.strftime("%Y-%m-%dT%H:%M"),
            },
        )

        # Extract hourly precipitation, newest first
        hourly_mm: list[float] = []
        for entry in reversed(data.get("weather", [])):
            hourly_mm.append(_safe_float(entry.get("precipitation")))

        total_mm = sum(hourly_mm)

        # Find hours since last significant rain (>0.5mm/h)
        last_rain_hours_ago: float | None = None
        for i, mm in enumerate(hourly_mm):
            if mm > 0.5:
                last_rain_hours_ago = float(i)
                break

        return RainHistory(
            lat=lat,
            lon=lon,
            total_mm_48h=total_mm,
            hourly_mm=hourly_mm,
            last_rain_hours_ago=last_rain_hours_ago,
        )
