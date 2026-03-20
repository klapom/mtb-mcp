"""Routing endpoints wrapping BRouter + ORS clients."""
from __future__ import annotations

import time
from typing import Any

import httpx
import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from mtb_mcp.api.deps import get_cached_settings, resolve_location
from mtb_mcp.api.models import err, ok
from mtb_mcp.clients.brouter import BRouterClient
from mtb_mcp.clients.ors import ORSClient
from mtb_mcp.models.common import GeoPoint

logger = structlog.get_logger(__name__)

router = APIRouter()


# ── Request models ─────────────────────────────────────────────────


class RoutePlanRequest(BaseModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    profile: str = "trekking"


class LoopPlanRequest(BaseModel):
    start_lat: float | None = None
    start_lon: float | None = None
    distance_km: float = 30.0
    profile: str = "trekking"


class ElevationProfileRequest(BaseModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float


# ── Helpers ────────────────────────────────────────────────────────


def _route_to_dict(route: Any) -> dict[str, Any]:
    """Serialise a Route model to a JSON-safe dict."""
    return route.model_dump(mode="json")  # type: ignore[no-any-return]


# ── Endpoints ──────────────────────────────────────────────────────


@router.post("/plan")
async def plan_route(body: RoutePlanRequest) -> dict[str, Any]:
    """Plan an MTB route from A to B.

    Tries BRouter first, falls back to ORS.
    """
    t = time.monotonic()
    settings = get_cached_settings()
    start = GeoPoint(lat=body.start_lat, lon=body.start_lon)
    end = GeoPoint(lat=body.end_lat, lon=body.end_lon)

    # Try BRouter first (self-hosted)
    try:
        async with BRouterClient(base_url=settings.brouter_url) as client:
            route = await client.plan_route(start, end, profile=body.profile)
            return ok(_route_to_dict(route), t)
    except (httpx.ConnectError, httpx.TransportError, httpx.TimeoutException) as exc:
        logger.warning("api_brouter_unavailable", error=str(exc))

    # Fall back to ORS
    if settings.ors_api_key:
        try:
            async with ORSClient(api_key=settings.ors_api_key) as client:
                route = await client.plan_route(start, end)
                return ok(_route_to_dict(route), t)
        except Exception as exc:
            return err("EXTERNAL_API_ERROR", f"ORS routing error: {exc}")

    return err(
        "SERVICE_UNAVAILABLE",
        "BRouter is not available and no ORS API key is configured",
    )


@router.post("/plan-loop")
async def plan_loop_route(body: LoopPlanRequest) -> dict[str, Any]:
    """Plan a loop/round-trip MTB route from a starting point.

    Tries BRouter (required for loop routes).
    """
    t = time.monotonic()
    settings = get_cached_settings()
    resolved_lat, resolved_lon = resolve_location(body.start_lat, body.start_lon)
    start = GeoPoint(lat=resolved_lat, lon=resolved_lon)

    try:
        async with BRouterClient(base_url=settings.brouter_url) as client:
            route = await client.plan_loop_route(
                start, distance_km=body.distance_km, profile=body.profile,
            )
            return ok(_route_to_dict(route), t)
    except (httpx.ConnectError, httpx.TransportError, httpx.TimeoutException) as exc:
        logger.warning("api_brouter_unavailable_for_loop", error=str(exc))

    return err(
        "SERVICE_UNAVAILABLE",
        "Loop route planning requires BRouter. ORS does not support loop routes.",
    )


@router.post("/elevation-profile")
async def elevation_profile(body: ElevationProfileRequest) -> dict[str, Any]:
    """Get the elevation profile between two points."""
    t = time.monotonic()
    settings = get_cached_settings()
    start = GeoPoint(lat=body.start_lat, lon=body.start_lon)
    end = GeoPoint(lat=body.end_lat, lon=body.end_lon)

    # Try BRouter first
    try:
        async with BRouterClient(base_url=settings.brouter_url) as client:
            profile = await client.get_elevation_profile([start, end])
            return ok(profile.model_dump(mode="json"), t)
    except (httpx.ConnectError, httpx.TransportError, httpx.TimeoutException) as exc:
        logger.warning("api_brouter_unavailable_for_elevation", error=str(exc))

    # Fall back to ORS: plan route and return its summary
    if settings.ors_api_key:
        try:
            async with ORSClient(api_key=settings.ors_api_key) as client:
                route = await client.plan_route(start, end)
                return ok(_route_to_dict(route), t)
        except Exception as exc:
            return err("EXTERNAL_API_ERROR", f"ORS elevation error: {exc}")

    return err(
        "SERVICE_UNAVAILABLE",
        "BRouter is not available and no ORS API key is configured",
    )
