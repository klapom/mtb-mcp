"""MCP tools for trail information."""

from __future__ import annotations

from mtb_mcp.clients.overpass import OverpassClient
from mtb_mcp.config import get_settings
from mtb_mcp.models.trail import MTBScale
from mtb_mcp.server import mcp


def _resolve_location(
    lat: float | None, lon: float | None
) -> tuple[float, float]:
    """Resolve lat/lon, falling back to home location from settings."""
    if lat is not None and lon is not None:
        return lat, lon
    settings = get_settings()
    return settings.home_lat, settings.home_lon


@mcp.tool()
async def find_trails(
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = 30.0,
    min_difficulty: str | None = None,
) -> str:
    """Find MTB trails near a location using OpenStreetMap data.

    Returns trails with difficulty rating (S0-S6), surface type, and length.
    Provide lat/lon or leave empty for home location.
    min_difficulty: minimum MTB scale (S0-S6), e.g. 'S2' for technical trails.
    """
    resolved_lat, resolved_lon = _resolve_location(lat, lon)
    radius_m = radius_km * 1000

    min_scale: MTBScale | None = None
    if min_difficulty is not None:
        try:
            min_scale = MTBScale(min_difficulty.upper())
        except ValueError:
            return (
                f"Invalid difficulty '{min_difficulty}'. "
                "Use S0 (easy) through S6 (extreme)."
            )

    async with OverpassClient() as client:
        trails = await client.find_trails(
            resolved_lat, resolved_lon, radius_m=radius_m, min_scale=min_scale
        )

    if not trails:
        return (
            f"No MTB trails found within {radius_km:.0f}km of "
            f"({resolved_lat:.2f}, {resolved_lon:.2f})"
        )

    lines = [
        f"MTB Trails within {radius_km:.0f}km of "
        f"({resolved_lat:.2f}, {resolved_lon:.2f})",
        f"Found {len(trails)} trail(s):",
        "",
    ]

    for trail in trails:
        name = trail.name or "Unnamed trail"
        scale = trail.mtb_scale.value if trail.mtb_scale else "?"
        surface = trail.surface.value if trail.surface else "unknown"
        length = (
            f"{trail.length_m:.0f}m" if trail.length_m is not None else "unknown length"
        )

        lines.append(f"  [{scale}] {name} ({length}, {surface}) — OSM ID: {trail.osm_id}")

    return "\n".join(lines)


@mcp.tool()
async def trail_details(osm_id: int) -> str:
    """Get detailed information about a specific trail by its OpenStreetMap ID."""
    async with OverpassClient() as client:
        trail = await client.get_trail_details(osm_id)

    if trail is None:
        return f"No trail found with OSM ID {osm_id}"

    name = trail.name or "Unnamed trail"
    lines = [
        f"Trail Details: {name}",
        f"OSM ID: {trail.osm_id}",
        f"Difficulty: {trail.mtb_scale.value if trail.mtb_scale else 'not rated'}",
        f"Surface: {trail.surface.value if trail.surface else 'unknown'}",
        f"Length: {trail.length_m:.0f}m" if trail.length_m else "Length: unknown",
        f"Points: {len(trail.geometry)} coordinates",
    ]

    if trail.geometry:
        start = trail.geometry[0]
        end = trail.geometry[-1]
        lines.extend([
            f"Start: ({start.lat:.5f}, {start.lon:.5f})",
            f"End: ({end.lat:.5f}, {end.lon:.5f})",
        ])

    return "\n".join(lines)
