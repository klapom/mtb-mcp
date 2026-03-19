"""OSM Overpass API client for MTB trail data."""

from __future__ import annotations

from typing import Any

import structlog

from mtb_mcp.clients.base import BaseClient
from mtb_mcp.models.common import GeoPoint
from mtb_mcp.models.trail import MTBScale, Trail, TrailSurface

logger = structlog.get_logger(__name__)

# Mapping from OSM surface values to our TrailSurface enum
_SURFACE_MAP: dict[str, TrailSurface] = {
    "asphalt": TrailSurface.asphalt,
    "paved": TrailSurface.asphalt,
    "concrete": TrailSurface.asphalt,
    "gravel": TrailSurface.gravel,
    "fine_gravel": TrailSurface.gravel,
    "compacted": TrailSurface.gravel,
    "pebblestone": TrailSurface.gravel,
    "dirt": TrailSurface.dirt,
    "earth": TrailSurface.dirt,
    "ground": TrailSurface.dirt,
    "mud": TrailSurface.dirt,
    "grass": TrailSurface.grass,
    "rock": TrailSurface.rock,
    "stone": TrailSurface.rock,
    "roots": TrailSurface.roots,
    "wood": TrailSurface.roots,
    "sand": TrailSurface.sand,
}

# Valid MTB scale values from OSM
_MTB_SCALE_MAP: dict[str, MTBScale] = {
    "0": MTBScale.S0,
    "0+": MTBScale.S0,
    "0-": MTBScale.S0,
    "1": MTBScale.S1,
    "1+": MTBScale.S1,
    "1-": MTBScale.S1,
    "2": MTBScale.S2,
    "2+": MTBScale.S2,
    "2-": MTBScale.S2,
    "3": MTBScale.S3,
    "3+": MTBScale.S3,
    "3-": MTBScale.S3,
    "4": MTBScale.S4,
    "4+": MTBScale.S4,
    "4-": MTBScale.S4,
    "5": MTBScale.S5,
    "5+": MTBScale.S5,
    "5-": MTBScale.S5,
    "6": MTBScale.S6,
}


def _parse_surface(raw: str | None) -> TrailSurface | None:
    """Parse an OSM surface tag value to TrailSurface enum."""
    if raw is None:
        return None
    return _SURFACE_MAP.get(raw.lower())


def _parse_mtb_scale(raw: str | None) -> MTBScale | None:
    """Parse an OSM mtb:scale tag value to MTBScale enum."""
    if raw is None:
        return None
    return _MTB_SCALE_MAP.get(raw.strip())


def _calculate_length(geometry: list[dict[str, float]]) -> float:
    """Approximate length in meters from a list of lat/lon points.

    Uses the Haversine formula for each segment.
    """
    import math

    total = 0.0
    for i in range(len(geometry) - 1):
        lat1 = math.radians(geometry[i]["lat"])
        lon1 = math.radians(geometry[i]["lon"])
        lat2 = math.radians(geometry[i + 1]["lat"])
        lon2 = math.radians(geometry[i + 1]["lon"])

        dlat = lat2 - lat1
        dlon = lon2 - lon1

        a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        c = 2 * math.asin(math.sqrt(a))
        total += 6371000 * c  # Earth radius in meters

    return total


def _parse_trail(element: dict[str, Any]) -> Trail:
    """Parse an Overpass API element into a Trail model."""
    tags = element.get("tags", {})
    raw_geometry = element.get("geometry", [])

    geo_points = [
        GeoPoint(lat=pt["lat"], lon=pt["lon"])
        for pt in raw_geometry
    ]

    length = _calculate_length(raw_geometry) if len(raw_geometry) >= 2 else None

    return Trail(
        osm_id=element["id"],
        name=tags.get("name"),
        mtb_scale=_parse_mtb_scale(tags.get("mtb:scale")),
        surface=_parse_surface(tags.get("surface")),
        length_m=round(length, 1) if length is not None else None,
        geometry=geo_points,
    )


class OverpassClient(BaseClient):
    """Client for OSM Overpass API to query MTB trail data."""

    def __init__(self, url: str = "https://overpass-api.de") -> None:
        super().__init__(base_url=url, rate_limit=1.0)  # Very conservative

    async def _query(self, overpass_ql: str) -> list[dict[str, Any]]:
        """Execute an Overpass QL query and return elements."""
        response = await self._request(
            "POST",
            "/api/interpreter",
            data={"data": overpass_ql},
        )
        result: dict[str, Any] = response.json()
        elements: list[dict[str, Any]] = result.get("elements", [])
        return elements

    async def find_trails(
        self,
        lat: float,
        lon: float,
        radius_m: float = 30000,
        min_scale: MTBScale | None = None,
    ) -> list[Trail]:
        """Find MTB trails within radius of a point.

        Queries Overpass for ways tagged with mtb:scale within the given radius.
        """
        query = (
            f"[out:json][timeout:30];"
            f'way(around:{radius_m},{lat},{lon})["mtb:scale"];'
            f"out geom;"
        )

        logger.debug("overpass_query", query=query)
        elements = await self._query(query)

        trails = [_parse_trail(el) for el in elements]

        # Filter by minimum scale if specified
        if min_scale is not None:
            scale_order = list(MTBScale)
            min_idx = scale_order.index(min_scale)
            trails = [
                t for t in trails
                if t.mtb_scale is not None and scale_order.index(t.mtb_scale) >= min_idx
            ]

        # Sort by name (unnamed trails last)
        trails.sort(key=lambda t: (t.name is None, t.name or ""))

        return trails

    async def get_trail_details(self, osm_id: int) -> Trail | None:
        """Get details for a specific OSM way by ID."""
        query = f"[out:json][timeout:10];way({osm_id});out geom;"

        elements = await self._query(query)
        if not elements:
            return None

        return _parse_trail(elements[0])
