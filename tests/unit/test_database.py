"""Tests for mtb_mcp.storage.database and migrations."""

from __future__ import annotations

from pathlib import Path

import pytest

from mtb_mcp.storage.database import Database
from mtb_mcp.storage.migrations import MIGRATIONS


class TestDatabaseLifecycle:
    """Test Database creation, initialization, and cleanup."""

    async def test_initialize_in_memory(self) -> None:
        """Database should initialize with an in-memory SQLite DB."""
        db = Database(Path(":memory:"))
        await db.initialize()
        try:
            # Schema version table should exist after migrations
            rows = await db.fetch_all("SELECT * FROM schema_version")
            assert len(rows) > 0
        finally:
            await db.close()

    async def test_context_manager(self) -> None:
        """Database should work as an async context manager."""
        async with Database(Path(":memory:")) as db:
            rows = await db.fetch_all("SELECT * FROM schema_version")
            assert len(rows) > 0

    async def test_close_sets_conn_none(self) -> None:
        """After close(), the connection should be None."""
        db = Database(Path(":memory:"))
        await db.initialize()
        await db.close()
        with pytest.raises(RuntimeError, match="not initialized"):
            db.connection  # noqa: B018

    async def test_connection_property_raises_before_init(self) -> None:
        """Accessing connection before initialize() should raise RuntimeError."""
        db = Database(Path(":memory:"))
        with pytest.raises(RuntimeError, match="not initialized"):
            db.connection  # noqa: B018

    async def test_initialize_creates_directory(self, tmp_path: Path) -> None:
        """initialize() should create the parent directory if needed."""
        db_path = tmp_path / "subdir" / "nested" / "test.db"
        async with Database(db_path) as db:
            rows = await db.fetch_all("SELECT * FROM schema_version")
            assert len(rows) > 0
        assert db_path.exists()


class TestDatabaseQueries:
    """Test execute, fetch_one, and fetch_all."""

    async def test_execute_and_fetch_all(self) -> None:
        """execute() and fetch_all() should work for basic CRUD."""
        async with Database(Path(":memory:")) as db:
            await db.execute_and_commit(
                "INSERT INTO cache (key, value, created_at, ttl_seconds) VALUES (?, ?, ?, ?)",
                ("test_key", '{"data": 1}', 1000.0, 3600.0),
            )
            rows = await db.fetch_all("SELECT * FROM cache WHERE key = ?", ("test_key",))
            assert len(rows) == 1
            assert rows[0]["key"] == "test_key"
            assert rows[0]["value"] == '{"data": 1}'

    async def test_fetch_one_returns_dict(self) -> None:
        """fetch_one() should return a dict with column names as keys."""
        async with Database(Path(":memory:")) as db:
            await db.execute_and_commit(
                "INSERT INTO cache (key, value, created_at, ttl_seconds) VALUES (?, ?, ?, ?)",
                ("k1", '"hello"', 1000.0, 3600.0),
            )
            row = await db.fetch_one("SELECT * FROM cache WHERE key = ?", ("k1",))
            assert row is not None
            assert isinstance(row, dict)
            assert row["key"] == "k1"

    async def test_fetch_one_returns_none_for_no_match(self) -> None:
        """fetch_one() should return None when no rows match."""
        async with Database(Path(":memory:")) as db:
            row = await db.fetch_one("SELECT * FROM cache WHERE key = ?", ("nonexistent",))
            assert row is None

    async def test_fetch_all_returns_empty_list(self) -> None:
        """fetch_all() should return an empty list when no rows match."""
        async with Database(Path(":memory:")) as db:
            rows = await db.fetch_all("SELECT * FROM cache WHERE key = ?", ("nonexistent",))
            assert rows == []

    async def test_execute_returns_cursor(self) -> None:
        """execute() should return an aiosqlite cursor."""
        async with Database(Path(":memory:")) as db:
            cursor = await db.execute("SELECT COUNT(*) as cnt FROM cache")
            row = await cursor.fetchone()
            assert row is not None


class TestMigrations:
    """Test that migrations are applied correctly."""

    async def test_all_migrations_applied(self) -> None:
        """All defined migrations should be recorded in schema_version."""
        async with Database(Path(":memory:")) as db:
            rows = await db.fetch_all(
                "SELECT version, description FROM schema_version ORDER BY version"
            )
            versions = [r["version"] for r in rows]
            for version, description, _ in MIGRATIONS:
                assert version in versions, f"Migration {version} ({description}) not applied"

    async def test_migrations_are_idempotent(self) -> None:
        """Running initialize() twice should not fail or duplicate migrations."""
        db = Database(Path(":memory:"))
        await db.initialize()
        # Run migrations again (simulates restart)
        from mtb_mcp.storage.migrations import run_migrations

        await run_migrations(db.connection)
        rows = await db.fetch_all("SELECT version FROM schema_version")
        versions = [r["version"] for r in rows]
        # No duplicates
        assert len(versions) == len(set(versions))
        await db.close()

    async def test_cache_table_exists(self) -> None:
        """The cache table should exist after migrations."""
        async with Database(Path(":memory:")) as db:
            rows = await db.fetch_all(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='cache'"
            )
            assert len(rows) == 1
            assert rows[0]["name"] == "cache"
