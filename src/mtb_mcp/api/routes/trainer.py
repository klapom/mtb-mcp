"""Trainer endpoints — invite, accept, athlete list, read-only data."""
from __future__ import annotations

import time
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from mtb_mcp.api.deps import get_cached_settings
from mtb_mcp.api.models import err, ok, ok_list
from mtb_mcp.auth.dependencies import get_current_user
from mtb_mcp.auth.models import User
from mtb_mcp.storage.database import Database
from mtb_mcp.storage.training_store import TrainingStore
from mtb_mcp.storage.user_store import UserStore

logger = structlog.get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class AcceptInviteRequest(BaseModel):
    token: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _open_db() -> tuple[Database, UserStore]:
    settings = get_cached_settings()
    db = Database(settings.resolved_db_path)
    await db.initialize()
    return db, UserStore(db)


async def _verify_trainer_access(
    store: UserStore, trainer_id: str, rider_id: str,
) -> None:
    """Verify trainer has access to rider's data."""
    if not await store.is_trainer_of(trainer_id, rider_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this athlete's data",
        )


# ---------------------------------------------------------------------------
# Rider-side: manage trainer
# ---------------------------------------------------------------------------

@router.post("/invite")
async def create_invite(
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Generate a trainer invite link (7 days validity)."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, store = await _open_db()
        invite_id, token = await store.create_invite_link(user.id)
        return ok(
            {
                "invite_id": invite_id,
                "token": token,
                "expires_in_days": 7,
            },
            t,
        )
    except Exception as exc:
        logger.error("trainer.create_invite_error", error=str(exc))
        return err("INTERNAL_ERROR", f"Failed to create invite: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.get("/my-trainer")
async def get_my_trainer(
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the current user's active trainer."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, store = await _open_db()
        trainer = await store.get_trainer(user.id)
        if trainer is None:
            return ok({"has_trainer": False}, t)
        return ok(
            {
                "has_trainer": True,
                "trainer": trainer.model_dump(),
            },
            t,
        )
    except Exception as exc:
        logger.error("trainer.get_my_trainer_error", error=str(exc))
        return err("INTERNAL_ERROR", f"Failed to get trainer: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.delete("/remove-trainer")
async def remove_trainer(
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Remove the current trainer relationship."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, store = await _open_db()
        await store.remove_trainer(user.id)
        return ok({"message": "Trainer removed"}, t)
    except Exception as exc:
        logger.error("trainer.remove_trainer_error", error=str(exc))
        return err("INTERNAL_ERROR", f"Failed to remove trainer: {exc}")
    finally:
        if db is not None:
            await db.close()


# ---------------------------------------------------------------------------
# Accept invite
# ---------------------------------------------------------------------------

@router.post("/accept-invite")
async def accept_invite(
    body: AcceptInviteRequest,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Accept a trainer invite link."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, store = await _open_db()

        invite = await store.get_invite_link(body.token)
        if invite is None:
            return err("NOT_FOUND", "Invalid invite link")

        rider_id = str(invite["rider_id"])
        if rider_id == user.id:
            return err("VALIDATION_ERROR", "Cannot be your own trainer")

        used = await store.use_invite_link(body.token, user.id)
        if not used:
            return err("EXPIRED", "Invite link expired or already used")

        rel_id = await store.add_trainer(rider_id=rider_id, trainer_id=user.id)

        return ok(
            {
                "relationship_id": rel_id,
                "rider_id": rider_id,
                "message": "Trainer relationship created",
            },
            t,
        )
    except Exception as exc:
        logger.error("trainer.accept_invite_error", error=str(exc))
        return err("INTERNAL_ERROR", f"Failed to accept invite: {exc}")
    finally:
        if db is not None:
            await db.close()


# ---------------------------------------------------------------------------
# Trainer-side: view athletes
# ---------------------------------------------------------------------------

@router.get("/athletes")
async def list_athletes(
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get all athletes for this trainer."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, store = await _open_db()
        athletes = await store.get_athletes(user.id)
        items = [a.model_dump() for a in athletes]
        return ok_list(items, len(items), t)
    except Exception as exc:
        logger.error("trainer.list_athletes_error", error=str(exc))
        return err("INTERNAL_ERROR", f"Failed to list athletes: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.get("/athletes/{athlete_id}/fitness")
async def athlete_fitness(
    athlete_id: str,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get an athlete's fitness data (read-only for trainer)."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, store = await _open_db()
        await _verify_trainer_access(store, user.id, athlete_id)

        training = TrainingStore(db)
        latest = await training.get_latest_snapshot(user_id=athlete_id)
        if latest is None:
            return ok({"has_data": False}, t)

        return ok(
            {
                "has_data": True,
                "ctl": latest.ctl,
                "atl": latest.atl,
                "tsb": latest.tsb,
                "weekly_km": latest.weekly_km,
                "weekly_elevation_m": latest.weekly_elevation_m,
                "weekly_hours": latest.weekly_hours,
                "weekly_rides": latest.weekly_rides,
            },
            t,
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("trainer.athlete_fitness_error", error=str(exc))
        return err("INTERNAL_ERROR", f"Failed to get athlete fitness: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.get("/athletes/{athlete_id}/goals")
async def athlete_goals(
    athlete_id: str,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get an athlete's training goals (read-only for trainer)."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, store = await _open_db()
        await _verify_trainer_access(store, user.id, athlete_id)

        training = TrainingStore(db)
        goals = await training.get_active_goals(user_id=athlete_id)
        items = [g.model_dump(mode="json") for g in goals]
        return ok_list(items, len(items), t)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("trainer.athlete_goals_error", error=str(exc))
        return err("INTERNAL_ERROR", f"Failed to get athlete goals: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.get("/athletes/{athlete_id}/activities")
async def athlete_activities(
    athlete_id: str,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get an athlete's Strava activities (read-only for trainer)."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, store = await _open_db()
        await _verify_trainer_access(store, user.id, athlete_id)

        # Get athlete's Strava tokens
        settings = get_cached_settings()
        if not settings.token_encryption_key:
            return err("CONFIG_ERROR", "Token encryption not configured")

        from mtb_mcp.auth.encryption import decrypt_token
        from mtb_mcp.clients.strava import StravaClient

        access_enc, refresh_enc, expires_at = await store.get_strava_tokens(athlete_id)
        if not access_enc:
            return ok({"has_strava": False, "activities": []}, t)

        access_token = decrypt_token(access_enc, settings.token_encryption_key)
        refresh_token = decrypt_token(refresh_enc, settings.token_encryption_key) if refresh_enc else None

        client = StravaClient(
            client_id=settings.strava_client_id,
            client_secret=settings.strava_client_secret,
            access_token=access_token,
            refresh_token=refresh_token,
        )

        try:
            async with client:
                activities = await client.get_recent_activities(limit=10, sport_type=None)
        except Exception as exc:
            return err("EXTERNAL_API_ERROR", f"Strava API error: {exc}")

        items = [a.model_dump(mode="json") for a in activities]
        return ok_list(items, len(items), t)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("trainer.athlete_activities_error", error=str(exc))
        return err("INTERNAL_ERROR", f"Failed to get athlete activities: {exc}")
    finally:
        if db is not None:
            await db.close()
