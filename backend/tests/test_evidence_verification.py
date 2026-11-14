"""Tests for Evidence-to-Claim Scientific Verification Service (Milestone 12)."""

import pytest
import uuid
from app.analysis.evidence_verification_service import (
    classify_passage_to_claim,
    RelationshipClassification,
    VerificationStatus,
    EvidenceVerificationService,
)
from app.db import SessionFactory
from app.models import Claim, Evidence, Investigation, Source, User


def test_classify_passage_directly_supports():
    claim = "Deep neural networks significantly accelerate protein structure prediction."
    passage = "Empirical data shows that deep neural networks found that protein structure prediction runtime was reduced by 90%, demonstrating that deep learning accelerates structural modeling."
    rel, conf, meaning, exp, status = classify_passage_to_claim(passage, claim)
    assert rel == RelationshipClassification.DIRECTLY_SUPPORTS
    assert conf >= 0.85
    assert status == VerificationStatus.VERIFIED


def test_classify_passage_safeguard_study_aim_is_not_direct_support():
    """Scientific safeguard: Study aims, purpose, and thesis framing must NOT be classified as direct support."""
    claim = "Quantum annealing solves vehicle routing faster than classical simulated annealing."
    passage = "The purpose of this study is to examine whether quantum annealing solves vehicle routing faster than classical algorithms. This paper explores the computational limits."
    rel, conf, meaning, exp, status = classify_passage_to_claim(passage, claim)
    assert rel == RelationshipClassification.CONTEXTUAL_BACKGROUND
    assert rel != RelationshipClassification.DIRECTLY_SUPPORTS
    assert "study_aim" in meaning


def test_classify_passage_contradiction():
    claim = "Hydration supplements increase sprint acceleration in elite athletes."
    passage = "Double-blind experimental results show that hydration supplements did not result in sprint acceleration changes, which refutes the claim and contradicts earlier findings."
    rel, conf, meaning, exp, status = classify_passage_to_claim(passage, claim)
    assert rel == RelationshipClassification.CONTRADICTS
    assert conf >= 0.80
    assert status == VerificationStatus.VERIFIED


def test_classify_passage_mentions_subject_without_claim():
    claim = "NVIDIA gross margins expanded due to datacenter generative AI accelerator dominance."
    passage = "NVIDIA is a technology company headquartered in Santa Clara that produces graphics chips and hardware components for personal computers."
    rel, conf, meaning, exp, status = classify_passage_to_claim(passage, claim)
    assert rel == RelationshipClassification.MENTIONS_SUBJECT


def test_classify_passage_insufficient_or_empty():
    claim = "Solid-state batteries achieve 500 Wh/kg energy density."
    rel, conf, meaning, exp, status = classify_passage_to_claim("", claim)
    assert rel == RelationshipClassification.INSUFFICIENT_INFORMATION
    assert status == VerificationStatus.UNCERTAIN


@pytest.mark.asyncio
async def test_evidence_verification_service_audit_and_challenge():
    """Verify service end-to-end verification and reviewer challenge handling."""
    inv_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    source_id = uuid.uuid4()
    ev_id = uuid.uuid4()
    user_id = uuid.uuid4()

    async with SessionFactory() as session:
        # Create test entities
        inv = Investigation(id=inv_id, question="Does fasting improve insulin sensitivity?", mode="deep", status="created")
        session.add(inv)
        src = Source(
            id=source_id,
            investigation_id=inv_id,
            title="Intermittent Fasting Trial",
            canonical_url="https://nature.com/articles/fasting-1",
            original_url="https://nature.com/articles/fasting-1",
            source_type="academic",
        )
        session.add(src)
        claim = Claim(id=claim_id, investigation_id=inv_id, text="Intermittent fasting increases insulin sensitivity by 20%.")
        session.add(claim)
        ev = Evidence(
            id=ev_id,
            source_id=source_id,
            exact_text="Results show that intermittent fasting increases insulin sensitivity significantly.",
            evidence_type="empirical",
            extraction_method="direct",
        )
        session.add(ev)
        user = User(id=user_id, email=f"reviewer_{uuid.uuid4().hex[:6]}@neomon.ai", password_hash="hash", display_name="Dr. Reviewer", role="researcher")
        session.add(user)
        await session.commit()

        service = EvidenceVerificationService(session)
        records = await service.verify_investigation_evidence(inv_id)
        assert len(records) == 1
        rec = records[0]
        assert rec.relationship_classification == RelationshipClassification.DIRECTLY_SUPPORTS.value
        assert rec.is_challenged is False

        # Reviewer challenges classification
        corrected = await service.challenge_and_correct_record(
            record_id=rec.id,
            user_id=user_id,
            corrected_classification=RelationshipClassification.PARTIALLY_SUPPORTS.value,
            reason="Effect size was 12%, not the full 20% claimed.",
        )
        assert corrected.is_challenged is True
        assert corrected.relationship_classification == RelationshipClassification.PARTIALLY_SUPPORTS.value
        assert corrected.verification_status == VerificationStatus.CORRECTED.value
        assert corrected.corrected_by_user_id == user_id
