"""Redis and Caching service for NEOMON Milestone 11.

Provides a unified caching and coordination layer with graceful in-memory fallback.
When Redis is unavailable or unconfigured, the service operates transparently
without dropping requests or throwing unhandled errors.
"""

import asyncio
from datetime import datetime, timezone
import time
from typing import Any, Dict, Optional


class MemoryCache:
    """In-memory thread-safe TTL cache fallback."""

    def __init__(self):
        self._store: Dict[str, Tuple[Any, Optional[float]]] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            if key not in self._store:
                return None
            val, expires_at = self._store[key]
            if expires_at is not None and time.time() > expires_at:
                del self._store[key]
                return None
            return str(val)

    async def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> bool:
        async with self._lock:
            expires_at = time.time() + ttl_seconds if ttl_seconds is not None else None
            self._store[key] = (str(value), expires_at)
            return True

    async def delete(self, key: str) -> bool:
        async with self._lock:
            return self._store.pop(key, None) is not None

    async def incr(self, key: str, ttl_seconds: Optional[int] = None, ttl: Optional[int] = None) -> int:
        effective_ttl = ttl if ttl is not None else ttl_seconds
        async with self._lock:
            now = time.time()
            if key in self._store:
                val, expires_at = self._store[key]
                if expires_at is not None and now > expires_at:
                    new_val = 1
                    exp = now + effective_ttl if effective_ttl is not None else None
                else:
                    try:
                        new_val = int(val) + 1
                    except (ValueError, TypeError):
                        new_val = 1
                    exp = expires_at
            else:
                new_val = 1
                exp = now + effective_ttl if effective_ttl is not None else None

            self._store[key] = (str(new_val), exp)
            return new_val

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()


class CacheService:
    """Unified cache interface with Redis backend and in-memory fallback."""

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url
        self._redis_client = None
        self._memory_cache = MemoryCache()
        self._is_redis_active = False

    async def initialize(self) -> None:
        """Attempt to connect to Redis if configured; otherwise use in-memory cache."""
        if not self.redis_url:
            self._is_redis_active = False
            return

        try:
            import redis.asyncio as aioredis
            self._redis_client = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
            )
            await self._redis_client.ping()
            self._is_redis_active = True
        except Exception:
            self._is_redis_active = False
            self._redis_client = None

    async def get(self, key: str) -> Optional[str]:
        if self._is_redis_active and self._redis_client:
            try:
                return await self._redis_client.get(key)
            except Exception:
                pass
        return await self._memory_cache.get(key)

    async def set(self, key: str, value: str, ttl_seconds: Optional[int] = None) -> bool:
        if self._is_redis_active and self._redis_client:
            try:
                if ttl_seconds:
                    await self._redis_client.setex(key, ttl_seconds, str(value))
                else:
                    await self._redis_client.set(key, str(value))
                return True
            except Exception:
                pass
        return await self._memory_cache.set(key, value, ttl_seconds)

    async def delete(self, key: str) -> bool:
        if self._is_redis_active and self._redis_client:
            try:
                res = await self._redis_client.delete(key)
                return bool(res)
            except Exception:
                pass
        return await self._memory_cache.delete(key)

    async def incr(self, key: str, ttl_seconds: Optional[int] = None, ttl: Optional[int] = None) -> int:
        """Atomically increment a key with optional TTL (used for sliding rate limiting)."""
        effective_ttl = ttl if ttl is not None else ttl_seconds
        if self._is_redis_active and self._redis_client:
            try:
                val = await self._redis_client.incr(key)
                if val == 1 and effective_ttl:
                    await self._redis_client.expire(key, effective_ttl)
                return int(val)
            except Exception:
                pass
        return await self._memory_cache.incr(key, ttl_seconds=effective_ttl)

    async def health_check(self) -> Dict[str, Any]:
        """Report cache backend status and probe latency."""
        start = time.perf_counter()
        if self._is_redis_active and self._redis_client:
            try:
                await self._redis_client.ping()
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                return {
                    "healthy": True,
                    "backend": "redis",
                    "status": "connected",
                    "url": self.redis_url,
                    "latency_ms": latency_ms,
                }
            except Exception as exc:
                latency_ms = round((time.perf_counter() - start) * 1000, 2)
                return {
                    "healthy": True,  # still operational via fallback
                    "backend": "memory_fallback",
                    "status": "degraded",
                    "redis_error": str(exc),
                    "latency_ms": latency_ms,
                }

        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "healthy": True,
            "backend": "in_memory",
            "status": "active",
            "latency_ms": latency_ms,
        }

    async def close(self) -> None:
        """Close connections."""
        if self._redis_client:
            try:
                await self._redis_client.close()
            except Exception:
                pass
            self._redis_client = None
            self._is_redis_active = False


# Module-level singleton
cache_service = CacheService()
