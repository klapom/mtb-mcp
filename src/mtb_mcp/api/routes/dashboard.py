"""Dashboard endpoint — aggregated overview in one call."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from fastapi import APIRouter

from mtb_mcp.api.deps import get_cached_settings, resolve_location
from mtb_mcp.api.models import ok
from mtb_mcp.clients.dwd import DWDClient
from mtb_mcp.intelligence.ride_score import RideScoreInput, calculate_ride_score
from mtb_mcp.intelligence.trail_condition import estimate_trail_condition
from mtb_mcp.intelligence.wear_engine import calculate_wear_pct, get_wear_status, km_remaining
from mtb_mcp.storage.bike_garage import BikeGarage
from mtb_mcp.storage.database import Database

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get("/dashboard")
async def dashboard(
    lat: float | None = None,
    lon: float | None = None,
    surface: str = "dirt",
) -> dict[str, Any]:
    """Aggregated dashboard: ride score, weather, trail, weekend preview, service, timer."""
    t = time.monotonic()
    rlat, rlon = resolve_location(lat, lon)

    result: dict[str, Any] = {
        "ride_score": None,
        "weather_current": None,
        "trail_condition": None,
        "weekend_preview": None,
        "next_service": None,
        "active_timer": None,
    }

    # --- Fetch DWD data once, reuse for multiple sections ---
    forecast = None
    history = None
    try:
        async with DWDClient() as client:
            forecast = await client.get_forecast(rlat, rlon)
            history = await client.get_rain_history(rlat, rlon)
    except Exception as exc:
        logger.warning("dashboard.dwd_error", error=str(exc))

    # --- 1. ride_score ---
    try:
        if forecast is not None and history is not None:
            now = datetime.now(tz=timezone.utc)
            current_temp = forecast.hours[0].temp_c if forecast.hours else 15.0

            condition, _confidence, _reasoning = estimate_trail_condition(
                surface=surface,
                hourly_rain_mm=history.hourly_mm,
                current_temp_c=current_temp,
            )

            h0 = forecast.hours[0] if forecast.hours else None
            score_input = RideScoreInput(
                temp_c=h0.temp_c if h0 else 15.0,
                wind_speed_kmh=h0.wind_speed_kmh if h0 else 0.0,
                wind_gust_kmh=(h0.wind_gust_kmh or 0.0) if h0 else 0.0,
                precipitation_probability=h0.precipitation_probability if h0 else 0.0,
                precipitation_mm=h0.precipitation_mm if h0 else 0.0,
                humidity_pct=h0.humidity_pct if h0 else 50.0,
                trail_condition=condition.value,
                ride_start=now,
                ride_duration_hours=2.0,
                sunrise=now.replace(hour=6, minute=0, second=0, microsecond=0),
                sunset=now.replace(hour=20, minute=0, second=0, microsecond=0),
            )

            score_result = calculate_ride_score(score_input)
            result["ride_score"] = {
                "score": score_result.score,
                "verdict": score_result.verdict,
                "weather_score": score_result.weather_score,
                "trail_score": score_result.trail_score,
                "wind_score": score_result.wind_score,
                "daylight_score": score_result.daylight_score,
                "factors": score_result.factors,
            }
    except Exception as exc:
        logger.warning("dashboard.ride_score_error", error=str(exc))

    # --- 2. weather_current ---
    try:
        if forecast is not None and forecast.hours:
            h = forecast.hours[0]
            result["weather_current"] = {
                "time": h.time.isoformat(),
                "temp_c": h.temp_c,
                "wind_speed_kmh": h.wind_speed_kmh,
                "wind_gust_kmh": h.wind_gust_kmh,
                "precipitation_mm": h.precipitation_mm,
                "precipitation_probability": h.precipitation_probability,
                "humidity_pct": h.humidity_pct,
                "condition": h.condition.value,
            }
    except Exception as exc:
        logger.warning("dashboard.weather_current_error", error=str(exc))

    # --- 3. trail_condition ---
    try:
        if forecast is not None and history is not None:
            current_temp = forecast.hours[0].temp_c if forecast.hours else 15.0
            condition, confidence, reasoning = estimate_trail_condition(
                surface=surface,
                hourly_rain_mm=history.hourly_mm,
                current_temp_c=current_temp,
            )
            result["trail_condition"] = {
                "surface": surface,
                "condition": condition.value,
                "confidence": confidence,
                "reasoning": reasoning,
                "rain_48h_mm": history.total_mm_48h,
            }
    except Exception as exc:
        logger.warning("dashboard.trail_condition_error", error=str(exc))

    # --- 4. weekend_preview (simplified: Saturday/Sunday scores) ---
    try:
        if forecast is not None and history is not None:
            today = datetime.now(tz=timezone.utc).date()
            days_until_saturday = (5 - today.weekday()) % 7
            if days_until_saturday == 0 and today.weekday() != 5:
                days_until_saturday = 7
            saturday = today + timedelta(days=days_until_saturday)
            if today.weekday() == 5:
                saturday = today
            elif today.weekday() == 6:
                saturday = today - timedelta(days=1)
            sunday = saturday + timedelta(days=1)

            preview: dict[str, Any] = {}
            for label, target_date in [("saturday", saturday), ("sunday", sunday)]:
                day_hours = [
                    h for h in forecast.hours
                    if h.time.date() == target_date and 6 <= h.time.hour <= 20
                ]
                if not day_hours:
                    preview[label] = None
                    continue

                ride_hours = [h for h in day_hours if 10 <= h.time.hour <= 12]
                if not ride_hours:
                    ride_hours = day_hours

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

                cond_temp = day_hours[0].temp_c
                cond, _cf, _re = estimate_trail_condition(
                    surface=surface,
                    hourly_rain_mm=history.hourly_mm,
                    current_temp_c=cond_temp,
                )

                day_base = datetime(
                    target_date.year, target_date.month, target_date.day,
                    tzinfo=timezone.utc,
                )
                inp = RideScoreInput(
                    temp_c=avg_temp,
                    wind_speed_kmh=avg_wind,
                    wind_gust_kmh=max_gust,
                    precipitation_probability=avg_prob,
                    precipitation_mm=total_precip,
                    humidity_pct=avg_humidity,
                    trail_condition=cond.value,
                    ride_start=day_base.replace(hour=10, minute=0),
                    ride_duration_hours=2.0,
                    sunrise=day_base.replace(hour=6, minute=0),
                    sunset=day_base.replace(hour=20, minute=0),
                )

                day_result = calculate_ride_score(inp)
                preview[label] = {
                    "date": target_date.isoformat(),
                    "score": day_result.score,
                    "verdict": day_result.verdict,
                }

            result["weekend_preview"] = preview
    except Exception as exc:
        logger.warning("dashboard.weekend_preview_error", error=str(exc))

    # --- 5. next_service (most worn component from bike garage) ---
    try:
        settings = get_cached_settings()
        db = Database(settings.resolved_db_path)
        await db.initialize()
        try:
            garage = BikeGarage(db)
            bikes = await garage.list_bikes()

            most_worn: dict[str, Any] | None = None
            highest_pct = -1.0

            for bike in bikes:
                for comp in bike.components:
                    pct = calculate_wear_pct(
                        comp.current_effective_km,
                        comp.current_hours,
                        comp.installed_date,
                        comp.type.value,
                    )
                    if pct > highest_pct:
                        highest_pct = pct
                        status = get_wear_status(
                            comp.current_effective_km,
                            comp.current_hours,
                            comp.installed_date,
                            comp.type.value,
                        )
                        remaining = km_remaining(
                            comp.current_effective_km, comp.type.value,
                        )
                        most_worn = {
                            "bike": bike.name,
                            "component_type": comp.type.value,
                            "brand": comp.brand,
                            "model": comp.model,
                            "wear_pct": round(pct, 1),
                            "status": status,
                            "km_remaining": round(remaining, 0) if remaining is not None else None,
                        }

            result["next_service"] = most_worn
        finally:
            await db.close()
    except Exception as exc:
        logger.warning("dashboard.next_service_error", error=str(exc))

    # --- 6. active_timer (from safety_timers table) ---
    try:
        settings = get_cached_settings()
        db = Database(settings.resolved_db_path)
        await db.initialize()
        try:
            timer = await db.fetch_one(
                "SELECT * FROM safety_timers WHERE status = 'active' "
                "ORDER BY created_at DESC LIMIT 1",
            )
            if timer is not None:
                expected_return = datetime.fromisoformat(str(timer["expected_return"]))
                now_utc = datetime.now(tz=timezone.utc)
                if expected_return.tzinfo is None:
                    expected_return = expected_return.replace(tzinfo=timezone.utc)

                is_overdue = now_utc > expected_return
                result["active_timer"] = {
                    "timer_id": timer["id"],
                    "expected_return": expected_return.isoformat(),
                    "ride_description": timer.get("ride_description"),
                    "emergency_contact": timer.get("emergency_contact"),
                    "status": "overdue" if is_overdue else "active",
                }
        finally:
            await db.close()
    except Exception as exc:
        logger.warning("dashboard.active_timer_error", error=str(exc))

    return ok(result, t)
