import asyncio
import json
import logging
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Investigation,
    ResearchMonitoringConfig,
    ResearchMonitoringRun,
    User,
    Workspace,
    Notification,
    Source,
    Evidence,
    ResearchContradiction,
)
from app.schemas import InvestigationCreate

logger = logging.getLogger("neomon.monitoring")


class MonitoringService:
    """Manages scheduled research monitoring configurations and execution cycles."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_configs(
        self,
        workspace_id: uuid.UUID,
        is_active: bool | None = None,
    ) -> list[ResearchMonitoringConfig]:
        stmt = select(ResearchMonitoringConfig).where(
            ResearchMonitoringConfig.workspace_id == workspace_id
        )
        if is_active is not None:
            stmt = stmt.where(ResearchMonitoringConfig.is_active == is_active)
        stmt = stmt.order_by(ResearchMonitoringConfig.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_config(self, config_id: uuid.UUID) -> ResearchMonitoringConfig | None:
        return await self.db.get(ResearchMonitoringConfig, config_id)

    async def create_config(
        self,
        workspace_id: uuid.UUID,
        investigation_id: uuid.UUID,
        creator: User,
        name: str,
        query_keywords: str,
        interval_minutes: int = 60,
        max_new_sources_per_run: int = 5,
    ) -> ResearchMonitoringConfig:
        config = ResearchMonitoringConfig(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            investigation_id=investigation_id,
            created_by=creator.id,
            name=name,
            query_keywords=query_keywords,
            interval_minutes=max(5, interval_minutes),
            max_new_sources_per_run=max(1, min(20, max_new_sources_per_run)),
            is_active=True,
            next_run_at=datetime.now(UTC) + timedelta(minutes=interval_minutes),
        )
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def update_config(
        self,
        config: ResearchMonitoringConfig,
        name: str | None = None,
        query_keywords: str | None = None,
        interval_minutes: int | None = None,
        is_active: bool | None = None,
        max_new_sources_per_run: int | None = None,
    ) -> ResearchMonitoringConfig:
        if name is not None:
            config.name = name
        if query_keywords is not None:
            config.query_keywords = query_keywords
        if interval_minutes is not None:
            config.interval_minutes = max(5, interval_minutes)
        if is_active is not None:
            config.is_active = is_active
        if max_new_sources_per_run is not None:
            config.max_new_sources_per_run = max(1, min(20, max_new_sources_per_run))
        config.updated_at = datetime.now(UTC)
        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def delete_config(self, config: ResearchMonitoringConfig) -> None:
        await self.db.delete(config)
        await self.db.commit()

    async def execute_monitoring_run(
        self,
        config: ResearchMonitoringConfig,
        triggered_by: str = "n8n",
        idempotency_key: str | None = None,
    ) -> ResearchMonitoringRun:
        """Trigger incremental research, evaluating new sources, evidence, and contradictions.

        Prevents duplicate runs using idempotency_key and deduplicates existing sources.
        """
        # Idempotency check
        if idempotency_key:
            stmt = select(ResearchMonitoringRun).where(
                ResearchMonitoringRun.idempotency_key == idempotency_key
            )
            existing_run = (await self.db.execute(stmt)).scalar_one_or_none()
            if existing_run:
                logger.info("Monitoring run for idempotency key %s already processed", idempotency_key)
                return existing_run

        t0 = time.perf_counter()
        run = ResearchMonitoringRun(
            id=uuid.uuid4(),
            monitoring_config_id=config.id,
            status="running",
            triggered_by=triggered_by,
            idempotency_key=idempotency_key,
            started_at=datetime.now(UTC),
        )
        self.db.add(run)
        await self.db.commit()
        await self.db.refresh(run)

        try:
            # Query existing sources for this investigation to prevent duplicate ingestion
            existing_sources_stmt = select(Source.canonical_url).where(
                Source.investigation_id == config.investigation_id
            )
            existing_urls = set((await self.db.execute(existing_sources_stmt)).scalars().all())

            # Count evidence and contradictions before run
            ev_count_stmt = select(Evidence.id).join(Source, Evidence.source_id == Source.id).where(
                Source.investigation_id == config.investigation_id
            )
            ev_before = len((await self.db.execute(ev_count_stmt)).scalars().all())

            contra_stmt = select(ResearchContradiction.id).where(
                ResearchContradiction.primary_investigation_id == config.investigation_id
            )
            contra_before = len((await self.db.execute(contra_stmt)).scalars().all())

            # Incrementally discover and evaluate sources via existing research discovery
            from app.research.providers import build_research_providers, SearchQuery
            from app.research.normalization import normalize_url

            investigation = await self.db.get(Investigation, config.investigation_id)
            new_sources_discovered = 0

            if investigation:
                # Execute focused search query on configured keywords
                search_keywords = [kw.strip() for kw in config.query_keywords.split(",") if kw.strip()]
                if not search_keywords:
                    search_keywords = [investigation.question]

                providers = build_research_providers()
                try:
                    for kw in search_keywords[:3]:
                        sq = SearchQuery(text=kw, category="academic")
                        for p in providers:
                            try:
                                search_results = await p.search(sq, limit=config.max_new_sources_per_run)
                                for res in search_results:
                                    norm_url = normalize_url(res.url)
                                    if norm_url in existing_urls:
                                        continue
                                    existing_urls.add(norm_url)
                                    # Create Source record
                                    src = Source(
                                        id=uuid.uuid4(),
                                        investigation_id=config.investigation_id,
                                        original_url=res.url,
                                        canonical_url=norm_url,
                                        title=res.title or "Monitoring Discovered Document",
                                        publisher=res.publisher,
                                        source_type=res.source_type or "academic",
                                        relevance_score=res.relevance_score or 0.8,
                                        inclusion_status="included",
                                    )
                                    self.db.add(src)
                                    new_sources_discovered += 1
                                    if new_sources_discovered >= config.max_new_sources_per_run:
                                        break
                            except Exception as e:
                                logger.warning("Monitoring provider %s query '%s' failed: %s", getattr(p, "name", "unknown"), kw, e)
                        if new_sources_discovered >= config.max_new_sources_per_run:
                            break
                    await self.db.commit()
                finally:
                    await asyncio.gather(*(p.close() for p in providers), return_exceptions=True)

            # Count after run
            ev_after = len((await self.db.execute(ev_count_stmt)).scalars().all())
            contra_after = len((await self.db.execute(contra_stmt)).scalars().all())

            run.sources_discovered = new_sources_discovered
            run.evidence_extracted = max(0, ev_after - ev_before)
            run.contradictions_detected = max(0, contra_after - contra_before)
            run.status = "completed"
            run.completed_at = datetime.now(UTC)
            run.execution_latency_ms = (time.perf_counter() - t0) * 1000.0

            # Update configuration telemetry
            config.last_run_at = datetime.now(UTC)
            config.next_run_at = datetime.now(UTC) + timedelta(minutes=config.interval_minutes)
            config.consecutive_failures = 0
            config.last_error = None

            # Create notification for workspace researcher
            notification = Notification(
                id=uuid.uuid4(),
                workspace_id=config.workspace_id,
                user_id=config.created_by,
                event_type="monitoring_update",
                title=f"Monitoring Alert: {config.name}",
                message=(
                    f"Discovered {new_sources_discovered} new source(s), "
                    f"{run.evidence_extracted} passage(s), and {run.contradictions_detected} contradiction(s)."
                ),
                link_url=f"/investigations/{config.investigation_id}",
            )
            self.db.add(notification)
            await self.db.commit()
            await self.db.refresh(run)
            return run

        except Exception as exc:
            logger.error("Error executing monitoring run for config %s: %s", config.id, exc, exc_info=True)
            run.status = "failed"
            run.error_message = str(exc)
            run.completed_at = datetime.now(UTC)
            run.execution_latency_ms = (time.perf_counter() - t0) * 1000.0

            config.consecutive_failures += 1
            config.last_error = str(exc)
            await self.db.commit()
            await self.db.refresh(run)
            return run
