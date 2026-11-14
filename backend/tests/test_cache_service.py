"""Tests for Redis & Memory Cache Service."""

import asyncio
import time
import pytest

from app.cache.service import CacheService, MemoryCache


@pytest.mark.asyncio
async def test_memory_cache_crud():
    """Verify basic CRUD operations on MemoryCache."""
    cache = MemoryCache()
    assert await cache.get("k1") is None

    await cache.set("k1", "v1")
    assert await cache.get("k1") == "v1"

    await cache.delete("k1")
    assert await cache.get("k1") is None


@pytest.mark.asyncio
async def test_memory_cache_ttl_expiration():
    """Verify that cached keys expire correctly after TTL."""
    cache = MemoryCache()
    await cache.set("temp_key", "temp_value", ttl_seconds=1)
    assert await cache.get("temp_key") == "temp_value"

    await asyncio.sleep(1.1)
    assert await cache.get("temp_key") is None


@pytest.mark.asyncio
async def test_atomic_incr():
    """Verify atomic increment counter for rate limiting."""
    cache = MemoryCache()
    val1 = await cache.incr("counter", ttl_seconds=60)
    assert val1 == 1

    val2 = await cache.incr("counter", ttl_seconds=60)
    assert val2 == 2

    val3 = await cache.incr("counter", ttl_seconds=60)
    assert val3 == 3


@pytest.mark.asyncio
async def test_cache_service_fallback_and_health():
    """Verify CacheService operates cleanly in fallback mode and reports health."""
    service = CacheService(redis_url=None)
    health = await service.health_check()
    assert health["healthy"] is True
    assert health["backend"] == "in_memory"
    assert health["status"] == "active"
    assert "latency_ms" in health

    # Set and get via service
    await service.set("svc_key", "svc_val", ttl_seconds=10)
    assert await service.get("svc_key") == "svc_val"

    # Incr via service
    n = await service.incr("svc_rate", ttl_seconds=10)
    assert n == 1
    n2 = await service.incr("svc_rate", ttl_seconds=10)
    assert n2 == 2

    await service.close()
