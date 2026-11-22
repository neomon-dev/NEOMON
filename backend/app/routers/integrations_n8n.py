import logging
import uuid
from typing import Any
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.collaboration.permission_service import PermissionService
from app.config import get_settings
from app.db import get_session
from app.models import (
    Investigation,
    ResearchMonitoringConfig,
    ResearchMonitoringRun,
    User,
    Workspace,
    Notification,
)
from app.monitoring.service import MonitoringService

logger = logging.getLogger("neomon.routers.integrations")

router = APIRouter(prefix="/integrations/n8n", tags=["integrations-n8n"])
monitoring_router = APIRouter(prefix="/monitoring", tags=["monitoring"])


# ---------------------------------------------------------
# Security & S2S Auth Helper
# ---------------------------------------------------------
def verify_service_token(authorization: str | None = Header(None)) -> bool:
    """Validate Bearer service-to-service token for n8n webhooks and callbacks."""
    settings = get_settings()
    configured_token = settings.n8n_service_token or settings.n8n_api_key
    if not configured_token:
        # Default development fallback if not explicitly set
        configured_token = "neomon_n8n_s2s_default_secret"
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Service authentication required for n8n integration.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization[7:].strip()
    if token != configured_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid service token for n8n integration.",
        )
    return True


# ---------------------------------------------------------
# Request / Response Schemas
# ---------------------------------------------------------
class N8nStatusResponse(BaseModel):
    status: str
    configured: bool
    webhook_url: str | None
    version: str = "1.0.0"
    active_monitors_count: int = 0
    total_runs_count: int = 0


class N8nTestRequest(BaseModel):
    event_type: str = "ping"
    payload: dict[str, Any] = Field(default_factory=dict)


class N8nEventRequest(BaseModel):
    event_type: str
    investigation_id: uuid.UUID | None = None
    workspace_id: uuid.UUID | None = None
    idempotency_key: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class MonitoringConfigCreate(BaseModel):
    workspace_id: uuid.UUID
    investigation_id: uuid.UUID
    name: str = Field(min_length=1, max_length=128)
    query_keywords: str = Field(min_length=1, max_length=1000)
    interval_minutes: int = Field(default=60, ge=5, le=10080)
    max_new_sources_per_run: int = Field(default=5, ge=1, le=20)


class MonitoringConfigUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=128)
    query_keywords: str | None = Field(default=None, max_length=1000)
    interval_minutes: int | None = Field(default=None, ge=5, le=10080)
    is_active: bool | None = None
    max_new_sources_per_run: int | None = Field(default=None, ge=1, le=20)


class MonitoringRunTriggerRequest(BaseModel):
    idempotency_key: str | None = None


# ---------------------------------------------------------
# n8n Integration Endpoints
# ---------------------------------------------------------
@router.get("/status", response_model=N8nStatusResponse)
async def get_n8n_status(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Return n8n connection telemetry and active monitors."""
    settings = get_settings()
    active_monitors_stmt = select(ResearchMonitoringConfig).where(ResearchMonitoringConfig.is_active == True)
    active_count = len((await db.execute(active_monitors_stmt)).scalars().all())

    runs_stmt = select(ResearchMonitoringRun)
    total_runs = len((await db.execute(runs_stmt)).scalars().all())

    configured = bool(settings.n8n_webhook_url or settings.n8n_api_key or settings.n8n_service_token)
    return N8nStatusResponse(
        status="connected" if configured else "ready",
        configured=configured,
        webhook_url=settings.n8n_webhook_url,
        active_monitors_count=active_count,
        total_runs_count=total_runs,
    )


@router.post("/test")
async def test_n8n_connection(
    req: N8nTestRequest,
    user: User = Depends(get_current_user),
):
    """Test connectivity or send a test ping to n8n."""
    settings = get_settings()
    # If webhook URL is set, dispatch a test HTTP POST
    webhook_dispatched = False
    status_msg = "Test event received and validated."
    if settings.n8n_webhook_url:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(
                    settings.n8n_webhook_url,
                    json={
                        "event": "neomon.test_ping",
                        "triggered_by": user.email,
                        "timestamp": datetime.utcnow().isoformat(),
                        "payload": req.payload,
                    },
                    headers={"Authorization": f"Bearer {settings.n8n_api_key or ''}"},
                )
                webhook_dispatched = res.is_success
        except Exception as exc:
            logger.warning("Failed sending test ping to n8n webhook: %s", exc)
            status_msg = f"Local validated; webhook ping failed: {exc}"

    return {
        "status": "success",
        "message": status_msg,
        "webhook_dispatched": webhook_dispatched,
        "received_event": req.event_type,
    }


@router.post("/events")
async def receive_n8n_event(
    req: N8nEventRequest,
    db: AsyncSession = Depends(get_session),
    authorized: bool = Depends(verify_service_token),
):
    """Handle incoming authenticated webhook events from n8n.

    Supports:
    - `monitoring.trigger`: triggers incremental research monitoring cycle.
    - `report.approval_decision`: receives human approval or rejection of report.
    - `notification.callback`: acknowledges notification delivery.
    """
    logger.info("Received n8n event: %s", req.event_type)

    if req.event_type == "monitoring.trigger":
        # Extract monitoring config id
        config_id_str = req.payload.get("monitoring_config_id")
        if not config_id_str:
            raise HTTPException(status_code=400, detail="monitoring_config_id required in payload")
        config = await db.get(ResearchMonitoringConfig, uuid.UUID(str(config_id_str)))
        if not config:
            raise HTTPException(status_code=404, detail="Monitoring configuration not found")

        monitoring_service = MonitoringService(db)
        run = await monitoring_service.execute_monitoring_run(
            config=config,
            triggered_by="n8n",
            idempotency_key=req.idempotency_key,
        )
        return {
            "status": "success",
            "run_id": str(run.id),
            "sources_discovered": run.sources_discovered,
            "evidence_extracted": run.evidence_extracted,
            "contradictions_detected": run.contradictions_detected,
        }

    elif req.event_type == "report.approval_decision":
        # Handled through human approval flow
        review_request_id = req.payload.get("review_request_id")
        decision = req.payload.get("decision")  # "approved" or "rejected"
        reviewer_id = req.payload.get("reviewer_id")
        rationale = req.payload.get("rationale", "Approved via automated n8n workflow")

        if not review_request_id or not decision or not reviewer_id:
            raise HTTPException(status_code=400, detail="review_request_id, decision, and reviewer_id required")

        from app.collaboration.review_service import ReviewService
        reviewer = await db.get(User, uuid.UUID(str(reviewer_id)))
        if not reviewer:
            raise HTTPException(status_code=404, detail="Reviewer not found")

        review_service = ReviewService(db)
        res = await review_service.submit_review_decision(
            review_request_id=uuid.UUID(str(review_request_id)),
            reviewer=reviewer,
            decision=decision,
            rationale=rationale,
        )
        return {"status": "success", "review_request": res}

    return {"status": "accepted", "event_type": req.event_type}


# ---------------------------------------------------------
# Research Monitoring Endpoints
# ---------------------------------------------------------
@monitoring_router.get("")
async def list_monitoring_configs(
    workspace_id: uuid.UUID = Query(...),
    is_active: bool | None = None,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """List monitoring configs for a workspace."""
    perm = PermissionService(db)
    await perm.require_workspace_membership(user.id, workspace_id, min_role="viewer")

    service = MonitoringService(db)
    items = await service.list_configs(workspace_id, is_active=is_active)
    return [
        {
            "id": str(c.id),
            "workspace_id": str(c.workspace_id),
            "investigation_id": str(c.investigation_id),
            "name": c.name,
            "query_keywords": c.query_keywords,
            "interval_minutes": c.interval_minutes,
            "is_active": c.is_active,
            "max_new_sources_per_run": c.max_new_sources_per_run,
            "last_run_at": c.last_run_at.isoformat() if c.last_run_at else None,
            "next_run_at": c.next_run_at.isoformat() if c.next_run_at else None,
            "consecutive_failures": c.consecutive_failures,
            "last_error": c.last_error,
            "created_at": c.created_at.isoformat(),
        }
        for c in items
    ]


@monitoring_router.post("", status_code=status.HTTP_201_CREATED)
async def create_monitoring_config(
    req: MonitoringConfigCreate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Create a new automated research monitoring configuration."""
    perm = PermissionService(db)
    await perm.require_workspace_membership(user.id, req.workspace_id, min_role="researcher")
    await perm.check_investigation_access(user, req.investigation_id, "read")

    service = MonitoringService(db)
    config = await service.create_config(
        workspace_id=req.workspace_id,
        investigation_id=req.investigation_id,
        creator=user,
        name=req.name,
        query_keywords=req.query_keywords,
        interval_minutes=req.interval_minutes,
        max_new_sources_per_run=req.max_new_sources_per_run,
    )
    return {
        "id": str(config.id),
        "name": config.name,
        "is_active": config.is_active,
        "interval_minutes": config.interval_minutes,
        "next_run_at": config.next_run_at.isoformat() if config.next_run_at else None,
        "created_at": config.created_at.isoformat(),
    }


@monitoring_router.patch("/{id}")
async def update_monitoring_config(
    id: uuid.UUID,
    req: MonitoringConfigUpdate,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Update or enable/disable an automated monitoring configuration."""
    service = MonitoringService(db)
    config = await service.get_config(id)
    if not config:
        raise HTTPException(status_code=404, detail="Monitoring configuration not found")

    perm = PermissionService(db)
    await perm.require_workspace_membership(user.id, config.workspace_id, min_role="researcher")

    updated = await service.update_config(
        config=config,
        name=req.name,
        query_keywords=req.query_keywords,
        interval_minutes=req.interval_minutes,
        is_active=req.is_active,
        max_new_sources_per_run=req.max_new_sources_per_run,
    )
    return {
        "id": str(updated.id),
        "name": updated.name,
        "is_active": updated.is_active,
        "interval_minutes": updated.interval_minutes,
        "next_run_at": updated.next_run_at.isoformat() if updated.next_run_at else None,
    }


@monitoring_router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monitoring_config(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Delete an automated monitoring configuration."""
    service = MonitoringService(db)
    config = await service.get_config(id)
    if not config:
        raise HTTPException(status_code=404, detail="Monitoring configuration not found")

    perm = PermissionService(db)
    await perm.require_workspace_membership(user.id, config.workspace_id, min_role="admin")
    await service.delete_config(config)
    return None


@monitoring_router.post("/{id}/trigger")
async def trigger_monitoring_run(
    id: uuid.UUID,
    req: MonitoringRunTriggerRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Immediately trigger a manual or webhook monitoring run."""
    service = MonitoringService(db)
    config = await service.get_config(id)
    if not config:
        raise HTTPException(status_code=404, detail="Monitoring configuration not found")

    perm = PermissionService(db)
    await perm.require_workspace_membership(user.id, config.workspace_id, min_role="researcher")

    run = await service.execute_monitoring_run(
        config=config,
        triggered_by=f"user:{user.id}",
        idempotency_key=req.idempotency_key,
    )
    return {
        "id": str(run.id),
        "status": run.status,
        "sources_discovered": run.sources_discovered,
        "evidence_extracted": run.evidence_extracted,
        "contradictions_detected": run.contradictions_detected,
        "execution_latency_ms": run.execution_latency_ms,
    }
