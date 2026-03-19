"""Tests for mtb_mcp.utils.units."""

from __future__ import annotations

import pytest

from mtb_mcp.utils.units import (
    bar_to_psi,
    celsius_to_fahrenheit,
    fahrenheit_to_celsius,
    feet_to_meters,
    km_to_miles,
    kmh_to_mps,
    meters_to_feet,
    miles_to_km,
    mps_to_kmh,
    psi_to_bar,
)


class TestDistanceConversions:
    """Test km/miles and meters/feet conversions."""

    def test_km_to_miles(self) -> None:
        assert km_to_miles(1.609344) == pytest.approx(1.0)

    def test_miles_to_km(self) -> None:
        assert miles_to_km(1.0) == pytest.approx(1.609344)

    def test_km_miles_roundtrip(self) -> None:
        assert miles_to_km(km_to_miles(42.195)) == pytest.approx(42.195)

    def test_meters_to_feet(self) -> None:
        assert meters_to_feet(1.0) == pytest.approx(3.28084)

    def test_feet_to_meters(self) -> None:
        assert feet_to_meters(3.28084) == pytest.approx(1.0)

    def test_meters_feet_roundtrip(self) -> None:
        assert feet_to_meters(meters_to_feet(1000.0)) == pytest.approx(1000.0)

    def test_zero_distance(self) -> None:
        assert km_to_miles(0.0) == pytest.approx(0.0)
        assert meters_to_feet(0.0) == pytest.approx(0.0)


class TestPressureConversions:
    """Test bar/PSI conversions."""

    def test_bar_to_psi(self) -> None:
        assert bar_to_psi(1.0) == pytest.approx(14.5038)

    def test_psi_to_bar(self) -> None:
        assert psi_to_bar(14.5038) == pytest.approx(1.0)

    def test_bar_psi_roundtrip(self) -> None:
        # Typical MTB tire pressure: 1.8 bar
        assert psi_to_bar(bar_to_psi(1.8)) == pytest.approx(1.8)

    def test_zero_pressure(self) -> None:
        assert bar_to_psi(0.0) == pytest.approx(0.0)


class TestTemperatureConversions:
    """Test Celsius/Fahrenheit conversions."""

    def test_celsius_to_fahrenheit_freezing(self) -> None:
        assert celsius_to_fahrenheit(0.0) == pytest.approx(32.0)

    def test_celsius_to_fahrenheit_boiling(self) -> None:
        assert celsius_to_fahrenheit(100.0) == pytest.approx(212.0)

    def test_fahrenheit_to_celsius_freezing(self) -> None:
        assert fahrenheit_to_celsius(32.0) == pytest.approx(0.0)

    def test_fahrenheit_to_celsius_boiling(self) -> None:
        assert fahrenheit_to_celsius(212.0) == pytest.approx(100.0)

    def test_celsius_fahrenheit_roundtrip(self) -> None:
        assert fahrenheit_to_celsius(celsius_to_fahrenheit(20.0)) == pytest.approx(20.0)

    def test_negative_celsius(self) -> None:
        assert celsius_to_fahrenheit(-40.0) == pytest.approx(-40.0)


class TestSpeedConversions:
    """Test m/s and km/h conversions."""

    def test_mps_to_kmh(self) -> None:
        assert mps_to_kmh(1.0) == pytest.approx(3.6)

    def test_kmh_to_mps(self) -> None:
        assert kmh_to_mps(3.6) == pytest.approx(1.0)

    def test_mps_kmh_roundtrip(self) -> None:
        # Typical MTB speed: 20 km/h
        assert mps_to_kmh(kmh_to_mps(20.0)) == pytest.approx(20.0)

    def test_zero_speed(self) -> None:
        assert mps_to_kmh(0.0) == pytest.approx(0.0)
        assert kmh_to_mps(0.0) == pytest.approx(0.0)
