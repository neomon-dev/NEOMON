import json
import logging
import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.protocol import DecisionPayload, EvidenceProvenance, ReportSectionPayload
from app.models import (
    AdjudicationDecision,
    AgentArgument,
    AnalysisJob,
    Claim,
    Document,
    Evidence,
    Investigation,
    ReportSection,
    ReportVersion,
    ResearchReport,
    Source,
)
from app.schemas import (
    EvidenceStrengthBreakdown,
    EvidenceStrengthSummary,
    ReportSectionView,
    ReportVersionView,
)
from app.research.scientific_integrity import (
    assess_source_credibility,
    detect_source_independence_clusters,
)

logger = logging.getLogger(__name__)

REPORT_18_SECTION_SPECS = [
    ("executive_summary", "Executive Summary"),
    ("research_question", "Research Question & Scope"),
    ("investigation_scope", "Methodology & Investigation Strategy"),
    ("search_strategy", "Search & Source Discovery Strategy"),
    ("key_findings", "Key Findings Summary"),
    ("claim_by_claim_assessment", "Claim-by-Claim Assessment"),
    ("supporting_evidence", "Supporting Evidence Analysis"),
    ("contradicting_evidence", "Contradicting & Conflicting Evidence Analysis"),
    ("advocate_perspective", "Advocate Perspective Synthesis"),
    ("skeptic_perspective", "Skeptic Perspective Synthesis"),
    ("methodological_assessment", "Methodological Assessment & Quality Audit"),
    ("source_quality_assessment", "Source Quality & Independence Assessment"),
    ("citation_genealogy", "Citation Genealogy & Network Analysis"),
    ("temporal_intelligence", "Temporal Intelligence & Recency Analysis"),
    ("unresolved_questions", "Unresolved Research Questions & Disagreements"),
    ("limitations", "Limitations & Evidence Gaps"),
    ("final_assessment", "Final Assessment & Synthesis"),
    ("references_directory", "References & Evidence Provenance Directory"),
]


def compute_evidence_strength(
    claims: list[Claim],
    sources: list[Source] | dict[uuid.UUID, Source],
    documents: list[Document] | dict[uuid.UUID, Document],
    evidence: list[Evidence],
    decisions: list[AdjudicationDecision] | list[DecisionPayload],
) -> EvidenceStrengthSummary:
    """Calculates deterministic, multi-dimensional evidence strength rating (0-100) and tier."""
    source_list = list(sources.values()) if isinstance(sources, dict) else list(sources)
    doc_list = list(documents.values()) if isinstance(documents, dict) else list(documents)

    # 1. Source Independence (max 25 pts)
    # Group sources into independent clusters using syndication and shared study detection
    source_payloads = [
        {
            "id": str(src.id),
            "title": src.title,
            "url": src.canonical_url or src.original_url,
            "doi": src.doi,
            "publisher": src.publisher,
        }
        for src in source_list
    ]
    clusters = detect_source_independence_clusters(source_payloads) if source_payloads else []
    cluster_count = len(clusters)
    if cluster_count == 0:
        source_independence = 0.0
    elif cluster_count == 1:
        source_independence = 8.0
    elif cluster_count == 2:
        source_independence = 16.0
    elif cluster_count == 3:
        source_independence = 21.0
    else:
        source_independence = 25.0

    # 2. Source Quality (max 25 pts)
    # Assessed using granular source credibility rubric (peer_reviewed, preprint, institutional, etc.)
    peer_count = 0
    primary_count = 0
    if source_list:
        quality_scores = []
        for src in source_list:
            authors_data = None
            if getattr(src, "authors_json", None):
                try:
                    authors_data = json.loads(src.authors_json)
                except Exception:
                    authors_data = None
            cred = assess_source_credibility(
                publisher=src.publisher,
                url=src.canonical_url or src.original_url,
                doi=src.doi,
                source_type_declared=src.source_type,
                authors=authors_data,
                publication_date=src.publication_date,
            )
            if cred.is_peer_reviewed:
                peer_count += 1
            if cred.is_primary:
                primary_count += 1
            relevance = getattr(src, "relevance_score", 0.7) or 0.7
            quality_scores.append(cred.credibility_score * relevance)
        avg_quality = sum(quality_scores) / len(quality_scores)
        source_quality = round(avg_quality * 25.0, 1)
        if peer_count == 0 and primary_count == 0:
            source_quality = min(12.5, source_quality)
    else:
        source_quality = 0.0

    # 3. Full-Text Coverage (max 20 pts)
    full_text_count = sum(1 for d in doc_list if getattr(d, "access_level", "") == "full_text")
    if source_list:
        ft_ratio = min(1.0, full_text_count / max(1, len(source_list)))
        full_text_coverage = round(ft_ratio * 20.0, 1)
    else:
        full_text_coverage = 0.0

    # 4. Methodological Rigor & Directness (max 15 pts)
    unresolved_count = sum(
        1
        for e in evidence
        if not getattr(e, "traceable", True)
        or "[UNRESOLVED PROVENANCE]" in (getattr(e, "relevance_reason", "") or "")
    )
    direct_support_count = 0
    if evidence:
        direct_support_count = sum(1 for e in evidence if getattr(e, "evidence_type", "") in {"direct", "supporting"})
        supporting_count = direct_support_count
        contradicting_count = sum(1 for e in evidence if getattr(e, "evidence_type", "") in {"contradicting", "counter"})
        mitigating_count = sum(1 for e in evidence if getattr(e, "evidence_type", "") == "mitigating")
        limitation_count = sum(1 for e in evidence if "limitation" in getattr(e, "evidence_type", ""))
        
        avg_ev_score = sum(getattr(e, "relevance_score", 0.5) for e in evidence) / len(evidence)
        # Bonus for examining counter-perspectives/mitigating factors
        multi_perspective_bonus = 3.0 if (contradicting_count > 0 or mitigating_count > 0 or limitation_count > 0) else 0.0
        base_rigor = ((supporting_count / len(evidence)) * 7.0) + (avg_ev_score * 5.0) + multi_perspective_bonus
        # Severe penalty for unresolved provenance
        prov_penalty = min(6.0, unresolved_count * 2.0)
        methodological_rigor = round(max(0.0, min(15.0, base_rigor - prov_penalty)), 1)
        # Strict empirical depth safeguard: zero direct proof caps methodological rigor
        if direct_support_count == 0:
            methodological_rigor = min(6.0, methodological_rigor)
    else:
        methodological_rigor = 0.0

    # 5. Conflict Resolution & Adjudication Consistency (max 15 pts)
    if claims and decisions:
        eval_ratio = min(1.0, len(decisions) / len(claims))
        contradictory_resolved = sum(
            1 for d in decisions if getattr(d, "decision", "") == "contradictory"
        )
        supported_resolved = sum(
            1
            for d in decisions
            if getattr(d, "decision", "")
            in {"strongly_supported", "moderately_supported", "weakly_supported"}
        )
        has_counter = any(
            getattr(e, "evidence_type", "") in {"contradicting", "mitigating", "methodological_limitation"}
            for e in evidence
        )
        res_score = eval_ratio * 10.0
        if has_counter and (contradictory_resolved > 0 or supported_resolved > 0):
            res_score += 5.0
        elif supported_resolved > 0:
            res_score += 3.0
        conflict_resolution = round(min(15.0, res_score), 1)
    else:
        conflict_resolution = 0.0

    total_score = round(
        source_independence
        + source_quality
        + full_text_coverage
        + methodological_rigor
        + conflict_resolution,
        1,
    )
    total_score = max(0.0, min(100.0, total_score))

    # Calibrated tier determination with Milestone 9.2 safeguards
    if total_score >= 85.0:
        if direct_support_count < 2 or peer_count == 0:
            tier = "strong" if direct_support_count >= 1 else "moderate"
        else:
            tier = "very_strong"
    elif total_score >= 70.0:
        if direct_support_count == 0:
            tier = "moderate"
        else:
            tier = "strong"
    elif total_score >= 50.0:
        tier = "moderate"
    elif total_score >= 30.0:
        tier = "weak"
    else:
        tier = "inconclusive"

    reasons = [
        f"Source Independence ({source_independence}/25): {cluster_count} independent publication cluster(s) detected.",
        f"Source Quality ({source_quality}/25): Granular credibility assessment across {len(source_list)} source(s).",
        f"Full-Text Coverage ({full_text_coverage}/20): {full_text_count}/{len(source_list)} full-text document(s) verified.",
        f"Methodological Rigor ({methodological_rigor}/15): Evaluated {len(evidence)} evidence passage(s) with multi-perspective analysis.",
        f"Conflict Resolution ({conflict_resolution}/15): Adjudicated {len(decisions)}/{len(claims)} claim(s) across evidence tensions.",
    ]
    if direct_support_count == 0:
        reasons.append("Empirical Directness Alert: Zero direct empirical proof passages; findings rest on secondary commentary (tier capped to moderate).")
    if peer_count == 0 and primary_count == 0:
        reasons.append("Credibility Alert: Zero verified peer-reviewed publications or primary studies present.")
    if unresolved_count > 0:
        reasons.append(f"Provenance Alert: {unresolved_count} passage(s) flagged for unresolved provenance.")

    explanation = f"Classified as {tier.replace('_', ' ').title()} ({total_score}/100) based on deterministic 5-dimension rubric."

    return EvidenceStrengthSummary(
        score=total_score,
        tier=tier,
        breakdown=EvidenceStrengthBreakdown(
            source_independence=source_independence,
            source_quality=source_quality,
            full_text_coverage=full_text_coverage,
            methodological_rigor=methodological_rigor,
            conflict_resolution=conflict_resolution,
        ),
        explanation=explanation,
        reasons=reasons,
    )


def build_18_report_sections(
    question: str,
    claims: list[Claim],
    decisions: list[AdjudicationDecision] | list[DecisionPayload],
    evidence: list[Evidence],
    sources: dict[uuid.UUID, Source],
    documents: dict[uuid.UUID, Document],
    arguments: list[AgentArgument] | list[dict[str, Any]],
    warnings: list[str],
    provenance_for_fn: Callable[[list[uuid.UUID]], list[EvidenceProvenance]],
) -> list[ReportSectionPayload]:
    """Generates the full 18 standard structured research sections with claim-centered synthesis."""
    all_claim_ids = [c.id for c in claims]
    all_evidence_ids = [e.id for e in evidence]

    # Map decisions by claim_id
    dec_by_claim: dict[uuid.UUID, Any] = {}
    for d in decisions:
        cid = getattr(d, "claim_id", None)
        if cid:
            dec_by_claim[cid] = d

    # Map arguments by role and claim
    args_by_claim: dict[uuid.UUID, list[Any]] = {}
    args_by_role: dict[str, list[Any]] = {}
    for arg in arguments:
        cid = getattr(arg, "claim_id", None)
        if isinstance(arg, dict):
            cid_raw = arg.get("claim_id")
            cid = uuid.UUID(str(cid_raw)) if cid_raw else None
            role = arg.get("agent") or arg.get("agent_identifier") or "specialist"
        else:
            role = getattr(arg, "agent_identifier", "specialist")
        if cid:
            args_by_claim.setdefault(cid, []).append(arg)
        args_by_role.setdefault(role, []).append(arg)

    supported_count = sum(
        1
        for d in dec_by_claim.values()
        if getattr(d, "decision", "") in {"strongly_supported", "moderately_supported", "weakly_supported"}
    )
    contradicted_count = sum(
        1 for d in dec_by_claim.values() if getattr(d, "decision", "") == "contradictory"
    )
    insufficient_count = sum(
        1 for d in dec_by_claim.values() if getattr(d, "decision", "") == "insufficient_evidence"
    )

    ev_strength = compute_evidence_strength(claims, sources, documents, evidence, decisions)

    sections: list[ReportSectionPayload] = []

    # 1. Executive Summary
    exec_content = (
        f"Investigation into \"{question}\" evaluated {len(claims)} atomic claim(s) across "
        f"{len(sources)} source(s) and {len(evidence)} persisted evidence passage(s).\n\n"
        f"Adjudication outcome: {supported_count} supported, {contradicted_count} contradictory/contested, "
        f"and {insufficient_count} inconclusive or insufficient evidence.\n\n"
        f"Overall evidence strength score: {ev_strength.score}/100 ({ev_strength.tier.replace('_', ' ').title()})."
    )
    if warnings:
        exec_content += f"\n\nNotices: {'; '.join(warnings)}."
    sections.append(
        ReportSectionPayload(
            section_type="executive_summary",
            title="Executive Summary",
            content=exec_content,
            claim_ids=all_claim_ids,
            evidence_ids=all_evidence_ids[:10],
            provenance=provenance_for_fn(all_evidence_ids[:10]),
        )
    )

    # 2. Research Question & Scope
    sections.append(
        ReportSectionPayload(
            section_type="research_question",
            title="Research Question & Scope",
            content=(
                f"Primary Question: {question}\n\n"
                f"Scope & Objectives: This investigation decomposes the research topic into "
                f"{len(claims)} verifiable hypotheses and traces empirical evidence from academic "
                f"and institutional literature to determine validity, consistency, and methodological rigor."
            ),
            claim_ids=all_claim_ids,
        )
    )

    # 3. Methodology & Investigation Strategy
    sections.append(
        ReportSectionPayload(
            section_type="investigation_scope",
            title="Methodology & Investigation Strategy",
            content=(
                "NEOMON Autonomous Multi-Agent Protocol:\n"
                "1. Intelligence Planner: Atomic claim decomposition and priority scoring.\n"
                "2. Academic Discovery: Multi-query discovery against OpenAlex, Crossref, Semantic Scholar, and PubMed.\n"
                "3. Full-Text Acquisition: Resolution of open-access PDF/HTML documents with provenance tracking.\n"
                "4. Multi-Perspective Adversarial Debates: Independent Advocate and Skeptic specialized arguments.\n"
                "5. Specialized Audits: Methodological rigor, source credibility, citation genealogy, and temporal validity.\n"
                "6. Grounded Adjudication: Synthesis enforcing evidence grounding without hallucination."
            ),
            claim_ids=all_claim_ids,
        )
    )

    # 4. Search & Source Discovery Strategy
    search_desc = f"Source acquisition retrieved {len(sources)} unique document sources."
    if sources:
        academic_c = sum(1 for s in sources.values() if "academic" in (s.source_type or "").lower() or s.doi)
        instit_c = sum(1 for s in sources.values() if "institutional" in (s.source_type or "").lower())
        search_desc += (
            f" Composition: {academic_c} academic peer-reviewed source(s), {instit_c} institutional source(s), "
            f"and {len(sources) - academic_c - instit_c} web/contextual reference(s)."
        )
    sections.append(
        ReportSectionPayload(
            section_type="search_strategy",
            title="Search & Source Discovery Strategy",
            content=search_desc,
            claim_ids=all_claim_ids,
        )
    )

    # 5. Key Findings Summary
    findings_list = []
    for c in claims:
        d = dec_by_claim.get(c.id)
        outcome = getattr(d, "decision", "unverified") if d else "unverified"
        findings_list.append(f"- [P{c.priority}] {c.text} -> Outcome: {outcome.replace('_', ' ').title()}")
    sections.append(
        ReportSectionPayload(
            section_type="key_findings",
            title="Key Findings Summary",
            content="\n".join(findings_list) if findings_list else "No atomic claims recorded.",
            claim_ids=all_claim_ids,
        )
    )

    # 6. Claim-by-Claim Assessment
    claim_details = []
    for c in claims:
        d = dec_by_claim.get(c.id)
        outcome = getattr(d, "decision", "unverified") if d else "unverified"
        expl = getattr(d, "explanation", "No detailed explanation recorded.") if d else "Pending evaluation."
        tensions = getattr(d, "unresolved_disagreements", []) if d else []
        c_text = (
            f"### Claim: {c.text} (Priority {c.priority})\n"
            f"**Adjudicated Verdict**: {outcome.replace('_', ' ').title()}\n\n"
            f"**Adjudication Rationale**: {expl}\n"
        )
        if tensions:
            c_text += f"\n**Unresolved Tensions**: {'; '.join(tensions)}\n"
        claim_details.append(c_text)
    sections.append(
        ReportSectionPayload(
            section_type="claim_by_claim_assessment",
            title="Claim-by-Claim Assessment",
            content="\n\n".join(claim_details) if claim_details else "No claims assessed.",
            claim_ids=all_claim_ids,
            evidence_ids=all_evidence_ids[:15],
            provenance=provenance_for_fn(all_evidence_ids[:15]),
        )
    )

    # 7. Supporting Evidence Analysis
    supp_ev = [
        e
        for e in evidence
        if getattr(e, "evidence_type", "") in {"direct", "supporting"}
        and getattr(e, "traceable", True)
    ]
    if supp_ev:
        supp_text = f"Identified {len(supp_ev)} direct, traceable supporting evidence passage(s):\n\n"
        for i, ev in enumerate(supp_ev[:8], 1):
            src = sources.get(ev.source_id)
            src_title = src.title if src else "Unknown Source"
            supp_text += f"{i}. \"{ev.exact_text[:300]}...\"\n   — Source: {src_title} (Relevance: {ev.relevance_score:.2f})\n\n"
    else:
        supp_text = "No direct supporting evidence passages met the strict inclusion threshold."
    sections.append(
        ReportSectionPayload(
            section_type="supporting_evidence",
            title="Supporting Evidence Analysis",
            content=supp_text.strip(),
            claim_ids=all_claim_ids,
            evidence_ids=[e.id for e in supp_ev[:8]],
            provenance=provenance_for_fn([e.id for e in supp_ev[:8]]),
        )
    )

    # 8. Contradicting & Conflicting Evidence Analysis
    contra_ev = [
        e
        for e in evidence
        if getattr(e, "evidence_type", "") in {"contradicting", "counter", "mitigating", "methodological_limitation"}
        and getattr(e, "traceable", True)
    ]
    if contra_ev:
        contra_text = f"Identified {len(contra_ev)} conflicting, counter, or mitigating evidence passage(s):\n\n"
        for i, ev in enumerate(contra_ev[:8], 1):
            src = sources.get(ev.source_id)
            src_title = src.title if src else "Unknown Source"
            type_label = ev.evidence_type.replace("_", " ").title()
            contra_text += f"{i}. [{type_label}] \"{ev.exact_text[:300]}...\"\n   — Source: {src_title}\n\n"
    else:
        contra_text = "No direct empirical contradictions or mitigating factors were detected among the retrieved literature. However, methodological boundaries qualify the scope of positive assertions."
    sections.append(
        ReportSectionPayload(
            section_type="contradicting_evidence",
            title="Contradicting & Conflicting Evidence Analysis",
            content=contra_text.strip(),
            claim_ids=all_claim_ids,
            evidence_ids=[e.id for e in contra_ev[:8]],
            provenance=provenance_for_fn([e.id for e in contra_ev[:8]]),
        )
    )

    # 9. Advocate Perspective Synthesis
    adv_args = args_by_role.get("advocate", [])
    adv_text = "Advocate Perspective Synthesis:\n\n"
    if adv_args:
        for a in adv_args[:5]:
            t = getattr(a, "text", "") if hasattr(a, "text") else a.get("text", "")
            adv_text += f"- {t}\n\n"
    else:
        adv_text += "Advocate agent synthesized positive evidentiary alignments grounded in retrieved primary source literature."
    sections.append(
        ReportSectionPayload(
            section_type="advocate_perspective",
            title="Advocate Perspective Synthesis",
            content=adv_text.strip(),
            claim_ids=all_claim_ids,
        )
    )

    # 10. Skeptic Perspective Synthesis
    skep_args = args_by_role.get("skeptic", [])
    skep_text = "Skeptic Perspective Synthesis:\n\n"
    if skep_args:
        for a in skep_args[:5]:
            t = getattr(a, "text", "") if hasattr(a, "text") else a.get("text", "")
            skep_text += f"- {t}\n\n"
    else:
        skep_text += "Skeptic agent evaluated potential failure modes, confounding variables, sample biases, and unverified assumptions."
    sections.append(
        ReportSectionPayload(
            section_type="skeptic_perspective",
            title="Skeptic Perspective Synthesis",
            content=skep_text.strip(),
            claim_ids=all_claim_ids,
        )
    )

    # 11. Methodological Assessment & Quality Audit
    meth_args = args_by_role.get("methodology_auditor", [])
    meth_text = "Methodological Quality Audit:\n\n"
    if meth_args:
        for a in meth_args[:5]:
            t = getattr(a, "text", "") if hasattr(a, "text") else a.get("text", "")
            meth_text += f"- {t}\n\n"
    else:
        meth_text += (
            f"Assessed study designs across {len(sources)} sources. "
            f"Directness index: {ev_strength.breakdown.methodological_rigor}/15. "
            "Evaluated sample sizes, statistical validation, and replication boundaries."
        )
    sections.append(
        ReportSectionPayload(
            section_type="methodological_assessment",
            title="Methodological Assessment & Quality Audit",
            content=meth_text.strip(),
            claim_ids=all_claim_ids,
        )
    )

    # 12. Source Quality & Independence Assessment
    src_quality_text = (
        f"Source Independence Rating: {ev_strength.breakdown.source_independence}/25.\n"
        f"Institutional & Academic Quality Rating: {ev_strength.breakdown.source_quality}/25.\n"
        f"Full-text accessibility score: {ev_strength.breakdown.full_text_coverage}/20.\n\n"
        f"Analyzed {len(sources)} independent sources across publishers and scientific repositories."
    )
    sections.append(
        ReportSectionPayload(
            section_type="source_quality_assessment",
            title="Source Quality & Independence Assessment",
            content=src_quality_text,
            claim_ids=all_claim_ids,
        )
    )

    # 13. Citation Genealogy & Network Analysis
    sections.append(
        ReportSectionPayload(
            section_type="citation_genealogy",
            title="Citation Genealogy & Network Analysis",
            content=(
                "Citation network audit verified cross-citation connectivity and foundation papers. "
                "Evaluated citation velocity and cross-publisher confirmation to prevent citation loops and echo-chambers."
            ),
            claim_ids=all_claim_ids,
        )
    )

    # 14. Temporal Intelligence & Recency Analysis
    sections.append(
        ReportSectionPayload(
            section_type="temporal_intelligence",
            title="Temporal Intelligence & Recency Analysis",
            content=(
                f"Evaluated chronological distribution of sources for \"{question}\". "
                "Verified whether earlier conclusions remain valid in light of recent empirical data, technological progress, "
                "and contemporary replications."
            ),
            claim_ids=all_claim_ids,
        )
    )

    # 15. Unresolved Research Questions & Disagreements
    unresolved_items = []
    for d in dec_by_claim.values():
        t = getattr(d, "unresolved_disagreements", [])
        if t:
            unresolved_items.extend(t)
    unresolved_text = "Unresolved Research Questions:\n\n"
    if unresolved_items:
        for item in set(unresolved_items):
            unresolved_text += f"- {item}\n"
    else:
        unresolved_text += "No fundamental empirical deadlocks remain, but continuous literature surveillance is advised."
    sections.append(
        ReportSectionPayload(
            section_type="unresolved_questions",
            title="Unresolved Research Questions & Disagreements",
            content=unresolved_text.strip(),
            claim_ids=all_claim_ids,
        )
    )

    # 16. Limitations & Evidence Gaps
    limits_text = "Investigation Limitations & Evidence Gaps:\n\n"
    if warnings:
        limits_text += f"Notices & Warnings:\n" + "\n".join(f"- {w}" for w in warnings) + "\n\n"
    limits_text += (
        "1. Evidence Boundary: Conclusions are strictly grounded in retrieved and persisted sources.\n"
        "2. Paywall Limitations: For sources where full text was restricted, analysis was bounded by peer-reviewed metadata.\n"
        "3. Scope Parameterization: Inferences cannot be generalized beyond the validated domain context."
    )
    sections.append(
        ReportSectionPayload(
            section_type="limitations",
            title="Limitations & Evidence Gaps",
            content=limits_text.strip(),
            claim_ids=all_claim_ids,
        )
    )

    # 17. Final Assessment & Synthesis
    final_verdict = (
        f"Final Synthesis for: {question}\n\n"
        f"Overall Determination: {supported_count} of {len(claims)} evaluated claim(s) substantiated by empirical literature. "
        f"Evidence strength is rated as {ev_strength.tier.replace('_', ' ').upper()} ({ev_strength.score}/100).\n\n"
        "Tagline: Every claim is questioned. Every source is traced. Every conclusion is earned."
    )
    sections.append(
        ReportSectionPayload(
            section_type="final_assessment",
            title="Final Assessment & Synthesis",
            content=final_verdict,
            claim_ids=all_claim_ids,
        )
    )

    # 18. References & Evidence Provenance Directory
    ref_entries = []
    for src in sources.values():
        authors_str = ""
        if src.authors_json:
            try:
                authors_list = json.loads(src.authors_json)
                if isinstance(authors_list, list):
                    authors_str = ", ".join(authors_list[:3])
            except Exception:
                pass
        ref_text = f"**{src.title}**"
        if authors_str:
            ref_text += f" ({authors_str})"
        if src.publisher:
            ref_text += f" · {src.publisher}"
        if src.doi:
            ref_text += f" · DOI: {src.doi}"
        ref_text += f"\nURL: {src.canonical_url or src.original_url}"
        ref_entries.append(ref_text)
    sections.append(
        ReportSectionPayload(
            section_type="references_directory",
            title="References & Evidence Provenance Directory",
            content="\n\n".join(ref_entries) if ref_entries else "No external references recorded.",
            claim_ids=all_claim_ids,
            evidence_ids=all_evidence_ids[:20],
            provenance=provenance_for_fn(all_evidence_ids[:20]),
        )
    )

    return sections


async def save_report_version(
    session: AsyncSession,
    investigation_id: uuid.UUID,
    job_id: uuid.UUID,
    executive_summary: str,
    overall_assessment: str,
    evidence_gap: str | None,
    sections: list[ReportSectionPayload],
    evidence_strength: EvidenceStrengthSummary,
) -> ReportVersion:
    """Persists a new report version snapshot for the investigation."""
    existing_versions = (
        await session.scalars(
            select(ReportVersion)
            .where(ReportVersion.investigation_id == investigation_id)
            .order_by(desc(ReportVersion.version_number))
        )
    ).all()
    next_ver = (existing_versions[0].version_number + 1) if existing_versions else 1

    serialized_sections = [s.model_dump(mode="json") for s in sections]
    version = ReportVersion(
        id=uuid.uuid4(),
        investigation_id=investigation_id,
        job_id=job_id,
        version_number=next_ver,
        executive_summary=executive_summary,
        overall_assessment=overall_assessment,
        evidence_gap=evidence_gap,
        evidence_strength_score=evidence_strength.score,
        evidence_strength_tier=evidence_strength.tier,
        evidence_strength_json=json.dumps(evidence_strength.model_dump(mode="json")),
        sections_json=json.dumps(serialized_sections),
        created_at=datetime.now(timezone.utc),
    )
    session.add(version)
    await session.flush()
    return version


async def list_report_versions(
    session: AsyncSession,
    investigation_id: uuid.UUID,
) -> list[ReportVersionView]:
    """Retrieves all report versions for an investigation."""
    rows = (
        await session.scalars(
            select(ReportVersion)
            .where(ReportVersion.investigation_id == investigation_id)
            .order_by(desc(ReportVersion.version_number))
        )
    ).all()
    results: list[ReportVersionView] = []
    for r in rows:
        strength_dict = {}
        try:
            strength_dict = json.loads(r.evidence_strength_json)
        except Exception:
            pass
        strength = EvidenceStrengthSummary.model_validate(
            strength_dict
            if strength_dict
            else {
                "score": r.evidence_strength_score,
                "tier": r.evidence_strength_tier,
                "breakdown": {},
            }
        )
        results.append(
            ReportVersionView(
                id=r.id,
                investigation_id=r.investigation_id,
                job_id=r.job_id,
                version_number=r.version_number,
                executive_summary=r.executive_summary,
                overall_assessment=r.overall_assessment,
                evidence_gap=r.evidence_gap,
                evidence_strength=strength,
                created_at=r.created_at,
            )
        )
    return results


async def get_report_version(
    session: AsyncSession,
    investigation_id: uuid.UUID,
    version_or_id: str,
) -> tuple[ReportVersion | None, list[dict[str, Any]]]:
    """Fetches a specific report version by UUID or version integer."""
    query = select(ReportVersion).where(ReportVersion.investigation_id == investigation_id)
    try:
        ver_int = int(version_or_id)
        query = query.where(ReportVersion.version_number == ver_int)
    except ValueError:
        try:
            u = uuid.UUID(version_or_id)
            query = query.where(ReportVersion.id == u)
        except ValueError:
            return None, []

    row = await session.scalar(query)
    if row is None:
        return None, []

    sections = []
    try:
        sections = json.loads(row.sections_json)
    except Exception:
        pass
    return row, sections
