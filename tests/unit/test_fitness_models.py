"""Tests for fitness and training data models."""

from __future__ import annotations

from datetime import date

import pytest

from mtb_mcp.models.fitness import (
    FitnessSnapshot,
    GoalType,
    TrainingGoal,
    TrainingPhase,
    TrainingWeek,
    TrainingZone,
)


class TestGoalType:
    """Tests for the GoalType enum."""

    def test_all_values(self) -> None:
        """GoalType should have the expected values."""
        assert GoalType.alpencross == "alpencross"
        assert GoalType.xc_race == "xc_race"
        assert GoalType.enduro_race == "enduro_race"
        assert GoalType.marathon == "marathon"
        assert GoalType.personal_challenge == "personal_challenge"

    def test_from_string(self) -> None:
        """GoalType should be constructable from string."""
        assert GoalType("alpencross") == GoalType.alpencross
        assert GoalType("xc_race") == GoalType.xc_race

    def test_invalid_value(self) -> None:
        """Invalid value should raise ValueError."""
        with pytest.raises(ValueError):
            GoalType("invalid")


class TestTrainingZone:
    """Tests for the TrainingZone enum."""

    def test_all_values(self) -> None:
        """TrainingZone should have the expected values."""
        assert TrainingZone.recovery == "recovery"
        assert TrainingZone.base == "base"
        assert TrainingZone.tempo == "tempo"
        assert TrainingZone.threshold == "threshold"
        assert TrainingZone.vo2max == "vo2max"


class TestTrainingPhase:
    """Tests for the TrainingPhase enum."""

    def test_all_values(self) -> None:
        """TrainingPhase should have the expected values."""
        assert TrainingPhase.base == "base"
        assert TrainingPhase.build == "build"
        assert TrainingPhase.peak == "peak"
        assert TrainingPhase.taper == "taper"


class TestTrainingGoal:
    """Tests for the TrainingGoal model."""

    def test_minimal_goal(self) -> None:
        """TrainingGoal with required fields only."""
        goal = TrainingGoal(
            id="g1",
            name="Alpencross Ischgl-Riva",
            type=GoalType.alpencross,
            target_date=date(2026, 7, 15),
        )
        assert goal.id == "g1"
        assert goal.name == "Alpencross Ischgl-Riva"
        assert goal.type == GoalType.alpencross
        assert goal.target_date == date(2026, 7, 15)
        assert goal.target_distance_km is None
        assert goal.target_elevation_m is None
        assert goal.target_ctl is None
        assert goal.description is None
        assert goal.status == "active"

    def test_full_goal(self) -> None:
        """TrainingGoal with all fields."""
        goal = TrainingGoal(
            id="g2",
            name="XC Race",
            type=GoalType.xc_race,
            target_date=date(2026, 9, 1),
            target_distance_km=40.0,
            target_elevation_m=1200.0,
            target_ctl=65,
            description="Regional XC championship",
            status="planning",
        )
        assert goal.target_distance_km == 40.0
        assert goal.target_elevation_m == 1200.0
        assert goal.target_ctl == 65
        assert goal.description == "Regional XC championship"
        assert goal.status == "planning"


class TestTrainingWeek:
    """Tests for the TrainingWeek model."""

    def test_create_week(self) -> None:
        """TrainingWeek should hold all plan data."""
        week = TrainingWeek(
            goal_id="g1",
            week_number=12,
            phase=TrainingPhase.base,
            planned_hours=6.0,
            planned_km=108.0,
            planned_elevation_m=2400.0,
            intensity_focus=TrainingZone.base,
            key_workout="Long ride 3-4h, steady pace",
            notes="Recovery week",
        )
        assert week.goal_id == "g1"
        assert week.week_number == 12
        assert week.phase == TrainingPhase.base
        assert week.planned_hours == 6.0
        assert week.planned_km == 108.0
        assert week.planned_elevation_m == 2400.0
        assert week.intensity_focus == TrainingZone.base
        assert week.key_workout == "Long ride 3-4h, steady pace"
        assert week.notes == "Recovery week"

    def test_optional_fields(self) -> None:
        """TrainingWeek key_workout and notes are optional."""
        week = TrainingWeek(
            goal_id="g1",
            week_number=1,
            phase=TrainingPhase.taper,
            planned_hours=3.0,
            planned_km=54.0,
            planned_elevation_m=800.0,
            intensity_focus=TrainingZone.recovery,
        )
        assert week.key_workout is None
        assert week.notes is None


class TestFitnessSnapshot:
    """Tests for the FitnessSnapshot model."""

    def test_minimal_snapshot(self) -> None:
        """FitnessSnapshot with required fields only."""
        snap = FitnessSnapshot(
            date=date(2026, 3, 15),
            ctl=55.3,
            atl=62.1,
            tsb=-6.8,
        )
        assert snap.date == date(2026, 3, 15)
        assert snap.ctl == 55.3
        assert snap.atl == 62.1
        assert snap.tsb == -6.8
        assert snap.weekly_km == 0.0
        assert snap.weekly_elevation_m == 0.0
        assert snap.weekly_hours == 0.0
        assert snap.weekly_rides == 0

    def test_full_snapshot(self) -> None:
        """FitnessSnapshot with all fields."""
        snap = FitnessSnapshot(
            date=date(2026, 3, 15),
            ctl=55.3,
            atl=62.1,
            tsb=-6.8,
            weekly_km=120.5,
            weekly_elevation_m=3200.0,
            weekly_hours=7.5,
            weekly_rides=4,
        )
        assert snap.weekly_km == 120.5
        assert snap.weekly_elevation_m == 3200.0
        assert snap.weekly_hours == 7.5
        assert snap.weekly_rides == 4
