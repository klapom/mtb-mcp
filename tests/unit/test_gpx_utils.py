"""Tests for GPX parsing and writing utilities."""

from __future__ import annotations

from pathlib import Path

import pytest

from mtb_mcp.models.common import GeoPoint
from mtb_mcp.utils.gpx import gpx_distance_km, gpx_elevation_gain, parse_gpx, write_gpx

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SIMPLE_GPX = """\
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test"
     xmlns="http://www.topografix.com/GPX/1/1">
  <trk>
    <name>Test Track</name>
    <trkseg>
      <trkpt lat="49.5964" lon="11.0042">
        <ele>280</ele>
      </trkpt>
      <trkpt lat="49.5980" lon="11.0050">
        <ele>290</ele>
      </trkpt>
      <trkpt lat="49.5995" lon="11.0070">
        <ele>285</ele>
      </trkpt>
    </trkseg>
  </trk>
</gpx>
"""

ROUTE_GPX = """\
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test"
     xmlns="http://www.topografix.com/GPX/1/1">
  <rte>
    <name>Test Route</name>
    <rtept lat="49.5964" lon="11.0042">
      <ele>280</ele>
    </rtept>
    <rtept lat="49.5980" lon="11.0050">
      <ele>290</ele>
    </rtept>
  </rte>
</gpx>
"""

WAYPOINT_GPX = """\
<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="test"
     xmlns="http://www.topografix.com/GPX/1/1">
  <wpt lat="49.5964" lon="11.0042">
    <ele>280</ele>
    <name>Start</name>
  </wpt>
  <wpt lat="49.5980" lon="11.0050">
    <ele>290</ele>
    <name>End</name>
  </wpt>
</gpx>
"""


FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "gpx_samples"


# ---------------------------------------------------------------------------
# parse_gpx tests
# ---------------------------------------------------------------------------


class TestParseGpx:
    """Tests for GPX parsing."""

    def test_parse_track(self) -> None:
        """Parse a GPX string with track points."""
        points = parse_gpx(SIMPLE_GPX)
        assert len(points) == 3
        assert all(isinstance(p, GeoPoint) for p in points)

    def test_parse_first_point(self) -> None:
        """First parsed point should match the GPX data."""
        points = parse_gpx(SIMPLE_GPX)
        assert points[0].lat == pytest.approx(49.5964)
        assert points[0].lon == pytest.approx(11.0042)
        assert points[0].ele == pytest.approx(280.0)

    def test_parse_bytes(self) -> None:
        """Should handle bytes input."""
        points = parse_gpx(SIMPLE_GPX.encode("utf-8"))
        assert len(points) == 3

    def test_parse_route(self) -> None:
        """Should parse route points when no tracks exist."""
        points = parse_gpx(ROUTE_GPX)
        assert len(points) == 2

    def test_parse_waypoints(self) -> None:
        """Should fall back to waypoints when no tracks or routes exist."""
        points = parse_gpx(WAYPOINT_GPX)
        assert len(points) == 2

    def test_parse_fixture_file(self) -> None:
        """Parse the simple_track.gpx fixture file."""
        gpx_file = FIXTURE_DIR / "simple_track.gpx"
        assert gpx_file.exists(), f"Fixture file not found: {gpx_file}"

        gpx_data = gpx_file.read_text(encoding="utf-8")
        points = parse_gpx(gpx_data)
        assert len(points) == 10
        # First and last point should be the same (loop)
        assert points[0].lat == pytest.approx(points[-1].lat)
        assert points[0].lon == pytest.approx(points[-1].lon)

    def test_parse_empty_gpx(self) -> None:
        """Empty GPX should return an empty list."""
        empty_gpx = '<?xml version="1.0"?><gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1"></gpx>'
        points = parse_gpx(empty_gpx)
        assert points == []


# ---------------------------------------------------------------------------
# write_gpx tests
# ---------------------------------------------------------------------------


class TestWriteGpx:
    """Tests for GPX writing."""

    def test_write_produces_xml(self) -> None:
        """write_gpx should produce valid XML."""
        points = [
            GeoPoint(lat=49.5964, lon=11.0042, ele=280.0),
            GeoPoint(lat=49.5980, lon=11.0050, ele=290.0),
        ]
        xml = write_gpx(points, name="Test")
        assert '<?xml' in xml
        assert '<gpx' in xml
        assert '<trk>' in xml

    def test_roundtrip(self) -> None:
        """Write points to GPX and parse them back."""
        original = [
            GeoPoint(lat=49.5964, lon=11.0042, ele=280.0),
            GeoPoint(lat=49.5980, lon=11.0050, ele=290.0),
            GeoPoint(lat=49.5995, lon=11.0070, ele=285.0),
        ]

        xml = write_gpx(original, name="Roundtrip Test")
        parsed = parse_gpx(xml)

        assert len(parsed) == len(original)
        for orig, p in zip(original, parsed, strict=True):
            assert p.lat == pytest.approx(orig.lat, abs=1e-4)
            assert p.lon == pytest.approx(orig.lon, abs=1e-4)
            assert p.ele is not None
            assert orig.ele is not None
            assert p.ele == pytest.approx(orig.ele, abs=0.1)

    def test_write_without_elevation(self) -> None:
        """Points without elevation should still produce valid GPX."""
        points = [
            GeoPoint(lat=49.5964, lon=11.0042),
            GeoPoint(lat=49.5980, lon=11.0050),
        ]
        xml = write_gpx(points)
        assert '<gpx' in xml
        # Should be parseable
        parsed = parse_gpx(xml)
        assert len(parsed) == 2

    def test_custom_name(self) -> None:
        """Track name should appear in the output."""
        points = [GeoPoint(lat=49.59, lon=11.00)]
        xml = write_gpx(points, name="Erlangen Trail")
        assert "Erlangen Trail" in xml


# ---------------------------------------------------------------------------
# gpx_distance_km tests
# ---------------------------------------------------------------------------


class TestGpxDistanceKm:
    """Tests for distance calculation from GeoPoints."""

    def test_empty_list(self) -> None:
        """Empty list should return 0."""
        assert gpx_distance_km([]) == 0.0

    def test_single_point(self) -> None:
        """Single point should return 0."""
        assert gpx_distance_km([GeoPoint(lat=49.59, lon=11.00)]) == 0.0

    def test_two_points(self) -> None:
        """Distance between two known points."""
        points = [
            GeoPoint(lat=49.5964, lon=11.0042),
            GeoPoint(lat=49.4539, lon=11.0775),
        ]
        dist = gpx_distance_km(points)
        # Erlangen to Nuernberg ~17 km
        assert 15.0 < dist < 19.0

    def test_fixture_track_distance(self) -> None:
        """Simple fixture track should have a reasonable distance."""
        gpx_data = (FIXTURE_DIR / "simple_track.gpx").read_text(encoding="utf-8")
        points = parse_gpx(gpx_data)
        dist = gpx_distance_km(points)
        # Short loop around Erlangen, should be a few km
        assert 1.0 < dist < 10.0


# ---------------------------------------------------------------------------
# gpx_elevation_gain tests
# ---------------------------------------------------------------------------


class TestGpxElevationGain:
    """Tests for elevation gain calculation."""

    def test_uphill_only(self) -> None:
        """Strictly increasing elevations should sum all differences."""
        points = [
            GeoPoint(lat=49.59, lon=11.00, ele=100.0),
            GeoPoint(lat=49.60, lon=11.01, ele=150.0),
            GeoPoint(lat=49.61, lon=11.02, ele=200.0),
        ]
        assert gpx_elevation_gain(points) == pytest.approx(100.0)

    def test_downhill_only(self) -> None:
        """Strictly decreasing elevations should yield 0 gain."""
        points = [
            GeoPoint(lat=49.59, lon=11.00, ele=200.0),
            GeoPoint(lat=49.60, lon=11.01, ele=150.0),
            GeoPoint(lat=49.61, lon=11.02, ele=100.0),
        ]
        assert gpx_elevation_gain(points) == pytest.approx(0.0)

    def test_mixed(self) -> None:
        """Mixed up/down should only sum the uphill segments."""
        points = [
            GeoPoint(lat=49.59, lon=11.00, ele=100.0),
            GeoPoint(lat=49.60, lon=11.01, ele=200.0),  # +100
            GeoPoint(lat=49.61, lon=11.02, ele=150.0),  # -50 (ignored)
            GeoPoint(lat=49.62, lon=11.03, ele=250.0),  # +100
        ]
        assert gpx_elevation_gain(points) == pytest.approx(200.0)

    def test_no_elevation(self) -> None:
        """Points without elevation should yield 0."""
        points = [
            GeoPoint(lat=49.59, lon=11.00),
            GeoPoint(lat=49.60, lon=11.01),
        ]
        assert gpx_elevation_gain(points) == pytest.approx(0.0)

    def test_fixture_track_elevation(self) -> None:
        """Simple fixture track should have some elevation gain."""
        gpx_data = (FIXTURE_DIR / "simple_track.gpx").read_text(encoding="utf-8")
        points = parse_gpx(gpx_data)
        gain = gpx_elevation_gain(points)
        # The fixture has climbs from 280 to 340, then down, so gain > 0
        assert gain > 0.0

    def test_empty_list(self) -> None:
        """Empty list should return 0."""
        assert gpx_elevation_gain([]) == pytest.approx(0.0)
