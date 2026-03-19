"""Tests for MCP tour search tools."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import respx

from mtb_mcp.models.tour import TourDifficulty, TourSource, TourSummary
from mtb_mcp.tools.tour_search_tools import (
    _format_tour_detail,
    _format_tour_summary,
    _validate_difficulty,
    gpstour_download_gpx,
    gpstour_tour_details,
    komoot_download_gpx,
    komoot_tour_details,
    mtbproject_trails,
    search_tours,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "api_responses"


def _load_fixture(name: str) -> dict:  # type: ignore[type-arg]
    """Load a JSON fixture file."""
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)  # type: ignore[no-any-return]


class TestValidateDifficulty:
    """Tests for difficulty validation."""

    def test_valid_values(self) -> None:
        assert _validate_difficulty("easy") == TourDifficulty.easy
        assert _validate_difficulty("moderate") == TourDifficulty.moderate
        assert _validate_difficulty("difficult") == TourDifficulty.difficult
        assert _validate_difficulty("expert") == TourDifficulty.expert

    def test_case_insensitive(self) -> None:
        assert _validate_difficulty("EASY") == TourDifficulty.easy
        assert _validate_difficulty("Moderate") == TourDifficulty.moderate

    def test_none(self) -> None:
        assert _validate_difficulty(None) is None

    def test_invalid(self) -> None:
        assert _validate_difficulty("impossible") is None


class TestFormatTourSummary:
    """Tests for tour summary formatting."""

    def test_format_full_summary(self) -> None:
        tour = TourSummary(
            id="1001",
            source=TourSource.komoot,
            name="Erlangen Loop",
            distance_km=32.5,
            elevation_m=450.0,
            difficulty=TourDifficulty.moderate,
            region="Franken",
            url="https://www.komoot.com/tour/1001",
        )
        result = _format_tour_summary(tour)

        assert "[komoot]" in result
        assert "Erlangen Loop" in result
        assert "32.5 km" in result
        assert "450 m elevation" in result
        assert "moderate" in result
        assert "Franken" in result
        assert "https://www.komoot.com/tour/1001" in result

    def test_format_minimal_summary(self) -> None:
        tour = TourSummary(
            id="2001",
            source=TourSource.gps_tour,
            name="Simple Tour",
        )
        result = _format_tour_summary(tour)

        assert "[gps_tour]" in result
        assert "Simple Tour" in result
        assert "ID: 2001" in result


class TestFormatTourDetail:
    """Tests for tour detail formatting."""

    def test_format_with_description(self) -> None:
        from mtb_mcp.models.tour import TourDetail

        detail = TourDetail(
            id="1001",
            source=TourSource.komoot,
            name="Test Tour",
            distance_km=25.0,
            elevation_m=300.0,
            difficulty=TourDifficulty.moderate,
            description="A wonderful mountain bike tour.",
            duration_minutes=135,
            surfaces=["gravel", "singletrack"],
            rating=4.5,
        )
        result = _format_tour_detail(detail)

        assert "Test Tour" in result
        assert "25.0 km" in result
        assert "300 m" in result
        assert "moderate" in result
        assert "2h 15min" in result
        assert "gravel, singletrack" in result
        assert "4.5" in result
        assert "A wonderful mountain bike tour." in result


class TestSearchTours:
    """Tests for unified search_tours tool."""

    @respx.mock
    @patch("mtb_mcp.tools.tour_search_tools.get_settings")
    async def test_search_with_komoot_and_gpstour(
        self, mock_settings: AsyncMock
    ) -> None:
        """Should search both sources and return combined results."""
        settings = mock_settings.return_value
        settings.home_lat = 49.59
        settings.home_lon = 11.00
        settings.komoot_email = "rider@example.com"
        settings.komoot_password = "secret"
        settings.searxng_url = "http://localhost:17888"
        settings.gpstour_username = None
        settings.gpstour_password = None

        # Mock Komoot auth
        login_fixture = _load_fixture("komoot_login.json")
        respx.get("https://api.komoot.de/v006/account/email/rider@example.com").mock(
            return_value=httpx.Response(200, json=login_fixture)
        )

        # Mock Komoot search
        tours_fixture = _load_fixture("komoot_tours.json")
        respx.get("https://api.komoot.de/v007/users/123456789/tours/").mock(
            return_value=httpx.Response(200, json=tours_fixture)
        )

        # Mock SearXNG search
        searxng_fixture = _load_fixture("searxng_gpstour.json")
        respx.get("http://localhost:17888/search").mock(
            return_value=httpx.Response(200, json=searxng_fixture)
        )

        result = await search_tours(lat=49.59, lon=11.00, radius_km=30.0)

        assert "Found" in result
        assert "tour(s)" in result
        assert "komoot" in result.lower()
        assert "gps_tour" in result.lower()

    @respx.mock
    @patch("mtb_mcp.tools.tour_search_tools.get_settings")
    async def test_search_without_komoot_credentials(
        self, mock_settings: AsyncMock
    ) -> None:
        """Should search only GPS-Tour.info when Komoot not configured."""
        settings = mock_settings.return_value
        settings.home_lat = 49.59
        settings.home_lon = 11.00
        settings.komoot_email = None
        settings.komoot_password = None
        settings.searxng_url = "http://localhost:17888"
        settings.gpstour_username = None
        settings.gpstour_password = None

        # Mock SearXNG search
        searxng_fixture = _load_fixture("searxng_gpstour.json")
        respx.get("http://localhost:17888/search").mock(
            return_value=httpx.Response(200, json=searxng_fixture)
        )

        result = await search_tours(query="Erlangen")

        assert "Found" in result
        assert "gps_tour" in result.lower()

    @respx.mock
    @patch("mtb_mcp.tools.tour_search_tools.get_settings")
    async def test_search_uses_home_location(self, mock_settings: AsyncMock) -> None:
        """Should use home location when no coordinates given."""
        settings = mock_settings.return_value
        settings.home_lat = 49.59
        settings.home_lon = 11.00
        settings.komoot_email = None
        settings.komoot_password = None
        settings.searxng_url = "http://localhost:17888"
        settings.gpstour_username = None
        settings.gpstour_password = None

        respx.get("http://localhost:17888/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )

        result = await search_tours()

        assert "49.59" in result
        assert "11.00" in result

    @respx.mock
    @patch("mtb_mcp.tools.tour_search_tools.get_settings")
    async def test_search_no_results(self, mock_settings: AsyncMock) -> None:
        """Should return informative message when no results found."""
        settings = mock_settings.return_value
        settings.home_lat = 49.59
        settings.home_lon = 11.00
        settings.komoot_email = None
        settings.komoot_password = None
        settings.searxng_url = "http://localhost:17888"
        settings.gpstour_username = None
        settings.gpstour_password = None

        respx.get("http://localhost:17888/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )

        result = await search_tours(query="nonexistent")

        assert "No tours found" in result


class TestKomootTourDetails:
    """Tests for komoot_tour_details tool."""

    @patch("mtb_mcp.tools.tour_search_tools.get_settings")
    async def test_missing_credentials(self, mock_settings: AsyncMock) -> None:
        """Should return error message without credentials."""
        settings = mock_settings.return_value
        settings.komoot_email = None

        result = await komoot_tour_details("1001")

        assert "not configured" in result

    @respx.mock
    @patch("mtb_mcp.tools.tour_search_tools.get_settings")
    async def test_successful_detail(self, mock_settings: AsyncMock) -> None:
        """Should return formatted tour details."""
        settings = mock_settings.return_value
        settings.komoot_email = "rider@example.com"
        settings.komoot_password = "secret"

        login_fixture = _load_fixture("komoot_login.json")
        detail_fixture = _load_fixture("komoot_tour_detail.json")

        respx.get("https://api.komoot.de/v006/account/email/rider@example.com").mock(
            return_value=httpx.Response(200, json=login_fixture)
        )
        respx.get("https://api.komoot.de/v007/tours/1001").mock(
            return_value=httpx.Response(200, json=detail_fixture)
        )

        result = await komoot_tour_details("1001")

        assert "Erlangen Forest Loop" in result
        assert "32.5 km" in result


class TestKomootDownloadGPX:
    """Tests for komoot_download_gpx tool."""

    @patch("mtb_mcp.tools.tour_search_tools.get_settings")
    async def test_missing_credentials(self, mock_settings: AsyncMock) -> None:
        """Should return error message without credentials."""
        settings = mock_settings.return_value
        settings.komoot_email = None

        result = await komoot_download_gpx("1001")

        assert "not configured" in result


class TestGPSTourDetails:
    """Tests for gpstour_tour_details tool."""

    @respx.mock
    @patch("mtb_mcp.tools.tour_search_tools.get_settings")
    async def test_successful_detail(self, mock_settings: AsyncMock) -> None:
        """Should return formatted tour details."""
        settings = mock_settings.return_value
        settings.searxng_url = "http://localhost:17888"
        settings.gpstour_username = None
        settings.gpstour_password = None

        html_fixture = Path(FIXTURES_DIR / "gpstour_detail.html").read_text()
        respx.get("https://www.gps-tour.info/de/touren/detail.200001.html").mock(
            return_value=httpx.Response(200, text=html_fixture)
        )

        result = await gpstour_tour_details("200001")

        assert "MTB Runde Erlangen Tennenlohe" in result
        assert "35.2 km" in result


class TestGPSTourDownloadGPX:
    """Tests for gpstour_download_gpx tool."""

    @patch("mtb_mcp.tools.tour_search_tools.get_settings")
    async def test_missing_credentials(self, mock_settings: AsyncMock) -> None:
        """Should return error message without credentials."""
        settings = mock_settings.return_value
        settings.gpstour_username = None

        result = await gpstour_download_gpx("200001")

        assert "not configured" in result


class TestMTBProjectTrails:
    """Tests for mtbproject_trails tool."""

    @patch("mtb_mcp.tools.tour_search_tools.get_settings")
    async def test_returns_informative_message(self, mock_settings: AsyncMock) -> None:
        """Should return informative message about limited availability."""
        settings = mock_settings.return_value
        settings.home_lat = 49.59
        settings.home_lon = 11.00

        result = await mtbproject_trails()

        assert "MTB Project" in result
        assert "planned" in result or "future" in result
        assert "49.59" in result

    @patch("mtb_mcp.tools.tour_search_tools.get_settings")
    async def test_uses_custom_coordinates(self, mock_settings: AsyncMock) -> None:
        """Should use provided coordinates."""
        settings = mock_settings.return_value
        settings.home_lat = 49.59
        settings.home_lon = 11.00

        result = await mtbproject_trails(lat=47.27, lon=11.39, radius_km=20.0)

        assert "47.27" in result
        assert "11.39" in result
        assert "20.0" in result
