"""Tests for the weekend planner intelligence module and MCP tool."""

from __future__ import annotations

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch

from mtb_mcp.intelligence.weekend_planner import (
    DayRecommendation,
    WeekendPlan,
    _build_summary,
    _compute_day_score,
    _hours_for_date,
    _next_weekend,
    _summarize_weather,
    plan_weekend,
)
from mtb_mcp.models.tour import TourDifficulty, TourSource, TourSummary
from mtb_mcp.models.weather import (
    HourlyForecast,
    RainHistory,
    WeatherCondition,
    WeatherForecast,
)
from mtb_mcp.tools.intelligence_tools import weekend_planner

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _make_hours(
    target_date: date,
    temp_c: float = 20.0,
    wind: float = 5.0,
    precip_mm: float = 0.0,
    precip_prob: float = 0.0,
    condition: WeatherCondition = WeatherCondition.clear,
) -> list[HourlyForecast]:
    """Create a full day (6-20h) of forecast hours for a specific date."""
    return [
        HourlyForecast(
            time=datetime(target_date.year, target_date.month, target_date.day,
                          hour, 0, tzinfo=timezone.utc),
            temp_c=temp_c,
            wind_speed_kmh=wind,
            wind_gust_kmh=wind * 1.5,
            precipitation_mm=precip_mm,
            precipitation_probability=precip_prob,
            humidity_pct=50.0,
            condition=condition,
        )
        for hour in range(6, 21)
    ]


def _make_forecast(
    sat_hours: list[HourlyForecast],
    sun_hours: list[HourlyForecast],
) -> WeatherForecast:
    """Create a WeatherForecast containing hours for Saturday and Sunday."""
    return WeatherForecast(
        location_name="NUERNBERG",
        lat=49.59,
        lon=11.00,
        hours=sat_hours + sun_hours,
        generated_at=datetime.now(tz=timezone.utc),
    )


def _make_history(
    hourly_mm: list[float] | None = None,
    total_mm: float = 0.0,
) -> RainHistory:
    """Create a test RainHistory (dry by default)."""
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
    forecast: WeatherForecast, history: RainHistory | None = None,
) -> AsyncMock:
    """Return a mock DWDClient context manager."""
    mock_client = AsyncMock()
    mock_client.get_forecast.return_value = forecast
    mock_client.get_rain_history.return_value = history or _make_history()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


def _make_tours() -> list[TourSummary]:
    """Create test tours."""
    return [
        TourSummary(
            id="t1",
            source=TourSource.komoot,
            name="Erlangen Forest Loop",
            distance_km=25.0,
            difficulty=TourDifficulty.moderate,
            url="https://komoot.com/tour/t1",
        ),
        TourSummary(
            id="t2",
            source=TourSource.gps_tour,
            name="Brucker Lache Trail",
            distance_km=15.0,
            difficulty=TourDifficulty.difficult,
            url="https://gps-tour.info/detail.t2.html",
        ),
    ]


# ---------------------------------------------------------------------------
# Unit tests for helper functions
# ---------------------------------------------------------------------------


class TestNextWeekend:
    """Tests for _next_weekend()."""

    @patch("mtb_mcp.intelligence.weekend_planner.datetime")
    def test_weekday_returns_upcoming_weekend(self, mock_dt: AsyncMock) -> None:
        """A Wednesday should return the upcoming Saturday/Sunday."""
        # 2025-07-16 is a Wednesday
        mock_dt.now.return_value = datetime(2025, 7, 16, 12, 0, tzinfo=timezone.utc)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        sat, sun = _next_weekend()
        assert sat == date(2025, 7, 19)
        assert sun == date(2025, 7, 20)

    @patch("mtb_mcp.intelligence.weekend_planner.datetime")
    def test_saturday_returns_this_weekend(self, mock_dt: AsyncMock) -> None:
        """A Saturday should return this Saturday/Sunday."""
        mock_dt.now.return_value = datetime(2025, 7, 19, 10, 0, tzinfo=timezone.utc)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        sat, sun = _next_weekend()
        assert sat == date(2025, 7, 19)
        assert sun == date(2025, 7, 20)


class TestHoursForDate:
    """Tests for _hours_for_date()."""

    def test_filters_correct_date(self) -> None:
        """Only hours matching the target date (6-20h) are returned."""
        target = date(2025, 7, 19)
        other = date(2025, 7, 20)
        forecast = _make_forecast(
            _make_hours(target, temp_c=22.0),
            _make_hours(other, temp_c=15.0),
        )
        result = _hours_for_date(forecast, target)
        assert len(result) == 15  # 6..20 inclusive
        assert all(h.temp_c == 22.0 for h in result)


class TestSummarizeWeather:
    """Tests for _summarize_weather()."""

    def test_dry_weather_summary(self) -> None:
        """Dry, warm weather summary."""
        hours = _make_hours(date(2025, 7, 19), temp_c=22.0, wind=8.0)
        result = _summarize_weather(hours)
        assert "22" in result
        assert "wind" in result
        assert "dry" in result

    def test_rainy_weather_summary(self) -> None:
        """Rainy weather shows precipitation info."""
        hours = _make_hours(date(2025, 7, 19), precip_mm=2.0, precip_prob=80.0)
        result = _summarize_weather(hours)
        assert "rain" in result

    def test_empty_hours(self) -> None:
        """Empty hours list returns a descriptive message."""
        result = _summarize_weather([])
        assert "No forecast data" in result


class TestComputeDayScore:
    """Tests for _compute_day_score()."""

    def test_good_day_high_score(self) -> None:
        """Clear, warm weather should produce a high score."""
        target = date(2025, 7, 19)
        hours = _make_hours(target, temp_c=20.0, wind=5.0)
        history = _make_history()
        score, verdict, trail, _reasoning = _compute_day_score(
            hours, history, target,
        )
        assert score >= 60
        assert verdict in ("Perfect", "Good")
        assert trail == "dry"

    def test_rainy_day_low_score(self) -> None:
        """Heavy rain should produce a low score."""
        target = date(2025, 7, 19)
        hours = _make_hours(target, temp_c=10.0, precip_mm=5.0, precip_prob=90.0)
        rain = [5.0, 5.0, 3.0] + [0.0] * 45
        history = _make_history(hourly_mm=rain, total_mm=13.0)
        score, verdict, _trail, _reasoning = _compute_day_score(
            hours, history, target,
        )
        assert score < 40
        assert verdict in ("Poor", "Stay Home")

    def test_no_hours_returns_zero(self) -> None:
        """No forecast hours should return score 0."""
        target = date(2025, 7, 19)
        history = _make_history()
        score, verdict, trail, reasoning = _compute_day_score(
            [], history, target,
        )
        assert score == 0
        assert verdict == "Stay Home"
        assert trail == "unknown"


class TestBuildSummary:
    """Tests for _build_summary()."""

    def _make_rec(self, score: int, verdict: str) -> DayRecommendation:
        return DayRecommendation(
            date=date(2025, 7, 19),
            ride_score=score,
            verdict=verdict,
            weather_summary="test",
            trail_condition="dry",
        )

    def test_both_good(self) -> None:
        summary = _build_summary("both", self._make_rec(80, "Perfect"),
                                 self._make_rec(70, "Good"))
        assert "Both days" in summary

    def test_neither_good(self) -> None:
        summary = _build_summary("neither", self._make_rec(20, "Poor"),
                                 self._make_rec(15, "Stay Home"))
        assert "indoor" in summary.lower() or "indoor" in summary or "Tough" in summary

    def test_saturday_best(self) -> None:
        summary = _build_summary("saturday", self._make_rec(75, "Good"),
                                 self._make_rec(30, "Poor"))
        assert "Saturday" in summary

    def test_sunday_best(self) -> None:
        summary = _build_summary("sunday", self._make_rec(30, "Poor"),
                                 self._make_rec(75, "Good"))
        assert "Sunday" in summary


# ---------------------------------------------------------------------------
# Integration tests for plan_weekend
# ---------------------------------------------------------------------------


class TestPlanWeekend:
    """Tests for the plan_weekend orchestration function."""

    @patch("mtb_mcp.intelligence.weekend_planner._search_tours")
    @patch("mtb_mcp.intelligence.weekend_planner.DWDClient")
    @patch("mtb_mcp.intelligence.weekend_planner._next_weekend")
    async def test_good_saturday_rainy_sunday(
        self,
        mock_weekend: AsyncMock,
        mock_dwd_cls: AsyncMock,
        mock_search: AsyncMock,
    ) -> None:
        """Good Saturday + rainy Sunday -> best_day='saturday'."""
        sat = date(2025, 7, 19)
        sun = date(2025, 7, 20)
        mock_weekend.return_value = (sat, sun)

        sat_hours = _make_hours(sat, temp_c=22.0, wind=5.0)
        sun_hours = _make_hours(sun, temp_c=10.0, precip_mm=5.0, precip_prob=90.0)
        rain_hist = [5.0, 4.0, 3.0] + [0.0] * 45
        forecast = _make_forecast(sat_hours, sun_hours)
        history = _make_history(hourly_mm=rain_hist, total_mm=12.0)

        mock_dwd_cls.return_value = _mock_dwd_client(forecast, history)
        mock_search.return_value = _make_tours()

        plan = await plan_weekend(lat=49.59, lon=11.00)

        assert plan.best_day == "saturday"
        assert plan.saturday is not None
        assert plan.sunday is not None
        assert plan.saturday.ride_score > plan.sunday.ride_score
        # Saturday should have tour suggestions, Sunday should not (score < 40)
        assert len(plan.saturday.suggested_tours) > 0

    @patch("mtb_mcp.intelligence.weekend_planner._search_tours")
    @patch("mtb_mcp.intelligence.weekend_planner.DWDClient")
    @patch("mtb_mcp.intelligence.weekend_planner._next_weekend")
    async def test_both_days_bad(
        self,
        mock_weekend: AsyncMock,
        mock_dwd_cls: AsyncMock,
        mock_search: AsyncMock,
    ) -> None:
        """Both days rainy -> best_day='neither', no tour search."""
        sat = date(2025, 7, 19)
        sun = date(2025, 7, 20)
        mock_weekend.return_value = (sat, sun)

        sat_hours = _make_hours(sat, temp_c=5.0, precip_mm=8.0, precip_prob=95.0)
        sun_hours = _make_hours(sun, temp_c=4.0, precip_mm=10.0, precip_prob=95.0)
        rain_hist = [8.0, 8.0, 5.0] + [0.0] * 45
        forecast = _make_forecast(sat_hours, sun_hours)
        history = _make_history(hourly_mm=rain_hist, total_mm=21.0)

        mock_dwd_cls.return_value = _mock_dwd_client(forecast, history)
        mock_search.return_value = []

        plan = await plan_weekend(lat=49.59, lon=11.00)

        assert plan.best_day == "neither"
        assert plan.saturday is not None
        assert plan.sunday is not None
        assert plan.saturday.ride_score < 40
        assert plan.sunday.ride_score < 40
        # No tours searched when both days are bad
        mock_search.assert_not_called()

    @patch("mtb_mcp.intelligence.weekend_planner._search_tours")
    @patch("mtb_mcp.intelligence.weekend_planner.DWDClient")
    @patch("mtb_mcp.intelligence.weekend_planner._next_weekend")
    async def test_both_days_good(
        self,
        mock_weekend: AsyncMock,
        mock_dwd_cls: AsyncMock,
        mock_search: AsyncMock,
    ) -> None:
        """Both days sunny -> best_day='both', tours suggested for both."""
        sat = date(2025, 7, 19)
        sun = date(2025, 7, 20)
        mock_weekend.return_value = (sat, sun)

        sat_hours = _make_hours(sat, temp_c=22.0, wind=5.0)
        sun_hours = _make_hours(sun, temp_c=24.0, wind=3.0)
        forecast = _make_forecast(sat_hours, sun_hours)
        history = _make_history()

        mock_dwd_cls.return_value = _mock_dwd_client(forecast, history)
        mock_search.return_value = _make_tours()

        plan = await plan_weekend(lat=49.59, lon=11.00)

        assert plan.best_day == "both"
        assert plan.saturday is not None
        assert plan.sunday is not None
        assert plan.saturday.ride_score >= 60
        assert plan.sunday.ride_score >= 60
        assert len(plan.saturday.suggested_tours) > 0
        assert len(plan.sunday.suggested_tours) > 0

    @patch("mtb_mcp.intelligence.weekend_planner._search_tours")
    @patch("mtb_mcp.intelligence.weekend_planner.DWDClient")
    @patch("mtb_mcp.intelligence.weekend_planner._next_weekend")
    async def test_tour_suggestions_when_good(
        self,
        mock_weekend: AsyncMock,
        mock_dwd_cls: AsyncMock,
        mock_search: AsyncMock,
    ) -> None:
        """Tour suggestions are included when a day is rideable."""
        sat = date(2025, 7, 19)
        sun = date(2025, 7, 20)
        mock_weekend.return_value = (sat, sun)

        sat_hours = _make_hours(sat, temp_c=22.0, wind=5.0)
        sun_hours = _make_hours(sun, temp_c=22.0, wind=5.0)
        forecast = _make_forecast(sat_hours, sun_hours)

        mock_dwd_cls.return_value = _mock_dwd_client(forecast)
        tours = _make_tours()
        mock_search.return_value = tours

        plan = await plan_weekend(lat=49.59, lon=11.00)

        # Tours should be searched and included
        mock_search.assert_called_once()
        assert plan.saturday is not None
        assert any("Erlangen" in t for t in plan.saturday.suggested_tours)

    @patch("mtb_mcp.intelligence.weekend_planner._search_tours")
    @patch("mtb_mcp.intelligence.weekend_planner.DWDClient")
    @patch("mtb_mcp.intelligence.weekend_planner._next_weekend")
    async def test_best_day_logic_saturday_wins(
        self,
        mock_weekend: AsyncMock,
        mock_dwd_cls: AsyncMock,
        mock_search: AsyncMock,
    ) -> None:
        """When Saturday is good and Sunday is fair, best_day='saturday'."""
        sat = date(2025, 7, 19)
        sun = date(2025, 7, 20)
        mock_weekend.return_value = (sat, sun)

        # Saturday: perfect; Sunday: cold + very windy + rain = poor
        sat_hours = _make_hours(sat, temp_c=22.0, wind=5.0)
        sun_hours = _make_hours(
            sun, temp_c=4.0, wind=40.0, precip_mm=3.0, precip_prob=70.0,
        )
        forecast = _make_forecast(sat_hours, sun_hours)

        mock_dwd_cls.return_value = _mock_dwd_client(forecast)
        mock_search.return_value = _make_tours()

        plan = await plan_weekend(lat=49.59, lon=11.00)

        assert plan.best_day == "saturday"
        assert plan.saturday is not None
        assert plan.sunday is not None
        assert plan.saturday.ride_score > plan.sunday.ride_score


# ---------------------------------------------------------------------------
# MCP tool tests
# ---------------------------------------------------------------------------


class TestWeekendPlannerTool:
    """Tests for the weekend_planner MCP tool."""

    @patch("mtb_mcp.intelligence.weekend_planner.plan_weekend")
    async def test_output_format(self, mock_plan: AsyncMock) -> None:
        """Tool should return structured text with all sections."""
        mock_plan.return_value = WeekendPlan(
            saturday=DayRecommendation(
                date=date(2025, 7, 19),
                ride_score=85,
                verdict="Perfect",
                weather_summary="20-24\u00b0C, wind 5 km/h, dry",
                trail_condition="dry",
                suggested_tours=["Erlangen Forest Loop | 25.0 km | moderate"],
                reasoning="Low absorbed water on dirt",
            ),
            sunday=DayRecommendation(
                date=date(2025, 7, 20),
                ride_score=35,
                verdict="Poor",
                weather_summary="8-12\u00b0C, wind 20 km/h, rain 5.0mm",
                trail_condition="wet",
                reasoning="Significant moisture on dirt",
            ),
            best_day="saturday",
            summary="Saturday is your best bet! Score: 85/100.",
        )

        result = await weekend_planner(lat=49.59, lon=11.00)

        assert "Weekend Ride Plan" in result
        assert "Best day: saturday" in result
        assert "SATURDAY" in result
        assert "SUNDAY" in result
        assert "85/100" in result
        assert "Perfect" in result
        assert "Suggested tours:" in result
        assert "Erlangen Forest Loop" in result

    @patch("mtb_mcp.intelligence.weekend_planner.plan_weekend")
    @patch("mtb_mcp.tools.intelligence_tools.get_settings")
    async def test_uses_home_location(
        self, mock_settings: AsyncMock, mock_plan: AsyncMock,
    ) -> None:
        """Should fall back to home location when no lat/lon given."""
        mock_settings.return_value.home_lat = 49.59
        mock_settings.return_value.home_lon = 11.00
        mock_plan.return_value = WeekendPlan(
            best_day="neither",
            summary="Tough weekend.",
        )

        await weekend_planner()

        mock_plan.assert_called_once_with(
            lat=49.59,
            lon=11.00,
            radius_km=30.0,
            preferred_distance_km=None,
            preferred_difficulty=None,
        )

    @patch("mtb_mcp.intelligence.weekend_planner.plan_weekend")
    async def test_no_tours_when_bad_weather(self, mock_plan: AsyncMock) -> None:
        """No tour suggestions for bad weather days."""
        mock_plan.return_value = WeekendPlan(
            saturday=DayRecommendation(
                date=date(2025, 7, 19),
                ride_score=15,
                verdict="Stay Home",
                weather_summary="rain all day",
                trail_condition="muddy",
            ),
            sunday=DayRecommendation(
                date=date(2025, 7, 20),
                ride_score=20,
                verdict="Poor",
                weather_summary="cold and windy",
                trail_condition="wet",
            ),
            best_day="neither",
            summary="Tough weekend.",
        )

        result = await weekend_planner(lat=49.59, lon=11.00)

        assert "Suggested tours:" not in result
