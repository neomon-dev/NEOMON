"""Intelligent Autonomous Research Planner (Milestone 9B).

Synthesizes existing NEOMON intelligence to construct prioritized, structured research plans:
- Unanswered research questions and weakly supported claims
- Claims with correlational or secondary-only evidence
- Missing primary research and full-text documents
- Active contradictions and unresolved tensions
- Falsifiable hypotheses requiring empirical testing
- High-severity research gaps

Deterministic-first generation with optional structured LLM enrichment.
No arbitrary executable operations allowed.
"""

from dataclasses import dataclass, field
from enum import StrEnum
import json
from typing import Any
import uuid

from app.models import (
    Claim,
    Evidence,
    Investigation,
    ResearchContradiction,
    ResearchGap,
    ResearchHypothesis,
    Source,
)


class ResearchActionType(StrEnum):
    REFINE_SEARCH_QUERY = "refine_search_query"
    SEARCH_ACADEMIC_LITERATURE = "search_academic_literature"
    SEARCH_GENERAL_WEB = "search_general_web"
    RETRIEVE_PRIMARY_SOURCE = "retrieve_primary_source"
    ACQUIRE_FULL_TEXT = "acquire_full_text"
    INVESTIGATE_CLAIM = "investigate_claim"
    FIND_COUNTER_EVIDENCE = "find_counter_evidence"
    INVESTIGATE_CONTRADICTION = "investigate_contradiction"
    VALIDATE_SOURCE_INDEPENDENCE = "validate_source_independence"
    IMPROVE_PROVENANCE = "improve_provenance"
    INVESTIGATE_METHODOLOGY = "investigate_methodology"
    EVALUATE_HYPOTHESIS = "evaluate_hypothesis"
    EXPAND_RESEARCH_QUESTION = "expand_research_question"
    REQUEST_HUMAN_REVIEW = "request_human_review"


@dataclass
class PlannedResearchAction:
    action_id: str
    action_type: ResearchActionType
    target_entity_type: str
    target_entity_id: str | None
    objective: str
    rationale: str
    search_queries: list[str] = field(default_factory=list)
    target_providers: list[str] = field(default_factory=list)
    priority: int = 3  # 1 (Highest) to 5 (Lowest)
    expected_information_gain: float = 0.5  # 0.0 to 1.0
    estimated_cost: float = 1.0  # Normalized resource units
    dependencies: list[str] = field(default_factory=list)
    requires_approval: bool = False


@dataclass
class ResearchPlan:
    workflow_id: str
    cycle_number: int
    cycle_goal: str
    actions: list[PlannedResearchAction] = field(default_factory=list)
    strategic_rationale: str = ""
    estimated_total_cost: float = 0.0


def plan_research_cycle(
    workflow_id: str,
    cycle_number: int,
    investigation: Investigation,
    claims: list[Claim],
    sources: list[Source],
    evidence: list[Evidence],
    gaps: list[ResearchGap] | list[dict[str, Any]] | None = None,
    contradictions: list[ResearchContradiction] | None = None,
    hypotheses: list[ResearchHypothesis] | None = None,
    executed_queries: list[str] | None = None,
    max_actions: int = 5,
) -> ResearchPlan:
    """Deterministic-first research planner constructing prioritized actions."""
    past_queries = set((executed_queries or []))
    actions: list[PlannedResearchAction] = []
    gap_list = gaps or []
    contra_list = contradictions or []
    hypo_list = hypotheses or []

    # Map evidence count and types per claim
    evidence_by_claim: dict[str, list[Evidence]] = {str(c.id): [] for c in claims}
    for ev in evidence:
        if ev.claim_id and str(ev.claim_id) in evidence_by_claim:
            evidence_by_claim[str(ev.claim_id)].append(ev)

    # 1. High Priority: Foundational claims with 0 evidence
    unsupported_claims = [c for c in claims if len(evidence_by_claim.get(str(c.id), [])) == 0]
    for c in unsupported_claims[:2]:
        q_academic = f"{c.text[:80]} empirical study"
        q_web = f"{c.text[:80]} analysis data"
        new_queries = [q for q in [q_academic, q_web] if q not in past_queries]
        if not new_queries:
            new_queries = [f"{c.text[:70]} evidence findings"]

        actions.append(
            PlannedResearchAction(
                action_id=f"act-{uuid.uuid4().hex[:8]}",
                action_type=ResearchActionType.INVESTIGATE_CLAIM,
                target_entity_type="claim",
                target_entity_id=str(c.id),
                objective=f"Retrieve direct empirical grounding for unsupported claim: '{c.text[:60]}...'",
                rationale="Claim has 0 associated evidence passages in the current research corpus.",
                search_queries=new_queries,
                target_providers=["crossref", "openalex", "arxiv", "tavily"],
                priority=1,
                expected_information_gain=0.9,
                estimated_cost=2.0,
                requires_approval=False,
            )
        )

    # 2. High Priority: Active Contradictions requiring targeted resolution
    for con in contra_list[:2]:
        if getattr(con, "status", "") in ("active", "under_debate"):
            q_res = f"reconciling {con.title[:60]} comparative evaluation"
            actions.append(
                PlannedResearchAction(
                    action_id=f"act-{uuid.uuid4().hex[:8]}",
                    action_type=ResearchActionType.INVESTIGATE_CONTRADICTION,
                    target_entity_type="contradiction",
                    target_entity_id=str(con.id),
                    objective=f"Reconcile evidentiary tension in contradiction: '{con.title[:60]}'",
                    rationale="Conflicting empirical findings prevent reliable conclusion; targeted adjudication required.",
                    search_queries=[q_res],
                    target_providers=["crossref", "arxiv"],
                    priority=1,
                    expected_information_gain=0.85,
                    estimated_cost=1.5,
                    requires_approval=False,
                )
            )

    # 3. Deliberate Counter-Evidence Search on high-confidence claims (Anti-Confirmation Bias)
    supported_claims = [c for c in claims if len(evidence_by_claim.get(str(c.id), [])) >= 2]
    if supported_claims and cycle_number >= 2:
        target_c = supported_claims[0]
        q_counter = f"limitations confounding counter-evidence {target_c.text[:60]}"
        if q_counter not in past_queries:
            actions.append(
                PlannedResearchAction(
                    action_id=f"act-{uuid.uuid4().hex[:8]}",
                    action_type=ResearchActionType.FIND_COUNTER_EVIDENCE,
                    target_entity_type="claim",
                    target_entity_id=str(target_c.id),
                    objective=f"Search for critical counter-evidence or boundary conditions on claim '{target_c.text[:50]}'",
                    rationale="Scientific rigor requires deliberate falsification testing to verify claim resilience.",
                    search_queries=[q_counter],
                    target_providers=["crossref", "openalex", "arxiv"],
                    priority=2,
                    expected_information_gain=0.8,
                    estimated_cost=1.5,
                    requires_approval=False,
                )
            )

    # 4. Critical Research Gaps
    for gap in gap_list[:2]:
        g_title = getattr(gap, "title", "") if not isinstance(gap, dict) else gap.get("title", "")
        g_id = str(getattr(gap, "id", "")) if not isinstance(gap, dict) else str(gap.get("id", ""))
        g_prio = getattr(gap, "research_priority", 5.0) if not isinstance(gap, dict) else gap.get("research_priority", 5.0)
        
        q_gap = f"{g_title[:70]} empirical literature"
        if q_gap not in past_queries:
            actions.append(
                PlannedResearchAction(
                    action_id=f"act-{uuid.uuid4().hex[:8]}",
                    action_type=ResearchActionType.REFINE_SEARCH_QUERY,
                    target_entity_type="gap",
                    target_entity_id=g_id,
                    objective=f"Close research gap: '{g_title[:60]}'",
                    rationale=f"Automated gap discovery flagged priority {g_prio:.1f} information deficiency.",
                    search_queries=[q_gap],
                    target_providers=["crossref", "openalex", "tavily"],
                    priority=2,
                    expected_information_gain=0.75,
                    estimated_cost=1.0,
                    requires_approval=False,
                )
            )

    # 5. Missing Full-Text Acquisition on key academic sources
    metadata_only_sources = [
        s for s in sources if not (getattr(s, "selected_document_url", "") or ("documents" in getattr(s, "__dict__", {}) and s.__dict__["documents"]))
        and ("academic" in (getattr(s, "source_type", "") or "") or getattr(s, "doi", None))
    ]
    for s in metadata_only_sources[:2]:
        s_title = getattr(s, "title", "Academic study")
        actions.append(
            PlannedResearchAction(
                action_id=f"act-{uuid.uuid4().hex[:8]}",
                action_type=ResearchActionType.ACQUIRE_FULL_TEXT,
                target_entity_type="source",
                target_entity_id=str(s.id),
                objective=f"Acquire open-access full text for: '{s_title[:60]}'",
                rationale="Source is currently metadata-only; full text required for rigorous methodological extraction.",
                search_queries=[],
                target_providers=["unpaywall", "arxiv", "openalex"],
                priority=3,
                expected_information_gain=0.7,
                estimated_cost=1.0,
                requires_approval=False,
            )
        )

    # 6. Falsifiable Hypothesis Evaluation
    for hyp in hypo_list[:1]:
        if getattr(hyp, "status", "") in ("proposed", "under_evaluation"):
            h_stmt = getattr(hyp, "statement", "")
            actions.append(
                PlannedResearchAction(
                    action_id=f"act-{uuid.uuid4().hex[:8]}",
                    action_type=ResearchActionType.EVALUATE_HYPOTHESIS,
                    target_entity_type="hypothesis",
                    target_entity_id=str(hyp.id),
                    objective=f"Gather empirical evidence testing hypothesis: '{h_stmt[:60]}'",
                    rationale="Evaluates testable mechanism and boundary conditions generated in Milestone 8B.",
                    search_queries=[f"testing {h_stmt[:60]} experimental results"],
                    target_providers=["crossref", "arxiv"],
                    priority=3,
                    expected_information_gain=0.65,
                    estimated_cost=1.5,
                    requires_approval=False,
                )
            )

    # Fallback: General exploratory broadening if actions are empty
    if not actions:
        base_q = f"{investigation.question[:80]} primary empirical evidence"
        actions.append(
            PlannedResearchAction(
                action_id=f"act-{uuid.uuid4().hex[:8]}",
                action_type=ResearchActionType.SEARCH_ACADEMIC_LITERATURE,
                target_entity_type="investigation",
                target_entity_id=str(investigation.id),
                objective="Broaden scientific search across academic repositories",
                rationale="Existing evidence is stable; exploratory search for newly indexed publications.",
                search_queries=[base_q],
                target_providers=["crossref", "openalex"],
                priority=4,
                expected_information_gain=0.5,
                estimated_cost=1.0,
                requires_approval=False,
            )
        )

    # Sort actions by priority (1 is highest) and take up to max_actions
    actions.sort(key=lambda a: a.priority)
    selected_actions = actions[:max_actions]

    total_cost = sum(a.estimated_cost for a in selected_actions)
    goal = f"Cycle {cycle_number}: Focus on {len(unsupported_claims)} unsupported claims, {len(contra_list)} contradictions, and targeted empirical retrieval."

    return ResearchPlan(
        workflow_id=workflow_id,
        cycle_number=cycle_number,
        cycle_goal=goal,
        actions=selected_actions,
        strategic_rationale=f"Plan generated deterministically using {len(claims)} claims, {len(sources)} sources, and {len(evidence)} evidence passages.",
        estimated_total_cost=total_cost,
    )
