"""MCP tools for fitness tracking and training planning.

Provides tools to set training goals, track CTL/ATL/TSB fitness metrics,
generate periodized training plans, and check race readiness.
"""

from __future__ import annotations

from datetime import date

import structlog

from mtb_mcp.config import get_settings
from mtb_mcp.intelligence.fitness_tracker import (
    check_alpencross_readiness,
    check_xc_readiness,
    get_training_status,
)
from mtb_mcp.intelligence.training_planner import (
    adjust_plan,
    generate_training_plan,
    suggest_weekly_rides,
)
from mtb_mcp.models.fitness import GoalType, TrainingGoal
from mtb_mcp.server import mcp
from mtb_mcp.storage.database import Database
from mtb_mcp.storage.training_store import TrainingStore

logger = structlog.get_logger(__name__)


async def _get_store() -> tuple[Database, TrainingStore]:
    """Initialize a Database and TrainingStore from settings.

    Returns:
        A tuple of (Database, TrainingStore). Caller must close the database.
    """
    settings = get_settings()
    db = Database(settings.resolved_db_path)
    await db.initialize()
    return db, TrainingStore(db)


async def _resolve_goal(
    store: TrainingStore, goal_name: str | None,
) -> TrainingGoal | None:
    """Resolve a goal by name, or return the first active goal.

    Args:
        store: The TrainingStore instance.
        goal_name: Optional goal name to search for.

    Returns:
        The resolved TrainingGoal or None.
    """
    if goal_name is not None:
        return await store.get_goal_by_name(goal_name)

    goals = await store.get_active_goals()
    if goals:
        return goals[0]
    return None


@mcp.tool()
async def set_training_goal(
    name: str,
    goal_type: str,
    target_date: str,
    target_distance_km: float | None = None,
    target_elevation_m: float | None = None,
    description: str | None = None,
) -> str:
    """Set a training goal (e.g. 'Alpencross Ischgl-Riva, 2026-07-15, 400km, 12000hm').

    Goal types: alpencross, xc_race, enduro_race, marathon, personal_challenge.
    Automatically generates a periodized training plan.
    """
    # Validate goal type
    try:
        GoalType(goal_type)
    except ValueError:
        valid = ", ".join(gt.value for gt in GoalType)
        return f"Invalid goal type '{goal_type}'. Valid types: {valid}"

    # Parse target date
    try:
        parsed_date = date.fromisoformat(target_date)
    except ValueError:
        return f"Invalid date format '{target_date}'. Use YYYY-MM-DD."

    if parsed_date <= date.today():
        return f"Target date {target_date} must be in the future."

    db: Database | None = None
    try:
        db, store = await _get_store()

        # Get current fitness for plan generation
        latest = await store.get_latest_snapshot()
        current_ctl = latest.ctl if latest else 30.0

        goal = await store.add_goal(
            name=name,
            goal_type=goal_type,
            target_date=parsed_date,
            target_distance_km=target_distance_km,
            target_elevation_m=target_elevation_m,
            description=description,
        )

        # Generate training plan
        plan = generate_training_plan(goal, current_ctl=current_ctl)
        await store.save_training_weeks(plan)

        weeks_to_event = (parsed_date - date.today()).days // 7
        lines = [
            f"Training goal set: {name}",
            f"  Type: {goal_type}",
            f"  Target date: {target_date} ({weeks_to_event} weeks away)",
        ]

        if target_distance_km is not None:
            lines.append(f"  Target distance: {target_distance_km} km")
        if target_elevation_m is not None:
            lines.append(f"  Target elevation: {target_elevation_m} m")
        if description:
            lines.append(f"  Description: {description}")

        lines.append(f"  Current CTL: {current_ctl:.0f}")
        lines.append(f"  Training plan: {len(plan)} weeks generated")

        # Summarize phases
        phases: dict[str, int] = {}
        for week in plan:
            phase_name = week.phase.value
            phases[phase_name] = phases.get(phase_name, 0) + 1
        phase_summary = ", ".join(f"{p}: {c}w" for p, c in phases.items())
        lines.append(f"  Phases: {phase_summary}")

        lines.append(f"  Goal ID: {goal.id}")

        return "\n".join(lines)
    finally:
        if db is not None:
            await db.close()


@mcp.tool()
async def get_training_status_tool() -> str:
    """Get current training status -- CTL/ATL/TSB, weekly volume vs plan.

    Shows if you're on track for your goals.
    """
    db: Database | None = None
    try:
        db, store = await _get_store()

        latest = await store.get_latest_snapshot()
        goals = await store.get_active_goals()

        if latest is None:
            lines = [
                "No fitness data yet.",
                "Log rides via Strava or bike_log_ride to build your fitness profile.",
            ]
            if goals:
                lines.append(f"\nActive goals: {len(goals)}")
                for g in goals:
                    days = (g.target_date - date.today()).days
                    lines.append(f"  - {g.name} ({g.type.value}) in {days} days")
            return "\n".join(lines)

        status = get_training_status(latest.tsb)

        lines = [
            "Current Training Status",
            "=" * 40,
            f"  CTL (Fitness):  {latest.ctl:.1f}",
            f"  ATL (Fatigue):  {latest.atl:.1f}",
            f"  TSB (Form):     {latest.tsb:.1f}",
            f"  Status:         {status}",
            "",
            "Weekly Volume:",
            f"  Rides: {latest.weekly_rides}",
            f"  Distance: {latest.weekly_km:.1f} km",
            f"  Elevation: {latest.weekly_elevation_m:.0f} m",
            f"  Hours: {latest.weekly_hours:.1f}h",
        ]

        if goals:
            lines.append("")
            lines.append("Active Goals:")
            for g in goals:
                days = (g.target_date - date.today()).days
                weeks = days // 7
                lines.append(f"  {g.name} ({g.type.value}): {weeks} weeks away")
                if g.target_ctl:
                    progress = min(100, int(latest.ctl / g.target_ctl * 100))
                    lines.append(
                        f"    CTL progress: {latest.ctl:.0f}/{g.target_ctl} "
                        f"({progress}%)"
                    )

        return "\n".join(lines)
    finally:
        if db is not None:
            await db.close()


@mcp.tool()
async def get_training_plan(goal_name: str | None = None) -> str:
    """Get your periodized training plan with weekly targets.

    Shows phase (base/build/peak/taper), planned km, elevation, key workouts.
    """
    db: Database | None = None
    try:
        db, store = await _get_store()

        goal = await _resolve_goal(store, goal_name)
        if goal is None:
            return (
                "No training goal found. "
                "Use set_training_goal to create one first."
            )

        weeks = await store.get_training_weeks(goal.id)
        if not weeks:
            return f"No training plan found for '{goal.name}'."

        days_to_event = (goal.target_date - date.today()).days
        current_week = days_to_event // 7

        lines = [
            f"Training Plan: {goal.name}",
            f"Event: {goal.target_date.isoformat()} ({days_to_event} days away)",
            "=" * 60,
        ]

        for week in weeks:
            marker = " <-- THIS WEEK" if week.week_number == current_week else ""
            lines.append(
                f"\nWeek {week.week_number} [{week.phase.value.upper()}]{marker}"
            )
            lines.append(
                f"  Planned: {week.planned_hours:.1f}h | "
                f"{week.planned_km:.0f} km | "
                f"{week.planned_elevation_m:.0f} m"
            )
            lines.append(f"  Focus: {week.intensity_focus.value}")
            if week.key_workout:
                lines.append(f"  Key workout: {week.key_workout}")
            if week.notes:
                lines.append(f"  Notes: {week.notes}")

        return "\n".join(lines)
    finally:
        if db is not None:
            await db.close()


@mcp.tool()
async def get_fitness_trend(days: int = 90) -> str:
    """View your fitness trend over time -- CTL curve, volume, progress toward goals."""
    db: Database | None = None
    try:
        db, store = await _get_store()

        snapshots = await store.get_snapshots(days=days)
        if not snapshots:
            return (
                f"No fitness data in the last {days} days. "
                "Log rides to build your fitness profile."
            )

        lines = [
            f"Fitness Trend (last {days} days)",
            "=" * 50,
            "",
            f"{'Date':<12} {'CTL':>6} {'ATL':>6} {'TSB':>6} {'Status':<25}",
            "-" * 56,
        ]

        # Show weekly summaries instead of daily for readability
        weekly_snapshots = snapshots[::7] if len(snapshots) > 14 else snapshots
        if snapshots and snapshots[-1] not in weekly_snapshots:
            weekly_snapshots.append(snapshots[-1])

        for snap in weekly_snapshots:
            status = get_training_status(snap.tsb)
            lines.append(
                f"{snap.date.isoformat():<12} "
                f"{snap.ctl:>6.1f} {snap.atl:>6.1f} {snap.tsb:>6.1f} "
                f"{status:<25}"
            )

        # Summary
        if len(snapshots) >= 2:
            first = snapshots[0]
            last = snapshots[-1]
            ctl_change = last.ctl - first.ctl
            direction = "up" if ctl_change > 0 else "down"
            lines.append("")
            lines.append(
                f"CTL trend: {first.ctl:.1f} -> {last.ctl:.1f} "
                f"({direction} {abs(ctl_change):.1f})"
            )

        return "\n".join(lines)
    finally:
        if db is not None:
            await db.close()


@mcp.tool()
async def check_race_readiness(goal_name: str | None = None) -> str:
    """Check if you're ready for your upcoming race or event.

    Evaluates CTL, weekly elevation, longest rides, and taper status.
    """
    db: Database | None = None
    try:
        db, store = await _get_store()

        goal = await _resolve_goal(store, goal_name)
        if goal is None:
            return (
                "No training goal found. "
                "Use set_training_goal to create one first."
            )

        latest = await store.get_latest_snapshot()
        if latest is None:
            return (
                "No fitness data yet. "
                "Log rides to assess race readiness."
            )

        snapshots = await store.get_snapshots(days=90)

        # Calculate weekly elevations from snapshots
        weekly_elevations = [s.weekly_elevation_m for s in snapshots if s.weekly_elevation_m > 0]

        # Get longest rides (approximate from weekly data)
        longest_rides = [s.weekly_km for s in snapshots if s.weekly_km > 0]

        days_to_event = (goal.target_date - date.today()).days
        weeks_to_event = days_to_event // 7

        lines = [
            f"Race Readiness: {goal.name}",
            f"Event: {goal.target_date.isoformat()} ({days_to_event} days away)",
            "=" * 50,
        ]

        if goal.type in (GoalType.alpencross, GoalType.marathon):
            readiness = check_alpencross_readiness(
                ctl=latest.ctl,
                weekly_elevations=weekly_elevations,
                longest_rides_km=longest_rides,
                back_to_back_count=0,  # Would need activity data to calculate
            )
        else:
            readiness = check_xc_readiness(
                ctl=latest.ctl,
                ftp_wkg=None,  # Would need power data
                weeks_to_race=weeks_to_event,
            )

        ready = readiness["ready"]
        score = readiness["score"]
        checks = readiness["checks"]
        recs = readiness["recommendations"]

        assert isinstance(ready, bool)
        assert isinstance(score, int)
        assert isinstance(checks, dict)
        assert isinstance(recs, list)

        verdict = "READY!" if ready else "NOT READY"
        lines.append(f"\n  Readiness: {verdict} ({score}%)")
        lines.append("")

        for check_name, passed in checks.items():
            icon = "[OK]" if passed else "[  ]"
            lines.append(f"  {icon} {check_name.replace('_', ' ').title()}")

        if recs:
            lines.append("")
            lines.append("Recommendations:")
            for rec in recs:
                lines.append(f"  - {rec}")

        lines.append("")
        lines.append(f"Current CTL: {latest.ctl:.1f}")
        lines.append(f"Current TSB: {latest.tsb:.1f} ({get_training_status(latest.tsb)})")

        return "\n".join(lines)
    finally:
        if db is not None:
            await db.close()


@mcp.tool()
async def suggest_weekly_rides_tool(goal_name: str | None = None) -> str:
    """Get concrete ride suggestions for this week based on your training plan.

    Matches training zones to appropriate tours and considers current conditions.
    """
    db: Database | None = None
    try:
        db, store = await _get_store()

        goal = await _resolve_goal(store, goal_name)
        if goal is None:
            return (
                "No training goal found. "
                "Use set_training_goal to create one first."
            )

        weeks = await store.get_training_weeks(goal.id)
        if not weeks:
            return f"No training plan found for '{goal.name}'."

        # Find the current week
        days_to_event = (goal.target_date - date.today()).days
        current_week_num = days_to_event // 7

        current_week = None
        for w in weeks:
            if w.week_number == current_week_num:
                current_week = w
                break

        if current_week is None:
            # Fall back to closest week
            current_week = min(weeks, key=lambda w: abs(w.week_number - current_week_num))

        rides = suggest_weekly_rides(current_week)

        lines = [
            f"Suggested Rides for Week {current_week.week_number}",
            f"Goal: {goal.name}",
            f"Phase: {current_week.phase.value.upper()} | "
            f"Focus: {current_week.intensity_focus.value}",
            f"Target: {current_week.planned_hours:.1f}h | "
            f"{current_week.planned_km:.0f} km | "
            f"{current_week.planned_elevation_m:.0f} m",
            "=" * 50,
        ]

        total_hours = 0.0
        total_km = 0.0
        for i, ride in enumerate(rides, 1):
            duration = ride.get("duration_hours", 0)
            dist = ride.get("distance_km", 0)
            if isinstance(duration, (int, float)):
                total_hours += duration
            if isinstance(dist, (int, float)):
                total_km += dist

            lines.append(f"\nRide {i}: {ride.get('type', 'Ride')}")
            if isinstance(duration, (int, float)):
                lines.append(f"  Duration: {duration:.1f}h")
            if isinstance(dist, (int, float)):
                lines.append(f"  Distance: ~{dist:.0f} km")
            lines.append(f"  {ride.get('description', '')}")

            if "weather_note" in ride:
                lines.append(f"  Note: {ride['weather_note']}")
            if "suggested_tour" in ride:
                tour = ride["suggested_tour"]
                if isinstance(tour, dict) and "name" in tour:
                    lines.append(f"  Suggested tour: {tour['name']}")

        if current_week.key_workout:
            lines.append(f"\nKey Workout: {current_week.key_workout}")

        lines.append(f"\nTotal planned: {total_hours:.1f}h | {total_km:.0f} km")

        return "\n".join(lines)
    finally:
        if db is not None:
            await db.close()


@mcp.tool()
async def adjust_training_plan_tool(
    reason: str,
    weeks_affected: int = 1,
    goal_name: str | None = None,
) -> str:
    """Adjust your training plan for illness, vacation, or overtraining.

    Reasons: illness, vacation, overtraining, injury.
    """
    valid_reasons = ("illness", "vacation", "overtraining", "injury")
    if reason not in valid_reasons:
        return (
            f"Invalid reason '{reason}'. "
            f"Valid reasons: {', '.join(valid_reasons)}"
        )

    if weeks_affected < 1:
        return "weeks_affected must be at least 1."

    db: Database | None = None
    try:
        db, store = await _get_store()

        goal = await _resolve_goal(store, goal_name)
        if goal is None:
            return (
                "No training goal found. "
                "Use set_training_goal to create one first."
            )

        weeks = await store.get_training_weeks(goal.id)
        if not weeks:
            return f"No training plan found for '{goal.name}'."

        adjusted = adjust_plan(weeks, reason=reason, weeks_affected=weeks_affected)
        await store.save_training_weeks(adjusted)

        lines = [
            f"Training plan adjusted for {goal.name}",
            f"  Reason: {reason}",
            f"  Weeks affected: {weeks_affected}",
            "",
        ]

        # Show affected weeks
        for week in adjusted:
            if week.notes and (reason in (week.notes or "").lower()):
                lines.append(
                    f"  Week {week.week_number}: "
                    f"{week.planned_hours:.1f}h | {week.planned_km:.0f} km | "
                    f"{week.notes}"
                )

        lines.append("")
        lines.append(
            "Plan updated. Use get_training_plan to see the full revised schedule."
        )

        return "\n".join(lines)
    finally:
        if db is not None:
            await db.close()
