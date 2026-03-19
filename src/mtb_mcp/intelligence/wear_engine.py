"""Component wear calculation engine.

Pure-function algorithm: no I/O, no side effects.
Calculates effective km, wear percentage, and service status
based on terrain, weather, and intensity modifiers.
"""

from __future__ import annotations

from datetime import date

TERRAIN_MODIFIERS: dict[str, float] = {
    "S0": 0.8,
    "S1": 1.0,
    "S2": 1.2,
    "S3": 1.5,
    "S4": 2.0,
    "S5": 2.0,
    "S6": 2.0,
}

WEATHER_MODIFIERS: dict[str, float] = {
    "dry": 1.0,
    "damp": 1.1,
    "wet": 1.3,
    "muddy": 1.8,
}

# (max_watts_exclusive, modifier)
INTENSITY_BRACKETS: list[tuple[float, float]] = [
    (150.0, 0.9),
    (250.0, 1.0),
    (350.0, 1.1),
    (float("inf"), 1.3),
]

# Service intervals: (effective_km or None, hours or None, months or None)
SERVICE_INTERVALS: dict[str, tuple[float | None, float | None, int | None]] = {
    "chain": (1500.0, None, None),
    "cassette": (4000.0, None, None),
    "brake_pads_front": (2500.0, None, None),
    "brake_pads_rear": (2500.0, None, None),
    "tire_front": (3000.0, None, None),
    "tire_rear": (3000.0, None, None),
    "fork": (None, 200.0, None),
    "shock": (None, 200.0, None),
    "brake_fluid": (None, None, 12),
    "tubeless_sealant": (None, None, 6),
    "bottom_bracket": (5000.0, None, None),
}


def _get_intensity_modifier(avg_power_watts: float) -> float:
    """Return the intensity modifier for the given average power."""
    for max_watts, modifier in INTENSITY_BRACKETS:
        if avg_power_watts < max_watts:
            return modifier
    return 1.3  # pragma: no cover — fallback for safety


def calculate_effective_km(
    actual_km: float,
    terrain: str = "S1",
    weather: str = "dry",
    avg_power_watts: float = 200.0,
) -> float:
    """Calculate effective km with terrain, weather, and intensity modifiers.

    Args:
        actual_km: Actual distance ridden in km.
        terrain: Trail difficulty scale (S0-S6).
        weather: Weather condition (dry, damp, wet, muddy).
        avg_power_watts: Average power output in watts.

    Returns:
        Effective km adjusted by all modifiers.
    """
    terrain_mod = TERRAIN_MODIFIERS.get(terrain, 1.0)
    weather_mod = WEATHER_MODIFIERS.get(weather, 1.0)
    intensity_mod = _get_intensity_modifier(avg_power_watts)

    return actual_km * terrain_mod * weather_mod * intensity_mod


def calculate_wear_pct(
    effective_km: float,
    hours: float,
    installed_date: date,
    component_type: str,
    reference_date: date | None = None,
) -> float:
    """Calculate wear percentage (0-100+) based on the most relevant interval.

    For km-based components, uses effective_km / service_interval_km.
    For hour-based components, uses hours / service_interval_hours.
    For time-based components, uses elapsed_months / service_interval_months.
    If multiple intervals apply, returns the maximum wear percentage.

    Args:
        effective_km: Accumulated effective kilometres since install.
        hours: Accumulated riding hours since install.
        installed_date: Date the component was installed.
        component_type: Component type string matching SERVICE_INTERVALS keys.
        reference_date: Date to calculate against (defaults to today).

    Returns:
        Wear percentage (0-100+). Values above 100 mean overdue.
    """
    if reference_date is None:
        reference_date = date.today()

    interval = SERVICE_INTERVALS.get(component_type)
    if interval is None:
        return 0.0

    interval_km, interval_hours, interval_months = interval
    wear_pcts: list[float] = []

    if interval_km is not None and interval_km > 0:
        wear_pcts.append((effective_km / interval_km) * 100.0)

    if interval_hours is not None and interval_hours > 0:
        wear_pcts.append((hours / interval_hours) * 100.0)

    if interval_months is not None and interval_months > 0:
        # Calculate months elapsed
        months_elapsed = (
            (reference_date.year - installed_date.year) * 12
            + (reference_date.month - installed_date.month)
        )
        # Add partial month from day difference
        if reference_date.day < installed_date.day:
            months_elapsed -= 1
        wear_pcts.append((max(0, months_elapsed) / interval_months) * 100.0)

    if not wear_pcts:
        return 0.0

    return max(wear_pcts)


def get_wear_status(
    effective_km: float,
    hours: float,
    installed_date: date,
    component_type: str,
    reference_date: date | None = None,
) -> str:
    """Return wear status label based on wear percentage.

    Args:
        effective_km: Accumulated effective kilometres since install.
        hours: Accumulated riding hours since install.
        installed_date: Date the component was installed.
        component_type: Component type string.
        reference_date: Date to calculate against (defaults to today).

    Returns:
        Status string: "good" (<60%), "warning" (60-85%),
        "critical" (85-100%), "overdue" (>100%).
    """
    pct = calculate_wear_pct(
        effective_km, hours, installed_date, component_type, reference_date,
    )

    if pct > 100.0:
        return "overdue"
    if pct >= 85.0:
        return "critical"
    if pct >= 60.0:
        return "warning"
    return "good"


def km_remaining(effective_km: float, component_type: str) -> float | None:
    """Estimate remaining effective km before service is needed.

    Only applicable for km-based service intervals.

    Args:
        effective_km: Current accumulated effective km.
        component_type: Component type string.

    Returns:
        Remaining km, or None if the component has no km-based interval.
    """
    interval = SERVICE_INTERVALS.get(component_type)
    if interval is None:
        return None

    interval_km = interval[0]
    if interval_km is None:
        return None

    return max(0.0, interval_km - effective_km)
