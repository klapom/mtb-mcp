"""Tests for weather MCP tools."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from mtb_mcp.models.weather import (
    HourlyForecast,
    RainHistory,
    RainRadar,
    WeatherAlert,
    WeatherCondition,
    WeatherForecast,
)
from mtb_mcp.tools.weather_tools import (
    weather_alerts,
    weather_forecast,
    weather_history,
    weather_rain_radar,
)


def _make_forecast() -> WeatherForecast:
    """Create a test WeatherForecast."""
    return WeatherForecast(
        location_name="NUERNBERG",
        lat=49.59,
        lon=11.00,
        hours=[
            HourlyForecast(
                time=datetime(2025, 7, 15, 10, 0, tzinfo=timezone.utc),
                temp_c=22.5,
                wind_speed_kmh=12.0,
                precipitation_mm=0.0,
                condition=WeatherCondition.clear,
            ),
            HourlyForecast(
                time=datetime(2025, 7, 15, 11, 0, tzinfo=timezone.utc),
                temp_c=24.0,
                wind_speed_kmh=15.0,
                precipitation_mm=0.5,
                condition=WeatherCondition.rain,
            ),
        ],
        generated_at=datetime(2025, 7, 15, 9, 0, tzinfo=timezone.utc),
    )


class TestWeatherForecastTool:
    """Tests for weather_forecast tool."""

    @patch("mtb_mcp.tools.weather_tools.DWDClient")
    async def test_returns_formatted_string(self, mock_client_cls: AsyncMock) -> None:
        """Should return a formatted forecast string."""
        mock_client = AsyncMock()
        mock_client.get_forecast.return_value = _make_forecast()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await weather_forecast(lat=49.59, lon=11.00)

        assert "NUERNBERG" in result
        assert "22.5" in result
        assert "clear" in result

    @patch("mtb_mcp.tools.weather_tools.DWDClient")
    @patch("mtb_mcp.tools.weather_tools.get_settings")
    async def test_uses_home_location(
        self, mock_settings: AsyncMock, mock_client_cls: AsyncMock
    ) -> None:
        """Should use home location when no lat/lon provided."""
        mock_settings.return_value.home_lat = 49.59
        mock_settings.return_value.home_lon = 11.00

        mock_client = AsyncMock()
        mock_client.get_forecast.return_value = _make_forecast()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await weather_forecast()

        mock_client.get_forecast.assert_called_once_with(49.59, 11.00)


class TestWeatherRainRadarTool:
    """Tests for weather_rain_radar tool."""

    @patch("mtb_mcp.tools.weather_tools.DWDClient")
    async def test_no_rain(self, mock_client_cls: AsyncMock) -> None:
        """Should display no-rain status."""
        mock_client = AsyncMock()
        mock_client.get_rain_radar.return_value = RainRadar(
            lat=49.59,
            lon=11.00,
            rain_next_60min=[0.0] * 12,
            rain_approaching=False,
            eta_minutes=None,
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await weather_rain_radar(lat=49.59, lon=11.00)

        assert "No rain expected" in result

    @patch("mtb_mcp.tools.weather_tools.DWDClient")
    async def test_currently_raining(self, mock_client_cls: AsyncMock) -> None:
        """Should display raining status."""
        mock_client = AsyncMock()
        mock_client.get_rain_radar.return_value = RainRadar(
            lat=49.59,
            lon=11.00,
            rain_next_60min=[1.0] * 12,
            rain_approaching=True,
            eta_minutes=0,
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await weather_rain_radar(lat=49.59, lon=11.00)

        assert "currently raining" in result


class TestWeatherAlertsTool:
    """Tests for weather_alerts tool."""

    @patch("mtb_mcp.tools.weather_tools.DWDClient")
    async def test_no_alerts(self, mock_client_cls: AsyncMock) -> None:
        """Should display safe message when no alerts."""
        mock_client = AsyncMock()
        mock_client.get_alerts.return_value = []
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await weather_alerts(lat=49.59, lon=11.00)

        assert "No active weather alerts" in result
        assert "safe" in result

    @patch("mtb_mcp.tools.weather_tools.DWDClient")
    async def test_with_alerts(self, mock_client_cls: AsyncMock) -> None:
        """Should list active alerts."""
        mock_client = AsyncMock()
        mock_client.get_alerts.return_value = [
            WeatherAlert(
                event="THUNDERSTORM",
                severity="severe",
                headline="Storm warning",
                description="Heavy thunderstorm expected.",
                onset=datetime(2025, 7, 15, 14, 0, tzinfo=timezone.utc),
                expires=datetime(2025, 7, 15, 20, 0, tzinfo=timezone.utc),
            ),
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await weather_alerts(lat=49.59, lon=11.00)

        assert "THUNDERSTORM" in result
        assert "SEVERE" in result
        assert "1 alert" in result


class TestWeatherHistoryTool:
    """Tests for weather_history tool."""

    @patch("mtb_mcp.tools.weather_tools.DWDClient")
    async def test_dry_conditions(self, mock_client_cls: AsyncMock) -> None:
        """Should suggest dry trail conditions."""
        mock_client = AsyncMock()
        mock_client.get_rain_history.return_value = RainHistory(
            lat=49.59,
            lon=11.00,
            total_mm_48h=0.5,
            hourly_mm=[0.0] * 48,
            last_rain_hours_ago=None,
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await weather_history(lat=49.59, lon=11.00)

        assert "DRY" in result
        assert "0.5mm" in result

    @patch("mtb_mcp.tools.weather_tools.DWDClient")
    async def test_muddy_conditions(self, mock_client_cls: AsyncMock) -> None:
        """Should warn about muddy conditions after heavy rain."""
        mock_client = AsyncMock()
        mock_client.get_rain_history.return_value = RainHistory(
            lat=49.59,
            lon=11.00,
            total_mm_48h=25.0,
            hourly_mm=[0.0, 0.0, 5.0, 10.0, 10.0] + [0.0] * 43,
            last_rain_hours_ago=2.0,
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await weather_history(lat=49.59, lon=11.00)

        assert "MUDDY" in result
        assert "25.0mm" in result

    @patch("mtb_mcp.tools.weather_tools.DWDClient")
    @patch("mtb_mcp.tools.weather_tools.get_settings")
    async def test_uses_home_location(
        self, mock_settings: AsyncMock, mock_client_cls: AsyncMock
    ) -> None:
        """Should use home location when no lat/lon provided."""
        mock_settings.return_value.home_lat = 49.59
        mock_settings.return_value.home_lon = 11.00

        mock_client = AsyncMock()
        mock_client.get_rain_history.return_value = RainHistory(
            lat=49.59,
            lon=11.00,
            total_mm_48h=0.0,
            hourly_mm=[0.0] * 48,
            last_rain_hours_ago=None,
        )
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        await weather_history()

        mock_client.get_rain_history.assert_called_once_with(49.59, 11.00)
