"""eBike range calculator based on battery, elevation, and rider weight.

Pure-function algorithm: no I/O, no side effects.
Calculates estimated battery consumption for a given route based on:
- Battery capacity and current charge
- Elevation profile (grade-based consumption model)
- Rider + bike weight vs. reference 90 kg
- Assist mode power factor
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from mtb_mcp.models.common import GeoPoint
from mtb_mcp.utils.geo import haversine

# Reference weight in kg (consumption model calibrated for 90 kg total)
_REFERENCE_WEIGHT_KG = 90.0

# Base consumption in Wh per km on flat terrain in Eco mode
_BASE_CONSUMPTION_WH_KM = 8.0

# Minimum grade factor (recuperation on steep downhill)
_MIN_GRADE_FACTOR = 0.2

# Grade threshold for recuperation mode (below -3%)
_RECUPERATION_GRADE_THRESHOLD = -0.03

# Grade factor scaling constant
_GRADE_FACTOR_SCALE = 12.0

# Safety margin (10%)
_SAFETY_MARGIN = 0.10

ASSIST_FACTORS: dict[str, float] = {
    "eco": 1.0,
    "tour": 1.3,
    "emtb": 1.6,
    "turbo": 2.2,
}


@dataclass
class EBikeRangeInput:
    """Input parameters for eBike range calculation."""

    battery_wh: float  # e.g. 625 for Bosch PowerTube 625
    charge_pct: float  # 0-100
    rider_kg: float = 80.0
    bike_kg: float = 23.0
    assist_mode: str = "tour"  # eco, tour, emtb, turbo


@dataclass
class EBikeRangeResult:
    """Result of eBike range calculation."""

    can_finish: bool
    estimated_consumption_wh: float
    available_wh: float
    remaining_wh: float
    remaining_pct: float
    safety_margin_pct: float
    consumption_per_km: float
    estimated_range_km: float  # How far you could still go


def _segment_consumption(
    distance_km: float,
    grade: float,
    total_weight_kg: float,
) -> float:
    """Calculate energy consumption for a single route segment.

    Args:
        distance_km: Horizontal distance of the segment in km.
        grade: Grade as a decimal (e.g. 0.05 for 5%).
        total_weight_kg: Combined rider + bike weight in kg.

    Returns:
        Energy consumption in Wh for this segment (before assist factor).
    """
    if distance_km <= 0:
        return 0.0

    # Apply recuperation for steep downhills
    if grade < _RECUPERATION_GRADE_THRESHOLD:
        grade_factor = _MIN_GRADE_FACTOR
    else:
        grade_factor = 1.0 + (grade * _GRADE_FACTOR_SCALE)
        # Floor at minimum factor to avoid negative consumption
        grade_factor = max(_MIN_GRADE_FACTOR, grade_factor)

    weight_factor = total_weight_kg / _REFERENCE_WEIGHT_KG

    return distance_km * _BASE_CONSUMPTION_WH_KM * grade_factor * weight_factor


def calculate_range(
    range_input: EBikeRangeInput,
    elevation_points: list[GeoPoint],
) -> EBikeRangeResult:
    """Calculate if battery is sufficient for a given route.

    For each segment between consecutive points:
    1. Calculate grade from elevation change / horizontal distance
    2. Apply grade factor (uphill costs more, downhill recuperates slightly)
    3. Weight factor based on total rider+bike weight vs reference 90 kg
    4. Sum up consumption, apply assist mode factor
    5. Compare against available battery with 10% safety margin

    Args:
        range_input: Battery, weight, and assist mode parameters.
        elevation_points: Route points with lat, lon, and elevation.

    Returns:
        EBikeRangeResult with consumption estimates and can_finish flag.
    """
    total_weight_kg = range_input.rider_kg + range_input.bike_kg
    assist_factor = ASSIST_FACTORS.get(range_input.assist_mode, ASSIST_FACTORS["tour"])

    total_consumption_wh = 0.0
    total_distance_km = 0.0

    for i in range(1, len(elevation_points)):
        prev = elevation_points[i - 1]
        curr = elevation_points[i]

        # Horizontal distance via haversine
        dist_km = haversine(prev.lat, prev.lon, curr.lat, curr.lon)
        if dist_km < 1e-6:
            continue

        total_distance_km += dist_km

        # Calculate grade
        ele_prev = prev.ele if prev.ele is not None else 0.0
        ele_curr = curr.ele if curr.ele is not None else 0.0
        ele_change_m = ele_curr - ele_prev
        horizontal_m = dist_km * 1000.0

        grade = ele_change_m / horizontal_m if horizontal_m > 0 else 0.0

        segment_wh = _segment_consumption(dist_km, grade, total_weight_kg)
        total_consumption_wh += segment_wh

    # Apply assist mode factor
    total_consumption_wh *= assist_factor

    # Available energy
    available_wh = range_input.battery_wh * range_input.charge_pct / 100.0

    # Check if we can finish with safety margin
    required_with_margin = total_consumption_wh * (1.0 + _SAFETY_MARGIN)
    can_finish = available_wh > required_with_margin

    remaining_wh = available_wh - total_consumption_wh
    remaining_pct = (remaining_wh / range_input.battery_wh * 100.0) if range_input.battery_wh > 0 else 0.0  # noqa: E501

    # Consumption per km
    consumption_per_km = (
        total_consumption_wh / total_distance_km if total_distance_km > 0 else 0.0
    )

    # Estimated range from remaining battery
    estimated_range_km = (
        remaining_wh / consumption_per_km if consumption_per_km > 0 else math.inf
    )

    return EBikeRangeResult(
        can_finish=can_finish,
        estimated_consumption_wh=round(total_consumption_wh, 1),
        available_wh=round(available_wh, 1),
        remaining_wh=round(remaining_wh, 1),
        remaining_pct=round(remaining_pct, 1),
        safety_margin_pct=round(_SAFETY_MARGIN * 100, 1),
        consumption_per_km=round(consumption_per_km, 1),
        estimated_range_km=round(estimated_range_km, 1),
    )


def estimate_flat_range_km(
    battery_wh: float,
    charge_pct: float,
    assist_mode: str = "tour",
    rider_kg: float = 80.0,
    bike_kg: float = 23.0,
) -> float:
    """Quick flat-terrain range estimate without elevation profile.

    Uses base consumption rate with weight and assist mode adjustments.

    Args:
        battery_wh: Battery capacity in Wh (e.g. 625).
        charge_pct: Current charge percentage (0-100).
        assist_mode: One of eco, tour, emtb, turbo.
        rider_kg: Rider weight in kg.
        bike_kg: Bike weight in kg.

    Returns:
        Estimated range in km on flat terrain.
    """
    available_wh = battery_wh * charge_pct / 100.0
    assist_factor = ASSIST_FACTORS.get(assist_mode, ASSIST_FACTORS["tour"])
    total_weight_kg = rider_kg + bike_kg
    weight_factor = total_weight_kg / _REFERENCE_WEIGHT_KG

    consumption_per_km = _BASE_CONSUMPTION_WH_KM * assist_factor * weight_factor

    if consumption_per_km <= 0:
        return 0.0

    return round(available_wh / consumption_per_km, 1)
