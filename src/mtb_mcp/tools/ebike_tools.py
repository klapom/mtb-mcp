"""MCP tools for eBike range planning."""

from __future__ import annotations

import structlog

from mtb_mcp.intelligence.ebike_range import (
    ASSIST_FACTORS,
    EBikeRangeInput,
    calculate_range,
    estimate_flat_range_km,
)
from mtb_mcp.models.common import GeoPoint
from mtb_mcp.server import mcp

logger = structlog.get_logger(__name__)


def _build_synthetic_elevation_profile(
    distance_km: float,
    elevation_gain_m: float,
) -> list[GeoPoint]:
    """Build a synthetic elevation profile from distance and elevation gain.

    Creates a simple out-and-up profile: flat start, climb, flat top.
    This approximation is used when no real elevation data is available.
    """
    if distance_km <= 0:
        return []

    # Split into segments: 1/3 flat, 1/3 climb, 1/3 flat at top
    num_segments = 30
    points: list[GeoPoint] = []

    for i in range(num_segments + 1):
        fraction = i / num_segments
        # Elevation: ramp up over the first 2/3, plateau for last 1/3
        ele = (fraction / 0.67) * elevation_gain_m if fraction < 0.67 else elevation_gain_m

        # Place points along a straight line (latitude changes)
        lat = 49.0 + (fraction * distance_km / 111.0)  # ~111 km per degree lat
        points.append(GeoPoint(lat=lat, lon=11.0, ele=ele))

    return points


def _format_range_result(
    result_data: dict[str, object],
    distance_km: float | None,
    assist_mode: str,
) -> str:
    """Format range check result as a human-readable string."""
    from mtb_mcp.intelligence.ebike_range import EBikeRangeResult

    r: EBikeRangeResult = result_data  # type: ignore[assignment]

    status = "YES -- Battery sufficient" if r.can_finish else "NO -- Battery may not be enough"

    lines = [
        "eBike Range Check",
        f"  Status: {status}",
        "",
        f"  Available energy: {r.available_wh} Wh",
        f"  Estimated consumption: {r.estimated_consumption_wh} Wh",
        f"  Remaining after route: {r.remaining_wh} Wh ({r.remaining_pct}%)",
        f"  Safety margin: {r.safety_margin_pct}%",
        "",
        f"  Consumption per km: {r.consumption_per_km} Wh/km",
        f"  Estimated total range: {r.estimated_range_km} km",
        f"  Assist mode: {assist_mode}",
    ]

    if distance_km is not None:
        lines.append(f"  Route distance: {distance_km:.1f} km")

    if not r.can_finish:
        lines.append("")
        lines.append("Suggestions:")
        lines.append("  - Switch to a lower assist mode (eco uses less battery)")
        lines.append("  - Start with a full charge")
        lines.append("  - Choose a route with less elevation gain")

    return "\n".join(lines)


@mcp.tool()
async def ebike_range_check(
    battery_wh: float = 625.0,
    charge_pct: float = 100.0,
    start_lat: float | None = None,
    start_lon: float | None = None,
    end_lat: float | None = None,
    end_lon: float | None = None,
    distance_km: float | None = None,
    elevation_gain_m: float | None = None,
    rider_kg: float = 80.0,
    bike_kg: float = 23.0,
    assist_mode: str = "tour",
) -> str:
    """Check if your eBike battery is sufficient for a planned route.

    Provide either start/end coordinates (for route-based calc) or
    distance_km + elevation_gain_m for quick estimation.
    Assist modes: eco, tour, emtb, turbo.
    """
    if assist_mode not in ASSIST_FACTORS:
        return (
            f"Unknown assist mode: '{assist_mode}'. "
            f"Valid modes: {', '.join(ASSIST_FACTORS.keys())}"
        )

    range_input = EBikeRangeInput(
        battery_wh=battery_wh,
        charge_pct=charge_pct,
        rider_kg=rider_kg,
        bike_kg=bike_kg,
        assist_mode=assist_mode,
    )

    # Route-based calculation with coordinates
    if (
        start_lat is not None
        and start_lon is not None
        and end_lat is not None
        and end_lon is not None
    ):
        # Try to get elevation profile from BRouter
        try:
            from mtb_mcp.clients.brouter import BRouterClient
            from mtb_mcp.config import get_settings

            settings = get_settings()
            start = GeoPoint(lat=start_lat, lon=start_lon)
            end = GeoPoint(lat=end_lat, lon=end_lon)

            async with BRouterClient(base_url=settings.brouter_url) as client:
                route = await client.plan_route(start, end)

            result = calculate_range(range_input, route.points)
            return _format_range_result(
                result,  # type: ignore[arg-type]
                distance_km=route.summary.distance_km,
                assist_mode=assist_mode,
            )
        except Exception as exc:
            logger.warning("ebike_brouter_unavailable", error=str(exc))
            return (
                f"Could not fetch route elevation data: {exc}\n"
                "Try providing distance_km and elevation_gain_m manually instead."
            )

    # Quick estimation with distance and elevation
    if distance_km is not None:
        gain = elevation_gain_m or 0.0
        profile_points = _build_synthetic_elevation_profile(distance_km, gain)

        if not profile_points:
            return "Error: distance_km must be greater than 0."

        result = calculate_range(range_input, profile_points)
        return _format_range_result(
            result,  # type: ignore[arg-type]
            distance_km=distance_km,
            assist_mode=assist_mode,
        )

    # Flat range estimate fallback
    flat_range = estimate_flat_range_km(
        battery_wh=battery_wh,
        charge_pct=charge_pct,
        assist_mode=assist_mode,
        rider_kg=rider_kg,
        bike_kg=bike_kg,
    )

    return (
        "eBike Range Estimate (flat terrain)\n"
        f"  Battery: {battery_wh} Wh at {charge_pct}%\n"
        f"  Assist mode: {assist_mode}\n"
        f"  Estimated flat range: {flat_range} km\n"
        "\n"
        "For a more accurate estimate, provide:\n"
        "  - distance_km + elevation_gain_m, or\n"
        "  - start_lat/lon + end_lat/lon for route-based calculation"
    )


@mcp.tool()
async def ebike_battery_status() -> str:
    """Check current eBike battery status.

    Note: Direct battery reading requires Bosch eBike Cloud connection
    (coming in a future update). Currently provides guidance for manual
    battery input.
    """
    lines = [
        "eBike Battery Status",
        "",
        "Direct battery reading is not yet available.",
        "Bosch eBike Cloud integration is planned for a future sprint.",
        "",
        "To check your range, use ebike_range_check with:",
        "  - battery_wh: Your battery capacity (e.g. 625 for PowerTube 625)",
        "  - charge_pct: Current charge level from your display",
        "",
        "Common Bosch batteries:",
        "  PowerTube 400: 400 Wh",
        "  PowerTube 500: 500 Wh",
        "  PowerTube 625: 625 Wh",
        "  PowerTube 750: 750 Wh",
        "",
        "Common Shimano batteries:",
        "  BT-E8010: 504 Wh",
        "  BT-E8035: 504 Wh",
        "  BT-E8036: 630 Wh",
    ]

    return "\n".join(lines)
