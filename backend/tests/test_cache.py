"""Tests for cache service."""

import asyncio

import pytest

from src.services.cache import TTLCache


@pytest.mark.asyncio
async def test_cache_set_and_get():
    """Test basic cache set and get."""
    cache = TTLCache()
    data = {"temperature": 22.5, "humidity": 65}

    await cache.set("ha", data, ttl_seconds=300)
    result = await cache.get("ha")

    assert result == data


@pytest.mark.asyncio
async def test_cache_get_nonexistent():
    """Test getting non-existent key returns None."""
    cache = TTLCache()
    result = await cache.get("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_cache_expiry():
    """Test that expired entries return None."""
    cache = TTLCache()
    data = {"temperature": 22.5}

    # Set with 0 TTL (immediately expired)
    await cache.set("ha", data, ttl_seconds=0)

    # Sleep to ensure expiry
    await asyncio.sleep(0.1)

    result = await cache.get("ha")
    assert result is None


@pytest.mark.asyncio
async def test_cache_invalidate():
    """Test cache invalidation."""
    cache = TTLCache()
    data = {"temperature": 22.5}

    await cache.set("ha", data, ttl_seconds=300)
    await cache.invalidate("ha")

    result = await cache.get("ha")
    assert result is None


@pytest.mark.asyncio
async def test_cache_lock_prevents_concurrent_fetches():
    """Test that per-source locks work."""
    cache = TTLCache()
    call_count = 0

    async def slow_operation():
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)

    lock = await cache.acquire_lock("ha")
    lock2 = await cache.acquire_lock("ha")

    # Both should be the same lock
    assert lock is lock2

    # Simulate concurrent requests using the same lock
    async with lock:
        await slow_operation()

    assert call_count == 1


@pytest.mark.asyncio
async def test_cache_status():
    """Test cache status reporting."""
    cache = TTLCache()
    data = {"temperature": 22.5}

    await cache.set("ha", data, ttl_seconds=300)
    status = cache.status()

    assert "ha" in status
    assert not status["ha"].expired
    assert status["ha"].ttl_remaining_seconds > 0
    assert status["ha"].expires_at is not None


@pytest.mark.asyncio
async def test_cache_status_empty():
    """Test status returns empty dict when cache is empty."""
    cache = TTLCache()
    status = cache.status()
    assert status == {}


@pytest.mark.asyncio
async def test_cache_overwrite():
    """Test that set() overwrites existing entry."""
    cache = TTLCache()

    await cache.set("ha", {"temperature": 20.0}, ttl_seconds=300)
    await cache.set("ha", {"temperature": 25.0}, ttl_seconds=300)

    result = await cache.get("ha")
    assert result["temperature"] == 25.0


@pytest.mark.asyncio
async def test_independent_locks():
    """Test that different sources have independent locks."""
    cache = TTLCache()

    lock_ha = await cache.acquire_lock("ha")
    lock_influx = await cache.acquire_lock("influxdb")

    assert lock_ha is not lock_influx
