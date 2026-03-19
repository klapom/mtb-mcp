"""API response cache with TTL support backed by SQLite.

Usage::

    cache = ResponseCache(db)
    await cache.get("weather:49.59,11.00")  # None or cached dict
    await cache.set("weather:49.59,11.00", data, ttl=CACHE_TTL["weather"])
    await cache.invalidate("weather:%")  # Pattern-based invalidation (SQL LIKE)
"""

from __future__ import annotations

import json
import time
from typing import Any

import structlog

from mtb_mcp.storage.database import Database

logger = structlog.get_logger(__name__)

# Recommended TTL values (in seconds) per data type.
# Use these when calling ``cache.set()`` to ensure consistent caching behaviour.
CACHE_TTL: dict[str, int] = {
    "weather": 1800,  # 30 minutes — forecasts update frequently
    "weather_alerts": 900,  # 15 minutes — alerts are time-critical
    "trails": 86400,  # 24 hours — trail geometry rarely changes
    "tours": 604800,  # 7 days — tour content is essentially static
    "strava_activities": 3600,  # 1 hour — new activities may appear
    "segments": 86400,  # 24 hours — segment definitions are stable
}


class ResponseCache:
    """Cache API responses in SQLite with per-key TTL.

    Keys are plain strings. Values are stored as JSON text. Each entry has a
    created_at timestamp and a TTL in seconds. Expired entries are returned as
    ``None`` by :meth:`get` and can be cleaned up with :meth:`cleanup_expired`.
    """

    def __init__(self, db: Database) -> None:
        self._db = db

    async def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve a cached value if it exists and has not expired.

        Args:
            key: The cache key to look up.

        Returns:
            The cached value as a dict, or None if missing or expired.
        """
        row = await self._db.fetch_one(
            "SELECT value, created_at, ttl_seconds FROM cache WHERE key = ?",
            (key,),
        )
        if row is None:
            return None

        age = time.time() - row["created_at"]
        if age > row["ttl_seconds"]:
            logger.debug("cache.expired", key=key, age=age, ttl=row["ttl_seconds"])
            return None

        value: dict[str, Any] = json.loads(row["value"])
        logger.debug("cache.hit", key=key)
        return value

    async def set(self, key: str, value: dict[str, Any], ttl: float = 3600) -> None:
        """Store a value in the cache with a TTL.

        Args:
            key: The cache key.
            value: The value to cache (must be JSON-serializable).
            ttl: Time-to-live in seconds (default: 1 hour).
        """
        serialized = json.dumps(value, ensure_ascii=False)
        await self._db.execute_and_commit(
            "INSERT OR REPLACE INTO cache (key, value, created_at, ttl_seconds) "
            "VALUES (?, ?, ?, ?)",
            (key, serialized, time.time(), ttl),
        )
        logger.debug("cache.set", key=key, ttl=ttl)

    async def delete(self, key: str) -> None:
        """Delete a specific cache entry.

        Args:
            key: The exact cache key to delete.
        """
        await self._db.execute_and_commit(
            "DELETE FROM cache WHERE key = ?",
            (key,),
        )
        logger.debug("cache.delete", key=key)

    async def invalidate(self, pattern: str) -> int:
        """Delete all cache entries matching a SQL LIKE pattern.

        Use ``%`` as a wildcard. For example, ``weather:%`` deletes all keys
        starting with ``weather:``.

        Args:
            pattern: SQL LIKE pattern to match against cache keys.

        Returns:
            The number of deleted entries.
        """
        cursor = await self._db.execute(
            "DELETE FROM cache WHERE key LIKE ?",
            (pattern,),
        )
        count = cursor.rowcount
        await self._db.connection.commit()
        logger.info("cache.invalidate", pattern=pattern, deleted=count)
        return count

    async def cleanup_expired(self) -> int:
        """Remove all expired cache entries.

        Returns:
            The number of deleted entries.
        """
        cursor = await self._db.execute(
            "DELETE FROM cache WHERE (created_at + ttl_seconds) < ?",
            (time.time(),),
        )
        count = cursor.rowcount
        await self._db.connection.commit()
        logger.info("cache.cleanup_expired", deleted=count)
        return count
