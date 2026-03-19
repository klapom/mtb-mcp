"""MCP tools for ride safety."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog

from mtb_mcp.config import get_settings
from mtb_mcp.server import mcp
from mtb_mcp.storage.database import Database

logger = structlog.get_logger(__name__)


async def _get_db() -> Database:
    """Initialize a Database from settings.

    Returns:
        A Database instance. Caller must close it.
    """
    settings = get_settings()
    db = Database(settings.resolved_db_path)
    await db.initialize()
    return db


def _parse_return_time(expected_return_time: str) -> datetime:
    """Parse expected return time from various formats.

    Accepts:
    - Full datetime: "2024-03-20 18:00"
    - Time only (assumes today): "18:00"

    Returns:
        A timezone-aware UTC datetime.
    """
    now = datetime.now(tz=timezone.utc)

    # Try full datetime first
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            parsed = datetime.strptime(expected_return_time, fmt)  # noqa: DTZ007
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    # Try time only (assume today)
    try:
        parsed_time = datetime.strptime(expected_return_time, "%H:%M")  # noqa: DTZ007
        return now.replace(
            hour=parsed_time.hour,
            minute=parsed_time.minute,
            second=0,
            microsecond=0,
        )
    except ValueError:
        pass

    msg = (
        f"Cannot parse '{expected_return_time}'. "
        "Use 'YYYY-MM-DD HH:MM' or 'HH:MM' format."
    )
    raise ValueError(msg)


async def _check_strava_for_recent_activity() -> bool:
    """Check Strava for a recent activity upload.

    Returns:
        True if a recent activity was found, False otherwise.
    """
    try:
        from mtb_mcp.clients.strava import StravaClient

        settings = get_settings()
        if not settings.strava_access_token:
            return False

        async with StravaClient(
            access_token=settings.strava_access_token,
        ) as strava:
            activities = await strava.get_recent_activities(
                limit=1, sport_type=None,
            )
            return len(activities) > 0
    except Exception as exc:
        logger.debug("safety_timer.strava_check_failed", error=str(exc))
        return False


@mcp.tool()
async def safety_timer_set(
    expected_return_time: str,
    ride_description: str = "",
    emergency_contact: str | None = None,
) -> str:
    """Set a safety timer for your ride. If you haven't uploaded a Strava activity
    by the expected return time, the timer will flag it.

    expected_return_time: When you expect to be back (e.g. "2024-03-20 18:00" or "18:00" for today)
    ride_description: Brief description of your planned ride
    emergency_contact: Optional phone number or name for emergency reference
    """
    try:
        return_dt = _parse_return_time(expected_return_time)
    except ValueError as exc:
        return str(exc)

    timer_id = str(uuid.uuid4())
    now = datetime.now(tz=timezone.utc)

    db: Database | None = None
    try:
        db = await _get_db()

        # Deactivate any existing active timers
        await db.execute_and_commit(
            "UPDATE safety_timers SET status = 'cancelled' WHERE status = 'active'",
        )

        await db.execute_and_commit(
            """INSERT INTO safety_timers
               (id, expected_return, ride_description, emergency_contact, created_at, status)
               VALUES (?, ?, ?, ?, ?, 'active')""",
            (
                timer_id,
                return_dt.isoformat(),
                ride_description,
                emergency_contact,
                now.isoformat(),
            ),
        )

        lines = [
            "Safety timer set",
            f"  Timer ID: {timer_id}",
            f"  Expected return: {return_dt.strftime('%Y-%m-%d %H:%M')} UTC",
        ]
        if ride_description:
            lines.append(f"  Ride: {ride_description}")
        if emergency_contact:
            lines.append(f"  Emergency contact: {emergency_contact}")

        lines.extend([
            "",
            "Use safety_timer_check to verify your status after the ride.",
        ])

        return "\n".join(lines)
    finally:
        if db is not None:
            await db.close()


@mcp.tool()
async def safety_timer_check() -> str:
    """Check if there's an active safety timer and whether the rider has returned.
    Checks for recent Strava activity uploads as confirmation of safe return."""
    db: Database | None = None
    try:
        db = await _get_db()

        timer = await db.fetch_one(
            "SELECT * FROM safety_timers WHERE status = 'active' "
            "ORDER BY created_at DESC LIMIT 1",
        )

        if timer is None:
            return (
                "No active safety timer. "
                "Use safety_timer_set to create one before your ride."
            )

        expected_return = datetime.fromisoformat(str(timer["expected_return"]))
        now = datetime.now(tz=timezone.utc)

        # Ensure expected_return is tz-aware for comparison
        if expected_return.tzinfo is None:
            expected_return = expected_return.replace(tzinfo=timezone.utc)

        # Check for recent Strava activity as proof of safe return
        strava_activity_found = await _check_strava_for_recent_activity()

        # Determine status
        if strava_activity_found:
            status = "cleared"
            await db.execute_and_commit(
                "UPDATE safety_timers SET status = 'cleared' WHERE id = ?",
                (str(timer["id"]),),
            )
        elif now > expected_return:
            status = "overdue"
        else:
            status = "active"

        ride_desc = (
            str(timer["ride_description"]) if timer["ride_description"] else None
        )
        emergency = (
            str(timer["emergency_contact"]) if timer["emergency_contact"] else None
        )

        lines = [
            f"Safety Timer Status: {status.upper()}",
            f"  Expected return: {expected_return.strftime('%Y-%m-%d %H:%M')} UTC",
            f"  Current time: {now.strftime('%Y-%m-%d %H:%M')} UTC",
        ]

        if ride_desc:
            lines.append(f"  Ride: {ride_desc}")
        if emergency:
            lines.append(f"  Emergency contact: {emergency}")

        if status == "overdue":
            minutes_overdue = int((now - expected_return).total_seconds() / 60)
            lines.extend([
                "",
                f"  OVERDUE by {minutes_overdue} minutes!",
                "  No recent Strava activity detected.",
            ])
            if emergency:
                lines.append(f"  Consider contacting: {emergency}")
        elif status == "cleared":
            lines.extend([
                "",
                "  Recent Strava activity found -- rider appears to have returned safely.",
            ])
        else:
            remaining = int((expected_return - now).total_seconds() / 60)
            lines.extend([
                "",
                f"  Time remaining: {remaining} minutes",
            ])

        return "\n".join(lines)
    finally:
        if db is not None:
            await db.close()
