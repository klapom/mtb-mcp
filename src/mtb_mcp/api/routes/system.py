"""System endpoints -- health, config, API status."""
from __future__ import annotations

import time
from typing import Any

import httpx
from fastapi import APIRouter

from mtb_mcp.api.deps import get_cached_settings
from mtb_mcp.api.models import err, ok

router = APIRouter()


@router.get("/config")
async def config() -> dict[str, Any]:
    """Return non-sensitive configuration values."""
    t = time.monotonic()
    try:
        settings = get_cached_settings()
        return ok(
            {
                "home_lat": settings.home_lat,
                "home_lon": settings.home_lon,
                "default_radius_km": settings.default_radius_km,
                "log_level": settings.log_level,
            },
            t,
        )
    except Exception as exc:
        return err("INTERNAL_ERROR", f"Failed to load config: {exc}")


async def _check_reachable(url: str, timeout: float = 5.0) -> bool:
    """Probe a URL with a short-timeout GET and return True if it responds."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url)
            return resp.status_code < 500
    except Exception:  # noqa: BLE001
        return False


@router.get("/api-status")
async def api_status() -> dict[str, Any]:
    """Check which APIs are configured and optionally reachable."""
    t = time.monotonic()
    settings = get_cached_settings()

    apis: list[dict[str, Any]] = []

    # --- Free / no-auth APIs: check reachability ---
    dwd_reachable = await _check_reachable("https://api.brightsky.dev/")
    apis.append({
        "name": "dwd",
        "configured": True,
        "reachable": dwd_reachable,
    })

    overpass_reachable = await _check_reachable(
        "https://overpass-api.de/api/status"
    )
    apis.append({
        "name": "overpass",
        "configured": True,
        "reachable": overpass_reachable,
    })

    # --- Auth-required APIs: only check if credentials exist ---
    apis.append({
        "name": "strava",
        "configured": bool(
            settings.strava_client_id and settings.strava_client_secret
        ),
        "reachable": None,
    })

    apis.append({
        "name": "komoot",
        "configured": bool(
            settings.komoot_email and settings.komoot_password
        ),
        "reachable": None,
    })

    apis.append({
        "name": "ors",
        "configured": bool(settings.ors_api_key),
        "reachable": None,
    })

    apis.append({
        "name": "brouter",
        "configured": bool(settings.brouter_url),
        "reachable": None,
    })

    apis.append({
        "name": "searxng",
        "configured": bool(settings.searxng_url),
        "reachable": None,
    })

    return ok({"apis": apis}, t)
