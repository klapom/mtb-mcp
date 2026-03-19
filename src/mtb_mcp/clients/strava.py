"""Strava API v3 client."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
import structlog

from mtb_mcp.clients.base import BaseClient
from mtb_mcp.models.activity import (
    ActivityDetail,
    ActivitySummary,
    AthleteStats,
    RideTotals,
    SegmentEffort,
    SegmentInfo,
)
from mtb_mcp.models.common import GeoPoint
from mtb_mcp.utils.gpx import write_gpx

logger = structlog.get_logger(__name__)


def _parse_latlng(raw: list[float] | None) -> GeoPoint | None:
    """Parse a [lat, lng] array into a GeoPoint."""
    if raw and len(raw) == 2:
        return GeoPoint(lat=raw[0], lon=raw[1])
    return None


def _ms_to_kmh(meters_per_second: float) -> float:
    """Convert m/s to km/h."""
    return round(meters_per_second * 3.6, 2)


def _parse_activity_summary(data: dict[str, Any]) -> ActivitySummary:
    """Parse a Strava activity JSON object into an ActivitySummary."""
    return ActivitySummary(
        id=data["id"],
        name=data.get("name", "Untitled"),
        sport_type=data.get("sport_type", data.get("type", "Ride")),
        distance_km=round(data.get("distance", 0.0) / 1000.0, 2),
        elevation_gain_m=data.get("total_elevation_gain", 0.0),
        moving_time_seconds=data.get("moving_time", 0),
        elapsed_time_seconds=data.get("elapsed_time", 0),
        start_date=datetime.fromisoformat(
            data.get("start_date", "2000-01-01T00:00:00Z").replace("Z", "+00:00")
        ),
        average_speed_kmh=_ms_to_kmh(data.get("average_speed", 0.0)),
        max_speed_kmh=_ms_to_kmh(data.get("max_speed", 0.0)),
        average_heartrate=data.get("average_heartrate"),
        max_heartrate=data.get("max_heartrate"),
        average_watts=data.get("average_watts"),
        max_watts=data.get("max_watts"),
        suffer_score=data.get("suffer_score"),
        calories=data.get("calories"),
        gear_id=data.get("gear_id"),
        start_latlng=_parse_latlng(data.get("start_latlng")),
    )


def _parse_segment_effort(data: dict[str, Any]) -> SegmentEffort:
    """Parse a Strava segment effort JSON object."""
    return SegmentEffort(
        id=data["id"],
        name=data.get("name", "Unknown Segment"),
        distance_m=data.get("distance", 0.0),
        elapsed_time_seconds=data.get("elapsed_time", 0),
        moving_time_seconds=data.get("moving_time", 0),
        average_heartrate=data.get("average_heartrate"),
        average_watts=data.get("average_watts"),
        pr_rank=data.get("pr_rank"),
    )


def _parse_activity_detail(data: dict[str, Any]) -> ActivityDetail:
    """Parse a Strava activity detail JSON object."""
    efforts_raw = data.get("segment_efforts", [])
    efforts = [_parse_segment_effort(e) for e in efforts_raw if isinstance(e, dict)]

    return ActivityDetail(
        id=data["id"],
        name=data.get("name", "Untitled"),
        sport_type=data.get("sport_type", data.get("type", "Ride")),
        distance_km=round(data.get("distance", 0.0) / 1000.0, 2),
        elevation_gain_m=data.get("total_elevation_gain", 0.0),
        moving_time_seconds=data.get("moving_time", 0),
        elapsed_time_seconds=data.get("elapsed_time", 0),
        start_date=datetime.fromisoformat(
            data.get("start_date", "2000-01-01T00:00:00Z").replace("Z", "+00:00")
        ),
        average_speed_kmh=_ms_to_kmh(data.get("average_speed", 0.0)),
        max_speed_kmh=_ms_to_kmh(data.get("max_speed", 0.0)),
        average_heartrate=data.get("average_heartrate"),
        max_heartrate=data.get("max_heartrate"),
        average_watts=data.get("average_watts"),
        max_watts=data.get("max_watts"),
        suffer_score=data.get("suffer_score"),
        calories=data.get("calories"),
        gear_id=data.get("gear_id"),
        start_latlng=_parse_latlng(data.get("start_latlng")),
        description=data.get("description"),
        average_cadence=data.get("average_cadence"),
        average_temp=data.get("average_temp"),
        device_name=data.get("device_name"),
        segment_efforts=efforts,
    )


def _parse_segment_info(data: dict[str, Any]) -> SegmentInfo:
    """Parse a Strava segment JSON object."""
    return SegmentInfo(
        id=data["id"],
        name=data.get("name", "Unknown Segment"),
        distance_m=data.get("distance", 0.0),
        average_grade=data.get("average_grade", 0.0),
        maximum_grade=data.get("maximum_grade", 0.0),
        elevation_high=data.get("elevation_high", 0.0),
        elevation_low=data.get("elevation_low", 0.0),
        climb_category=data.get("climb_category", 0),
        start_latlng=_parse_latlng(data.get("start_latlng")),
        end_latlng=_parse_latlng(data.get("end_latlng")),
    )


def _parse_ride_totals(data: dict[str, Any]) -> RideTotals:
    """Parse a Strava ride totals JSON object."""
    return RideTotals(
        count=data.get("count", 0),
        distance_km=round(data.get("distance", 0.0) / 1000.0, 2),
        elevation_gain_m=data.get("elevation_gain", 0.0),
        moving_time_seconds=data.get("moving_time", 0),
    )


class StravaClient(BaseClient):
    """Client for Strava API v3.

    Handles OAuth2 token refresh automatically.
    Rate limits: 200 req/15min, 2000 req/day.
    """

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        access_token: str | None = None,
        refresh_token: str | None = None,
    ) -> None:
        super().__init__(
            base_url="https://www.strava.com/api/v3",
            rate_limit=10.0,  # Stay well under 200/15min
        )
        self._client_id = client_id
        self._client_secret = client_secret
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._token_expires_at: int = 0
        self._athlete_id: int | None = None

    async def _ensure_token(self) -> None:
        """Refresh access token if expired."""
        if self._access_token and self._token_expires_at > int(time.time()) + 60:
            return

        if not self._client_id or not self._client_secret or not self._refresh_token:
            if self._access_token:
                return
            msg = "Strava credentials incomplete: need client_id, client_secret, and refresh_token"
            raise ValueError(msg)

        logger.info("strava_token_refresh")

        # Token refresh goes to a different host, use raw httpx
        async with httpx.AsyncClient() as refresh_client:
            response = await refresh_client.post(
                "https://www.strava.com/oauth/token",
                data={
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "refresh_token": self._refresh_token,
                    "grant_type": "refresh_token",
                },
            )
            response.raise_for_status()
            token_data = response.json()

        self._access_token = token_data["access_token"]
        self._refresh_token = token_data.get("refresh_token", self._refresh_token)
        self._token_expires_at = token_data.get("expires_at", 0)
        self._athlete_id = token_data.get("athlete", {}).get("id")

        logger.info("strava_token_refreshed", expires_at=self._token_expires_at)

    async def _authed_get(
        self, path: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """GET with Authorization header, refreshing token if needed."""
        await self._ensure_token()
        await self._rate_limiter.acquire()
        client = self._get_client()

        response = await client.get(
            path,
            params=params,
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        result: dict[str, Any] = response.json()
        return result

    async def _authed_get_list(
        self, path: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """GET that returns a JSON array with Authorization header."""
        await self._ensure_token()
        await self._rate_limiter.acquire()
        client = self._get_client()

        response = await client.get(
            path,
            params=params,
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        result: list[dict[str, Any]] = response.json()
        return result

    async def get_recent_activities(
        self, limit: int = 20, sport_type: str | None = "MountainBikeRide"
    ) -> list[ActivitySummary]:
        """Get recent activities, optionally filtered by sport type."""
        data = await self._authed_get_list(
            "/athlete/activities",
            params={"per_page": str(limit), "page": "1"},
        )

        activities = [_parse_activity_summary(a) for a in data if isinstance(a, dict)]

        if sport_type:
            activities = [a for a in activities if a.sport_type == sport_type]

        return activities

    async def get_activity_details(self, activity_id: int) -> ActivityDetail:
        """Get detailed activity with segment efforts."""
        data = await self._authed_get(
            f"/activities/{activity_id}",
            params={"include_all_efforts": "true"},
        )
        return _parse_activity_detail(data)

    async def get_athlete_stats(self) -> AthleteStats:
        """Get athlete's aggregate statistics."""
        # Get athlete ID if not known
        if self._athlete_id is None:
            athlete_data = await self._authed_get("/athlete")
            self._athlete_id = athlete_data["id"]

        data = await self._authed_get(f"/athletes/{self._athlete_id}/stats")

        return AthleteStats(
            recent_ride_totals=_parse_ride_totals(data.get("recent_ride_totals", {})),
            ytd_ride_totals=_parse_ride_totals(data.get("ytd_ride_totals", {})),
            all_ride_totals=_parse_ride_totals(data.get("all_ride_totals", {})),
        )

    async def explore_segments(
        self, lat: float, lon: float, radius_km: float = 10.0
    ) -> list[SegmentInfo]:
        """Discover segments near a location.

        Uses the Strava segments/explore endpoint with a bounding box.
        """
        # Convert radius to a bounding box
        delta_lat = radius_km / 111.0  # ~111 km per degree latitude
        delta_lon = radius_km / 85.0  # ~85 km per degree longitude at ~49N

        bounds = f"{lat - delta_lat},{lon - delta_lon},{lat + delta_lat},{lon + delta_lon}"

        data = await self._authed_get(
            "/segments/explore",
            params={"bounds": bounds, "activity_type": "riding"},
        )

        segments_raw = data.get("segments", [])
        return [_parse_segment_info(s) for s in segments_raw if isinstance(s, dict)]

    async def get_segment_efforts(
        self, segment_id: int, limit: int = 10
    ) -> list[SegmentEffort]:
        """Get personal efforts on a segment."""
        data = await self._authed_get_list(
            "/segment_efforts",
            params={"segment_id": str(segment_id), "per_page": str(limit)},
        )

        return [_parse_segment_effort(e) for e in data if isinstance(e, dict)]

    async def export_gpx(self, activity_id: int) -> str:
        """Export activity route as GPX.

        Strava doesn't directly export GPX; we get streams and build GPX
        using the write_gpx utility.
        """
        await self._ensure_token()
        await self._rate_limiter.acquire()
        client = self._get_client()

        response = await client.get(
            f"/activities/{activity_id}/streams",
            params={"keys": "latlng,altitude,time", "key_type": "distance"},
            headers={"Authorization": f"Bearer {self._access_token}"},
        )
        response.raise_for_status()
        streams: list[dict[str, Any]] = response.json()

        # Extract data from streams
        latlng_data: list[list[float]] = []
        altitude_data: list[float] = []

        for stream in streams:
            if stream.get("type") == "latlng":
                latlng_data = stream.get("data", [])
            elif stream.get("type") == "altitude":
                altitude_data = stream.get("data", [])

        if not latlng_data:
            msg = f"No GPS data available for activity {activity_id}"
            raise ValueError(msg)

        # Build GeoPoints
        points: list[GeoPoint] = []
        for i, coord in enumerate(latlng_data):
            ele = altitude_data[i] if i < len(altitude_data) else None
            points.append(GeoPoint(lat=coord[0], lon=coord[1], ele=ele))

        # Get activity name for GPX track name
        detail = await self.get_activity_details(activity_id)
        return write_gpx(points, name=detail.name)

    async def get_weekly_summary(self, weeks: int = 1) -> dict[str, Any]:
        """Get aggregated weekly summary.

        Fetches recent activities and aggregates by week.
        """
        now = datetime.now(tz=timezone.utc)
        cutoff = now - timedelta(weeks=weeks)

        # Fetch enough activities to cover the period
        all_activities = await self.get_recent_activities(
            limit=50, sport_type=None
        )

        # Filter to the time window and cycling types
        cycling_types = {
            "MountainBikeRide", "Ride", "GravelRide", "EBikeRide", "EMountainBikeRide"
        }
        recent = [
            a for a in all_activities
            if a.start_date >= cutoff and a.sport_type in cycling_types
        ]

        total_distance_km = sum(a.distance_km for a in recent)
        total_elevation_m = sum(a.elevation_gain_m for a in recent)
        total_moving_time_s = sum(a.moving_time_seconds for a in recent)
        total_rides = len(recent)

        avg_speed = 0.0
        if total_moving_time_s > 0:
            avg_speed = round(total_distance_km / (total_moving_time_s / 3600), 2)

        # Count by sport type
        sport_counts: dict[str, int] = {}
        for a in recent:
            sport_counts[a.sport_type] = sport_counts.get(a.sport_type, 0) + 1

        return {
            "weeks": weeks,
            "from": cutoff.isoformat(),
            "to": now.isoformat(),
            "total_rides": total_rides,
            "total_distance_km": round(total_distance_km, 2),
            "total_elevation_m": round(total_elevation_m, 1),
            "total_moving_time_seconds": total_moving_time_s,
            "average_speed_kmh": avg_speed,
            "sport_type_counts": sport_counts,
            "activities": [
                {"name": a.name, "sport_type": a.sport_type, "distance_km": a.distance_km}
                for a in recent
            ],
        }
