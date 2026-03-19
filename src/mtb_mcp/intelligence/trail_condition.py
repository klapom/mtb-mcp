"""Trail condition estimation based on rainfall and surface type.

Pure-function algorithm: no I/O, no side effects.
Input: surface type + hourly rain history + current temperature.
Output: (condition_status, confidence, reasoning).
"""

from __future__ import annotations

import math

from mtb_mcp.models.trail import TrailConditionStatus, TrailSurface

ABSORPTION_RATES: dict[str, float] = {
    "asphalt": 0.0,
    "gravel": 0.3,
    "dirt": 0.8,
    "roots": 0.9,
    "grass": 0.7,
    "rock": 0.1,
    "sand": 0.5,
}

DRYING_CONSTANTS: dict[str, float] = {  # hours for 50 % drying
    "asphalt": 2.0,
    "gravel": 6.0,
    "dirt": 24.0,
    "roots": 36.0,
    "grass": 18.0,
    "rock": 4.0,
    "sand": 8.0,
}


def estimate_trail_condition(
    surface: TrailSurface | str,
    hourly_rain_mm: list[float],
    current_temp_c: float = 15.0,
) -> tuple[TrailConditionStatus, str, str]:
    """Estimate trail condition from rainfall history and surface type.

    Args:
        surface: Trail surface type (enum or raw string).
        hourly_rain_mm: Hourly precipitation in mm, **newest hour first**.
            Typically 48-72 entries covering the recent past.
        current_temp_c: Current temperature in Celsius.

    Returns:
        A tuple of ``(condition, confidence, reasoning)`` where *condition*
        is a :class:`TrailConditionStatus`, *confidence* is one of
        ``"high"``, ``"medium-high"``, ``"medium"``, and *reasoning* is a
        human-readable explanation.
    """
    # --- Frozen check (takes precedence) ---
    if current_temp_c < 0:
        return (
            TrailConditionStatus.frozen,
            "high",
            f"Temperature {current_temp_c:.1f}\u00b0C \u2014 frozen ground",
        )

    # --- Resolve surface key ---
    surface_key = surface.value if isinstance(surface, TrailSurface) else surface
    absorption = ABSORPTION_RATES.get(surface_key, 0.5)
    drying = DRYING_CONSTANTS.get(surface_key, 12.0)

    # --- Calculate absorbed water ---
    absorbed = 0.0
    for h, rain_mm in enumerate(hourly_rain_mm):
        absorbed += rain_mm * absorption * math.exp(-h / drying)

    # --- Classify ---
    if absorbed < 1.0:
        return (
            TrailConditionStatus.dry,
            "high",
            f"Low absorbed water ({absorbed:.1f}mm) on {surface_key}",
        )
    if absorbed < 3.0:
        return (
            TrailConditionStatus.damp,
            "medium-high",
            f"Moderate moisture ({absorbed:.1f}mm) on {surface_key}",
        )
    if absorbed < 8.0:
        return (
            TrailConditionStatus.wet,
            "medium",
            f"Significant moisture ({absorbed:.1f}mm) on {surface_key}",
        )
    return (
        TrailConditionStatus.muddy,
        "medium",
        f"High absorbed water ({absorbed:.1f}mm) on {surface_key}",
    )
