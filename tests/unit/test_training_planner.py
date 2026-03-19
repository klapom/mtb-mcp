"""Tests for training plan generation with periodization."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from mtb_mcp.intelligence.training_planner import (
    _allocate_phases,
    adjust_plan,
    generate_training_plan,
    suggest_weekly_rides,
)
from mtb_mcp.models.fitness import (
    GoalType,
    TrainingGoal,
    TrainingPhase,
    TrainingWeek,
    TrainingZone,
)

# ---------------------------------------------------------------------------
# Phase Allocation
# ---------------------------------------------------------------------------


class TestAllocatePhases:
    """Tests for phase allocation logic."""

    def test_standard_12_week_plan(self) -> None:
        """12 weeks should distribute across all phases."""
        phases = _allocate_phases(12)
        phase_dict = dict(phases)

        assert TrainingPhase.base in phase_dict
        assert TrainingPhase.build in phase_dict
        assert TrainingPhase.peak in phase_dict
        assert TrainingPhase.taper in phase_dict

        total = sum(c for _, c in phases)
        assert total == 12

    def test_minimum_1_week_per_phase(self) -> None:
        """With 4+ weeks, each phase gets at least 1 week."""
        phases = _allocate_phases(4)
        phase_dict = dict(phases)

        for phase in TrainingPhase:
            assert phase in phase_dict
            assert phase_dict[phase] >= 1

    def test_very_short_plan(self) -> None:
        """2-week plan should have base + taper."""
        phases = _allocate_phases(2)
        assert len(phases) == 2
        assert phases[0][0] == TrainingPhase.base
        assert phases[1][0] == TrainingPhase.taper

    def test_single_week(self) -> None:
        """1-week plan should be taper only."""
        phases = _allocate_phases(1)
        assert len(phases) == 1
        assert phases[0] == (TrainingPhase.taper, 1)

    def test_total_weeks_always_match(self) -> None:
        """Allocated weeks should always sum to the input."""
        for total in range(1, 30):
            phases = _allocate_phases(total)
            assert sum(c for _, c in phases) == total

    def test_base_is_largest_phase(self) -> None:
        """Base phase should get the most weeks for plans >= 8 weeks."""
        phases = _allocate_phases(16)
        phase_dict = dict(phases)
        assert phase_dict[TrainingPhase.base] >= phase_dict[TrainingPhase.build]
        assert phase_dict[TrainingPhase.base] >= phase_dict[TrainingPhase.peak]
        assert phase_dict[TrainingPhase.base] >= phase_dict[TrainingPhase.taper]


# ---------------------------------------------------------------------------
# Plan Generation
# ---------------------------------------------------------------------------


class TestGenerateTrainingPlan:
    """Tests for training plan generation."""

    def _make_goal(
        self,
        goal_type: GoalType = GoalType.alpencross,
        weeks_ahead: int = 16,
    ) -> TrainingGoal:
        """Create a test goal."""
        return TrainingGoal(
            id="test-goal",
            name="Test Event",
            type=goal_type,
            target_date=date.today() + timedelta(weeks=weeks_ahead),
        )

    def test_generates_correct_number_of_weeks(self) -> None:
        """Plan should have the expected number of weeks."""
        goal = self._make_goal(weeks_ahead=12)
        plan = generate_training_plan(goal, weeks_available=12)
        assert len(plan) == 12

    def test_all_weeks_have_goal_id(self) -> None:
        """All weeks should reference the goal."""
        goal = self._make_goal()
        plan = generate_training_plan(goal, weeks_available=12)
        for week in plan:
            assert week.goal_id == "test-goal"

    def test_week_numbers_are_countdown(self) -> None:
        """Week numbers should count down to 1."""
        goal = self._make_goal()
        plan = generate_training_plan(goal, weeks_available=8)
        week_nums = sorted([w.week_number for w in plan], reverse=True)
        assert week_nums[0] == 8
        assert week_nums[-1] == 1

    def test_phases_in_correct_order(self) -> None:
        """Phases should follow base -> build -> peak -> taper."""
        goal = self._make_goal()
        plan = generate_training_plan(goal, weeks_available=12)

        # Sort by week_number descending (furthest from event first)
        sorted_plan = sorted(plan, key=lambda w: -w.week_number)

        phases_seen: list[TrainingPhase] = []
        for week in sorted_plan:
            if not phases_seen or phases_seen[-1] != week.phase:
                phases_seen.append(week.phase)

        expected_order = [TrainingPhase.base, TrainingPhase.build,
                          TrainingPhase.peak, TrainingPhase.taper]
        assert phases_seen == expected_order

    def test_taper_has_reduced_volume(self) -> None:
        """Taper weeks should have lower volume than build/peak weeks."""
        goal = self._make_goal()
        plan = generate_training_plan(goal, weeks_available=12, current_ctl=50.0)

        taper_weeks = [w for w in plan if w.phase == TrainingPhase.taper]
        build_weeks = [w for w in plan if w.phase == TrainingPhase.build]

        assert taper_weeks  # At least one taper week
        assert build_weeks  # At least one build week

        avg_taper_hours = sum(w.planned_hours for w in taper_weeks) / len(taper_weeks)
        avg_build_hours = sum(w.planned_hours for w in build_weeks) / len(build_weeks)

        assert avg_taper_hours < avg_build_hours

    def test_volume_increases_during_base(self) -> None:
        """Volume should generally increase during base phase."""
        goal = self._make_goal()
        plan = generate_training_plan(goal, weeks_available=16, current_ctl=30.0)

        base_weeks = sorted(
            [w for w in plan if w.phase == TrainingPhase.base],
            key=lambda w: -w.week_number,
        )

        if len(base_weeks) >= 3:
            # First base week should have less volume than last base week
            assert base_weeks[-1].planned_hours >= base_weeks[0].planned_hours

    def test_different_goal_types(self) -> None:
        """Different goal types should produce valid plans."""
        for goal_type in GoalType:
            goal = self._make_goal(goal_type=goal_type)
            plan = generate_training_plan(goal, weeks_available=8)
            assert len(plan) == 8
            assert all(w.planned_hours > 0 or w.phase == TrainingPhase.taper for w in plan)

    def test_higher_ctl_means_more_volume(self) -> None:
        """Higher current CTL should start with higher base volume."""
        goal = self._make_goal()
        plan_low = generate_training_plan(goal, weeks_available=8, current_ctl=20.0)
        plan_high = generate_training_plan(goal, weeks_available=8, current_ctl=60.0)

        first_low = sorted(plan_low, key=lambda w: -w.week_number)[0]
        first_high = sorted(plan_high, key=lambda w: -w.week_number)[0]

        assert first_high.planned_hours >= first_low.planned_hours

    def test_key_workouts_present(self) -> None:
        """Key workouts should be assigned to weeks."""
        goal = self._make_goal(goal_type=GoalType.alpencross)
        plan = generate_training_plan(goal, weeks_available=12)

        key_workouts = [w.key_workout for w in plan if w.key_workout]
        assert len(key_workouts) > 0


# ---------------------------------------------------------------------------
# Weekly Ride Suggestions
# ---------------------------------------------------------------------------


class TestSuggestWeeklyRides:
    """Tests for weekly ride suggestion logic."""

    def _make_week(
        self, zone: TrainingZone = TrainingZone.base, hours: float = 6.0,
    ) -> TrainingWeek:
        """Create a test training week."""
        return TrainingWeek(
            goal_id="test",
            week_number=8,
            phase=TrainingPhase.base,
            planned_hours=hours,
            planned_km=hours * 18,
            planned_elevation_m=hours * 400,
            intensity_focus=zone,
        )

    def test_base_zone_multiple_rides(self) -> None:
        """Base zone should suggest multiple rides."""
        week = self._make_week(zone=TrainingZone.base, hours=6.0)
        rides = suggest_weekly_rides(week)
        assert len(rides) >= 2

    def test_recovery_zone_single_ride(self) -> None:
        """Recovery zone should suggest at most one short ride."""
        week = self._make_week(zone=TrainingZone.recovery, hours=2.0)
        rides = suggest_weekly_rides(week)
        assert len(rides) >= 1
        for ride in rides:
            duration = ride.get("duration_hours", 0)
            assert isinstance(duration, (int, float))
            assert duration <= 2.0

    def test_threshold_zone_includes_intervals(self) -> None:
        """Threshold zone should include interval work."""
        week = self._make_week(zone=TrainingZone.threshold, hours=6.0)
        rides = suggest_weekly_rides(week)

        descriptions = " ".join(str(r.get("description", "")) for r in rides)
        types = " ".join(str(r.get("type", "")) for r in rides)

        assert "interval" in descriptions.lower() or "threshold" in (descriptions + types).lower()

    def test_vo2max_zone_includes_max_effort(self) -> None:
        """VO2max zone should include max effort work."""
        week = self._make_week(zone=TrainingZone.vo2max, hours=5.0)
        rides = suggest_weekly_rides(week)

        types = " ".join(str(r.get("type", "")) for r in rides)
        assert "vo2max" in types.lower() or "VO2" in types

    def test_tempo_zone_includes_sustained(self) -> None:
        """Tempo zone should include sustained effort."""
        week = self._make_week(zone=TrainingZone.tempo, hours=6.0)
        rides = suggest_weekly_rides(week)

        descriptions = " ".join(str(r.get("description", "")) for r in rides)
        assert "tempo" in descriptions.lower()

    def test_bad_weather_adds_note(self) -> None:
        """Bad weather should add indoor trainer note."""
        week = self._make_week()
        rides = suggest_weekly_rides(
            week,
            weather_forecast={"precipitation_probability": 90},
        )

        has_weather_note = any("weather_note" in r for r in rides)
        assert has_weather_note

    def test_rides_have_duration_and_distance(self) -> None:
        """All rides should have duration and distance."""
        week = self._make_week()
        rides = suggest_weekly_rides(week)

        for ride in rides:
            assert "duration_hours" in ride
            assert "distance_km" in ride
            assert isinstance(ride["duration_hours"], (int, float))
            assert isinstance(ride["distance_km"], (int, float))

    @pytest.mark.parametrize("zone", list(TrainingZone))
    def test_all_zones_produce_rides(self, zone: TrainingZone) -> None:
        """Every training zone should produce at least one ride suggestion."""
        week = self._make_week(zone=zone, hours=5.0)
        rides = suggest_weekly_rides(week)
        assert len(rides) >= 1

    def test_available_tours_matched(self) -> None:
        """Available tours should be matched to rides."""
        week = self._make_week(zone=TrainingZone.base, hours=6.0)
        tours = [
            {"name": "Forest Loop", "distance_km": 25.0},
            {"name": "Mountain Pass", "distance_km": 60.0},
        ]
        rides = suggest_weekly_rides(week, available_tours=tours)

        has_tour = any("suggested_tour" in r for r in rides)
        assert has_tour


# ---------------------------------------------------------------------------
# Plan Adjustment
# ---------------------------------------------------------------------------


class TestAdjustPlan:
    """Tests for plan adjustment logic."""

    def _make_plan(self, weeks: int = 8) -> list[TrainingWeek]:
        """Create a test training plan."""
        return [
            TrainingWeek(
                goal_id="test",
                week_number=weeks - i,
                phase=TrainingPhase.build,
                planned_hours=6.0,
                planned_km=108.0,
                planned_elevation_m=2400.0,
                intensity_focus=TrainingZone.tempo,
                key_workout="Tempo ride",
            )
            for i in range(weeks)
        ]

    def test_illness_reduces_volume(self) -> None:
        """Illness should reduce volume by 50% for affected weeks."""
        plan = self._make_plan()
        adjusted = adjust_plan(plan, reason="illness", weeks_affected=2)

        # Sort by week_number descending (same as original)
        sorted_adj = sorted(adjusted, key=lambda w: -w.week_number)

        # First 2 weeks (highest week_number) should be reduced
        for week in sorted_adj[:2]:
            assert week.planned_hours == pytest.approx(3.0, abs=0.1)
            assert week.intensity_focus == TrainingZone.recovery
            assert week.key_workout is None
            assert "illness" in (week.notes or "").lower()

    def test_illness_adds_transition_week(self) -> None:
        """Illness should add a transition week after affected weeks."""
        plan = self._make_plan()
        adjusted = adjust_plan(plan, reason="illness", weeks_affected=1)
        sorted_adj = sorted(adjusted, key=lambda w: -w.week_number)

        # Second week should be transition
        assert "transition" in (sorted_adj[1].notes or "").lower()
        assert sorted_adj[1].planned_hours == pytest.approx(6.0 * 0.7, abs=0.1)

    def test_vacation_zeros_volume(self) -> None:
        """Vacation should set volume to zero."""
        plan = self._make_plan()
        adjusted = adjust_plan(plan, reason="vacation", weeks_affected=1)
        sorted_adj = sorted(adjusted, key=lambda w: -w.week_number)

        assert sorted_adj[0].planned_hours == 0.0
        assert sorted_adj[0].planned_km == 0.0
        assert "vacation" in (sorted_adj[0].notes or "").lower()

    def test_overtraining_heavy_reduction(self) -> None:
        """Overtraining should reduce volume to 30%."""
        plan = self._make_plan()
        adjusted = adjust_plan(plan, reason="overtraining", weeks_affected=1)
        sorted_adj = sorted(adjusted, key=lambda w: -w.week_number)

        assert sorted_adj[0].planned_hours == pytest.approx(6.0 * 0.3, abs=0.1)
        assert sorted_adj[0].intensity_focus == TrainingZone.recovery

    def test_injury_zeros_volume(self) -> None:
        """Injury should set volume to zero."""
        plan = self._make_plan()
        adjusted = adjust_plan(plan, reason="injury", weeks_affected=2)
        sorted_adj = sorted(adjusted, key=lambda w: -w.week_number)

        for week in sorted_adj[:2]:
            assert week.planned_hours == 0.0
            assert "injury" in (week.notes or "").lower()

    def test_unaffected_weeks_unchanged(self) -> None:
        """Weeks beyond the affected range should remain unchanged."""
        plan = self._make_plan(weeks=8)
        adjusted = adjust_plan(plan, reason="illness", weeks_affected=1)
        sorted_adj = sorted(adjusted, key=lambda w: -w.week_number)

        # Weeks 3+ (index 2+) should be unchanged (after illness + transition)
        for week in sorted_adj[2:]:
            assert week.planned_hours == 6.0
            assert week.intensity_focus == TrainingZone.tempo

    def test_empty_plan(self) -> None:
        """Empty plan should return empty list."""
        result = adjust_plan([], reason="illness")
        assert result == []

    def test_preserves_plan_length(self) -> None:
        """Adjustment should not add or remove weeks."""
        plan = self._make_plan(weeks=8)
        adjusted = adjust_plan(plan, reason="vacation", weeks_affected=2)
        assert len(adjusted) == 8

    @pytest.mark.parametrize("reason", ["illness", "vacation", "overtraining", "injury"])
    def test_all_reasons_produce_valid_plan(self, reason: str) -> None:
        """All adjustment reasons should produce a valid adjusted plan."""
        plan = self._make_plan(weeks=6)
        adjusted = adjust_plan(plan, reason=reason, weeks_affected=1)

        assert len(adjusted) == 6
        for week in adjusted:
            assert week.planned_hours >= 0
            assert week.planned_km >= 0
            assert week.planned_elevation_m >= 0
