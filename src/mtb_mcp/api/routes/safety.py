"""Safety timer endpoints."""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from mtb_mcp.api.deps import get_cached_settings
from mtb_mcp.api.models import err, ok
from mtb_mcp.auth.dependencies import get_current_user
from mtb_mcp.auth.models import User
from mtb_mcp.storage.database import Database

logger = structlog.get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class SetTimerRequest(BaseModel):
    expected_return_time: str
    ride_description: str = ""
    emergency_contact: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_return_time(expected_return_time: str) -> datetime:
    """Parse expected return time from various formats.

    Accepts:
    - Full datetime: "2024-03-20 18:00"
    - Time only (assumes today): "18:00"

    Returns:
        A timezone-aware UTC datetime.

    Raises:
        ValueError: If the string cannot be parsed.
    """
    now = datetime.now(tz=timezone.utc)

    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            parsed = datetime.strptime(expected_return_time, fmt)  # noqa: DTZ007
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

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


async def _get_db() -> Database:
    settings = get_cached_settings()
    db = Database(settings.resolved_db_path)
    await db.initialize()
    return db


async def _check_strava_for_recent_activity() -> bool:
    """Check Strava for a recent activity upload."""
    try:
        from mtb_mcp.clients.strava import StravaClient

        settings = get_cached_settings()
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
        logger.debug("safety.strava_check_failed", error=str(exc))
        return False


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/timer")
async def set_timer(body: SetTimerRequest, user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Set a safety timer for a ride."""
    t = time.monotonic()

    try:
        return_dt = _parse_return_time(body.expected_return_time)
    except ValueError as exc:
        return err("VALIDATION_ERROR", str(exc))

    timer_id = str(uuid.uuid4())
    now = datetime.now(tz=timezone.utc)

    db: Database | None = None
    try:
        db = await _get_db()

        # Deactivate any existing active timers
        await db.execute_and_commit(
            "UPDATE safety_timers SET status = 'cancelled' WHERE status = 'active' AND user_id = ?",
            (user.id,),
        )

        await db.execute_and_commit(
            """INSERT INTO safety_timers
               (id, user_id, expected_return, ride_description, emergency_contact, created_at, status)
               VALUES (?, ?, ?, ?, ?, ?, 'active')""",
            (
                timer_id,
                user.id,
                return_dt.isoformat(),
                body.ride_description,
                body.emergency_contact,
                now.isoformat(),
            ),
        )

        return ok(
            {
                "timer_id": timer_id,
                "expected_return": return_dt.strftime("%Y-%m-%d %H:%M UTC"),
                "ride_description": body.ride_description or None,
                "emergency_contact": body.emergency_contact,
                "status": "active",
            },
            t,
        )
    except Exception as exc:
        logger.error("safety.set_timer_failed", error=str(exc))
        return err("INTERNAL_ERROR", f"Failed to set timer: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.get("/timer")
async def check_timer(user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Check active safety timer status."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db = await _get_db()

        timer = await db.fetch_one(
            "SELECT * FROM safety_timers WHERE status = 'active' AND user_id = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (user.id,),
        )

        if timer is None:
            return ok(
                {
                    "active": False,
                    "message": "No active safety timer.",
                },
                t,
            )

        expected_return = datetime.fromisoformat(str(timer["expected_return"]))
        now = datetime.now(tz=timezone.utc)

        if expected_return.tzinfo is None:
            expected_return = expected_return.replace(tzinfo=timezone.utc)

        strava_activity_found = await _check_strava_for_recent_activity()

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

        result: dict[str, Any] = {
            "active": True,
            "timer_id": str(timer["id"]),
            "status": status,
            "expected_return": expected_return.strftime("%Y-%m-%d %H:%M UTC"),
            "current_time": now.strftime("%Y-%m-%d %H:%M UTC"),
            "ride_description": ride_desc,
            "emergency_contact": emergency,
        }

        if status == "overdue":
            minutes_overdue = int((now - expected_return).total_seconds() / 60)
            result["minutes_overdue"] = minutes_overdue
            result["strava_activity_found"] = False
        elif status == "cleared":
            result["strava_activity_found"] = True
        else:
            remaining = int((expected_return - now).total_seconds() / 60)
            result["minutes_remaining"] = remaining

        return ok(result, t)
    except Exception as exc:
        logger.error("safety.check_timer_failed", error=str(exc))
        return err("INTERNAL_ERROR", f"Failed to check timer: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.delete("/timer")
async def cancel_timer(user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Cancel the active safety timer."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db = await _get_db()

        timer = await db.fetch_one(
            "SELECT * FROM safety_timers WHERE status = 'active' AND user_id = ? "
            "ORDER BY created_at DESC LIMIT 1",
            (user.id,),
        )

        if timer is None:
            return err("NOT_FOUND", "No active safety timer to cancel.")

        await db.execute_and_commit(
            "UPDATE safety_timers SET status = 'cancelled' WHERE id = ?",
            (str(timer["id"]),),
        )

        return ok(
            {
                "timer_id": str(timer["id"]),
                "status": "cancelled",
            },
            t,
        )
    except Exception as exc:
        logger.error("safety.cancel_timer_failed", error=str(exc))
        return err("INTERNAL_ERROR", f"Failed to cancel timer: {exc}")
    finally:
        if db is not None:
            await db.close()
