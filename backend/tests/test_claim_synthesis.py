"""Tests for Claim-Level Evidence Synthesis Engine (Milestone 12)."""

import json
import uuid
import pytest
from app.analysis.claim_synthesis_service import ClaimSynthesisService, ClaimSynthesisOutcome
from app.analysis.evidence_verification_service import RelationshipClassification
from app.db import SessionFactory
from app.models import (
    Claim,
    Evidence,
    EvidenceVerificationRecord,
    Investigation,
    Source,
    StudyIndependenceCluster,
)


@pytest.mark.asyncio
async def test_claim_synthesis_strongly_supported():
    """Verify >= 2 independent studies with direct support synthesizes to strongly_supported."""
    inv_id = uuid.uuid4()
    claim_id = uuid.uuid4()

    async with SessionFactory() as session:
        inv = Investigation(id=inv_id, question="Quantum error mitigation efficacy", mode="deep", status="created")
        session.add(inv)
        claim = Claim(id=claim_id, investigation_id=inv_id, text="Zero noise extrapolation reduces quantum expectation value bias.")
        session.add(claim)

        # 2 distinct study clusters
        c1_id = uuid.uuid4()
        c2_id = uuid.uuid4()
        s1_id = uuid.uuid4()
        s2_id = uuid.uuid4()

        cluster1 = StudyIndependenceCluster(
            id=c1_id,
            investigation_id=inv_id,
            cluster_label="IBM Quantum Group",
            member_source_ids_json=json.dumps([str(s1_id)]),
            relationship_category="confirmed_independent",
            confidence=0.95,
            evidence_rationale="Independent peer reviewed",
        )
        cluster2 = StudyIndependenceCluster(
            id=c2_id,
            investigation_id=inv_id,
            cluster_label="ETH Zurich Group",
            member_source_ids_json=json.dumps([str(s2_id)]),
            relationship_category="confirmed_independent",
            confidence=0.95,
            evidence_rationale="Independent replication",
        )
        session.add(cluster1)
        session.add(cluster2)

        # 2 direct supporting verification records
        vr1 = EvidenceVerificationRecord(
            id=uuid.uuid4(),
            investigation_id=inv_id,
            claim_id=claim_id,
            evidence_id=uuid.uuid4(),
            source_id=s1_id,
            exact_passage_text="Data proves zero noise extrapolation reduces bias by 70%.",
            relationship_classification=RelationshipClassification.DIRECTLY_SUPPORTS.value,
            verification_status="verified",
            confidence=0.92,
        )
        vr2 = EvidenceVerificationRecord(
            id=uuid.uuid4(),
            investigation_id=inv_id,
            claim_id=claim_id,
            evidence_id=uuid.uuid4(),
            source_id=s2_id,
            exact_passage_text="Independent experiments confirm reduction in expectation value bias.",
            relationship_classification=RelationshipClassification.DIRECTLY_SUPPORTS.value,
            verification_status="verified",
            confidence=0.90,
        )
        session.add(vr1)
        session.add(vr2)
        await session.commit()

        service = ClaimSynthesisService(session)
        results = await service.synthesize_investigation_claims(inv_id)
        assert len(results) == 1
        res = results[0]
        assert res.synthesis_outcome == ClaimSynthesisOutcome.STRONGLY_SUPPORTED.value
        assert res.unique_underlying_studies_count == 2
        assert res.direct_supporting_count == 2
        assert res.contradicting_count == 0


@pytest.mark.asyncio
async def test_claim_synthesis_duplicate_study_deduplication():
    """Verify that multiple documents reproducing the same underlying study count as 1 study."""
    inv_id = uuid.uuid4()
    claim_id = uuid.uuid4()

    async with SessionFactory() as session:
        inv = Investigation(id=inv_id, question="Graphene thermal conductivity", mode="deep", status="created")
        session.add(inv)
        claim = Claim(id=claim_id, investigation_id=inv_id, text="Single-layer graphene exhibits 5000 W/mK thermal conductivity.")
        session.add(claim)

        # 3 documents from the SAME study cluster (e.g. syndicated news)
        cluster_id = uuid.uuid4()
        s1 = uuid.uuid4()
        s2 = uuid.uuid4()
        s3 = uuid.uuid4()

        cluster = StudyIndependenceCluster(
            id=cluster_id,
            investigation_id=inv_id,
            cluster_label="Original Balandin Study & Syndications",
            member_source_ids_json=json.dumps([str(s1), str(s2), str(s3)]),
            relationship_category="duplicate_publications",
            confidence=0.95,
            evidence_rationale="Syndicated coverage of the same single study",
        )
        session.add(cluster)

        for sid in [s1, s2, s3]:
            vr = EvidenceVerificationRecord(
                id=uuid.uuid4(),
                investigation_id=inv_id,
                claim_id=claim_id,
                evidence_id=uuid.uuid4(),
                source_id=sid,
                exact_passage_text="Balandin found graphene thermal conductivity reached 5000 W/mK.",
                relationship_classification=RelationshipClassification.DIRECTLY_SUPPORTS.value,
                verification_status="verified",
                confidence=0.88,
            )
            session.add(vr)

        await session.commit()

        service = ClaimSynthesisService(session)
        results = await service.synthesize_investigation_claims(inv_id)
        assert len(results) == 1
        res = results[0]
        # Should count as 1 unique study, not 3!
        assert res.unique_underlying_studies_count == 1
        assert res.direct_supporting_count == 3
        # With only 1 study, cannot be "strongly_supported"; should be "moderately_supported"
        assert res.synthesis_outcome == ClaimSynthesisOutcome.MODERATELY_SUPPORTED.value
        assert "Relies on single study" in res.methodological_limitations_json


@pytest.mark.asyncio
async def test_claim_synthesis_mixed_and_contradicted():
    """Verify contradiction handling leads to mixed_evidence or contradicted."""
    inv_id = uuid.uuid4()
    claim_id = uuid.uuid4()

    async with SessionFactory() as session:
        inv = Investigation(id=inv_id, question="Sodium glucose co-transporter renal effect", mode="deep", status="created")
        session.add(inv)
        claim = Claim(id=claim_id, investigation_id=inv_id, text="Drug X has no effect on glomerular filtration rate.")
        session.add(claim)

        # 1 supporting and 2 contradicting
        s1 = uuid.uuid4()
        s2 = uuid.uuid4()

        vr1 = EvidenceVerificationRecord(
            id=uuid.uuid4(),
            investigation_id=inv_id,
            claim_id=claim_id,
            evidence_id=uuid.uuid4(),
            source_id=s1,
            exact_passage_text="No significant GFR change observed.",
            relationship_classification=RelationshipClassification.DIRECTLY_SUPPORTS.value,
            verification_status="verified",
            confidence=0.75,
        )
        vr2 = EvidenceVerificationRecord(
            id=uuid.uuid4(),
            investigation_id=inv_id,
            claim_id=claim_id,
            evidence_id=uuid.uuid4(),
            source_id=s2,
            exact_passage_text="Clinical trial refutes this: GFR increased by 15% with statistical significance.",
            relationship_classification=RelationshipClassification.CONTRADICTS.value,
            verification_status="verified",
            confidence=0.92,
        )
        session.add(vr1)
        session.add(vr2)
        await session.commit()

        service = ClaimSynthesisService(session)
        results = await service.synthesize_investigation_claims(inv_id)
        assert len(results) == 1
        res = results[0]
        assert res.synthesis_outcome == ClaimSynthesisOutcome.MIXED_EVIDENCE.value
        assert res.contradicting_count == 1
        assert res.direct_supporting_count == 1
