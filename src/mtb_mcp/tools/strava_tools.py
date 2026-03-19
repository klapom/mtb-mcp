"""MCP tools for Strava integration."""

from __future__ import annotations

from pathlib import Path

import structlog

from mtb_mcp.clients.strava import StravaClient
from mtb_mcp.config import get_settings
from mtb_mcp.server import mcp

logger = structlog.get_logger(__name__)


def _get_strava_client() -> StravaClient | None:
    """Create a StravaClient from settings, or None if not configured."""
    settings = get_settings()
    if not settings.strava_access_token and not settings.strava_refresh_token:
        return None
    return StravaClient(
        client_id=settings.strava_client_id,
        client_secret=settings.strava_client_secret,
        access_token=settings.strava_access_token,
        refresh_token=settings.strava_refresh_token,
    )


def _format_time(seconds: int) -> str:
    """Format seconds as Xh YYmin."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes:02d}min"
    return f"{minutes}min"


_NOT_CONFIGURED_MSG = (
    "Strava credentials not configured. "
    "Set MTB_MCP_STRAVA_ACCESS_TOKEN (and optionally MTB_MCP_STRAVA_CLIENT_ID, "
    "MTB_MCP_STRAVA_CLIENT_SECRET, MTB_MCP_STRAVA_REFRESH_TOKEN for auto-refresh)."
)


@mcp.tool()
async def strava_recent_activities(
    limit: int = 10, include_all_types: bool = False
) -> str:
    """Get your recent MTB rides from Strava.

    By default shows only MountainBikeRide activities.
    Set include_all_types=True to see all cycling activities.
    """
    client = _get_strava_client()
    if client is None:
        return _NOT_CONFIGURED_MSG

    try:
        async with client:
            sport_type = None if include_all_types else "MountainBikeRide"
            activities = await client.get_recent_activities(
                limit=limit, sport_type=sport_type
            )
    except Exception as exc:
        logger.warning("strava_recent_activities_error", error=str(exc))
        return f"Error fetching Strava activities: {exc}"

    if not activities:
        filter_msg = "all cycling types" if include_all_types else "MountainBikeRide"
        return f"No recent activities found (filter: {filter_msg})."

    lines = [f"Recent Strava Activities ({len(activities)}):", ""]

    for a in activities:
        lines.append(f"  {a.name} ({a.sport_type})")
        lines.append(
            f"    {a.distance_km} km | {a.elevation_gain_m:.0f}m gain | "
            f"{_format_time(a.moving_time_seconds)}"
        )
        lines.append(
            f"    Avg {a.average_speed_kmh} km/h | Max {a.max_speed_kmh} km/h"
        )
        detail_parts: list[str] = []
        if a.average_heartrate:
            detail_parts.append(f"HR avg {a.average_heartrate:.0f}")
        if a.average_watts:
            detail_parts.append(f"Power avg {a.average_watts:.0f}W")
        if a.calories:
            detail_parts.append(f"{a.calories:.0f} kcal")
        if detail_parts:
            lines.append(f"    {' | '.join(detail_parts)}")
        lines.append(f"    Date: {a.start_date:%Y-%m-%d %H:%M} | ID: {a.id}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def strava_activity_details(activity_id: int) -> str:
    """Get detailed information about a Strava activity including segments and splits."""
    client = _get_strava_client()
    if client is None:
        return _NOT_CONFIGURED_MSG

    try:
        async with client:
            detail = await client.get_activity_details(activity_id)
    except Exception as exc:
        logger.warning("strava_activity_details_error", error=str(exc))
        return f"Error fetching activity {activity_id}: {exc}"

    lines = [
        f"Activity: {detail.name}",
        f"Type: {detail.sport_type}",
        f"Date: {detail.start_date:%Y-%m-%d %H:%M}",
        f"Distance: {detail.distance_km} km",
        f"Elevation Gain: {detail.elevation_gain_m:.0f} m",
        f"Moving Time: {_format_time(detail.moving_time_seconds)}",
        f"Elapsed Time: {_format_time(detail.elapsed_time_seconds)}",
        f"Avg Speed: {detail.average_speed_kmh} km/h",
        f"Max Speed: {detail.max_speed_kmh} km/h",
    ]

    if detail.average_heartrate:
        lines.append(
            f"Heart Rate: avg {detail.average_heartrate:.0f} / max {detail.max_heartrate or 0:.0f}"
        )
    if detail.average_watts:
        lines.append(
            f"Power: avg {detail.average_watts:.0f}W / max {detail.max_watts or 0:.0f}W"
        )
    if detail.average_cadence:
        lines.append(f"Cadence: avg {detail.average_cadence:.0f} rpm")
    if detail.average_temp is not None:
        lines.append(f"Temperature: {detail.average_temp:.0f} C")
    if detail.calories:
        lines.append(f"Calories: {detail.calories:.0f} kcal")
    if detail.suffer_score:
        lines.append(f"Suffer Score: {detail.suffer_score:.0f}")
    if detail.device_name:
        lines.append(f"Device: {detail.device_name}")
    if detail.description:
        lines.append(f"\nDescription: {detail.description}")

    if detail.segment_efforts:
        lines.append(f"\nSegment Efforts ({len(detail.segment_efforts)}):")
        for effort in detail.segment_efforts:
            pr_tag = ""
            if effort.pr_rank == 1:
                pr_tag = " [PR!]"
            elif effort.pr_rank == 2:
                pr_tag = " [2nd best]"
            elif effort.pr_rank == 3:
                pr_tag = " [3rd best]"

            lines.append(
                f"  {effort.name}: {_format_time(effort.elapsed_time_seconds)} "
                f"({effort.distance_m:.0f}m){pr_tag}"
            )
            effort_parts: list[str] = []
            if effort.average_heartrate:
                effort_parts.append(f"HR {effort.average_heartrate:.0f}")
            if effort.average_watts:
                effort_parts.append(f"{effort.average_watts:.0f}W")
            if effort_parts:
                lines.append(f"    {' | '.join(effort_parts)}")

    lines.append(f"\nActivity ID: {detail.id}")
    return "\n".join(lines)


@mcp.tool()
async def strava_athlete_stats() -> str:
    """Get your Strava statistics -- recent, year-to-date, and all-time ride totals."""
    client = _get_strava_client()
    if client is None:
        return _NOT_CONFIGURED_MSG

    try:
        async with client:
            stats = await client.get_athlete_stats()
    except Exception as exc:
        logger.warning("strava_athlete_stats_error", error=str(exc))
        return f"Error fetching athlete stats: {exc}"

    def _fmt_totals(label: str, totals: object) -> list[str]:
        from mtb_mcp.models.activity import RideTotals as _RT

        if not isinstance(totals, _RT):
            return [f"{label}: no data"]
        return [
            f"{label}:",
            f"  Rides: {totals.count}",
            f"  Distance: {totals.distance_km:.1f} km",
            f"  Elevation: {totals.elevation_gain_m:.0f} m",
            f"  Moving Time: {_format_time(totals.moving_time_seconds)}",
        ]

    lines = ["Strava Athlete Statistics", ""]
    lines.extend(_fmt_totals("Recent (4 weeks)", stats.recent_ride_totals))
    lines.append("")
    lines.extend(_fmt_totals("Year-to-Date", stats.ytd_ride_totals))
    lines.append("")
    lines.extend(_fmt_totals("All-Time", stats.all_ride_totals))

    return "\n".join(lines)


@mcp.tool()
async def strava_explore_segments(
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = 10.0,
) -> str:
    """Discover Strava segments near a location. Great for finding popular climbs and trails."""
    client = _get_strava_client()
    if client is None:
        return _NOT_CONFIGURED_MSG

    settings = get_settings()
    search_lat = lat if lat is not None else settings.home_lat
    search_lon = lon if lon is not None else settings.home_lon

    try:
        async with client:
            segments = await client.explore_segments(
                search_lat, search_lon, radius_km
            )
    except Exception as exc:
        logger.warning("strava_explore_segments_error", error=str(exc))
        return f"Error exploring segments: {exc}"

    if not segments:
        return (
            f"No segments found near {search_lat:.2f}, {search_lon:.2f} "
            f"(radius: {radius_km} km)."
        )

    lines = [
        f"Strava Segments near {search_lat:.2f}, {search_lon:.2f} "
        f"({len(segments)} found):",
        "",
    ]

    cat_names = {0: "No cat", 1: "Cat 4", 2: "Cat 3", 3: "Cat 2", 4: "Cat 1", 5: "HC"}

    for seg in segments:
        cat = cat_names.get(seg.climb_category, f"Cat {seg.climb_category}")
        lines.append(f"  {seg.name} ({cat})")
        lines.append(
            f"    {seg.distance_m:.0f}m | "
            f"avg grade {seg.average_grade:.1f}% | "
            f"max grade {seg.maximum_grade:.1f}%"
        )
        lines.append(
            f"    Elevation: {seg.elevation_low:.0f}m - {seg.elevation_high:.0f}m"
        )
        lines.append(f"    Segment ID: {seg.id}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def strava_segment_efforts(segment_id: int, limit: int = 10) -> str:
    """Get your personal history on a Strava segment. Shows PRs and recent efforts."""
    client = _get_strava_client()
    if client is None:
        return _NOT_CONFIGURED_MSG

    try:
        async with client:
            efforts = await client.get_segment_efforts(segment_id, limit=limit)
    except Exception as exc:
        logger.warning("strava_segment_efforts_error", error=str(exc))
        return f"Error fetching segment efforts: {exc}"

    if not efforts:
        return f"No personal efforts found for segment {segment_id}."

    lines = [f"Segment Efforts for segment {segment_id} ({len(efforts)}):", ""]

    for effort in efforts:
        pr_tag = ""
        if effort.pr_rank == 1:
            pr_tag = " [PR!]"
        elif effort.pr_rank == 2:
            pr_tag = " [2nd best]"
        elif effort.pr_rank == 3:
            pr_tag = " [3rd best]"

        lines.append(f"  {effort.name}: {_format_time(effort.elapsed_time_seconds)}{pr_tag}")
        detail_parts: list[str] = [f"{effort.distance_m:.0f}m"]
        if effort.average_heartrate:
            detail_parts.append(f"HR {effort.average_heartrate:.0f}")
        if effort.average_watts:
            detail_parts.append(f"{effort.average_watts:.0f}W")
        lines.append(f"    {' | '.join(detail_parts)}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def strava_export_gpx(activity_id: int) -> str:
    """Export a Strava activity as GPX file for use on GPS devices."""
    client = _get_strava_client()
    if client is None:
        return _NOT_CONFIGURED_MSG

    try:
        async with client:
            gpx_xml = await client.export_gpx(activity_id)
    except ValueError as exc:
        return f"Cannot export GPX: {exc}"
    except Exception as exc:
        logger.warning("strava_export_gpx_error", error=str(exc))
        return f"Error exporting GPX for activity {activity_id}: {exc}"

    # Save to data directory
    settings = get_settings()
    data_dir = Path(settings.resolved_data_dir) / "gpx"
    data_dir.mkdir(parents=True, exist_ok=True)
    gpx_path = data_dir / f"strava_{activity_id}.gpx"
    gpx_path.write_text(gpx_xml, encoding="utf-8")

    return f"GPX exported: {gpx_path} ({len(gpx_xml)} bytes)"


@mcp.tool()
async def strava_weekly_summary(weeks: int = 1) -> str:
    """Get an aggregated summary of your riding over the past week(s).

    Shows total distance, elevation, time, and ride count.
    """
    client = _get_strava_client()
    if client is None:
        return _NOT_CONFIGURED_MSG

    try:
        async with client:
            summary = await client.get_weekly_summary(weeks=weeks)
    except Exception as exc:
        logger.warning("strava_weekly_summary_error", error=str(exc))
        return f"Error fetching weekly summary: {exc}"

    period = f"past {weeks} week(s)" if weeks > 1 else "past week"
    lines = [
        f"Strava Weekly Summary ({period})",
        "",
        f"Total Rides: {summary['total_rides']}",
        f"Total Distance: {summary['total_distance_km']:.1f} km",
        f"Total Elevation: {summary['total_elevation_m']:.0f} m",
        f"Total Moving Time: {_format_time(summary['total_moving_time_seconds'])}",
        f"Average Speed: {summary['average_speed_kmh']:.1f} km/h",
    ]

    sport_counts: dict[str, int] = summary.get("sport_type_counts", {})
    if sport_counts:
        lines.append("")
        lines.append("By type:")
        for sport, count in sport_counts.items():
            lines.append(f"  {sport}: {count}")

    activities: list[dict[str, object]] = summary.get("activities", [])
    if activities:
        lines.append("")
        lines.append("Activities:")
        for act in activities:
            lines.append(f"  {act.get('name')} ({act.get('sport_type')}) - {act.get('distance_km')} km")

    return "\n".join(lines)
