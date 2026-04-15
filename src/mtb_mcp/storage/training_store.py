"""Training plan and fitness data storage.

Usage::

    async with Database(Path(":memory:")) as db:
        store = TrainingStore(db)
        goal = await store.add_goal("Alpencross", "alpencross", date(2026, 7, 15))
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import TYPE_CHECKING

import structlog

from mtb_mcp.models.fitness import (
    FitnessSnapshot,
    GoalType,
    TrainingGoal,
    TrainingPhase,
    TrainingWeek,
    TrainingZone,
)

if TYPE_CHECKING:
    from mtb_mcp.storage.database import Database

logger = structlog.get_logger(__name__)


class TrainingStore:
    """Manage training goals, plans, and fitness data in SQLite."""

    def __init__(self, db: Database) -> None:
        self._db = db

    # -----------------------------------------------------------------------
    # Goals
    # -----------------------------------------------------------------------

    async def add_goal(
        self,
        name: str,
        goal_type: str,
        target_date: date,
        target_distance_km: float | None = None,
        target_elevation_m: float | None = None,
        target_ctl: int | None = None,
        description: str | None = None,
        user_id: str | None = None,
    ) -> TrainingGoal:
        """Add a new training goal.

        Args:
            name: Human-readable goal name.
            goal_type: One of GoalType values.
            target_date: Target event date.
            target_distance_km: Target distance in km.
            target_elevation_m: Target elevation in metres.
            target_ctl: Target CTL to achieve.
            description: Optional description.
            user_id: Owner user ID.

        Returns:
            The newly created TrainingGoal.
        """
        # Validate goal type
        GoalType(goal_type)

        goal_id = str(uuid.uuid4())
        await self._db.execute_and_commit(
            "INSERT INTO training_goals "
            "(id, name, type, target_date, target_distance_km, target_elevation_m, "
            "target_ctl, description, status, user_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)",
            (
                goal_id, name, goal_type, target_date.isoformat(),
                target_distance_km, target_elevation_m, target_ctl, description,
                user_id,
            ),
        )
        logger.info("training_store.goal_added", goal_id=goal_id, name=name)
        return TrainingGoal(
            id=goal_id,
            name=name,
            type=GoalType(goal_type),
            target_date=target_date,
            target_distance_km=target_distance_km,
            target_elevation_m=target_elevation_m,
            target_ctl=target_ctl,
            description=description,
            status="active",
        )

    async def get_goal(self, goal_id: str) -> TrainingGoal | None:
        """Get a training goal by ID.

        Args:
            goal_id: The goal's UUID.

        Returns:
            The TrainingGoal, or None if not found.
        """
        row = await self._db.fetch_one(
            "SELECT * FROM training_goals WHERE id = ?", (goal_id,),
        )
        if row is None:
            return None
        return _row_to_goal(row)

    async def get_goal_by_name(
        self, name: str, user_id: str | None = None,
    ) -> TrainingGoal | None:
        """Get a training goal by name (case-insensitive).

        Args:
            name: Goal name to search for.
            user_id: Owner filter.

        Returns:
            The TrainingGoal, or None if not found.
        """
        if user_id is not None:
            row = await self._db.fetch_one(
                "SELECT * FROM training_goals WHERE LOWER(name) = LOWER(?) AND user_id = ?",
                (name, user_id),
            )
        else:
            row = await self._db.fetch_one(
                "SELECT * FROM training_goals WHERE LOWER(name) = LOWER(?)", (name,),
            )
        if row is None:
            return None
        return _row_to_goal(row)

    async def get_active_goals(self, user_id: str | None = None) -> list[TrainingGoal]:
        """Get all active training goals.

        Args:
            user_id: Owner filter.

        Returns:
            List of active TrainingGoal objects.
        """
        if user_id is not None:
            rows = await self._db.fetch_all(
                "SELECT * FROM training_goals WHERE status = 'active' AND user_id = ? "
                "ORDER BY target_date",
                (user_id,),
            )
        else:
            rows = await self._db.fetch_all(
                "SELECT * FROM training_goals WHERE status = 'active' ORDER BY target_date",
            )
        return [_row_to_goal(row) for row in rows]

    async def update_goal_status(self, goal_id: str, status: str) -> None:
        """Update a goal's status.

        Args:
            goal_id: The goal's UUID.
            status: New status (planning, active, completed, abandoned).
        """
        await self._db.execute_and_commit(
            "UPDATE training_goals SET status = ? WHERE id = ?",
            (status, goal_id),
        )
        logger.info("training_store.goal_status_updated", goal_id=goal_id, status=status)

    # -----------------------------------------------------------------------
    # Training Weeks
    # -----------------------------------------------------------------------

    async def save_training_weeks(self, weeks: list[TrainingWeek]) -> None:
        """Save (upsert) training weeks for a goal.

        Args:
            weeks: List of TrainingWeek objects to save.
        """
        for week in weeks:
            await self._db.execute_and_commit(
                "INSERT OR REPLACE INTO training_weeks "
                "(goal_id, week_number, phase, planned_hours, planned_km, "
                "planned_elevation_m, intensity_focus, key_workout, notes) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    week.goal_id, week.week_number, week.phase.value,
                    week.planned_hours, week.planned_km, week.planned_elevation_m,
                    week.intensity_focus.value, week.key_workout, week.notes,
                ),
            )
        logger.info(
            "training_store.weeks_saved",
            count=len(weeks),
            goal_id=weeks[0].goal_id if weeks else None,
        )

    async def get_training_weeks(self, goal_id: str) -> list[TrainingWeek]:
        """Get all training weeks for a goal.

        Args:
            goal_id: The goal's UUID.

        Returns:
            List of TrainingWeek objects, sorted by week number descending.
        """
        rows = await self._db.fetch_all(
            "SELECT * FROM training_weeks WHERE goal_id = ? ORDER BY week_number DESC",
            (goal_id,),
        )
        return [
            TrainingWeek(
                goal_id=row["goal_id"],
                week_number=row["week_number"],
                phase=TrainingPhase(row["phase"]),
                planned_hours=row["planned_hours"],
                planned_km=row["planned_km"],
                planned_elevation_m=row["planned_elevation_m"],
                intensity_focus=TrainingZone(row["intensity_focus"]),
                key_workout=row["key_workout"],
                notes=row["notes"],
            )
            for row in rows
        ]

    # -----------------------------------------------------------------------
    # Fitness Snapshots
    # -----------------------------------------------------------------------

    async def save_snapshot(
        self, snapshot: FitnessSnapshot, user_id: str | None = None,
    ) -> None:
        """Save (upsert) a fitness snapshot.

        Args:
            snapshot: The FitnessSnapshot to save.
            user_id: Owner user ID.
        """
        await self._db.execute_and_commit(
            "INSERT OR REPLACE INTO fitness_snapshots "
            "(user_id, date, ctl, atl, tsb, weekly_km, weekly_elevation_m, "
            "weekly_hours, weekly_rides) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                user_id or "", snapshot.date.isoformat(),
                snapshot.ctl, snapshot.atl, snapshot.tsb,
                snapshot.weekly_km, snapshot.weekly_elevation_m,
                snapshot.weekly_hours, snapshot.weekly_rides,
            ),
        )

    async def get_snapshots(
        self, days: int = 90, user_id: str | None = None,
    ) -> list[FitnessSnapshot]:
        """Get fitness snapshots for the last N days.

        Args:
            days: Number of days to look back.
            user_id: Owner filter.

        Returns:
            List of FitnessSnapshot objects, sorted by date.
        """
        since = (date.today() - timedelta(days=days)).isoformat()
        if user_id is not None:
            rows = await self._db.fetch_all(
                "SELECT * FROM fitness_snapshots WHERE date >= ? AND user_id = ? ORDER BY date",
                (since, user_id),
            )
        else:
            rows = await self._db.fetch_all(
                "SELECT * FROM fitness_snapshots WHERE date >= ? ORDER BY date",
                (since,),
            )
        return [
            FitnessSnapshot(
                date=date.fromisoformat(row["date"]),
                ctl=row["ctl"],
                atl=row["atl"],
                tsb=row["tsb"],
                weekly_km=row["weekly_km"],
                weekly_elevation_m=row["weekly_elevation_m"],
                weekly_hours=row["weekly_hours"],
                weekly_rides=row["weekly_rides"],
            )
            for row in rows
        ]

    async def get_latest_snapshot(self, user_id: str | None = None) -> FitnessSnapshot | None:
        """Get the most recent fitness snapshot.

        Args:
            user_id: Owner filter.

        Returns:
            The most recent FitnessSnapshot, or None if no snapshots exist.
        """
        if user_id is not None:
            row = await self._db.fetch_one(
                "SELECT * FROM fitness_snapshots WHERE user_id = ? ORDER BY date DESC LIMIT 1",
                (user_id,),
            )
        else:
            row = await self._db.fetch_one(
                "SELECT * FROM fitness_snapshots ORDER BY date DESC LIMIT 1",
            )
        if row is None:
            return None
        return FitnessSnapshot(
            date=date.fromisoformat(row["date"]),
            ctl=row["ctl"],
            atl=row["atl"],
            tsb=row["tsb"],
            weekly_km=row["weekly_km"],
            weekly_elevation_m=row["weekly_elevation_m"],
            weekly_hours=row["weekly_hours"],
            weekly_rides=row["weekly_rides"],
        )


def _row_to_goal(row: dict[str, object]) -> TrainingGoal:
    """Convert a database row dict to a TrainingGoal model."""
    target_date_raw = row["target_date"]
    assert isinstance(target_date_raw, str)

    raw_dist = row.get("target_distance_km")
    target_distance_km = float(str(raw_dist)) if raw_dist is not None else None

    raw_elev = row.get("target_elevation_m")
    target_elevation_m = float(str(raw_elev)) if raw_elev is not None else None

    raw_ctl = row.get("target_ctl")
    target_ctl = int(float(str(raw_ctl))) if raw_ctl is not None else None

    return TrainingGoal(
        id=str(row["id"]),
        name=str(row["name"]),
        type=GoalType(str(row["type"])),
        target_date=date.fromisoformat(target_date_raw),
        target_distance_km=target_distance_km,
        target_elevation_m=target_elevation_m,
        target_ctl=target_ctl,
        description=str(row["description"]) if row.get("description") is not None else None,
        status=str(row["status"]),
    )
