"""Tests for Komoot API client."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import respx

from mtb_mcp.clients.komoot import (
    KomootClient,
    _map_difficulty,
    _parse_tour_detail,
    _parse_tour_summary,
)
from mtb_mcp.models.tour import TourDifficulty, TourSource

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "api_responses"


def _load_fixture(name: str) -> dict:  # type: ignore[type-arg]
    """Load a JSON fixture file."""
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)  # type: ignore[no-any-return]


class TestMapDifficulty:
    """Tests for difficulty mapping."""

    def test_easy(self) -> None:
        assert _map_difficulty("easy") == TourDifficulty.easy

    def test_moderate(self) -> None:
        assert _map_difficulty("moderate") == TourDifficulty.moderate

    def test_difficult(self) -> None:
        assert _map_difficulty("difficult") == TourDifficulty.difficult

    def test_expert(self) -> None:
        assert _map_difficulty("expert") == TourDifficulty.expert

    def test_none(self) -> None:
        assert _map_difficulty(None) is None

    def test_unknown(self) -> None:
        assert _map_difficulty("unknown_grade") is None

    def test_case_insensitive(self) -> None:
        assert _map_difficulty("MODERATE") == TourDifficulty.moderate
        assert _map_difficulty("Easy") == TourDifficulty.easy


class TestParseTourSummary:
    """Tests for tour summary parsing."""

    def test_parse_basic_tour(self) -> None:
        """Should parse a basic Komoot tour object."""
        data = {
            "id": 1001,
            "name": "Test Tour",
            "distance": 32500.0,
            "elevation_up": 450.0,
            "difficulty": {"grade": "moderate"},
            "start_point": {"lat": 49.596, "lng": 11.004},
        }
        summary = _parse_tour_summary(data)

        assert summary.id == "1001"
        assert summary.source == TourSource.komoot
        assert summary.name == "Test Tour"
        assert summary.distance_km == 32.5
        assert summary.elevation_m == 450.0
        assert summary.difficulty == TourDifficulty.moderate
        assert summary.url == "https://www.komoot.com/tour/1001"
        assert summary.start_point is not None
        assert summary.start_point.lat == 49.596

    def test_parse_minimal_tour(self) -> None:
        """Should handle missing optional fields."""
        data = {"id": 2001, "name": "Minimal Tour"}
        summary = _parse_tour_summary(data)

        assert summary.id == "2001"
        assert summary.name == "Minimal Tour"
        assert summary.distance_km is None
        assert summary.elevation_m is None
        assert summary.difficulty is None
        assert summary.start_point is None

    def test_parse_from_fixture(self) -> None:
        """Should parse tours from fixture file."""
        fixture = _load_fixture("komoot_tours.json")
        tours = fixture["_embedded"]["tours"]

        assert len(tours) == 3
        summary = _parse_tour_summary(tours[0])
        assert summary.name == "Erlangen Forest Loop"
        assert summary.distance_km == 32.5
        assert summary.difficulty == TourDifficulty.moderate


class TestParseTourDetail:
    """Tests for tour detail parsing."""

    def test_parse_detail_from_fixture(self) -> None:
        """Should parse full tour detail from fixture."""
        data = _load_fixture("komoot_tour_detail.json")
        detail = _parse_tour_detail(data)

        assert detail.id == "1001"
        assert detail.name == "Erlangen Forest Loop"
        assert detail.distance_km == 32.5
        assert detail.elevation_m == 450.0
        assert detail.difficulty == TourDifficulty.moderate
        assert detail.description is not None
        assert "forests" in detail.description
        assert detail.duration_minutes == 120
        assert "gravel" in detail.surfaces
        assert "singletrack" in detail.surfaces
        assert len(detail.waypoints) == 5
        assert detail.waypoints[0].ele == 280.0
        assert detail.download_count == 142
        assert detail.rating == 4.5

    def test_parse_detail_minimal(self) -> None:
        """Should handle detail with minimal data."""
        data = {"id": 3001, "name": "Bare Tour"}
        detail = _parse_tour_detail(data)

        assert detail.id == "3001"
        assert detail.description is None
        assert detail.duration_minutes is None
        assert detail.surfaces == []
        assert detail.waypoints == []


class TestKomootClientInit:
    """Tests for KomootClient initialization."""

    def test_default_init(self) -> None:
        """Should initialize with default settings."""
        client = KomootClient()
        assert client._base_url == "https://api.komoot.de"
        assert client._email is None
        assert client._password is None
        assert client._user_id is None
        assert client._authenticated is False

    def test_init_with_credentials(self) -> None:
        """Should accept email and password."""
        client = KomootClient(email="test@example.com", password="secret")
        assert client._email == "test@example.com"
        assert client._password == "secret"


class TestKomootClientAuth:
    """Tests for Komoot authentication."""

    @respx.mock
    async def test_successful_auth(self) -> None:
        """Should authenticate and extract user_id."""
        fixture = _load_fixture("komoot_login.json")
        respx.get("https://api.komoot.de/v006/account/email/rider@example.com").mock(
            return_value=httpx.Response(200, json=fixture)
        )

        async with KomootClient(
            email="rider@example.com", password="secret"
        ) as client:
            result = await client.authenticate()

        assert result is True
        assert client._user_id == "123456789"
        assert client._authenticated is True

    @respx.mock
    async def test_auth_failure_401(self) -> None:
        """Should handle 401 unauthorized."""
        respx.get("https://api.komoot.de/v006/account/email/bad@example.com").mock(
            return_value=httpx.Response(401, json={"error": "unauthorized"})
        )

        async with KomootClient(email="bad@example.com", password="wrong") as client:
            result = await client.authenticate()

        assert result is False
        assert client._authenticated is False

    async def test_auth_without_credentials(self) -> None:
        """Should return False without credentials."""
        async with KomootClient() as client:
            result = await client.authenticate()

        assert result is False

    @respx.mock
    async def test_auth_already_authenticated(self) -> None:
        """Should skip re-authentication."""
        async with KomootClient(
            email="rider@example.com", password="secret"
        ) as client:
            client._authenticated = True
            client._user_id = "123456789"
            result = await client.authenticate()

        assert result is True


class TestKomootClientSearch:
    """Tests for Komoot tour search."""

    @respx.mock
    async def test_search_tours(self) -> None:
        """Should search and parse tours."""
        login_fixture = _load_fixture("komoot_login.json")
        tours_fixture = _load_fixture("komoot_tours.json")

        respx.get("https://api.komoot.de/v006/account/email/rider@example.com").mock(
            return_value=httpx.Response(200, json=login_fixture)
        )
        respx.get("https://api.komoot.de/v007/users/123456789/tours/").mock(
            return_value=httpx.Response(200, json=tours_fixture)
        )

        async with KomootClient(
            email="rider@example.com", password="secret"
        ) as client:
            results = await client.search_tours(lat=49.59, lon=11.00, radius_km=30.0)

        assert len(results) == 3
        assert results[0].name == "Erlangen Forest Loop"
        assert results[0].source == TourSource.komoot
        assert results[1].name == "Rathsberg Singletrail"
        assert results[2].distance_km == 12.0

    @respx.mock
    async def test_search_without_auth(self) -> None:
        """Should return empty list if auth fails."""
        respx.get("https://api.komoot.de/v006/account/email/bad@example.com").mock(
            return_value=httpx.Response(401, json={"error": "unauthorized"})
        )

        async with KomootClient(email="bad@example.com", password="wrong") as client:
            results = await client.search_tours(lat=49.59, lon=11.00)

        assert results == []


class TestKomootClientDetail:
    """Tests for Komoot tour detail retrieval."""

    @respx.mock
    async def test_get_tour_details(self) -> None:
        """Should fetch and parse tour details."""
        login_fixture = _load_fixture("komoot_login.json")
        detail_fixture = _load_fixture("komoot_tour_detail.json")

        respx.get("https://api.komoot.de/v006/account/email/rider@example.com").mock(
            return_value=httpx.Response(200, json=login_fixture)
        )
        respx.get("https://api.komoot.de/v007/tours/1001").mock(
            return_value=httpx.Response(200, json=detail_fixture)
        )

        async with KomootClient(
            email="rider@example.com", password="secret"
        ) as client:
            detail = await client.get_tour_details("1001")

        assert detail is not None
        assert detail.name == "Erlangen Forest Loop"
        assert detail.description is not None
        assert detail.duration_minutes == 120
        assert len(detail.surfaces) > 0
        assert len(detail.waypoints) == 5

    @respx.mock
    async def test_get_tour_details_not_found(self) -> None:
        """Should return None for non-existent tour."""
        login_fixture = _load_fixture("komoot_login.json")

        respx.get("https://api.komoot.de/v006/account/email/rider@example.com").mock(
            return_value=httpx.Response(200, json=login_fixture)
        )
        respx.get("https://api.komoot.de/v007/tours/99999").mock(
            return_value=httpx.Response(404, json={"error": "not found"})
        )

        async with KomootClient(
            email="rider@example.com", password="secret"
        ) as client:
            detail = await client.get_tour_details("99999")

        assert detail is None


class TestKomootClientGPX:
    """Tests for Komoot GPX download."""

    @respx.mock
    async def test_download_gpx(self) -> None:
        """Should download GPX data."""
        login_fixture = _load_fixture("komoot_login.json")
        gpx_content = b'<?xml version="1.0"?><gpx><trk><name>Test</name></trk></gpx>'

        respx.get("https://api.komoot.de/v006/account/email/rider@example.com").mock(
            return_value=httpx.Response(200, json=login_fixture)
        )
        respx.get("https://api.komoot.de/v007/tours/1001.gpx").mock(
            return_value=httpx.Response(200, content=gpx_content)
        )

        async with KomootClient(
            email="rider@example.com", password="secret"
        ) as client:
            gpx = await client.download_gpx("1001")

        assert gpx is not None
        assert b"<gpx>" in gpx

    async def test_download_gpx_without_auth(self) -> None:
        """Should return None without credentials."""
        async with KomootClient() as client:
            gpx = await client.download_gpx("1001")

        assert gpx is None
