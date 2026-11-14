"""Tests for Human Review, Evidence Corrections, and Reassessment (Milestone 12)."""

import uuid
import pytest
from app.db import SessionFactory
from app.models import (
    Claim,
    Evidence,
    EvidenceVerificationRecord,
    Investigation,
    Source,
    User,
    Workspace,
    WorkspaceMember,
)
from app.analysis.human_review_service import HumanReviewService, CorrectionType
from app.analysis.evidence_verification_service import RelationshipClassification


@pytest.mark.asyncio
async def test_human_correction_permission_and_audit():
    """Verify that reviewer can submit corrections and unauthorized users are blocked."""
    ws_id = uuid.uuid4()
    inv_id = uuid.uuid4()
    claim_id = uuid.uuid4()
    ev_id = uuid.uuid4()
    reviewer_id = uuid.uuid4()
    viewer_id = uuid.uuid4()

    async with SessionFactory() as session:
        ws = Workspace(id=ws_id, name="Scientific Audit Workspace", slug="scientific-audit-workspace", owner_id=reviewer_id)
        session.add(ws)
        inv = Investigation(id=inv_id, question="Effect of lithium on neurogenesis", mode="deep", workspace_id=ws_id)
        session.add(inv)
        src = Source(
            id=uuid.uuid4(),
            investigation_id=inv_id,
            title="Neuroscience Report",
            canonical_url="https://nature.com/neuro-1",
            original_url="https://nature.com/neuro-1",
            source_type="peer_reviewed",
        )
        session.add(src)
        claim = Claim(id=claim_id, investigation_id=inv_id, text="Lithium doubles hippocampal neurogenesis.")
        session.add(claim)
        ev = Evidence(
            id=ev_id,
            source_id=src.id,
            exact_text="Lithium was associated with hippocampal neurogenesis markers in rodents.",
            evidence_type="empirical",
            extraction_method="direct",
        )
        session.add(ev)

        vr = EvidenceVerificationRecord(
            id=uuid.uuid4(),
            investigation_id=inv_id,
            claim_id=claim_id,
            evidence_id=ev_id,
            source_id=src.id,
            exact_passage_text=ev.passage,
            relationship_classification=RelationshipClassification.DIRECTLY_SUPPORTS.value,
            verification_status="verified",
            confidence=0.85,
        )
        session.add(vr)

        reviewer = User(id=reviewer_id, email=f"rev_{uuid.uuid4().hex[:6]}@neomon.ai", password_hash="h", display_name="Dr. Reviewer", role="researcher")
        viewer = User(id=viewer_id, email=f"view_{uuid.uuid4().hex[:6]}@neomon.ai", password_hash="h", display_name="Dr. Viewer", role="researcher")
        session.add(reviewer)
        session.add(viewer)

        m_rev = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=reviewer_id, role="reviewer")
        m_view = WorkspaceMember(id=uuid.uuid4(), workspace_id=ws_id, user_id=viewer_id, role="viewer")
        session.add(m_rev)
        session.add(m_view)
        await session.commit()

        service = HumanReviewService(session)

        # Viewer should be blocked (min role is reviewer)
        with pytest.raises(Exception):
            await service.submit_evidence_correction(
                investigation_id=inv_id,
                claim_id=claim_id,
                evidence_id=ev_id,
                user=viewer,
                correction_type=CorrectionType.MARK_CONTEXTUAL.value,
                corrected_value=RelationshipClassification.CONTEXTUAL_BACKGROUND.value,
                reason="Passage is associative rodent study, not human clinical trial.",
            )

        # Reviewer succeeds
        correction = await service.submit_evidence_correction(
            investigation_id=inv_id,
            claim_id=claim_id,
            evidence_id=ev_id,
            user=reviewer,
            correction_type=CorrectionType.MARK_CONTEXTUAL.value,
            corrected_value=RelationshipClassification.CONTEXTUAL_BACKGROUND.value,
            reason="Passage is associative rodent study, not human clinical trial.",
        )
        assert correction.original_value == RelationshipClassification.DIRECTLY_SUPPORTS.value
        assert correction.corrected_value == RelationshipClassification.CONTEXTUAL_BACKGROUND.value
        assert correction.user_id == reviewer_id

        # Verify audit history
        history = await service.list_investigation_corrections(inv_id)
        assert len(history) == 1
        assert history[0].id == correction.id

        # Verify versioned reassessment runs cleanly
        reassessment = await service.trigger_versioned_reassessment(inv_id, reviewer)
        assert reassessment["status"] == "reassessed"
        assert "synthesized_claims_count" in reassessment
        assert "calibrated_quality_tier" in reassessment
