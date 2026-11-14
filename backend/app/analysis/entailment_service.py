"""Evidence-to-Claim Entailment Validation Service (Milestone 8G.3).

Evaluates every evidence passage against specific claims with rigorous scientific criteria:
1. Distinguishes topical relevance from entailment (mentioning keywords != proving claim).
2. Distinguishes contextual background from direct causal support.
3. Distinguishes correlation from causation (flags associative co-occurrence).
4. Explicitly articulates missing inferential steps.
"""

from dataclasses import dataclass, field
from enum import StrEnum
import json
import re
from typing import Any


class EntailmentClassification(StrEnum):
    DIRECT_SUPPORT = "direct_support"
    PARTIAL_SUPPORT = "partial_support"
    CONTEXTUAL_SUPPORT = "contextual_support"
    DIRECT_CONTRADICTION = "direct_contradiction"
    MITIGATING = "mitigating"
    METHODOLOGICAL_LIMITATION = "methodological_limitation"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    UNVERIFIED_RELATIONSHIP = "unverified_relationship"


@dataclass
class EntailmentValidationResult:
    claim_id: str
    evidence_id: str
    entailment_classification: EntailmentClassification
    entailment_strength: float
    explanation: str
    missing_inferential_steps: list[str] = field(default_factory=list)
    correlation_vs_causation_flag: bool = False
    validation_method: str = "deterministic_heuristic"
    validator_model: str | None = None
    status: str = "validated"


# Causal mechanism phrases indicating direct causal assertion
_CAUSAL_PHRASES = {
    "causes", "caused", "caused by", "leads to", "led to", "leading to", "results in", "resulted in", "resulting in",
    "drives", "drove", "driven by", "produces", "produced", "triggering", "triggers", "triggered", "directly responsible",
    "attributable to", "because of", "explains why", "demonstrates that", "proves that"
}

# Correlational / Associative phrases without proven mechanism
_CORRELATIONAL_PHRASES = {
    "associated with", "correlated with", "alongside", "coincides with", "during the same period",
    "concomitant with", "parallel to", "tracked with", "linked to", "co-occurred",
    "in tandem with", "at the same time as"
}

# Contradiction / Refutation phrases
_CONTRADICTION_PHRASES = {
    "refutes", "disproves", "contradicts", "fails to support", "no evidence that",
    "contrary to", "does not cause", "did not result in", "inconsistent with",
    "rebuts", "challenges the assumption", "debunks"
}

# Limitation / Qualification phrases
_LIMITATION_PHRASES = {
    "small sample size", "limited sample", "simulation only", "in vitro", "preliminary finding",
    "selection bias", "confounding variable", "uncontrolled study", "caveat", "cannot be generalized",
    "boundary condition", "under specific conditions only", "retrospective analysis"
}

_MITIGATING_PHRASES = {
    "partially mitigated", "mitigated by", "offset by", "compensated for", "adaptive response",
    "secondary adjustment", "cushioned by", "temporary effect", "dampened"
}

# Study intent / thesis statement phrases that describe objectives or framing rather than results
_STUDY_INTENT_PHRASES = {
    "aims to", "aimed to", "aim of this study", "aim of this paper", "purpose of this study",
    "purpose of this paper", "purpose of this thesis", "objective was to", "objective is to",
    "this paper explores", "this thesis explores", "this study examines", "this paper examines",
    "we investigate whether", "we investigate the", "we explore the", "we examine the",
    "sought to analyze", "sought to investigate", "hypothesized that", "focuses on whether",
    "intended to assess", "this chapter describes", "this thesis investigates",
}

# Empirical findings phrases that denote proven results, data, or verified findings
_FINDINGS_PHRASES = {
    "found that", "demonstrates that", "showed that", "results show", "results indicate",
    "empirical data reveals", "empirical data shows", "data reveals", "data shows",
    "statistically significant", "statistically demonstrated", "empirically confirmed",
    "observed a significant", "concluded that", "measurements confirmed", "measurements show",
    "empirical measurements show", "experimental results show", "findings demonstrate", "analysis confirms",
}


# Synonym mapping for domain concepts
_DOMAIN_SYNONYMS = {
    "ram": "memory",
    "dram": "memory",
    "hbm": "memory",
    "gpu": "accelerator",
    "gpus": "accelerators",
}


def _clean_tokens(text: str) -> set[str]:
    clean = re.sub(r"[^\w\s]", " ", (text or "").lower())
    stop = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for", "with", "by", "of"}
    tokens = set()
    for t in clean.split():
        if len(t) >= 2 and t not in stop:
            mapped = _DOMAIN_SYNONYMS.get(t, t)
            tokens.add(mapped)
            tokens.add(t)
    return tokens


def validate_evidence_claim_entailment_heuristic(
    claim_id: str,
    claim_text: str,
    evidence_id: str,
    evidence_text: str,
    surrounding_context: str | None = None,
) -> EntailmentValidationResult:
    """Rigorous deterministic heuristic evaluation of entailment."""
    c_clean = (claim_text or "").strip().lower()
    e_clean = (evidence_text or "").strip().lower()
    ctx_clean = (surrounding_context or "").strip().lower()
    full_text = f"{e_clean} {ctx_clean}"

    # Check 1: Insufficient / Empty text
    if len(e_clean) < 15 or len(full_text.split()) < 4:
        return EntailmentValidationResult(
            claim_id=claim_id,
            evidence_id=evidence_id,
            entailment_classification=EntailmentClassification.INSUFFICIENT_EVIDENCE,
            entailment_strength=0.1,
            explanation="Evidence passage is too brief or insubstantial to assess inferential entailment.",
            missing_inferential_steps=["Requires substantive empirical data or complete narrative context."],
            correlation_vs_causation_flag=False,
            validation_method="deterministic_heuristic",
        )

    # Check 2: Direct Contradiction
    has_contradiction = any(cp in full_text for cp in _CONTRADICTION_PHRASES)
    if has_contradiction:
        return EntailmentValidationResult(
            claim_id=claim_id,
            evidence_id=evidence_id,
            entailment_classification=EntailmentClassification.DIRECT_CONTRADICTION,
            entailment_strength=0.85,
            explanation="Evidence passage explicitly contains refutational or contradictory findings directly challenging the claim.",
            missing_inferential_steps=[],
            correlation_vs_causation_flag=False,
            validation_method="deterministic_heuristic",
        )

    # Check 3: Methodological Limitation
    has_limitation = any(lp in full_text for lp in _LIMITATION_PHRASES)
    if has_limitation:
        return EntailmentValidationResult(
            claim_id=claim_id,
            evidence_id=evidence_id,
            entailment_classification=EntailmentClassification.METHODOLOGICAL_LIMITATION,
            entailment_strength=0.75,
            explanation="Evidence documents specific methodological constraints, sample limitations, or confounding factors affecting validity.",
            missing_inferential_steps=["Findings cannot be generalized without addressing stated methodological boundary conditions."],
            correlation_vs_causation_flag=False,
            validation_method="deterministic_heuristic",
        )

    # Check 4: Mitigating Factors
    has_mitigating = any(mp in full_text for mp in _MITIGATING_PHRASES)
    if has_mitigating:
        return EntailmentValidationResult(
            claim_id=claim_id,
            evidence_id=evidence_id,
            entailment_classification=EntailmentClassification.MITIGATING,
            entailment_strength=0.70,
            explanation="Evidence identifies offsetting factors, adaptive adjustments, or stabilizing mechanisms that moderate the claim's effect.",
            missing_inferential_steps=["Must account for compensatory industry or market mechanisms."],
            correlation_vs_causation_flag=False,
            validation_method="deterministic_heuristic",
        )

    # Check 5: Token overlap and topicality
    c_tokens = _clean_tokens(c_clean)
    e_tokens = _clean_tokens(full_text)
    overlap = c_tokens & e_tokens
    overlap_ratio = len(overlap) / max(1, len(c_tokens))

    # Check for causal vs correlational language
    has_causal = any(cp in full_text for cp in _CAUSAL_PHRASES)
    has_correlational = any(corr in full_text for corr in _CORRELATIONAL_PHRASES)

    # If evidence has virtually no conceptual overlap with claim
    if overlap_ratio < 0.15 and len(overlap) < 2:
        return EntailmentValidationResult(
            claim_id=claim_id,
            evidence_id=evidence_id,
            entailment_classification=EntailmentClassification.INSUFFICIENT_EVIDENCE,
            entailment_strength=0.2,
            explanation=f"Minimal lexical and semantic alignment with claim proposition (overlap ratio: {overlap_ratio:.1%}).",
            missing_inferential_steps=["Evidence does not address the core entities or concepts articulated in the claim."],
            correlation_vs_causation_flag=False,
            validation_method="deterministic_heuristic",
        )

    # Correlation vs Causation Flagging (Benchmark B problem)
    is_claim_causal = any(cp in c_clean for cp in ("cause", "contribute", "lead to", "effect", "impact", "role", "affect", "result in", "shortage"))
    
    if is_claim_causal and has_correlational and not has_causal:
        return EntailmentValidationResult(
            claim_id=claim_id,
            evidence_id=evidence_id,
            entailment_classification=EntailmentClassification.CONTEXTUAL_SUPPORT,
            entailment_strength=0.55,
            explanation="Evidence observes statistical association or concurrent timeline but does not prove direct causal mechanism.",
            missing_inferential_steps=[
                "Evidence demonstrates correlational co-occurrence rather than counterfactual or mechanistic causality.",
                "Requires proof that observed effect would not have occurred absent the claimed causal driver."
            ],
            correlation_vs_causation_flag=True,
            validation_method="deterministic_heuristic",
        )

    # Study Intent vs Findings Flagging (Milestone 9.2: study objectives must not count as direct proof)
    has_study_intent = any(sip in full_text for sip in _STUDY_INTENT_PHRASES)
    has_findings = any(fp in full_text for fp in _FINDINGS_PHRASES)

    if has_study_intent and not has_findings:
        return EntailmentValidationResult(
            claim_id=claim_id,
            evidence_id=evidence_id,
            entailment_classification=EntailmentClassification.CONTEXTUAL_SUPPORT,
            entailment_strength=0.45,
            explanation="Passage articulates study intent, hypothesis, or research framing; does not constitute empirical proof of the conclusion.",
            missing_inferential_steps=[
                "Passage describes the study's stated objective or thesis statement rather than verified findings or empirical data."
            ],
            correlation_vs_causation_flag=False,
            validation_method="deterministic_heuristic",
        )

    # Contextual vs Direct Support (Benchmark A & B problem)
    # Direct support requires demonstrable causal mechanism OR explicit empirical findings and high overlap
    if (has_causal or has_findings) and overlap_ratio >= 0.45:
        return EntailmentValidationResult(
            claim_id=claim_id,
            evidence_id=evidence_id,
            entailment_classification=EntailmentClassification.DIRECT_SUPPORT,
            entailment_strength=0.88,
            explanation="Evidence articulates direct empirical support and demonstrable mechanism directly substantiating the claim.",
            missing_inferential_steps=[],
            correlation_vs_causation_flag=False,
            validation_method="deterministic_heuristic",
        )

    # Partial Support: establishes partial mechanism or sub-claim with moderate overlap
    if (has_causal or has_findings) and overlap_ratio >= 0.28:
        return EntailmentValidationResult(
            claim_id=claim_id,
            evidence_id=evidence_id,
            entailment_classification=EntailmentClassification.PARTIAL_SUPPORT,
            entailment_strength=0.72,
            explanation="Evidence establishes partial empirical support or an intermediate step, but does not fully entail the complete causal assertion.",
            missing_inferential_steps=[
                "Substantiates an intermediate step or entity relation; full causal conclusion requires supplementary empirical confirmation."
            ],
            correlation_vs_causation_flag=False,
            validation_method="deterministic_heuristic",
        )

    # Topical Contextual Support
    missing_steps = []
    if is_claim_causal:
        missing_steps.append("Passage establishes contextual relevance or background entity involvement, but stops short of proving causal impact.")
    else:
        missing_steps.append("Corroborates descriptive aspects of the claim without independent empirical confirmation.")

    return EntailmentValidationResult(
        claim_id=claim_id,
        evidence_id=evidence_id,
        entailment_classification=EntailmentClassification.CONTEXTUAL_SUPPORT,
        entailment_strength=0.60,
        explanation="Evidence provides contextual background or descriptive topic relevance, but does not definitively entail the specific claim proposition.",
        missing_inferential_steps=missing_steps,
        correlation_vs_causation_flag=False,
        validation_method="deterministic_heuristic",
    )


async def validate_evidence_claim_entailment(
    claim_id: str,
    claim_text: str,
    evidence_id: str,
    evidence_text: str,
    surrounding_context: str | None = None,
    llm_service: Any = None,
) -> EntailmentValidationResult:
    """Validate entailment using deterministic analysis with optional LLM enhancement."""
    heuristic_res = validate_evidence_claim_entailment_heuristic(
        claim_id=claim_id,
        claim_text=claim_text,
        evidence_id=evidence_id,
        evidence_text=evidence_text,
        surrounding_context=surrounding_context,
    )

    if not llm_service:
        return heuristic_res

    # If LLM service provided, attempt structured validation
    prompt = f"""You are a scientific peer reviewer evaluating logical entailment between an evidence passage and a research claim.

Claim: "{claim_text}"
Evidence Passage: "{evidence_text}"
Surrounding Context: "{surrounding_context or 'None'}"

Evaluate:
1. Does the evidence DIRECTLY support, merely provide CONTEXTUAL background, DIRECTLY CONTRADICT, MITIGATE, note a METHODOLOGICAL LIMITATION, or represent INSUFFICIENT evidence?
2. Is there a correlation-vs-causation error (co-occurrence mistaken for causal proof)?
3. What specific inferential steps are missing between the evidence and the claim?

Respond with JSON adhering to:
{{
  "classification": "direct_support" | "contextual_support" | "direct_contradiction" | "mitigating" | "methodological_limitation" | "insufficient_evidence",
  "entailment_strength": 0.0 to 1.0,
  "correlation_vs_causation_flag": true | false,
  "explanation": "concise explanation",
  "missing_inferential_steps": ["step 1", "step 2"]
}}
"""
    try:
        raw_res = await llm_service.generate_json(prompt)
        if isinstance(raw_res, dict) and "classification" in raw_res:
            classification_str = raw_res.get("classification", heuristic_res.entailment_classification.value)
            try:
                c_enum = EntailmentClassification(classification_str)
            except ValueError:
                c_enum = heuristic_res.entailment_classification

            return EntailmentValidationResult(
                claim_id=claim_id,
                evidence_id=evidence_id,
                entailment_classification=c_enum,
                entailment_strength=float(raw_res.get("entailment_strength", heuristic_res.entailment_strength)),
                explanation=raw_res.get("explanation", heuristic_res.explanation),
                missing_inferential_steps=raw_res.get("missing_inferential_steps", heuristic_res.missing_inferential_steps),
                correlation_vs_causation_flag=bool(raw_res.get("correlation_vs_causation_flag", heuristic_res.correlation_vs_causation_flag)),
                validation_method="structured_llm",
                validator_model=getattr(llm_service, "model_name", "llm"),
                status="validated",
            )
    except Exception:
        pass

    return heuristic_res
