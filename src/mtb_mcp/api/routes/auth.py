"""Auth endpoints — register, login, Strava OAuth, refresh, profile."""
from __future__ import annotations

import time
from typing import Any

import structlog
from fastapi import APIRouter, Depends

from mtb_mcp.api.deps import get_cached_settings
from mtb_mcp.api.models import err, ok
from mtb_mcp.auth.dependencies import get_current_user
from mtb_mcp.auth.encryption import encrypt_token
from mtb_mcp.auth.jwt import create_access_token, create_refresh_token
from mtb_mcp.auth.models import (
    LoginRequest,
    OnboardingRequest,
    ProfileUpdateRequest,
    RefreshRequest,
    RegisterRequest,
    StravaCallbackData,
    User,
)
from mtb_mcp.auth.strava_oauth import exchange_code, get_authorize_url
from mtb_mcp.storage.bike_garage import BikeGarage
from mtb_mcp.storage.database import Database
from mtb_mcp.storage.user_store import UserStore

logger = structlog.get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _open_db() -> tuple[Database, UserStore]:
    settings = get_cached_settings()
    db = Database(settings.resolved_db_path)
    await db.initialize()
    return db, UserStore(db)


def _build_token_pair(user_id: str, secret: str) -> dict[str, str | int]:
    access = create_access_token(user_id, secret)
    refresh, refresh_hash = create_refresh_token(user_id, secret)
    return {
        "access_token": access,
        "refresh_token": refresh,
        "token_type": "bearer",
        "expires_in": 3600,
        "_refresh_hash": refresh_hash,
    }


# ---------------------------------------------------------------------------
# Strava OAuth
# ---------------------------------------------------------------------------

@router.get("/strava/authorize")
async def strava_authorize() -> dict[str, Any]:
    """Generate Strava OAuth authorization URL."""
    t = time.monotonic()
    settings = get_cached_settings()

    if not settings.strava_client_id:
        return err("CONFIG_ERROR", "Strava client_id not configured")

    url = get_authorize_url(
        client_id=settings.strava_client_id,
        redirect_uri=settings.strava_oauth_redirect_uri,
    )
    return ok({"authorize_url": url}, t)


@router.post("/strava/callback")
async def strava_callback(body: StravaCallbackData) -> dict[str, Any]:
    """Exchange Strava OAuth code for tokens, create/find user, return JWT."""
    t = time.monotonic()
    settings = get_cached_settings()

    if not settings.strava_client_id or not settings.strava_client_secret:
        return err("CONFIG_ERROR", "Strava credentials not configured")
    if not settings.jwt_secret:
        return err("CONFIG_ERROR", "JWT secret not configured")

    # Exchange code for tokens
    try:
        strava_data = await exchange_code(
            code=body.code,
            client_id=settings.strava_client_id,
            client_secret=settings.strava_client_secret,
        )
    except Exception as exc:
        logger.error("auth.strava_callback_failed", error=str(exc))
        return err("STRAVA_ERROR", f"Strava token exchange failed: {exc}")

    athlete = strava_data.get("athlete", {})
    athlete_id = athlete.get("id")
    if not athlete_id:
        return err("STRAVA_ERROR", "No athlete ID in Strava response")

    db: Database | None = None
    try:
        db, store = await _open_db()

        # Find existing user or create
        user = await store.get_user_by_strava_id(athlete_id)
        if user is None:
            display_name = f"{athlete.get('firstname', '')} {athlete.get('lastname', '')}".strip()
            if not display_name:
                display_name = f"Strava User {athlete_id}"
            user = await store.create_user(
                display_name=display_name,
                avatar_url=athlete.get("profile"),
                strava_athlete_id=athlete_id,
            )

        # Encrypt and store Strava tokens
        if settings.token_encryption_key:
            access_enc = encrypt_token(strava_data["access_token"], settings.token_encryption_key)
            refresh_enc = encrypt_token(strava_data["refresh_token"], settings.token_encryption_key)
            await store.update_strava_tokens(
                user_id=user.id,
                access_token_enc=access_enc,
                refresh_token_enc=refresh_enc,
                expires_at=strava_data.get("expires_at", 0),
            )

        # Create JWT pair
        tokens = _build_token_pair(user.id, settings.jwt_secret)
        refresh_hash = str(tokens.pop("_refresh_hash"))
        await store.store_refresh_token(user.id, refresh_hash)

        return ok(
            {
                "user": user.model_dump(),
                **tokens,
            },
            t,
        )
    except Exception as exc:
        logger.error("auth.strava_callback_error", error=str(exc))
        return err("INTERNAL_ERROR", f"Auth failed: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.post("/strava/connect")
async def strava_connect(
    body: StravaCallbackData,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Connect Strava to an already-authenticated user account."""
    t = time.monotonic()
    settings = get_cached_settings()

    if not settings.strava_client_id or not settings.strava_client_secret:
        return err("CONFIG_ERROR", "Strava credentials not configured")

    try:
        strava_data = await exchange_code(
            code=body.code,
            client_id=settings.strava_client_id,
            client_secret=settings.strava_client_secret,
        )
    except Exception as exc:
        logger.error("auth.strava_connect_failed", error=str(exc))
        return err("STRAVA_ERROR", f"Strava token exchange failed: {exc}")

    athlete = strava_data.get("athlete", {})
    athlete_id = athlete.get("id")
    if not athlete_id:
        return err("STRAVA_ERROR", "No athlete ID in Strava response")

    db: Database | None = None
    try:
        db, store = await _open_db()

        # Update user with Strava athlete ID + avatar
        await db.execute_and_commit(
            "UPDATE users SET strava_athlete_id = ?, avatar_url = COALESCE(avatar_url, ?), "
            "updated_at = ? WHERE id = ?",
            (athlete_id, athlete.get("profile"), time.strftime("%Y-%m-%dT%H:%M:%SZ"), user.id),
        )

        # Encrypt and store Strava tokens
        if settings.token_encryption_key:
            access_enc = encrypt_token(strava_data["access_token"], settings.token_encryption_key)
            refresh_enc = encrypt_token(strava_data["refresh_token"], settings.token_encryption_key)
            await store.update_strava_tokens(
                user_id=user.id,
                access_token_enc=access_enc,
                refresh_token_enc=refresh_enc,
                expires_at=strava_data.get("expires_at", 0),
            )

        updated = await store.get_user(user.id)
        return ok(
            {
                "user": updated.model_dump() if updated else user.model_dump(),
                "strava_connected": True,
                "athlete_id": athlete_id,
            },
            t,
        )
    except Exception as exc:
        logger.error("auth.strava_connect_error", error=str(exc))
        return err("INTERNAL_ERROR", f"Strava connect failed: {exc}")
    finally:
        if db is not None:
            await db.close()


# ---------------------------------------------------------------------------
# Email/Password
# ---------------------------------------------------------------------------

@router.post("/register")
async def register(body: RegisterRequest) -> dict[str, Any]:
    """Register with email and password."""
    t = time.monotonic()
    settings = get_cached_settings()
    if not settings.jwt_secret:
        return err("CONFIG_ERROR", "JWT secret not configured")

    if not body.email or not body.password:
        return err("VALIDATION_ERROR", "Email and password are required")
    if len(body.password) < 8:
        return err("VALIDATION_ERROR", "Password must be at least 8 characters")

    db: Database | None = None
    try:
        db, store = await _open_db()

        existing = await store.get_user_by_email(body.email)
        if existing is not None:
            return err("CONFLICT", "Email already registered")

        user = await store.create_user(
            display_name=body.display_name,
            email=body.email,
            password=body.password,
        )

        tokens = _build_token_pair(user.id, settings.jwt_secret)
        refresh_hash = str(tokens.pop("_refresh_hash"))
        await store.store_refresh_token(user.id, refresh_hash)

        return ok({"user": user.model_dump(), **tokens}, t)
    except Exception as exc:
        logger.error("auth.register_error", error=str(exc))
        return err("INTERNAL_ERROR", f"Registration failed: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.post("/login")
async def login(body: LoginRequest) -> dict[str, Any]:
    """Login with email and password."""
    t = time.monotonic()
    settings = get_cached_settings()
    if not settings.jwt_secret:
        return err("CONFIG_ERROR", "JWT secret not configured")

    db: Database | None = None
    try:
        db, store = await _open_db()

        user = await store.verify_password(body.email, body.password)
        if user is None:
            return err("AUTH_FAILED", "Invalid email or password")

        tokens = _build_token_pair(user.id, settings.jwt_secret)
        refresh_hash = str(tokens.pop("_refresh_hash"))
        await store.store_refresh_token(user.id, refresh_hash)

        return ok({"user": user.model_dump(), **tokens}, t)
    except Exception as exc:
        logger.error("auth.login_error", error=str(exc))
        return err("INTERNAL_ERROR", f"Login failed: {exc}")
    finally:
        if db is not None:
            await db.close()


# ---------------------------------------------------------------------------
# Token Management
# ---------------------------------------------------------------------------

@router.post("/refresh")
async def refresh_token(body: RefreshRequest) -> dict[str, Any]:
    """Refresh access token using refresh token."""
    t = time.monotonic()
    settings = get_cached_settings()
    if not settings.jwt_secret:
        return err("CONFIG_ERROR", "JWT secret not configured")

    db: Database | None = None
    try:
        db, store = await _open_db()

        token_hash = store.hash_token(body.refresh_token)
        user_id = await store.validate_refresh_token(token_hash)
        if user_id is None:
            return err("AUTH_FAILED", "Invalid or expired refresh token")

        # Issue new access token (keep same refresh token)
        access = create_access_token(user_id, settings.jwt_secret)
        return ok(
            {
                "access_token": access,
                "token_type": "bearer",
                "expires_in": 3600,
            },
            t,
        )
    except Exception as exc:
        logger.error("auth.refresh_error", error=str(exc))
        return err("INTERNAL_ERROR", f"Token refresh failed: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.post("/logout")
async def logout(user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Logout — revoke all refresh tokens."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, store = await _open_db()
        await store.revoke_refresh_tokens(user.id)
        return ok({"message": "Logged out"}, t)
    except Exception as exc:
        logger.error("auth.logout_error", error=str(exc))
        return err("INTERNAL_ERROR", f"Logout failed: {exc}")
    finally:
        if db is not None:
            await db.close()


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@router.get("/me")
async def get_me(user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Get current user profile."""
    t = time.monotonic()

    # Check if Strava is connected
    settings = get_cached_settings()
    strava_connected = False
    if settings.token_encryption_key:
        db: Database | None = None
        try:
            db, store = await _open_db()
            access_enc, _, _ = await store.get_strava_tokens(user.id)
            strava_connected = access_enc is not None
        finally:
            if db is not None:
                await db.close()

    return ok(
        {
            **user.model_dump(),
            "strava_connected": strava_connected,
        },
        t,
    )


@router.patch("/me")
async def update_me(
    body: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Update current user profile."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, store = await _open_db()
        await store.update_profile(
            user_id=user.id,
            display_name=body.display_name,
            home_lat=body.home_lat,
            home_lon=body.home_lon,
            avatar_url=body.avatar_url,
        )
        updated = await store.get_user(user.id)
        return ok(updated.model_dump() if updated else user.model_dump(), t)
    except Exception as exc:
        logger.error("auth.update_me_error", error=str(exc))
        return err("INTERNAL_ERROR", f"Profile update failed: {exc}")
    finally:
        if db is not None:
            await db.close()


@router.post("/me/onboarding")
async def complete_onboarding(
    body: OnboardingRequest,
    user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Complete onboarding with location and optional first bike."""
    t = time.monotonic()
    db: Database | None = None
    try:
        db, store = await _open_db()
        await store.complete_onboarding(user.id, body.home_lat, body.home_lon)

        # Optionally create first bike
        if body.bike_name:
            garage = BikeGarage(db)
            await garage.add_bike(
                name=body.bike_name,
                bike_type=body.bike_type or "mtb",
                user_id=user.id,
            )

        updated = await store.get_user(user.id)
        return ok(
            {
                "user": updated.model_dump() if updated else user.model_dump(),
                "message": "Onboarding complete",
            },
            t,
        )
    except Exception as exc:
        logger.error("auth.onboarding_error", error=str(exc))
        return err("INTERNAL_ERROR", f"Onboarding failed: {exc}")
    finally:
        if db is not None:
            await db.close()
