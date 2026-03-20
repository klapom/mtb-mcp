"""eBike range endpoints."""
from __future__ import annotations

import time
from dataclasses import asdict
from typing import Any

import structlog
from fastapi import APIRouter
from pydantic import BaseModel

from mtb_mcp.api.models import err, ok
from mtb_mcp.intelligence.ebike_range import (
    ASSIST_FACTORS,
    EBikeRangeInput,
    calculate_range,
    estimate_flat_range_km,
)
from mtb_mcp.models.common import GeoPoint

logger = structlog.get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class RangeCheckRequest(BaseModel):
    battery_wh: float = 625.0
    charge_pct: float = 100.0
    distance_km: float | None = None
    elevation_gain_m: float | None = None
    rider_kg: float = 80.0
    bike_kg: float = 23.0
    assist_mode: str = "tour"


# ---------------------------------------------------------------------------
# Helpers (reused from tools/ebike_tools.py, no duplication of logic)
# ---------------------------------------------------------------------------

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

    num_segments = 30
    points: list[GeoPoint] = []

    for i in range(num_segments + 1):
        fraction = i / num_segments
        ele = (fraction / 0.67) * elevation_gain_m if fraction < 0.67 else elevation_gain_m
        lat = 49.0 + (fraction * distance_km / 111.0)
        points.append(GeoPoint(lat=lat, lon=11.0, ele=ele))

    return points


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/range-check")
async def range_check(body: RangeCheckRequest) -> dict[str, Any]:
    """Check if eBike battery is sufficient for a planned route."""
    t = time.monotonic()

    if body.assist_mode not in ASSIST_FACTORS:
        return err(
            "VALIDATION_ERROR",
            f"Unknown assist mode '{body.assist_mode}'. "
            f"Valid: {', '.join(ASSIST_FACTORS.keys())}",
        )

    range_input = EBikeRangeInput(
        battery_wh=body.battery_wh,
        charge_pct=body.charge_pct,
        rider_kg=body.rider_kg,
        bike_kg=body.bike_kg,
        assist_mode=body.assist_mode,
    )

    # Route estimation with distance + optional elevation
    if body.distance_km is not None:
        gain = body.elevation_gain_m or 0.0
        profile_points = _build_synthetic_elevation_profile(body.distance_km, gain)

        if not profile_points:
            return err("VALIDATION_ERROR", "distance_km must be greater than 0.")

        result = calculate_range(range_input, profile_points)
        return ok(
            {
                **asdict(result),
                "route_distance_km": body.distance_km,
                "assist_mode": body.assist_mode,
            },
            t,
        )

    # Flat range estimate fallback (no distance provided)
    flat_range = estimate_flat_range_km(
        battery_wh=body.battery_wh,
        charge_pct=body.charge_pct,
        assist_mode=body.assist_mode,
        rider_kg=body.rider_kg,
        bike_kg=body.bike_kg,
    )

    return ok(
        {
            "battery_wh": body.battery_wh,
            "charge_pct": body.charge_pct,
            "assist_mode": body.assist_mode,
            "estimated_flat_range_km": flat_range,
            "note": (
                "Flat terrain estimate only. Provide distance_km and "
                "elevation_gain_m for a more accurate calculation."
            ),
        },
        t,
    )


@router.get("/battery-status")
async def battery_status() -> dict[str, Any]:
    """eBike battery status (placeholder until Bosch Cloud integration)."""
    t = time.monotonic()
    return ok(
        {
            "available": False,
            "message": (
                "Direct battery reading not yet available. "
                "Bosch eBike Cloud integration is planned."
            ),
            "common_batteries": {
                "bosch": {
                    "PowerTube 400": 400,
                    "PowerTube 500": 500,
                    "PowerTube 625": 625,
                    "PowerTube 750": 750,
                },
                "shimano": {
                    "BT-E8010": 504,
                    "BT-E8035": 504,
                    "BT-E8036": 630,
                },
            },
        },
        t,
    )
