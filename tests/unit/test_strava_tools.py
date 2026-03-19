"""Tests for Strava MCP tools."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from mtb_mcp.models.activity import (
    ActivityDetail,
    ActivitySummary,
    AthleteStats,
    RideTotals,
    SegmentEffort,
    SegmentInfo,
)
from mtb_mcp.models.common import GeoPoint
from mtb_mcp.tools.strava_tools import (
    strava_activity_details,
    strava_athlete_stats,
    strava_explore_segments,
    strava_export_gpx,
    strava_recent_activities,
    strava_segment_efforts,
    strava_weekly_summary,
)


def _make_activity_summary() -> ActivitySummary:
    """Create a test ActivitySummary."""
    return ActivitySummary(
        id=12345678901,
        name="Morning MTB Ride",
        sport_type="MountainBikeRide",
        distance_km=32.5,
        elevation_gain_m=450.0,
        moving_time_seconds=5400,
        elapsed_time_seconds=6000,
        start_date=datetime(2025, 7, 15, 7, 0, tzinfo=timezone.utc),
        average_speed_kmh=21.67,
        max_speed_kmh=52.2,
        average_heartrate=145.0,
        max_heartrate=172.0,
        average_watts=185.0,
        calories=950.0,
        gear_id="b12345",
        start_latlng=GeoPoint(lat=49.596, lon=11.004),
    )


def _make_activity_detail() -> ActivityDetail:
    """Create a test ActivityDetail."""
    return ActivityDetail(
        id=12345678901,
        name="Morning MTB Ride",
        sport_type="MountainBikeRide",
        distance_km=32.5,
        elevation_gain_m=450.0,
        moving_time_seconds=5400,
        elapsed_time_seconds=6000,
        start_date=datetime(2025, 7, 15, 7, 0, tzinfo=timezone.utc),
        average_speed_kmh=21.67,
        max_speed_kmh=52.2,
        average_heartrate=145.0,
        max_heartrate=172.0,
        average_watts=185.0,
        max_watts=420.0,
        calories=950.0,
        suffer_score=85.0,
        description="Great ride!",
        average_cadence=78.0,
        average_temp=22.0,
        device_name="Garmin Edge 540",
        segment_efforts=[
            SegmentEffort(
                id=987,
                name="Rathsberg Climb",
                distance_m=1200.0,
                elapsed_time_seconds=360,
                moving_time_seconds=350,
                average_heartrate=165.0,
                average_watts=250.0,
                pr_rank=1,
            ),
            SegmentEffort(
                id=988,
                name="Valley Sprint",
                distance_m=800.0,
                elapsed_time_seconds=90,
                moving_time_seconds=88,
                pr_rank=None,
            ),
        ],
    )


def _make_athlete_stats() -> AthleteStats:
    """Create test AthleteStats."""
    return AthleteStats(
        recent_ride_totals=RideTotals(
            count=12, distance_km=485.0, elevation_gain_m=5200.0, moving_time_seconds=64800
        ),
        ytd_ride_totals=RideTotals(
            count=85, distance_km=3250.0, elevation_gain_m=38500.0, moving_time_seconds=432000
        ),
        all_ride_totals=RideTotals(
            count=520, distance_km=18500.0, elevation_gain_m=225000.0, moving_time_seconds=2592000
        ),
    )


class TestStravaRecentActivities:
    """Tests for strava_recent_activities tool."""

    @patch("mtb_mcp.tools.strava_tools.get_settings")
    async def test_missing_credentials(self, mock_settings: AsyncMock) -> None:
        """Should return error message without credentials."""
        settings = mock_settings.return_value
        settings.strava_access_token = None
        settings.strava_refresh_token = None

        result = await strava_recent_activities()

        assert "not configured" in result
        assert "MTB_MCP_STRAVA" in result

    @patch("mtb_mcp.tools.strava_tools.StravaClient")
    @patch("mtb_mcp.tools.strava_tools.get_settings")
    async def test_returns_formatted_activities(
        self, mock_settings: AsyncMock, mock_client_cls: AsyncMock
    ) -> None:
        """Should return formatted activity list."""
        settings = mock_settings.return_value
        settings.strava_access_token = "test_token"
        settings.strava_refresh_token = "test_refresh"
        settings.strava_client_id = "id"
        settings.strava_client_secret = "secret"

        mock_client = AsyncMock()
        mock_client.get_recent_activities.return_value = [_make_activity_summary()]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await strava_recent_activities(limit=10)

        assert "Morning MTB Ride" in result
        assert "32.5 km" in result
        assert "450" in result
        assert "145" in result
        assert "12345678901" in result

    @patch("mtb_mcp.tools.strava_tools.StravaClient")
    @patch("mtb_mcp.tools.strava_tools.get_settings")
    async def test_no_activities(
        self, mock_settings: AsyncMock, mock_client_cls: AsyncMock
    ) -> None:
        """Should show message when no activities found."""
        settings = mock_settings.return_value
        settings.strava_access_token = "test_token"
        settings.strava_refresh_token = "test_refresh"
        settings.strava_client_id = "id"
        settings.strava_client_secret = "secret"

        mock_client = AsyncMock()
        mock_client.get_recent_activities.return_value = []
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await strava_recent_activities()

        assert "No recent activities" in result

    @patch("mtb_mcp.tools.strava_tools.StravaClient")
    @patch("mtb_mcp.tools.strava_tools.get_settings")
    async def test_handles_api_error(
        self, mock_settings: AsyncMock, mock_client_cls: AsyncMock
    ) -> None:
        """Should handle API errors gracefully."""
        settings = mock_settings.return_value
        settings.strava_access_token = "test_token"
        settings.strava_refresh_token = "test_refresh"
        settings.strava_client_id = "id"
        settings.strava_client_secret = "secret"

        mock_client = AsyncMock()
        mock_client.get_recent_activities.side_effect = Exception("Rate limited")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await strava_recent_activities()

        assert "Error" in result
        assert "Rate limited" in result


class TestStravaActivityDetails:
    """Tests for strava_activity_details tool."""

    @patch("mtb_mcp.tools.strava_tools.get_settings")
    async def test_missing_credentials(self, mock_settings: AsyncMock) -> None:
        """Should return error message without credentials."""
        settings = mock_settings.return_value
        settings.strava_access_token = None
        settings.strava_refresh_token = None

        result = await strava_activity_details(activity_id=123)

        assert "not configured" in result

    @patch("mtb_mcp.tools.strava_tools.StravaClient")
    @patch("mtb_mcp.tools.strava_tools.get_settings")
    async def test_returns_formatted_detail(
        self, mock_settings: AsyncMock, mock_client_cls: AsyncMock
    ) -> None:
        """Should return formatted activity detail with segments."""
        settings = mock_settings.return_value
        settings.strava_access_token = "test_token"
        settings.strava_refresh_token = "test_refresh"
        settings.strava_client_id = "id"
        settings.strava_client_secret = "secret"

        mock_client = AsyncMock()
        mock_client.get_activity_details.return_value = _make_activity_detail()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await strava_activity_details(activity_id=12345678901)

        assert "Morning MTB Ride" in result
        assert "MountainBikeRide" in result
        assert "32.5 km" in result
        assert "Rathsberg Climb" in result
        assert "[PR!]" in result
        assert "Garmin Edge 540" in result
        assert "Great ride!" in result
        assert "Segment Efforts (2)" in result


class TestStravaAthleteStats:
    """Tests for strava_athlete_stats tool."""

    @patch("mtb_mcp.tools.strava_tools.get_settings")
    async def test_missing_credentials(self, mock_settings: AsyncMock) -> None:
        """Should return error message without credentials."""
        settings = mock_settings.return_value
        settings.strava_access_token = None
        settings.strava_refresh_token = None

        result = await strava_athlete_stats()

        assert "not configured" in result

    @patch("mtb_mcp.tools.strava_tools.StravaClient")
    @patch("mtb_mcp.tools.strava_tools.get_settings")
    async def test_returns_formatted_stats(
        self, mock_settings: AsyncMock, mock_client_cls: AsyncMock
    ) -> None:
        """Should return formatted athlete stats."""
        settings = mock_settings.return_value
        settings.strava_access_token = "test_token"
        settings.strava_refresh_token = "test_refresh"
        settings.strava_client_id = "id"
        settings.strava_client_secret = "secret"

        mock_client = AsyncMock()
        mock_client.get_athlete_stats.return_value = _make_athlete_stats()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await strava_athlete_stats()

        assert "Strava Athlete Statistics" in result
        assert "Recent" in result
        assert "Year-to-Date" in result
        assert "All-Time" in result
        assert "12" in result  # recent count
        assert "485.0 km" in result
        assert "520" in result  # all-time count


class TestStravaExploreSegments:
    """Tests for strava_explore_segments tool."""

    @patch("mtb_mcp.tools.strava_tools.get_settings")
    async def test_missing_credentials(self, mock_settings: AsyncMock) -> None:
        """Should return error message without credentials."""
        settings = mock_settings.return_value
        settings.strava_access_token = None
        settings.strava_refresh_token = None

        result = await strava_explore_segments(lat=49.59, lon=11.00)

        assert "not configured" in result

    @patch("mtb_mcp.tools.strava_tools.StravaClient")
    @patch("mtb_mcp.tools.strava_tools.get_settings")
    async def test_returns_formatted_segments(
        self, mock_settings: AsyncMock, mock_client_cls: AsyncMock
    ) -> None:
        """Should return formatted segment list."""
        settings = mock_settings.return_value
        settings.strava_access_token = "test_token"
        settings.strava_refresh_token = "test_refresh"
        settings.strava_client_id = "id"
        settings.strava_client_secret = "secret"
        settings.home_lat = 49.59
        settings.home_lon = 11.00

        mock_client = AsyncMock()
        mock_client.explore_segments.return_value = [
            SegmentInfo(
                id=5550001,
                name="Rathsberg Climb",
                distance_m=1200.0,
                average_grade=6.5,
                maximum_grade=12.0,
                elevation_high=380.0,
                elevation_low=302.0,
                climb_category=1,
            ),
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await strava_explore_segments(lat=49.59, lon=11.00)

        assert "Rathsberg Climb" in result
        assert "Cat 4" in result
        assert "6.5%" in result
        assert "5550001" in result

    @patch("mtb_mcp.tools.strava_tools.StravaClient")
    @patch("mtb_mcp.tools.strava_tools.get_settings")
    async def test_uses_home_location(
        self, mock_settings: AsyncMock, mock_client_cls: AsyncMock
    ) -> None:
        """Should use home location when no lat/lon provided."""
        settings = mock_settings.return_value
        settings.strava_access_token = "test_token"
        settings.strava_refresh_token = "test_refresh"
        settings.strava_client_id = "id"
        settings.strava_client_secret = "secret"
        settings.home_lat = 49.59
        settings.home_lon = 11.00

        mock_client = AsyncMock()
        mock_client.explore_segments.return_value = []
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await strava_explore_segments()

        assert "49.59" in result
        assert "11.00" in result
        mock_client.explore_segments.assert_called_once_with(49.59, 11.00, 10.0)

    @patch("mtb_mcp.tools.strava_tools.StravaClient")
    @patch("mtb_mcp.tools.strava_tools.get_settings")
    async def test_no_segments_found(
        self, mock_settings: AsyncMock, mock_client_cls: AsyncMock
    ) -> None:
        """Should show message when no segments found."""
        settings = mock_settings.return_value
        settings.strava_access_token = "test_token"
        settings.strava_refresh_token = "test_refresh"
        settings.strava_client_id = "id"
        settings.strava_client_secret = "secret"
        settings.home_lat = 49.59
        settings.home_lon = 11.00

        mock_client = AsyncMock()
        mock_client.explore_segments.return_value = []
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await strava_explore_segments(lat=49.59, lon=11.00)

        assert "No segments found" in result


class TestStravaSegmentEfforts:
    """Tests for strava_segment_efforts tool."""

    @patch("mtb_mcp.tools.strava_tools.get_settings")
    async def test_missing_credentials(self, mock_settings: AsyncMock) -> None:
        """Should return error message without credentials."""
        settings = mock_settings.return_value
        settings.strava_access_token = None
        settings.strava_refresh_token = None

        result = await strava_segment_efforts(segment_id=123)

        assert "not configured" in result

    @patch("mtb_mcp.tools.strava_tools.StravaClient")
    @patch("mtb_mcp.tools.strava_tools.get_settings")
    async def test_returns_formatted_efforts(
        self, mock_settings: AsyncMock, mock_client_cls: AsyncMock
    ) -> None:
        """Should return formatted segment efforts with PR tags."""
        settings = mock_settings.return_value
        settings.strava_access_token = "test_token"
        settings.strava_refresh_token = "test_refresh"
        settings.strava_client_id = "id"
        settings.strava_client_secret = "secret"

        mock_client = AsyncMock()
        mock_client.get_segment_efforts.return_value = [
            SegmentEffort(
                id=88001,
                name="Rathsberg Climb",
                distance_m=1200.0,
                elapsed_time_seconds=360,
                moving_time_seconds=350,
                average_heartrate=165.0,
                average_watts=250.0,
                pr_rank=1,
            ),
            SegmentEffort(
                id=88002,
                name="Rathsberg Climb",
                distance_m=1200.0,
                elapsed_time_seconds=375,
                moving_time_seconds=370,
                pr_rank=2,
            ),
        ]
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await strava_segment_efforts(segment_id=5550001)

        assert "Rathsberg Climb" in result
        assert "[PR!]" in result
        assert "[2nd best]" in result
        assert "HR 165" in result
        assert "250W" in result

    @patch("mtb_mcp.tools.strava_tools.StravaClient")
    @patch("mtb_mcp.tools.strava_tools.get_settings")
    async def test_no_efforts_found(
        self, mock_settings: AsyncMock, mock_client_cls: AsyncMock
    ) -> None:
        """Should show message when no efforts found."""
        settings = mock_settings.return_value
        settings.strava_access_token = "test_token"
        settings.strava_refresh_token = "test_refresh"
        settings.strava_client_id = "id"
        settings.strava_client_secret = "secret"

        mock_client = AsyncMock()
        mock_client.get_segment_efforts.return_value = []
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await strava_segment_efforts(segment_id=99999)

        assert "No personal efforts" in result


class TestStravaExportGPX:
    """Tests for strava_export_gpx tool."""

    @patch("mtb_mcp.tools.strava_tools.get_settings")
    async def test_missing_credentials(self, mock_settings: AsyncMock) -> None:
        """Should return error message without credentials."""
        settings = mock_settings.return_value
        settings.strava_access_token = None
        settings.strava_refresh_token = None

        result = await strava_export_gpx(activity_id=123)

        assert "not configured" in result

    @patch("mtb_mcp.tools.strava_tools.StravaClient")
    @patch("mtb_mcp.tools.strava_tools.get_settings")
    async def test_handles_no_gps_data(
        self, mock_settings: AsyncMock, mock_client_cls: AsyncMock
    ) -> None:
        """Should handle ValueError for missing GPS data."""
        settings = mock_settings.return_value
        settings.strava_access_token = "test_token"
        settings.strava_refresh_token = "test_refresh"
        settings.strava_client_id = "id"
        settings.strava_client_secret = "secret"

        mock_client = AsyncMock()
        mock_client.export_gpx.side_effect = ValueError("No GPS data available")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await strava_export_gpx(activity_id=99999)

        assert "Cannot export GPX" in result
        assert "No GPS data" in result


class TestStravaWeeklySummary:
    """Tests for strava_weekly_summary tool."""

    @patch("mtb_mcp.tools.strava_tools.get_settings")
    async def test_missing_credentials(self, mock_settings: AsyncMock) -> None:
        """Should return error message without credentials."""
        settings = mock_settings.return_value
        settings.strava_access_token = None
        settings.strava_refresh_token = None

        result = await strava_weekly_summary()

        assert "not configured" in result

    @patch("mtb_mcp.tools.strava_tools.StravaClient")
    @patch("mtb_mcp.tools.strava_tools.get_settings")
    async def test_returns_formatted_summary(
        self, mock_settings: AsyncMock, mock_client_cls: AsyncMock
    ) -> None:
        """Should return formatted weekly summary."""
        settings = mock_settings.return_value
        settings.strava_access_token = "test_token"
        settings.strava_refresh_token = "test_refresh"
        settings.strava_client_id = "id"
        settings.strava_client_secret = "secret"

        mock_client = AsyncMock()
        mock_client.get_weekly_summary.return_value = {
            "weeks": 1,
            "from": "2025-07-08T00:00:00+00:00",
            "to": "2025-07-15T00:00:00+00:00",
            "total_rides": 3,
            "total_distance_km": 92.5,
            "total_elevation_m": 1170.0,
            "total_moving_time_seconds": 14400,
            "average_speed_kmh": 23.1,
            "sport_type_counts": {"MountainBikeRide": 2, "GravelRide": 1},
            "activities": [
                {
                    "name": "Morning MTB Ride",
                    "sport_type": "MountainBikeRide",
                    "distance_km": 32.5,
                },
            ],
        }
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        result = await strava_weekly_summary(weeks=1)

        assert "Weekly Summary" in result
        assert "Total Rides: 3" in result
        assert "92.5 km" in result
        assert "1170" in result
        assert "MountainBikeRide: 2" in result
        assert "GravelRide: 1" in result
        assert "Morning MTB Ride" in result
