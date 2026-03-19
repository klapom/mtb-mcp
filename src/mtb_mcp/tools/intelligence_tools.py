"""MCP tools for ride intelligence -- trail conditions, ride scoring, tour fusion, trail tagging."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog

from mtb_mcp.clients.dwd import DWDClient
from mtb_mcp.clients.gpstour import GPSTourClient
from mtb_mcp.clients.komoot import KomootClient
from mtb_mcp.clients.overpass import OverpassClient
from mtb_mcp.clients.strava import StravaClient
from mtb_mcp.config import get_settings
from mtb_mcp.intelligence.ride_score import RideScoreInput, calculate_ride_score
from mtb_mcp.intelligence.tour_fusion import deduplicate_tours, rank_tours
from mtb_mcp.intelligence.trail_condition import estimate_trail_condition
from mtb_mcp.intelligence.trail_tagger import match_trails, tag_ride_segments
from mtb_mcp.models.common import GeoPoint
from mtb_mcp.models.tour import TourSummary
from mtb_mcp.server import mcp

logger = structlog.get_logger(__name__)


def _resolve_location(
    lat: float | None, lon: float | None,
) -> tuple[float, float]:
    """Resolve lat/lon, falling back to home location from settings."""
    if lat is not None and lon is not None:
        return lat, lon
    settings = get_settings()
    return settings.home_lat, settings.home_lon


@mcp.tool()
async def trail_condition_estimate(
    lat: float | None = None,
    lon: float | None = None,
    surface: str = "dirt",
) -> str:
    """Estimate current trail condition based on recent rainfall and surface type.

    Surfaces: asphalt, gravel, dirt, grass, rock, roots, sand.
    Uses DWD precipitation history to estimate: dry, damp, wet, muddy, or frozen.
    """
    resolved_lat, resolved_lon = _resolve_location(lat, lon)

    async with DWDClient() as client:
        history = await client.get_rain_history(resolved_lat, resolved_lon)
        forecast = await client.get_forecast(resolved_lat, resolved_lon)

    # Current temperature from the first forecast hour (closest to now)
    current_temp = 15.0
    if forecast.hours:
        current_temp = forecast.hours[0].temp_c

    condition, confidence, reasoning = estimate_trail_condition(
        surface=surface,
        hourly_rain_mm=history.hourly_mm,
        current_temp_c=current_temp,
    )

    lines = [
        f"Trail Condition Estimate for ({resolved_lat:.2f}, {resolved_lon:.2f})",
        f"Surface: {surface}",
        f"Condition: {condition.value.upper()}",
        f"Confidence: {confidence}",
        f"Reasoning: {reasoning}",
        "",
        f"Rain last 48h: {history.total_mm_48h:.1f}mm",
    ]

    if history.last_rain_hours_ago is not None:
        lines.append(
            f"Last significant rain: {history.last_rain_hours_ago:.0f} hours ago"
        )
    else:
        lines.append("No significant rain in the last 48 hours")

    lines.append(f"Current temperature: {current_temp:.1f}\u00b0C")

    return "\n".join(lines)


@mcp.tool()
async def ride_score(
    lat: float | None = None,
    lon: float | None = None,
    ride_start_hour: int | None = None,
    ride_duration_hours: float = 2.0,
    surface: str = "dirt",
) -> str:
    """Calculate a ride score (0-100) -- 'Should I ride today?'

    Combines weather forecast, trail conditions, wind, and daylight.
    Score: 80+ Perfect | 60+ Good | 40+ Fair | 20+ Poor | <20 Stay Home
    """
    resolved_lat, resolved_lon = _resolve_location(lat, lon)

    async with DWDClient() as client:
        forecast = await client.get_forecast(resolved_lat, resolved_lon)
        history = await client.get_rain_history(resolved_lat, resolved_lon)

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

    # --- Approximate sunrise / sunset (simple latitude-based heuristic) ---
    # A proper implementation would use an ephemeris library; for a first
    # version we use a rough central-European estimate.
    day_base = ride_start.replace(hour=0, minute=0, second=0, microsecond=0)
    sunrise = day_base.replace(hour=6, minute=0)
    sunset = day_base.replace(hour=20, minute=0)

    # --- Build input ---
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

    # --- Format output ---
    lines = [
        f"Ride Score for ({resolved_lat:.2f}, {resolved_lon:.2f})",
        f"Ride window: {ride_start:%H:%M} - {ride_end:%H:%M} UTC "
        f"({ride_duration_hours:.1f}h)",
        "",
        f"  SCORE: {result.score}/100 -- {result.verdict}",
        "",
        f"  Weather:  {result.weather_score:2d}/40",
        f"  Trail:    {result.trail_score:2d}/30  (surface: {surface}, "
        f"condition: {condition.value})",
        f"  Wind:     {result.wind_score:2d}/15  "
        f"(avg {avg_wind:.0f} km/h, gusts {max_gust:.0f} km/h)",
        f"  Daylight: {result.daylight_score:2d}/15",
        "",
    ]

    if result.factors:
        lines.append("Factors:")
        for factor in result.factors:
            lines.append(f"  - {factor}")
    else:
        lines.append("No penalties -- conditions look great!")

    # Recommendation
    if result.score >= 80:
        lines.append("\nGet out there -- perfect riding conditions!")
    elif result.score >= 60:
        lines.append("\nGood conditions, enjoy your ride!")
    elif result.score >= 40:
        lines.append(
            "\nRideable but not ideal. Consider shorter route or road alternatives."
        )
    elif result.score >= 20:
        lines.append("\nPoor conditions. Indoor trainer or road ride recommended.")
    else:
        lines.append(
            "\nStay home. Conditions are unsafe or unpleasant for riding."
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sprint 8: Tour Fusion & Trail Tagger
# ---------------------------------------------------------------------------


def _format_tour_summary_fused(tour: TourSummary) -> str:
    """Format a TourSummary for fusion display."""
    parts: list[str] = [f"  [{tour.source.value}] {tour.name}"]
    details: list[str] = []
    if tour.distance_km is not None:
        details.append(f"{tour.distance_km} km")
    if tour.elevation_m is not None:
        details.append(f"{tour.elevation_m:.0f} m elevation")
    if tour.difficulty is not None:
        details.append(tour.difficulty.value)
    if tour.region:
        details.append(tour.region)
    if details:
        parts.append(f"    {' | '.join(details)}")
    if tour.url:
        parts.append(f"    URL: {tour.url}")
    parts.append(f"    ID: {tour.id}")
    return "\n".join(parts)


@mcp.tool()
async def tour_fusion_search(
    query: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = 30.0,
    preference_distance_km: float | None = None,
    preference_difficulty: str | None = None,
) -> str:
    """Search tours across all sources with automatic deduplication.

    Combines Komoot + GPS-Tour.info results, removes duplicates,
    and enriches with details from all sources.
    Optionally rank by distance preference and difficulty preference.
    """
    settings = get_settings()
    search_lat = lat if lat is not None else settings.home_lat
    search_lon = lon if lon is not None else settings.home_lon
    search_query = query or f"{search_lat},{search_lon}"

    all_results: list[TourSummary] = []

    # Search Komoot
    if settings.komoot_email:
        try:
            async with KomootClient(
                email=settings.komoot_email,
                password=settings.komoot_password,
            ) as komoot:
                komoot_results = await komoot.search_tours(
                    lat=search_lat, lon=search_lon, radius_km=radius_km
                )
                all_results.extend(komoot_results)
        except Exception as exc:
            logger.warning("tour_fusion_komoot_error", error=str(exc))

    # Search GPS-Tour.info via SearXNG
    try:
        async with GPSTourClient(
            searxng_url=settings.searxng_url,
            username=settings.gpstour_username,
            password=settings.gpstour_password,
        ) as gpstour:
            gpstour_results = await gpstour.search_tours(query=search_query)
            all_results.extend(gpstour_results)
    except Exception as exc:
        logger.warning("tour_fusion_gpstour_error", error=str(exc))

    if not all_results:
        return (
            f"No tours found near {search_lat:.2f}, {search_lon:.2f} "
            f"(radius: {radius_km} km). "
            "Check that Komoot credentials are configured or SearXNG is running."
        )

    original_count = len(all_results)

    # Deduplicate
    deduped = deduplicate_tours(all_results)

    # Rank by preferences
    ranked = rank_tours(
        deduped,
        preference_distance_km=preference_distance_km,
        preference_difficulty=preference_difficulty,
    )

    removed = original_count - len(ranked)
    header_parts = [
        f"Found {len(ranked)} unique tour(s) near "
        f"{search_lat:.2f}, {search_lon:.2f} (radius: {radius_km} km)",
    ]
    if removed > 0:
        header_parts.append(
            f"({removed} duplicate(s) removed from {original_count} total)"
        )
    header = "\n".join(header_parts) + "\n"

    tour_lines = [_format_tour_summary_fused(t) for t in ranked]
    return header + "\n\n".join(tour_lines)


def _parse_gpx_points(gpx_data: str) -> list[GeoPoint]:
    """Parse GPX XML data into a list of GeoPoints."""
    import gpxpy

    gpx = gpxpy.parse(gpx_data)
    points: list[GeoPoint] = []
    for track in gpx.tracks:
        for segment in track.segments:
            for pt in segment.points:
                points.append(GeoPoint(
                    lat=pt.latitude,
                    lon=pt.longitude,
                    ele=pt.elevation,
                ))
    return points


@mcp.tool()
async def auto_tag_trails(
    activity_id: int | None = None,
    gpx_data: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = 5.0,
) -> str:
    """Match a GPS trace (from Strava activity or GPX data) to known trail names.

    Returns which trails you rode, with difficulty ratings and overlap confidence.
    Provide either activity_id (to fetch from Strava) or gpx_data (raw GPX XML).
    """
    settings = get_settings()

    # Get GPS points from either source
    gps_points: list[GeoPoint] = []

    if activity_id is not None:
        # Fetch from Strava
        if not settings.strava_access_token and not settings.strava_refresh_token:
            return (
                "Strava credentials not configured. "
                "Set MTB_MCP_STRAVA_ACCESS_TOKEN or provide gpx_data directly."
            )
        try:
            strava = StravaClient(
                client_id=settings.strava_client_id,
                client_secret=settings.strava_client_secret,
                access_token=settings.strava_access_token,
                refresh_token=settings.strava_refresh_token,
            )
            async with strava:
                gpx_xml = await strava.export_gpx(activity_id)
                gps_points = _parse_gpx_points(gpx_xml)
        except Exception as exc:
            logger.warning("auto_tag_strava_error", error=str(exc))
            return f"Error fetching Strava activity {activity_id}: {exc}"
    elif gpx_data is not None:
        try:
            gps_points = _parse_gpx_points(gpx_data)
        except Exception as exc:
            logger.warning("auto_tag_gpx_parse_error", error=str(exc))
            return f"Error parsing GPX data: {exc}"
    else:
        return "Provide either activity_id (Strava) or gpx_data (GPX XML)."

    if not gps_points:
        return "No GPS points found in the provided data."

    # Determine search area from GPS points
    search_lat = lat if lat is not None else gps_points[0].lat
    search_lon = lon if lon is not None else gps_points[0].lon

    # Fetch known trails from OSM
    try:
        async with OverpassClient() as overpass:
            known_trails = await overpass.find_trails(
                search_lat, search_lon, radius_m=radius_km * 1000
            )
    except Exception as exc:
        logger.warning("auto_tag_overpass_error", error=str(exc))
        return f"Error fetching trails from OSM: {exc}"

    if not known_trails:
        return (
            f"No known OSM trails found near {search_lat:.2f}, {search_lon:.2f}. "
            "Cannot match GPS trace to trail names."
        )

    # Match trails
    matches = match_trails(gps_points, known_trails)

    if not matches:
        return (
            "No trail matches found. "
            f"Checked {len(gps_points)} GPS points against "
            f"{len(known_trails)} known trails."
        )

    lines = [
        f"Trail Matches ({len(matches)} found from {len(gps_points)} GPS points):",
        "",
    ]

    for m in matches:
        name = m.trail.name or f"OSM #{m.trail.osm_id}"
        scale = m.trail.mtb_scale.value if m.trail.mtb_scale else "unrated"
        surface = m.trail.surface.value if m.trail.surface else "unknown"
        lines.append(f"  {name}")
        lines.append(
            f"    Overlap: {m.overlap_pct:.1f}% | "
            f"Avg distance: {m.distance_avg_m:.1f}m | "
            f"Difficulty: {scale} | Surface: {surface}"
        )
        lines.append(f"    OSM ID: {m.trail.osm_id}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
async def post_ride_analysis(activity_id: int) -> str:
    """Analyze a completed ride -- compare against segments, detect PRs,
    match trails ridden, and summarize performance."""
    settings = get_settings()

    if not settings.strava_access_token and not settings.strava_refresh_token:
        return (
            "Strava credentials not configured. "
            "Set MTB_MCP_STRAVA_ACCESS_TOKEN for post-ride analysis."
        )

    # Fetch activity details
    try:
        strava = StravaClient(
            client_id=settings.strava_client_id,
            client_secret=settings.strava_client_secret,
            access_token=settings.strava_access_token,
            refresh_token=settings.strava_refresh_token,
        )
        async with strava:
            detail = await strava.get_activity_details(activity_id)
            gpx_xml = await strava.export_gpx(activity_id)
    except Exception as exc:
        logger.warning("post_ride_analysis_error", error=str(exc))
        return f"Error fetching activity {activity_id}: {exc}"

    # Parse GPS points
    gps_points = _parse_gpx_points(gpx_xml)

    lines = [
        f"Post-Ride Analysis: {detail.name}",
        f"Date: {detail.start_date:%Y-%m-%d %H:%M}",
        "",
        "Performance Summary:",
        f"  Distance: {detail.distance_km} km",
        f"  Elevation Gain: {detail.elevation_gain_m:.0f} m",
    ]

    # Format time
    hours = detail.moving_time_seconds // 3600
    minutes = (detail.moving_time_seconds % 3600) // 60
    time_str = f"{hours}h {minutes:02d}min" if hours > 0 else f"{minutes}min"
    lines.append(f"  Moving Time: {time_str}")
    lines.append(f"  Avg Speed: {detail.average_speed_kmh} km/h")
    lines.append(f"  Max Speed: {detail.max_speed_kmh} km/h")

    if detail.average_heartrate:
        lines.append(f"  Avg HR: {detail.average_heartrate:.0f} bpm")
    if detail.average_watts:
        lines.append(f"  Avg Power: {detail.average_watts:.0f} W")
    if detail.calories:
        lines.append(f"  Calories: {detail.calories:.0f} kcal")

    # Segment PRs
    if detail.segment_efforts:
        pr_count = sum(1 for e in detail.segment_efforts if e.pr_rank == 1)
        top3_count = sum(
            1 for e in detail.segment_efforts if e.pr_rank and e.pr_rank <= 3
        )

        lines.append("")
        lines.append(f"Segments ({len(detail.segment_efforts)}):")
        if pr_count > 0:
            lines.append(f"  PRs: {pr_count}")
        if top3_count > pr_count:
            lines.append(f"  Top 3 efforts: {top3_count}")

        for effort in detail.segment_efforts:
            pr_tag = ""
            if effort.pr_rank == 1:
                pr_tag = " [PR!]"
            elif effort.pr_rank == 2:
                pr_tag = " [2nd best]"
            elif effort.pr_rank == 3:
                pr_tag = " [3rd best]"

            eff_min = effort.elapsed_time_seconds // 60
            eff_sec = effort.elapsed_time_seconds % 60
            lines.append(f"  {effort.name}: {eff_min}:{eff_sec:02d}{pr_tag}")

    # Trail matching
    if gps_points:
        search_lat = gps_points[0].lat
        search_lon = gps_points[0].lon
        try:
            async with OverpassClient() as overpass:
                known_trails = await overpass.find_trails(
                    search_lat, search_lon, radius_m=5000
                )

            if known_trails:
                segments = tag_ride_segments(gps_points, known_trails)
                if segments:
                    lines.append("")
                    lines.append(f"Trails Ridden ({len(segments)}):")
                    for seg in segments:
                        difficulty = seg.get("trail_difficulty") or "unrated"
                        confidence = seg.get("overlap_confidence", 0)
                        lines.append(
                            f"  {seg['trail_name']} ({difficulty}) "
                            f"- confidence: {confidence}%"
                        )
        except Exception as exc:
            logger.warning("post_ride_trail_match_error", error=str(exc))
            lines.append("")
            lines.append(f"Trail matching unavailable: {exc}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Sprint 13: Weekend Planner
# ---------------------------------------------------------------------------


@mcp.tool()
async def weekend_planner(
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = 30.0,
    preferred_distance_km: float | None = None,
    preferred_difficulty: str | None = None,
) -> str:
    """Plan your weekend rides! Analyzes weather for Saturday and Sunday,
    estimates trail conditions, calculates ride scores, and suggests tours.
    Returns which day is best and what tours to ride."""
    from mtb_mcp.intelligence.weekend_planner import plan_weekend

    resolved_lat, resolved_lon = _resolve_location(lat, lon)

    plan = await plan_weekend(
        lat=resolved_lat,
        lon=resolved_lon,
        radius_km=radius_km,
        preferred_distance_km=preferred_distance_km,
        preferred_difficulty=preferred_difficulty,
    )

    lines: list[str] = [
        f"Weekend Ride Plan for ({resolved_lat:.2f}, {resolved_lon:.2f})",
        f"Best day: {plan.best_day}",
        "",
        plan.summary,
        "",
    ]

    for label, day in [("SATURDAY", plan.saturday), ("SUNDAY", plan.sunday)]:
        if day is None:
            lines.append(f"{label}: No data available")
            continue

        lines.append(f"{label} ({day.date.isoformat()}):")
        lines.append(f"  Score: {day.ride_score}/100 -- {day.verdict}")
        lines.append(f"  Weather: {day.weather_summary}")
        lines.append(f"  Trail condition: {day.trail_condition}")
        lines.append(f"  Reasoning: {day.reasoning}")

        if day.suggested_tours:
            lines.append("  Suggested tours:")
            for tour in day.suggested_tours:
                lines.append(f"    - {tour}")
        lines.append("")

    return "\n".join(lines)
