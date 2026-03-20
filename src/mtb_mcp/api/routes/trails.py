"""Trail endpoints wrapping Overpass client + trail condition intelligence."""
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Query

from mtb_mcp.api.deps import resolve_location
from mtb_mcp.api.models import err, ok, ok_list
from mtb_mcp.clients.dwd import DWDClient
from mtb_mcp.clients.overpass import OverpassClient
from mtb_mcp.intelligence.trail_condition import estimate_trail_condition
from mtb_mcp.models.trail import MTBScale

router = APIRouter()


def _parse_mtb_scale(value: str | None) -> MTBScale | None:
    """Parse a string like 'S2' into an MTBScale enum, or None."""
    if value is None:
        return None
    try:
        return MTBScale(value)
    except ValueError:
        return None


@router.get("", include_in_schema=False)
@router.get("/")
async def list_trails(
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = Query(10, gt=0, le=100),
    min_difficulty: str | None = None,
    surface: str | None = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Find MTB trails within radius of a point."""
    t = time.monotonic()
    rlat, rlon = resolve_location(lat, lon)

    min_scale = _parse_mtb_scale(min_difficulty)
    if min_difficulty is not None and min_scale is None:
        return err(
            "VALIDATION_ERROR",
            f"Invalid min_difficulty '{min_difficulty}'. Use S0-S6.",
        )

    try:
        async with OverpassClient() as client:
            trails = await client.find_trails(
                rlat, rlon, radius_m=radius_km * 1000, min_scale=min_scale,
            )
    except Exception as exc:
        return err("EXTERNAL_API_ERROR", f"Overpass API error: {exc}")

    # Optional surface filter
    if surface is not None:
        surface_lower = surface.lower()
        trails = [
            trail for trail in trails
            if trail.surface is not None and trail.surface.value == surface_lower
        ]

    total = len(trails)
    page = trails[offset : offset + limit]
    return ok_list(
        [trail.model_dump(mode="json") for trail in page],
        total,
        t,
    )


@router.get("/{osm_id}")
async def trail_details(osm_id: int) -> dict[str, Any]:
    """Get details for a specific trail by OSM way ID."""
    t = time.monotonic()
    try:
        async with OverpassClient() as client:
            trail = await client.get_trail_details(osm_id)
    except Exception as exc:
        return err("EXTERNAL_API_ERROR", f"Overpass API error: {exc}")

    if trail is None:
        return err("NOT_FOUND", f"Trail with osm_id {osm_id} not found")

    return ok(trail.model_dump(mode="json"), t)


@router.get("/{osm_id}/condition")
async def trail_condition(
    osm_id: int,
    surface: str = Query("dirt"),
) -> dict[str, Any]:
    """Estimate trail condition based on recent weather and surface type."""
    t = time.monotonic()

    try:
        async with OverpassClient() as op_client:
            trail = await op_client.get_trail_details(osm_id)
    except Exception as exc:
        return err("EXTERNAL_API_ERROR", f"Overpass API error: {exc}")

    if trail is None:
        return err("NOT_FOUND", f"Trail with osm_id {osm_id} not found")

    # Use trail's own surface if available, otherwise use the query param
    surface_value = trail.surface.value if trail.surface is not None else surface

    # Get weather data at the trail's first geometry point (or midpoint)
    if trail.geometry:
        geo = trail.geometry[len(trail.geometry) // 2]
        wlat, wlon = geo.lat, geo.lon
    else:
        # Fall back to home location if no geometry
        wlat, wlon = resolve_location(None, None)

    try:
        async with DWDClient() as dwd_client:
            rain_history = await dwd_client.get_rain_history(wlat, wlon)
            forecast = await dwd_client.get_forecast(wlat, wlon)
    except Exception as exc:
        return err("EXTERNAL_API_ERROR", f"DWD API error: {exc}")

    # Current temperature from the first forecast hour
    current_temp_c = forecast.hours[0].temp_c if forecast.hours else 15.0

    condition_status, confidence, reasoning = estimate_trail_condition(
        surface=surface_value,
        hourly_rain_mm=rain_history.hourly_mm,
        current_temp_c=current_temp_c,
    )

    return ok(
        {
            "osm_id": osm_id,
            "trail_name": trail.name,
            "surface": surface_value,
            "condition": condition_status.value,
            "confidence": confidence,
            "rain_48h_mm": rain_history.total_mm_48h,
            "hours_since_rain": rain_history.last_rain_hours_ago,
            "reasoning": reasoning,
        },
        t,
    )
