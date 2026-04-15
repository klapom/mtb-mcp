"""Komoot v007 API client using direct HTTP via BaseClient."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
import structlog

from mtb_mcp.clients.base import BaseClient
from mtb_mcp.models.common import GeoPoint
from mtb_mcp.models.tour import TourDetail, TourDifficulty, TourSource, TourSummary

logger = structlog.get_logger(__name__)


def _map_difficulty(raw: str | None) -> TourDifficulty | None:
    """Map Komoot difficulty string to TourDifficulty enum."""
    if raw is None:
        return None
    mapping: dict[str, TourDifficulty] = {
        "easy": TourDifficulty.easy,
        "moderate": TourDifficulty.moderate,
        "difficult": TourDifficulty.difficult,
        "expert": TourDifficulty.expert,
    }
    return mapping.get(raw.lower())


def _parse_tour_summary(data: dict[str, Any]) -> TourSummary:
    """Parse a Komoot tour object into a TourSummary."""
    tour_id = str(data.get("id", ""))
    name = data.get("name", "Unknown Tour")
    distance_km = data.get("distance", 0.0) / 1000.0 if data.get("distance") else None
    elevation_m = data.get("elevation_up")

    difficulty_raw = data.get("difficulty", {})
    difficulty_grade = difficulty_raw.get("grade") if isinstance(difficulty_raw, dict) else None
    difficulty = _map_difficulty(difficulty_grade)

    start_point: GeoPoint | None = None
    start_data = data.get("start_point")
    if isinstance(start_data, dict) and "lat" in start_data and "lng" in start_data:
        start_point = GeoPoint(lat=start_data["lat"], lon=start_data["lng"])

    return TourSummary(
        id=tour_id,
        source=TourSource.komoot,
        name=name,
        distance_km=round(distance_km, 2) if distance_km is not None else None,
        elevation_m=round(elevation_m, 0) if elevation_m is not None else None,
        difficulty=difficulty,
        url=f"https://www.komoot.com/tour/{tour_id}",
        start_point=start_point,
    )


def _parse_tour_detail(data: dict[str, Any]) -> TourDetail:
    """Parse a Komoot tour object into a TourDetail."""
    summary = _parse_tour_summary(data)
    description = data.get("description")
    duration_minutes = None
    if data.get("duration"):
        duration_minutes = int(data["duration"] / 60)

    surfaces: list[str] = []
    segments = data.get("segments", [])
    if isinstance(segments, list):
        for seg in segments:
            surface = seg.get("surface") if isinstance(seg, dict) else None
            if surface and surface not in surfaces:
                surfaces.append(surface)

    waypoints: list[GeoPoint] = []
    coordinates = data.get("coordinates")
    if isinstance(coordinates, list):
        for coord in coordinates[:100]:
            if isinstance(coord, dict) and "lat" in coord and "lng" in coord:
                waypoints.append(
                    GeoPoint(lat=coord["lat"], lon=coord["lng"], ele=coord.get("alt"))
                )

    return TourDetail(
        id=summary.id,
        source=summary.source,
        name=summary.name,
        distance_km=summary.distance_km,
        elevation_m=summary.elevation_m,
        difficulty=summary.difficulty,
        region=summary.region,
        url=summary.url,
        start_point=summary.start_point,
        description=description,
        duration_minutes=duration_minutes,
        surfaces=surfaces,
        waypoints=waypoints,
        download_count=data.get("downloads"),
        rating=data.get("rating"),
    )


class KomootClient(BaseClient):
    """Client for Komoot v007 API.

    Uses direct HTTP calls with Basic Auth against the reverse-engineered v007 API.
    """

    def __init__(self, email: str | None = None, password: str | None = None,
                 searxng_url: str = "http://localhost:17888") -> None:
        super().__init__(
            base_url="https://api.komoot.de",
            rate_limit=2.0,
        )
        self._email = email
        self._password = password
        self._searxng_url = searxng_url
        self._user_id: str | None = None
        self._token: str | None = None
        self._authenticated = False

    async def authenticate(self) -> bool:
        """Authenticate with Komoot using email/password via Basic Auth.

        Calls v006 account endpoint to get user_id and token.
        Returns True if authentication succeeded.
        """
        if not self._email or not self._password:
            logger.warning("komoot_auth_missing_credentials")
            return False

        if self._authenticated and self._user_id:
            return True

        try:
            await self._rate_limiter.acquire()
            client = self._get_client()

            # Trailing slash is required (kompy pattern)
            response = await client.get(
                f"/v006/account/email/{self._email}/",
                auth=(self._email, self._password),
            )
            response.raise_for_status()

            data = response.json()
            username = data.get("username")
            token = data.get("password")
            if username:
                self._user_id = str(username)
                # Use token for subsequent requests (more reliable than password)
                if token:
                    self._token = str(token)
                self._authenticated = True
                logger.info("komoot_auth_success", user_id=self._user_id)
                return True

            logger.warning("komoot_auth_no_username", response_keys=list(data.keys()))
            return False

        except httpx.HTTPStatusError as exc:
            logger.warning("komoot_auth_failed", status=exc.response.status_code)
            return False
        except httpx.HTTPError as exc:
            logger.warning("komoot_auth_error", error=str(exc))
            return False

    async def search_tours(
        self,
        lat: float,
        lon: float,
        radius_km: float = 30.0,
        sport_type: str = "mtb",
        limit: int = 20,
    ) -> list[TourSummary]:
        """Search for tours near a location.

        First tries to find user's own tours via v007 API,
        then discovers public tours via Komoot Guide pages.
        """
        results: list[TourSummary] = []

        # 1. Own tours via API (requires auth)
        if not self._authenticated:
            await self.authenticate()

        if self._authenticated:
            own = await self._search_own_tours(lat, lon, radius_km, sport_type, limit)
            results.extend(own)

        # 2. Public tours via Guide page scraping (no auth needed)
        public = await self.discover_public_tours(lat, lon, sport_type, limit,
                                                   searxng_url=self._searxng_url)
        # Avoid duplicates (by URL)
        existing_urls = {t.url for t in results}
        for tour in public:
            if tour.url not in existing_urls:
                results.append(tour)
                existing_urls.add(tour.url)

        logger.info("komoot_search_results", own=len(results) - len(public), public=len(public),
                     total=len(results))
        return results[:limit]

    async def _search_own_tours(
        self, lat: float, lon: float, radius_km: float, sport_type: str, limit: int,
    ) -> list[TourSummary]:
        """Search user's own tours via v007 API."""
        try:
            await self._rate_limiter.acquire()
            client = self._get_client()

            params: dict[str, str] = {
                "sport_types": sport_type,
                "center": f"{lat},{lon}",
                "max_distance": str(int(radius_km * 1000)),
                "sort_field": "proximity",
                "sort_direction": "asc",
                "limit": str(limit),
                "status": "public",
            }

            response = await client.get(
                f"/v007/users/{self._user_id}/tours/",
                params=params,
                auth=(self._email or "", self._token or self._password or ""),
            )
            response.raise_for_status()

            data = response.json()
            embedded = data.get("_embedded", {})
            tours_data = embedded.get("tours", [])

            results: list[TourSummary] = []
            for tour_data in tours_data[:limit]:
                if isinstance(tour_data, dict):
                    results.append(_parse_tour_summary(tour_data))
            return results

        except httpx.HTTPError as exc:
            logger.warning("komoot_own_tours_error", error=str(exc))
            return []

    async def discover_public_tours(
        self,
        lat: float,
        lon: float,
        sport_type: str = "mtb",
        limit: int = 20,
        searxng_url: str = "http://localhost:17888",
    ) -> list[TourSummary]:
        """Discover public tours by finding and scraping Komoot Guide pages.

        Strategy:
        1. Use SearXNG to find Komoot guide pages for the region
        2. Fetch the best matching guide page
        3. Extract tour data from JSON-LD structured data

        Rate-limited: 1 SearXNG query + 1 Komoot page fetch.
        """
        sport_slug = "mountainbike" if sport_type == "mtb" else sport_type
        try:
            await self._rate_limiter.acquire()
            client = self._get_client()

            # Step 1: Find guide page URL via SearXNG
            guide_url = await self._find_guide_page(client, lat, lon, sport_slug, searxng_url)
            if not guide_url:
                logger.debug("komoot_no_guide_page_found")
                return []

            # Step 2: Fetch and parse the guide page
            await self._rate_limiter.acquire()
            response = await client.get(
                guide_url,
                headers={
                    "User-Agent": "TrailPilot-MCP/0.1 (MTB route planner)",
                    "Accept": "text/html",
                },
                follow_redirects=True,
            )
            if response.status_code != 200:
                logger.debug("komoot_guide_page_failed", url=guide_url, status=response.status_code)
                return []

            tours = self._extract_tours_from_html(response.text, limit)
            logger.info("komoot_public_tours_found", guide_url=guide_url, count=len(tours))
            return tours

        except httpx.HTTPError as exc:
            logger.warning("komoot_discover_error", error=str(exc))
            return []

    @staticmethod
    async def _find_guide_page(
        client: httpx.AsyncClient, lat: float, lon: float, sport_slug: str,
        searxng_url: str,
    ) -> str | None:
        """Find the best Komoot guide page URL for a region via SearXNG."""
        try:
            # Reverse-geocode via Nominatim to get city name (free, no auth)
            nominatim_resp = await client.get(
                "https://nominatim.openstreetmap.org/reverse",
                params={"lat": str(lat), "lon": str(lon), "format": "json", "zoom": "10"},
                headers={"User-Agent": "TrailPilot-MCP/0.1"},
            )
            city = "region"
            if nominatim_resp.status_code == 200:
                addr = nominatim_resp.json().get("address", {})
                city = addr.get("city", addr.get("town", addr.get("county", "region")))

            # Search SearXNG for Komoot guide page
            resp = await client.get(
                f"{searxng_url}/search",
                params={
                    "q": f"site:komoot.com {sport_slug}-touren-rund-um {city}",
                    "format": "json",
                },
            )
            if resp.status_code != 200:
                return None

            results = resp.json().get("results", [])
            # Find the best guide URL
            for r in results:
                url: str = r.get("url", "")
                if "komoot.com" in url and "guide" in url:
                    return url

            return None

        except Exception as exc:
            logger.warning("komoot_guide_search_error", error=str(exc))
            return None

    @staticmethod
    def _extract_tours_from_html(html: str, limit: int) -> list[TourSummary]:
        """Extract tour data from Komoot HTML page using JSON-LD structured data."""
        results: list[TourSummary] = []

        try:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html, "lxml")
            for script in soup.find_all("script", type="application/ld+json"):
                if not script.string:
                    continue
                data = json.loads(script.string)
                if data.get("@type") != "CollectionPage":
                    continue

                item_list = data.get("mainEntity", {})
                elements = item_list.get("itemListElement", [])

                for el in elements[:limit]:
                    item = el.get("item", {})
                    name = item.get("name", "")
                    url = item.get("url", "")
                    if not name or not url:
                        continue

                    # Extract tour ID from URL
                    tour_id_match = re.search(r"/(\d+)", url)
                    tour_id = tour_id_match.group(1) if tour_id_match else ""
                    # Also handle smarttour URLs like /smarttour/e1234/name
                    if not tour_id:
                        tour_id_match = re.search(r"/smarttour/(?:e)?(\d+)", url)
                        tour_id = tour_id_match.group(1) if tour_id_match else url

                    results.append(
                        TourSummary(
                            id=tour_id,
                            source=TourSource.komoot,
                            name=name,
                            url=url if url.startswith("http") else f"https://www.komoot.com{url}",
                        )
                    )

                if results:
                    break  # Found tours, no need to check more scripts

        except Exception as exc:
            logger.warning("komoot_html_parse_error", error=str(exc))

        logger.info("komoot_public_tours_found", count=len(results))
        return results

    async def get_tour_details(self, tour_id: str) -> TourDetail | None:
        """Get detailed tour information by tour ID.

        Tries v007 API first, falls back to scraping the public smarttour page.
        """
        # Try v007 API first
        if self._authenticated or await self.authenticate():
            try:
                await self._rate_limiter.acquire()
                client = self._get_client()
                response = await client.get(
                    f"/v007/tours/{tour_id}",
                    auth=(self._email or "", self._token or self._password or ""),
                )
                response.raise_for_status()
                data = response.json()
                return _parse_tour_detail(data)
            except httpx.HTTPError:
                logger.debug("komoot_v007_fallback", tour_id=tour_id)

        # Fallback: scrape the public smarttour/tour page
        return await self._scrape_tour_details(tour_id)

    async def _scrape_tour_details(self, tour_id: str) -> TourDetail | None:
        """Scrape tour details from public Komoot page."""
        try:
            from bs4 import BeautifulSoup

            await self._rate_limiter.acquire()
            client = self._get_client()

            # Try smarttour URL first, then regular tour URL
            for url_pattern in [
                f"https://www.komoot.com/de-de/smarttour/{tour_id}",
                f"https://www.komoot.com/de-de/tour/{tour_id}",
            ]:
                response = await client.get(
                    url_pattern,
                    headers={
                        "User-Agent": "TrailPilot-MCP/0.1 (MTB route planner)",
                        "Accept": "text/html",
                    },
                    follow_redirects=True,
                )
                if response.status_code != 200:
                    continue

                soup = BeautifulSoup(response.text, "lxml")
                for script in soup.find_all("script", type="application/ld+json"):
                    if not script.string:
                        continue
                    data = json.loads(script.string)
                    types = data.get("@type", [])
                    if isinstance(types, str):
                        types = [types]
                    if "Trip" not in types:
                        continue

                    # Extract properties
                    props: dict[str, str] = {}
                    for prop in data.get("additionalProperty", []):
                        name = prop.get("name", "")
                        value = prop.get("value", "")
                        if name and value:
                            props[name] = value

                    # Parse distance
                    distance_km = None
                    dist_raw = props.get("Distanz", "")
                    if dist_raw:
                        dist_clean = dist_raw.replace(",", ".").replace("\xa0", "").strip()
                        dist_match = re.search(r"([\d.]+)", dist_clean)
                        if dist_match:
                            distance_km = float(dist_match.group(1))

                    # Parse duration (PT4H41M format)
                    duration_minutes = None
                    dur_raw = props.get("Dauer", "")
                    if dur_raw:
                        h_match = re.search(r"(\d+)H", dur_raw)
                        m_match = re.search(r"(\d+)M", dur_raw)
                        hours = int(h_match.group(1)) if h_match else 0
                        mins = int(m_match.group(1)) if m_match else 0
                        duration_minutes = hours * 60 + mins

                    # Parse difficulty
                    diff_raw = props.get("Schwierigkeit", "").lower()
                    diff_map = {
                        "leicht": TourDifficulty.easy,
                        "mittel": TourDifficulty.moderate,
                        "schwierig": TourDifficulty.difficult,
                        "schwer": TourDifficulty.difficult,
                    }
                    difficulty = diff_map.get(diff_raw)

                    tour_url = data.get("url", url_pattern)

                    logger.info("komoot_smarttour_scraped", tour_id=tour_id, name=data.get("name"))

                    return TourDetail(
                        id=tour_id,
                        source=TourSource.komoot,
                        name=data.get("name", f"Tour {tour_id}"),
                        distance_km=distance_km,
                        difficulty=difficulty,
                        description=data.get("description", ""),
                        url=tour_url if tour_url.startswith("http") else f"https://www.komoot.com{tour_url}",
                        duration_minutes=duration_minutes,
                    )

            logger.warning("komoot_scrape_no_data", tour_id=tour_id)
            return None

        except Exception as exc:
            logger.warning("komoot_scrape_error", tour_id=tour_id, error=str(exc))
            return None

    async def download_gpx(self, tour_id: str) -> bytes | None:
        """Download GPX file for a tour."""
        if not self._authenticated:
            auth_ok = await self.authenticate()
            if not auth_ok:
                return None

        try:
            await self._rate_limiter.acquire()
            client = self._get_client()

            response = await client.get(
                f"/v007/tours/{tour_id}.gpx",
                auth=(self._email or "", self._token or self._password or ""),
            )
            response.raise_for_status()

            logger.info("komoot_gpx_downloaded", tour_id=tour_id, size=len(response.content))
            return response.content

        except httpx.HTTPError as exc:
            logger.warning("komoot_gpx_error", tour_id=tour_id, error=str(exc))
            return None
