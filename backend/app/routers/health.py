"""Health, readiness, and observability metrics endpoints for NEOMON."""

import time
from typing import Any, Dict
from fastapi import APIRouter, Response, status

from app.config import get_settings
from app.db import check_database_health
from app.cache.service import cache_service
from app.jobs.worker import worker_service
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])

_START_TIME = time.time()


@router.get("/", response_model=HealthResponse)
@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe indicating process is active."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.api_version,
        demo_mode=settings.demo_mode,
        database="configured",
    )


@router.get("/ready")
async def readiness(response: Response) -> Dict[str, Any]:
    """Readiness probe verifying DB, Cache, and Worker subsystem health."""
    settings = get_settings()

    db_health = await check_database_health()
    cache_health = await cache_service.health_check()
    worker_status = await worker_service.get_status()

    is_ready = db_health.get("status") == "healthy"

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "not_ready",
        "app": settings.app_name,
        "version": settings.api_version,
        "environment": settings.environment,
        "database": db_health,
        "cache": cache_health,
        "worker": {
            "is_running": worker_status.is_running,
            "active_jobs": worker_status.active_jobs,
            "queued_jobs": worker_status.queued_jobs,
        },
    }


@router.get("/metrics")
async def metrics() -> Dict[str, Any]:
    """Operational metrics covering database pool, cache performance, and background jobs."""
    settings = get_settings()
    uptime = round(time.time() - _START_TIME, 2)

    db_health = await check_database_health()
    cache_health = await cache_service.health_check()
    worker_status = await worker_service.get_status()

    return {
        "app": settings.app_name,
        "version": settings.api_version,
        "environment": settings.environment,
        "uptime_seconds": uptime,
        "database": db_health,
        "cache": cache_health,
        "worker": worker_status.model_dump(),
    }
