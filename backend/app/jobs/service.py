"""JobService for managing persistent BackgroundJob records."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BackgroundJob, User, WorkspaceMember
from app.collaboration.permission_service import PermissionService


class JobService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.perm = PermissionService(db)

    async def create_job(
        self,
        job_type: str,
        target_entity_type: str = "investigation",
        target_entity_id: Optional[uuid.UUID] = None,
        workspace_id: Optional[uuid.UUID] = None,
        owner_id: Optional[uuid.UUID] = None,
        payload: Optional[Dict[str, Any]] = None,
        priority: int = 0,
        max_retries: int = 3,
        timeout_seconds: int = 1800,
    ) -> BackgroundJob:
        """Create and enqueue a new durable background job."""
        job = BackgroundJob(
            id=uuid.uuid4(),
            job_type=job_type,
            target_entity_type=target_entity_type,
            target_entity_id=target_entity_id,
            workspace_id=workspace_id,
            owner_id=owner_id,
            status="queued",
            priority=priority,
            progress_percent=0.0,
            current_step="Queued for processing",
            max_retries=max_retries,
            retry_count=0,
            timeout_seconds=timeout_seconds,
            payload_json=json.dumps(payload or {}),
            result_json="{}",
            cancel_requested=False,
            queued_at=datetime.now(timezone.utc),
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def get_job(self, job_id: uuid.UUID) -> Optional[BackgroundJob]:
        """Fetch job by ID."""
        return await self.db.get(BackgroundJob, job_id)

    async def list_jobs(
        self,
        workspace_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[BackgroundJob]:
        """List jobs with filtering and pagination."""
        stmt = select(BackgroundJob)
        if workspace_id:
            stmt = stmt.where(BackgroundJob.workspace_id == workspace_id)
        if status:
            stmt = stmt.where(BackgroundJob.status == status)
        if job_type:
            stmt = stmt.where(BackgroundJob.job_type == job_type)
        stmt = stmt.order_by(BackgroundJob.priority.desc(), BackgroundJob.queued_at.desc()).offset(offset).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def request_cancellation(self, job_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> bool:
        """Request cooperative cancellation for an in-flight or queued job."""
        job = await self.db.get(BackgroundJob, job_id)
        if not job:
            return False

        if user_id and job.workspace_id:
            await self.perm.require_workspace_membership(user_id, job.workspace_id, min_role="researcher")

        if job.status in ("completed", "failed", "cancelled"):
            return False

        job.cancel_requested = True
        if job.status == "queued":
            job.status = "cancelled"
            job.completed_at = datetime.now(timezone.utc)
            job.current_step = "Cancelled while queued."

        await self.db.commit()
        return True

    async def retry_job(self, job_id: uuid.UUID, user_id: Optional[uuid.UUID] = None) -> BackgroundJob:
        """Retry a failed or cancelled job."""
        job = await self.db.get(BackgroundJob, job_id)
        if not job:
            raise ValueError("Job not found.")

        if user_id and job.workspace_id:
            await self.perm.require_workspace_membership(user_id, job.workspace_id, min_role="researcher")

        if job.status not in ("failed", "cancelled"):
            raise ValueError(f"Only failed or cancelled jobs can be retried. Current status: {job.status}")

        job.status = "queued"
        job.retry_count += 1
        job.progress_percent = 0.0
        job.current_step = f"Retrying (attempt {job.retry_count})"
        job.cancel_requested = False
        job.error_message = None
        job.queued_at = datetime.now(timezone.utc)
        job.started_at = None
        job.completed_at = None
        job.heartbeat_at = None

        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def update_progress(
        self, job_id: uuid.UUID, progress_percent: float, current_step: Optional[str] = None
    ) -> None:
        """Update job progress and heartbeat."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(BackgroundJob)
            .where(BackgroundJob.id == job_id)
            .values(
                progress_percent=min(100.0, max(0.0, progress_percent)),
                current_step=current_step,
                heartbeat_at=now,
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def complete_job(self, job_id: uuid.UUID, result: Dict[str, Any]) -> None:
        """Mark job as successfully completed."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(BackgroundJob)
            .where(BackgroundJob.id == job_id)
            .values(
                status="completed",
                progress_percent=100.0,
                current_step="Execution completed successfully",
                result_json=json.dumps(result or {}),
                completed_at=now,
                heartbeat_at=now,
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def fail_job(self, job_id: uuid.UUID, error_message: str) -> None:
        """Mark job as failed."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(BackgroundJob)
            .where(BackgroundJob.id == job_id)
            .values(
                status="failed",
                current_step="Execution failed",
                error_message=str(error_message),
                completed_at=now,
                heartbeat_at=now,
            )
        )
        await self.db.execute(stmt)
        await self.db.commit()
