"""Tests for Strava API v3 client."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from mtb_mcp.clients.strava import (
    StravaClient,
    _ms_to_kmh,
    _parse_activity_detail,
    _parse_activity_summary,
    _parse_latlng,
    _parse_ride_totals,
    _parse_segment_effort,
    _parse_segment_info,
)

FIXTURES = Path(__file__).parent.parent / "fixtures" / "api_responses"


def _load_fixture(name: str) -> dict | list:  # type: ignore[type-arg]
    """Load a JSON fixture file."""
    with open(FIXTURES / name) as f:
        return json.load(f)  # type: ignore[no-any-return]


class TestHelpers:
    """Tests for helper functions."""

    def test_parse_latlng_valid(self) -> None:
        pt = _parse_latlng([49.596, 11.004])
        assert pt is not None
        assert pt.lat == 49.596
        assert pt.lon == 11.004

    def test_parse_latlng_none(self) -> None:
        assert _parse_latlng(None) is None

    def test_parse_latlng_empty(self) -> None:
        assert _parse_latlng([]) is None

    def test_parse_latlng_single(self) -> None:
        assert _parse_latlng([49.5]) is None

    def test_ms_to_kmh(self) -> None:
        assert _ms_to_kmh(1.0) == 3.6
        assert _ms_to_kmh(0.0) == 0.0
        assert _ms_to_kmh(10.0) == 36.0


class TestParseActivitySummary:
    """Tests for activity summary parsing."""

    def test_parse_full_activity(self) -> None:
        """Should parse a full Strava activity."""
        fixture = _load_fixture("strava_activities.json")
        activity = _parse_activity_summary(fixture[0])

        assert activity.id == 12345678901
        assert activity.name == "Morning MTB Ride"
        assert activity.sport_type == "MountainBikeRide"
        assert activity.distance_km == 32.5
        assert activity.elevation_gain_m == 450.0
        assert activity.moving_time_seconds == 5400
        assert activity.elapsed_time_seconds == 6000
        assert activity.average_heartrate == 145.0
        assert activity.max_heartrate == 172.0
        assert activity.average_watts == 185.0
        assert activity.max_watts == 420.0
        assert activity.suffer_score == 85.0
        assert activity.calories == 950.0
        assert activity.gear_id == "b12345"
        assert activity.start_latlng is not None
        assert activity.start_latlng.lat == 49.596

    def test_parse_activity_without_optional(self) -> None:
        """Should handle activity without optional fields."""
        fixture = _load_fixture("strava_activities.json")
        activity = _parse_activity_summary(fixture[2])

        assert activity.id == 12345678903
        assert activity.name == "Quick Trail Spin"
        assert activity.average_heartrate is None
        assert activity.average_watts is None
        assert activity.suffer_score is None
        assert activity.calories is None
        assert activity.gear_id is None

    def test_parse_speed_conversion(self) -> None:
        """Should convert m/s to km/h."""
        fixture = _load_fixture("strava_activities.json")
        activity = _parse_activity_summary(fixture[0])

        # 6.02 m/s * 3.6 = 21.672 -> 21.67
        assert activity.average_speed_kmh == 21.67
        # 14.5 m/s * 3.6 = 52.2
        assert activity.max_speed_kmh == 52.2

    def test_parse_distance_conversion(self) -> None:
        """Should convert meters to km."""
        fixture = _load_fixture("strava_activities.json")
        activity = _parse_activity_summary(fixture[0])

        # 32500 / 1000 = 32.5
        assert activity.distance_km == 32.5


class TestParseActivityDetail:
    """Tests for activity detail parsing."""

    def test_parse_full_detail(self) -> None:
        """Should parse activity detail with segment efforts."""
        fixture = _load_fixture("strava_activity_detail.json")
        detail = _parse_activity_detail(fixture)

        assert detail.id == 12345678901
        assert detail.name == "Morning MTB Ride"
        assert detail.description == "Great morning ride through the forest trails."
        assert detail.average_cadence == 78.0
        assert detail.average_temp == 22.0
        assert detail.device_name == "Garmin Edge 540"
        assert len(detail.segment_efforts) == 3

    def test_parse_segment_efforts_from_detail(self) -> None:
        """Should parse segment efforts within activity detail."""
        fixture = _load_fixture("strava_activity_detail.json")
        detail = _parse_activity_detail(fixture)

        effort = detail.segment_efforts[0]
        assert effort.name == "Rathsberg Climb"
        assert effort.distance_m == 1200.0
        assert effort.elapsed_time_seconds == 360
        assert effort.pr_rank == 1

        # Second effort has no PR
        assert detail.segment_efforts[1].pr_rank is None

        # Third effort is 2nd best
        assert detail.segment_efforts[2].pr_rank == 2


class TestParseSegmentInfo:
    """Tests for segment info parsing."""

    def test_parse_segment(self) -> None:
        """Should parse segment from explore response."""
        fixture = _load_fixture("strava_segments_explore.json")
        seg = _parse_segment_info(fixture["segments"][0])

        assert seg.id == 5550001
        assert seg.name == "Rathsberg Climb"
        assert seg.distance_m == 1200.0
        assert seg.average_grade == 6.5
        assert seg.maximum_grade == 12.0
        assert seg.elevation_high == 380.0
        assert seg.elevation_low == 302.0
        assert seg.climb_category == 1
        assert seg.start_latlng is not None
        assert seg.end_latlng is not None

    def test_parse_hc_segment(self) -> None:
        """Should parse HC climb segment."""
        fixture = _load_fixture("strava_segments_explore.json")
        seg = _parse_segment_info(fixture["segments"][2])

        assert seg.name == "Ehrenbürg HC"
        assert seg.climb_category == 5


class TestParseSegmentEffort:
    """Tests for segment effort parsing."""

    def test_parse_effort_with_pr(self) -> None:
        """Should parse segment effort with PR rank."""
        fixture = _load_fixture("strava_segment_efforts.json")
        effort = _parse_segment_effort(fixture[0])

        assert effort.id == 88001
        assert effort.name == "Rathsberg Climb"
        assert effort.distance_m == 1200.0
        assert effort.elapsed_time_seconds == 360
        assert effort.average_heartrate == 165.0
        assert effort.average_watts == 250.0
        assert effort.pr_rank == 1

    def test_parse_effort_ranks(self) -> None:
        """Should parse different PR ranks."""
        fixture = _load_fixture("strava_segment_efforts.json")

        assert _parse_segment_effort(fixture[0]).pr_rank == 1
        assert _parse_segment_effort(fixture[1]).pr_rank == 2
        assert _parse_segment_effort(fixture[2]).pr_rank == 3


class TestParseRideTotals:
    """Tests for ride totals parsing."""

    def test_parse_totals(self) -> None:
        """Should parse ride totals with unit conversion."""
        fixture = _load_fixture("strava_athlete_stats.json")
        totals = _parse_ride_totals(fixture["recent_ride_totals"])

        assert totals.count == 12
        assert totals.distance_km == 485.0
        assert totals.elevation_gain_m == 5200.0
        assert totals.moving_time_seconds == 64800

    def test_parse_empty_totals(self) -> None:
        """Should handle empty totals dict."""
        totals = _parse_ride_totals({})
        assert totals.count == 0
        assert totals.distance_km == 0.0


class TestStravaClientInit:
    """Tests for StravaClient initialization."""

    def test_default_init(self) -> None:
        """Should initialize with default settings."""
        client = StravaClient()
        assert client._base_url == "https://www.strava.com/api/v3"
        assert client._client_id is None
        assert client._access_token is None

    def test_init_with_credentials(self) -> None:
        """Should accept credentials."""
        client = StravaClient(
            client_id="123",
            client_secret="secret",
            access_token="token",
            refresh_token="refresh",
        )
        assert client._client_id == "123"
        assert client._client_secret == "secret"
        assert client._access_token == "token"
        assert client._refresh_token == "refresh"


class TestStravaClientTokenRefresh:
    """Tests for Strava token refresh."""

    @respx.mock
    async def test_token_refresh(self) -> None:
        """Should refresh token when expired."""
        token_fixture = _load_fixture("strava_token_refresh.json")
        respx.post("https://www.strava.com/oauth/token").mock(
            return_value=httpx.Response(200, json=token_fixture)
        )

        # Also mock the activities endpoint
        activities_fixture = _load_fixture("strava_activities.json")
        respx.get("https://www.strava.com/api/v3/athlete/activities").mock(
            return_value=httpx.Response(200, json=activities_fixture)
        )

        async with StravaClient(
            client_id="test_id",
            client_secret="test_secret",
            access_token="expired_token",
            refresh_token="my_refresh_token",
        ) as client:
            client._token_expires_at = 0  # Force token as expired
            activities = await client.get_recent_activities(
                limit=3, sport_type=None
            )

        assert len(activities) == 3
        assert client._access_token == "new_access_token_abc123"
        assert client._refresh_token == "new_refresh_token_xyz789"
        assert client._athlete_id == 42424242

    @respx.mock
    async def test_skip_refresh_when_valid(self) -> None:
        """Should not refresh when token is still valid."""
        activities_fixture = _load_fixture("strava_activities.json")
        respx.get("https://www.strava.com/api/v3/athlete/activities").mock(
            return_value=httpx.Response(200, json=activities_fixture)
        )

        async with StravaClient(
            access_token="valid_token",
        ) as client:
            client._token_expires_at = 9999999999  # Far in the future
            activities = await client.get_recent_activities(
                limit=3, sport_type=None
            )

        assert len(activities) == 3

    async def test_raises_without_credentials(self) -> None:
        """Should raise ValueError when no credentials for refresh."""
        async with StravaClient(
            client_id="test_id",
            # Missing client_secret and refresh_token
        ) as client:
            client._token_expires_at = 0
            with pytest.raises(ValueError, match="credentials incomplete"):
                await client._ensure_token()


class TestStravaClientActivities:
    """Tests for Strava activities retrieval."""

    @respx.mock
    async def test_get_recent_activities(self) -> None:
        """Should fetch and parse recent activities."""
        fixture = _load_fixture("strava_activities.json")
        respx.get("https://www.strava.com/api/v3/athlete/activities").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with StravaClient(access_token="test_token") as client:
            client._token_expires_at = 9999999999
            activities = await client.get_recent_activities(
                limit=10, sport_type=None
            )

        assert len(activities) == 3
        assert activities[0].name == "Morning MTB Ride"
        assert activities[1].name == "Evening Gravel Ride"

    @respx.mock
    async def test_filter_by_sport_type(self) -> None:
        """Should filter by sport type."""
        fixture = _load_fixture("strava_activities.json")
        respx.get("https://www.strava.com/api/v3/athlete/activities").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with StravaClient(access_token="test_token") as client:
            client._token_expires_at = 9999999999
            activities = await client.get_recent_activities(
                limit=10, sport_type="MountainBikeRide"
            )

        assert len(activities) == 2
        assert all(a.sport_type == "MountainBikeRide" for a in activities)


class TestStravaClientActivityDetail:
    """Tests for activity detail retrieval."""

    @respx.mock
    async def test_get_activity_details(self) -> None:
        """Should fetch and parse activity detail."""
        fixture = _load_fixture("strava_activity_detail.json")
        respx.get("https://www.strava.com/api/v3/activities/12345678901").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with StravaClient(access_token="test_token") as client:
            client._token_expires_at = 9999999999
            detail = await client.get_activity_details(12345678901)

        assert detail.name == "Morning MTB Ride"
        assert detail.description == "Great morning ride through the forest trails."
        assert len(detail.segment_efforts) == 3
        assert detail.segment_efforts[0].pr_rank == 1

    @respx.mock
    async def test_activity_detail_http_error(self) -> None:
        """Should propagate HTTP errors."""
        respx.get("https://www.strava.com/api/v3/activities/99999").mock(
            return_value=httpx.Response(404, json={"message": "Not Found"})
        )

        async with StravaClient(access_token="test_token") as client:
            client._token_expires_at = 9999999999
            with pytest.raises(httpx.HTTPStatusError):
                await client.get_activity_details(99999)


class TestStravaClientAthleteStats:
    """Tests for athlete stats retrieval."""

    @respx.mock
    async def test_get_athlete_stats(self) -> None:
        """Should fetch athlete stats."""
        athlete_fixture = _load_fixture("strava_athlete.json")
        stats_fixture = _load_fixture("strava_athlete_stats.json")

        respx.get("https://www.strava.com/api/v3/athlete").mock(
            return_value=httpx.Response(200, json=athlete_fixture)
        )
        respx.get("https://www.strava.com/api/v3/athletes/42424242/stats").mock(
            return_value=httpx.Response(200, json=stats_fixture)
        )

        async with StravaClient(access_token="test_token") as client:
            client._token_expires_at = 9999999999
            stats = await client.get_athlete_stats()

        assert stats.recent_ride_totals.count == 12
        assert stats.recent_ride_totals.distance_km == 485.0
        assert stats.ytd_ride_totals.count == 85
        assert stats.all_ride_totals.count == 520

    @respx.mock
    async def test_get_athlete_stats_with_cached_id(self) -> None:
        """Should skip athlete lookup when ID is cached."""
        stats_fixture = _load_fixture("strava_athlete_stats.json")

        respx.get("https://www.strava.com/api/v3/athletes/42424242/stats").mock(
            return_value=httpx.Response(200, json=stats_fixture)
        )

        async with StravaClient(access_token="test_token") as client:
            client._token_expires_at = 9999999999
            client._athlete_id = 42424242
            stats = await client.get_athlete_stats()

        assert stats.recent_ride_totals.count == 12


class TestStravaClientSegments:
    """Tests for segment exploration."""

    @respx.mock
    async def test_explore_segments(self) -> None:
        """Should explore and parse segments."""
        fixture = _load_fixture("strava_segments_explore.json")
        respx.get("https://www.strava.com/api/v3/segments/explore").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with StravaClient(access_token="test_token") as client:
            client._token_expires_at = 9999999999
            segments = await client.explore_segments(49.59, 11.00, radius_km=10.0)

        assert len(segments) == 3
        assert segments[0].name == "Rathsberg Climb"
        assert segments[0].climb_category == 1
        assert segments[2].climb_category == 5

    @respx.mock
    async def test_get_segment_efforts(self) -> None:
        """Should fetch segment efforts."""
        fixture = _load_fixture("strava_segment_efforts.json")
        respx.get("https://www.strava.com/api/v3/segment_efforts").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with StravaClient(access_token="test_token") as client:
            client._token_expires_at = 9999999999
            efforts = await client.get_segment_efforts(5550001, limit=10)

        assert len(efforts) == 3
        assert efforts[0].pr_rank == 1
        assert efforts[1].pr_rank == 2
        assert efforts[2].pr_rank == 3


class TestStravaClientGPXExport:
    """Tests for GPX export."""

    @respx.mock
    async def test_export_gpx(self) -> None:
        """Should build GPX from activity streams."""
        streams_fixture = _load_fixture("strava_streams.json")
        detail_fixture = _load_fixture("strava_activity_detail.json")

        respx.get("https://www.strava.com/api/v3/activities/12345678901/streams").mock(
            return_value=httpx.Response(200, json=streams_fixture)
        )
        respx.get("https://www.strava.com/api/v3/activities/12345678901").mock(
            return_value=httpx.Response(200, json=detail_fixture)
        )

        async with StravaClient(access_token="test_token") as client:
            client._token_expires_at = 9999999999
            gpx_xml = await client.export_gpx(12345678901)

        assert "<?xml" in gpx_xml
        assert "<gpx" in gpx_xml
        assert "Morning MTB Ride" in gpx_xml
        assert "49.596" in gpx_xml
        assert "11.004" in gpx_xml
        # Should have elevation data
        assert "280" in gpx_xml

    @respx.mock
    async def test_export_gpx_no_data(self) -> None:
        """Should raise ValueError when no GPS data."""
        empty_streams: list[dict[str, object]] = [
            {"type": "time", "data": [0, 60, 120]},
        ]
        respx.get("https://www.strava.com/api/v3/activities/99999/streams").mock(
            return_value=httpx.Response(200, json=empty_streams)
        )

        async with StravaClient(access_token="test_token") as client:
            client._token_expires_at = 9999999999
            with pytest.raises(ValueError, match="No GPS data"):
                await client.export_gpx(99999)


class TestStravaClientWeeklySummary:
    """Tests for weekly summary."""

    @respx.mock
    async def test_weekly_summary(self) -> None:
        """Should aggregate activities into weekly summary."""
        fixture = _load_fixture("strava_activities.json")
        respx.get("https://www.strava.com/api/v3/athlete/activities").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with StravaClient(access_token="test_token") as client:
            client._token_expires_at = 9999999999
            # Use a large week range to include all fixtures
            summary = await client.get_weekly_summary(weeks=52)

        assert summary["total_rides"] > 0
        assert summary["total_distance_km"] > 0
        assert "sport_type_counts" in summary
        assert "activities" in summary
