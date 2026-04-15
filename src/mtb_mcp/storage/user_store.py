"""User storage — CRUD for users, trainer relationships, invites, refresh tokens."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import bcrypt
import structlog

from mtb_mcp.auth.models import User

if TYPE_CHECKING:
    from mtb_mcp.storage.database import Database

logger = structlog.get_logger(__name__)


def _hash_password(password: str) -> str:
    """Hash a password with bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _row_to_user(row: dict[str, object]) -> User:
    """Convert a DB row to a User model."""
    return User(
        id=str(row["id"]),
        email=str(row["email"]) if row.get("email") else None,
        display_name=str(row["display_name"]),
        avatar_url=str(row["avatar_url"]) if row.get("avatar_url") else None,
        home_lat=float(str(row["home_lat"])) if row.get("home_lat") is not None else None,
        home_lon=float(str(row["home_lon"])) if row.get("home_lon") is not None else None,
        strava_athlete_id=int(str(row["strava_athlete_id"]))
        if row.get("strava_athlete_id") is not None
        else None,
        onboarding_done=bool(row.get("onboarding_done", False)),
    )


class UserStore:
    """Manage users, trainer relationships, invites in SQLite."""

    def __init__(self, db: Database) -> None:
        self._db = db

    # -----------------------------------------------------------------------
    # Users
    # -----------------------------------------------------------------------

    async def create_user(
        self,
        display_name: str,
        email: str | None = None,
        password: str | None = None,
        avatar_url: str | None = None,
        strava_athlete_id: int | None = None,
    ) -> User:
        """Create a new user."""
        user_id = str(uuid.uuid4())
        now = _now_iso()
        password_hash = _hash_password(password) if password else None

        await self._db.execute_and_commit(
            "INSERT INTO users "
            "(id, email, display_name, avatar_url, password_hash, "
            "strava_athlete_id, onboarding_done, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, FALSE, ?, ?)",
            (user_id, email, display_name, avatar_url, password_hash,
             strava_athlete_id, now, now),
        )
        logger.info("user_store.user_created", user_id=user_id, email=email)
        return User(
            id=user_id,
            email=email,
            display_name=display_name,
            avatar_url=avatar_url,
            strava_athlete_id=strava_athlete_id,
        )

    async def get_user(self, user_id: str) -> User | None:
        """Get a user by ID."""
        row = await self._db.fetch_one(
            "SELECT * FROM users WHERE id = ?", (user_id,),
        )
        if row is None:
            return None
        return _row_to_user(row)

    async def get_user_by_email(self, email: str) -> User | None:
        """Get a user by email."""
        row = await self._db.fetch_one(
            "SELECT * FROM users WHERE email = ?", (email,),
        )
        if row is None:
            return None
        return _row_to_user(row)

    async def get_user_by_strava_id(self, strava_athlete_id: int) -> User | None:
        """Get a user by Strava athlete ID."""
        row = await self._db.fetch_one(
            "SELECT * FROM users WHERE strava_athlete_id = ?", (strava_athlete_id,),
        )
        if row is None:
            return None
        return _row_to_user(row)

    async def verify_password(self, email: str, password: str) -> User | None:
        """Verify email/password and return User or None."""
        row = await self._db.fetch_one(
            "SELECT * FROM users WHERE email = ?", (email,),
        )
        if row is None:
            return None
        pw_hash = row.get("password_hash")
        if not pw_hash or not _verify_password(password, str(pw_hash)):
            return None
        return _row_to_user(row)

    async def update_profile(
        self,
        user_id: str,
        display_name: str | None = None,
        home_lat: float | None = None,
        home_lon: float | None = None,
        avatar_url: str | None = None,
    ) -> None:
        """Update user profile fields."""
        updates: list[str] = []
        params: list[object] = []
        if display_name is not None:
            updates.append("display_name = ?")
            params.append(display_name)
        if home_lat is not None:
            updates.append("home_lat = ?")
            params.append(home_lat)
        if home_lon is not None:
            updates.append("home_lon = ?")
            params.append(home_lon)
        if avatar_url is not None:
            updates.append("avatar_url = ?")
            params.append(avatar_url)
        if not updates:
            return
        updates.append("updated_at = ?")
        params.append(_now_iso())
        params.append(user_id)
        sql = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
        await self._db.execute_and_commit(sql, tuple(params))

    async def complete_onboarding(
        self,
        user_id: str,
        home_lat: float,
        home_lon: float,
    ) -> None:
        """Mark onboarding as complete with home location."""
        await self._db.execute_and_commit(
            "UPDATE users SET home_lat = ?, home_lon = ?, onboarding_done = TRUE, "
            "updated_at = ? WHERE id = ?",
            (home_lat, home_lon, _now_iso(), user_id),
        )

    # -----------------------------------------------------------------------
    # Strava Tokens (encrypted)
    # -----------------------------------------------------------------------

    async def update_strava_tokens(
        self,
        user_id: str,
        access_token_enc: str,
        refresh_token_enc: str,
        expires_at: int,
    ) -> None:
        """Store encrypted Strava tokens."""
        await self._db.execute_and_commit(
            "UPDATE users SET strava_access_token_enc = ?, "
            "strava_refresh_token_enc = ?, strava_token_expires_at = ?, "
            "updated_at = ? WHERE id = ?",
            (access_token_enc, refresh_token_enc, expires_at, _now_iso(), user_id),
        )

    async def get_strava_tokens(
        self, user_id: str,
    ) -> tuple[str | None, str | None, int]:
        """Get encrypted Strava tokens.

        Returns:
            (access_token_enc, refresh_token_enc, expires_at)
        """
        row = await self._db.fetch_one(
            "SELECT strava_access_token_enc, strava_refresh_token_enc, "
            "strava_token_expires_at FROM users WHERE id = ?",
            (user_id,),
        )
        if row is None:
            return None, None, 0
        return (
            str(row["strava_access_token_enc"]) if row["strava_access_token_enc"] else None,
            str(row["strava_refresh_token_enc"]) if row["strava_refresh_token_enc"] else None,
            int(str(row["strava_token_expires_at"])) if row["strava_token_expires_at"] else 0,
        )

    # -----------------------------------------------------------------------
    # Trainer Relationships
    # -----------------------------------------------------------------------

    async def add_trainer(
        self, rider_id: str, trainer_id: str, ai_trainer: bool = False,
    ) -> str:
        """Create a trainer relationship."""
        rel_id = str(uuid.uuid4())
        await self._db.execute_and_commit(
            "INSERT INTO trainer_relationships "
            "(id, rider_id, trainer_id, status, ai_trainer, created_at) "
            "VALUES (?, ?, ?, 'active', ?, ?)",
            (rel_id, rider_id, trainer_id, ai_trainer, _now_iso()),
        )
        logger.info("user_store.trainer_added", rider_id=rider_id, trainer_id=trainer_id)
        return rel_id

    async def get_trainer(self, rider_id: str) -> User | None:
        """Get the active trainer for a rider."""
        row = await self._db.fetch_one(
            "SELECT u.* FROM users u "
            "JOIN trainer_relationships tr ON tr.trainer_id = u.id "
            "WHERE tr.rider_id = ? AND tr.status = 'active'",
            (rider_id,),
        )
        if row is None:
            return None
        return _row_to_user(row)

    async def get_athletes(self, trainer_id: str) -> list[User]:
        """Get all athletes for a trainer."""
        rows = await self._db.fetch_all(
            "SELECT u.* FROM users u "
            "JOIN trainer_relationships tr ON tr.rider_id = u.id "
            "WHERE tr.trainer_id = ? AND tr.status = 'active'",
            (trainer_id,),
        )
        return [_row_to_user(row) for row in rows]

    async def is_trainer_of(self, trainer_id: str, rider_id: str) -> bool:
        """Check if trainer_id is an active trainer of rider_id."""
        row = await self._db.fetch_one(
            "SELECT 1 FROM trainer_relationships "
            "WHERE trainer_id = ? AND rider_id = ? AND status = 'active'",
            (trainer_id, rider_id),
        )
        return row is not None

    async def remove_trainer(self, rider_id: str) -> None:
        """Remove active trainer relationship for a rider."""
        await self._db.execute_and_commit(
            "UPDATE trainer_relationships SET status = 'removed' "
            "WHERE rider_id = ? AND status = 'active'",
            (rider_id,),
        )

    # -----------------------------------------------------------------------
    # Invite Links
    # -----------------------------------------------------------------------

    async def create_invite_link(self, rider_id: str) -> tuple[str, str]:
        """Create a trainer invite link.

        Returns:
            (invite_id, token)
        """
        invite_id = str(uuid.uuid4())
        token = str(uuid.uuid4())
        expires = (datetime.now(tz=timezone.utc) + timedelta(days=7)).isoformat()
        await self._db.execute_and_commit(
            "INSERT INTO invite_links (id, rider_id, token, expires_at, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (invite_id, rider_id, token, expires, _now_iso()),
        )
        return invite_id, token

    async def get_invite_link(self, token: str) -> dict[str, object] | None:
        """Get an invite link by token."""
        row = await self._db.fetch_one(
            "SELECT * FROM invite_links WHERE token = ?", (token,),
        )
        if row is None:
            return None
        return row

    async def use_invite_link(self, token: str, used_by: str) -> bool:
        """Mark an invite link as used.

        Returns:
            True if the invite was valid and used, False otherwise.
        """
        row = await self._db.fetch_one(
            "SELECT * FROM invite_links WHERE token = ? AND used_by IS NULL",
            (token,),
        )
        if row is None:
            return False

        expires_at = datetime.fromisoformat(str(row["expires_at"]))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(tz=timezone.utc) > expires_at:
            return False

        await self._db.execute_and_commit(
            "UPDATE invite_links SET used_by = ? WHERE token = ?",
            (used_by, token),
        )
        return True

    # -----------------------------------------------------------------------
    # Refresh Tokens
    # -----------------------------------------------------------------------

    async def store_refresh_token(
        self, user_id: str, token_hash: str,
    ) -> None:
        """Store a hashed refresh token."""
        token_id = str(uuid.uuid4())
        expires = (datetime.now(tz=timezone.utc) + timedelta(days=30)).isoformat()
        await self._db.execute_and_commit(
            "INSERT INTO refresh_tokens (id, user_id, token_hash, expires_at, created_at, revoked) "
            "VALUES (?, ?, ?, ?, ?, FALSE)",
            (token_id, user_id, token_hash, expires, _now_iso()),
        )

    async def validate_refresh_token(self, token_hash: str) -> str | None:
        """Validate a refresh token hash. Returns user_id or None."""
        row = await self._db.fetch_one(
            "SELECT * FROM refresh_tokens "
            "WHERE token_hash = ? AND revoked = FALSE",
            (token_hash,),
        )
        if row is None:
            return None

        expires_at = datetime.fromisoformat(str(row["expires_at"]))
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if datetime.now(tz=timezone.utc) > expires_at:
            return None

        return str(row["user_id"])

    async def revoke_refresh_tokens(self, user_id: str) -> None:
        """Revoke all refresh tokens for a user."""
        await self._db.execute_and_commit(
            "UPDATE refresh_tokens SET revoked = TRUE WHERE user_id = ?",
            (user_id,),
        )

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash a token for storage."""
        return hashlib.sha256(token.encode()).hexdigest()
