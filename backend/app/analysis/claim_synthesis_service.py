"""Claim-Level Evidence Synthesis Engine (Milestone 12).

Synthesizes multi-stream evidence for individual atomic claims:
1. Evaluates direct support, partial support, contradictions, and contextual material.
2. Distinguishes unique underlying studies from syndicated duplicates.
3. Derives transparent, non-arbitrary claim outcomes.
4. Identifies critical missing evidence and methodological limitations.
"""

from collections import defaultdict
from datetime import datetime, timezone
from enum import StrEnum
import json
import logging
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Claim,
    ClaimSynthesisResult,
    EvidenceVerificationRecord,
    Investigation,
    Source,
    StudyIndependenceCluster,
)
from app.analysis.evidence_verification_service import RelationshipClassification

logger = logging.getLogger("neomon.analysis.claim_synthesis")


class ClaimSynthesisOutcome(StrEnum):
    STRONGLY_SUPPORTED = "strongly_supported"
    MODERATELY_SUPPORTED = "moderately_supported"
    WEAKLY_SUPPORTED = "weakly_supported"
    MIXED_EVIDENCE = "mixed_evidence"
    CONTRADICTED = "contradicted"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    NOT_ASSESSED = "not_assessed"


class ClaimSynthesisService:
    """Computes transparent, defensible evidence synthesis per claim."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def synthesize_investigation_claims(
        self,
        investigation_id: uuid.UUID,
    ) -> List[ClaimSynthesisResult]:
        """Synthesize all atomic claims for an investigation based on verified records."""
        # Fetch claims
        claims_res = await self.db.execute(
            select(Claim).where(Claim.investigation_id == investigation_id)
        )
        claims = list(claims_res.scalars().all())

        # Fetch verification records
        vr_stmt = select(EvidenceVerificationRecord).where(
            EvidenceVerificationRecord.investigation_id == investigation_id
        )
        vr_res = await self.db.execute(vr_stmt)
        records = list(vr_res.scalars().all())

        # Fetch study independence clusters
        cluster_stmt = select(StudyIndependenceCluster).where(
            StudyIndependenceCluster.investigation_id == investigation_id
        )
        cluster_res = await self.db.execute(cluster_stmt)
        clusters = list(cluster_res.scalars().all())

        # Map source_id to cluster_id to track unique underlying studies
        source_to_cluster: Dict[str, str] = {}
        for c in clusters:
            try:
                member_ids = json.loads(c.member_source_ids_json)
                for sid in member_ids:
                    source_to_cluster[str(sid)] = str(c.id)
            except Exception:
                pass

        # Group records by claim_id
        records_by_claim: Dict[uuid.UUID, List[EvidenceVerificationRecord]] = defaultdict(list)
        for r in records:
            records_by_claim[r.claim_id].append(r)

        results: List[ClaimSynthesisResult] = []
        now = datetime.now(timezone.utc)

        # Clear previous synthesis results for clean re-assessment
        old_res = await self.db.execute(
            select(ClaimSynthesisResult).where(
                ClaimSynthesisResult.investigation_id == investigation_id
            )
        )
        for old in old_res.scalars().all():
            await self.db.delete(old)

        for claim in claims:
            claim_records = records_by_claim.get(claim.id, [])
            synth = self._evaluate_single_claim(
                claim=claim,
                records=claim_records,
                source_to_cluster=source_to_cluster,
                investigation_id=investigation_id,
                now=now,
            )
            self.db.add(synth)
            results.append(synth)

        await self.db.commit()
        return results

    def _evaluate_single_claim(
        self,
        claim: Claim,
        records: List[EvidenceVerificationRecord],
        source_to_cluster: Dict[str, str],
        investigation_id: uuid.UUID,
        now: datetime,
    ) -> ClaimSynthesisResult:
        if not records:
            return ClaimSynthesisResult(
                id=uuid.uuid4(),
                investigation_id=investigation_id,
                claim_id=claim.id,
                synthesis_outcome=ClaimSynthesisOutcome.NOT_ASSESSED.value,
                explanation="No verification records have been generated for this claim.",
                created_at=now,
                updated_at=now,
            )

        direct_supporting = [r for r in records if r.relationship_classification == RelationshipClassification.DIRECTLY_SUPPORTS.value]
        partial_supporting = [r for r in records if r.relationship_classification == RelationshipClassification.PARTIALLY_SUPPORTS.value]
        contradicting = [r for r in records if r.relationship_classification == RelationshipClassification.CONTRADICTS.value]
        contextual = [r for r in records if r.relationship_classification in (
            RelationshipClassification.CONTEXTUAL_BACKGROUND.value,
            RelationshipClassification.METHODOLOGICAL_CONTEXT.value,
            RelationshipClassification.MENTIONS_SUBJECT.value,
        )]
        unverified = [r for r in records if r.relationship_classification in (
            RelationshipClassification.INSUFFICIENT_INFORMATION.value,
            RelationshipClassification.UNVERIFIABLE.value,
        )]

        # Unique sources and studies
        relevant_source_ids = {str(r.source_id) for r in (direct_supporting + partial_supporting + contradicting)}
        
        # Determine unique underlying studies
        supporting_study_keys = set()
        for r in direct_supporting:
            sid = str(r.source_id)
            # Use cluster_id if part of a cluster, otherwise individual source_id
            cluster_id = source_to_cluster.get(sid, sid)
            supporting_study_keys.add(cluster_id)

        all_study_keys = set()
        for sid in relevant_source_ids:
            all_study_keys.add(source_to_cluster.get(sid, sid))

        unique_studies_count = len(all_study_keys) if all_study_keys else len(relevant_source_ids)
        direct_studies_count = len(supporting_study_keys)

        # Publication date distribution
        year_dist: Dict[str, int] = defaultdict(int)
        for r in records:
            if r.source_publication_date:
                yr = str(r.source_publication_date.year)
                year_dist[yr] += 1

        # Independence score calculation: ratio of unique studies to relevant sources
        independence_score = round(unique_studies_count / max(1, len(relevant_source_ids)), 2) if relevant_source_ids else 0.50

        # Methodological limitations and missing evidence
        methodological_limitations = []
        if len(records) > 0 and direct_studies_count <= 1:
            methodological_limitations.append("Relies on single study or uncorroborated primary source.")
        if any(r.confidence < 0.60 for r in direct_supporting):
            methodological_limitations.append("Some supporting passages have low inferential confidence.")

        missing_evidence = []
        if len(direct_supporting) == 0:
            missing_evidence.append("Lacks direct empirical evidence; relies on partial or contextual passages.")
        if len(contradicting) > 0:
            missing_evidence.append("Requires reconciliation of unresolved contradictory evidence.")

        # Transparent rule-based outcome determination
        if len(contradicting) > 0 and len(direct_supporting) > 0:
            outcome = ClaimSynthesisOutcome.MIXED_EVIDENCE
            exp = f"Claim has mixed evidence: {len(direct_supporting)} direct supporting passages alongside {len(contradicting)} contradicting passages."
        elif len(contradicting) > 0 and len(direct_supporting) == 0:
            outcome = ClaimSynthesisOutcome.CONTRADICTED
            exp = f"Evidence directly contradicts claim proposition ({len(contradicting)} contradicting passages, 0 supporting)."
        elif direct_studies_count >= 2 and independence_score >= 0.70:
            outcome = ClaimSynthesisOutcome.STRONGLY_SUPPORTED
            exp = f"Strongly supported by {direct_studies_count} independent empirical studies with no unrefuted contradictions."
        elif direct_studies_count >= 1 or len(partial_supporting) >= 2:
            outcome = ClaimSynthesisOutcome.MODERATELY_SUPPORTED
            exp = f"Moderately supported by {direct_studies_count} study/sources with corroborating partial evidence."
        elif len(partial_supporting) > 0:
            outcome = ClaimSynthesisOutcome.WEAKLY_SUPPORTED
            exp = f"Weakly supported: contains partial corroboration ({len(partial_supporting)} passages) without conclusive direct proof."
        else:
            outcome = ClaimSynthesisOutcome.INSUFFICIENT_EVIDENCE
            exp = "Insufficient empirical evidence: passages provide background context without proving specific claim."

        return ClaimSynthesisResult(
            id=uuid.uuid4(),
            investigation_id=investigation_id,
            claim_id=claim.id,
            relevant_sources_count=len(relevant_source_ids),
            unique_underlying_studies_count=unique_studies_count,
            direct_supporting_count=len(direct_supporting),
            partial_supporting_count=len(partial_supporting),
            contradicting_count=len(contradicting),
            contextual_count=len(contextual),
            unverified_count=len(unverified),
            methodological_limitations_json=json.dumps(methodological_limitations),
            publication_date_distribution_json=json.dumps(dict(year_dist)),
            source_independence_score=independence_score,
            important_missing_evidence_json=json.dumps(missing_evidence),
            outstanding_verification_operations_json=json.dumps([]),
            synthesis_outcome=outcome.value,
            explanation=exp,
            created_at=now,
            updated_at=now,
        )

    async def list_claim_synthesis_results(
        self,
        investigation_id: uuid.UUID,
    ) -> List[ClaimSynthesisResult]:
        """Retrieve synthesis results for an investigation."""
        stmt = select(ClaimSynthesisResult).where(
            ClaimSynthesisResult.investigation_id == investigation_id
        ).order_by(ClaimSynthesisResult.created_at.asc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
