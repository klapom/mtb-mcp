"""Tests for DWD (Bright Sky) API client."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from mtb_mcp.clients.dwd import DWDClient
from mtb_mcp.models.weather import WeatherCondition

FIXTURES = Path(__file__).parent.parent / "fixtures" / "api_responses"


def _load_fixture(name: str) -> dict[str, object]:
    """Load a JSON fixture file."""
    with open(FIXTURES / name) as f:
        result: dict[str, object] = json.load(f)
        return result


class TestDWDClientForecast:
    """Tests for DWDClient.get_forecast."""

    @respx.mock
    async def test_parses_forecast(self) -> None:
        """Should parse Bright Sky weather response into WeatherForecast."""
        fixture = _load_fixture("brightsky_weather.json")
        respx.get("https://api.brightsky.dev/weather").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with DWDClient() as client:
            forecast = await client.get_forecast(49.59, 11.00)

        assert forecast.location_name == "NUERNBERG"
        assert forecast.lat == 49.59
        assert forecast.lon == 11.00
        assert len(forecast.hours) == 3

    @respx.mock
    async def test_forecast_hourly_data(self) -> None:
        """Should correctly parse temperature, wind, precipitation."""
        fixture = _load_fixture("brightsky_weather.json")
        respx.get("https://api.brightsky.dev/weather").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with DWDClient() as client:
            forecast = await client.get_forecast(49.59, 11.00)

        first = forecast.hours[0]
        assert first.temp_c == 22.5
        assert first.wind_speed_kmh == 12.0
        assert first.wind_gust_kmh == 25.0
        assert first.precipitation_mm == 0.0
        assert first.condition == WeatherCondition.cloudy

    @respx.mock
    async def test_forecast_rain_condition(self) -> None:
        """Should parse rain condition from icon."""
        fixture = _load_fixture("brightsky_weather.json")
        respx.get("https://api.brightsky.dev/weather").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with DWDClient() as client:
            forecast = await client.get_forecast(49.59, 11.00)

        last = forecast.hours[2]
        assert last.condition == WeatherCondition.rain
        assert last.precipitation_mm == 0.5

    @respx.mock
    async def test_forecast_empty_weather(self) -> None:
        """Should handle empty weather list."""
        respx.get("https://api.brightsky.dev/weather").mock(
            return_value=httpx.Response(200, json={"weather": [], "sources": []})
        )

        async with DWDClient() as client:
            forecast = await client.get_forecast(49.59, 11.00)

        assert len(forecast.hours) == 0
        assert forecast.location_name == "49.59,11.00"


class TestDWDClientRainRadar:
    """Tests for DWDClient.get_rain_radar."""

    @respx.mock
    async def test_no_rain(self) -> None:
        """Should detect no rain when precipitation_10 is 0."""
        fixture = _load_fixture("brightsky_current_weather.json")
        respx.get("https://api.brightsky.dev/current_weather").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with DWDClient() as client:
            radar = await client.get_rain_radar(49.59, 11.00)

        assert not radar.rain_approaching
        assert radar.eta_minutes is None
        assert all(v == 0.0 for v in radar.rain_next_60min)

    @respx.mock
    async def test_currently_raining(self) -> None:
        """Should detect current rain."""
        fixture = _load_fixture("brightsky_current_weather_rain.json")
        respx.get("https://api.brightsky.dev/current_weather").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with DWDClient() as client:
            radar = await client.get_rain_radar(49.59, 11.00)

        assert radar.rain_approaching
        assert radar.eta_minutes == 0
        assert len(radar.rain_next_60min) == 12
        assert all(v > 0 for v in radar.rain_next_60min)


class TestDWDClientAlerts:
    """Tests for DWDClient.get_alerts."""

    @respx.mock
    async def test_parses_alerts(self) -> None:
        """Should parse alert data correctly."""
        fixture = _load_fixture("brightsky_alerts.json")
        respx.get("https://api.brightsky.dev/alerts").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with DWDClient() as client:
            alerts = await client.get_alerts(49.59, 11.00)

        assert len(alerts) == 2
        assert alerts[0].event == "HEAVY THUNDERSTORM"
        assert alerts[0].severity == "severe"
        assert alerts[1].event == "WIND GUSTS"
        assert alerts[1].severity == "moderate"

    @respx.mock
    async def test_empty_alerts(self) -> None:
        """Should return empty list when no alerts."""
        fixture = _load_fixture("brightsky_alerts_empty.json")
        respx.get("https://api.brightsky.dev/alerts").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with DWDClient() as client:
            alerts = await client.get_alerts(49.59, 11.00)

        assert alerts == []


class TestDWDClientRainHistory:
    """Tests for DWDClient.get_rain_history."""

    @respx.mock
    async def test_parses_rain_history(self) -> None:
        """Should calculate total precipitation and find last rain."""
        fixture = _load_fixture("brightsky_rain_history.json")
        respx.get("https://api.brightsky.dev/weather").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with DWDClient() as client:
            history = await client.get_rain_history(49.59, 11.00)

        # Total should be 0.2 + 0.8 + 2.5 + 1.2 + 0.3 = 5.0
        assert abs(history.total_mm_48h - 5.0) < 0.01
        # Newest first, so last rain should be recent hours
        assert history.last_rain_hours_ago is not None

    @respx.mock
    async def test_dry_history(self) -> None:
        """Should handle completely dry period."""
        respx.get("https://api.brightsky.dev/weather").mock(
            return_value=httpx.Response(
                200,
                json={
                    "weather": [
                        {"timestamp": f"2025-07-15T{h:02d}:00:00+00:00", "precipitation": 0.0}
                        for h in range(24)
                    ],
                    "sources": [],
                },
            )
        )

        async with DWDClient() as client:
            history = await client.get_rain_history(49.59, 11.00)

        assert history.total_mm_48h == 0.0
        assert history.last_rain_hours_ago is None


class TestDWDClientErrorHandling:
    """Tests for error handling."""

    @respx.mock
    async def test_api_error_propagated(self) -> None:
        """HTTP errors from Bright Sky should propagate."""
        respx.get("https://api.brightsky.dev/weather").mock(
            return_value=httpx.Response(500, json={"error": "internal"})
        )

        async with DWDClient() as client:
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_forecast(49.59, 11.00)
