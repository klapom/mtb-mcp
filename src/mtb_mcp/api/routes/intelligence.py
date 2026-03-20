"""Intelligence endpoints — ride score, trail condition, weekend planner."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from fastapi import APIRouter, Query

from mtb_mcp.api.deps import resolve_location
from mtb_mcp.api.models import err, ok
from mtb_mcp.clients.dwd import DWDClient
from mtb_mcp.intelligence.ride_score import RideScoreInput, calculate_ride_score
from mtb_mcp.intelligence.trail_condition import estimate_trail_condition
from mtb_mcp.intelligence.weekend_planner import plan_weekend

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/ride-score")
async def ride_score(
    lat: float | None = None,
    lon: float | None = None,
    ride_start_hour: int | None = None,
    ride_duration_hours: float = Query(2.0, ge=0.5, le=12.0),
    surface: str = "dirt",
) -> dict[str, Any]:
    """Calculate a ride score (0-100) combining weather, trail, wind, daylight."""
    t = time.monotonic()
    rlat, rlon = resolve_location(lat, lon)

    try:
        async with DWDClient() as client:
            forecast = await client.get_forecast(rlat, rlon)
            history = await client.get_rain_history(rlat, rlon)

        # --- Determine ride window ---
        now = datetime.now(tz=timezone.utc)
        if ride_start_hour is not None:
            ride_start = now.replace(
                hour=ride_start_hour, minute=0, second=0, microsecond=0,
            )
            if ride_start < now:
                ride_start += timedelta(days=1)
        else:
            ride_start = now

        ride_end = ride_start + timedelta(hours=ride_duration_hours)

        # --- Pick forecast hours inside the ride window ---
        ride_hours = [
            h for h in forecast.hours
            if ride_start <= h.time <= ride_end
        ]

        if ride_hours:
            avg_temp = sum(h.temp_c for h in ride_hours) / len(ride_hours)
            avg_wind = sum(h.wind_speed_kmh for h in ride_hours) / len(ride_hours)
            max_gust = max(
                (h.wind_gust_kmh or 0.0 for h in ride_hours), default=0.0,
            )
            total_precip = sum(h.precipitation_mm for h in ride_hours)
            avg_prob = (
                sum(h.precipitation_probability for h in ride_hours) / len(ride_hours)
            )
            avg_humidity = sum(h.humidity_pct for h in ride_hours) / len(ride_hours)
        else:
            # Fallback: use first available hour
            h0 = forecast.hours[0] if forecast.hours else None
            avg_temp = h0.temp_c if h0 else 15.0
            avg_wind = h0.wind_speed_kmh if h0 else 0.0
            max_gust = (h0.wind_gust_kmh or 0.0) if h0 else 0.0
            total_precip = h0.precipitation_mm if h0 else 0.0
            avg_prob = h0.precipitation_probability if h0 else 0.0
            avg_humidity = h0.humidity_pct if h0 else 50.0

        # --- Trail condition ---
        current_temp = forecast.hours[0].temp_c if forecast.hours else 15.0
        condition, _confidence, _reasoning = estimate_trail_condition(
            surface=surface,
            hourly_rain_mm=history.hourly_mm,
            current_temp_c=current_temp,
        )

        # --- Approximate sunrise / sunset ---
        day_base = ride_start.replace(hour=0, minute=0, second=0, microsecond=0)
        sunrise = day_base.replace(hour=6, minute=0)
        sunset = day_base.replace(hour=20, minute=0)

        # --- Build input & calculate ---
        score_input = RideScoreInput(
            temp_c=avg_temp,
            wind_speed_kmh=avg_wind,
            wind_gust_kmh=max_gust,
            precipitation_probability=avg_prob,
            precipitation_mm=total_precip,
            humidity_pct=avg_humidity,
            trail_condition=condition.value,
            ride_start=ride_start,
            ride_duration_hours=ride_duration_hours,
            sunrise=sunrise,
            sunset=sunset,
        )

        result = calculate_ride_score(score_input)

        return ok(
            {
                "score": result.score,
                "verdict": result.verdict,
                "weather_score": result.weather_score,
                "trail_score": result.trail_score,
                "wind_score": result.wind_score,
                "daylight_score": result.daylight_score,
                "factors": result.factors,
                "location": {"lat": rlat, "lon": rlon},
                "ride_window": {
                    "start": ride_start.isoformat(),
                    "end": ride_end.isoformat(),
                    "duration_hours": ride_duration_hours,
                },
                "surface": surface,
                "trail_condition": condition.value,
            },
            t,
        )
    except Exception as exc:
        logger.error("ride_score_error", error=str(exc))
        return err("RIDE_SCORE_ERROR", f"Failed to calculate ride score: {exc}")


@router.get("/trail-condition")
async def trail_condition(
    lat: float | None = None,
    lon: float | None = None,
    surface: str = "dirt",
) -> dict[str, Any]:
    """Estimate current trail condition based on recent rainfall and surface type."""
    t = time.monotonic()
    rlat, rlon = resolve_location(lat, lon)

    try:
        async with DWDClient() as client:
            history = await client.get_rain_history(rlat, rlon)
            forecast = await client.get_forecast(rlat, rlon)

        current_temp = forecast.hours[0].temp_c if forecast.hours else 15.0

        condition, confidence, reasoning = estimate_trail_condition(
            surface=surface,
            hourly_rain_mm=history.hourly_mm,
            current_temp_c=current_temp,
        )

        return ok(
            {
                "surface": surface,
                "condition": condition.value,
                "confidence": confidence,
                "reasoning": reasoning,
                "rain_48h_mm": history.total_mm_48h,
                "last_rain_hours_ago": history.last_rain_hours_ago,
                "current_temp_c": current_temp,
            },
            t,
        )
    except Exception as exc:
        logger.error("trail_condition_error", error=str(exc))
        return err("TRAIL_CONDITION_ERROR", f"Failed to estimate trail condition: {exc}")


@router.get("/weekend-planner")
async def weekend_planner(
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = Query(30.0, ge=1.0, le=100.0),
    preferred_distance_km: float | None = None,
    preferred_difficulty: str | None = None,
) -> dict[str, Any]:
    """Plan weekend rides — weather, trail conditions, scores, and tour suggestions."""
    t = time.monotonic()
    rlat, rlon = resolve_location(lat, lon)

    try:
        plan = await plan_weekend(
            lat=rlat,
            lon=rlon,
            radius_km=radius_km,
            preferred_distance_km=preferred_distance_km,
            preferred_difficulty=preferred_difficulty,
        )

        def _day_to_dict(day: Any) -> dict[str, Any] | None:
            if day is None:
                return None
            return {
                "date": day.date.isoformat(),
                "ride_score": day.ride_score,
                "verdict": day.verdict,
                "weather_summary": day.weather_summary,
                "trail_condition": day.trail_condition,
                "suggested_tours": day.suggested_tours,
                "reasoning": day.reasoning,
            }

        return ok(
            {
                "best_day": plan.best_day,
                "summary": plan.summary,
                "saturday": _day_to_dict(plan.saturday),
                "sunday": _day_to_dict(plan.sunday),
                "location": {"lat": rlat, "lon": rlon},
                "radius_km": radius_km,
            },
            t,
        )
    except Exception as exc:
        logger.error("weekend_planner_error", error=str(exc))
        return err("WEEKEND_PLANNER_ERROR", f"Failed to plan weekend: {exc}")
