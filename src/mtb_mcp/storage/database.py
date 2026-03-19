"""Async SQLite database manager with migration support.

Usage::

    db = Database(Path("~/.mtb-mcp/mtb.db"))
    await db.initialize()  # Creates DB + runs migrations
    rows = await db.fetch_all("SELECT * FROM cache")
    await db.close()

Or as an async context manager::

    async with Database(Path("~/.mtb-mcp/mtb.db")) as db:
        rows = await db.fetch_all("SELECT * FROM cache")
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import aiosqlite
import structlog

from mtb_mcp.storage.migrations import run_migrations

logger = structlog.get_logger(__name__)


class Database:
    """Async SQLite database manager.

    Provides a thin wrapper around aiosqlite with migration support
    and convenience methods for common query patterns.
    """

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path.expanduser()
        self._conn: aiosqlite.Connection | None = None

    @property
    def connection(self) -> aiosqlite.Connection:
        """Return the active connection, raising if not initialized."""
        if self._conn is None:
            msg = "Database not initialized. Call initialize() first."
            raise RuntimeError(msg)
        return self._conn

    async def initialize(self) -> None:
        """Create database file and run pending migrations.

        Creates the parent directory if it does not exist, opens the SQLite
        connection, enables WAL mode for better concurrency, and applies
        any pending schema migrations.
        """
        # Ensure parent directory exists (skip for :memory:)
        if str(self._db_path) != ":memory:":
            self._db_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info("database.connecting", path=str(self._db_path))
        self._conn = await aiosqlite.connect(str(self._db_path))
        self._conn.row_factory = aiosqlite.Row

        # Enable WAL mode for better concurrent access
        if str(self._db_path) != ":memory:":
            await self._conn.execute("PRAGMA journal_mode=WAL")

        await run_migrations(self._conn)
        logger.info("database.ready", path=str(self._db_path))

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> aiosqlite.Cursor:
        """Execute a SQL statement and return the cursor.

        Args:
            sql: SQL statement to execute.
            params: Parameters to bind to the statement.

        Returns:
            The cursor after execution.
        """
        return await self.connection.execute(sql, params)

    async def execute_and_commit(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        """Execute a SQL statement and commit the transaction.

        Args:
            sql: SQL statement to execute.
            params: Parameters to bind to the statement.
        """
        await self.connection.execute(sql, params)
        await self.connection.commit()

    async def fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        """Execute a query and return the first row as a dict.

        Args:
            sql: SQL query to execute.
            params: Parameters to bind to the query.

        Returns:
            A dictionary of column names to values, or None if no rows match.
        """
        cursor = await self.connection.execute(sql, params)
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    async def fetch_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        """Execute a query and return all rows as a list of dicts.

        Args:
            sql: SQL query to execute.
            params: Parameters to bind to the query.

        Returns:
            A list of dictionaries, one per row.
        """
        cursor = await self.connection.execute(sql, params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            await self._conn.close()
            self._conn = None
            logger.info("database.closed")

    async def __aenter__(self) -> Database:
        """Enter the async context manager, initializing the database."""
        await self.initialize()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Exit the async context manager, closing the database."""
        await self.close()
