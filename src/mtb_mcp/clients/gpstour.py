"""GPS-Tour.info client using SearXNG for search and BeautifulSoup for scraping.

GPS-Tour.info is a community project with 150k+ GPS tracks (Europe, mainly DACH).
This client is very conservative with rate limiting to respect the community resource.
"""

from __future__ import annotations

import contextlib
import re
from typing import Any

import httpx
import structlog
from bs4 import BeautifulSoup

from mtb_mcp.clients.base import BaseClient
from mtb_mcp.models.common import GeoPoint
from mtb_mcp.models.tour import TourDetail, TourDifficulty, TourSource, TourSummary
from mtb_mcp.utils.rate_limiter import TokenBucketRateLimiter

logger = structlog.get_logger(__name__)

# Honest User-Agent for GPS-Tour.info requests
_GPSTOUR_USER_AGENT = (
    "TrailPilot-MCP/0.1 (MTB tour search; https://github.com/klapom/mtb-mcp; "
    "respectful scraping with 4s+ delays)"
)


def _extract_tour_id_from_url(url: str) -> str | None:
    """Extract tour ID from a GPS-Tour.info URL.

    Patterns:
        /de/touren/detail.123456.html -> 123456
        /en/tours/detail.123456.html  -> 123456
    """
    match = re.search(r"detail\.(\d+)\.html", url)
    if match:
        return match.group(1)
    return None


def _parse_distance(text: str) -> float | None:
    """Parse distance text like '45,3 km' to float."""
    match = re.search(r"([\d.,]+)\s*km", text, re.IGNORECASE)
    if match:
        value = match.group(1).replace(",", ".")
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _parse_elevation(text: str) -> float | None:
    """Parse elevation text like '1.200 Hm' or '850 m' to float."""
    match = re.search(r"([\d.]+)\s*(?:Hm|hm|m)", text)
    if match:
        value = match.group(1).replace(".", "")
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _map_difficulty(text: str) -> TourDifficulty | None:
    """Map GPS-Tour.info difficulty text to TourDifficulty."""
    lower = text.lower()
    # Check "extrem"/"expert" before "schwer"/"difficult" since
    # "Extrem schwer" should map to expert, not difficult.
    if "extrem" in lower or "expert" in lower:
        return TourDifficulty.expert
    if "schwer" in lower or "difficult" in lower or "hard" in lower:
        return TourDifficulty.difficult
    if "mittel" in lower or "moderate" in lower:
        return TourDifficulty.moderate
    if "leicht" in lower or "easy" in lower:
        return TourDifficulty.easy
    return None


class GPSTourClient(BaseClient):
    """Client for GPS-Tour.info via SearXNG search + HTML scraping.

    Respects rate limits (4s+ between requests) and uses honest User-Agent.
    """

    def __init__(
        self,
        searxng_url: str = "http://localhost:17888",
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        super().__init__(
            base_url="https://www.gps-tour.info",
            rate_limit=0.25,  # Max 1 request per 4 seconds
            headers={"User-Agent": _GPSTOUR_USER_AGENT},
        )
        # Allow burst of 1 request immediately, then enforce 4s spacing
        self._rate_limiter = TokenBucketRateLimiter(rate=0.25, burst=1.0)
        self._searxng_url = searxng_url
        self._username = username
        self._password = password
        self._session_cookie: str | None = None
        self._searxng_client: httpx.AsyncClient | None = None

    def _get_searxng_client(self) -> httpx.AsyncClient:
        """Return the SearXNG httpx client, creating it lazily if needed."""
        if self._searxng_client is None or self._searxng_client.is_closed:
            self._searxng_client = httpx.AsyncClient(
                base_url=self._searxng_url,
                timeout=30.0,
            )
        return self._searxng_client

    async def search_tours(
        self,
        query: str,
        sport_type: str = "mountainbike",
        limit: int = 10,
    ) -> list[TourSummary]:
        """Search tours via SearXNG meta-search.

        Searches: site:gps-tour.info {sport_type} {query}
        Parses: title, URL, extract tour ID from URL pattern.
        """
        search_query = f"site:gps-tour.info {sport_type} {query}"

        try:
            searxng = self._get_searxng_client()
            response = await searxng.get(
                "/search",
                params={
                    "q": search_query,
                    "format": "json",
                    "engines": "google,bing,duckduckgo",
                },
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()

        except httpx.HTTPError as exc:
            logger.warning("gpstour_searxng_error", error=str(exc))
            return []

        results: list[TourSummary] = []
        search_results = data.get("results", [])

        for item in search_results[:limit]:
            if not isinstance(item, dict):
                continue

            url = item.get("url", "")
            tour_id = _extract_tour_id_from_url(url)
            if not tour_id:
                continue

            title = item.get("title", "Unknown Tour")
            # Clean up title (remove site name suffixes)
            title = re.sub(r"\s*[-|]\s*GPS-Tour\.info.*$", "", title).strip()

            results.append(
                TourSummary(
                    id=tour_id,
                    source=TourSource.gps_tour,
                    name=title or f"GPS-Tour {tour_id}",
                    url=f"https://www.gps-tour.info/de/touren/detail.{tour_id}.html",
                )
            )

        logger.info("gpstour_search_results", query=query, count=len(results))
        return results

    async def get_tour_details(self, tour_id: str) -> TourDetail | None:
        """Scrape tour detail page for metadata.

        URL: /de/touren/detail.{tour_id}.html
        Extracts: description, distance, elevation, difficulty, ratings.
        """
        try:
            html = await self._get_text(f"/de/touren/detail.{tour_id}.html")
        except httpx.HTTPError as exc:
            logger.warning("gpstour_detail_error", tour_id=tour_id, error=str(exc))
            return None

        soup = BeautifulSoup(html, "lxml")

        # Extract tour name from page title or h1
        name = "Unknown Tour"
        h1 = soup.find("h1")
        if h1:
            name = h1.get_text(strip=True)
        elif soup.title:
            name = soup.title.get_text(strip=True)
            name = re.sub(r"\s*[-|]\s*GPS-Tour\.info.*$", "", name).strip()

        # Extract description
        description: str | None = None
        desc_elem = soup.find("div", class_="tour-description")
        if desc_elem is None:
            desc_elem = soup.find("div", {"id": "description"})
        if desc_elem is not None:
            description = desc_elem.get_text(strip=True)

        # Extract metadata from detail table
        distance_km: float | None = None
        elevation_m: float | None = None
        difficulty: TourDifficulty | None = None
        download_count: int | None = None
        rating: float | None = None
        duration_minutes: int | None = None
        region: str | None = None
        start_point: GeoPoint | None = None

        # Look for metadata in table rows or definition lists
        for row in soup.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                label = cells[0].get_text(strip=True).lower()
                value = cells[1].get_text(strip=True)

                if "strecke" in label or "distance" in label or "länge" in label:
                    distance_km = _parse_distance(value)
                elif "höhenmeter" in label or "elevation" in label or "aufstieg" in label:
                    elevation_m = _parse_elevation(value)
                elif "schwierigkeit" in label or "difficulty" in label:
                    difficulty = _map_difficulty(value)
                elif "downloads" in label:
                    match = re.search(r"(\d+)", value)
                    if match:
                        download_count = int(match.group(1))
                elif "bewertung" in label or "rating" in label:
                    match = re.search(r"([\d.,]+)", value)
                    if match:
                        with contextlib.suppress(ValueError):
                            rating = float(match.group(1).replace(",", "."))
                elif "dauer" in label or "duration" in label or "zeit" in label:
                    # Parse duration like "3:30" or "3h 30min"
                    hours_match = re.search(r"(\d+)\s*[:h]\s*(\d+)", value)
                    if hours_match:
                        hours = int(hours_match.group(1))
                        mins = int(hours_match.group(2))
                        duration_minutes = hours * 60 + mins
                elif "region" in label or "gebiet" in label or "ort" in label:
                    region = value

        # Try to extract coordinates from map or meta tags
        for meta in soup.find_all("meta"):
            if meta.get("name") == "geo.position":
                content = str(meta.get("content", ""))
                parts = content.split(";")
                if len(parts) == 2:
                    with contextlib.suppress(ValueError, TypeError):
                        start_point = GeoPoint(
                            lat=float(parts[0].strip()),
                            lon=float(parts[1].strip()),
                        )

        return TourDetail(
            id=tour_id,
            source=TourSource.gps_tour,
            name=name,
            distance_km=distance_km,
            elevation_m=elevation_m,
            difficulty=difficulty,
            region=region,
            url=f"https://www.gps-tour.info/de/touren/detail.{tour_id}.html",
            start_point=start_point,
            description=description,
            duration_minutes=duration_minutes,
            download_count=download_count,
            rating=rating,
        )

    async def download_gpx(self, tour_id: str) -> bytes | None:
        """Download GPX file (requires login).

        1. Login if not authenticated
        2. GET /de/touren/download.{tour_id}.html
        """
        if not self._session_cookie:
            login_ok = await self._login()
            if not login_ok:
                return None

        try:
            gpx_data = await self._get_raw(f"/de/touren/download.{tour_id}.html")
            logger.info("gpstour_gpx_downloaded", tour_id=tour_id, size=len(gpx_data))
            return gpx_data
        except httpx.HTTPError as exc:
            logger.warning("gpstour_gpx_error", tour_id=tour_id, error=str(exc))
            return None

    async def _login(self) -> bool:
        """Login to GPS-Tour.info for GPX downloads."""
        if not self._username or not self._password:
            logger.warning("gpstour_login_missing_credentials")
            return False

        try:
            await self._rate_limiter.acquire()
            client = self._get_client()

            response = await client.post(
                "/de/login.html",
                data={
                    "username": self._username,
                    "password": self._password,
                    "redx_autologin": "1",
                },
                follow_redirects=True,
            )
            response.raise_for_status()

            # Extract session cookie
            cookies = response.cookies
            for name in cookies:
                if "session" in name.lower() or "redx" in name.lower():
                    self._session_cookie = f"{name}={cookies[name]}"
                    break

            if not self._session_cookie:
                # Some sites just set cookies directly on the client
                self._session_cookie = "authenticated"

            logger.info("gpstour_login_success")
            return True

        except httpx.HTTPError as exc:
            logger.warning("gpstour_login_error", error=str(exc))
            return False

    async def close(self) -> None:
        """Close both HTTP clients."""
        await super().close()
        if self._searxng_client is not None and not self._searxng_client.is_closed:
            await self._searxng_client.aclose()
            self._searxng_client = None
