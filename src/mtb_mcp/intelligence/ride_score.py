"""Ride Score algorithm -- 'Should I ride today?' (0-100).

Pure-function algorithm: no I/O, no side effects.
Score breakdown:
    weather  0-40
    trail    0-30
    wind     0-15
    daylight 0-15
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RideScoreInput:
    """All inputs needed to compute a ride score."""

    temp_c: float
    wind_speed_kmh: float
    wind_gust_kmh: float = 0.0
    precipitation_probability: float = 0.0  # 0-100
    precipitation_mm: float = 0.0  # expected in ride window
    humidity_pct: float = 50.0
    trail_condition: str = "dry"  # dry | damp | wet | muddy | frozen
    ride_start: datetime | None = None
    ride_duration_hours: float = 2.0
    sunrise: datetime | None = None
    sunset: datetime | None = None


@dataclass
class RideScoreResult:
    """Result of the ride-score calculation."""

    score: int  # 0-100
    verdict: str  # Perfect | Good | Fair | Poor | Stay Home
    weather_score: int  # 0-40
    trail_score: int  # 0-30
    wind_score: int  # 0-15
    daylight_score: int  # 0-15
    factors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Sub-scorers
# ---------------------------------------------------------------------------

def _weather_score(inp: RideScoreInput) -> tuple[int, list[str]]:
    """Compute the weather sub-score (0-40)."""
    score = 40
    factors: list[str] = []

    # Temperature penalties (tighter band applied first, wider second)
    if inp.temp_c < 2 or inp.temp_c > 35:
        score -= 20
        factors.append(f"Extreme temp ({inp.temp_c:.0f}\u00b0C): -20")
    elif inp.temp_c < 5 or inp.temp_c > 32:
        score -= 10
        factors.append(f"Uncomfortable temp ({inp.temp_c:.0f}\u00b0C): -10")

    # Rain probability
    if inp.precipitation_probability > 80:
        score -= 30
        factors.append(f"High rain probability ({inp.precipitation_probability:.0f}%): -30")
    elif inp.precipitation_probability > 50:
        score -= 15
        factors.append(f"Moderate rain probability ({inp.precipitation_probability:.0f}%): -15")

    # Expected precipitation
    if inp.precipitation_mm > 5:
        score -= 20
        factors.append(f"Heavy rain expected ({inp.precipitation_mm:.1f}mm): -20")

    # Humidity
    if inp.humidity_pct > 90:
        score -= 5
        factors.append(f"Very high humidity ({inp.humidity_pct:.0f}%): -5")

    return max(0, score), factors


def _trail_score(inp: RideScoreInput) -> tuple[int, list[str]]:
    """Compute the trail sub-score (0-30)."""
    mapping: dict[str, int] = {
        "dry": 30,
        "damp": 20,
        "wet": 10,
        "muddy": 0,
        "frozen": 5,
    }
    score = mapping.get(inp.trail_condition, 15)
    factors: list[str] = []
    if score < 30:
        factors.append(f"Trail condition '{inp.trail_condition}': {score}/30")
    return score, factors


def _wind_score(inp: RideScoreInput) -> tuple[int, list[str]]:
    """Compute the wind sub-score (0-15)."""
    factors: list[str] = []

    if inp.wind_speed_kmh < 15:
        score = 15
    elif inp.wind_speed_kmh < 25:
        score = 10
        factors.append(f"Moderate wind ({inp.wind_speed_kmh:.0f} km/h): 10/15")
    elif inp.wind_speed_kmh < 40:
        score = 5
        factors.append(f"Strong wind ({inp.wind_speed_kmh:.0f} km/h): 5/15")
    elif inp.wind_speed_kmh < 55:
        score = 2
        factors.append(f"Very strong wind ({inp.wind_speed_kmh:.0f} km/h): 2/15")
    else:
        score = 0
        factors.append(f"Dangerous wind ({inp.wind_speed_kmh:.0f} km/h): 0/15")

    if inp.wind_gust_kmh > 60:
        score = max(0, score - 5)
        factors.append(f"Dangerous gusts ({inp.wind_gust_kmh:.0f} km/h): -5")

    return max(0, score), factors


def _daylight_score(inp: RideScoreInput) -> tuple[int, list[str]]:
    """Compute the daylight sub-score (0-15).

    Measures overlap between the ride window and the sunrise-sunset window.
    Full overlap → 15, no overlap → 0.
    """
    factors: list[str] = []

    if inp.ride_start is None or inp.sunrise is None or inp.sunset is None:
        # Assume full daylight when data is unavailable
        return 15, []

    from datetime import timedelta

    ride_end = inp.ride_start + timedelta(hours=inp.ride_duration_hours)

    # Overlap between [ride_start, ride_end] and [sunrise, sunset]
    overlap_start = max(inp.ride_start, inp.sunrise)
    overlap_end = min(ride_end, inp.sunset)

    overlap_seconds = max(0.0, (overlap_end - overlap_start).total_seconds())
    ride_seconds = inp.ride_duration_hours * 3600.0

    if ride_seconds <= 0:
        return 15, []

    ratio = overlap_seconds / ride_seconds
    score = int(round(15 * ratio))

    if score < 15:
        factors.append(f"Partial daylight ({ratio:.0%} of ride): {score}/15")

    return max(0, min(15, score)), factors


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def calculate_ride_score(inp: RideScoreInput) -> RideScoreResult:
    """Calculate the composite ride score (0-100).

    Args:
        inp: All ride-score inputs bundled into a dataclass.

    Returns:
        A :class:`RideScoreResult` with the total score, sub-scores,
        verdict, and human-readable factor explanations.
    """
    w_score, w_factors = _weather_score(inp)
    t_score, t_factors = _trail_score(inp)
    wi_score, wi_factors = _wind_score(inp)
    d_score, d_factors = _daylight_score(inp)

    total = max(0, min(100, w_score + t_score + wi_score + d_score))
    all_factors = w_factors + t_factors + wi_factors + d_factors

    if total >= 80:
        verdict = "Perfect"
    elif total >= 60:
        verdict = "Good"
    elif total >= 40:
        verdict = "Fair"
    elif total >= 20:
        verdict = "Poor"
    else:
        verdict = "Stay Home"

    return RideScoreResult(
        score=total,
        verdict=verdict,
        weather_score=w_score,
        trail_score=t_score,
        wind_score=wi_score,
        daylight_score=d_score,
        factors=all_factors,
    )
