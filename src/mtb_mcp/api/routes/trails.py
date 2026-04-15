"""Trail endpoints wrapping Overpass client + trail condition intelligence."""
from __future__ import annotations

import math
import time
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from mtb_mcp.api.deps import resolve_location
from mtb_mcp.api.models import err, ok, ok_list
from mtb_mcp.clients.dwd import DWDClient
from mtb_mcp.clients.overpass import OverpassClient
from mtb_mcp.intelligence.trail_condition import estimate_trail_condition
from mtb_mcp.models.trail import MTBScale

router = APIRouter()


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance in km."""
    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


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

    # Filter out very short segments (< 200m) — not useful for riders
    trails = [trail for trail in trails if trail.length_m >= 200]

    # Optional surface filter
    if surface is not None:
        surface_lower = surface.lower()
        trails = [
            trail for trail in trails
            if trail.surface is not None and trail.surface.value == surface_lower
        ]

    # Sort by length descending (longer trails first)
    trails.sort(key=lambda t: t.length_m, reverse=True)

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


class AlongRouteRequest(BaseModel):
    """Request body for trail fragments along a route."""

    waypoints: list[list[float]]  # [[lat, lon], [lat, lon], ...]
    corridor_km: float = 1.0  # Search corridor in km


@router.post("/along-route")
async def trails_along_route(body: AlongRouteRequest) -> dict[str, Any]:
    """Find trail fragments near a route.

    Takes a list of waypoints (tour route) and finds all MTB trails
    within the specified corridor distance. Great for discovering
    singletrack detours along a planned tour.
    """
    t = time.monotonic()

    if len(body.waypoints) < 2:
        return err("VALIDATION_ERROR", "At least 2 waypoints required")
    if body.corridor_km < 0.1 or body.corridor_km > 5.0:
        return err("VALIDATION_ERROR", "corridor_km must be between 0.1 and 5.0")

    # Sample waypoints along the route (max ~10 search points to avoid Overpass rate limits)
    points = body.waypoints
    step = max(1, len(points) // 10)
    sample_points = points[::step]
    if points[-1] not in sample_points:
        sample_points.append(points[-1])

    # Compute bounding box covering the entire route + corridor
    all_lats = [p[0] for p in points]
    all_lons = [p[1] for p in points]
    center_lat = (min(all_lats) + max(all_lats)) / 2
    center_lon = (min(all_lons) + max(all_lons)) / 2

    # Search radius = half the route extent + corridor
    lat_extent = max(all_lats) - min(all_lats)
    lon_extent = max(all_lons) - min(all_lons)
    route_radius_km = max(lat_extent * 111, lon_extent * 85) / 2 + body.corridor_km
    search_radius_m = min(route_radius_km * 1000, 50000)  # Cap at 50km

    try:
        async with OverpassClient() as client:
            all_trails = await client.find_trails(
                center_lat, center_lon, radius_m=search_radius_m,
            )
    except Exception as exc:
        return err("EXTERNAL_API_ERROR", f"Overpass API error: {exc}")

    # Include ALL fragments (no min length filter) — short ones are the point here
    # For each trail, compute min distance to any route waypoint
    results: list[dict[str, Any]] = []
    seen_ids: set[int] = set()

    for trail in all_trails:
        if trail.osm_id in seen_ids:
            continue

        # Get trail center point
        if not trail.geometry:
            continue
        trail_lat = trail.geometry[len(trail.geometry) // 2].lat
        trail_lon = trail.geometry[len(trail.geometry) // 2].lon

        # Find minimum distance from any route point to this trail
        min_dist = float("inf")
        for wp in sample_points:
            d = _haversine_km(wp[0], wp[1], trail_lat, trail_lon)
            if d < min_dist:
                min_dist = d

        if min_dist <= body.corridor_km:
            seen_ids.add(trail.osm_id)
            trail_data = trail.model_dump(mode="json")
            trail_data["distance_to_route_km"] = round(min_dist, 2)
            results.append(trail_data)

    # Sort by distance to route
    results.sort(key=lambda x: x["distance_to_route_km"])

    return ok_list(results, len(results), t)
