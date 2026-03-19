"""Tests for GPS-Tour.info client."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from mtb_mcp.clients.gpstour import (
    GPSTourClient,
    _extract_tour_id_from_url,
    _map_difficulty,
    _parse_distance,
    _parse_elevation,
)
from mtb_mcp.models.tour import TourDifficulty, TourSource

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "api_responses"


def _load_json_fixture(name: str) -> dict:  # type: ignore[type-arg]
    """Load a JSON fixture file."""
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)  # type: ignore[no-any-return]


def _load_html_fixture(name: str) -> str:
    """Load an HTML fixture file."""
    with open(FIXTURES_DIR / name) as f:
        return f.read()


class TestExtractTourId:
    """Tests for URL tour ID extraction."""

    def test_german_url(self) -> None:
        url = "https://www.gps-tour.info/de/touren/detail.200001.html"
        assert _extract_tour_id_from_url(url) == "200001"

    def test_english_url(self) -> None:
        url = "https://www.gps-tour.info/en/tours/detail.123456.html"
        assert _extract_tour_id_from_url(url) == "123456"

    def test_no_match(self) -> None:
        url = "https://www.example.com/some/page.html"
        assert _extract_tour_id_from_url(url) is None

    def test_invalid_url(self) -> None:
        assert _extract_tour_id_from_url("not a url") is None


class TestParseDistance:
    """Tests for distance parsing."""

    def test_german_format(self) -> None:
        assert _parse_distance("35,2 km") == 35.2

    def test_english_format(self) -> None:
        assert _parse_distance("35.2 km") == 35.2

    def test_no_space(self) -> None:
        assert _parse_distance("12km") == 12.0

    def test_no_match(self) -> None:
        assert _parse_distance("keine Angabe") is None


class TestParseElevation:
    """Tests for elevation parsing."""

    def test_hm_format(self) -> None:
        assert _parse_elevation("420 Hm") == 420.0

    def test_thousands(self) -> None:
        assert _parse_elevation("1.200 Hm") == 1200.0

    def test_m_format(self) -> None:
        assert _parse_elevation("850 m") == 850.0

    def test_no_match(self) -> None:
        assert _parse_elevation("keine Angabe") is None


class TestMapDifficulty:
    """Tests for difficulty mapping."""

    def test_leicht(self) -> None:
        assert _map_difficulty("Leicht") == TourDifficulty.easy

    def test_easy(self) -> None:
        assert _map_difficulty("easy") == TourDifficulty.easy

    def test_mittel(self) -> None:
        assert _map_difficulty("Mittel") == TourDifficulty.moderate

    def test_schwer(self) -> None:
        assert _map_difficulty("Schwer") == TourDifficulty.difficult

    def test_extrem(self) -> None:
        assert _map_difficulty("Extrem schwer") == TourDifficulty.expert

    def test_unknown(self) -> None:
        assert _map_difficulty("unbekannt") is None


class TestGPSTourClientInit:
    """Tests for GPSTourClient initialization."""

    def test_default_init(self) -> None:
        """Should initialize with default settings."""
        client = GPSTourClient()
        assert client._base_url == "https://www.gps-tour.info"
        assert client._searxng_url == "http://localhost:17888"
        assert client._username is None
        assert client._password is None
        assert client._session_cookie is None

    def test_custom_init(self) -> None:
        """Should accept custom searxng URL and credentials."""
        client = GPSTourClient(
            searxng_url="http://searxng:8888",
            username="user",
            password="pass",
        )
        assert client._searxng_url == "http://searxng:8888"
        assert client._username == "user"
        assert client._password == "pass"

    def test_rate_limit(self) -> None:
        """Should have conservative rate limit (0.25 = 1 req per 4s)."""
        client = GPSTourClient()
        assert client._rate_limiter.rate == 0.25

    def test_user_agent(self) -> None:
        """Should set honest User-Agent header."""
        client = GPSTourClient()
        assert "TrailPilot" in client._headers.get("User-Agent", "")
        assert "respectful" in client._headers.get("User-Agent", "")


class TestGPSTourClientSearch:
    """Tests for GPS-Tour.info tour search via SearXNG."""

    @respx.mock
    async def test_search_tours(self) -> None:
        """Should search via SearXNG and parse results."""
        fixture = _load_json_fixture("searxng_gpstour.json")
        respx.get("http://localhost:17888/search").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with GPSTourClient() as client:
            results = await client.search_tours("Erlangen")

        assert len(results) == 3  # 4 results but 1 is not from gps-tour.info
        assert results[0].id == "200001"
        assert results[0].source == TourSource.gps_tour
        assert "MTB Runde Erlangen Tennenlohe" in results[0].name
        assert results[0].url is not None
        assert "200001" in (results[0].url or "")

    @respx.mock
    async def test_search_filters_non_gpstour(self) -> None:
        """Should skip results not from GPS-Tour.info."""
        fixture = _load_json_fixture("searxng_gpstour.json")
        respx.get("http://localhost:17888/search").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with GPSTourClient() as client:
            results = await client.search_tours("Erlangen")

        # Verify the non-GPS-Tour.info URL is excluded
        urls = [r.url for r in results]
        assert not any("example.com" in (u or "") for u in urls)

    @respx.mock
    async def test_search_searxng_error(self) -> None:
        """Should return empty list on SearXNG error."""
        respx.get("http://localhost:17888/search").mock(
            return_value=httpx.Response(500, json={"error": "internal"})
        )

        async with GPSTourClient() as client:
            results = await client.search_tours("Erlangen")

        assert results == []

    @respx.mock
    async def test_search_empty_results(self) -> None:
        """Should handle empty search results."""
        respx.get("http://localhost:17888/search").mock(
            return_value=httpx.Response(200, json={"results": []})
        )

        async with GPSTourClient() as client:
            results = await client.search_tours("nonexistent place")

        assert results == []


class TestGPSTourClientDetail:
    """Tests for GPS-Tour.info tour detail scraping."""

    @respx.mock
    async def test_get_tour_details(self) -> None:
        """Should scrape and parse tour detail page."""
        html = _load_html_fixture("gpstour_detail.html")
        respx.get("https://www.gps-tour.info/de/touren/detail.200001.html").mock(
            return_value=httpx.Response(200, text=html)
        )

        async with GPSTourClient() as client:
            detail = await client.get_tour_details("200001")

        assert detail is not None
        assert detail.id == "200001"
        assert detail.source == TourSource.gps_tour
        assert detail.name == "MTB Runde Erlangen Tennenlohe"
        assert detail.distance_km == 35.2
        assert detail.elevation_m == 420.0
        assert detail.difficulty == TourDifficulty.moderate
        assert detail.duration_minutes == 165  # 2:45 = 165 min
        assert detail.region == "Mittelfranken, Bayern"
        assert detail.download_count == 287
        assert detail.rating == 4.2
        assert detail.description is not None
        assert "Tennenloher Forst" in detail.description

    @respx.mock
    async def test_get_tour_details_with_coordinates(self) -> None:
        """Should extract geo.position meta tag."""
        html = _load_html_fixture("gpstour_detail.html")
        respx.get("https://www.gps-tour.info/de/touren/detail.200001.html").mock(
            return_value=httpx.Response(200, text=html)
        )

        async with GPSTourClient() as client:
            detail = await client.get_tour_details("200001")

        assert detail is not None
        assert detail.start_point is not None
        assert abs(detail.start_point.lat - 49.568) < 0.001
        assert abs(detail.start_point.lon - 11.023) < 0.001

    @respx.mock
    async def test_get_tour_details_404(self) -> None:
        """Should return None for non-existent tour."""
        respx.get("https://www.gps-tour.info/de/touren/detail.99999.html").mock(
            return_value=httpx.Response(404, text="Not Found")
        )

        async with GPSTourClient() as client:
            detail = await client.get_tour_details("99999")

        assert detail is None

    @respx.mock
    async def test_get_tour_details_minimal_html(self) -> None:
        """Should handle minimal HTML without crashing."""
        minimal_html = "<html><head><title>Tour</title></head><body><h1>Simple</h1></body></html>"
        respx.get("https://www.gps-tour.info/de/touren/detail.300001.html").mock(
            return_value=httpx.Response(200, text=minimal_html)
        )

        async with GPSTourClient() as client:
            detail = await client.get_tour_details("300001")

        assert detail is not None
        assert detail.name == "Simple"
        assert detail.distance_km is None
        assert detail.elevation_m is None


class TestGPSTourClientLogin:
    """Tests for GPS-Tour.info login."""

    async def test_login_without_credentials(self) -> None:
        """Should return False without credentials."""
        async with GPSTourClient() as client:
            result = await client._login()

        assert result is False

    @respx.mock
    async def test_login_success(self) -> None:
        """Should login and set session cookie."""
        respx.post("https://www.gps-tour.info/de/login.html").mock(
            return_value=httpx.Response(
                200,
                text="<html>Welcome</html>",
                headers={"Set-Cookie": "session_id=abc123; Path=/"},
            )
        )

        async with GPSTourClient(username="user", password="pass") as client:
            result = await client._login()

        assert result is True
        assert client._session_cookie is not None


class TestGPSTourClientGPX:
    """Tests for GPS-Tour.info GPX download."""

    async def test_download_without_credentials(self) -> None:
        """Should return None without login credentials."""
        async with GPSTourClient() as client:
            gpx = await client.download_gpx("200001")

        assert gpx is None

    @respx.mock
    async def test_download_gpx_success(self) -> None:
        """Should download GPX after login."""
        gpx_content = b'<?xml version="1.0"?><gpx><trk><name>Test</name></trk></gpx>'

        respx.post("https://www.gps-tour.info/de/login.html").mock(
            return_value=httpx.Response(200, text="OK")
        )
        respx.get("https://www.gps-tour.info/de/touren/download.200001.html").mock(
            return_value=httpx.Response(200, content=gpx_content)
        )

        async with GPSTourClient(username="user", password="pass") as client:
            gpx = await client.download_gpx("200001")

        assert gpx is not None
        assert b"<gpx>" in gpx


class TestGPSTourClientCleanup:
    """Tests for GPSTourClient cleanup."""

    async def test_close_both_clients(self) -> None:
        """Should close both HTTP clients."""
        client = GPSTourClient()
        # Force creation of both clients
        _ = client._get_client()
        _ = client._get_searxng_client()

        await client.close()

        assert client._client is None
        assert client._searxng_client is None
