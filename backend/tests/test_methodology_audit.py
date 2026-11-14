"""Tests for Research Methodology Audit Service (Milestone 12)."""

import uuid
from datetime import datetime, timezone
import pytest
from app.db import SessionFactory
from app.models import Claim, Evidence, Investigation, Source
from app.analysis.methodology_audit_service import MethodologyAuditService, AuditSeverity


@pytest.mark.asyncio
async def test_audit_question_clarity_and_decomposition():
    """Verify that broad questions reduced to 1 claim or short non-interrogative questions trigger findings."""
    inv_id = uuid.uuid4()

    async with SessionFactory() as session:
        # Question with only 2 words
        inv = Investigation(
            id=inv_id,
            question="Artificial intelligence",
            mode="deep",
            status="created",
        )
        session.add(inv)
        # Single claim for broad topic
        claim = Claim(id=uuid.uuid4(), investigation_id=inv_id, text="AI is transforming society.")
        session.add(claim)
        await session.commit()

        service = MethodologyAuditService(session)
        findings = await service.audit_investigation(inv_id)
        
        dimensions = {f.audit_dimension for f in findings}
        assert "question_clarity" in dimensions
        severities = {f.issue_severity for f in findings}
        assert AuditSeverity.CONFIRMED_PROBLEM.value in severities


@pytest.mark.asyncio
async def test_audit_selection_and_temporal_bias():
    """Verify detection of source selection bias (0 academic papers) and temporal obsolescence."""
    inv_id = uuid.uuid4()

    async with SessionFactory() as session:
        inv = Investigation(
            id=inv_id,
            question="What are the latest enterprise cybersecurity zero trust frameworks?",
            mode="deep",
            status="created",
        )
        session.add(inv)

        # 3 vendor/commercial sources published in 2015 (> 10 years old)
        old_date = datetime(2015, 1, 15, tzinfo=timezone.utc)
        for i in range(3):
            s = Source(
                id=uuid.uuid4(),
                investigation_id=inv_id,
                title=f"Vendor Security Whitepaper {i}",
                canonical_url=f"https://vendor-security-portal.com/wp{i}",
                original_url=f"https://vendor-security-portal.com/wp{i}",
                source_type="vendor_commercial",
                publication_date=old_date,
            )
            session.add(s)

        await session.commit()

        service = MethodologyAuditService(session)
        findings = await service.audit_investigation(inv_id)

        dimensions = {f.audit_dimension: f for f in findings}
        assert "source_selection_bias" in dimensions
        assert "Total Absence of Peer-Reviewed Literature" in dimensions["source_selection_bias"].finding_title

        assert "temporal_bias" in dimensions
        assert "Outdated Evidence Base" in dimensions["temporal_bias"].finding_title


@pytest.mark.asyncio
async def test_audit_correlation_vs_causation():
    """Verify detection of correlational evidence used without isolating mechanism."""
    inv_id = uuid.uuid4()

    async with SessionFactory() as session:
        inv = Investigation(
            id=inv_id,
            question="Does standing desk usage reduce corporate healthcare expenditures?",
            mode="deep",
            status="created",
        )
        session.add(inv)
        src = Source(
            id=uuid.uuid4(),
            investigation_id=inv_id,
            title="Ergonomics Journal",
            canonical_url="https://ergonomics.org/paper1",
            original_url="https://ergonomics.org/paper1",
            source_type="academic",
        )
        session.add(src)
        ev = Evidence(
            id=uuid.uuid4(),
            source_id=src.id,
            exact_text="Standing desk adoption was correlated with lower reported absenteeism alongside lower health claims during the same period.",
            evidence_type="empirical",
            extraction_method="direct",
        )
        session.add(ev)
        await session.commit()

        service = MethodologyAuditService(session)
        findings = await service.audit_investigation(inv_id)

        cv_finding = next((f for f in findings if f.audit_dimension == "correlation_vs_causation"), None)
        assert cv_finding is not None
        assert cv_finding.issue_severity == AuditSeverity.POTENTIAL_CONCERN.value
        assert "conflating correlation with causation" in cv_finding.description.lower() or "statistical association" in cv_finding.description.lower()
