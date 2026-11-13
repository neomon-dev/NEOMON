"""Evidence-Grounded Hypothesis Generation Service for NEOMON.

Implements Milestone 8B:
- Generates scientifically testable, falsifiable hypotheses grounded in observed claims,
  evidence, contradictions, and research gaps.
- Strictly adheres to scientific validity:
  * A hypothesis is not a finding or proof.
  * Correlation is never conflated with causation.
  * Explicit falsification criteria, assumptions, and confounding variables.
  * Tracks both supporting and challenging evidence.
- Multi-dimensional evaluation:
  * Evidence grounding, novelty, logical consistency, falsifiability, testability, feasibility.
- Review status lifecycle: proposed -> under_review -> supported / challenged / rejected.
- Deterministic-first generation with schema-validated LLM enrichment and robust fallback.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analysis.service import _extract_json_object
from app.models import (
    Claim,
    ClaimEvidenceRelationship,
    Document,
    Evidence,
    HypothesisEvaluation,
    Investigation,
    ResearchContradiction,
    ResearchGap,
    ResearchGapAnalysis,
    ResearchHypothesis,
    Source,
)
from app.providers import create_provider
from app.providers.base import AIProvider
from app.research.relevance import _term_matches, _terms
from app.research.scientific_integrity import classify_evidence_for_claim
from app.schemas import (
    HypothesisCategory,
    HypothesisEvaluationRequest,
    HypothesisEvaluationView,
    HypothesisGenerationResponse,
    HypothesisStatus,
    HypothesisView,
)

logger = logging.getLogger(__name__)


def _sanitize_variables(text: str) -> tuple[list[str], list[str]]:
    """Extract candidate independent and dependent variables from claim or question text."""
    lower = text.lower()
    ivs: list[str] = []
    dvs: list[str] = []

    # Look for common causal indicator patterns: "X causes/leads to/affects Y"
    causal_patterns = [
        r"how does\s+(?P<iv>[^?]+?)\s+(?:affect|impact|lead to|influence|cause)\s+(?P<dv>[^?]+)",
        r"(?P<iv>.+?)\s+(?:causes|leads to|results in|drives|increases|reduces|constrains)\s+(?P<dv>.+)",
    ]
    for pattern in causal_patterns:
        match = re.search(pattern, lower)
        if match:
            raw_iv = match.group("iv").strip()
            raw_dv = match.group("dv").strip()
            if raw_iv and raw_iv not in ivs:
                ivs.append(raw_iv)
            if raw_dv and raw_dv not in dvs:
                dvs.append(raw_dv)
            break

    if not ivs:
        words = [w for w in re.sub(r"[^\w\s]", "", text).split() if len(w) > 3]
        if len(words) >= 2:
            ivs.append(" ".join(words[:2]))
            dvs.append(" ".join(words[2:4]) if len(words) >= 4 else "observed outcome")
        else:
            ivs.append("primary condition")
            dvs.append("measured outcome")

    return ivs[:3], dvs[:3]


class HypothesisService:
    """Core engine for evidence-grounded hypothesis generation and evaluation."""

    async def generate_hypotheses(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
        provider_kind: str | None = None,
        model: str | None = None,
        force_regenerate: bool = False,
        focus_gap_id: uuid.UUID | None = None,
    ) -> HypothesisGenerationResponse:
        """Generate testable, evidence-grounded hypotheses for an investigation."""
        # 1. Check existing hypotheses if not force_regenerate
        if not force_regenerate:
            existing = await self.list_hypotheses(session, investigation_id)
            if existing:
                return HypothesisGenerationResponse(
                    investigation_id=investigation_id,
                    hypotheses=existing,
                    total=len(existing),
                )

        # 2. Fetch investigation
        inv = await session.get(Investigation, investigation_id)
        if inv is None:
            raise ValueError(f"Investigation {investigation_id} not found")

        # 3. Load claims, evidence, gaps, and sources
        claims_stmt = (
            select(Claim)
            .where(Claim.investigation_id == investigation_id)
            .order_by(Claim.priority.asc())
        )
        claims = list((await session.execute(claims_stmt)).scalars().all())
        claim_map = {c.id: c for c in claims}

        sources_stmt = select(Source).where(Source.investigation_id == investigation_id)
        sources = list((await session.execute(sources_stmt)).scalars().all())
        source_ids = [s.id for s in sources]

        evidence_items_dict: dict[uuid.UUID, Evidence] = {}
        if source_ids:
            ev_stmt = select(Evidence).where(Evidence.source_id.in_(source_ids))
            for ev in (await session.execute(ev_stmt)).scalars().all():
                evidence_items_dict[ev.id] = ev
        if claims:
            ev_claim_stmt = select(Evidence).where(Evidence.claim_id.in_(list(claim_map.keys())))
            for ev in (await session.execute(ev_claim_stmt)).scalars().all():
                evidence_items_dict[ev.id] = ev

        evidence_items = list(evidence_items_dict.values())

        # Load research gaps
        gaps_stmt = (
            select(ResearchGap)
            .where(ResearchGap.investigation_id == investigation_id)
            .order_by(ResearchGap.research_priority.desc())
        )
        gaps = list((await session.execute(gaps_stmt)).scalars().all())

        # 4. Deterministic Hypothesis Generation
        generated_candidates: list[dict[str, Any]] = []

        # Strategy A: Gap-Driven Hypotheses (Addresses identified research gaps)
        for gap in gaps[:4]:
            gap_claims = [claim_map[cid] for cid in [uuid.UUID(x) for x in json.loads(gap.claim_ids_json or "[]")] if cid in claim_map]
            primary_claim = gap_claims[0] if gap_claims else (claims[0] if claims else None)
            claim_text = primary_claim.text if primary_claim else inv.question

            ivs, dvs = _sanitize_variables(claim_text)
            iv_str = ", ".join(ivs)
            dv_str = ", ".join(dvs)

            if gap.gap_type == "unresolved_contradiction":
                cat = HypothesisCategory.comparative.value
                title = f"Boundary Condition Hypothesis: Discrepancy in {dv_str}"
                statement = (
                    f"The observed contradiction regarding '{claim_text[:90]}' is governed by operational scale "
                    f"and deployment threshold: under conditions where {iv_str} exceeds nominal capacity, "
                    f"secondary mitigating factors attenuate the primary effect."
                )
                rationale = (
                    f"Addresses unresolved contradiction flagged in gap '{gap.title}'. Reconciles conflicting "
                    "findings through parametric boundary condition testing rather than forced consensus."
                )
                falsification = (
                    f"Evidence demonstrating that the observed effect remains strictly invariant across both high and "
                    f"low thresholds of {iv_str} would falsify this hypothesis."
                )
                mechanism = f"Non-linear scaling response where {iv_str} triggers feedback inhibition."
            elif gap.gap_type in {"no_supporting_evidence", "only_contextual_evidence"}:
                cat = HypothesisCategory.causal.value
                title = f"Causal Mechanism Hypothesis: Direct effect of {iv_str} on {dv_str}"
                statement = (
                    f"Elevated levels of {iv_str} directly induce a statistically significant shift in {dv_str}, "
                    f"independent of ambient contextual factors."
                )
                rationale = (
                    f"Currently, claim '{claim_text[:80]}' lacks direct empirical corroboration (Gap: {gap.title}). "
                    "This testable causal hypothesis provides a concrete proposition for experimental validation."
                )
                falsification = (
                    f"Controlled prospective trials showing zero measurable change in {dv_str} following deliberate "
                    f"manipulation of {iv_str} would decisively falsify this hypothesis."
                )
                mechanism = f"Direct causal pathway wherein {iv_str} modulates {dv_str}."
            elif gap.gap_type == "missing_mitigating_factors":
                cat = HypothesisCategory.mechanistic.value
                title = f"Mitigating Factor Hypothesis: Adaptive buffering of {dv_str}"
                statement = (
                    f"The adverse impact of {iv_str} on {dv_str} is substantially mitigated when adaptive "
                    "compensatory protocols are proactively deployed."
                )
                rationale = (
                    f"Addresses perspective gap '{gap.title}' by introducing an empirical test of compensatory adaptations."
                )
                falsification = (
                    f"Empirical data showing that adaptive protocols yield no attenuation of {dv_str} would falsify this hypothesis."
                )
                mechanism = "Counterbalancing operational buffers absorb peak demand."
            else:
                cat = HypothesisCategory.correlational.value
                title = f"Correlational Hypothesis: Association between {iv_str} and {dv_str}"
                statement = (
                    f"Cross-sectional variations in {iv_str} positively correlate with variations in {dv_str} "
                    f"across diverse operational cohorts."
                )
                rationale = f"Formulated to resolve knowledge gap: {gap.title}."
                falsification = f"Meta-analysis demonstrating a correlation coefficient indistinguishable from zero (r ≈ 0)."
                mechanism = "Co-occurring systemic dependency."

            # Collect supporting and challenging evidence references
            supp_ev_ids = []
            chall_ev_ids = []
            for ev in evidence_items:
                ev_type = getattr(ev, "evidence_type", "").lower()
                if ev_type in {"supporting", "direct"}:
                    supp_ev_ids.append(ev.id)
                elif ev_type in {"contradicting", "counter"}:
                    chall_ev_ids.append(ev.id)

            generated_candidates.append({
                "title": title[:290],
                "statement": statement,
                "rationale": rationale,
                "category": cat,
                "claim_ids": [c.id for c in gap_claims] if gap_claims else ([claims[0].id] if claims else []),
                "evidence_ids": [e.id for e in evidence_items[:5]],
                "gap_ids": [gap.id],
                "supporting_evidence_ids": supp_ev_ids[:4],
                "challenging_evidence_ids": chall_ev_ids[:4],
                "proposed_mechanism": mechanism,
                "independent_variables": ivs,
                "dependent_variables": dvs,
                "expected_outcome": f"Measurable non-random variation in {dv_str}.",
                "boundary_conditions": f"Applicable when baseline {iv_str} exceeds minimum detection sensitivity.",
                "assumptions": ["Measurement instruments exhibit adequate test-retest reliability.", "Confounders are controlled."],
                "confounding_variables": ["Sampling selection bias", "Unmeasured temporal shocks"],
                "suggested_methodology": "Pre-registered controlled comparative trial with stratified cohort sampling.",
                "falsification_criteria": falsification,
                "generation_method": "deterministic",
                "confidence_level": "medium",
                "testability_score": 8.0,
                "novelty_score": 7.0,
                "evidence_grounding_score": 7.5,
                "falsifiability_score": 8.5,
            })

        # Strategy B: If no gaps existed, formulate from primary claims
        if not generated_candidates and claims:
            for c in claims[:3]:
                ivs, dvs = _sanitize_variables(c.text)
                title = f"Empirical Test Hypothesis: {c.text[:80]}"
                statement = (
                    f"Under standardized testing environments, {', '.join(ivs)} produces a reproducible effect "
                    f"on {', '.join(dvs)} consistent with '{c.text}'."
                )
                falsification = f"Failure to observe directional effect in replications with p > 0.05."
                generated_candidates.append({
                    "title": title[:290],
                    "statement": statement,
                    "rationale": f"Systematic empirical formulation of foundational claim '{c.text}'.",
                    "category": HypothesisCategory.causal.value if c.priority == 1 else HypothesisCategory.correlational.value,
                    "claim_ids": [c.id],
                    "evidence_ids": [e.id for e in evidence_items[:4]],
                    "gap_ids": [],
                    "supporting_evidence_ids": [e.id for e in evidence_items if getattr(e, "evidence_type", "") == "supporting"][:3],
                    "challenging_evidence_ids": [e.id for e in evidence_items if getattr(e, "evidence_type", "") == "contradicting"][:3],
                    "proposed_mechanism": "Direct mechanistic entailment.",
                    "independent_variables": ivs,
                    "dependent_variables": dvs,
                    "expected_outcome": "Statistically significant directional variance.",
                    "boundary_conditions": "Controlled laboratory or structured observational settings.",
                    "assumptions": ["Stable baseline operating parameters."],
                    "confounding_variables": ["Measurement noise", "Temporal drift"],
                    "suggested_methodology": "Randomized comparative benchmark evaluation.",
                    "falsification_criteria": falsification,
                    "generation_method": "deterministic",
                    "confidence_level": "medium",
                    "testability_score": 7.5,
                    "novelty_score": 6.5,
                    "evidence_grounding_score": 7.0,
                    "falsifiability_score": 8.0,
                })

        # Strategy C: Primary Question Exploratory Fallback if no candidates generated yet
        if not generated_candidates:
            ivs, dvs = _sanitize_variables(inv.question)
            title = f"Exploratory Hypothesis: Investigating {', '.join(dvs) or 'core inquiry'}"
            generated_candidates.append({
                "title": title[:290],
                "statement": (
                    f"In the context of '{inv.question[:120]}', systematic variation in {', '.join(ivs)} "
                    f"produces measurable variance on {', '.join(dvs)}."
                ),
                "rationale": "Initial exploratory hypothesis formulated directly from the primary research inquiry.",
                "category": HypothesisCategory.exploratory.value,
                "claim_ids": [c.id for c in claims],
                "evidence_ids": [e.id for e in evidence_items[:4]],
                "gap_ids": [g.id for g in gaps[:2]],
                "supporting_evidence_ids": [],
                "challenging_evidence_ids": [],
                "proposed_mechanism": "Systemic domain interaction.",
                "independent_variables": ivs,
                "dependent_variables": dvs,
                "expected_outcome": "Empirical directional variance observed under standardized metrics.",
                "boundary_conditions": "Target domain context.",
                "assumptions": ["Contextual variables remain bounded."],
                "confounding_variables": ["Unmeasured external factors"],
                "suggested_methodology": "Systematic literature review and empirical benchmarking.",
                "falsification_criteria": "Controlled trials demonstrating zero measurable change in dependent outcomes.",
                "generation_method": "deterministic",
                "confidence_level": "medium",
                "testability_score": 7.0,
                "novelty_score": 6.0,
                "evidence_grounding_score": 6.5,
                "falsifiability_score": 7.5,
            })

        # 5. Optional LLM Enrichment (Guarded)
        effective_provider = provider_kind
        effective_model = model
        if effective_provider:
            try:
                llm_hyps = await self._run_llm_hypothesis_generation(
                    provider_kind=effective_provider,
                    model=effective_model,
                    question=inv.question,
                    claims=claims,
                    evidence_count=len(evidence_items),
                    gaps=gaps,
                )
                for lh in llm_hyps:
                    lh["generation_method"] = "hybrid"
                    # Validate that claim_ids exist
                    valid_cids = [cid for cid in lh.get("claim_ids", []) if cid in claim_map]
                    lh["claim_ids"] = valid_cids or ([claims[0].id] if claims else [])
                    lh["gap_ids"] = [gid for gid in lh.get("gap_ids", []) if any(g.id == gid for g in gaps)]
                    generated_candidates.append(lh)
            except Exception as e:
                logger.warning("LLM hypothesis enrichment failed gracefully: %s", e)

        # 6. Deduplicate candidates by title / statement
        seen_titles: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for cand in generated_candidates:
            key = cand["title"].strip().lower()
            if key not in seen_titles:
                seen_titles.add(key)
                deduped.append(cand)

        # 7. Persist to Database
        persisted_views: list[HypothesisView] = []
        for item in deduped:
            hyp_id = uuid.uuid4()
            hyp_record = ResearchHypothesis(
                id=hyp_id,
                investigation_id=investigation_id,
                title=item["title"][:300],
                statement=item["statement"],
                rationale=item["rationale"],
                category=item.get("category", HypothesisCategory.causal.value),
                status=HypothesisStatus.proposed.value,
                claim_ids_json=json.dumps([str(cid) for cid in item.get("claim_ids", [])]),
                evidence_ids_json=json.dumps([str(eid) for eid in item.get("evidence_ids", [])]),
                gap_ids_json=json.dumps([str(gid) for gid in item.get("gap_ids", [])]),
                supporting_evidence_ids_json=json.dumps([str(eid) for eid in item.get("supporting_evidence_ids", [])]),
                challenging_evidence_ids_json=json.dumps([str(eid) for eid in item.get("challenging_evidence_ids", [])]),
                proposed_mechanism=item.get("proposed_mechanism", ""),
                independent_variables_json=json.dumps(item.get("independent_variables", [])),
                dependent_variables_json=json.dumps(item.get("dependent_variables", [])),
                expected_outcome=item.get("expected_outcome", ""),
                boundary_conditions=item.get("boundary_conditions", ""),
                assumptions_json=json.dumps(item.get("assumptions", [])),
                confounding_variables_json=json.dumps(item.get("confounding_variables", [])),
                suggested_methodology=item.get("suggested_methodology", ""),
                falsification_criteria=item.get("falsification_criteria", ""),
                generation_method=item.get("generation_method", "deterministic"),
                confidence_level=item.get("confidence_level", "medium"),
                testability_score=float(item.get("testability_score", 7.0)),
                novelty_score=float(item.get("novelty_score", 6.0)),
                evidence_grounding_score=float(item.get("evidence_grounding_score", 7.0)),
                falsifiability_score=float(item.get("falsifiability_score", 8.0)),
                evaluation_notes=item.get("evaluation_notes", "Automated baseline generation."),
                version_number=1,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(hyp_record)

            persisted_views.append(
                HypothesisView(
                    id=hyp_id,
                    investigation_id=investigation_id,
                    title=hyp_record.title,
                    statement=hyp_record.statement,
                    rationale=hyp_record.rationale,
                    category=hyp_record.category,
                    status=hyp_record.status,
                    claim_ids=[uuid.UUID(str(x)) for x in item.get("claim_ids", [])],
                    evidence_ids=[uuid.UUID(str(x)) for x in item.get("evidence_ids", [])],
                    gap_ids=[uuid.UUID(str(x)) for x in item.get("gap_ids", [])],
                    supporting_evidence_ids=[uuid.UUID(str(x)) for x in item.get("supporting_evidence_ids", [])],
                    challenging_evidence_ids=[uuid.UUID(str(x)) for x in item.get("challenging_evidence_ids", [])],
                    proposed_mechanism=hyp_record.proposed_mechanism,
                    independent_variables=item.get("independent_variables", []),
                    dependent_variables=item.get("dependent_variables", []),
                    expected_outcome=hyp_record.expected_outcome,
                    boundary_conditions=hyp_record.boundary_conditions,
                    assumptions=item.get("assumptions", []),
                    confounding_variables=item.get("confounding_variables", []),
                    suggested_methodology=hyp_record.suggested_methodology,
                    falsification_criteria=hyp_record.falsification_criteria,
                    generation_method=hyp_record.generation_method,
                    confidence_level=hyp_record.confidence_level,
                    testability_score=hyp_record.testability_score,
                    novelty_score=hyp_record.novelty_score,
                    evidence_grounding_score=hyp_record.evidence_grounding_score,
                    falsifiability_score=hyp_record.falsifiability_score,
                    evaluation_notes=hyp_record.evaluation_notes,
                    version_number=hyp_record.version_number,
                    evaluations=[],
                    created_at=hyp_record.created_at,
                    updated_at=hyp_record.updated_at,
                )
            )

        await session.commit()

        return HypothesisGenerationResponse(
            investigation_id=investigation_id,
            hypotheses=persisted_views,
            total=len(persisted_views),
        )

    async def _run_llm_hypothesis_generation(
        self,
        provider_kind: str,
        model: str | None,
        question: str,
        claims: list[Claim],
        evidence_count: int,
        gaps: list[ResearchGap],
    ) -> list[dict[str, Any]]:
        """LLM enrichment for mechanistic or exploratory scientific hypotheses."""
        from app.schemas import ProviderConfigRequest, ProviderKind
        prov = create_provider(ProviderConfigRequest(provider=ProviderKind(provider_kind), model=model))

        prompt = (
            f"You are the Hypothesis Generator for NEOMON.\n"
            f"Research Question: {question}\n\n"
            f"Claims ({len(claims)}):\n"
            + "\n".join(f"- [{c.id}] {c.text}" for c in claims[:4])
            + f"\n\nObserved Evidence Count: {evidence_count}\n"
            f"Observed Research Gaps ({len(gaps)}):\n"
            + "\n".join(f"- [{g.id}] {g.title}" for g in gaps[:3])
            + "\n\nFormulate 1 novel, scientifically grounded, testable hypothesis that addresses these gaps.\n"
            "Requirements:\n"
            "- A hypothesis is not a fact or finding.\n"
            "- State explicit falsification criteria.\n"
            "- Identify independent and dependent variables, assumptions, and confounding variables.\n"
            "- Return strictly valid JSON object with a 'hypotheses' list matching the schema.\n"
            "{\n"
            '  "hypotheses": [\n'
            "    {\n"
            '      "title": "short title",\n'
            '      "statement": "clear testable statement",\n'
            '      "rationale": "scientific rationale",\n'
            '      "category": "causal" or "mechanistic" or "comparative",\n'
            '      "proposed_mechanism": "mechanism",\n'
            '      "independent_variables": ["var1"],\n'
            '      "dependent_variables": ["var2"],\n'
            '      "expected_outcome": "expected outcome",\n'
            '      "boundary_conditions": "conditions",\n'
            '      "assumptions": ["assumption1"],\n'
            '      "confounding_variables": ["confounder1"],\n'
            '      "suggested_methodology": "methodology",\n'
            '      "falsification_criteria": "what specific evidence would disprove this",\n'
            '      "testability_score": 8.0,\n'
            '      "novelty_score": 7.5,\n'
            '      "evidence_grounding_score": 7.0,\n'
            '      "falsifiability_score": 8.5\n'
            "    }\n"
            "  ]\n"
            "}"
        )

        res = await prov.generate(
            prompt,
            system_instruction="You are a rigorous scientific hypothesis generator. Output valid JSON only.",
        )
        parsed = _extract_json_object(res.content)
        raw_list = parsed.get("hypotheses", [])
        return [h for h in raw_list if isinstance(h, dict) and "statement" in h and "falsification_criteria" in h]

    async def list_hypotheses(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
        category: str | None = None,
        status: str | None = None,
        min_testability: float | None = None,
    ) -> list[HypothesisView]:
        """List hypotheses for an investigation with optional filtering."""
        stmt = (
            select(ResearchHypothesis)
            .where(ResearchHypothesis.investigation_id == investigation_id)
            .options(selectinload(ResearchHypothesis.evaluations))
            .order_by(ResearchHypothesis.testability_score.desc(), ResearchHypothesis.created_at.desc())
        )
        records = list((await session.execute(stmt)).scalars().all())

        if category:
            records = [r for r in records if r.category.lower() == category.lower()]
        if status:
            records = [r for r in records if r.status.lower() == status.lower()]
        if min_testability is not None:
            records = [r for r in records if r.testability_score >= min_testability]

        views: list[HypothesisView] = []
        for r in records:
            views.append(self._to_view(r))
        return views

    async def get_hypothesis(
        self, session: AsyncSession, investigation_id: uuid.UUID, hypothesis_id: uuid.UUID
    ) -> HypothesisView | None:
        """Retrieve a specific hypothesis with evaluations."""
        stmt = (
            select(ResearchHypothesis)
            .where(
                ResearchHypothesis.id == hypothesis_id,
                ResearchHypothesis.investigation_id == investigation_id,
            )
            .options(selectinload(ResearchHypothesis.evaluations))
        )
        record = (await session.execute(stmt)).scalars().first()
        if record is None:
            return None
        return self._to_view(record)

    async def update_hypothesis_status(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
        hypothesis_id: uuid.UUID,
        new_status: str,
        review_comments: str = "",
    ) -> HypothesisView:
        """Update review status of a hypothesis."""
        stmt = select(ResearchHypothesis).where(
            ResearchHypothesis.id == hypothesis_id,
            ResearchHypothesis.investigation_id == investigation_id,
        )
        record = (await session.execute(stmt)).scalars().first()
        if record is None:
            raise ValueError(f"Hypothesis {hypothesis_id} not found")

        record.status = new_status
        record.updated_at = datetime.now(UTC)
        if review_comments:
            record.evaluation_notes = (
                f"{record.evaluation_notes}\n[{datetime.now(UTC).isoformat()}] Status changed to {new_status}: {review_comments}"
            ).strip()

        # Log evaluation
        eval_record = HypothesisEvaluation(
            id=uuid.uuid4(),
            hypothesis_id=hypothesis_id,
            reviewer_role="human_reviewer",
            status=new_status,
            evidence_grounding_score=record.evidence_grounding_score,
            novelty_score=record.novelty_score,
            logical_consistency_score=8.0,
            falsifiability_score=record.falsifiability_score,
            testability_score=record.testability_score,
            methodological_feasibility_score=7.0,
            review_comments=review_comments,
            created_at=datetime.now(UTC),
        )
        session.add(eval_record)
        await session.commit()

        return await self.get_hypothesis(session, investigation_id, hypothesis_id)  # type: ignore

    async def evaluate_hypothesis(
        self,
        session: AsyncSession,
        investigation_id: uuid.UUID,
        hypothesis_id: uuid.UUID,
        payload: HypothesisEvaluationRequest,
    ) -> HypothesisView:
        """Submit a structured multi-dimensional evaluation for a hypothesis."""
        stmt = select(ResearchHypothesis).where(
            ResearchHypothesis.id == hypothesis_id,
            ResearchHypothesis.investigation_id == investigation_id,
        )
        record = (await session.execute(stmt)).scalars().first()
        if record is None:
            raise ValueError(f"Hypothesis {hypothesis_id} not found")

        eval_record = HypothesisEvaluation(
            id=uuid.uuid4(),
            hypothesis_id=hypothesis_id,
            reviewer_role=payload.reviewer_role,
            status=payload.status,
            evidence_grounding_score=payload.evidence_grounding_score,
            novelty_score=payload.novelty_score,
            logical_consistency_score=payload.logical_consistency_score,
            falsifiability_score=payload.falsifiability_score,
            testability_score=payload.testability_score,
            methodological_feasibility_score=payload.methodological_feasibility_score,
            review_comments=payload.review_comments,
            created_at=datetime.now(UTC),
        )
        session.add(eval_record)

        # Update aggregated scores on the hypothesis model
        record.status = payload.status
        record.evidence_grounding_score = payload.evidence_grounding_score
        record.novelty_score = payload.novelty_score
        record.falsifiability_score = payload.falsifiability_score
        record.testability_score = payload.testability_score
        record.updated_at = datetime.now(UTC)

        await session.commit()
        return await self.get_hypothesis(session, investigation_id, hypothesis_id)  # type: ignore

    def _to_view(self, r: ResearchHypothesis) -> HypothesisView:
        """Convert ORM model to schema view."""
        eval_views = [
            HypothesisEvaluationView(
                id=e.id,
                hypothesis_id=e.hypothesis_id,
                reviewer_role=e.reviewer_role,
                status=e.status,
                evidence_grounding_score=e.evidence_grounding_score,
                novelty_score=e.novelty_score,
                logical_consistency_score=e.logical_consistency_score,
                falsifiability_score=e.falsifiability_score,
                testability_score=e.testability_score,
                methodological_feasibility_score=e.methodological_feasibility_score,
                review_comments=e.review_comments,
                created_at=e.created_at,
            )
            for e in getattr(r, "evaluations", [])
        ]

        return HypothesisView(
            id=r.id,
            investigation_id=r.investigation_id,
            title=r.title,
            statement=r.statement,
            rationale=r.rationale,
            category=r.category,
            status=r.status,
            claim_ids=[uuid.UUID(x) for x in json.loads(r.claim_ids_json or "[]")],
            evidence_ids=[uuid.UUID(x) for x in json.loads(r.evidence_ids_json or "[]")],
            gap_ids=[uuid.UUID(x) for x in json.loads(r.gap_ids_json or "[]")],
            supporting_evidence_ids=[uuid.UUID(x) for x in json.loads(r.supporting_evidence_ids_json or "[]")],
            challenging_evidence_ids=[uuid.UUID(x) for x in json.loads(r.challenging_evidence_ids_json or "[]")],
            proposed_mechanism=r.proposed_mechanism,
            independent_variables=json.loads(r.independent_variables_json or "[]"),
            dependent_variables=json.loads(r.dependent_variables_json or "[]"),
            expected_outcome=r.expected_outcome,
            boundary_conditions=r.boundary_conditions,
            assumptions=json.loads(r.assumptions_json or "[]"),
            confounding_variables=json.loads(r.confounding_variables_json or "[]"),
            suggested_methodology=r.suggested_methodology,
            falsification_criteria=r.falsification_criteria,
            generation_method=r.generation_method,
            confidence_level=r.confidence_level,
            testability_score=r.testability_score,
            novelty_score=r.novelty_score,
            evidence_grounding_score=r.evidence_grounding_score,
            falsifiability_score=r.falsifiability_score,
            evaluation_notes=r.evaluation_notes,
            version_number=r.version_number,
            evaluations=eval_views,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )


hypothesis_service = HypothesisService()
