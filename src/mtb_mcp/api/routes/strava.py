"""Strava endpoints wrapping Strava client."""
from __future__ import annotations

import time
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from mtb_mcp.api.deps import get_cached_settings, resolve_location
from mtb_mcp.api.models import err, ok, ok_list
from mtb_mcp.auth.dependencies import get_current_user
from mtb_mcp.auth.encryption import decrypt_token
from mtb_mcp.auth.models import User
from mtb_mcp.clients.strava import StravaClient
from mtb_mcp.storage.database import Database
from mtb_mcp.storage.user_store import UserStore

logger = structlog.get_logger(__name__)

router = APIRouter()


# ── Helpers ────────────────────────────────────────────────────────


async def _get_strava_client_for_user(user: User) -> StravaClient | None:
    """Create a StravaClient using the user's stored tokens."""
    settings = get_cached_settings()
    if not settings.token_encryption_key:
        return None

    db = Database(settings.resolved_db_path)
    try:
        await db.initialize()
        store = UserStore(db)
        access_enc, refresh_enc, expires_at = await store.get_strava_tokens(user.id)
    finally:
        await db.close()

    if not access_enc:
        return None

    access_token = decrypt_token(access_enc, settings.token_encryption_key)
    refresh_token = decrypt_token(refresh_enc, settings.token_encryption_key) if refresh_enc else None

    return StravaClient(
        client_id=settings.strava_client_id,
        client_secret=settings.strava_client_secret,
        access_token=access_token,
        refresh_token=refresh_token,
    )


_AUTH_ERR = ("AUTH_MISSING", "Strava credentials not configured")


# ── Endpoints ──────────────────────────────────────────────────────


@router.get("/activities")
async def list_activities(
    limit: int = Query(10, ge=1, le=100),
    include_all_types: bool = False,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get recent Strava activities."""
    t = time.monotonic()
    client = await _get_strava_client_for_user(user)
    if client is None:
        return err(*_AUTH_ERR)

    try:
        async with client:
            sport_type = None if include_all_types else "MountainBikeRide"
            activities = await client.get_recent_activities(
                limit=limit, sport_type=sport_type,
            )
    except Exception as exc:
        return err("EXTERNAL_API_ERROR", f"Strava API error: {exc}")

    items = [a.model_dump(mode="json") for a in activities]
    return ok_list(items, len(items), t)


@router.get("/activities/{activity_id}")
async def activity_detail(
    activity_id: int,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get detailed information about a Strava activity."""
    t = time.monotonic()
    client = await _get_strava_client_for_user(user)
    if client is None:
        return err(*_AUTH_ERR)

    try:
        async with client:
            detail = await client.get_activity_details(activity_id)
    except Exception as exc:
        return err("EXTERNAL_API_ERROR", f"Strava API error: {exc}")

    return ok(detail.model_dump(mode="json"), t)


@router.get("/athlete/stats")
async def athlete_stats(
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get Strava athlete statistics."""
    t = time.monotonic()
    client = await _get_strava_client_for_user(user)
    if client is None:
        return err(*_AUTH_ERR)

    try:
        async with client:
            stats = await client.get_athlete_stats()
    except Exception as exc:
        return err("EXTERNAL_API_ERROR", f"Strava API error: {exc}")

    return ok(stats.model_dump(mode="json"), t)


@router.get("/segments")
async def explore_segments(
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = Query(10.0, gt=0),
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Discover Strava segments near a location."""
    t = time.monotonic()
    client = await _get_strava_client_for_user(user)
    if client is None:
        return err(*_AUTH_ERR)

    search_lat, search_lon = resolve_location(lat, lon, user=user)

    try:
        async with client:
            segments = await client.explore_segments(
                search_lat, search_lon, radius_km,
            )
    except Exception as exc:
        return err("EXTERNAL_API_ERROR", f"Strava API error: {exc}")

    items = [s.model_dump(mode="json") for s in segments]
    return ok_list(items, len(items), t)


@router.get("/activities/{activity_id}/gpx", response_model=None)
async def export_gpx(
    activity_id: int,
    user: User = Depends(get_current_user),
) -> Response | dict[str, Any]:
    """Export a Strava activity as GPX."""
    client = await _get_strava_client_for_user(user)
    if client is None:
        return err(*_AUTH_ERR)

    try:
        async with client:
            gpx_xml = await client.export_gpx(activity_id)
    except ValueError as exc:
        return err("NO_GPS_DATA", str(exc))
    except Exception as exc:
        return err("EXTERNAL_API_ERROR", f"Strava GPX export error: {exc}")

    return Response(
        content=gpx_xml,
        media_type="application/gpx+xml",
        headers={"Content-Disposition": f"attachment; filename=strava_{activity_id}.gpx"},
    )
