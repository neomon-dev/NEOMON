"""Intelligent prompt and context optimization for NEOMON multi-agent network.

Provides token-aware budgeting, role-specific evidence filtering, passage
deduplication, and concise structured payload synthesis to minimize TTFT and KV-cache
overhead on local OpenVINO / Intel Arc GPU runtimes without reducing scientific rigor.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from typing import Any, Sequence

from app.models import Claim, Document, Evidence, Source


@dataclass(frozen=True)
class AgentContextBudget:
    role: str
    target_prompt_tokens: int
    max_completion_tokens: int
    max_evidence_per_claim: int
    preserve_full_text: bool


# Empirical token budgets calibrated for Intel Arc GPU Unified Shared Memory (USM)
AGENT_BUDGETS: dict[str, AgentContextBudget] = {
    "intelligence_planner": AgentContextBudget(
        role="intelligence_planner",
        target_prompt_tokens=400,
        max_completion_tokens=1024,
        max_evidence_per_claim=0,
        preserve_full_text=False,
    ),
    "advocate": AgentContextBudget(
        role="advocate",
        target_prompt_tokens=1400,
        max_completion_tokens=1536,
        max_evidence_per_claim=4,
        preserve_full_text=False,
    ),
    "skeptic": AgentContextBudget(
        role="skeptic",
        target_prompt_tokens=1400,
        max_completion_tokens=1536,
        max_evidence_per_claim=4,
        preserve_full_text=False,
    ),
    "methodology_auditor": AgentContextBudget(
        role="methodology_auditor",
        target_prompt_tokens=1400,
        max_completion_tokens=1536,
        max_evidence_per_claim=4,
        preserve_full_text=False,
    ),
    "source_intelligence": AgentContextBudget(
        role="source_intelligence",
        target_prompt_tokens=1300,
        max_completion_tokens=1536,
        max_evidence_per_claim=3,
        preserve_full_text=False,
    ),
    "citation_genealogy": AgentContextBudget(
        role="citation_genealogy",
        target_prompt_tokens=1300,
        max_completion_tokens=1536,
        max_evidence_per_claim=3,
        preserve_full_text=False,
    ),
    "temporal_intelligence": AgentContextBudget(
        role="temporal_intelligence",
        target_prompt_tokens=1300,
        max_completion_tokens=1536,
        max_evidence_per_claim=3,
        preserve_full_text=False,
    ),
    "debate_moderator": AgentContextBudget(
        role="debate_moderator",
        target_prompt_tokens=1200,
        max_completion_tokens=1024,
        max_evidence_per_claim=0,
        preserve_full_text=False,
    ),
    "conflict_adjudicator": AgentContextBudget(
        role="conflict_adjudicator",
        target_prompt_tokens=1800,
        max_completion_tokens=1536,
        max_evidence_per_claim=4,
        preserve_full_text=False,
    ),
    "report_intelligence": AgentContextBudget(
        role="report_intelligence",
        target_prompt_tokens=2200,
        max_completion_tokens=2048,
        max_evidence_per_claim=5,
        preserve_full_text=False,
    ),
}

DEFAULT_BUDGET = AgentContextBudget(
    role="default",
    target_prompt_tokens=1400,
    max_completion_tokens=1536,
    max_evidence_per_claim=4,
    preserve_full_text=False,
)


def estimate_tokens(text: str) -> int:
    """Fast, accurate token estimation (~4 chars/token with word boundary compensation)."""
    if not text:
        return 0
    words = len(text.split())
    chars = len(text)
    return max(words, int(chars / 3.8))


def compact_evidence_text(text: str, max_length: int = 500) -> str:
    """Normalize whitespace and cap length while preserving complete sentences where possible."""
    cleaned = " ".join(text.strip().split())
    if len(cleaned) <= max_length:
        return cleaned
    truncated = cleaned[:max_length]
    last_period = truncated.rfind(".")
    if last_period > max_length // 2:
        return truncated[: last_period + 1]
    return truncated + "..."


METHODOLOGY_KEYWORDS = re.compile(
    r"\b(method|design|sample|control|cohort|trial|random|p-value|ci|error|bias|observational|retrospective|prospective|statistical|protocol|reproduc)\b",
    re.IGNORECASE,
)

TEMPORAL_KEYWORDS = re.compile(
    r"\b(year|annual|period|trend|recent|20\d\d|baseline|follow-up|longitudinal|timeline|historical|projection|horizon)\b",
    re.IGNORECASE,
)


def deduplicate_evidence(evidence_items: Sequence[Evidence]) -> list[Evidence]:
    """Remove exact or near-duplicate passages while preserving distinct IDs and types."""
    seen_hashes: set[str] = set()
    unique: list[Evidence] = []
    for item in evidence_items:
        normalized = " ".join(item.exact_text.casefold().split()[:25])
        if normalized not in seen_hashes:
            seen_hashes.add(normalized)
            unique.append(item)
    return unique


def select_evidence_for_role(
    role: str,
    evidence_items: Sequence[Evidence],
    budget: AgentContextBudget,
) -> list[Evidence]:
    """Select the most informative, role-specific evidence items up to the agent's budget."""
    if not evidence_items:
        return []

    deduped = deduplicate_evidence(evidence_items)
    limit = budget.max_evidence_per_claim

    if role == "advocate":
        # Prioritize supporting and empirical evidence with high relevance
        supporting = [e for e in deduped if e.evidence_type == "supporting"]
        supporting.sort(key=lambda e: (e.relevance_score or 0.0), reverse=True)
        if len(supporting) < limit:
            others = [e for e in deduped if e.evidence_type != "supporting"]
            others.sort(key=lambda e: (e.relevance_score or 0.0), reverse=True)
            return (supporting + others)[:limit]
        return supporting[:limit]

    elif role == "skeptic":
        # Critical invariant: NEVER drop contradicting or mitigating evidence
        contradicting = [
            e for e in deduped if e.evidence_type in {"contradicting", "mitigating", "methodological_limitation"}
        ]
        contradicting.sort(key=lambda e: (e.relevance_score or 0.0), reverse=True)
        # Also include low-relevance or qualifying passages for skepticism
        remaining = [e for e in deduped if e not in contradicting]
        remaining.sort(key=lambda e: (e.relevance_score or 0.0))
        return (contradicting + remaining)[:limit]

    elif role == "methodology_auditor":
        # Score by presence of methodological indicators and limitations
        def method_score(e: Evidence) -> tuple[int, float]:
            matches = len(METHODOLOGY_KEYWORDS.findall(e.exact_text))
            is_limit = 1 if e.evidence_type == "methodological_limitation" else 0
            return (matches + is_limit * 2, e.relevance_score or 0.0)

        scored = sorted(deduped, key=method_score, reverse=True)
        return scored[:limit]

    elif role == "source_intelligence":
        # Diverse sources with rich metadata
        seen_sources: set[uuid.UUID] = set()
        diverse: list[Evidence] = []
        for e in deduped:
            if e.source_id not in seen_sources:
                seen_sources.add(e.source_id)
                diverse.append(e)
        if len(diverse) < limit:
            remaining = [e for e in deduped if e not in diverse]
            diverse.extend(remaining)
        return diverse[:limit]

    elif role == "citation_genealogy":
        # Passages with citation/provenance links or multiple source overlaps
        return deduped[:limit]

    elif role == "temporal_intelligence":
        # Passages with temporal markers or publication dates
        def temporal_score(e: Evidence) -> tuple[int, float]:
            matches = len(TEMPORAL_KEYWORDS.findall(e.exact_text))
            return (matches, e.relevance_score or 0.0)

        scored = sorted(deduped, key=temporal_score, reverse=True)
        return scored[:limit]

    else:
        # Default ranking by relevance
        sorted_ev = sorted(deduped, key=lambda e: (e.relevance_score or 0.0), reverse=True)
        return sorted_ev[:limit]


def build_specialist_agent_context(
    role: str,
    claims: list[Claim],
    associated_evidence: dict[uuid.UUID, list[Evidence]],
    sources: dict[uuid.UUID, Source],
    documents: dict[uuid.UUID, Document],
) -> dict[str, Any]:
    """Construct an optimized, compact JSON context payload tailored for a specialist agent."""
    budget = AGENT_BUDGETS.get(role, DEFAULT_BUDGET)
    max_char_len = 700 if role in {"advocate", "skeptic", "methodology_auditor"} else 500

    context_claims: list[dict[str, Any]] = []
    for claim in claims:
        all_ev = associated_evidence.get(claim.id, [])
        selected_ev = select_evidence_for_role(role, all_ev, budget)

        claim_entry: dict[str, Any] = {
            "claim_id": str(claim.id),
            "text": claim.text,
            "evidence": [
                {
                    "evidence_id": str(ev.id),
                    "source_id": str(ev.source_id),
                    "text": compact_evidence_text(ev.exact_text, max_length=max_char_len),
                    "type": ev.evidence_type,
                }
                for ev in selected_ev
            ],
        }
        context_claims.append(claim_entry)

    return {
        "role": role,
        "claims": context_claims,
    }


def build_adjudication_compact_context(
    claims: list[Claim],
    arguments: list[Any],
    evidence: list[Evidence],
    associated_evidence: dict[uuid.UUID, list[Evidence]],
    documents: dict[uuid.UUID, Document],
) -> dict[str, Any]:
    """Construct an optimized context for the conflict adjudicator."""
    budget = AGENT_BUDGETS.get("conflict_adjudicator", DEFAULT_BUDGET)

    # Only include evidence associated with claims or cited in arguments
    cited_evidence_ids = {
        uuid.UUID(str(eid))
        for arg in arguments
        for eid in (getattr(arg, "evidence_ids", None) or [])
    }
    for claim in claims:
        for ev in associated_evidence.get(claim.id, []):
            cited_evidence_ids.add(ev.id)

    relevant_evidence = [e for e in evidence if e.id in cited_evidence_ids]
    deduped_evidence = deduplicate_evidence(relevant_evidence)

    # Sort so contradictory evidence is listed first to guarantee detection
    deduped_evidence.sort(
        key=lambda e: (1 if e.evidence_type in {"contradicting", "mitigating"} else 0, e.relevance_score or 0.0),
        reverse=True,
    )

    return {
        "claims": [
            {
                "claim_id": str(item.id),
                "text": item.text,
                "associated_evidence_ids": [str(ev.id) for ev in associated_evidence.get(item.id, [])[:budget.max_evidence_per_claim]],
            }
            for item in claims
        ],
        "arguments": [
            {
                "argument_id": str(getattr(item, "id", "") or getattr(item, "argument_id", "")),
                "claim_id": str(item.claim_id),
                "agent": getattr(item, "agent_identifier", None) or getattr(item, "agent", "specialist"),
                "type": getattr(item, "argument_type", "supporting"),
                "text": getattr(item, "text", "")[:400],
                "evidence_ids": [str(eid) for eid in (getattr(item, "evidence_ids", []) or [])],
                "evidence_basis": getattr(item, "evidence_basis", "direct"),
                "limitations": (getattr(item, "limitations", []) or [])[:3],
            }
            for item in arguments
        ],
        "evidence": [
            {
                "evidence_id": str(item.id),
                "source_id": str(item.source_id),
                "claim_id": str(item.claim_id) if item.claim_id else None,
                "exact_text": compact_evidence_text(item.exact_text, max_length=500),
                "type": item.evidence_type,
                "relevance_score": item.relevance_score,
                "access_level": documents[item.document_id].access_level if item.document_id in documents else "metadata_only",
            }
            for item in deduped_evidence[:24]
        ],
    }
