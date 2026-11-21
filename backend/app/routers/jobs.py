"""API Router for Background Job Management."""

import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import BackgroundJob, User
from app.auth.dependencies import get_current_user
from app.jobs.schemas import JobCreateRequest, JobResponse, WorkerStatusResponse
from app.jobs.service import JobService
from app.jobs.worker import worker_service
from app.collaboration.permission_service import PermissionService

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _job_to_response(job: BackgroundJob) -> JobResponse:
    payload = {}
    result = {}
    try:
        if job.payload_json:
            payload = json.loads(job.payload_json)
    except Exception:
        pass
    try:
        if job.result_json:
            result = json.loads(job.result_json)
    except Exception:
        pass

    return JobResponse(
        id=str(job.id),
        job_type=job.job_type,
        target_entity_type=job.target_entity_type,
        target_entity_id=str(job.target_entity_id) if job.target_entity_id else None,
        workspace_id=str(job.workspace_id) if job.workspace_id else None,
        owner_id=str(job.owner_id) if job.owner_id else None,
        status=job.status,
        priority=job.priority,
        progress_percent=job.progress_percent,
        current_step=job.current_step,
        max_retries=job.max_retries,
        retry_count=job.retry_count,
        timeout_seconds=job.timeout_seconds,
        payload=payload,
        result=result,
        error_message=job.error_message,
        worker_id=job.worker_id,
        cancel_requested=job.cancel_requested,
        queued_at=job.queued_at.isoformat() if job.queued_at else None,
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        heartbeat_at=job.heartbeat_at.isoformat() if job.heartbeat_at else None,
    )


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    req: JobCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Enqueue a new background processing job."""
    perm = PermissionService(db)
    if req.workspace_id:
        await perm.require_workspace_membership(user.id, req.workspace_id, min_role="researcher")

    service = JobService(db)
    job = await service.create_job(
        job_type=req.job_type,
        target_entity_type=req.target_entity_type,
        target_entity_id=req.target_entity_id,
        workspace_id=req.workspace_id,
        owner_id=user.id,
        payload=req.payload,
        priority=req.priority,
        timeout_seconds=req.timeout_seconds,
        max_retries=req.max_retries,
    )
    return _job_to_response(job)


@router.get("/worker/status", response_model=WorkerStatusResponse)
async def get_worker_status(
    user: User = Depends(get_current_user),
):
    """Retrieve current worker health, active concurrency, and queue counts."""
    return await worker_service.get_status()


@router.get("", response_model=List[JobResponse])
async def list_jobs(
    workspace_id: Optional[uuid.UUID] = Query(None),
    status: Optional[str] = Query(None),
    job_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List background jobs with filtering."""
    if workspace_id:
        perm = PermissionService(db)
        await perm.require_workspace_membership(user.id, workspace_id, min_role="viewer")

    service = JobService(db)
    jobs = await service.list_jobs(
        workspace_id=workspace_id,
        status=status,
        job_type=job_type,
        limit=limit,
        offset=offset,
    )
    return [_job_to_response(j) for j in jobs]


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Get single job status and results."""
    service = JobService(db)
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.workspace_id:
        perm = PermissionService(db)
        await perm.require_workspace_membership(user.id, job.workspace_id, min_role="viewer")

    return _job_to_response(job)


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Request cooperative cancellation of a background job."""
    service = JobService(db)
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.workspace_id:
        perm = PermissionService(db)
        await perm.require_workspace_membership(user.id, job.workspace_id, min_role="researcher")

    success = await service.request_cancellation(job_id, user_id=user.id)
    if not success:
        raise HTTPException(status_code=400, detail="Job cannot be cancelled in its current state")

    job = await service.get_job(job_id)
    return _job_to_response(job)


@router.post("/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Retry a failed or cancelled job."""
    service = JobService(db)
    job = await service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.workspace_id:
        perm = PermissionService(db)
        await perm.require_workspace_membership(user.id, job.workspace_id, min_role="researcher")

    try:
        retried = await service.retry_job(job_id, user_id=user.id)
        return _job_to_response(retried)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
