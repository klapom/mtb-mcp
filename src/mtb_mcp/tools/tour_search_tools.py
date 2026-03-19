"""MCP tools for multi-source tour search."""

from __future__ import annotations

import structlog

from mtb_mcp.clients.gpstour import GPSTourClient
from mtb_mcp.clients.komoot import KomootClient
from mtb_mcp.config import get_settings
from mtb_mcp.models.tour import TourDetail, TourDifficulty, TourSummary
from mtb_mcp.server import mcp

logger = structlog.get_logger(__name__)


def _format_tour_summary(tour: TourSummary) -> str:
    """Format a TourSummary as a human-readable string."""
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


def _format_tour_detail(tour: TourDetail) -> str:
    """Format a TourDetail as a human-readable string."""
    lines: list[str] = [f"Tour: {tour.name}", f"Source: {tour.source.value}"]

    if tour.distance_km is not None:
        lines.append(f"Distance: {tour.distance_km} km")
    if tour.elevation_m is not None:
        lines.append(f"Elevation: {tour.elevation_m:.0f} m")
    if tour.difficulty is not None:
        lines.append(f"Difficulty: {tour.difficulty.value}")
    if tour.duration_minutes is not None:
        hours = tour.duration_minutes // 60
        mins = tour.duration_minutes % 60
        lines.append(f"Duration: {hours}h {mins:02d}min")
    if tour.region:
        lines.append(f"Region: {tour.region}")
    if tour.rating is not None:
        lines.append(f"Rating: {tour.rating}")
    if tour.download_count is not None:
        lines.append(f"Downloads: {tour.download_count}")
    if tour.surfaces:
        lines.append(f"Surfaces: {', '.join(tour.surfaces)}")
    if tour.description:
        desc = tour.description[:500]
        if len(tour.description) > 500:
            desc += "..."
        lines.append(f"\nDescription:\n{desc}")
    if tour.url:
        lines.append(f"\nURL: {tour.url}")
    if tour.start_point:
        lines.append(f"Start: {tour.start_point.lat:.4f}, {tour.start_point.lon:.4f}")
    if tour.waypoints:
        lines.append(f"Waypoints: {len(tour.waypoints)} coordinates available")

    return "\n".join(lines)


def _validate_difficulty(difficulty: str | None) -> TourDifficulty | None:
    """Validate and convert difficulty string to enum."""
    if difficulty is None:
        return None
    try:
        return TourDifficulty(difficulty.lower())
    except ValueError:
        return None


@mcp.tool()
async def search_tours(
    query: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = 30.0,
    min_distance_km: float | None = None,
    max_distance_km: float | None = None,
    difficulty: str | None = None,
) -> str:
    """Search for MTB tours across multiple sources (Komoot + GPS-Tour.info).

    Provide a search query and/or coordinates.
    Uses home location if no coordinates given.
    Returns unified results with source, distance, elevation, difficulty.
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
            logger.warning("search_tours_komoot_error", error=str(exc))

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
        logger.warning("search_tours_gpstour_error", error=str(exc))

    # Filter by difficulty if specified
    diff_filter = _validate_difficulty(difficulty)
    if diff_filter is not None:
        all_results = [t for t in all_results if t.difficulty == diff_filter]

    # Filter by distance range
    if min_distance_km is not None:
        all_results = [
            t for t in all_results
            if t.distance_km is not None and t.distance_km >= min_distance_km
        ]
    if max_distance_km is not None:
        all_results = [
            t for t in all_results
            if t.distance_km is not None and t.distance_km <= max_distance_km
        ]

    if not all_results:
        return (
            f"No tours found near {search_lat:.2f}, {search_lon:.2f} "
            f"(radius: {radius_km} km). "
            "Check that Komoot credentials are configured or SearXNG is running."
        )

    header = (
        f"Found {len(all_results)} tour(s) near "
        f"{search_lat:.2f}, {search_lon:.2f} (radius: {radius_km} km):\n"
    )
    tour_lines = [_format_tour_summary(t) for t in all_results]
    return header + "\n\n".join(tour_lines)


@mcp.tool()
async def komoot_tour_details(tour_id: str) -> str:
    """Get detailed information about a Komoot tour.

    Includes segments, surfaces, elevation profile, and description.
    """
    settings = get_settings()
    if not settings.komoot_email:
        return "Komoot credentials not configured. Set MTB_MCP_KOMOOT_EMAIL and MTB_MCP_KOMOOT_PASSWORD."

    try:
        async with KomootClient(
            email=settings.komoot_email,
            password=settings.komoot_password,
        ) as komoot:
            detail = await komoot.get_tour_details(tour_id)
    except Exception as exc:
        return f"Error fetching Komoot tour {tour_id}: {exc}"

    if detail is None:
        return f"Tour {tour_id} not found on Komoot or authentication failed."

    return _format_tour_detail(detail)


@mcp.tool()
async def komoot_download_gpx(tour_id: str) -> str:
    """Download a Komoot tour as GPX file. Returns the file path or GPX data info."""
    settings = get_settings()
    if not settings.komoot_email:
        return "Komoot credentials not configured. Set MTB_MCP_KOMOOT_EMAIL and MTB_MCP_KOMOOT_PASSWORD."

    try:
        async with KomootClient(
            email=settings.komoot_email,
            password=settings.komoot_password,
        ) as komoot:
            gpx_data = await komoot.download_gpx(tour_id)
    except Exception as exc:
        return f"Error downloading GPX for Komoot tour {tour_id}: {exc}"

    if gpx_data is None:
        return f"Could not download GPX for tour {tour_id}. Check authentication."

    # Save to data directory
    data_dir = settings.resolved_data_dir / "gpx"
    data_dir.mkdir(parents=True, exist_ok=True)
    gpx_path = data_dir / f"komoot_{tour_id}.gpx"
    gpx_path.write_bytes(gpx_data)

    return f"GPX downloaded: {gpx_path} ({len(gpx_data)} bytes)"


@mcp.tool()
async def gpstour_tour_details(tour_id: str) -> str:
    """Get detailed information about a GPS-Tour.info tour.

    Scrapes the tour detail page for metadata, description, and ratings.
    """
    settings = get_settings()

    try:
        async with GPSTourClient(
            searxng_url=settings.searxng_url,
            username=settings.gpstour_username,
            password=settings.gpstour_password,
        ) as gpstour:
            detail = await gpstour.get_tour_details(tour_id)
    except Exception as exc:
        return f"Error fetching GPS-Tour.info tour {tour_id}: {exc}"

    if detail is None:
        return f"Tour {tour_id} not found on GPS-Tour.info."

    return _format_tour_detail(detail)


@mcp.tool()
async def gpstour_download_gpx(tour_id: str) -> str:
    """Download a GPS-Tour.info tour as GPX file.

    Requires GPS-Tour.info login credentials (MTB_MCP_GPSTOUR_USERNAME/PASSWORD).
    """
    settings = get_settings()
    if not settings.gpstour_username:
        return (
            "GPS-Tour.info credentials not configured. "
            "Set MTB_MCP_GPSTOUR_USERNAME and MTB_MCP_GPSTOUR_PASSWORD."
        )

    try:
        async with GPSTourClient(
            searxng_url=settings.searxng_url,
            username=settings.gpstour_username,
            password=settings.gpstour_password,
        ) as gpstour:
            gpx_data = await gpstour.download_gpx(tour_id)
    except Exception as exc:
        return f"Error downloading GPX for GPS-Tour.info tour {tour_id}: {exc}"

    if gpx_data is None:
        return f"Could not download GPX for tour {tour_id}. Check login credentials."

    # Save to data directory
    data_dir = settings.resolved_data_dir / "gpx"
    data_dir.mkdir(parents=True, exist_ok=True)
    gpx_path = data_dir / f"gpstour_{tour_id}.gpx"
    gpx_path.write_bytes(gpx_data)

    return f"GPX downloaded: {gpx_path} ({len(gpx_data)} bytes)"


@mcp.tool()
async def mtbproject_trails(
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = 30.0,
) -> str:
    """Search for trails on MTB Project.

    Note: Limited availability outside North America.
    Uses the MTB Project / Trailforks API where available.
    """
    settings = get_settings()
    search_lat = lat if lat is not None else settings.home_lat
    search_lon = lon if lon is not None else settings.home_lon

    return (
        f"MTB Project search near {search_lat:.2f}, {search_lon:.2f} "
        f"(radius: {radius_km} km)\n\n"
        "Note: MTB Project API integration is planned for a future release. "
        "MTB Project (now part of Trailforks) has limited API availability. "
        "For trail information, try:\n"
        "  - search_tours() for Komoot and GPS-Tour.info results\n"
        "  - OSM Overpass queries for trail geometry and mtb:scale ratings\n"
        "  - Visit https://www.trailforks.com/ directly for trail conditions"
    )
