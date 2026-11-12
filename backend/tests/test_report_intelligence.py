import asyncio
import json
import uuid

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.analysis.protocol import DecisionPayload, EvidenceProvenance
from app.analysis.report_service import (
    REPORT_18_SECTION_SPECS,
    build_18_report_sections,
    compute_evidence_strength,
    get_report_version,
    list_report_versions,
    save_report_version,
)
from app.db import SessionFactory
from app.main import app
from app.models import (
    AdjudicationDecision,
    AnalysisJob,
    Base,
    Claim,
    Document,
    Evidence,
    Investigation,
    ReportSection,
    ReportVersion,
    ResearchReport,
    Source,
)
from app.schemas import EvidenceStrengthSummary


@pytest_asyncio.fixture
async def session(tmp_path):
    db_path = tmp_path / "report_test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", connect_args={"timeout": 5})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as sess:
        yield sess
    await engine.dispose()


def test_evidence_strength_scoring_dimensions_and_tiers():
    c1 = Claim(id=uuid.uuid4(), text="Claim A", priority=1)
    c2 = Claim(id=uuid.uuid4(), text="Claim B", priority=2)

    src1 = Source(
        id=uuid.uuid4(),
        title="Journal of Systems",
        canonical_url="https://acm.org/paper1",
        publisher="ACM",
        source_type="academic",
        doi="10.1145/1",
        relevance_score=0.95,
    )
    src2 = Source(
        id=uuid.uuid4(),
        title="IEEE Transactions",
        canonical_url="https://ieee.org/paper2",
        publisher="IEEE",
        source_type="academic",
        doi="10.1109/2",
        relevance_score=0.92,
    )
    src3 = Source(
        id=uuid.uuid4(),
        title="Nature Machine Intelligence",
        canonical_url="https://nature.com/paper3",
        publisher="Nature",
        source_type="academic",
        doi="10.1038/3",
        relevance_score=0.98,
    )
    src4 = Source(
        id=uuid.uuid4(),
        title="Government Technical Report",
        canonical_url="https://nist.gov/report",
        publisher="NIST",
        source_type="institutional",
        relevance_score=0.90,
    )

    doc1 = Document(id=uuid.uuid4(), source_id=src1.id, access_level="full_text")
    doc2 = Document(id=uuid.uuid4(), source_id=src2.id, access_level="full_text")
    doc3 = Document(id=uuid.uuid4(), source_id=src3.id, access_level="full_text")
    doc4 = Document(id=uuid.uuid4(), source_id=src4.id, access_level="full_text")

    ev1 = Evidence(id=uuid.uuid4(), source_id=src1.id, exact_text="Direct finding 1", evidence_type="direct", relevance_score=0.95)
    ev2 = Evidence(id=uuid.uuid4(), source_id=src2.id, exact_text="Direct finding 2", evidence_type="direct", relevance_score=0.90)

    dec1 = DecisionPayload(claim_id=c1.id, decision="strongly_supported", explanation="Confirmed", supporting_argument_ids=[], evidence_ids=[ev1.id], unresolved_disagreements=[])
    dec2 = DecisionPayload(claim_id=c2.id, decision="strongly_supported", explanation="Confirmed", supporting_argument_ids=[], evidence_ids=[ev2.id], unresolved_disagreements=[])

    strength_high = compute_evidence_strength(
        claims=[c1, c2],
        sources=[src1, src2, src3, src4],
        documents=[doc1, doc2, doc3, doc4],
        evidence=[ev1, ev2],
        decisions=[dec1, dec2],
    )
    assert strength_high.score >= 85.0
    assert strength_high.tier == "very_strong"
    assert strength_high.breakdown.source_independence == 25.0
    assert strength_high.breakdown.full_text_coverage == 20.0

    src_weak = Source(
        id=uuid.uuid4(),
        title="Random Blog Post",
        canonical_url="https://blog.example.com/post",
        source_type="web",
        relevance_score=0.4,
    )
    ev_weak = Evidence(id=uuid.uuid4(), source_id=src_weak.id, exact_text="Vague mention", evidence_type="contextual", relevance_score=0.4)
    dec_weak = DecisionPayload(claim_id=c1.id, decision="insufficient_evidence", explanation="Weak", supporting_argument_ids=[], evidence_ids=[], unresolved_disagreements=["Unverified"])

    strength_low = compute_evidence_strength(
        claims=[c1],
        sources=[src_weak],
        documents=[],
        evidence=[ev_weak],
        decisions=[dec_weak],
    )
    assert strength_low.score < 50.0
    assert strength_low.tier in {"weak", "inconclusive"}


def test_build_18_report_sections_has_complete_structure():
    cid = uuid.uuid4()
    claim = Claim(id=cid, text="LLMs improve code comprehension speed.", priority=1)
    src_id = uuid.uuid4()
    src = Source(
        id=src_id,
        title="Controlled Developer Experiment",
        canonical_url="https://doi.org/10.1234/test",
        publisher="ACM",
        authors_json=json.dumps(["Alice", "Bob"]),
        doi="10.1234/test",
    )
    eid = uuid.uuid4()
    ev = Evidence(id=eid, source_id=src_id, exact_text="Comprehension speed was 22% faster.", evidence_type="direct", relevance_score=0.9)
    dec = DecisionPayload(claim_id=cid, decision="strongly_supported", explanation="Statistically significant.", supporting_argument_ids=[], evidence_ids=[eid], unresolved_disagreements=[])

    def dummy_prov(eids):
        return [
            EvidenceProvenance(
                evidence_id=eid,
                source_url="https://doi.org/10.1234/test",
                access_level="full_text",
            )
        ] if eid in eids else []

    sections = build_18_report_sections(
        question="How do LLMs impact software comprehension?",
        claims=[claim],
        decisions=[dec],
        evidence=[ev],
        sources={src_id: src},
        documents={},
        arguments=[],
        warnings=["Non-fatal queue notice"],
        provenance_for_fn=dummy_prov,
    )

    assert len(sections) == 18
    actual_types = [s.section_type for s in sections]
    expected_types = [spec[0] for spec in REPORT_18_SECTION_SPECS]
    assert actual_types == expected_types

    claim_sec = next(s for s in sections if s.section_type == "claim_by_claim_assessment")
    assert "LLMs improve code comprehension" in claim_sec.content
    assert "Strongly Supported" in claim_sec.content
    assert cid in claim_sec.claim_ids

    ref_sec = next(s for s in sections if s.section_type == "references_directory")
    assert "Controlled Developer Experiment" in ref_sec.content
    assert "Alice, Bob" in ref_sec.content


@pytest.mark.asyncio
async def test_report_versioning_and_snapshots(session):
    inv_id = uuid.uuid4()
    job_id = uuid.uuid4()

    inv = Investigation(id=inv_id, question="Quantum supremacy verification", mode="deep")
    session.add(inv)
    job = AnalysisJob(id=job_id, investigation_id=inv_id, status="completed")
    session.add(job)
    await session.commit()

    strength = EvidenceStrengthSummary(score=78.5, tier="strong")

    from app.analysis.protocol import ReportSectionPayload
    payload = [
        ReportSectionPayload(
            section_type="executive_summary",
            title="Executive Summary",
            content="Initial findings",
            claim_ids=[],
        )
    ]

    v1 = await save_report_version(
        session, inv_id, job_id, "Summary V1", "qualified", None, payload, strength
    )
    assert v1.version_number == 1

    payload[0].content = "Updated findings with additional evidence"
    v2 = await save_report_version(
        session, inv_id, job_id, "Summary V2", "strongly_supported", None, payload, strength
    )
    assert v2.version_number == 2

    versions = await list_report_versions(session, inv_id)
    assert len(versions) == 2
    assert versions[0].version_number == 2
    assert versions[1].version_number == 1
    assert versions[0].executive_summary == "Summary V2"

    row, sec = await get_report_version(session, inv_id, "1")
    assert row is not None
    assert row.version_number == 1
    assert sec[0]["content"] == "Initial findings"

    row_uuid, _ = await get_report_version(session, inv_id, str(v2.id))
    assert row_uuid is not None
    assert row_uuid.version_number == 2

    row_none, _ = await get_report_version(session, inv_id, "999")
    assert row_none is None


def test_report_endpoints_via_test_client():
    inv_id = uuid.uuid4()
    job_id = uuid.uuid4()
    report_id = uuid.uuid4()
    sec_id = uuid.uuid4()

    async def seed():
        async with SessionFactory() as s:
            inv = Investigation(id=inv_id, question="Does code review reduce production bugs?", mode="quick")
            job = AnalysisJob(id=job_id, investigation_id=inv_id, status="completed")
            rep = ResearchReport(id=report_id, job_id=job_id, executive_summary="Initial summary", overall_assessment="qualified")
            sec = ReportSection(report_id=report_id, section_type="executive_summary", title="Executive Summary", content="Summary content", position=0)
            c = Claim(id=uuid.uuid4(), investigation_id=inv_id, text="Review reduces bugs.", priority=1)
            src = Source(
                id=uuid.uuid4(),
                investigation_id=inv_id,
                title="Study 1",
                canonical_url="https://example.org/1",
                original_url="https://example.org/1",
                source_type="academic",
            )
            s.add_all([inv, job, rep, sec, c, src])
            await s.commit()

    asyncio.run(seed())

    try:
        with TestClient(app) as client:
            # 1. Read active report
            report_resp = client.get(f"/api/v1/research/analysis/{job_id}/report")
            assert report_resp.status_code == 200
            data = report_resp.json()
            assert data["id"] == str(report_id)
            assert data["evidence_strength"] is not None

            # 2. Regenerate report
            regen_resp = client.post(f"/api/v1/research/investigations/{inv_id}/reports/generate")
            assert regen_resp.status_code == 200
            regen_data = regen_resp.json()
            assert len(regen_data["sections"]) == 18
            assert regen_data["version_number"] >= 1

            # 3. List report versions
            ver_resp = client.get(f"/api/v1/research/investigations/{inv_id}/reports")
            assert ver_resp.status_code == 200
            vers = ver_resp.json()
            assert len(vers) >= 1
            assert vers[0]["version_number"] >= 1

            # 4. Fetch specific version
            ver1_resp = client.get(f"/api/v1/research/investigations/{inv_id}/reports/1")
            assert ver1_resp.status_code == 200
            assert ver1_resp.json()["version_number"] == 1

            # 5. Invalid version returns 404
            assert client.get(f"/api/v1/research/investigations/{inv_id}/reports/999").status_code == 404
    finally:
        async def cleanup():
            async with SessionFactory() as s:
                await s.execute(delete(ReportVersion).where(ReportVersion.investigation_id == inv_id))
                await s.execute(delete(ReportSection).where(ReportSection.report_id == report_id))
                await s.execute(delete(ResearchReport).where(ResearchReport.id == report_id))
                await s.execute(delete(AnalysisJob).where(AnalysisJob.id == job_id))
                await s.execute(delete(Investigation).where(Investigation.id == inv_id))
                await s.commit()
        asyncio.run(cleanup())
