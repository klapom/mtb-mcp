"""Weekend ride planner -- combines weather, trails, fitness, and tours.

Orchestrates existing subsystems to produce proactive weekend ride recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

import structlog

from mtb_mcp.clients.dwd import DWDClient
from mtb_mcp.clients.gpstour import GPSTourClient
from mtb_mcp.clients.komoot import KomootClient
from mtb_mcp.config import get_settings
from mtb_mcp.intelligence.ride_score import RideScoreInput, calculate_ride_score
from mtb_mcp.intelligence.tour_fusion import deduplicate_tours, rank_tours
from mtb_mcp.intelligence.trail_condition import estimate_trail_condition
from mtb_mcp.models.tour import TourSummary
from mtb_mcp.models.weather import HourlyForecast, RainHistory, WeatherForecast

logger = structlog.get_logger(__name__)


@dataclass
class DayRecommendation:
    """Recommendation for a single day of riding."""

    date: date
    ride_score: int  # 0-100
    verdict: str
    weather_summary: str
    trail_condition: str
    suggested_tours: list[str] = field(default_factory=list)  # Tour names/descriptions
    reasoning: str = ""


@dataclass
class WeekendPlan:
    """Full weekend plan with recommendations for Saturday and Sunday."""

    saturday: DayRecommendation | None = None
    sunday: DayRecommendation | None = None
    best_day: str | None = None  # "saturday", "sunday", "both", "neither"
    summary: str = ""


def _next_weekend() -> tuple[date, date]:
    """Return (saturday, sunday) for the upcoming weekend.

    If today is Saturday, returns this weekend.
    If today is Sunday, returns this weekend (today as Sunday).
    """
    today = datetime.now(tz=timezone.utc).date()
    days_until_saturday = (5 - today.weekday()) % 7
    if days_until_saturday == 0 and today.weekday() == 5:
        # Today is Saturday
        saturday = today
    elif today.weekday() == 6:
        # Today is Sunday -- return yesterday (Saturday) and today
        saturday = today - timedelta(days=1)
    else:
        if days_until_saturday == 0:
            days_until_saturday = 7
        saturday = today + timedelta(days=days_until_saturday)
    sunday = saturday + timedelta(days=1)
    return saturday, sunday


def _hours_for_date(
    forecast: WeatherForecast, target_date: date,
) -> list[HourlyForecast]:
    """Extract forecast hours for a specific date (daytime: 6-20 UTC)."""
    return [
        h for h in forecast.hours
        if h.time.date() == target_date and 6 <= h.time.hour <= 20
    ]


def _summarize_weather(hours: list[HourlyForecast]) -> str:
    """Build a human-readable weather summary from forecast hours."""
    if not hours:
        return "No forecast data available"

    avg_temp = sum(h.temp_c for h in hours) / len(hours)
    max_temp = max(h.temp_c for h in hours)
    min_temp = min(h.temp_c for h in hours)
    avg_wind = sum(h.wind_speed_kmh for h in hours) / len(hours)
    total_precip = sum(h.precipitation_mm for h in hours)
    avg_precip_prob = sum(h.precipitation_probability for h in hours) / len(hours)

    parts: list[str] = [f"{min_temp:.0f}-{max_temp:.0f}\u00b0C (avg {avg_temp:.0f}\u00b0C)"]
    parts.append(f"wind {avg_wind:.0f} km/h")

    if total_precip > 0.1:
        parts.append(f"rain {total_precip:.1f}mm ({avg_precip_prob:.0f}% prob)")
    elif avg_precip_prob > 20:
        parts.append(f"rain chance {avg_precip_prob:.0f}%")
    else:
        parts.append("dry")

    return ", ".join(parts)


def _compute_day_score(
    hours: list[HourlyForecast],
    history: RainHistory,
    target_date: date,
    surface: str = "dirt",
) -> tuple[int, str, str, str]:
    """Compute ride score for a day, returning (score, verdict, trail_condition, reasoning).

    Uses a 10:00-12:00 ride window as the default scoring window.
    """
    if not hours:
        return 0, "Stay Home", "unknown", "No forecast data available for this day"

    # Use midday hours (10-12) as the ride window
    ride_hours = [h for h in hours if 10 <= h.time.hour <= 12]
    if not ride_hours:
        ride_hours = hours  # Fallback to all daytime hours

    avg_temp = sum(h.temp_c for h in ride_hours) / len(ride_hours)
    avg_wind = sum(h.wind_speed_kmh for h in ride_hours) / len(ride_hours)
    max_gust = max((h.wind_gust_kmh or 0.0 for h in ride_hours), default=0.0)
    total_precip = sum(h.precipitation_mm for h in ride_hours)
    avg_prob = sum(h.precipitation_probability for h in ride_hours) / len(ride_hours)
    avg_humidity = sum(h.humidity_pct for h in ride_hours) / len(ride_hours)

    # Trail condition
    current_temp = hours[0].temp_c
    condition, _confidence, reasoning = estimate_trail_condition(
        surface=surface,
        hourly_rain_mm=history.hourly_mm,
        current_temp_c=current_temp,
    )

    # Ride score -- assume 10:00 start, 2h duration
    day_base = datetime(
        target_date.year, target_date.month, target_date.day,
        tzinfo=timezone.utc,
    )
    ride_start = day_base.replace(hour=10, minute=0)
    sunrise = day_base.replace(hour=6, minute=0)
    sunset = day_base.replace(hour=20, minute=0)

    score_input = RideScoreInput(
        temp_c=avg_temp,
        wind_speed_kmh=avg_wind,
        wind_gust_kmh=max_gust,
        precipitation_probability=avg_prob,
        precipitation_mm=total_precip,
        humidity_pct=avg_humidity,
        trail_condition=condition.value,
        ride_start=ride_start,
        ride_duration_hours=2.0,
        sunrise=sunrise,
        sunset=sunset,
    )

    result = calculate_ride_score(score_input)
    return result.score, result.verdict, condition.value, reasoning


def _format_tour_line(tour: TourSummary) -> str:
    """Format a tour for display in a weekend plan."""
    parts: list[str] = [tour.name]
    if tour.distance_km is not None:
        parts.append(f"{tour.distance_km} km")
    if tour.difficulty is not None:
        parts.append(tour.difficulty.value)
    return " | ".join(parts)


async def _search_tours(
    lat: float,
    lon: float,
    radius_km: float,
    preferred_distance_km: float | None,
    preferred_difficulty: str | None,
) -> list[TourSummary]:
    """Search and rank tours from all sources."""
    settings = get_settings()
    all_results: list[TourSummary] = []

    # Komoot
    if settings.komoot_email:
        try:
            async with KomootClient(
                email=settings.komoot_email,
                password=settings.komoot_password,
            ) as komoot:
                komoot_results = await komoot.search_tours(
                    lat=lat, lon=lon, radius_km=radius_km,
                )
                all_results.extend(komoot_results)
        except Exception as exc:
            logger.warning("weekend_planner_komoot_error", error=str(exc))

    # GPS-Tour.info via SearXNG
    try:
        async with GPSTourClient(
            searxng_url=settings.searxng_url,
            username=settings.gpstour_username,
            password=settings.gpstour_password,
        ) as gpstour:
            gpstour_results = await gpstour.search_tours(
                query=f"{lat},{lon}",
            )
            all_results.extend(gpstour_results)
    except Exception as exc:
        logger.warning("weekend_planner_gpstour_error", error=str(exc))

    if not all_results:
        return []

    deduped = deduplicate_tours(all_results)
    ranked = rank_tours(
        deduped,
        preference_distance_km=preferred_distance_km,
        preference_difficulty=preferred_difficulty,
    )
    return ranked


async def plan_weekend(
    lat: float,
    lon: float,
    radius_km: float = 30.0,
    preferred_distance_km: float | None = None,
    preferred_difficulty: str | None = None,
) -> WeekendPlan:
    """Generate weekend ride recommendations.

    Steps:
    1. Get weather forecast for Saturday + Sunday
    2. Estimate trail conditions for each day
    3. Calculate ride score for each day
    4. Search for suitable tours (if at least one day is rideable)
    5. Rank and recommend
    """
    saturday, sunday = _next_weekend()

    # Fetch weather and rain history
    async with DWDClient() as client:
        forecast = await client.get_forecast(lat, lon)
        history = await client.get_rain_history(lat, lon)

    # Compute scores for each day
    sat_hours = _hours_for_date(forecast, saturday)
    sun_hours = _hours_for_date(forecast, sunday)

    sat_score, sat_verdict, sat_trail, sat_reasoning = _compute_day_score(
        sat_hours, history, saturday,
    )
    sun_score, sun_verdict, sun_trail, sun_reasoning = _compute_day_score(
        sun_hours, history, sunday,
    )

    sat_weather = _summarize_weather(sat_hours)
    sun_weather = _summarize_weather(sun_hours)

    # Search tours if at least one day is rideable (score >= 40)
    tours: list[TourSummary] = []
    if sat_score >= 40 or sun_score >= 40:
        tours = await _search_tours(
            lat, lon, radius_km, preferred_distance_km, preferred_difficulty,
        )

    tour_lines = [_format_tour_line(t) for t in tours[:5]]

    # Build day recommendations
    sat_rec = DayRecommendation(
        date=saturday,
        ride_score=sat_score,
        verdict=sat_verdict,
        weather_summary=sat_weather,
        trail_condition=sat_trail,
        suggested_tours=tour_lines if sat_score >= 40 else [],
        reasoning=sat_reasoning,
    )
    sun_rec = DayRecommendation(
        date=sunday,
        ride_score=sun_score,
        verdict=sun_verdict,
        weather_summary=sun_weather,
        trail_condition=sun_trail,
        suggested_tours=tour_lines if sun_score >= 40 else [],
        reasoning=sun_reasoning,
    )

    # Determine best day
    if sat_score >= 60 and sun_score >= 60:
        best_day = "both"
    elif sat_score < 40 and sun_score < 40:
        best_day = "neither"
    elif sat_score >= sun_score:
        best_day = "saturday"
    else:
        best_day = "sunday"

    # Build summary
    summary = _build_summary(best_day, sat_rec, sun_rec)

    return WeekendPlan(
        saturday=sat_rec,
        sunday=sun_rec,
        best_day=best_day,
        summary=summary,
    )


def _build_summary(
    best_day: str,
    sat: DayRecommendation,
    sun: DayRecommendation,
) -> str:
    """Build a human-readable weekend summary."""
    if best_day == "both":
        return (
            f"Great weekend ahead! Both days look good for riding. "
            f"Saturday scores {sat.ride_score}/100, Sunday {sun.ride_score}/100."
        )
    if best_day == "neither":
        return (
            f"Tough weekend for riding. Saturday scores {sat.ride_score}/100 "
            f"({sat.verdict}), Sunday {sun.ride_score}/100 ({sun.verdict}). "
            f"Consider indoor training or a road ride."
        )
    if best_day == "saturday":
        return (
            f"Saturday is your best bet! Score: {sat.ride_score}/100 ({sat.verdict}). "
            f"Sunday looks worse at {sun.ride_score}/100 ({sun.verdict})."
        )
    # sunday
    return (
        f"Sunday is the day to ride! Score: {sun.ride_score}/100 ({sun.verdict}). "
        f"Saturday is less ideal at {sat.ride_score}/100 ({sat.verdict})."
    )
