"""Shared fixtures for API integration tests."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from mtb_mcp.config import Settings
from mtb_mcp.models.common import GeoPoint
from mtb_mcp.models.tour import TourDetail, TourDifficulty, TourSource, TourSummary
from mtb_mcp.models.trail import MTBScale, Trail, TrailSurface
from mtb_mcp.models.weather import (
    HourlyForecast,
    RainHistory,
    RainRadar,
    WeatherAlert,
    WeatherCondition,
    WeatherForecast,
)
from mtb_mcp.storage.database import Database

# All modules that import get_cached_settings via
# ``from mtb_mcp.api.deps import get_cached_settings``
_SETTINGS_PATCH_TARGETS = [
    "mtb_mcp.api.deps.get_cached_settings",
    "mtb_mcp.api.routes.bikes.get_cached_settings",
    "mtb_mcp.api.routes.dashboard.get_cached_settings",
    "mtb_mcp.api.routes.safety.get_cached_settings",
    "mtb_mcp.api.routes.tours.get_cached_settings",
    "mtb_mcp.api.routes.training.get_cached_settings",
    "mtb_mcp.api.routes.system.get_cached_settings",
    "mtb_mcp.api.routes.strava.get_cached_settings",
    "mtb_mcp.api.routes.routing.get_cached_settings",
]


# ---------------------------------------------------------------------------
# Test Settings — override to use tmp_path for SQLite
# ---------------------------------------------------------------------------


def _make_test_settings(tmp_path: Path) -> Settings:
    """Create Settings pointing at a temporary database."""
    db_path = tmp_path / "test.db"
    return Settings(
        log_level="DEBUG",
        data_dir=str(tmp_path),
        db_path=str(db_path),
        home_lat=49.59,
        home_lon=11.00,
        komoot_email="test@example.com",
        komoot_password="secret",
        searxng_url="http://localhost:17888",
        strava_access_token=None,
    )


# ---------------------------------------------------------------------------
# API client fixture — patches get_cached_settings everywhere so DB routes
# use tmp_path instead of the real ~/.mtb-mcp/mtb.db
# ---------------------------------------------------------------------------


def _apply_settings_patches(test_settings: Settings):
    """Return a combined context manager that patches get_cached_settings in
    every module that imports it."""
    import contextlib

    @contextlib.contextmanager
    def _combined():
        patches = [
            patch(target, return_value=test_settings)
            for target in _SETTINGS_PATCH_TARGETS
        ]
        for p in patches:
            p.start()
        try:
            yield
        finally:
            for p in patches:
                p.stop()

    return _combined()


@pytest.fixture
async def api_client(tmp_path: Path) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client wired to the FastAPI app with a temp DB."""
    test_settings = _make_test_settings(tmp_path)

    with _apply_settings_patches(test_settings):
        from mtb_mcp.api.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


@pytest.fixture
async def api_client_with_db(tmp_path: Path) -> AsyncGenerator[AsyncClient, None]:
    """API client with an initialised database (migrations run)."""
    test_settings = _make_test_settings(tmp_path)

    # Pre-initialise the database so tables exist for bikes, safety, training
    db = Database(test_settings.resolved_db_path)
    await db.initialize()
    await db.close()

    with _apply_settings_patches(test_settings):
        from mtb_mcp.api.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            yield client


# ---------------------------------------------------------------------------
# Weather mock data factories
# ---------------------------------------------------------------------------


def make_hourly_forecast(
    hours: int = 3,
    temp_c: float = 18.0,
) -> WeatherForecast:
    """Build a minimal WeatherForecast with *hours* entries."""
    now = datetime.now(tz=timezone.utc)
    entries = []
    for i in range(hours):
        entries.append(
            HourlyForecast(
                time=now.replace(hour=(now.hour + i) % 24),
                temp_c=temp_c + i,
                wind_speed_kmh=10.0,
                wind_gust_kmh=20.0,
                precipitation_mm=0.0,
                precipitation_probability=10.0,
                humidity_pct=55.0,
                condition=WeatherCondition.clear,
            )
        )
    return WeatherForecast(
        location_name="Test Station",
        lat=49.59,
        lon=11.00,
        hours=entries,
        generated_at=now,
    )


def make_rain_radar() -> RainRadar:
    return RainRadar(
        lat=49.59,
        lon=11.00,
        rain_next_60min=[0.0] * 12,
        rain_approaching=False,
        eta_minutes=None,
    )


def make_rain_history() -> RainHistory:
    return RainHistory(
        lat=49.59,
        lon=11.00,
        total_mm_48h=2.5,
        hourly_mm=[0.0] * 48,
        last_rain_hours_ago=12.0,
    )


def make_weather_alerts() -> list[WeatherAlert]:
    now = datetime.now(tz=timezone.utc)
    return [
        WeatherAlert(
            event="THUNDERSTORM",
            severity="moderate",
            headline="Gewitter am Nachmittag",
            description="Gewitterwarnung Stufe 2",
            onset=now,
            expires=now.replace(hour=23),
        )
    ]


# ---------------------------------------------------------------------------
# Trail mock data
# ---------------------------------------------------------------------------


def make_trail_list() -> list[Trail]:
    return [
        Trail(
            osm_id=12345,
            name="Flowtrail Erlangen",
            mtb_scale=MTBScale.S2,
            surface=TrailSurface.dirt,
            length_m=3200.0,
            geometry=[GeoPoint(lat=49.59, lon=11.00, ele=300.0)],
        ),
        Trail(
            osm_id=67890,
            name="Rosskopf Loop",
            mtb_scale=MTBScale.S1,
            surface=TrailSurface.gravel,
            length_m=5100.0,
            geometry=[GeoPoint(lat=49.60, lon=11.01, ele=350.0)],
        ),
    ]


def make_trail_detail() -> Trail:
    return Trail(
        osm_id=12345,
        name="Flowtrail Erlangen",
        mtb_scale=MTBScale.S2,
        surface=TrailSurface.dirt,
        length_m=3200.0,
        geometry=[
            GeoPoint(lat=49.590, lon=11.000, ele=300.0),
            GeoPoint(lat=49.591, lon=11.001, ele=320.0),
            GeoPoint(lat=49.592, lon=11.002, ele=310.0),
        ],
    )


# ---------------------------------------------------------------------------
# Tour mock data
# ---------------------------------------------------------------------------


def make_tour_summaries() -> list[TourSummary]:
    return [
        TourSummary(
            id="komoot-1234",
            source=TourSource.komoot,
            name="Rund um die Burg",
            distance_km=42.0,
            elevation_m=850.0,
            difficulty=TourDifficulty.moderate,
            region="Fränkische Schweiz",
            url="https://www.komoot.com/tour/1234",
        ),
    ]


def make_tour_detail() -> TourDetail:
    return TourDetail(
        id="komoot-1234",
        source=TourSource.komoot,
        name="Rund um die Burg",
        distance_km=42.0,
        elevation_m=850.0,
        difficulty=TourDifficulty.moderate,
        region="Fränkische Schweiz",
        url="https://www.komoot.com/tour/1234",
        description="Schöne Rundtour",
        duration_minutes=240,
        surfaces=["dirt", "gravel"],
        waypoints=[GeoPoint(lat=49.7, lon=11.1)],
    )


def make_gpstour_detail() -> TourDetail:
    return TourDetail(
        id="gps-5678",
        source=TourSource.gps_tour,
        name="Altmühltal Classic",
        distance_km=35.0,
        elevation_m=620.0,
        difficulty=TourDifficulty.easy,
        region="Altmühltal",
        url="https://www.gps-tour.info/tour/5678",
        description="Gemütliche Tour",
        duration_minutes=180,
    )
