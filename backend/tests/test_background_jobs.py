"""Tests for Background Job Infrastructure, Worker, and Lifecycle."""

import asyncio
import json
import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy import select

from app.db import SessionFactory
from app.models import BackgroundJob
from app.jobs.service import JobService
from app.jobs.worker import WorkerService


@pytest.mark.asyncio
async def test_job_creation_and_queue():
    """Verify JobService creates persistent jobs with proper default attributes."""
    async with SessionFactory() as session:
        service = JobService(session)
        job = await service.create_job(
            job_type="investigation_execution",
            target_entity_type="investigation",
            target_entity_id=uuid.uuid4(),
            payload={"test_param": "hello_world"},
            priority=5,
            max_retries=2,
            timeout_seconds=300,
        )
        assert job.id is not None
        assert job.status == "queued"
        assert job.priority == 5
        assert job.retry_count == 0
        assert job.max_retries == 2
        assert job.progress_percent == 0.0

        fetched = await service.get_job(job.id)
        assert fetched is not None
        assert fetched.id == job.id
        assert json.loads(fetched.payload_json)["test_param"] == "hello_world"


@pytest.mark.asyncio
async def test_job_cancellation_lifecycle():
    """Verify cooperative cancellation on queued and running jobs."""
    async with SessionFactory() as session:
        service = JobService(session)
        job = await service.create_job(
            job_type="export_generation",
            payload={"format": "pdf"},
        )
        # Cancelling while queued should immediately mark as cancelled
        success = await service.request_cancellation(job.id)
        assert success is True

        cancelled_job = await service.get_job(job.id)
        assert cancelled_job.status == "cancelled"
        assert cancelled_job.cancel_requested is True
        assert cancelled_job.completed_at is not None


@pytest.mark.asyncio
async def test_job_retry_transition():
    """Verify retry transitions failed/cancelled jobs back to queued."""
    async with SessionFactory() as session:
        service = JobService(session)
        job = await service.create_job(
            job_type="quality_calibration",
            max_retries=3,
        )
        # Simulate failure
        await service.fail_job(job.id, "Simulated network timeout")

        failed_job = await service.get_job(job.id)
        assert failed_job.status == "failed"
        assert failed_job.error_message == "Simulated network timeout"

        # Retry job
        retried = await service.retry_job(job.id)
        assert retried.status == "queued"
        assert retried.retry_count == 1
        assert retried.error_message is None
        assert retried.progress_percent == 0.0


@pytest.mark.asyncio
async def test_worker_execution_lifecycle():
    """Verify WorkerService picks up queued job, executes it, and marks it completed."""
    test_worker = WorkerService(worker_id="test-worker-alpha", concurrency=1, poll_interval=0.1)

    # Create a job
    async with SessionFactory() as session:
        service = JobService(session)
        job = await service.create_job(
            job_type="quality_calibration",
            payload={"investigation_id": str(uuid.uuid4())},
        )
        job_id = job.id

    # Run worker briefly to process the job
    await test_worker.start()
    for _ in range(30):
        await asyncio.sleep(0.2)
        async with SessionFactory() as session:
            j = await session.get(BackgroundJob, job_id)
            if j and j.status in ("completed", "failed"):
                break

    await test_worker.stop()

    async with SessionFactory() as session:
        finished = await session.get(BackgroundJob, job_id)
        assert finished is not None
        assert finished.status == "completed"
        assert finished.progress_percent == 100.0
        assert finished.completed_at is not None
        result = json.loads(finished.result_json)
        assert result.get("quality_score") == 0.88


@pytest.mark.asyncio
async def test_worker_restart_recovers_interrupted_jobs():
    """Verify that jobs stuck in 'running' state are recovered upon worker restart."""
    job_id = uuid.uuid4()
    async with SessionFactory() as session:
        stale_job = BackgroundJob(
            id=job_id,
            job_type="investigation_execution",
            target_entity_type="investigation",
            status="running",
            priority=1,
            progress_percent=45.0,
            max_retries=3,
            retry_count=0,
            payload_json="{}",
            queued_at=datetime.now(timezone.utc),
            started_at=datetime.now(timezone.utc),
            heartbeat_at=datetime.now(timezone.utc),
        )
        session.add(stale_job)
        await session.commit()

    test_worker = WorkerService(worker_id="recovery-worker")
    recovered_count = await test_worker.recover_interrupted_jobs()
    assert recovered_count >= 1

    async with SessionFactory() as session:
        recovered = await session.get(BackgroundJob, job_id)
        assert recovered is not None
        assert recovered.status == "queued"
        assert recovered.retry_count == 1
        assert "Recovered" in recovered.current_step
