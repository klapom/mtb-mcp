"""Unit conversion utilities for MTB-related measurements."""

from __future__ import annotations

# Distance
_KM_PER_MILE = 1.609344
_FEET_PER_METER = 3.28084

# Pressure
_PSI_PER_BAR = 14.5038

# Speed
_KMH_PER_MPS = 3.6


def km_to_miles(km: float) -> float:
    """Convert kilometers to miles."""
    return km / _KM_PER_MILE


def miles_to_km(miles: float) -> float:
    """Convert miles to kilometers."""
    return miles * _KM_PER_MILE


def meters_to_feet(m: float) -> float:
    """Convert meters to feet."""
    return m * _FEET_PER_METER


def feet_to_meters(ft: float) -> float:
    """Convert feet to meters."""
    return ft / _FEET_PER_METER


def bar_to_psi(bar: float) -> float:
    """Convert bar to PSI."""
    return bar * _PSI_PER_BAR


def psi_to_bar(psi: float) -> float:
    """Convert PSI to bar."""
    return psi / _PSI_PER_BAR


def celsius_to_fahrenheit(c: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return c * 9.0 / 5.0 + 32.0


def fahrenheit_to_celsius(f: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return (f - 32.0) * 5.0 / 9.0


def mps_to_kmh(mps: float) -> float:
    """Convert meters per second to kilometers per hour."""
    return mps * _KMH_PER_MPS


def kmh_to_mps(kmh: float) -> float:
    """Convert kilometers per hour to meters per second."""
    return kmh / _KMH_PER_MPS
