"""Unit tests for Core Product Simplification, Scientific Reliability & OpenVINO Context Optimization."""

import uuid
import pytest
from app.analysis.context_manager import (
    AGENT_BUDGETS,
    DEFAULT_BUDGET,
    estimate_tokens,
    compact_evidence_text,
    validate_and_enforce_context_bounds,
    get_cached_relevance,
    set_cached_relevance,
)
from app.analysis.entailment_service import (
    EntailmentClassification,
    validate_evidence_claim_entailment_heuristic,
)
from app.analysis.quality_calibration_service import (
    calculate_calibrated_quality,
)
from app.analysis.protocol import (
    ArgumentPayload,
    ArgumentType,
    ConfidenceAssessment,
    DebatePayload,
)


def test_context_budgets_calibrated_targets():
    """Verify calibrated token budgets for Intel Arc GPU."""
    assert AGENT_BUDGETS["intelligence_planner"].target_prompt_tokens == 2048
    assert AGENT_BUDGETS["intelligence_planner"].max_completion_tokens == 1024

    assert AGENT_BUDGETS["advocate"].target_prompt_tokens == 3072
    assert AGENT_BUDGETS["advocate"].max_completion_tokens == 1536

    assert AGENT_BUDGETS["skeptic"].target_prompt_tokens == 3072
    assert AGENT_BUDGETS["skeptic"].max_completion_tokens == 1536

    assert AGENT_BUDGETS["conflict_adjudicator"].target_prompt_tokens == 2560
    assert AGENT_BUDGETS["conflict_adjudicator"].max_completion_tokens == 1536

    assert AGENT_BUDGETS["report_intelligence"].target_prompt_tokens == 4096
    assert AGENT_BUDGETS["report_intelligence"].max_completion_tokens == 2048


def test_context_bounds_enforcement_and_compression():
    """Verify that oversized prompts are compressed while preserving structure."""
    small_prompt = '{"claim_id": "test", "text": "Short prompt."}'
    bounded, est, was_compressed = validate_and_enforce_context_bounds(small_prompt, "advocate")
    assert was_compressed is False
    assert bounded == small_prompt

    # Create oversized prompt exceeding 3072 tokens
    huge_prompt = "Large repetitive context line.\n" * 800
    bounded_huge, est_huge, was_compressed_huge = validate_and_enforce_context_bounds(huge_prompt, "advocate")
    assert was_compressed_huge is True
    assert est_huge < estimate_tokens(huge_prompt)


def test_passage_relevance_caching():
    """Verify deterministic passage relevance caching."""
    claim = "Deep learning increases throughput."
    evidence = "Experimental data confirms a 3.4x throughput increase."
    
    # Initially None
    assert get_cached_relevance(claim, evidence) is None
    
    # Store and retrieve
    set_cached_relevance(claim, evidence, 0.92)
    assert get_cached_relevance(claim, evidence) == 0.92


def test_study_intent_vs_empirical_findings_gate():
    """Verify that study intent without findings is classified as contextual support, not direct proof."""
    intent_passage = (
        "In this thesis, we investigate whether artificial intelligence models can optimize "
        "energy efficiency in industrial manufacturing protocols."
    )
    result = validate_evidence_claim_entailment_heuristic(
        claim_id=str(uuid.uuid4()),
        claim_text="Artificial intelligence models optimize industrial energy efficiency.",
        evidence_id=str(uuid.uuid4()),
        evidence_text=intent_passage,
    )
    assert result.entailment_classification == EntailmentClassification.CONTEXTUAL_SUPPORT
    assert "study intent" in result.explanation.lower()


def test_correlation_vs_causation_flag():
    """Verify that associative phrases flag correlation vs causation on causal claims."""
    correlational_passage = (
        "High GPU utilization was associated with increased server rack temperatures "
        "alongside elevated fan speeds during the observation period."
    )
    result = validate_evidence_claim_entailment_heuristic(
        claim_id=str(uuid.uuid4()),
        claim_text="GPU utilization caused the thermal spike in server racks.",
        evidence_id=str(uuid.uuid4()),
        evidence_text=correlational_passage,
    )
    assert result.correlation_vs_causation_flag is True
    assert result.entailment_classification == EntailmentClassification.CONTEXTUAL_SUPPORT


def test_direct_contradiction_detection():
    """Verify that contradicting passages are strictly classified as direct contradiction."""
    contradiction_passage = (
        "Our randomized controlled benchmark refutes the assertion that model quantization "
        "always preserves zero-shot reasoning accuracy, demonstrating an 18% degradation."
    )
    result = validate_evidence_claim_entailment_heuristic(
        claim_id=str(uuid.uuid4()),
        claim_text="Model quantization preserves zero-shot reasoning accuracy.",
        evidence_id=str(uuid.uuid4()),
        evidence_text=contradiction_passage,
    )
    assert result.entailment_classification == EntailmentClassification.DIRECT_CONTRADICTION
    assert result.entailment_strength >= 0.8


def test_quality_calibration_denies_very_strong_without_peer_review():
    """Verify that 'Very Strong' is denied when verified peer-reviewed literature is absent."""
    fake_sources = [
        {"id": str(uuid.uuid4()), "url": "https://techblog.com/post1", "title": "Blog post", "source_type": "web", "publisher": "TechBlog"},
        {"id": str(uuid.uuid4()), "url": "https://techblog.com/post2", "title": "Blog post 2", "source_type": "web", "publisher": "TechBlog"},
    ]
    fake_claims = [{"id": str(uuid.uuid4()), "text": "Claim 1"}]
    fake_evidence = [
        {"id": str(uuid.uuid4()), "claim_id": fake_claims[0]["id"], "exact_text": "Passage text 1"},
    ]

    breakdown = calculate_calibrated_quality(fake_sources, fake_claims, fake_evidence)
    assert breakdown.calibrated_tier != "Very Strong"
    assert breakdown.calibrated_tier != "Strong"


def test_argument_payload_normalizer_robustness():
    """Verify that ArgumentPayload normalizer handles varied LLM inputs safely without validation errors."""
    raw_llm_dict = {
        "claim_id": str(uuid.uuid4()),
        "evidence_basis": "source_criticism",  # Misplaced argument type in evidence_basis
        "confidence_level": "high",  # Flat string confidence
        "text": "Empirical critique of source methodology.",
        "extra_unexpected_field": "safe_to_ignore",
    }
    payload = ArgumentPayload.model_validate(raw_llm_dict)
    assert payload.argument_type == ArgumentType.source_criticism
    assert payload.evidence_basis == "direct"
    assert payload.confidence.level == "strong"


def test_openvino_qwen_screenshot_variations_pass_validation():
    """Verify exact payload anomalies from OpenVINO Qwen screenshot pass without validation errors."""
    from app.analysis.protocol import DecisionPayload
    from app.analysis.service import _ArgumentsListPayload, _DecisionsListPayload

    # 1. advocate anomaly: missing argument_type, confidence: 'high', confidence_level: 'high'
    advocate_dict = {
        "claim_id": str(uuid.uuid4()),
        "confidence": "high",
        "confidence_level": "high",
        "text": "Advocate argument supporting the claim.",
    }
    adv_arg = ArgumentPayload.model_validate(advocate_dict)
    assert adv_arg.confidence.level == "strong"
    assert adv_arg.argument_type == ArgumentType.qualifying
    assert adv_arg.evidence_basis == "none"

    # 2. skeptic anomaly: omitted claim_id, confidence: 'insufficient', confidence_level: 'insufficient'
    skeptic_dict = {
        "argument_type": "qualifying",
        "confidence": "insufficient",
        "confidence_level": "insufficient",
    }
    skep_arg = ArgumentPayload.model_validate(skeptic_dict)
    assert skep_arg.claim_id is None
    assert skep_arg.confidence.level == "insufficient"
    assert "Evidence-grounded" in skep_arg.text

    # 3. methodology_auditor anomaly: confidence dict with level only, no explanation
    methodology_dict = {
        "claim_id": str(uuid.uuid4()),
        "argument_type": "methodological_criticism",
        "confidence": {"level": "insufficient"},
        "confidence_level": "insufficient",
    }
    meth_arg = ArgumentPayload.model_validate(methodology_dict)
    assert meth_arg.confidence.level == "insufficient"
    assert "insufficient" in meth_arg.confidence.explanation

    # 4. source_intelligence anomaly: evidence_basis: 'contextual', missing reasoning_summary
    source_dict = {
        "claim_id": str(uuid.uuid4()),
        "evidence_basis": "contextual",
        "confidence": "moderate",
    }
    src_arg = ArgumentPayload.model_validate(source_dict)
    assert src_arg.evidence_basis == "indirect"
    assert src_arg.reasoning_summary is not None

    # Wrapper payload extra="ignore" check
    wrapped = _ArgumentsListPayload.model_validate({
        "arguments": [advocate_dict, skeptic_dict, methodology_dict, source_dict],
        "unexpected_openvino_meta": {"tokens": 120, "speed": 11.7},
    })
    assert len(wrapped.arguments) == 4

    # DecisionPayload normalization check
    dec = DecisionPayload.model_validate({
        "decision": "supported",
        "extra_field": 123,
    })
    assert dec.decision == "moderately_supported"
    assert dec.claim_id is None
    assert len(dec.explanation) > 0
