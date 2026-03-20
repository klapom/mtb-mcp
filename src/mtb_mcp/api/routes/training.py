"""Training & fitness endpoints."""
from __future__ import annotations

import time
from datetime import date
from typing import Any

import structlog
from fastapi import APIRouter, Query
from pydantic import BaseModel

from mtb_mcp.api.deps import get_cached_settings
from mtb_mcp.api.models import err, ok, ok_list
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
from mtb_mcp.storage.database import Database
from mtb_mcp.storage.training_store import TrainingStore

logger = structlog.get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class CreateGoalRequest(BaseModel):
    name: str
    goal_type: str
    target_date: str
    target_distance_km: float | None = None
    target_elevation_m: float | None = None
    description: str | None = None


class AdjustPlanRequest(BaseModel):
    reason: str
    weeks_affected: int = 1
    goal_name: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_store() -> tuple[Database, TrainingStore]:
    settings = get_cached_settings()
    db = Database(settings.resolved_db_path)
    await db.initialize()
    return db, TrainingStore(db)


async def _resolve_goal(
    store: TrainingStore, goal_name: str | None,
) -> TrainingGoal | None:
    if goal_name is not None:
        return await store.get_goal_by_name(goal_name)
    goals = await store.get_active_goals()
    if goals:
        return goals[0]
    return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/goals")
async def create_goal(body: CreateGoalRequest) -> dict[str, Any]:
    """Create a training goal and generate a periodized plan."""
    t = time.monotonic()

    # Validate goal type
    try:
        GoalType(body.goal_type)
    except ValueError:
        valid = ", ".join(gt.value for gt in GoalType)
        return err("VALIDATION_ERROR", f"Invalid goal type '{body.goal_type}'. Valid: {valid}")

    # Parse target date
    try:
        parsed_date = date.fromisoformat(body.target_date)
    except ValueError:
        return err("VALIDATION_ERROR", f"Invalid date format '{body.target_date}'. Use YYYY-MM-DD.")

    if parsed_date <= date.today():
        return err("VALIDATION_ERROR", f"Target date {body.target_date} must be in the future.")

    db: Database | None = None
    try:
        db, store = await _get_store()

        latest = await store.get_latest_snapshot()
        current_ctl = latest.ctl if latest else 30.0

        goal = await store.add_goal(
            name=body.name,
            goal_type=body.goal_type,
            target_date=parsed_date,
            target_distance_km=body.target_distance_km,
            target_elevation_m=body.target_elevation_m,
            description=body.description,
        )

        plan = generate_training_plan(goal, current_ctl=current_ctl)
        await store.save_training_weeks(plan)

        weeks_to_event = (parsed_date - date.today()).days // 7

        phases: dict[str, int] = {}
        for week in plan:
            phase_name = week.phase.value
            phases[phase_name] = phases.get(phase_name, 0) + 1

        return ok(
            {
                "goal": goal.model_dump(mode="json"),
                "plan_summary": {
                    "weeks": len(plan),
                    "weeks_to_event": weeks_to_event,
                    "current_ctl": current_ctl,
                    "phases": phases,
                },
            },
            t,
        )
    except Exception as exc:
        logger.error("training.create_goal_failed", error=str(exc))
        return err("INTERNAL_ERROR", f"Failed to create goal: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.get("/goals")
async def list_goals() -> dict[str, Any]:
    """List all active training goals."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, store = await _get_store()
        goals = await store.get_active_goals()
        return ok_list(
            [g.model_dump(mode="json") for g in goals],
            len(goals),
            t,
        )
    except Exception as exc:
        logger.error("training.list_goals_failed", error=str(exc))
        return err("INTERNAL_ERROR", f"Failed to list goals: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.get("/status")
async def training_status() -> dict[str, Any]:
    """Current training status (CTL/ATL/TSB, weekly volume)."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, store = await _get_store()

        latest = await store.get_latest_snapshot()
        goals = await store.get_active_goals()

        if latest is None:
            goal_items = []
            for g in goals:
                days = (g.target_date - date.today()).days
                goal_items.append({"name": g.name, "type": g.type.value, "days_away": days})
            return ok(
                {
                    "has_data": False,
                    "message": "No fitness data yet. Log rides to build your fitness profile.",
                    "active_goals": goal_items,
                },
                t,
            )

        status = get_training_status(latest.tsb)

        goal_items = []
        for g in goals:
            days = (g.target_date - date.today()).days
            weeks = days // 7
            item: dict[str, Any] = {
                "name": g.name,
                "type": g.type.value,
                "weeks_away": weeks,
            }
            if g.target_ctl:
                progress = min(100, int(latest.ctl / g.target_ctl * 100))
                item["ctl_progress_pct"] = progress
                item["target_ctl"] = g.target_ctl
            goal_items.append(item)

        return ok(
            {
                "has_data": True,
                "ctl": latest.ctl,
                "atl": latest.atl,
                "tsb": latest.tsb,
                "status": status,
                "weekly_volume": {
                    "rides": latest.weekly_rides,
                    "distance_km": latest.weekly_km,
                    "elevation_m": latest.weekly_elevation_m,
                    "hours": latest.weekly_hours,
                },
                "active_goals": goal_items,
            },
            t,
        )
    except Exception as exc:
        logger.error("training.status_failed", error=str(exc))
        return err("INTERNAL_ERROR", f"Failed to get training status: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.get("/plan")
async def training_plan(
    goal_name: str | None = Query(None),
) -> dict[str, Any]:
    """Get training plan weeks for a goal."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, store = await _get_store()

        goal = await _resolve_goal(store, goal_name)
        if goal is None:
            return err("NOT_FOUND", "No training goal found. Create one first.")

        weeks = await store.get_training_weeks(goal.id)
        if not weeks:
            return err("NOT_FOUND", f"No training plan found for '{goal.name}'.")

        days_to_event = (goal.target_date - date.today()).days
        current_week_num = days_to_event // 7

        week_items = []
        for week in weeks:
            item = {
                "week_number": week.week_number,
                "phase": week.phase.value,
                "planned_hours": week.planned_hours,
                "planned_km": week.planned_km,
                "planned_elevation_m": week.planned_elevation_m,
                "intensity_focus": week.intensity_focus.value,
                "key_workout": week.key_workout,
                "notes": week.notes,
                "is_current_week": week.week_number == current_week_num,
            }
            week_items.append(item)

        return ok(
            {
                "goal": goal.model_dump(mode="json"),
                "days_to_event": days_to_event,
                "current_week_number": current_week_num,
                "weeks": week_items,
            },
            t,
        )
    except Exception as exc:
        logger.error("training.plan_failed", error=str(exc))
        return err("INTERNAL_ERROR", f"Failed to get training plan: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.get("/trend")
async def fitness_trend(
    days: int = Query(90, ge=1, le=365),
) -> dict[str, Any]:
    """Fitness trend snapshots over time."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, store = await _get_store()

        snapshots = await store.get_snapshots(days=days)
        if not snapshots:
            return ok(
                {
                    "has_data": False,
                    "message": f"No fitness data in the last {days} days.",
                },
                t,
            )

        snapshot_items = []
        for snap in snapshots:
            snapshot_items.append({
                "date": snap.date.isoformat(),
                "ctl": snap.ctl,
                "atl": snap.atl,
                "tsb": snap.tsb,
                "status": get_training_status(snap.tsb),
                "weekly_km": snap.weekly_km,
                "weekly_elevation_m": snap.weekly_elevation_m,
                "weekly_hours": snap.weekly_hours,
                "weekly_rides": snap.weekly_rides,
            })

        summary: dict[str, Any] = {"has_data": True, "days": days}
        if len(snapshots) >= 2:
            first = snapshots[0]
            last = snapshots[-1]
            ctl_change = last.ctl - first.ctl
            summary["ctl_start"] = first.ctl
            summary["ctl_end"] = last.ctl
            summary["ctl_change"] = round(ctl_change, 1)
            summary["ctl_direction"] = "up" if ctl_change > 0 else "down"

        summary["snapshots"] = snapshot_items
        return ok(summary, t)
    except Exception as exc:
        logger.error("training.trend_failed", error=str(exc))
        return err("INTERNAL_ERROR", f"Failed to get fitness trend: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.get("/readiness")
async def race_readiness(
    goal_name: str | None = Query(None),
) -> dict[str, Any]:
    """Race readiness check for an upcoming goal."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, store = await _get_store()

        goal = await _resolve_goal(store, goal_name)
        if goal is None:
            return err("NOT_FOUND", "No training goal found. Create one first.")

        latest = await store.get_latest_snapshot()
        if latest is None:
            return err("NO_DATA", "No fitness data yet. Log rides to assess readiness.")

        snapshots = await store.get_snapshots(days=90)

        weekly_elevations = [s.weekly_elevation_m for s in snapshots if s.weekly_elevation_m > 0]
        longest_rides = [s.weekly_km for s in snapshots if s.weekly_km > 0]

        days_to_event = (goal.target_date - date.today()).days
        weeks_to_event = days_to_event // 7

        if goal.type in (GoalType.alpencross, GoalType.marathon):
            readiness = check_alpencross_readiness(
                ctl=latest.ctl,
                weekly_elevations=weekly_elevations,
                longest_rides_km=longest_rides,
                back_to_back_count=0,
            )
        else:
            readiness = check_xc_readiness(
                ctl=latest.ctl,
                ftp_wkg=None,
                weeks_to_race=weeks_to_event,
            )

        return ok(
            {
                "goal": goal.model_dump(mode="json"),
                "days_to_event": days_to_event,
                "ready": readiness["ready"],
                "score": readiness["score"],
                "checks": readiness["checks"],
                "recommendations": readiness["recommendations"],
                "current_ctl": latest.ctl,
                "current_tsb": latest.tsb,
                "tsb_status": get_training_status(latest.tsb),
            },
            t,
        )
    except Exception as exc:
        logger.error("training.readiness_failed", error=str(exc))
        return err("INTERNAL_ERROR", f"Failed to check readiness: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.post("/plan/adjust")
async def adjust_training(body: AdjustPlanRequest) -> dict[str, Any]:
    """Adjust training plan for illness, vacation, or overtraining."""
    t = time.monotonic()

    valid_reasons = ("illness", "vacation", "overtraining", "injury")
    if body.reason not in valid_reasons:
        return err(
            "VALIDATION_ERROR",
            f"Invalid reason '{body.reason}'. Valid: {', '.join(valid_reasons)}",
        )
    if body.weeks_affected < 1:
        return err("VALIDATION_ERROR", "weeks_affected must be at least 1.")

    db: Database | None = None
    try:
        db, store = await _get_store()

        goal = await _resolve_goal(store, body.goal_name)
        if goal is None:
            return err("NOT_FOUND", "No training goal found. Create one first.")

        weeks = await store.get_training_weeks(goal.id)
        if not weeks:
            return err("NOT_FOUND", f"No training plan found for '{goal.name}'.")

        adjusted = adjust_plan(weeks, reason=body.reason, weeks_affected=body.weeks_affected)
        await store.save_training_weeks(adjusted)

        affected_weeks = []
        for week in adjusted:
            if week.notes and body.reason in (week.notes or "").lower():
                affected_weeks.append({
                    "week_number": week.week_number,
                    "planned_hours": week.planned_hours,
                    "planned_km": week.planned_km,
                    "notes": week.notes,
                })

        return ok(
            {
                "goal": goal.model_dump(mode="json"),
                "reason": body.reason,
                "weeks_affected": body.weeks_affected,
                "adjusted_weeks": affected_weeks,
            },
            t,
        )
    except Exception as exc:
        logger.error("training.adjust_failed", error=str(exc))
        return err("INTERNAL_ERROR", f"Failed to adjust plan: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.get("/suggestions")
async def weekly_suggestions(
    goal_name: str | None = Query(None),
) -> dict[str, Any]:
    """Weekly ride suggestions based on current training plan."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, store = await _get_store()

        goal = await _resolve_goal(store, goal_name)
        if goal is None:
            return err("NOT_FOUND", "No training goal found. Create one first.")

        weeks = await store.get_training_weeks(goal.id)
        if not weeks:
            return err("NOT_FOUND", f"No training plan found for '{goal.name}'.")

        days_to_event = (goal.target_date - date.today()).days
        current_week_num = days_to_event // 7

        current_week = None
        for w in weeks:
            if w.week_number == current_week_num:
                current_week = w
                break

        if current_week is None:
            current_week = min(weeks, key=lambda w: abs(w.week_number - current_week_num))

        rides = suggest_weekly_rides(current_week)

        total_hours = 0.0
        total_km = 0.0
        for ride in rides:
            dur = ride.get("duration_hours", 0)
            dist = ride.get("distance_km", 0)
            if isinstance(dur, (int, float)):
                total_hours += dur
            if isinstance(dist, (int, float)):
                total_km += dist

        return ok(
            {
                "goal": goal.model_dump(mode="json"),
                "week": {
                    "week_number": current_week.week_number,
                    "phase": current_week.phase.value,
                    "intensity_focus": current_week.intensity_focus.value,
                    "planned_hours": current_week.planned_hours,
                    "planned_km": current_week.planned_km,
                    "planned_elevation_m": current_week.planned_elevation_m,
                    "key_workout": current_week.key_workout,
                },
                "rides": rides,
                "totals": {
                    "hours": round(total_hours, 1),
                    "km": round(total_km, 0),
                },
            },
            t,
        )
    except Exception as exc:
        logger.error("training.suggestions_failed", error=str(exc))
        return err("INTERNAL_ERROR", f"Failed to get suggestions: {exc}")
    finally:
        if db is not None:
            await db.close()
