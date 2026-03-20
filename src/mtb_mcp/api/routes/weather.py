"""Weather endpoints wrapping DWD client."""
from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Query

from mtb_mcp.api.deps import resolve_location
from mtb_mcp.api.models import err, ok
from mtb_mcp.clients.dwd import DWDClient

router = APIRouter()


@router.get("/forecast")
async def forecast(
    lat: float | None = None,
    lon: float | None = None,
    hours: int = Query(72, ge=1, le=168),
) -> dict[str, Any]:
    """Get multi-day hourly weather forecast for a location."""
    t = time.monotonic()
    rlat, rlon = resolve_location(lat, lon)
    try:
        async with DWDClient() as client:
            data = await client.get_forecast(rlat, rlon)
        result = data.model_dump(mode="json")
        result["hours"] = result["hours"][:hours]
        return ok(result, t)
    except Exception as exc:
        return err("EXTERNAL_API_ERROR", f"DWD API error: {exc}")


@router.get("/rain-radar")
async def rain_radar(
    lat: float | None = None,
    lon: float | None = None,
) -> dict[str, Any]:
    """Get rain nowcasting for the next 60 minutes."""
    t = time.monotonic()
    rlat, rlon = resolve_location(lat, lon)
    try:
        async with DWDClient() as client:
            data = await client.get_rain_radar(rlat, rlon)
        return ok(data.model_dump(mode="json"), t)
    except Exception as exc:
        return err("EXTERNAL_API_ERROR", f"DWD API error: {exc}")


@router.get("/alerts")
async def alerts(
    lat: float | None = None,
    lon: float | None = None,
) -> dict[str, Any]:
    """Get active weather alerts for the region."""
    t = time.monotonic()
    rlat, rlon = resolve_location(lat, lon)
    try:
        async with DWDClient() as client:
            data = await client.get_alerts(rlat, rlon)
        return ok({"alerts": [a.model_dump(mode="json") for a in data]}, t)
    except Exception as exc:
        return err("EXTERNAL_API_ERROR", f"DWD API error: {exc}")


@router.get("/history")
async def history(
    lat: float | None = None,
    lon: float | None = None,
) -> dict[str, Any]:
    """Get precipitation history for the last 48 hours."""
    t = time.monotonic()
    rlat, rlon = resolve_location(lat, lon)
    try:
        async with DWDClient() as client:
            data = await client.get_rain_history(rlat, rlon)
        return ok(data.model_dump(mode="json"), t)
    except Exception as exc:
        return err("EXTERNAL_API_ERROR", f"DWD API error: {exc}")
