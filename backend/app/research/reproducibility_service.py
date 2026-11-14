"""Research Execution Manifest and Reproducibility Service (Milestone 12).

Preserves immutable, machine-readable provenance records for research investigations:
1. Generates cryptographic SHA-256 manifest hashes.
2. Captures complete configuration snapshots, query histories, and agent timelines.
3. Completely sanitizes API keys and private credentials.
4. Allows reproduction attempts to spawn new versioned executions without overwriting historical data.
"""

from datetime import datetime, timezone
import hashlib
import json
import logging
import re
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AnalysisAgentExecution,
    AnalysisJob,
    AutonomousResearchWorkflow,
    Claim,
    Evidence,
    Investigation,
    ResearchExecutionManifest,
    ResearchQualityCalibration,
    ResearchQueryHistory,
    Source,
)

logger = logging.getLogger("neomon.research.reproducibility")


def sanitize_sensitive_config(data: Any) -> Any:
    """Recursively scrub API keys, tokens, and passwords from config objects."""
    if isinstance(data, dict):
        sanitized = {}
        for k, v in data.items():
            if any(s in k.lower() for s in ["key", "secret", "token", "password", "auth", "credential"]):
                sanitized[k] = "***REDACTED***"
            else:
                sanitized[k] = sanitize_sensitive_config(v)
        return sanitized
    elif isinstance(data, list):
        return [sanitize_sensitive_config(item) for item in data]
    return data


class ReproducibilityService:
    """Manages research manifests, integrity verification, and reproduction runs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_manifest(
        self,
        investigation_id: uuid.UUID,
    ) -> ResearchExecutionManifest:
        """Construct canonical research manifest and compute cryptographic hash."""
        inv = await self.db.get(Investigation, investigation_id)
        if not inv:
            raise ValueError("Investigation not found.")

        # Gather sources
        sources = list((await self.db.execute(select(Source).where(Source.investigation_id == investigation_id))).scalars().all())
        source_manifest = []
        for s in sources:
            source_manifest.append({
                "source_id": str(s.id),
                "title": s.title,
                "canonical_url": s.canonical_url,
                "doi": s.doi,
                "publication_date": s.publication_date.isoformat() if isinstance(s.publication_date, datetime) else str(s.publication_date) if s.publication_date else None,
                "source_type": s.source_type,
                "publisher": s.publisher,
                "retrieval_timestamp": s.retrieval_timestamp.isoformat() if s.retrieval_timestamp else None,
            })

        # Gather evidence
        ev_stmt = select(Evidence).join(Source, Evidence.source_id == Source.id).where(Source.investigation_id == investigation_id)
        evidence_list = list((await self.db.execute(ev_stmt)).scalars().all())
        evidence_manifest = []
        for e in evidence_list:
            passage_hash = hashlib.sha256((e.passage or "").encode("utf-8")).hexdigest()
            evidence_manifest.append({
                "evidence_id": str(e.id),
                "source_id": str(e.source_id),
                "passage_sha256": passage_hash,
                "passage_excerpt": (e.passage or "")[:150],
                "char_length": len(e.passage or ""),
            })

        # Gather search queries via workflows linked to this investigation
        workflows = list((await self.db.execute(select(AutonomousResearchWorkflow).where(AutonomousResearchWorkflow.investigation_id == investigation_id))).scalars().all())
        wf_ids = [w.id for w in workflows]
        queries = []
        if wf_ids:
            queries = list((await self.db.execute(select(ResearchQueryHistory).where(ResearchQueryHistory.workflow_id.in_(wf_ids)))).scalars().all())

        search_manifest = []
        for q in queries:
            search_manifest.append({
                "query": q.query_text,
                "provider": q.provider,
                "executed_at": q.created_at.isoformat() if q.created_at else None,
                "results_count": q.results_count,
            })

        # Gather agent timeline via analysis jobs linked to this investigation
        jobs = list((await self.db.execute(select(AnalysisJob).where(AnalysisJob.investigation_id == investigation_id))).scalars().all())
        job_ids = [j.id for j in jobs]
        agent_execs = []
        if job_ids:
            agent_execs = list((await self.db.execute(select(AnalysisAgentExecution).where(AnalysisAgentExecution.job_id.in_(job_ids)))).scalars().all())

        timeline = []
        for ae in agent_execs:
            timeline.append({
                "agent_role": ae.agent_identifier,
                "status": ae.status,
                "model_identifier": ae.model,
                "started_at": ae.started_at.isoformat() if ae.started_at else None,
                "completed_at": ae.completed_at.isoformat() if ae.completed_at else None,
            })

        # Gather quality snapshot
        qual_res = await self.db.execute(
            select(ResearchQualityCalibration).where(ResearchQualityCalibration.investigation_id == investigation_id)
        )
        qual = qual_res.scalars().first()
        quality_snapshot = {
            "calibrated_tier": qual.calibrated_tier if qual else "Inconclusive",
            "calibrated_score": qual.calibrated_score if qual else 0.0,
            "raw_score": qual.raw_score if qual else 0.0,
        }

        # Build canonical dict for hashing
        canonical_payload = {
            "manifest_version": "1.0",
            "investigation_id": str(investigation_id),
            "research_question": inv.question,
            "investigation_mode": inv.mode,
            "sources": source_manifest,
            "evidence": evidence_manifest,
            "search_queries": search_manifest,
            "agent_timeline": timeline,
            "quality_snapshot": quality_snapshot,
        }

        canonical_str = json.dumps(canonical_payload, sort_keys=True)
        manifest_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

        # Check reproducibility status
        is_fully_reproducible = len(source_manifest) > 0 and len(timeline) > 0
        repro_status = "fully_reproducible" if is_fully_reproducible else "observational_only"
        notes = "Deterministic heuristics and exact passage hashes recorded. Note that dynamic LLM completions exhibit stochastic variability across model versions."

        manifest = ResearchExecutionManifest(
            id=uuid.uuid4(),
            investigation_id=investigation_id,
            manifest_version="1.0",
            manifest_hash=manifest_hash,
            research_question=inv.question or "",
            config_snapshot_json=json.dumps({"mode": inv.mode, "timeframe": inv.timeframe}),
            claim_decomposition_version="1.0",
            search_queries_json=json.dumps(search_manifest),
            providers_used_json=json.dumps(list({s["provider"] for s in search_manifest if s.get("provider")})),
            execution_timeline_json=json.dumps(timeline),
            source_manifest_json=json.dumps(source_manifest),
            evidence_manifest_json=json.dumps(evidence_manifest),
            quality_assessment_snapshot_json=json.dumps(quality_snapshot),
            reproducibility_status=repro_status,
            reproducibility_notes=notes,
            created_at=datetime.now(timezone.utc),
        )

        self.db.add(manifest)
        await self.db.commit()
        await self.db.refresh(manifest)
        return manifest

    async def get_latest_manifest(
        self,
        investigation_id: uuid.UUID,
    ) -> Optional[ResearchExecutionManifest]:
        """Fetch the latest reproducibility manifest for an investigation."""
        stmt = (
            select(ResearchExecutionManifest)
            .where(ResearchExecutionManifest.investigation_id == investigation_id)
            .order_by(ResearchExecutionManifest.created_at.desc())
            .limit(1)
        )
        res = await self.db.execute(stmt)
        return res.scalars().first()

    async def verify_manifest_integrity(
        self,
        manifest_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """Verify cryptographic integrity of an existing manifest."""
        manifest = await self.db.get(ResearchExecutionManifest, manifest_id)
        if not manifest:
            raise ValueError("Manifest not found.")

        canonical_payload = {
            "manifest_version": manifest.manifest_version,
            "investigation_id": str(manifest.investigation_id),
            "research_question": manifest.research_question,
            "investigation_mode": json.loads(manifest.config_snapshot_json).get("mode", "deep"),
            "sources": json.loads(manifest.source_manifest_json),
            "evidence": json.loads(manifest.evidence_manifest_json),
            "search_queries": json.loads(manifest.search_queries_json),
            "agent_timeline": json.loads(manifest.execution_timeline_json),
            "quality_snapshot": json.loads(manifest.quality_assessment_snapshot_json),
        }
        canonical_str = json.dumps(canonical_payload, sort_keys=True)
        computed_hash = hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()

        is_valid = computed_hash == manifest.manifest_hash
        return {
            "manifest_id": str(manifest.id),
            "stored_hash": manifest.manifest_hash,
            "computed_hash": computed_hash,
            "is_tamper_free": is_valid,
            "status": "verified" if is_valid else "tampered",
        }

    async def reproduce_investigation_run(
        self,
        original_investigation_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Investigation:
        """Create a new versioned investigation execution linked to the parent manifest."""
        orig = await self.db.get(Investigation, original_investigation_id)
        if not orig:
            raise ValueError("Original investigation not found.")

        latest_manifest = await self.get_latest_manifest(original_investigation_id)
        if not latest_manifest:
            latest_manifest = await self.generate_manifest(original_investigation_id)

        # Spawn a new distinct investigation
        reproduced = Investigation(
            id=uuid.uuid4(),
            question=f"[Reproduction] {orig.question}",
            mode=orig.mode,
            timeframe=orig.timeframe,
            status="created",
            workspace_id=orig.workspace_id,
            owner_id=user_id,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(reproduced)
        await self.db.commit()
        await self.db.refresh(reproduced)

        # Link child manifest to parent
        child_manifest = await self.generate_manifest(reproduced.id)
        child_manifest.parent_reproduced_manifest_id = latest_manifest.id
        child_manifest.reproducibility_notes = f"Reproduction run initiated from Parent Manifest {latest_manifest.id} (Hash: {latest_manifest.manifest_hash[:16]}...)"
        await self.db.commit()

        return reproduced
