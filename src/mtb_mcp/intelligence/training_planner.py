"""Training plan generation with periodization.

Pure-function algorithm: no I/O, no side effects.

Phases (as % of total weeks):
- Base: 40% (aerobic foundation)
- Build: 30% (increase intensity)
- Peak: 20% (race-specific intensity)
- Taper: 10% (reduce volume, maintain intensity)
"""

from __future__ import annotations

from datetime import date

from mtb_mcp.models.fitness import (
    GoalType,
    TrainingGoal,
    TrainingPhase,
    TrainingWeek,
    TrainingZone,
)

# Phase distribution as fraction of total weeks
PHASE_DISTRIBUTION: dict[TrainingPhase, float] = {
    TrainingPhase.base: 0.40,
    TrainingPhase.build: 0.30,
    TrainingPhase.peak: 0.20,
    TrainingPhase.taper: 0.10,
}

# Default target CTL by goal type
DEFAULT_TARGET_CTL: dict[GoalType, int] = {
    GoalType.alpencross: 80,
    GoalType.xc_race: 60,
    GoalType.enduro_race: 55,
    GoalType.marathon: 70,
    GoalType.personal_challenge: 50,
}

# Weekly volume multipliers by phase
PHASE_VOLUME_MULTIPLIER: dict[TrainingPhase, float] = {
    TrainingPhase.base: 1.0,
    TrainingPhase.build: 1.15,
    TrainingPhase.peak: 1.1,
    TrainingPhase.taper: 0.6,
}

# Default intensity focus by phase
PHASE_INTENSITY: dict[TrainingPhase, TrainingZone] = {
    TrainingPhase.base: TrainingZone.base,
    TrainingPhase.build: TrainingZone.tempo,
    TrainingPhase.peak: TrainingZone.threshold,
    TrainingPhase.taper: TrainingZone.base,
}

# Key workouts by phase and goal type
KEY_WORKOUTS: dict[TrainingPhase, dict[GoalType, str]] = {
    TrainingPhase.base: {
        GoalType.alpencross: "Long ride 3-4h, steady pace, moderate climbing",
        GoalType.xc_race: "2h base ride with 2x20min tempo blocks",
        GoalType.enduro_race: "2h ride with technical descents",
        GoalType.marathon: "3h steady ride, rolling terrain",
        GoalType.personal_challenge: "2-3h comfortable ride",
    },
    TrainingPhase.build: {
        GoalType.alpencross: "4-5h ride with 2000m+ climbing",
        GoalType.xc_race: "2h with 3x10min threshold intervals",
        GoalType.enduro_race: "3h with repeated descents + climb intervals",
        GoalType.marathon: "3-4h with sustained tempo sections",
        GoalType.personal_challenge: "3h ride with intensity blocks",
    },
    TrainingPhase.peak: {
        GoalType.alpencross: "Back-to-back days: 5h + 4h with major climbing",
        GoalType.xc_race: "Race-pace simulation: 1.5h XC intensity",
        GoalType.enduro_race: "Stage simulation with full race effort",
        GoalType.marathon: "4h race-pace simulation",
        GoalType.personal_challenge: "Goal-specific dress rehearsal",
    },
    TrainingPhase.taper: {
        GoalType.alpencross: "2h easy ride with a few short climbs",
        GoalType.xc_race: "1h with 2x5min race-pace openers",
        GoalType.enduro_race: "1.5h easy with 3 short race-pace descents",
        GoalType.marathon: "1.5h easy with short tempo bursts",
        GoalType.personal_challenge: "1h easy with openers",
    },
}


def _allocate_phases(total_weeks: int) -> list[tuple[TrainingPhase, int]]:
    """Allocate weeks to training phases.

    Ensures at least 1 week per phase (if total >= 4) and distributes
    remaining weeks proportionally.

    Args:
        total_weeks: Total number of weeks in the plan.

    Returns:
        List of (phase, week_count) tuples.
    """
    if total_weeks < 4:
        # Very short plan: just base + taper
        if total_weeks <= 1:
            return [(TrainingPhase.taper, total_weeks)]
        taper = 1
        return [
            (TrainingPhase.base, total_weeks - taper),
            (TrainingPhase.taper, taper),
        ]

    phases = list(PHASE_DISTRIBUTION.keys())
    raw = {p: max(1, int(total_weeks * frac)) for p, frac in PHASE_DISTRIBUTION.items()}

    # Adjust to match total
    allocated = sum(raw.values())
    diff = total_weeks - allocated
    if diff > 0:
        # Add extra weeks to base (largest phase)
        raw[TrainingPhase.base] += diff
    elif diff < 0:
        # Remove from base first, then build
        for phase in [TrainingPhase.base, TrainingPhase.build, TrainingPhase.peak]:
            removable = min(-diff, raw[phase] - 1)
            raw[phase] -= removable
            diff += removable
            if diff == 0:
                break

    return [(p, raw[p]) for p in phases if raw[p] > 0]


def generate_training_plan(
    goal: TrainingGoal,
    current_ctl: float = 30.0,
    weeks_available: int | None = None,
) -> list[TrainingWeek]:
    """Generate a periodized training plan for a goal.

    Volume progression: ~10% increase per week during base/build.
    Taper reduces volume by ~40% while maintaining intensity.

    Args:
        goal: The training goal to plan for.
        current_ctl: Current Chronic Training Load.
        weeks_available: Override for weeks until event.

    Returns:
        List of TrainingWeek objects forming the plan.
    """
    if weeks_available is None:
        delta = goal.target_date - date.today()
        weeks_available = max(1, delta.days // 7)

    phases = _allocate_phases(weeks_available)

    target_ctl = goal.target_ctl or DEFAULT_TARGET_CTL.get(goal.type, 50)

    # Base weekly volume: scale from current CTL to target
    # Rough heuristic: 1 CTL point ~ 1h/week at moderate intensity
    base_hours = max(3.0, current_ctl / 10)
    target_hours = max(base_hours, target_ctl / 10)

    # Base km/h rate (rough average for MTB)
    avg_speed_kmh = 18.0
    # Elevation per hour (rough average)
    avg_elevation_per_hour = 400.0

    weeks: list[TrainingWeek] = []
    week_counter = weeks_available  # Countdown from event

    for phase, phase_weeks in phases:
        for i in range(phase_weeks):
            # Progressive overload within phase
            if phase in (TrainingPhase.base, TrainingPhase.build):
                # ~10% increase per week within the phase
                progression = 1.0 + (i / max(1, phase_weeks - 1)) * 0.1 * phase_weeks
                progression = min(progression, 1.5)  # Cap at 50% increase
            else:
                progression = 1.0

            volume_mult = PHASE_VOLUME_MULTIPLIER[phase]

            # Interpolate hours from base to target based on position in plan
            plan_progress = 1.0 - (week_counter / weeks_available)
            current_base_hours = base_hours + (target_hours - base_hours) * plan_progress

            planned_hours = round(current_base_hours * volume_mult * progression, 1)
            planned_km = round(planned_hours * avg_speed_kmh, 1)
            planned_elevation = round(planned_hours * avg_elevation_per_hour, 0)

            key_workout = KEY_WORKOUTS.get(phase, {}).get(goal.type)

            weeks.append(TrainingWeek(
                goal_id=goal.id,
                week_number=week_counter,
                phase=phase,
                planned_hours=planned_hours,
                planned_km=planned_km,
                planned_elevation_m=planned_elevation,
                intensity_focus=PHASE_INTENSITY[phase],
                key_workout=key_workout,
            ))

            week_counter -= 1

    return weeks


def suggest_weekly_rides(
    week: TrainingWeek,
    available_tours: list[dict[str, object]] | None = None,
    weather_forecast: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    """Suggest concrete rides for a training week.

    Match training zone to appropriate ride type:
    - Recovery: flat, easy, <1h
    - Base: moderate distance, steady pace
    - Tempo: rolling terrain, sustained effort
    - Threshold: intervals or sustained climbs
    - VO2max: short, steep repeats

    Args:
        week: The training week to plan rides for.
        available_tours: Optional list of tour dicts to match against.
        weather_forecast: Optional weather info to consider.

    Returns:
        List of suggested ride dicts with type, duration, description.
    """
    rides: list[dict[str, object]] = []

    zone = week.intensity_focus
    total_hours = week.planned_hours

    # Weather consideration
    bad_weather = False
    if weather_forecast:
        rain_prob = weather_forecast.get("precipitation_probability", 0)
        if isinstance(rain_prob, (int, float)) and rain_prob > 70:
            bad_weather = True

    if zone == TrainingZone.recovery:
        rides.append({
            "type": "Recovery ride",
            "duration_hours": min(1.0, total_hours),
            "description": "Flat, easy spinning. Keep HR in zone 1.",
            "distance_km": round(min(1.0, total_hours) * 20, 1),
        })
    elif zone == TrainingZone.base:
        # Split into 3-4 rides
        long_ride_hours = round(total_hours * 0.4, 1)
        remaining = total_hours - long_ride_hours
        mid_ride = round(remaining * 0.5, 1)
        short_rides = round(remaining - mid_ride, 1)

        rides.append({
            "type": "Long base ride",
            "duration_hours": long_ride_hours,
            "description": "Steady pace, moderate terrain. HR zone 2.",
            "distance_km": round(long_ride_hours * 20, 1),
        })
        rides.append({
            "type": "Mid-week ride",
            "duration_hours": mid_ride,
            "description": "Rolling terrain, steady effort.",
            "distance_km": round(mid_ride * 20, 1),
        })
        if short_rides >= 0.5:
            rides.append({
                "type": "Easy spin",
                "duration_hours": short_rides,
                "description": "Recovery pace, flat route.",
                "distance_km": round(short_rides * 18, 1),
            })
    elif zone == TrainingZone.tempo:
        long_ride_hours = round(total_hours * 0.35, 1)
        tempo_ride = round(total_hours * 0.35, 1)
        easy_ride = round(total_hours - long_ride_hours - tempo_ride, 1)

        rides.append({
            "type": "Long ride with tempo blocks",
            "duration_hours": long_ride_hours,
            "description": "Include 2-3 x 20min tempo efforts on climbs.",
            "distance_km": round(long_ride_hours * 22, 1),
        })
        rides.append({
            "type": "Tempo intervals",
            "duration_hours": tempo_ride,
            "description": "Sustained tempo on rolling terrain. HR zone 3.",
            "distance_km": round(tempo_ride * 22, 1),
        })
        if easy_ride >= 0.5:
            rides.append({
                "type": "Recovery ride",
                "duration_hours": easy_ride,
                "description": "Easy spinning for recovery.",
                "distance_km": round(easy_ride * 18, 1),
            })
    elif zone == TrainingZone.threshold:
        interval_ride = round(total_hours * 0.3, 1)
        climb_ride = round(total_hours * 0.35, 1)
        easy_ride = round(total_hours - interval_ride - climb_ride, 1)

        rides.append({
            "type": "Threshold intervals",
            "duration_hours": interval_ride,
            "description": "4-5 x 8min at threshold power/HR. Full recovery between.",
            "distance_km": round(interval_ride * 22, 1),
        })
        rides.append({
            "type": "Sustained climbing",
            "duration_hours": climb_ride,
            "description": "Long climb at threshold intensity. HR zone 4.",
            "distance_km": round(climb_ride * 18, 1),
        })
        if easy_ride >= 0.5:
            rides.append({
                "type": "Recovery spin",
                "duration_hours": easy_ride,
                "description": "Very easy, active recovery.",
                "distance_km": round(easy_ride * 18, 1),
            })
    elif zone == TrainingZone.vo2max:
        vo2_ride = round(total_hours * 0.3, 1)
        endurance_ride = round(total_hours * 0.35, 1)
        easy_ride = round(total_hours - vo2_ride - endurance_ride, 1)

        rides.append({
            "type": "VO2max intervals",
            "duration_hours": vo2_ride,
            "description": "6-8 x 3min max effort on steep climb. Full recovery.",
            "distance_km": round(vo2_ride * 20, 1),
        })
        rides.append({
            "type": "Endurance ride",
            "duration_hours": endurance_ride,
            "description": "Moderate pace, base maintenance.",
            "distance_km": round(endurance_ride * 20, 1),
        })
        if easy_ride >= 0.5:
            rides.append({
                "type": "Recovery ride",
                "duration_hours": easy_ride,
                "description": "Easy spinning, legs up.",
                "distance_km": round(easy_ride * 18, 1),
            })

    if bad_weather:
        for ride in rides:
            ride["weather_note"] = "Bad weather expected -- consider indoor trainer."

    # Match against available tours if provided
    if available_tours:
        for ride in rides:
            target_km = ride.get("distance_km", 0)
            if isinstance(target_km, (int, float)):
                best_match = _find_matching_tour(available_tours, float(target_km), zone)
                if best_match:
                    ride["suggested_tour"] = best_match

    return rides


def _find_matching_tour(
    tours: list[dict[str, object]],
    target_km: float,
    zone: TrainingZone,
) -> dict[str, object] | None:
    """Find a tour matching the target distance and zone.

    Args:
        tours: Available tours.
        target_km: Target distance in km.
        zone: Training zone to match.

    Returns:
        Best matching tour dict or None.
    """
    best: dict[str, object] | None = None
    best_score = float("inf")

    for tour in tours:
        tour_km = tour.get("distance_km")
        if not isinstance(tour_km, (int, float)):
            continue

        # Distance match (closer is better)
        km_diff = abs(float(tour_km) - target_km)
        score = km_diff

        if score < best_score:
            best_score = score
            best = tour

    return best


def adjust_plan(
    plan: list[TrainingWeek],
    reason: str,
    weeks_affected: int = 1,
) -> list[TrainingWeek]:
    """Adjust a training plan for illness, vacation, or overtraining.

    illness: reduce volume 50% for affected weeks, add recovery week.
    vacation: skip weeks, extend plan.
    overtraining: add rest week, reduce following weeks 30%.

    Args:
        plan: Current training plan (list of TrainingWeek).
        reason: Reason for adjustment (illness, vacation, overtraining, injury).
        weeks_affected: Number of weeks affected.

    Returns:
        Adjusted training plan.
    """
    if not plan:
        return plan

    # Sort by week_number descending (countdown to event)
    sorted_plan = sorted(plan, key=lambda w: -w.week_number)

    # Find the "current" position (highest week_number = furthest from event)
    adjusted: list[TrainingWeek] = []

    for idx, week in enumerate(sorted_plan):
        if idx < weeks_affected:
            # This week is affected
            if reason == "illness":
                adjusted.append(week.model_copy(update={
                    "planned_hours": round(week.planned_hours * 0.5, 1),
                    "planned_km": round(week.planned_km * 0.5, 1),
                    "planned_elevation_m": round(week.planned_elevation_m * 0.5, 0),
                    "intensity_focus": TrainingZone.recovery,
                    "key_workout": None,
                    "notes": f"Reduced for illness (week {idx + 1}/{weeks_affected})",
                }))
            elif reason == "vacation":
                adjusted.append(week.model_copy(update={
                    "planned_hours": 0.0,
                    "planned_km": 0.0,
                    "planned_elevation_m": 0.0,
                    "intensity_focus": TrainingZone.recovery,
                    "key_workout": None,
                    "notes": f"Vacation (week {idx + 1}/{weeks_affected})",
                }))
            elif reason == "overtraining":
                adjusted.append(week.model_copy(update={
                    "planned_hours": round(week.planned_hours * 0.3, 1),
                    "planned_km": round(week.planned_km * 0.3, 1),
                    "planned_elevation_m": round(week.planned_elevation_m * 0.3, 0),
                    "intensity_focus": TrainingZone.recovery,
                    "key_workout": None,
                    "notes": "Rest week: overtraining recovery",
                }))
            elif reason == "injury":
                adjusted.append(week.model_copy(update={
                    "planned_hours": 0.0,
                    "planned_km": 0.0,
                    "planned_elevation_m": 0.0,
                    "intensity_focus": TrainingZone.recovery,
                    "key_workout": None,
                    "notes": f"Injury recovery (week {idx + 1}/{weeks_affected})",
                }))
            else:
                adjusted.append(week)
        elif idx < weeks_affected + 1 and reason in ("illness", "overtraining"):
            # Add a recovery transition week after illness/overtraining
            adjusted.append(week.model_copy(update={
                "planned_hours": round(week.planned_hours * 0.7, 1),
                "planned_km": round(week.planned_km * 0.7, 1),
                "planned_elevation_m": round(week.planned_elevation_m * 0.7, 0),
                "intensity_focus": TrainingZone.base,
                "notes": f"Transition week after {reason}",
            }))
        else:
            adjusted.append(week)

    # Re-sort by week_number descending to maintain original order
    return sorted(adjusted, key=lambda w: -w.week_number)
