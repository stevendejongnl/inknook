"""Cache service with TTL and per-source locking."""

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any


@dataclass
class CacheEntry:
    """A single cache entry with TTL."""

    data: Any
    expires_at: datetime


@dataclass
class CacheStatus:
    """Status information for a cache source."""

    expired: bool
    last_updated: str | None
    expires_at: str | None
    ttl_remaining_seconds: int | None


class TTLCache:
    """Thread-safe cache with per-source TTL and locking."""

    def __init__(self) -> None:
        """Initialize empty cache with per-source locks."""
        self._cache: dict[str, CacheEntry] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def get(self, source: str) -> dict | None:
        """
        Get cached data for source if not expired.

        Returns:
            Cached data dict if present and not expired, None otherwise.
        """
        if source not in self._cache:
            return None

        entry = self._cache[source]
        if datetime.now() >= entry.expires_at:
            # Expired but don't delete; let set() overwrite it
            return None

        return entry.data

    async def set(self, source: str, data: dict, ttl_seconds: int) -> None:
        """
        Store data for source with TTL.

        Args:
            source: Cache key (e.g., 'ha', 'influxdb', 'calendar')
            data: Data to cache
            ttl_seconds: Time-to-live in seconds
        """
        expires_at = datetime.now() + timedelta(seconds=ttl_seconds)
        self._cache[source] = CacheEntry(data=data, expires_at=expires_at)

    async def invalidate(self, source: str) -> None:
        """Force cache invalidation for source."""
        self._cache.pop(source, None)

    async def acquire_lock(self, source: str) -> asyncio.Lock:
        """
        Get or create asyncio.Lock for source.

        Used to prevent thundering herd when multiple requests try to
        fetch the same source simultaneously.

        Args:
            source: Cache key

        Returns:
            asyncio.Lock for this source
        """
        if source not in self._locks:
            self._locks[source] = asyncio.Lock()
        return self._locks[source]

    def status(self) -> dict[str, CacheStatus]:
        """
        Get status of all cached sources.

        Returns:
            Dict mapping source name to CacheStatus
        """
        result: dict[str, CacheStatus] = {}
        now = datetime.now()

        for source, entry in self._cache.items():
            is_expired = now >= entry.expires_at
            remaining = max(0, (entry.expires_at - now).total_seconds())

            result[source] = CacheStatus(
                expired=is_expired,
                last_updated=entry.expires_at.isoformat(),
                expires_at=entry.expires_at.isoformat(),
                ttl_remaining_seconds=int(remaining),
            )

        return result
