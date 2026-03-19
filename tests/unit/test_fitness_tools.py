"""Tests for fitness MCP tools."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

from mtb_mcp.models.fitness import (
    FitnessSnapshot,
    GoalType,
    TrainingGoal,
    TrainingPhase,
    TrainingWeek,
    TrainingZone,
)
from mtb_mcp.storage.database import Database
from mtb_mcp.storage.training_store import TrainingStore
from mtb_mcp.tools.fitness_tools import (
    adjust_training_plan_tool,
    check_race_readiness,
    get_fitness_trend,
    get_training_plan,
    get_training_status_tool,
    set_training_goal,
    suggest_weekly_rides_tool,
)


def _mock_store_setup() -> tuple[AsyncMock, AsyncMock]:
    """Create mock Database and TrainingStore for tool tests."""
    mock_db = AsyncMock(spec=Database)
    mock_store = AsyncMock(spec=TrainingStore)
    return mock_db, mock_store


def _make_goal(
    name: str = "Test Event",
    goal_type: GoalType = GoalType.alpencross,
    days_away: int = 90,
) -> TrainingGoal:
    """Create a test training goal."""
    return TrainingGoal(
        id="goal-1",
        name=name,
        type=goal_type,
        target_date=date.today() + timedelta(days=days_away),
        target_distance_km=400.0,
        target_elevation_m=12000.0,
    )


def _make_snapshot(
    days_ago: int = 0,
    ctl: float = 55.0,
    atl: float = 60.0,
) -> FitnessSnapshot:
    """Create a test fitness snapshot."""
    return FitnessSnapshot(
        date=date.today() - timedelta(days=days_ago),
        ctl=ctl,
        atl=atl,
        tsb=ctl - atl,
        weekly_km=120.0,
        weekly_elevation_m=2500.0,
        weekly_hours=6.5,
        weekly_rides=4,
    )


def _make_weeks(goal_id: str = "goal-1", count: int = 4) -> list[TrainingWeek]:
    """Create test training weeks."""
    return [
        TrainingWeek(
            goal_id=goal_id,
            week_number=count - i,
            phase=TrainingPhase.build,
            planned_hours=6.0,
            planned_km=108.0,
            planned_elevation_m=2400.0,
            intensity_focus=TrainingZone.tempo,
            key_workout="Tempo ride with climbing",
        )
        for i in range(count)
    ]


# ---------------------------------------------------------------------------
# set_training_goal
# ---------------------------------------------------------------------------


class TestSetTrainingGoal:
    """Tests for the set_training_goal tool."""

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_create_goal(self, mock_get_store: AsyncMock) -> None:
        """Creating a goal should return confirmation with plan details."""
        mock_db, mock_store = _mock_store_setup()
        mock_store.get_latest_snapshot.return_value = None
        mock_store.add_goal.return_value = _make_goal()
        mock_get_store.return_value = (mock_db, mock_store)

        target = (date.today() + timedelta(days=90)).isoformat()
        result = await set_training_goal(
            name="Alpencross Ischgl-Riva",
            goal_type="alpencross",
            target_date=target,
            target_distance_km=400.0,
            target_elevation_m=12000.0,
        )

        assert "Training goal set" in result
        assert "Alpencross Ischgl-Riva" in result
        assert "alpencross" in result
        assert "weeks" in result.lower()
        mock_store.add_goal.assert_called_once()
        mock_store.save_training_weeks.assert_called_once()

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_invalid_goal_type(self, mock_get_store: AsyncMock) -> None:
        """Invalid goal type should return error."""
        mock_db, mock_store = _mock_store_setup()
        mock_get_store.return_value = (mock_db, mock_store)

        result = await set_training_goal(
            name="Test",
            goal_type="invalid",
            target_date="2026-09-01",
        )

        assert "Invalid goal type" in result

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_invalid_date_format(self, mock_get_store: AsyncMock) -> None:
        """Invalid date format should return error."""
        mock_db, mock_store = _mock_store_setup()
        mock_get_store.return_value = (mock_db, mock_store)

        result = await set_training_goal(
            name="Test",
            goal_type="xc_race",
            target_date="not-a-date",
        )

        assert "Invalid date format" in result

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_past_date_rejected(self, mock_get_store: AsyncMock) -> None:
        """Past target date should be rejected."""
        mock_db, mock_store = _mock_store_setup()
        mock_get_store.return_value = (mock_db, mock_store)

        result = await set_training_goal(
            name="Test",
            goal_type="xc_race",
            target_date="2020-01-01",
        )

        assert "must be in the future" in result

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_uses_existing_fitness(self, mock_get_store: AsyncMock) -> None:
        """Should use existing CTL for plan generation."""
        mock_db, mock_store = _mock_store_setup()
        mock_store.get_latest_snapshot.return_value = _make_snapshot(ctl=60.0)
        mock_store.add_goal.return_value = _make_goal()
        mock_get_store.return_value = (mock_db, mock_store)

        target = (date.today() + timedelta(days=90)).isoformat()
        result = await set_training_goal(
            name="Test", goal_type="alpencross", target_date=target,
        )

        assert "CTL: 60" in result


# ---------------------------------------------------------------------------
# get_training_status_tool
# ---------------------------------------------------------------------------


class TestGetTrainingStatusTool:
    """Tests for the get_training_status_tool."""

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_with_fitness_data(self, mock_get_store: AsyncMock) -> None:
        """Should show CTL/ATL/TSB when data exists."""
        mock_db, mock_store = _mock_store_setup()
        mock_store.get_latest_snapshot.return_value = _make_snapshot()
        mock_store.get_active_goals.return_value = [_make_goal()]
        mock_get_store.return_value = (mock_db, mock_store)

        result = await get_training_status_tool()

        assert "CTL" in result
        assert "ATL" in result
        assert "TSB" in result
        assert "55.0" in result  # CTL value
        assert "Active Goals" in result

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_no_fitness_data(self, mock_get_store: AsyncMock) -> None:
        """Should show helpful message when no data."""
        mock_db, mock_store = _mock_store_setup()
        mock_store.get_latest_snapshot.return_value = None
        mock_store.get_active_goals.return_value = []
        mock_get_store.return_value = (mock_db, mock_store)

        result = await get_training_status_tool()

        assert "No fitness data" in result

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_shows_weekly_volume(self, mock_get_store: AsyncMock) -> None:
        """Should show weekly volume stats."""
        mock_db, mock_store = _mock_store_setup()
        mock_store.get_latest_snapshot.return_value = _make_snapshot()
        mock_store.get_active_goals.return_value = []
        mock_get_store.return_value = (mock_db, mock_store)

        result = await get_training_status_tool()

        assert "120.0 km" in result
        assert "2500" in result  # elevation
        assert "6.5" in result  # hours


# ---------------------------------------------------------------------------
# get_training_plan
# ---------------------------------------------------------------------------


class TestGetTrainingPlan:
    """Tests for the get_training_plan tool."""

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_shows_plan(self, mock_get_store: AsyncMock) -> None:
        """Should display the training plan."""
        mock_db, mock_store = _mock_store_setup()
        goal = _make_goal()
        mock_store.get_goal_by_name.return_value = goal
        mock_store.get_active_goals.return_value = [goal]
        mock_store.get_training_weeks.return_value = _make_weeks()
        mock_get_store.return_value = (mock_db, mock_store)

        result = await get_training_plan(goal_name="Test Event")

        assert "Training Plan" in result
        assert "Test Event" in result
        assert "BUILD" in result
        assert "Tempo ride" in result

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_no_goal_found(self, mock_get_store: AsyncMock) -> None:
        """Should return helpful message when no goal exists."""
        mock_db, mock_store = _mock_store_setup()
        mock_store.get_goal_by_name.return_value = None
        mock_store.get_active_goals.return_value = []
        mock_get_store.return_value = (mock_db, mock_store)

        result = await get_training_plan()

        assert "No training goal" in result

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_uses_first_active_goal(self, mock_get_store: AsyncMock) -> None:
        """Should fall back to first active goal when no name given."""
        mock_db, mock_store = _mock_store_setup()
        goal = _make_goal()
        mock_store.get_active_goals.return_value = [goal]
        mock_store.get_training_weeks.return_value = _make_weeks()
        mock_get_store.return_value = (mock_db, mock_store)

        result = await get_training_plan()

        assert "Test Event" in result


# ---------------------------------------------------------------------------
# get_fitness_trend
# ---------------------------------------------------------------------------


class TestGetFitnessTrend:
    """Tests for the get_fitness_trend tool."""

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_shows_trend(self, mock_get_store: AsyncMock) -> None:
        """Should display fitness trend data."""
        mock_db, mock_store = _mock_store_setup()
        snapshots = [_make_snapshot(days_ago=i, ctl=40 + i * 0.5) for i in range(10)]
        mock_store.get_snapshots.return_value = list(reversed(snapshots))
        mock_get_store.return_value = (mock_db, mock_store)

        result = await get_fitness_trend(days=30)

        assert "Fitness Trend" in result
        assert "CTL" in result
        assert "ATL" in result

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_no_data(self, mock_get_store: AsyncMock) -> None:
        """Should return helpful message when no data."""
        mock_db, mock_store = _mock_store_setup()
        mock_store.get_snapshots.return_value = []
        mock_get_store.return_value = (mock_db, mock_store)

        result = await get_fitness_trend()

        assert "No fitness data" in result

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_shows_ctl_trend(self, mock_get_store: AsyncMock) -> None:
        """Should show CTL trend direction."""
        mock_db, mock_store = _mock_store_setup()
        snapshots = [
            _make_snapshot(days_ago=10, ctl=40.0),
            _make_snapshot(days_ago=0, ctl=55.0),
        ]
        mock_store.get_snapshots.return_value = snapshots
        mock_get_store.return_value = (mock_db, mock_store)

        result = await get_fitness_trend()

        assert "trend" in result.lower()
        assert "up" in result.lower()


# ---------------------------------------------------------------------------
# check_race_readiness
# ---------------------------------------------------------------------------


class TestCheckRaceReadiness:
    """Tests for the check_race_readiness tool."""

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_shows_readiness(self, mock_get_store: AsyncMock) -> None:
        """Should display readiness assessment."""
        mock_db, mock_store = _mock_store_setup()
        goal = _make_goal()
        mock_store.get_goal_by_name.return_value = goal
        mock_store.get_active_goals.return_value = [goal]
        mock_store.get_latest_snapshot.return_value = _make_snapshot(ctl=85.0)
        mock_store.get_snapshots.return_value = [_make_snapshot(ctl=85.0)]
        mock_get_store.return_value = (mock_db, mock_store)

        result = await check_race_readiness(goal_name="Test Event")

        assert "Readiness" in result
        assert "Test Event" in result
        assert "CTL" in result

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_no_goal(self, mock_get_store: AsyncMock) -> None:
        """Should return error when no goal exists."""
        mock_db, mock_store = _mock_store_setup()
        mock_store.get_goal_by_name.return_value = None
        mock_store.get_active_goals.return_value = []
        mock_get_store.return_value = (mock_db, mock_store)

        result = await check_race_readiness()

        assert "No training goal" in result

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_no_fitness_data(self, mock_get_store: AsyncMock) -> None:
        """Should return error when no fitness data."""
        mock_db, mock_store = _mock_store_setup()
        goal = _make_goal()
        mock_store.get_active_goals.return_value = [goal]
        mock_store.get_latest_snapshot.return_value = None
        mock_get_store.return_value = (mock_db, mock_store)

        result = await check_race_readiness()

        assert "No fitness data" in result

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_xc_race_readiness(self, mock_get_store: AsyncMock) -> None:
        """Should check XC-specific criteria for xc_race goals."""
        mock_db, mock_store = _mock_store_setup()
        goal = _make_goal(goal_type=GoalType.xc_race, days_away=10)
        mock_store.get_active_goals.return_value = [goal]
        mock_store.get_latest_snapshot.return_value = _make_snapshot(ctl=65.0)
        mock_store.get_snapshots.return_value = [_make_snapshot(ctl=65.0)]
        mock_get_store.return_value = (mock_db, mock_store)

        result = await check_race_readiness()

        assert "Readiness" in result


# ---------------------------------------------------------------------------
# suggest_weekly_rides_tool
# ---------------------------------------------------------------------------


class TestSuggestWeeklyRidesTool:
    """Tests for the suggest_weekly_rides_tool."""

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_suggests_rides(self, mock_get_store: AsyncMock) -> None:
        """Should suggest rides for the current week."""
        mock_db, mock_store = _mock_store_setup()
        goal = _make_goal(days_away=28)
        mock_store.get_active_goals.return_value = [goal]
        mock_store.get_training_weeks.return_value = _make_weeks()
        mock_get_store.return_value = (mock_db, mock_store)

        result = await suggest_weekly_rides_tool()

        assert "Suggested Rides" in result
        assert "Ride 1" in result

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_no_goal(self, mock_get_store: AsyncMock) -> None:
        """Should return error when no goal exists."""
        mock_db, mock_store = _mock_store_setup()
        mock_store.get_goal_by_name.return_value = None
        mock_store.get_active_goals.return_value = []
        mock_get_store.return_value = (mock_db, mock_store)

        result = await suggest_weekly_rides_tool()

        assert "No training goal" in result

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_shows_key_workout(self, mock_get_store: AsyncMock) -> None:
        """Should show the key workout from the plan."""
        mock_db, mock_store = _mock_store_setup()
        goal = _make_goal(days_away=28)
        mock_store.get_active_goals.return_value = [goal]
        mock_store.get_training_weeks.return_value = _make_weeks()
        mock_get_store.return_value = (mock_db, mock_store)

        result = await suggest_weekly_rides_tool()

        assert "Key Workout" in result


# ---------------------------------------------------------------------------
# adjust_training_plan_tool
# ---------------------------------------------------------------------------


class TestAdjustTrainingPlanTool:
    """Tests for the adjust_training_plan_tool."""

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_adjust_for_illness(self, mock_get_store: AsyncMock) -> None:
        """Should adjust plan for illness."""
        mock_db, mock_store = _mock_store_setup()
        goal = _make_goal()
        mock_store.get_active_goals.return_value = [goal]
        mock_store.get_training_weeks.return_value = _make_weeks()
        mock_get_store.return_value = (mock_db, mock_store)

        result = await adjust_training_plan_tool(reason="illness", weeks_affected=1)

        assert "adjusted" in result.lower()
        assert "illness" in result.lower()
        mock_store.save_training_weeks.assert_called_once()

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_invalid_reason(self, mock_get_store: AsyncMock) -> None:
        """Invalid reason should return error."""
        mock_db, mock_store = _mock_store_setup()
        mock_get_store.return_value = (mock_db, mock_store)

        result = await adjust_training_plan_tool(reason="boredom")

        assert "Invalid reason" in result

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_invalid_weeks(self, mock_get_store: AsyncMock) -> None:
        """Zero or negative weeks should return error."""
        mock_db, mock_store = _mock_store_setup()
        mock_get_store.return_value = (mock_db, mock_store)

        result = await adjust_training_plan_tool(reason="illness", weeks_affected=0)

        assert "at least 1" in result

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_no_goal(self, mock_get_store: AsyncMock) -> None:
        """Should return error when no goal exists."""
        mock_db, mock_store = _mock_store_setup()
        mock_store.get_goal_by_name.return_value = None
        mock_store.get_active_goals.return_value = []
        mock_get_store.return_value = (mock_db, mock_store)

        result = await adjust_training_plan_tool(reason="illness")

        assert "No training goal" in result

    @patch("mtb_mcp.tools.fitness_tools._get_store")
    async def test_vacation_adjustment(self, mock_get_store: AsyncMock) -> None:
        """Should adjust plan for vacation."""
        mock_db, mock_store = _mock_store_setup()
        goal = _make_goal()
        mock_store.get_active_goals.return_value = [goal]
        mock_store.get_training_weeks.return_value = _make_weeks()
        mock_get_store.return_value = (mock_db, mock_store)

        result = await adjust_training_plan_tool(reason="vacation", weeks_affected=2)

        assert "adjusted" in result.lower()
        assert "vacation" in result.lower()
