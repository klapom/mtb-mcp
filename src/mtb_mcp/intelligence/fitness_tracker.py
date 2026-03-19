"""Fitness tracking -- CTL, ATL, TSB calculation from training data.

Pure-function algorithm: no I/O, no side effects.

CTL (Chronic Training Load, ~42-day fitness):
    CTL_today = CTL_yesterday + (TSS_today - CTL_yesterday) / 42

ATL (Acute Training Load, ~7-day fatigue):
    ATL_today = ATL_yesterday + (TSS_today - ATL_yesterday) / 7

TSB (Training Stress Balance = Form):
    TSB = CTL - ATL
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

CTL_TIME_CONSTANT = 42
ATL_TIME_CONSTANT = 7


@dataclass
class DailyTrainingLoad:
    """A single day's training stress score."""

    date: date
    tss: float


@dataclass
class FitnessState:
    """Fitness state for a given day: CTL, ATL, TSB."""

    date: date
    ctl: float
    atl: float
    tsb: float


def estimate_tss_from_activity(
    distance_km: float,
    elevation_m: float,
    duration_hours: float,
    avg_hr: float | None = None,
    avg_power: float | None = None,
    ftp: float | None = None,
) -> float:
    """Estimate Training Stress Score from activity data.

    Priority:
    1. Power-based TSS if power and FTP available
    2. HR-based estimation
    3. Duration + intensity estimation as fallback

    Args:
        distance_km: Distance in kilometres.
        elevation_m: Total elevation gain in metres.
        avg_hr: Average heart rate (bpm).
        avg_power: Average power (watts).
        ftp: Functional Threshold Power (watts).
        duration_hours: Ride duration in hours.

    Returns:
        Estimated TSS value.
    """
    # 1. Power-based TSS (most accurate)
    if avg_power is not None and ftp is not None and ftp > 0:
        intensity_factor = avg_power / ftp
        normalized_power = avg_power  # simplified: using avg as proxy for NP
        tss = (duration_hours * 3600 * normalized_power * intensity_factor) / (ftp * 3600) * 100
        return round(tss, 1)

    # 2. HR-based estimation (rough)
    if avg_hr is not None:
        # Estimate intensity from HR (assumes max HR ~190, resting ~50)
        hr_fraction = min(1.0, max(0.0, (avg_hr - 50) / 140))
        intensity = hr_fraction ** 2  # Quadratic relationship
        tss = duration_hours * intensity * 100
        return round(tss, 1)

    # 3. Duration + terrain-based fallback
    # Base: ~50 TSS per hour of moderate riding
    base_tss_per_hour = 50.0

    # Elevation adds intensity: +10 TSS per 500m climbing per hour
    if duration_hours > 0:
        climbing_rate = elevation_m / duration_hours
        elevation_factor = 1.0 + (climbing_rate / 500) * 0.2
    else:
        elevation_factor = 1.0

    # Distance provides a sanity check on speed/effort
    if duration_hours > 0:
        speed_kmh = distance_km / duration_hours
        speed_factor = min(1.5, max(0.5, speed_kmh / 20.0))
    else:
        speed_factor = 1.0

    tss = duration_hours * base_tss_per_hour * elevation_factor * speed_factor
    return round(tss, 1)


def calculate_fitness_history(
    daily_loads: list[DailyTrainingLoad],
    initial_ctl: float = 0.0,
    initial_atl: float = 0.0,
) -> list[FitnessState]:
    """Calculate CTL/ATL/TSB for each day in the daily_loads sequence.

    Uses exponentially weighted moving average:
    CTL_today = CTL_yesterday + (TSS_today - CTL_yesterday) / 42
    ATL_today = ATL_yesterday + (TSS_today - ATL_yesterday) / 7
    TSB = CTL - ATL

    Days are processed in chronological order. If there are gaps between
    dates in the input, rest days (TSS=0) are filled in automatically.

    Args:
        daily_loads: Training loads sorted by date.
        initial_ctl: Starting CTL value.
        initial_atl: Starting ATL value.

    Returns:
        A FitnessState for each day from the first to the last input date.
    """
    if not daily_loads:
        return []

    # Build date->TSS lookup
    loads_by_date: dict[date, float] = {dl.date: dl.tss for dl in daily_loads}

    # Determine date range
    sorted_loads = sorted(daily_loads, key=lambda dl: dl.date)
    start_date = sorted_loads[0].date
    end_date = sorted_loads[-1].date

    ctl = initial_ctl
    atl = initial_atl
    history: list[FitnessState] = []

    current = start_date
    while current <= end_date:
        tss = loads_by_date.get(current, 0.0)

        ctl = ctl + (tss - ctl) / CTL_TIME_CONSTANT
        atl = atl + (tss - atl) / ATL_TIME_CONSTANT
        tsb = ctl - atl

        history.append(FitnessState(
            date=current,
            ctl=round(ctl, 2),
            atl=round(atl, 2),
            tsb=round(tsb, 2),
        ))

        current += timedelta(days=1)

    return history


def get_training_status(tsb: float) -> str:
    """Interpret a TSB value into a human-readable training status.

    Args:
        tsb: Training Stress Balance value.

    Returns:
        Human-readable status string.
    """
    if tsb > 15:
        return "Fresh (possibly detrained)"
    if tsb > 5:
        return "Optimal for racing"
    if tsb > -10:
        return "Productive training"
    if tsb > -30:
        return "Fatigued"
    return "Overtraining risk!"


def check_alpencross_readiness(
    ctl: float,
    weekly_elevations: list[float],
    longest_rides_km: list[float],
    back_to_back_count: int,
) -> dict[str, object]:
    """Check readiness for a multi-day alpine crossing.

    Criteria:
    - CTL >= 80
    - Weekly elevation >= 3000m (last 4 weeks)
    - Longest ride >= 80km (at least 2x)
    - Back-to-back rides >= 2

    Args:
        ctl: Current Chronic Training Load.
        weekly_elevations: Weekly elevation totals (most recent 4 weeks).
        longest_rides_km: Distances of longest rides in training.
        back_to_back_count: Number of back-to-back ride days completed.

    Returns:
        Dict with readiness score, individual checks, and recommendations.
    """
    checks: dict[str, bool] = {}
    recommendations: list[str] = []

    # CTL check
    checks["ctl_ready"] = ctl >= 80
    if not checks["ctl_ready"]:
        recommendations.append(
            f"CTL is {ctl:.0f}, target is 80+. "
            f"Need ~{max(1, int((80 - ctl) / 2))} more weeks of consistent training."
        )

    # Weekly elevation check (last 4 weeks)
    recent_elevations = weekly_elevations[-4:] if weekly_elevations else []
    high_elevation_weeks = sum(1 for e in recent_elevations if e >= 3000)
    checks["elevation_ready"] = high_elevation_weeks >= 2
    if not checks["elevation_ready"]:
        recommendations.append(
            f"Only {high_elevation_weeks}/4 recent weeks had 3000m+ elevation. "
            "Add more climbing to your long rides."
        )

    # Longest ride check
    long_rides = [r for r in longest_rides_km if r >= 80]
    checks["long_ride_ready"] = len(long_rides) >= 2
    if not checks["long_ride_ready"]:
        recommendations.append(
            f"Only {len(long_rides)} rides of 80km+. Need at least 2 before the event."
        )

    # Back-to-back check
    checks["back_to_back_ready"] = back_to_back_count >= 2
    if not checks["back_to_back_ready"]:
        recommendations.append(
            f"Only {back_to_back_count} back-to-back ride days. "
            "Do at least 2 double-day weekends."
        )

    # Overall score (0-100)
    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    score = int(passed / total * 100) if total > 0 else 0

    return {
        "ready": all(checks.values()),
        "score": score,
        "checks": checks,
        "recommendations": recommendations,
    }


def check_xc_readiness(
    ctl: float,
    ftp_wkg: float | None,
    weeks_to_race: int,
) -> dict[str, object]:
    """Check readiness for an XC race.

    Criteria:
    - CTL >= 60
    - FTP >= 3.5 W/kg
    - Taper: 1-2 weeks before race (volume -40%, keep intensity)

    Args:
        ctl: Current Chronic Training Load.
        ftp_wkg: FTP in watts per kilogram.
        weeks_to_race: Weeks until race day.

    Returns:
        Dict with readiness score, individual checks, and recommendations.
    """
    checks: dict[str, bool] = {}
    recommendations: list[str] = []

    # CTL check
    checks["ctl_ready"] = ctl >= 60
    if not checks["ctl_ready"]:
        recommendations.append(
            f"CTL is {ctl:.0f}, target is 60+. "
            f"Need ~{max(1, int((60 - ctl) / 2))} more weeks of training."
        )

    # FTP check
    if ftp_wkg is not None:
        checks["ftp_ready"] = ftp_wkg >= 3.5
        if not checks["ftp_ready"]:
            recommendations.append(
                f"FTP is {ftp_wkg:.1f} W/kg, target is 3.5+ W/kg. "
                "Add threshold intervals to your training."
            )
    else:
        checks["ftp_ready"] = False
        recommendations.append(
            "FTP unknown. Do an FTP test to assess power-to-weight."
        )

    # Taper check
    checks["taper_appropriate"] = 1 <= weeks_to_race <= 2
    if weeks_to_race > 2:
        recommendations.append(
            f"{weeks_to_race} weeks to race. "
            "Continue building; taper starts 1-2 weeks before."
        )
    elif weeks_to_race < 1:
        recommendations.append(
            "Race is imminent! Focus on rest and pre-race nutrition."
        )

    # Overall score
    passed = sum(1 for v in checks.values() if v)
    total = len(checks)
    score = int(passed / total * 100) if total > 0 else 0

    return {
        "ready": all(checks.values()),
        "score": score,
        "checks": checks,
        "recommendations": recommendations,
    }
