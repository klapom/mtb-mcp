"""Tests for weather data models."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from mtb_mcp.models.weather import (
    HourlyForecast,
    RainHistory,
    RainRadar,
    WeatherAlert,
    WeatherCondition,
    WeatherForecast,
)


class TestWeatherCondition:
    """Tests for WeatherCondition enum."""

    def test_all_values(self) -> None:
        """All expected weather conditions should be defined."""
        expected = {"clear", "cloudy", "rain", "heavy_rain", "snow", "thunderstorm", "fog"}
        actual = {c.value for c in WeatherCondition}
        assert actual == expected

    def test_from_string(self) -> None:
        """Should be constructable from string value."""
        assert WeatherCondition("rain") == WeatherCondition.rain

    def test_invalid_value(self) -> None:
        """Should reject invalid values."""
        with pytest.raises(ValueError):
            WeatherCondition("tornado")


class TestHourlyForecast:
    """Tests for HourlyForecast model."""

    def test_create_minimal(self) -> None:
        """Should be creatable with just required fields."""
        hf = HourlyForecast(
            time=datetime(2025, 7, 15, 10, 0, tzinfo=timezone.utc),
            temp_c=22.5,
            wind_speed_kmh=12.0,
        )
        assert hf.temp_c == 22.5
        assert hf.wind_gust_kmh is None
        assert hf.precipitation_mm == 0.0
        assert hf.condition == WeatherCondition.clear

    def test_create_full(self) -> None:
        """Should accept all fields."""
        hf = HourlyForecast(
            time=datetime(2025, 7, 15, 10, 0, tzinfo=timezone.utc),
            temp_c=18.0,
            wind_speed_kmh=25.0,
            wind_gust_kmh=45.0,
            precipitation_mm=3.5,
            precipitation_probability=80.0,
            humidity_pct=90.0,
            condition=WeatherCondition.heavy_rain,
        )
        assert hf.wind_gust_kmh == 45.0
        assert hf.precipitation_probability == 80.0
        assert hf.humidity_pct == 90.0

    def test_precipitation_probability_bounds(self) -> None:
        """Precipitation probability should be between 0 and 100."""
        with pytest.raises(ValidationError):
            HourlyForecast(
                time=datetime(2025, 7, 15, 10, 0, tzinfo=timezone.utc),
                temp_c=20.0,
                wind_speed_kmh=10.0,
                precipitation_probability=150.0,
            )

    def test_humidity_bounds(self) -> None:
        """Humidity should be between 0 and 100."""
        with pytest.raises(ValidationError):
            HourlyForecast(
                time=datetime(2025, 7, 15, 10, 0, tzinfo=timezone.utc),
                temp_c=20.0,
                wind_speed_kmh=10.0,
                humidity_pct=-5.0,
            )

    def test_serialization(self) -> None:
        """Should serialize to dict correctly."""
        hf = HourlyForecast(
            time=datetime(2025, 7, 15, 10, 0, tzinfo=timezone.utc),
            temp_c=22.5,
            wind_speed_kmh=12.0,
        )
        data = hf.model_dump()
        assert data["temp_c"] == 22.5
        assert data["condition"] == "clear"


class TestWeatherForecast:
    """Tests for WeatherForecast model."""

    def test_create(self) -> None:
        """Should accept all required fields."""
        now = datetime.now(tz=timezone.utc)
        wf = WeatherForecast(
            location_name="NUERNBERG",
            lat=49.5,
            lon=11.05,
            hours=[],
            generated_at=now,
        )
        assert wf.location_name == "NUERNBERG"
        assert wf.hours == []

    def test_with_hours(self) -> None:
        """Should hold a list of hourly forecasts."""
        hours = [
            HourlyForecast(
                time=datetime(2025, 7, 15, h, 0, tzinfo=timezone.utc),
                temp_c=20.0 + h,
                wind_speed_kmh=10.0,
            )
            for h in range(3)
        ]
        wf = WeatherForecast(
            location_name="Test",
            lat=49.0,
            lon=11.0,
            hours=hours,
            generated_at=datetime.now(tz=timezone.utc),
        )
        assert len(wf.hours) == 3
        assert wf.hours[0].temp_c == 20.0
        assert wf.hours[2].temp_c == 22.0


class TestRainRadar:
    """Tests for RainRadar model."""

    def test_no_rain(self) -> None:
        """Should represent no-rain conditions."""
        rr = RainRadar(
            lat=49.59,
            lon=11.00,
            rain_next_60min=[0.0] * 12,
            rain_approaching=False,
            eta_minutes=None,
        )
        assert not rr.rain_approaching
        assert rr.eta_minutes is None
        assert len(rr.rain_next_60min) == 12

    def test_rain_approaching(self) -> None:
        """Should represent approaching rain."""
        rr = RainRadar(
            lat=49.59,
            lon=11.00,
            rain_next_60min=[0.0, 0.0, 0.0, 0.5, 1.0, 1.5, 2.0, 1.0, 0.5, 0.0, 0.0, 0.0],
            rain_approaching=True,
            eta_minutes=15,
        )
        assert rr.rain_approaching
        assert rr.eta_minutes == 15

    def test_currently_raining(self) -> None:
        """Should represent current rain with eta=0."""
        rr = RainRadar(
            lat=49.59,
            lon=11.00,
            rain_next_60min=[1.0] * 12,
            rain_approaching=True,
            eta_minutes=0,
        )
        assert rr.eta_minutes == 0


class TestWeatherAlert:
    """Tests for WeatherAlert model."""

    def test_create(self) -> None:
        """Should accept all required fields."""
        alert = WeatherAlert(
            event="HEAVY THUNDERSTORM",
            severity="severe",
            headline="Amtliche UNWETTERWARNUNG",
            description="Es treten schwere Gewitter auf.",
            onset=datetime(2025, 7, 15, 14, 0, tzinfo=timezone.utc),
            expires=datetime(2025, 7, 15, 20, 0, tzinfo=timezone.utc),
        )
        assert alert.event == "HEAVY THUNDERSTORM"
        assert alert.severity == "severe"

    def test_serialization(self) -> None:
        """Should serialize correctly."""
        alert = WeatherAlert(
            event="WIND",
            severity="moderate",
            headline="Wind warning",
            description="Strong winds expected.",
            onset=datetime(2025, 7, 15, 12, 0, tzinfo=timezone.utc),
            expires=datetime(2025, 7, 15, 18, 0, tzinfo=timezone.utc),
        )
        data = alert.model_dump()
        assert data["event"] == "WIND"
        assert data["severity"] == "moderate"


class TestRainHistory:
    """Tests for RainHistory model."""

    def test_dry_period(self) -> None:
        """Should represent a dry period."""
        rh = RainHistory(
            lat=49.59,
            lon=11.00,
            total_mm_48h=0.0,
            hourly_mm=[0.0] * 48,
            last_rain_hours_ago=None,
        )
        assert rh.total_mm_48h == 0.0
        assert rh.last_rain_hours_ago is None

    def test_recent_rain(self) -> None:
        """Should represent recent rain."""
        hourly = [0.0] * 48
        hourly[5] = 2.5  # 5 hours ago (newest first)
        rh = RainHistory(
            lat=49.59,
            lon=11.00,
            total_mm_48h=2.5,
            hourly_mm=hourly,
            last_rain_hours_ago=5.0,
        )
        assert rh.total_mm_48h == 2.5
        assert rh.last_rain_hours_ago == 5.0

    def test_serialization(self) -> None:
        """Should serialize correctly."""
        rh = RainHistory(
            lat=49.59,
            lon=11.00,
            total_mm_48h=5.0,
            hourly_mm=[0.0, 0.0, 1.0, 2.0, 2.0, 0.0],
            last_rain_hours_ago=2.0,
        )
        data = rh.model_dump()
        assert data["total_mm_48h"] == 5.0
        assert len(data["hourly_mm"]) == 6
