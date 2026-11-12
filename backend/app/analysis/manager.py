import asyncio
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.analysis.service import run_analysis
from app.db import SessionFactory
from app.events import EventBroker
from app.models import AnalysisJob, Investigation
from app.schemas import ProviderConfigRequest


class AnalysisManager:
    def __init__(self, broker: EventBroker) -> None:
        self.broker = broker
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def schedule(
        self,
        job_id: str,
        question: str,
        provider_config: ProviderConfigRequest | None = None,
        role_models: dict[str, str] | None = None,
    ) -> None:
        if job_id in self._tasks and not self._tasks[job_id].done():
            return
        task = asyncio.create_task(self._run(job_id, question, provider_config, role_models))
        self._tasks[job_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(job_id, None))

    async def _run(
        self,
        job_id: str,
        question: str,
        provider_config: ProviderConfigRequest | None,
        role_models: dict[str, str] | None,
    ) -> None:
        async with SessionFactory() as session:
            job = await session.get(AnalysisJob, uuid.UUID(job_id))
            if job is None:
                return
            await run_analysis(session, self.broker, job, question, provider_config, role_models)

    async def recover(self) -> None:
        to_schedule: list[tuple[str, str]] = []
        async with SessionFactory() as session:
            stale_investigations = list(
                (await session.scalars(select(Investigation).where(Investigation.status == "running"))).all()
            )
            for inv in stale_investigations:
                inv.status = "failed"
                inv.evidence_gap = (
                    f"{inv.evidence_gap} " if inv.evidence_gap else ""
                ) + "Investigation was interrupted by a backend restart."

            jobs = list(
                (
                    await session.scalars(
                        select(AnalysisJob).where(
                            AnalysisJob.status.in_(
                                ("queued", "planning", "researching", "debating", "adjudicating", "reporting")
                            )
                        )
                    )
                ).all()
            )
            now = datetime.now(UTC)
            for job in jobs:
                if job.cancel_requested:
                    job.status = "cancelled"
                    job.completed_at = now
                    job.error_message = "Analysis cancelled before completion."
                    continue
                if job.provider_kind is not None:
                    job.status = "failed"
                    job.completed_at = now
                    job.error_message = (
                        "Backend restarted during provider-backed analysis; re-enter provider credentials and re-run."
                    )
                    continue
                job.status = "queued"
                job.error_message = "Recovered after backend restart; continuing rule-based analysis."
                parent = await session.get(Investigation, job.investigation_id)
                if parent is not None:
                    to_schedule.append((str(job.id), parent.question))
            await session.commit()

        for job_id, question in to_schedule:
            self.schedule(job_id, question)

    async def cancel(self, job_id: str) -> bool:
        try:
            job_uuid = uuid.UUID(job_id)
        except ValueError:
            return False
        async with SessionFactory() as session:
            job = await session.get(AnalysisJob, job_uuid)
            if job is None:
                return False
            job.cancel_requested = True
            if job.status == "queued":
                job.status = "cancelled"
            await session.commit()
        task = self._tasks.get(str(job_uuid))
        if task is not None and not task.done():
            task.cancel()
        return True


async def stop_analysis_manager(manager: AnalysisManager) -> None:
    tasks = list(manager._tasks.values())
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
