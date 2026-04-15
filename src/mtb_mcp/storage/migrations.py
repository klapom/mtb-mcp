"""Database schema migrations.

Migrations are applied in order by version number. Each migration is a tuple of
(version, description, sql). The schema_version table tracks which migrations
have been applied.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    import aiosqlite

logger = structlog.get_logger(__name__)

# (version, description, sql)
MIGRATIONS: list[tuple[int, str, str]] = [
    (
        1,
        "Create schema_version table",
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at REAL NOT NULL,
            description TEXT
        );
        """,
    ),
    (
        2,
        "Create cache table",
        """
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            created_at REAL NOT NULL,
            ttl_seconds REAL NOT NULL
        );
        """,
    ),
    (
        3,
        "Create bikes table",
        """
        CREATE TABLE IF NOT EXISTS bikes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            brand TEXT,
            model TEXT,
            bike_type TEXT DEFAULT 'mtb',
            total_km REAL DEFAULT 0,
            strava_gear_id TEXT
        );
        """,
    ),
    (
        4,
        "Create components table",
        """
        CREATE TABLE IF NOT EXISTS components (
            id TEXT PRIMARY KEY,
            bike_id TEXT NOT NULL REFERENCES bikes(id),
            type TEXT NOT NULL,
            brand TEXT,
            model TEXT,
            installed_date TEXT NOT NULL,
            installed_km REAL DEFAULT 0,
            current_effective_km REAL DEFAULT 0,
            current_hours REAL DEFAULT 0
        );
        """,
    ),
    (
        5,
        "Create service_log table",
        """
        CREATE TABLE IF NOT EXISTS service_log (
            id TEXT PRIMARY KEY,
            bike_id TEXT NOT NULL REFERENCES bikes(id),
            component_type TEXT NOT NULL,
            service_type TEXT NOT NULL,
            date TEXT NOT NULL,
            notes TEXT
        );
        """,
    ),
    (
        6,
        "Create safety_timers table",
        """
        CREATE TABLE IF NOT EXISTS safety_timers (
            id TEXT PRIMARY KEY,
            expected_return TEXT NOT NULL,
            ride_description TEXT,
            emergency_contact TEXT,
            created_at TEXT NOT NULL,
            status TEXT DEFAULT 'active'
        );
        """,
    ),
    (
        7,
        "Create training_goals table",
        """
        CREATE TABLE IF NOT EXISTS training_goals (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            target_date TEXT NOT NULL,
            target_distance_km REAL,
            target_elevation_m REAL,
            target_ctl INTEGER,
            description TEXT,
            status TEXT DEFAULT 'active'
        );
        """,
    ),
    (
        8,
        "Create training_weeks table",
        """
        CREATE TABLE IF NOT EXISTS training_weeks (
            goal_id TEXT NOT NULL REFERENCES training_goals(id),
            week_number INTEGER NOT NULL,
            phase TEXT NOT NULL,
            planned_hours REAL NOT NULL,
            planned_km REAL NOT NULL,
            planned_elevation_m REAL NOT NULL,
            intensity_focus TEXT NOT NULL,
            key_workout TEXT,
            notes TEXT,
            PRIMARY KEY (goal_id, week_number)
        );
        """,
    ),
    (
        9,
        "Create fitness_snapshots table",
        """
        CREATE TABLE IF NOT EXISTS fitness_snapshots (
            date TEXT PRIMARY KEY,
            ctl REAL NOT NULL,
            atl REAL NOT NULL,
            tsb REAL NOT NULL,
            weekly_km REAL DEFAULT 0,
            weekly_elevation_m REAL DEFAULT 0,
            weekly_hours REAL DEFAULT 0,
            weekly_rides INTEGER DEFAULT 0
        );
        """,
    ),
    (
        10,
        "Create users table",
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            email TEXT UNIQUE,
            display_name TEXT NOT NULL,
            avatar_url TEXT,
            password_hash TEXT,
            home_lat REAL,
            home_lon REAL,
            strava_athlete_id INTEGER UNIQUE,
            strava_access_token_enc TEXT,
            strava_refresh_token_enc TEXT,
            strava_token_expires_at INTEGER DEFAULT 0,
            onboarding_done BOOLEAN DEFAULT FALSE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """,
    ),
    (
        11,
        "Create trainer_relationships table",
        """
        CREATE TABLE IF NOT EXISTS trainer_relationships (
            id TEXT PRIMARY KEY,
            rider_id TEXT NOT NULL REFERENCES users(id),
            trainer_id TEXT NOT NULL REFERENCES users(id),
            status TEXT DEFAULT 'pending',
            ai_trainer BOOLEAN DEFAULT FALSE,
            created_at TEXT NOT NULL,
            UNIQUE(rider_id, trainer_id)
        );
        """,
    ),
    (
        12,
        "Create refresh_tokens table",
        """
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL REFERENCES users(id),
            token_hash TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            revoked BOOLEAN DEFAULT FALSE
        );
        """,
    ),
    (
        13,
        "Create invite_links table",
        """
        CREATE TABLE IF NOT EXISTS invite_links (
            id TEXT PRIMARY KEY,
            rider_id TEXT NOT NULL REFERENCES users(id),
            token TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            used_by TEXT REFERENCES users(id),
            created_at TEXT NOT NULL
        );
        """,
    ),
    (
        14,
        "Add user_id to data tables",
        """
        ALTER TABLE bikes ADD COLUMN user_id TEXT;
        ALTER TABLE components ADD COLUMN user_id TEXT;
        ALTER TABLE service_log ADD COLUMN user_id TEXT;
        ALTER TABLE safety_timers ADD COLUMN user_id TEXT;
        ALTER TABLE training_goals ADD COLUMN user_id TEXT;
        ALTER TABLE training_weeks ADD COLUMN user_id TEXT;
        ALTER TABLE fitness_snapshots ADD COLUMN user_id TEXT;
        CREATE INDEX idx_bikes_user ON bikes(user_id);
        CREATE INDEX idx_training_goals_user ON training_goals(user_id);
        CREATE INDEX idx_safety_timers_user ON safety_timers(user_id);
        CREATE INDEX idx_fitness_snapshots_user ON fitness_snapshots(user_id);
        """,
    ),
    (
        15,
        "Recreate fitness_snapshots with composite PK",
        """
        CREATE TABLE IF NOT EXISTS fitness_snapshots_new (
            user_id TEXT NOT NULL,
            date TEXT NOT NULL,
            ctl REAL NOT NULL,
            atl REAL NOT NULL,
            tsb REAL NOT NULL,
            weekly_km REAL DEFAULT 0,
            weekly_elevation_m REAL DEFAULT 0,
            weekly_hours REAL DEFAULT 0,
            weekly_rides INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, date)
        );
        INSERT INTO fitness_snapshots_new (user_id, date, ctl, atl, tsb, weekly_km, weekly_elevation_m, weekly_hours, weekly_rides)
            SELECT COALESCE(user_id, ''), date, ctl, atl, tsb, weekly_km, weekly_elevation_m, weekly_hours, weekly_rides
            FROM fitness_snapshots;
        DROP TABLE fitness_snapshots;
        ALTER TABLE fitness_snapshots_new RENAME TO fitness_snapshots;
        """,
    ),
]


async def _get_current_version(conn: aiosqlite.Connection) -> int:
    """Get the current schema version, or 0 if no migrations have been applied."""
    # Check if schema_version table exists
    cursor = await conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_version'"
    )
    row = await cursor.fetchone()
    if row is None:
        return 0

    cursor = await conn.execute("SELECT MAX(version) FROM schema_version")
    row = await cursor.fetchone()
    if row is None or row[0] is None:
        return 0
    return int(row[0])


async def run_migrations(conn: aiosqlite.Connection) -> None:
    """Run pending migrations against the given connection.

    Args:
        conn: An open aiosqlite connection.
    """
    current_version = await _get_current_version(conn)
    pending = [m for m in MIGRATIONS if m[0] > current_version]

    if not pending:
        logger.debug("database.migrations.none_pending", current_version=current_version)
        return

    for version, description, sql in pending:
        logger.info(
            "database.migration.applying",
            version=version,
            description=description,
        )
        await conn.executescript(sql)

        # Record the migration (schema_version table exists after migration 1)
        if version >= 1:
            await conn.execute(
                "INSERT OR REPLACE INTO schema_version (version, applied_at, description) "
                "VALUES (?, ?, ?)",
                (version, time.time(), description),
            )
        await conn.commit()

    logger.info(
        "database.migrations.complete",
        applied=len(pending),
        new_version=pending[-1][0],
    )
