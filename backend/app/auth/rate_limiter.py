"""Rate limiting middleware and dependencies for NEOMON."""

import time
from typing import Callable, Optional
from fastapi import HTTPException, Request, status

from app.cache.service import cache_service
from app.config import settings


def get_client_identifier(request: Request) -> str:
    """Extract client IP address or authenticated subject for rate limiting."""
    # If user is already authenticated and attached to request state
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"

    # Extract IP address
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        client_ip = xff.split(",")[0].strip()
    elif request.client:
        client_ip = request.client.host
    else:
        client_ip = "127.0.0.1"

    return f"ip:{client_ip}"


class RateLimiter:
    """Configurable rate limiter using CacheService (Redis or In-Memory)."""

    def __init__(self, limit_per_minute: int, bucket: str = "default"):
        self.limit = limit_per_minute
        self.bucket = bucket

    async def __call__(self, request: Request) -> None:
        if not settings.rate_limit_enabled:
            return
        if settings.environment == "test" and request.headers.get("X-Enable-Rate-Limit") != "true":
            return
        client_id = get_client_identifier(request)
        now = int(time.time())
        window = now // 60
        window_expires = 60 - (now % 60)
        cache_key = f"rl:{self.bucket}:{client_id}:{window}"

        # Increment count
        count = await cache_service.incr(cache_key, ttl=window_expires + 2)

        if count > self.limit:
            retry_after = max(1, window_expires)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {self.bucket}. Try again in {retry_after} seconds.",
                headers={"Retry-After": str(retry_after)},
            )


# Dependency factories with configuration defaults
def rate_limit_auth() -> RateLimiter:
    return RateLimiter(limit_per_minute=settings.rate_limit_auth_rpm, bucket="auth")


def rate_limit_research() -> RateLimiter:
    return RateLimiter(limit_per_minute=settings.rate_limit_research_rpm, bucket="research")


def rate_limit_export() -> RateLimiter:
    return RateLimiter(limit_per_minute=settings.rate_limit_export_rpm, bucket="export")


def rate_limit_general() -> RateLimiter:
    return RateLimiter(limit_per_minute=settings.rate_limit_general_rpm, bucket="general")
