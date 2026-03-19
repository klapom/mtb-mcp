"""Tests for intelligence MCP tools (ride_score, trail_condition_estimate)."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from mtb_mcp.models.weather import (
    HourlyForecast,
    RainHistory,
    WeatherCondition,
    WeatherForecast,
)
from mtb_mcp.tools.intelligence_tools import ride_score, trail_condition_estimate


def _make_forecast(temp_c: float = 20.0, wind: float = 5.0) -> WeatherForecast:
    """Create a test WeatherForecast."""
    return WeatherForecast(
        location_name="NUERNBERG",
        lat=49.59,
        lon=11.00,
        hours=[
            HourlyForecast(
                time=datetime(2025, 7, 15, 10, 0, tzinfo=timezone.utc),
                temp_c=temp_c,
                wind_speed_kmh=wind,
                wind_gust_kmh=10.0,
                precipitation_mm=0.0,
                precipitation_probability=0.0,
                humidity_pct=50.0,
                condition=WeatherCondition.clear,
            ),
        ],
        generated_at=datetime(2025, 7, 15, 9, 0, tzinfo=timezone.utc),
    )


def _make_history(
    hourly_mm: list[float] | None = None,
    total_mm: float = 0.0,
) -> RainHistory:
    """Create a test RainHistory."""
    if hourly_mm is None:
        hourly_mm = [0.0] * 48
    return RainHistory(
        lat=49.59,
        lon=11.00,
        total_mm_48h=total_mm,
        hourly_mm=hourly_mm,
        last_rain_hours_ago=None,
    )


def _mock_dwd_client(
    forecast: WeatherForecast | None = None,
    history: RainHistory | None = None,
) -> AsyncMock:
    """Return a mock DWDClient context manager."""
    mock_client = AsyncMock()
    mock_client.get_forecast.return_value = forecast or _make_forecast()
    mock_client.get_rain_history.return_value = history or _make_history()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


class TestTrailConditionEstimateTool:
    """Tests for the trail_condition_estimate MCP tool."""

    @patch("mtb_mcp.tools.intelligence_tools.DWDClient")
    async def test_dry_conditions(self, mock_cls: AsyncMock) -> None:
        """Dry weather → dry trail."""
        mock_cls.return_value = _mock_dwd_client()

        result = await trail_condition_estimate(lat=49.59, lon=11.00, surface="dirt")

        assert "DRY" in result
        assert "dirt" in result
        assert "49.59" in result

    @patch("mtb_mcp.tools.intelligence_tools.DWDClient")
    async def test_wet_conditions(self, mock_cls: AsyncMock) -> None:
        """Recent rain on dirt → wet or muddy."""
        rain = [5.0, 5.0, 3.0] + [0.0] * 45
        mock_cls.return_value = _mock_dwd_client(
            history=_make_history(hourly_mm=rain, total_mm=13.0),
        )

        result = await trail_condition_estimate(lat=49.59, lon=11.00, surface="dirt")

        # Should be WET or MUDDY (depends on absorbed calculation)
        assert "WET" in result or "MUDDY" in result

    @patch("mtb_mcp.tools.intelligence_tools.DWDClient")
    async def test_frozen_conditions(self, mock_cls: AsyncMock) -> None:
        """Sub-zero temperature → frozen."""
        mock_cls.return_value = _mock_dwd_client(
            forecast=_make_forecast(temp_c=-5.0),
        )

        result = await trail_condition_estimate(lat=49.59, lon=11.00, surface="dirt")

        assert "FROZEN" in result

    @patch("mtb_mcp.tools.intelligence_tools.DWDClient")
    async def test_asphalt_stays_dry(self, mock_cls: AsyncMock) -> None:
        """Asphalt surface → always dry regardless of rain."""
        rain = [10.0] * 10 + [0.0] * 38
        mock_cls.return_value = _mock_dwd_client(
            history=_make_history(hourly_mm=rain, total_mm=100.0),
        )

        result = await trail_condition_estimate(lat=49.59, lon=11.00, surface="asphalt")

        assert "DRY" in result

    @patch("mtb_mcp.tools.intelligence_tools.DWDClient")
    @patch("mtb_mcp.tools.intelligence_tools.get_settings")
    async def test_uses_home_location(
        self, mock_settings: AsyncMock, mock_cls: AsyncMock,
    ) -> None:
        """Should fall back to home location when no lat/lon given."""
        mock_settings.return_value.home_lat = 49.59
        mock_settings.return_value.home_lon = 11.00
        mock_client = _mock_dwd_client()
        mock_cls.return_value = mock_client

        await trail_condition_estimate()

        mock_client.get_rain_history.assert_called_once_with(49.59, 11.00)

    @patch("mtb_mcp.tools.intelligence_tools.DWDClient")
    async def test_output_includes_rain_info(self, mock_cls: AsyncMock) -> None:
        """Output should include rain total and temperature."""
        mock_cls.return_value = _mock_dwd_client(
            history=_make_history(total_mm=5.3),
        )

        result = await trail_condition_estimate(lat=49.59, lon=11.00)

        assert "5.3mm" in result
        assert "20.0" in result  # temperature from forecast


class TestRideScoreTool:
    """Tests for the ride_score MCP tool."""

    @patch("mtb_mcp.tools.intelligence_tools.DWDClient")
    async def test_output_format(self, mock_cls: AsyncMock) -> None:
        """ride_score should return a structured text report."""
        mock_cls.return_value = _mock_dwd_client()

        result = await ride_score(lat=49.59, lon=11.00)

        assert "Ride Score" in result
        assert "SCORE:" in result
        assert "/100" in result
        assert "Weather:" in result
        assert "Trail:" in result
        assert "Wind:" in result
        assert "Daylight:" in result

    @patch("mtb_mcp.tools.intelligence_tools.DWDClient")
    async def test_good_conditions_high_score(self, mock_cls: AsyncMock) -> None:
        """Good weather + no rain → high score."""
        mock_cls.return_value = _mock_dwd_client()

        result = await ride_score(lat=49.59, lon=11.00)

        assert "Perfect" in result or "Good" in result

    @patch("mtb_mcp.tools.intelligence_tools.DWDClient")
    async def test_surface_parameter(self, mock_cls: AsyncMock) -> None:
        """Surface parameter should appear in output."""
        mock_cls.return_value = _mock_dwd_client()

        result = await ride_score(lat=49.59, lon=11.00, surface="gravel")

        assert "gravel" in result

    @patch("mtb_mcp.tools.intelligence_tools.DWDClient")
    @patch("mtb_mcp.tools.intelligence_tools.get_settings")
    async def test_uses_home_location(
        self, mock_settings: AsyncMock, mock_cls: AsyncMock,
    ) -> None:
        """Should fall back to home location when no lat/lon given."""
        mock_settings.return_value.home_lat = 49.59
        mock_settings.return_value.home_lon = 11.00
        mock_client = _mock_dwd_client()
        mock_cls.return_value = mock_client

        await ride_score()

        mock_client.get_forecast.assert_called_once_with(49.59, 11.00)

    @patch("mtb_mcp.tools.intelligence_tools.DWDClient")
    async def test_includes_recommendation(self, mock_cls: AsyncMock) -> None:
        """Output should include a recommendation string."""
        mock_cls.return_value = _mock_dwd_client()

        result = await ride_score(lat=49.59, lon=11.00)

        # Any of the recommendation messages should be present
        recommendations = [
            "perfect riding",
            "enjoy your ride",
            "not ideal",
            "Indoor trainer",
            "Stay home",
        ]
        assert any(r in result for r in recommendations)
