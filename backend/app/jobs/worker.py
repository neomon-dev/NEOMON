"""WorkerService for processing durable background jobs in NEOMON."""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Set
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import async_session_factory
from app.models import BackgroundJob
from app.jobs.handlers import HANDLER_REGISTRY
from app.jobs.schemas import WorkerStatusResponse

logger = logging.getLogger("neomon.jobs.worker")


class WorkerService:
    def __init__(
        self,
        worker_id: Optional[str] = None,
        concurrency: Optional[int] = None,
        poll_interval: Optional[float] = None,
        session_factory=None,
    ):
        self.worker_id = worker_id or f"worker-{uuid.uuid4().hex[:8]}"
        self.concurrency = concurrency or settings.worker_concurrency
        self.poll_interval = poll_interval or settings.worker_poll_interval
        self.session_factory = session_factory or async_session_factory
        self.semaphore = asyncio.Semaphore(self.concurrency)
        self.is_running = False
        self._loop_task: Optional[asyncio.Task] = None
        self._active_tasks: Set[asyncio.Task] = set()
        self._start_time: float = time.time()
        self.completed_count = 0
        self.failed_count = 0

    async def start(self) -> None:
        """Start the background worker service."""
        if self.is_running:
            return
        self.is_running = True
        self._start_time = time.time()
        logger.info(f"Starting WorkerService [{self.worker_id}] with concurrency {self.concurrency}")

        # Recover any jobs that were interrupted in a previous run
        try:
            await self.recover_interrupted_jobs()
        except Exception as e:
            logger.error(f"Error during job recovery on worker startup: {e}")

        self._loop_task = asyncio.create_task(self._poll_loop())

    async def stop(self, timeout: Optional[float] = None) -> None:
        """Stop worker gracefully."""
        if not self.is_running:
            return
        logger.info(f"Stopping WorkerService [{self.worker_id}]...")
        self.is_running = False

        if self._loop_task and not self._loop_task.done():
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass

        timeout = timeout or settings.worker_graceful_shutdown_timeout
        if self._active_tasks:
            logger.info(f"Waiting for {len(self._active_tasks)} active jobs to complete (timeout={timeout}s)...")
            done, pending = await asyncio.wait(self._active_tasks, timeout=timeout)
            for t in pending:
                t.cancel()

        logger.info(f"WorkerService [{self.worker_id}] stopped.")

    async def recover_interrupted_jobs(self) -> int:
        """Recover any jobs stuck in 'running' state on worker restart."""
        recovered = 0
        async with self.session_factory() as session:
            stmt = select(BackgroundJob).where(BackgroundJob.status == "running")
            res = await session.execute(stmt)
            running_jobs = res.scalars().all()

            for job in running_jobs:
                if job.retry_count < job.max_retries:
                    job.status = "queued"
                    job.retry_count += 1
                    job.current_step = f"Recovered after unexpected worker restart (retry {job.retry_count}/{job.max_retries})"
                    job.heartbeat_at = datetime.now(timezone.utc)
                    recovered += 1
                    logger.warning(f"Recovered job {job.id}: marked as queued for retry.")
                else:
                    job.status = "failed"
                    job.completed_at = datetime.now(timezone.utc)
                    job.error_message = "Worker terminated unexpectedly and max retries exceeded."
                    job.current_step = "Failed due to unrecoverable worker crash."
                    recovered += 1
                    logger.error(f"Job {job.id} exceeded retries after crash, marked as failed.")

            if running_jobs:
                await session.commit()

        return recovered

    async def _poll_loop(self) -> None:
        """Main polling loop for queued jobs."""
        while self.is_running:
            try:
                # Try acquiring a slot before querying to prevent fetching jobs we can't run
                await self.semaphore.acquire()

                job_id = await self._claim_next_job()
                if job_id:
                    task = asyncio.create_task(self._execute_job_wrapper(job_id))
                    self._active_tasks.add(task)
                    task.add_done_callback(lambda t: self._active_tasks.discard(t))
                else:
                    # No job claimed, release the semaphore and sleep
                    self.semaphore.release()
                    await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in worker polling loop: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)

    async def _claim_next_job(self) -> Optional[uuid.UUID]:
        """Atomically find and claim the next highest priority queued job."""
        async with self.session_factory() as session:
            stmt = (
                select(BackgroundJob)
                .where(BackgroundJob.status == "queued")
                .order_by(BackgroundJob.priority.desc(), BackgroundJob.queued_at.asc())
                .limit(1)
            )
            res = await session.execute(stmt)
            job = res.scalars().first()

            if not job:
                return None

            now = datetime.now(timezone.utc)
            job.status = "running"
            job.worker_id = self.worker_id
            job.started_at = now
            job.heartbeat_at = now
            job.current_step = "Job started by worker"
            await session.commit()
            return job.id

    async def _execute_job_wrapper(self, job_id: uuid.UUID) -> None:
        """Executes a single job with heartbeat, cancellation, and error handling."""
        try:
            await self._run_job(job_id)
        finally:
            self.semaphore.release()

    async def _run_job(self, job_id: uuid.UUID) -> None:
        """Inner execution logic with periodic heartbeat and cooperative cancellation."""
        heartbeat_task: Optional[asyncio.Task] = None
        stop_heartbeat = asyncio.Event()

        async def _heartbeat_worker():
            while not stop_heartbeat.is_set():
                try:
                    await asyncio.sleep(5.0)
                    if stop_heartbeat.is_set():
                        break
                    async with self.session_factory() as s:
                        await s.execute(
                            update(BackgroundJob)
                            .where(BackgroundJob.id == job_id)
                            .values(heartbeat_at=datetime.now(timezone.utc))
                        )
                        await s.commit()
                except Exception as ex:
                    logger.debug(f"Heartbeat update error for job {job_id}: {ex}")

        async def _progress_callback(pct: float, step: str):
            async with self.session_factory() as s:
                await s.execute(
                    update(BackgroundJob)
                    .where(BackgroundJob.id == job_id)
                    .values(
                        progress_percent=min(100.0, max(0.0, pct)),
                        current_step=step,
                        heartbeat_at=datetime.now(timezone.utc),
                    )
                )
                await s.commit()

        async def _is_cancelled() -> bool:
            async with self.session_factory() as s:
                res = await s.execute(
                    select(BackgroundJob.cancel_requested, BackgroundJob.status).where(BackgroundJob.id == job_id)
                )
                row = res.first()
                if not row:
                    return True
                return bool(row[0] or row[1] == "cancelled")

        heartbeat_task = asyncio.create_task(_heartbeat_worker())

        try:
            async with self.session_factory() as session:
                job = await session.get(BackgroundJob, job_id)
                if not job:
                    return

                if job.cancel_requested:
                    job.status = "cancelled"
                    job.completed_at = datetime.now(timezone.utc)
                    job.current_step = "Job cancelled before execution"
                    await session.commit()
                    return

                handler = HANDLER_REGISTRY.get(job.job_type)
                if not handler:
                    raise ValueError(f"No registered handler for job type '{job.job_type}'")

                # Execute handler with timeout
                timeout = job.timeout_seconds or 1800
                result = await asyncio.wait_for(
                    handler(job, session, _progress_callback, _is_cancelled),
                    timeout=float(timeout),
                )

                # Mark completed
                job = await session.get(BackgroundJob, job_id)
                if job:
                    job.status = "completed"
                    job.progress_percent = 100.0
                    job.current_step = "Execution completed successfully"
                    job.result_json = json.dumps(result or {})
                    job.completed_at = datetime.now(timezone.utc)
                    job.heartbeat_at = datetime.now(timezone.utc)
                    await session.commit()
                    self.completed_count += 1
                    logger.info(f"Job {job_id} [{job.job_type}] completed successfully.")

        except asyncio.CancelledError:
            logger.warning(f"Job {job_id} was cancelled.")
            async with self.session_factory() as session:
                job = await session.get(BackgroundJob, job_id)
                if job:
                    job.status = "cancelled"
                    job.completed_at = datetime.now(timezone.utc)
                    job.current_step = "Job execution cancelled"
                    await session.commit()

        except Exception as e:
            logger.error(f"Job {job_id} execution failed: {e}", exc_info=True)
            async with self.session_factory() as session:
                job = await session.get(BackgroundJob, job_id)
                if job:
                    if job.retry_count < job.max_retries:
                        job.status = "queued"
                        job.retry_count += 1
                        job.current_step = f"Retrying after failure (attempt {job.retry_count}/{job.max_retries}): {str(e)[:100]}"
                        job.heartbeat_at = datetime.now(timezone.utc)
                        logger.info(f"Re-queued job {job_id} for retry ({job.retry_count}/{job.max_retries}).")
                    else:
                        job.status = "failed"
                        job.error_message = str(e)
                        job.completed_at = datetime.now(timezone.utc)
                        job.current_step = "Job failed permanently after exhausting retries."
                        self.failed_count += 1
                    await session.commit()

        finally:
            stop_heartbeat.set()
            if heartbeat_task:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass

    async def get_status(self) -> WorkerStatusResponse:
        """Return operational worker status and queue metrics."""
        queued_count = 0
        try:
            async with self.session_factory() as session:
                res = await session.execute(
                    select(func.count(BackgroundJob.id)).where(BackgroundJob.status == "queued")
                )
                queued_count = res.scalar() or 0
        except Exception:
            pass

        return WorkerStatusResponse(
            worker_id=self.worker_id,
            is_running=self.is_running,
            concurrency_limit=self.concurrency,
            active_jobs=len(self._active_tasks),
            queued_jobs=queued_count,
            completed_jobs=self.completed_count,
            failed_jobs=self.failed_count,
            uptime_seconds=round(time.time() - self._start_time, 2),
        )


# Global worker instance
worker_service = WorkerService()
