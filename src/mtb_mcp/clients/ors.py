"""OpenRouteService (ORS) API client as routing fallback."""

from __future__ import annotations

from typing import Any

import httpx
import structlog

from mtb_mcp.clients.base import BaseClient
from mtb_mcp.models.common import GeoPoint
from mtb_mcp.models.route import Route, RouteSummary

logger = structlog.get_logger(__name__)

# Average MTB speed for duration estimates (km/h)
_AVG_MTB_SPEED_KMH = 12.0


def _elevation_loss_from_values(elevations: list[float]) -> float:
    """Calculate total elevation loss from a list of elevation values."""
    loss = 0.0
    for i in range(1, len(elevations)):
        if elevations[i] < elevations[i - 1]:
            loss += elevations[i - 1] - elevations[i]
    return loss


def _elevation_gain_from_values(elevations: list[float]) -> float:
    """Calculate total elevation gain from a list of elevation values."""
    gain = 0.0
    for i in range(1, len(elevations)):
        if elevations[i] > elevations[i - 1]:
            gain += elevations[i] - elevations[i - 1]
    return gain


class ORSClient(BaseClient):
    """Client for OpenRouteService cycling-mountain routing.

    Used as fallback when BRouter is not available.
    Free tier: 40 req/min.
    """

    def __init__(self, api_key: str | None = None) -> None:
        super().__init__(
            base_url="https://api.openrouteservice.org",
            rate_limit=1.0,  # Stay well under 40/min limit
        )
        self._api_key = api_key

    async def plan_route(self, start: GeoPoint, end: GeoPoint) -> Route:
        """Calculate cycling-mountain route.

        POST /v2/directions/cycling-mountain/geojson
        Body: {"coordinates": [[lon1,lat1],[lon2,lat2]]}
        Header: Authorization: {api_key}
        """
        if not self._api_key:
            msg = "ORS API key is required"
            raise ValueError(msg)

        body: dict[str, Any] = {
            "coordinates": [
                [start.lon, start.lat],
                [end.lon, end.lat],
            ],
            "elevation": True,
        }

        await self._rate_limiter.acquire()
        client = self._get_client()

        response = await client.request(
            method="POST",
            url="/v2/directions/cycling-mountain/geojson",
            json=body,
            headers={
                "Authorization": self._api_key,
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        data: dict[str, Any] = response.json()

        logger.info(
            "ors_route_calculated",
            start=f"{start.lat},{start.lon}",
            end=f"{end.lat},{end.lon}",
        )

        return self._parse_geojson_route(data)

    async def is_available(self) -> bool:
        """Check if ORS API key is configured and service is reachable."""
        if not self._api_key:
            return False
        try:
            client = self._get_client()
            response = await client.get(
                "/v2/health",
                headers={"Authorization": self._api_key},
            )
            return response.status_code == 200
        except (httpx.TransportError, httpx.TimeoutException):
            return False

    def _parse_geojson_route(self, data: dict[str, Any]) -> Route:
        """Parse ORS GeoJSON response into a Route model."""
        features = data.get("features", [])
        if not features:
            msg = "No route features in ORS response"
            raise ValueError(msg)

        feature = features[0]
        geometry = feature.get("geometry", {})
        properties = feature.get("properties", {})
        summary = properties.get("summary", {})

        # Parse coordinates: ORS returns [lon, lat, ele] with elevation=True
        coordinates: list[list[float]] = geometry.get("coordinates", [])
        points: list[GeoPoint] = []
        elevations: list[float] = []

        for coord in coordinates:
            ele = coord[2] if len(coord) > 2 else None
            points.append(GeoPoint(lat=coord[1], lon=coord[0], ele=ele))
            if ele is not None:
                elevations.append(ele)

        # ORS returns distance in meters, duration in seconds
        distance_m = summary.get("distance", 0.0)
        distance_km = distance_m / 1000.0

        # Use ORS duration if available, else estimate
        duration_sec = summary.get("duration", 0.0)
        duration_minutes = duration_sec / 60.0 if duration_sec > 0 else None

        # Calculate elevation from coordinates
        gain = _elevation_gain_from_values(elevations) if elevations else 0.0
        loss = _elevation_loss_from_values(elevations) if elevations else 0.0

        route_summary = RouteSummary(
            distance_km=round(distance_km, 2),
            elevation_gain_m=round(gain, 1),
            elevation_loss_m=round(loss, 1),
            duration_minutes=round(duration_minutes, 0) if duration_minutes else None,
            source="ors",
        )

        return Route(
            summary=route_summary,
            points=points,
        )
