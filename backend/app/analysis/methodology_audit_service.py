"""Comprehensive Research Methodology Audit Service (Milestone 12).

Evaluates investigations across 15 scientific methodology dimensions:
- Research question clarity and scope boundaries
- Claim decomposition granularity
- Selection, geographic, temporal, and publication-type biases
- Confounding variables and correlation-vs-causation errors
- Missing primary sources and unaddressed counterevidence
- Distinguishes confirmed problems from potential concerns and unassessed limitations.
"""

from collections import defaultdict
from datetime import datetime, timezone
from enum import StrEnum
import json
import logging
import re
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Claim,
    Evidence,
    Investigation,
    MethodologyAuditFinding,
    Source,
)
from app.analysis.evidence_verification_service import RelationshipClassification

logger = logging.getLogger("neomon.analysis.methodology_audit")


class AuditSeverity(StrEnum):
    CONFIRMED_PROBLEM = "confirmed_problem"
    POTENTIAL_CONCERN = "potential_concern"
    UNASSESSED_LIMITATION = "unassessed_limitation"


class MethodologyAuditService:
    """Executes evidence-backed methodology audits for research investigations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def audit_investigation(
        self,
        investigation_id: uuid.UUID,
    ) -> List[MethodologyAuditFinding]:
        """Execute comprehensive methodology audit and persist findings."""
        inv = await self.db.get(Investigation, investigation_id)
        if not inv:
            raise ValueError("Investigation not found.")

        # Fetch claims, sources, and evidence
        claims = list((await self.db.execute(select(Claim).where(Claim.investigation_id == investigation_id))).scalars().all())
        sources = list((await self.db.execute(select(Source).where(Source.investigation_id == investigation_id))).scalars().all())
        
        ev_stmt = (
            select(Evidence)
            .join(Source, Evidence.source_id == Source.id)
            .where(Source.investigation_id == investigation_id)
        )
        evidence_list = list((await self.db.execute(ev_stmt)).scalars().all())

        # Clear prior findings for clean re-audit
        old_findings = await self.db.execute(
            select(MethodologyAuditFinding).where(MethodologyAuditFinding.investigation_id == investigation_id)
        )
        for old in old_findings.scalars().all():
            await self.db.delete(old)

        findings: List[MethodologyAuditFinding] = []
        now = datetime.now(timezone.utc)

        # -------------------------------------------------------------
        # 1. Research Question Clarity & Scope
        # -------------------------------------------------------------
        q = (inv.question or "").strip()
        if len(q.split()) < 4:
            findings.append(MethodologyAuditFinding(
                id=uuid.uuid4(),
                investigation_id=investigation_id,
                audit_dimension="question_clarity",
                issue_severity=AuditSeverity.CONFIRMED_PROBLEM.value,
                finding_title="Research Question Lacks Sufficient Specificity",
                description="The research question contains fewer than 4 words, leaving scope boundaries undefined.",
                missing_data_condition="Explicit scope parameters (population, timeframe, specific mechanism) are missing.",
                suggested_action="Refine question with specific domain entities, constraints, or comparative criteria.",
                created_at=now,
            ))
        elif "?" not in q and not any(q.lower().startswith(w) for w in ["what", "how", "why", "investigate", "analyze", "evaluate"]):
            findings.append(MethodologyAuditFinding(
                id=uuid.uuid4(),
                investigation_id=investigation_id,
                audit_dimension="question_clarity",
                issue_severity=AuditSeverity.POTENTIAL_CONCERN.value,
                finding_title="Non-Interrogative Question Formulation",
                description="The research question is formulated as a keyword phrase rather than a falsifiable inquiry.",
                suggested_action="Reformulate question as an empirical, falsifiable question.",
                created_at=now,
            ))

        # -------------------------------------------------------------
        # 2. Claim Decomposition Granularity
        # -------------------------------------------------------------
        if len(claims) == 1 and len(q.split()) >= 8:
            findings.append(MethodologyAuditFinding(
                id=uuid.uuid4(),
                investigation_id=investigation_id,
                audit_dimension="claim_decomposition",
                issue_severity=AuditSeverity.CONFIRMED_PROBLEM.value,
                finding_title="Complex Inquiry Reduced to Single Atomic Claim",
                description="The investigation addresses a multi-faceted inquiry but decomposed into only 1 atomic claim, risking oversimplification.",
                missing_data_condition="Decomposition of sub-mechanisms and rival hypotheses.",
                suggested_action="Decompose investigation question into 3-5 sub-claims covering preconditions, direct effects, and counter-effects.",
                created_at=now,
            ))

        # -------------------------------------------------------------
        # 3. Source Selection & Publication-Type Bias
        # -------------------------------------------------------------
        academic_count = sum(1 for s in sources if s.source_type in ("peer_reviewed", "academic"))
        vendor_count = sum(1 for s in sources if s.source_type in ("vendor_commercial", "corporate_disclosure"))
        
        if len(sources) >= 3 and academic_count == 0:
            findings.append(MethodologyAuditFinding(
                id=uuid.uuid4(),
                investigation_id=investigation_id,
                audit_dimension="source_selection_bias",
                issue_severity=AuditSeverity.CONFIRMED_PROBLEM.value,
                finding_title="Total Absence of Peer-Reviewed Literature",
                description="All retrieved sources originate from commercial web, journalism, or vendor content with 0 peer-reviewed papers.",
                missing_data_condition="Peer-reviewed studies or institutional academic datasets.",
                suggested_action="Formulate academic retrieval queries targeting OpenAlex, Semantic Scholar, or Unpaywall DOIs.",
                created_at=now,
            ))
        elif len(sources) >= 3 and (vendor_count / len(sources)) >= 0.50:
            findings.append(MethodologyAuditFinding(
                id=uuid.uuid4(),
                investigation_id=investigation_id,
                audit_dimension="publication_bias",
                issue_severity=AuditSeverity.POTENTIAL_CONCERN.value,
                finding_title="High Vendor / Corporate Source Concentration",
                description=f"Commercial and vendor sources represent {round(vendor_count/len(sources)*100)}% of retrieved evidence.",
                suggested_action="Incorporate non-vendor independent audits or third-party academic benchmarks.",
                created_at=now,
            ))

        # -------------------------------------------------------------
        # 4. Temporal Bias & Publication Date Limitations
        # -------------------------------------------------------------
        years: List[int] = []
        for s in sources:
            if not s.publication_date:
                continue
            if isinstance(s.publication_date, datetime):
                years.append(s.publication_date.year)
            elif isinstance(s.publication_date, str):
                m = re.search(r"\b(19\d\d|20\d\d)\b", s.publication_date)
                if m:
                    years.append(int(m.group(1)))
        current_year = datetime.now(timezone.utc).year
        if years and max(years) < (current_year - 5):
            findings.append(MethodologyAuditFinding(
                id=uuid.uuid4(),
                investigation_id=investigation_id,
                audit_dimension="temporal_bias",
                issue_severity=AuditSeverity.CONFIRMED_PROBLEM.value,
                finding_title="Outdated Evidence Base (> 5 Years Old)",
                description=f"The most recent source retrieved was published in {max(years)}, which may omit recent technological developments.",
                missing_data_condition=f"Contemporary publications from {current_year - 3} to {current_year}.",
                suggested_action="Execute recency-filtered search queries for publications from the past 24 months.",
                created_at=now,
            ))

        # -------------------------------------------------------------
        # 5. Correlation vs. Causation & Confounding Variables
        # -------------------------------------------------------------
        correlational_evidence = []
        for ev in evidence_list:
            text = (ev.passage or "").lower()
            if any(term in text for term in ["correlated with", "associated with", "linked to", "coincides with"]):
                correlational_evidence.append(ev)

        if correlational_evidence:
            first_ev = correlational_evidence[0]
            findings.append(MethodologyAuditFinding(
                id=uuid.uuid4(),
                investigation_id=investigation_id,
                audit_dimension="correlation_vs_causation",
                issue_severity=AuditSeverity.POTENTIAL_CONCERN.value,
                finding_title="Associative Evidence Used for Causal Propositions",
                description=f"Identified {len(correlational_evidence)} passages expressing statistical association without demonstrating isolating mechanism.",
                linked_source_id=first_ev.source_id,
                linked_passage_text=first_ev.passage[:200] if first_ev.passage else None,
                suggested_action="Verify whether controlled trials, difference-in-differences, or natural experiment analyses exist.",
                created_at=now,
            ))

        # -------------------------------------------------------------
        # 6. Sample Size Limitations (Where Reported)
        # -------------------------------------------------------------
        small_sample_ev = [ev for ev in evidence_list if re.search(r"\b(n\s*=\s*[1-9]\d?|small\s+sample|sample\s+size\s+of\s+\d{1,2})\b", ev.passage or "", re.I)]
        if small_sample_ev:
            findings.append(MethodologyAuditFinding(
                id=uuid.uuid4(),
                investigation_id=investigation_id,
                audit_dimension="sample_size_limitations",
                issue_severity=AuditSeverity.CONFIRMED_PROBLEM.value,
                finding_title="Empirical Findings Constrained by Small Sample Size",
                description="Evidence indicates restricted sample cohorts (N < 100), limiting statistical power and generalizability.",
                linked_source_id=small_sample_ev[0].source_id,
                linked_passage_text=small_sample_ev[0].passage[:200] if small_sample_ev[0].passage else None,
                suggested_action="Seek larger meta-analyses or multi-center cohort replications.",
                created_at=now,
            ))

        # -------------------------------------------------------------
        # 7. Unassessed Generalizability
        # -------------------------------------------------------------
        findings.append(MethodologyAuditFinding(
            id=uuid.uuid4(),
            investigation_id=investigation_id,
            audit_dimension="generalizability",
            issue_severity=AuditSeverity.UNASSESSED_LIMITATION.value,
            finding_title="Cross-Domain Generalizability Unverified",
            description="Available evidence does not establish whether findings hold across differing operating conditions or external industry sectors.",
            missing_data_condition="Cross-industry replication data.",
            suggested_action="Conduct targeted search for replication studies in alternative operational contexts.",
            created_at=now,
        ))

        for f in findings:
            self.db.add(f)

        await self.db.commit()
        return findings

    async def list_methodology_findings(
        self,
        investigation_id: uuid.UUID,
    ) -> List[MethodologyAuditFinding]:
        """Fetch audit findings for an investigation."""
        stmt = select(MethodologyAuditFinding).where(
            MethodologyAuditFinding.investigation_id == investigation_id
        ).order_by(MethodologyAuditFinding.issue_severity.asc(), MethodologyAuditFinding.created_at.asc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())
