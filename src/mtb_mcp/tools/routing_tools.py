"""MCP tools for MTB route planning."""

from __future__ import annotations

import httpx
import structlog

from mtb_mcp.clients.brouter import BRouterClient
from mtb_mcp.clients.ors import ORSClient
from mtb_mcp.config import get_settings
from mtb_mcp.models.common import GeoPoint
from mtb_mcp.models.route import ElevationProfile, Route
from mtb_mcp.server import mcp

logger = structlog.get_logger(__name__)


def _resolve_location(
    lat: float | None, lon: float | None
) -> tuple[float, float]:
    """Resolve lat/lon, falling back to home location from settings."""
    if lat is not None and lon is not None:
        return lat, lon
    settings = get_settings()
    return settings.home_lat, settings.home_lon


def _format_route(route: Route) -> str:
    """Format a Route into a human-readable summary string."""
    s = route.summary
    lines = [
        f"Route ({s.source.upper()})",
        f"  Distance: {s.distance_km:.1f} km",
        f"  Elevation gain: {s.elevation_gain_m:.0f} m",
        f"  Elevation loss: {s.elevation_loss_m:.0f} m",
    ]

    if s.duration_minutes is not None:
        hours = int(s.duration_minutes // 60)
        mins = int(s.duration_minutes % 60)
        if hours > 0:
            lines.append(f"  Estimated time: {hours}h {mins}min")
        else:
            lines.append(f"  Estimated time: {mins} min")

    lines.append(f"  Points: {len(route.points)}")

    if route.gpx:
        lines.append("  GPX data: available (use route GPX export for download)")

    return "\n".join(lines)


def _format_elevation_profile(profile: ElevationProfile) -> str:
    """Format an ElevationProfile into a human-readable string."""
    lines = [
        "Elevation Profile",
        f"  Total distance: {profile.total_distance_km:.1f} km",
        f"  Total climb: {profile.total_gain_m:.0f} m",
        f"  Total descent: {profile.total_loss_m:.0f} m",
        f"  Min elevation: {profile.min_elevation_m:.0f} m",
        f"  Max elevation: {profile.max_elevation_m:.0f} m",
        f"  Elevation range: {profile.max_elevation_m - profile.min_elevation_m:.0f} m",
        "",
        "Profile (distance → elevation):",
    ]

    # Show up to 10 evenly-spaced sample points
    total = len(profile.points)
    if total <= 10:
        sample_indices = list(range(total))
    else:
        step = (total - 1) / 9.0
        sample_indices = [int(round(i * step)) for i in range(10)]

    for idx in sample_indices:
        pt = profile.points[idx]
        bar_len = max(0, int((pt.elevation_m - profile.min_elevation_m) / 10))
        bar = "#" * min(bar_len, 40)
        lines.append(f"  {pt.distance_km:6.1f} km  {pt.elevation_m:6.0f} m  {bar}")

    return "\n".join(lines)


async def _plan_route_with_fallback(
    start: GeoPoint, end: GeoPoint, profile: str = "trekking"
) -> Route:
    """Try BRouter first, fall back to ORS if unavailable."""
    settings = get_settings()

    # Try BRouter first (self-hosted)
    try:
        async with BRouterClient(base_url=settings.brouter_url) as client:
            return await client.plan_route(start, end, profile=profile)
    except (httpx.ConnectError, httpx.TransportError, httpx.TimeoutException) as exc:
        logger.warning("brouter_unavailable", error=str(exc))

    # Fall back to ORS
    if settings.ors_api_key:
        logger.info("falling_back_to_ors")
        async with ORSClient(api_key=settings.ors_api_key) as client:
            return await client.plan_route(start, end)

    msg = (
        "BRouter is not available and no ORS API key is configured. "
        "Set MTB_MCP_BROUTER_URL or MTB_MCP_ORS_API_KEY."
    )
    raise ConnectionError(msg)


@mcp.tool()
async def plan_route(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
    profile: str = "trekking",
) -> str:
    """Plan an MTB route from A to B using BRouter (self-hosted) or OpenRouteService.

    Profiles: trekking (default, good for MTB).
    Returns distance, elevation gain/loss, estimated duration, and can export GPX.
    """
    start = GeoPoint(lat=start_lat, lon=start_lon)
    end = GeoPoint(lat=end_lat, lon=end_lon)

    try:
        route = await _plan_route_with_fallback(start, end, profile=profile)
    except ConnectionError as exc:
        return f"Error: {exc}"

    return _format_route(route)


@mcp.tool()
async def plan_loop_route(
    start_lat: float | None = None,
    start_lon: float | None = None,
    distance_km: float = 30.0,
    profile: str = "trekking",
) -> str:
    """Plan a loop/round-trip MTB route from a starting point.

    Specify desired distance in km. Uses home location if no start given.
    """
    resolved_lat, resolved_lon = _resolve_location(start_lat, start_lon)
    start = GeoPoint(lat=resolved_lat, lon=resolved_lon)
    settings = get_settings()

    # Try BRouter first (supports loop routes natively)
    try:
        async with BRouterClient(base_url=settings.brouter_url) as client:
            route = await client.plan_loop_route(
                start, distance_km=distance_km, profile=profile
            )
            return _format_route(route)
    except (httpx.ConnectError, httpx.TransportError, httpx.TimeoutException) as exc:
        logger.warning("brouter_unavailable_for_loop", error=str(exc))

    return (
        "Error: Loop route planning requires BRouter (self-hosted). "
        "ORS fallback does not support loop routes. "
        "Set MTB_MCP_BROUTER_URL and ensure BRouter is running."
    )


@mcp.tool()
async def route_elevation_profile(
    start_lat: float,
    start_lon: float,
    end_lat: float,
    end_lon: float,
) -> str:
    """Get the elevation profile for a route between two points.

    Shows total climb, descent, min/max elevation, and profile summary.
    """
    start = GeoPoint(lat=start_lat, lon=start_lon)
    end = GeoPoint(lat=end_lat, lon=end_lon)
    settings = get_settings()

    # Try BRouter first
    try:
        async with BRouterClient(base_url=settings.brouter_url) as client:
            profile = await client.get_elevation_profile([start, end])
            return _format_elevation_profile(profile)
    except (httpx.ConnectError, httpx.TransportError, httpx.TimeoutException) as exc:
        logger.warning("brouter_unavailable_for_elevation", error=str(exc))

    # Fall back to ORS: plan route and extract elevation from points
    if settings.ors_api_key:
        logger.info("falling_back_to_ors_for_elevation")
        try:
            async with ORSClient(api_key=settings.ors_api_key) as client:
                route = await client.plan_route(start, end)
                return _format_route(route)
        except (httpx.HTTPStatusError, ValueError) as exc:
            return f"Error getting elevation from ORS: {exc}"

    return (
        "Error: BRouter is not available and no ORS API key is configured. "
        "Set MTB_MCP_BROUTER_URL or MTB_MCP_ORS_API_KEY."
    )
