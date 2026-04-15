"""Tour search endpoints wrapping Komoot + GPS-Tour clients."""
from __future__ import annotations

import time
from typing import Any

import structlog
from fastapi import APIRouter, Query
from fastapi.responses import Response

from mtb_mcp.api.deps import get_cached_settings, resolve_location
from mtb_mcp.api.models import err, ok, ok_list
from mtb_mcp.clients.gpstour import GPSTourClient
from mtb_mcp.clients.komoot import KomootClient
from mtb_mcp.models.tour import TourDifficulty, TourSummary

logger = structlog.get_logger(__name__)

router = APIRouter()


def _validate_difficulty(difficulty: str | None) -> TourDifficulty | None:
    """Validate and convert difficulty string to enum."""
    if difficulty is None:
        return None
    try:
        return TourDifficulty(difficulty.lower())
    except ValueError:
        return None


@router.get("/search")
async def search_tours(
    query: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = Query(30.0, gt=0),
    min_distance_km: float | None = None,
    max_distance_km: float | None = None,
    difficulty: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Search for MTB tours across Komoot and GPS-Tour.info."""
    t = time.monotonic()
    settings = get_cached_settings()
    search_lat, search_lon = resolve_location(lat, lon)
    all_results: list[TourSummary] = []

    # Search Komoot
    if settings.komoot_email:
        try:
            async with KomootClient(
                email=settings.komoot_email,
                password=settings.komoot_password,
            ) as komoot:
                komoot_results = await komoot.search_tours(
                    lat=search_lat, lon=search_lon, radius_km=radius_km,
                )
                all_results.extend(komoot_results)
        except Exception as exc:
            logger.warning("api_search_tours_komoot_error", error=str(exc))

    # Search GPS-Tour.info via SearXNG
    # GPS-Tour needs a text query, not coordinates — reverse-geocode if needed
    gpstour_query = query
    if not gpstour_query:
        try:
            import httpx
            resp = await httpx.AsyncClient().get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": str(search_lat), "lon": str(search_lon), "format": "json", "zoom": "10"},
                headers={"User-Agent": "TrailPilot/0.1"},
            )
            if resp.status_code == 200:
                addr = resp.json().get("address", {})
                gpstour_query = f"mtb {addr.get('city', addr.get('town', addr.get('county', '')))}"
        except Exception:
            pass
    if gpstour_query:
        try:
            async with GPSTourClient(
                searxng_url=settings.searxng_url,
                username=settings.gpstour_username,
                password=settings.gpstour_password,
            ) as gpstour:
                gpstour_results = await gpstour.search_tours(query=gpstour_query)
                all_results.extend(gpstour_results)
        except Exception as exc:
            logger.warning("api_search_tours_gpstour_error", error=str(exc))

    # Filter by difficulty
    diff_filter = _validate_difficulty(difficulty)
    if diff_filter is not None:
        all_results = [t_ for t_ in all_results if t_.difficulty == diff_filter]

    # Filter by distance range
    if min_distance_km is not None:
        all_results = [
            t_ for t_ in all_results
            if t_.distance_km is not None and t_.distance_km >= min_distance_km
        ]
    if max_distance_km is not None:
        all_results = [
            t_ for t_ in all_results
            if t_.distance_km is not None and t_.distance_km <= max_distance_km
        ]

    total = len(all_results)
    page = all_results[offset : offset + limit]
    return ok_list(
        [r.model_dump(mode="json") for r in page],
        total,
        t,
    )


@router.get("/komoot/{tour_id}")
async def komoot_tour_details(tour_id: str) -> dict[str, Any]:
    """Get detailed information about a Komoot tour."""
    t = time.monotonic()
    settings = get_cached_settings()
    if not settings.komoot_email:
        return err("AUTH_MISSING", "Komoot credentials not configured")

    try:
        async with KomootClient(
            email=settings.komoot_email,
            password=settings.komoot_password,
        ) as komoot:
            detail = await komoot.get_tour_details(tour_id)
    except Exception as exc:
        return err("EXTERNAL_API_ERROR", f"Komoot API error: {exc}")

    if detail is None:
        return err("NOT_FOUND", f"Tour {tour_id} not found on Komoot")

    return ok(detail.model_dump(mode="json"), t)


@router.get("/komoot/{tour_id}/gpx", response_model=None)
async def komoot_download_gpx(tour_id: str) -> Response | dict[str, Any]:
    """Download a Komoot tour as GPX file."""
    settings = get_cached_settings()
    if not settings.komoot_email:
        return err("AUTH_MISSING", "Komoot credentials not configured")

    try:
        async with KomootClient(
            email=settings.komoot_email,
            password=settings.komoot_password,
        ) as komoot:
            gpx_data = await komoot.download_gpx(tour_id)
    except Exception as exc:
        return err("EXTERNAL_API_ERROR", f"Komoot GPX download error: {exc}")

    if gpx_data is None:
        return err("NOT_FOUND", f"Could not download GPX for tour {tour_id}")

    return Response(content=gpx_data, media_type="application/gpx+xml")


@router.get("/gpstour/{tour_id}")
async def gpstour_tour_details(tour_id: str) -> dict[str, Any]:
    """Get detailed information about a GPS-Tour.info tour."""
    t = time.monotonic()
    settings = get_cached_settings()

    try:
        async with GPSTourClient(
            searxng_url=settings.searxng_url,
            username=settings.gpstour_username,
            password=settings.gpstour_password,
        ) as gpstour:
            detail = await gpstour.get_tour_details(tour_id)
    except Exception as exc:
        return err("EXTERNAL_API_ERROR", f"GPS-Tour.info API error: {exc}")

    if detail is None:
        return err("NOT_FOUND", f"Tour {tour_id} not found on GPS-Tour.info")

    return ok(detail.model_dump(mode="json"), t)
