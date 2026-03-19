"""Tests for safety MCP tools."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from mtb_mcp.storage.database import Database
from mtb_mcp.tools.safety_tools import safety_timer_check, safety_timer_set


async def _make_db() -> Database:
    """Create an in-memory database with migrations applied."""
    db = Database(Path(":memory:"))
    await db.initialize()
    return db


def _mock_get_db_factory(db: Database) -> AsyncMock:
    """Create an async mock _get_db that returns db without closing it.

    We patch db.close to be a no-op so the tool's finally block
    does not destroy the in-memory database mid-test.
    """
    db.close = AsyncMock()  # type: ignore[method-assign]

    async def _fake_get_db() -> Database:
        return db

    return AsyncMock(side_effect=_fake_get_db)


class TestSafetyTimerSet:
    """Tests for the safety_timer_set tool."""

    @patch("mtb_mcp.tools.safety_tools._get_db")
    async def test_set_timer_creates_record(self, mock_get_db: AsyncMock) -> None:
        """Setting a timer should create a safety_timers row."""
        db = await _make_db()
        mock_get_db.side_effect = _mock_get_db_factory(db).side_effect

        result = await safety_timer_set(
            expected_return_time="2025-06-15 18:00",
            ride_description="Evening ride on Frankenschnellweg trail",
            emergency_contact="Alice: 0151-12345678",
        )

        assert "Safety timer set" in result
        assert "2025-06-15 18:00" in result
        assert "Frankenschnellweg" in result
        assert "Alice" in result

        # Verify database record
        rows = await db.fetch_all(
            "SELECT * FROM safety_timers WHERE status = 'active'"
        )
        assert len(rows) == 1
        assert rows[0]["ride_description"] == "Evening ride on Frankenschnellweg trail"
        assert rows[0]["emergency_contact"] == "Alice: 0151-12345678"

    @patch("mtb_mcp.tools.safety_tools._get_db")
    async def test_set_timer_time_only(self, mock_get_db: AsyncMock) -> None:
        """Setting a timer with time-only format should use today's date."""
        db = await _make_db()
        mock_get_db.side_effect = _mock_get_db_factory(db).side_effect

        result = await safety_timer_set(expected_return_time="18:00")

        assert "Safety timer set" in result
        assert "18:00" in result

    @patch("mtb_mcp.tools.safety_tools._get_db")
    async def test_set_timer_cancels_previous(self, mock_get_db: AsyncMock) -> None:
        """Setting a new timer should cancel any existing active timers."""
        db = await _make_db()
        mock_get_db.side_effect = _mock_get_db_factory(db).side_effect

        await safety_timer_set(expected_return_time="2025-06-15 14:00")
        await safety_timer_set(expected_return_time="2025-06-15 18:00")

        rows = await db.fetch_all(
            "SELECT * FROM safety_timers WHERE status = 'active'"
        )
        assert len(rows) == 1
        assert "18:00" in rows[0]["expected_return"]

        cancelled = await db.fetch_all(
            "SELECT * FROM safety_timers WHERE status = 'cancelled'"
        )
        assert len(cancelled) == 1

    async def test_set_timer_invalid_format(self) -> None:
        """Invalid time format should return an error message."""
        # _parse_return_time raises before _get_db is called,
        # but we still patch _get_db to be safe
        with patch("mtb_mcp.tools.safety_tools._get_db") as mock_get_db:
            db = await _make_db()
            mock_get_db.side_effect = _mock_get_db_factory(db).side_effect

            result = await safety_timer_set(expected_return_time="not-a-time")

            assert "Cannot parse" in result


class TestSafetyTimerCheck:
    """Tests for the safety_timer_check tool."""

    @patch("mtb_mcp.tools.safety_tools._check_strava_for_recent_activity")
    @patch("mtb_mcp.tools.safety_tools._get_db")
    async def test_check_no_active_timer(
        self, mock_get_db: AsyncMock, mock_strava: AsyncMock,
    ) -> None:
        """Should report no active timer when none exists."""
        db = await _make_db()
        mock_get_db.side_effect = _mock_get_db_factory(db).side_effect
        mock_strava.return_value = False

        result = await safety_timer_check()

        assert "No active safety timer" in result

    @patch("mtb_mcp.tools.safety_tools._check_strava_for_recent_activity")
    @patch("mtb_mcp.tools.safety_tools._get_db")
    async def test_check_active_timer_before_expected(
        self, mock_get_db: AsyncMock, mock_strava: AsyncMock,
    ) -> None:
        """Should show 'active' status when before expected return time."""
        db = await _make_db()
        mock_get_db.side_effect = _mock_get_db_factory(db).side_effect

        # Insert a timer set for the future
        future_time = datetime.now(tz=timezone.utc) + timedelta(hours=2)
        now = datetime.now(tz=timezone.utc)
        await db.execute_and_commit(
            """INSERT INTO safety_timers
               (id, expected_return, ride_description, emergency_contact,
                created_at, status)
               VALUES (?, ?, ?, ?, ?, 'active')""",
            (
                "test-timer-1",
                future_time.isoformat(),
                "Trail ride",
                "Bob: 555-1234",
                now.isoformat(),
            ),
        )

        mock_strava.return_value = False

        result = await safety_timer_check()

        assert "ACTIVE" in result
        assert "Time remaining" in result
        assert "Trail ride" in result

    @patch("mtb_mcp.tools.safety_tools._check_strava_for_recent_activity")
    @patch("mtb_mcp.tools.safety_tools._get_db")
    async def test_check_overdue_timer(
        self, mock_get_db: AsyncMock, mock_strava: AsyncMock,
    ) -> None:
        """Should show 'overdue' status when past expected return time."""
        db = await _make_db()
        mock_get_db.side_effect = _mock_get_db_factory(db).side_effect

        # Insert a timer that's already past
        past_time = datetime.now(tz=timezone.utc) - timedelta(hours=1)
        created = datetime.now(tz=timezone.utc) - timedelta(hours=3)
        await db.execute_and_commit(
            """INSERT INTO safety_timers
               (id, expected_return, ride_description, emergency_contact,
                created_at, status)
               VALUES (?, ?, ?, ?, ?, 'active')""",
            (
                "test-timer-2",
                past_time.isoformat(),
                "Mountain loop",
                "Alice: 555-5678",
                created.isoformat(),
            ),
        )

        mock_strava.return_value = False

        result = await safety_timer_check()

        assert "OVERDUE" in result
        assert "minutes" in result
        assert "Mountain loop" in result
        assert "Alice" in result

    @patch("mtb_mcp.tools.safety_tools._check_strava_for_recent_activity")
    @patch("mtb_mcp.tools.safety_tools._get_db")
    async def test_check_cleared_timer_with_strava(
        self, mock_get_db: AsyncMock, mock_strava: AsyncMock,
    ) -> None:
        """Should show 'cleared' when Strava activity is found."""
        db = await _make_db()
        mock_get_db.side_effect = _mock_get_db_factory(db).side_effect

        # Insert an active timer (past expected return)
        past_time = datetime.now(tz=timezone.utc) - timedelta(minutes=30)
        created = datetime.now(tz=timezone.utc) - timedelta(hours=2)
        await db.execute_and_commit(
            """INSERT INTO safety_timers
               (id, expected_return, ride_description, emergency_contact,
                created_at, status)
               VALUES (?, ?, ?, ?, ?, 'active')""",
            (
                "test-timer-3",
                past_time.isoformat(),
                "Quick spin",
                None,
                created.isoformat(),
            ),
        )

        mock_strava.return_value = True

        result = await safety_timer_check()

        assert "CLEARED" in result
        assert "returned safely" in result

        # Verify database was updated
        timer = await db.fetch_one(
            "SELECT * FROM safety_timers WHERE id = ?", ("test-timer-3",),
        )
        assert timer is not None
        assert timer["status"] == "cleared"
