"""BRouter self-hosted routing client."""

from __future__ import annotations

import math

import structlog

from mtb_mcp.clients.base import BaseClient
from mtb_mcp.models.common import GeoPoint
from mtb_mcp.models.route import (
    ElevationPoint,
    ElevationProfile,
    Route,
    RouteSummary,
)
from mtb_mcp.utils.geo import haversine
from mtb_mcp.utils.gpx import gpx_distance_km, gpx_elevation_gain, parse_gpx

logger = structlog.get_logger(__name__)

# Average MTB speed for duration estimates (km/h)
_AVG_MTB_SPEED_KMH = 12.0


def _elevation_loss(points: list[GeoPoint]) -> float:
    """Calculate total elevation loss in meters (only downhill segments)."""
    loss = 0.0
    prev_ele: float | None = None
    for pt in points:
        if pt.ele is not None:
            if prev_ele is not None and pt.ele < prev_ele:
                loss += prev_ele - pt.ele
            prev_ele = pt.ele
    return loss


def _build_route(gpx_text: str, source: str = "brouter") -> Route:
    """Build a Route model from GPX text."""
    points = parse_gpx(gpx_text)
    distance_km = gpx_distance_km(points)
    gain = gpx_elevation_gain(points)
    loss = _elevation_loss(points)

    # Estimate duration: base speed + penalty for climbing
    # Add ~10 min per 100m elevation gain on top of flat speed
    base_minutes = (distance_km / _AVG_MTB_SPEED_KMH) * 60.0
    climb_penalty = (gain / 100.0) * 10.0
    duration_minutes = base_minutes + climb_penalty

    summary = RouteSummary(
        distance_km=round(distance_km, 2),
        elevation_gain_m=round(gain, 1),
        elevation_loss_m=round(loss, 1),
        duration_minutes=round(duration_minutes, 0),
        source=source,
    )

    return Route(
        summary=summary,
        points=points,
        gpx=gpx_text,
    )


class BRouterClient(BaseClient):
    """Client for self-hosted BRouter HTTP API.

    BRouter provides MTB-optimized routing with various profiles.
    Default: http://localhost:17777
    """

    def __init__(self, base_url: str = "http://localhost:17777") -> None:
        super().__init__(base_url=base_url, rate_limit=10.0)

    async def plan_route(
        self,
        start: GeoPoint,
        end: GeoPoint,
        profile: str = "trekking",
        via_points: list[GeoPoint] | None = None,
    ) -> Route:
        """Calculate a route from start to end.

        BRouter API: GET /brouter?lonlats=LON,LAT|LON,LAT&profile=PROFILE
                     &alternativeidx=0&format=gpx
        """
        all_points = [start]
        if via_points:
            all_points.extend(via_points)
        all_points.append(end)

        lonlats = "|".join(f"{p.lon},{p.lat}" for p in all_points)

        gpx_text = await self._get_text(
            "/brouter",
            params={
                "lonlats": lonlats,
                "profile": profile,
                "alternativeidx": "0",
                "format": "gpx",
            },
        )

        logger.info(
            "brouter_route_calculated",
            start=f"{start.lat},{start.lon}",
            end=f"{end.lat},{end.lon}",
            profile=profile,
        )

        return _build_route(gpx_text, source="brouter")

    async def plan_loop_route(
        self,
        start: GeoPoint,
        distance_km: float = 30.0,
        profile: str = "trekking",
    ) -> Route:
        """Plan a loop route from a starting point.

        Strategy: Generate waypoints in a rough circle around start,
        then route through them back to start.
        """
        # Approximate radius for desired distance (circumference = 2*pi*r)
        radius_km = distance_km / (2.0 * math.pi)

        # Generate 5 waypoints evenly spaced around the circle
        via_points: list[GeoPoint] = []
        num_waypoints = 5
        for i in range(num_waypoints):
            angle = (2.0 * math.pi * i) / num_waypoints
            # Convert km offset to degree offset
            dlat = math.degrees(radius_km / 6371.0) * math.cos(angle)
            dlon = math.degrees(
                radius_km / (6371.0 * math.cos(math.radians(start.lat)))
            ) * math.sin(angle)
            via_points.append(GeoPoint(lat=start.lat + dlat, lon=start.lon + dlon))

        # Route: start → via_points → start
        all_points = [start, *via_points, start]
        lonlats = "|".join(f"{p.lon},{p.lat}" for p in all_points)

        gpx_text = await self._get_text(
            "/brouter",
            params={
                "lonlats": lonlats,
                "profile": profile,
                "alternativeidx": "0",
                "format": "gpx",
            },
        )

        logger.info(
            "brouter_loop_route_calculated",
            start=f"{start.lat},{start.lon}",
            distance_km=distance_km,
            profile=profile,
        )

        return _build_route(gpx_text, source="brouter")

    async def get_elevation_profile(
        self, points: list[GeoPoint]
    ) -> ElevationProfile:
        """Get elevation profile for a list of points by routing through them."""
        if len(points) < 2:
            msg = "Need at least 2 points for elevation profile"
            raise ValueError(msg)

        lonlats = "|".join(f"{p.lon},{p.lat}" for p in points)

        gpx_text = await self._get_text(
            "/brouter",
            params={
                "lonlats": lonlats,
                "profile": "trekking",
                "alternativeidx": "0",
                "format": "gpx",
            },
        )

        route_points = parse_gpx(gpx_text)

        # Build elevation profile with cumulative distance
        profile_points: list[ElevationPoint] = []
        cumulative_km = 0.0
        elevations: list[float] = []

        for i, pt in enumerate(route_points):
            if i > 0:
                cumulative_km += haversine(
                    route_points[i - 1].lat,
                    route_points[i - 1].lon,
                    pt.lat,
                    pt.lon,
                )

            ele = pt.ele if pt.ele is not None else 0.0
            elevations.append(ele)
            profile_points.append(
                ElevationPoint(
                    distance_km=round(cumulative_km, 3),
                    elevation_m=round(ele, 1),
                )
            )

        total_gain = gpx_elevation_gain(route_points)
        total_loss = _elevation_loss(route_points)

        return ElevationProfile(
            points=profile_points,
            total_distance_km=round(cumulative_km, 2),
            total_gain_m=round(total_gain, 1),
            total_loss_m=round(total_loss, 1),
            min_elevation_m=round(min(elevations), 1) if elevations else 0.0,
            max_elevation_m=round(max(elevations), 1) if elevations else 0.0,
        )
