"""Tests for mtb_mcp.storage.cache."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from mtb_mcp.storage.cache import ResponseCache
from mtb_mcp.storage.database import Database


@pytest.fixture
async def db() -> Database:
    """Create an in-memory database for testing."""
    database = Database(Path(":memory:"))
    await database.initialize()
    yield database  # type: ignore[misc]
    await database.close()


@pytest.fixture
async def cache(db: Database) -> ResponseCache:
    """Create a ResponseCache backed by an in-memory database."""
    return ResponseCache(db)


class TestCacheSetGet:
    """Test basic set/get operations."""

    async def test_set_and_get(self, cache: ResponseCache) -> None:
        """set() followed by get() should return the cached value."""
        data = {"temperature": 22.5, "condition": "sunny"}
        await cache.set("weather:49.59,11.00", data, ttl=3600)
        result = await cache.get("weather:49.59,11.00")
        assert result == data

    async def test_get_nonexistent_key(self, cache: ResponseCache) -> None:
        """get() for a missing key should return None."""
        result = await cache.get("nonexistent:key")
        assert result is None

    async def test_set_overwrites_existing(self, cache: ResponseCache) -> None:
        """set() with an existing key should overwrite the previous value."""
        await cache.set("key1", {"v": 1}, ttl=3600)
        await cache.set("key1", {"v": 2}, ttl=3600)
        result = await cache.get("key1")
        assert result == {"v": 2}

    async def test_set_preserves_unicode(self, cache: ResponseCache) -> None:
        """Cache should correctly store and retrieve unicode values."""
        data = {"name": "Frankenweg", "description": "Schoner Weg"}
        await cache.set("trail:1", data, ttl=3600)
        result = await cache.get("trail:1")
        assert result == data


class TestCacheTTL:
    """Test TTL expiration behavior."""

    async def test_get_returns_none_when_expired(self, cache: ResponseCache) -> None:
        """get() should return None for expired entries."""
        now = 1000.0
        with patch("mtb_mcp.storage.cache.time") as mock_time:
            # Set at time=1000 with TTL=60s
            mock_time.time.return_value = now
            await cache.set("key", {"data": 1}, ttl=60)

            # Read at time=1061 (expired)
            mock_time.time.return_value = now + 61
            result = await cache.get("key")
            assert result is None

    async def test_get_returns_value_before_expiry(self, cache: ResponseCache) -> None:
        """get() should return the value before TTL expires."""
        now = 1000.0
        with patch("mtb_mcp.storage.cache.time") as mock_time:
            mock_time.time.return_value = now
            await cache.set("key", {"data": 1}, ttl=60)

            # Read at time=1059 (not expired)
            mock_time.time.return_value = now + 59
            result = await cache.get("key")
            assert result == {"data": 1}

    async def test_default_ttl_is_one_hour(self, cache: ResponseCache) -> None:
        """Default TTL should be 3600 seconds."""
        now = 1000.0
        with patch("mtb_mcp.storage.cache.time") as mock_time:
            mock_time.time.return_value = now
            await cache.set("key", {"data": 1})

            # Still valid after 3599 seconds
            mock_time.time.return_value = now + 3599
            result = await cache.get("key")
            assert result == {"data": 1}

            # Expired after 3601 seconds
            mock_time.time.return_value = now + 3601
            result = await cache.get("key")
            assert result is None


class TestCacheDelete:
    """Test cache deletion."""

    async def test_delete_removes_entry(self, cache: ResponseCache) -> None:
        """delete() should remove a specific cache entry."""
        await cache.set("key1", {"v": 1}, ttl=3600)
        await cache.delete("key1")
        result = await cache.get("key1")
        assert result is None

    async def test_delete_nonexistent_key_is_noop(self, cache: ResponseCache) -> None:
        """delete() on a nonexistent key should not raise."""
        await cache.delete("nonexistent")  # Should not raise


class TestCacheInvalidate:
    """Test pattern-based invalidation."""

    async def test_invalidate_by_prefix(self, cache: ResponseCache) -> None:
        """invalidate() with prefix% should delete matching keys."""
        await cache.set("weather:lat1,lon1", {"t": 20}, ttl=3600)
        await cache.set("weather:lat2,lon2", {"t": 22}, ttl=3600)
        await cache.set("trail:1", {"name": "X"}, ttl=3600)

        deleted = await cache.invalidate("weather:%")
        assert deleted == 2

        # Weather keys gone
        assert await cache.get("weather:lat1,lon1") is None
        assert await cache.get("weather:lat2,lon2") is None
        # Trail key still exists
        assert await cache.get("trail:1") is not None

    async def test_invalidate_returns_zero_for_no_match(self, cache: ResponseCache) -> None:
        """invalidate() should return 0 when no keys match the pattern."""
        deleted = await cache.invalidate("nonexistent:%")
        assert deleted == 0


class TestCacheCleanup:
    """Test cleanup of expired entries."""

    async def test_cleanup_expired_removes_old_entries(self, cache: ResponseCache) -> None:
        """cleanup_expired() should remove entries past their TTL."""
        now = 1000.0
        with patch("mtb_mcp.storage.cache.time") as mock_time:
            mock_time.time.return_value = now
            await cache.set("old", {"v": 1}, ttl=60)
            await cache.set("fresh", {"v": 2}, ttl=3600)

            # Advance time past the short TTL but not the long one
            mock_time.time.return_value = now + 120
            deleted = await cache.cleanup_expired()
            assert deleted == 1

            # "old" should be gone, "fresh" should remain
            result = await cache.get("fresh")
            assert result == {"v": 2}

    async def test_cleanup_expired_returns_zero_when_nothing_expired(
        self, cache: ResponseCache
    ) -> None:
        """cleanup_expired() should return 0 when nothing is expired."""
        await cache.set("key", {"v": 1}, ttl=3600)
        deleted = await cache.cleanup_expired()
        assert deleted == 0
