import json
import socket
import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import httpx
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.analysis.service import ROLE_SYSTEM_INSTRUCTIONS, run_analysis
from app.db import SessionFactory, engine as app_engine
from app.events import EventBroker
from app.main import app
from app.models import (
    AgentArgument,
    AnalysisAgentExecution,
    AnalysisJob,
    Base,
    Claim,
    ClaimEvidenceRelationship,
    Document,
    Evidence,
    ExtractionExecution,
    Investigation,
    OpenAccessLocation,
    Source,
)
from app.providers.limiter import provider_concurrency_registry
from app.schemas import ProviderConfigRequest, ProviderKind


@pytest_asyncio.fixture
async def isolated_session(tmp_path):
    db_path = tmp_path / "workspace_test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", connect_args={"timeout": 5})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture(autouse=True)
def _reset_limiter():
    provider_concurrency_registry.reset()
    yield
    provider_concurrency_registry.reset()


def test_role_system_instructions_only_mention_valid_argument_types():
    allowed = {
        "supporting",
        "contradicting",
        "qualifying",
        "methodological_criticism",
        "source_criticism",
        "temporal_qualification",
    }
    invalid_legacy = ("contextual", "methodological_critique", "source_assessment")
    for role, prompt in ROLE_SYSTEM_INSTRUCTIONS.items():
        for bad in invalid_legacy:
            assert f"'{bad}'" not in prompt, f"{role} references invalid ArgumentType '{bad}'"
        assert "EXACTLY ONE argument object per supplied claim_id" in prompt
        assert any(f"'{token}'" in prompt for token in allowed)


def test_workspace_evidence_sources_and_observatory_pagination_filters_and_isolation():
    import asyncio

    inv1_id = uuid.uuid4()
    inv2_id = uuid.uuid4()
    src1_id = uuid.uuid4()
    src2_rejected_id = uuid.uuid4()
    src_other_id = uuid.uuid4()
    doc1_id = uuid.uuid4()
    claim1_id = uuid.uuid4()
    claim2_unassessed_id = uuid.uuid4()
    claim_other_id = uuid.uuid4()
    ev1_id = uuid.uuid4()
    ev2_missing_doc_id = uuid.uuid4()
    ev_other_id = uuid.uuid4()
    job1_id = uuid.uuid4()
    exec_waiting_id = uuid.uuid4()
    exec_completed_id = uuid.uuid4()
    exec_failed_id = uuid.uuid4()

    async def seed():
        now = datetime.now(UTC)
        async with SessionFactory() as session:
            inv1 = Investigation(id=inv1_id, question="Does code review tooling catch defects early?", mode="deep")
            inv2 = Investigation(id=inv2_id, question="Isolated second investigation question?", mode="quick")
            session.add_all([inv1, inv2])
            await session.flush()

            src1 = Source(
                id=src1_id,
                investigation_id=inv1_id,
                title="Empirical Static Analysis Review",
                canonical_url="https://example.org/review-study",
                original_url="https://example.org/review-study?utm=1",
                source_type="academic",
                publisher="Journal of Systems",
                authors_json=json.dumps(["A. Patel", "B. Gomez"]),
                publication_date="2025-02-14",
                doi="10.1000/review.2025",
                relevance_score=0.91,
                relevance_reasons_json=json.dumps(["Matches software defect detection"]),
                inclusion_status="included",
                open_access_status="resolved",
                selected_document_url="https://repo.example.org/review.pdf",
                retrieval_timestamp=now - timedelta(minutes=10),
            )
            src2 = Source(
                id=src2_rejected_id,
                investigation_id=inv1_id,
                title="Unverified Marketing Blog",
                canonical_url="https://example.org/blog",
                original_url="https://example.org/blog",
                source_type="web",
                relevance_score=0.22,
                inclusion_status="rejected",
                rejection_reason="Lacks primary empirical study methods.",
                open_access_status="unavailable",
                retrieval_timestamp=now - timedelta(minutes=5),
            )
            src_other = Source(
                id=src_other_id,
                investigation_id=inv2_id,
                title="Cross-Investigation Confidential Source",
                canonical_url="https://example.org/other",
                original_url="https://example.org/other",
                source_type="institutional",
                relevance_score=0.99,
                inclusion_status="included",
                open_access_status="metadata_only",
            )
            session.add_all([src1, src2, src_other])
            await session.flush()

            doc1 = Document(
                id=doc1_id,
                source_id=src1_id,
                content_type="application/pdf",
                title="Full-text PDF of Empirical Review",
                content="Automated review detected 28% more boundary defects before merge.",
                headings_json=json.dumps(["Abstract", "Results"]),
                page_count=12,
                access_level="full_text",
                extraction_quality="high",
                document_url="https://repo.example.org/review.pdf",
                version_type="publishedVersion",
                access_route="open_access_repository",
                metadata_match_status="verified",
                retrieved_at=now - timedelta(minutes=9),
            )
            session.add(doc1)
            session.add(
                OpenAccessLocation(
                    source_id=src1_id,
                    url="https://repo.example.org/review.pdf",
                    repository="Zenodo",
                    version_type="publishedVersion",
                    license="CC-BY-4.0",
                    match_status="matched",
                    match_reason="DOI and title verified.",
                    acquisition_status="downloaded",
                )
            )
            session.add(
                ExtractionExecution(
                    source_id=src2_rejected_id,
                    status="failed",
                    error_message="HTTP 403 prevented full-text fetch.",
                    executed_at=now - timedelta(minutes=4),
                )
            )
            await session.flush()

            claim1 = Claim(
                id=claim1_id,
                investigation_id=inv1_id,
                text="Automated review tools detect boundary defects prior to merge.",
                status="moderately_supported",
            )
            claim2 = Claim(
                id=claim2_unassessed_id,
                investigation_id=inv1_id,
                text="Automated review reduces onboarding delays.",
                status="unassessed",
            )
            claim_other = Claim(
                id=claim_other_id,
                investigation_id=inv2_id,
                text="Foreign investigation claim that must never leak.",
                status="unassessed",
            )
            session.add_all([claim1, claim2, claim_other])
            await session.flush()

            ev1 = Evidence(
                id=ev1_id,
                source_id=src1_id,
                claim_id=claim1_id,
                document_id=doc1_id,
                exact_text="Automated review detected 28% more boundary defects before merge.",
                surrounding_context="Across 14 repositories, automated review detected 28% more boundary defects before merge.",
                evidence_type="supporting",
                relevance_score=0.89,
                relevance_reason="Direct empirical comparison.",
                extraction_method="pdf_sentence_match",
                page_number=4,
                section_name="Results",
                retrieval_timestamp=now - timedelta(minutes=8),
                traceable=True,
            )
            # Missing document_id, missing claim_id, missing page_number -> must not fabricate values.
            ev2 = Evidence(
                id=ev2_missing_doc_id,
                source_id=src2_rejected_id,
                claim_id=None,
                document_id=None,
                exact_text="Claimed productivity gains were anecdotal with no control group.",
                surrounding_context=None,
                evidence_type="methodological_limitation",
                relevance_score=0.35,
                relevance_reason="Missing experimental control.",
                extraction_method="snippet_fallback",
                page_number=None,
                section_name=None,
                retrieval_timestamp=now - timedelta(minutes=3),
                traceable=False,
            )
            ev_other = Evidence(
                id=ev_other_id,
                source_id=src_other_id,
                claim_id=claim_other_id,
                exact_text="Isolated second investigation passage.",
                evidence_type="supporting",
                relevance_score=0.95,
                relevance_reason="Other inv",
                extraction_method="test",
                traceable=True,
            )
            session.add_all([ev1, ev2, ev_other])
            await session.flush()

            # Add valid same-investigation relationship AND a corrupt cross-investigation relationship to verify isolation!
            session.add_all(
                [
                    ClaimEvidenceRelationship(
                        claim_id=claim1_id,
                        evidence_id=ev1_id,
                        relationship_type="supporting",
                        explanation="Matches outcome metric.",
                    ),
                    ClaimEvidenceRelationship(
                        claim_id=claim_other_id,
                        evidence_id=ev1_id,
                        relationship_type="contradicting",
                        explanation="Cross-investigation row that must stay isolated.",
                    ),
                ]
            )

            job1 = AnalysisJob(
                id=job1_id,
                investigation_id=inv1_id,
                status="researching",
                provider_kind="lm_studio",
                default_model="gemma-test",
            )
            session.add(job1)
            await session.flush()

            exec_completed = AnalysisAgentExecution(
                id=exec_completed_id,
                job_id=job1_id,
                agent_identifier="advocate",
                status="completed",
                model="gemma-test",
                token_usage_json=json.dumps(
                    {"total_tokens": 310, "queue_wait_seconds": 1.25, "inference_duration_seconds": 18.5}
                ),
                output_json=json.dumps({"arguments_created": 1}),
                started_at=now - timedelta(seconds=30),
                completed_at=now - timedelta(seconds=10),
            )
            exec_waiting = AnalysisAgentExecution(
                id=exec_waiting_id,
                job_id=job1_id,
                agent_identifier="skeptic",
                status="waiting_in_queue",
                model="gemma-test",
                token_usage_json="{}",
                started_at=now - timedelta(seconds=8),
            )
            exec_failed = AnalysisAgentExecution(
                id=exec_failed_id,
                job_id=job1_id,
                agent_identifier="temporal_intelligence",
                status="failed",
                model="gemma-test",
                token_usage_json=json.dumps({"queue_wait_seconds": 600.0}),
                error_message="Timed out waiting 600s in provider queue for lm_studio.",
                started_at=now - timedelta(seconds=610),
                completed_at=now - timedelta(seconds=10),
            )
            session.add_all([exec_completed, exec_waiting, exec_failed])
            await session.flush()

            session.add(
                AgentArgument(
                    job_id=job1_id,
                    execution_id=exec_completed_id,
                    claim_id=claim1_id,
                    agent_identifier="advocate",
                    argument_type="supporting",
                    text="Empirical evidence shows 28% improvement.",
                    evidence_ids_json=json.dumps([str(ev1_id)]),
                    source_ids_json=json.dumps([str(src1_id)]),
                    evidence_basis="direct",
                    reasoning_summary="Grounded in full-text PDF.",
                    limitations_json="[]",
                    confidence_level="moderate",
                    confidence_explanation="Single repository multi-project study.",
                )
            )
            await session.commit()
        await app_engine.dispose()

    asyncio.run(seed())
    try:
        from tests.conftest import authed_client
        with authed_client() as client:
            # 1. Evidence filtering, provenance, missing provenance handling, and isolation
            ev_resp = client.get(f"/api/v1/research/evidence?investigation_id={inv1_id}&limit=1&offset=0")
            assert ev_resp.status_code == 200
            ev_page1 = ev_resp.json()
            assert ev_page1["total"] == 2
            assert len(ev_page1["items"]) == 1
            first_ev = ev_page1["items"][0]
            assert first_ev["id"] == str(ev1_id)
            assert first_ev["document_access_level"] == "full_text"
            assert first_ev["page_number"] == 4
            assert first_ev["section_name"] == "Results"
            # Verify cross-investigation claim_other_id is never leaked via linked_claims!
            assert [link["claim_id"] for link in first_ev["linked_claims"]] == [str(claim1_id)]

            ev_page2 = client.get(f"/api/v1/research/evidence?investigation_id={inv1_id}&limit=1&offset=1")
            assert ev_page2.status_code == 200
            missing_prov_ev = ev_page2.json()["items"][0]
            assert missing_prov_ev["id"] == str(ev2_missing_doc_id)
            assert missing_prov_ev["document_id"] is None
            assert missing_prov_ev["document_url"] is None
            assert missing_prov_ev["claim_id"] is None
            assert missing_prov_ev["page_number"] is None
            assert missing_prov_ev["traceable"] is False

            # Search & classification filter
            q_resp = client.get(f"/api/v1/research/evidence?investigation_id={inv1_id}&q=anecdotal&traceable=false")
            assert q_resp.status_code == 200
            assert q_resp.json()["total"] == 1
            assert q_resp.json()["items"][0]["id"] == str(ev2_missing_doc_id)

            # Isolation & 404 check
            missing_inv = uuid.uuid4()
            assert client.get(f"/api/v1/research/evidence?investigation_id={missing_inv}").status_code == 404

            # 2. Sources filtering, OA locations, extraction errors, and pagination
            src_resp = client.get(f"/api/v1/research/sources?investigation_id={inv1_id}&sort=evidence_desc")
            assert src_resp.status_code == 200
            src_data = src_resp.json()
            assert src_data["total"] == 2
            s1, s2 = src_data["items"]
            assert s1["id"] == str(src1_id)
            assert s1["evidence_count"] == 1
            assert s1["open_access_status"] == "resolved"
            assert len(s1["open_access_locations"]) == 1
            assert s2["id"] == str(src2_rejected_id)
            assert s2["inclusion_status"] == "rejected"
            assert s2["extraction_status"] == "failed"
            assert "HTTP 403" in s2["extraction_error"]

            oa_filtered = client.get(
                f"/api/v1/research/sources?investigation_id={inv1_id}&access_level=full_text&open_access_status=resolved"
            )
            assert oa_filtered.status_code == 200
            assert [item["id"] for item in oa_filtered.json()["items"]] == [str(src1_id)]
            assert client.get(f"/api/v1/research/sources?investigation_id={missing_inv}").status_code == 404

            # 3. Agent Observatory telemetry, queue wait vs generating states, and errors
            obs_resp = client.get(f"/api/v1/agents/observatory?investigation_id={inv1_id}")
            assert obs_resp.status_code == 200
            obs = obs_resp.json()
            assert len(obs["agents"]) >= 12
            assert obs["summary"]["waiting_in_queue"] == 1
            assert obs["summary"]["completed"] == 1
            assert obs["summary"]["failed"] == 1
            assert obs["executions_total"] == 3

            execs_by_id = {item["id"]: item for item in obs["executions"]}
            assert execs_by_id[str(exec_waiting_id)]["status"] == "waiting_in_queue"
            assert execs_by_id[str(exec_completed_id)]["queue_wait_seconds"] == 1.25
            assert execs_by_id[str(exec_completed_id)]["inference_duration_seconds"] == 18.5
            assert execs_by_id[str(exec_completed_id)]["argument_count"] == 1
            assert execs_by_id[str(exec_completed_id)]["cited_evidence_count"] == 1
            assert execs_by_id[str(exec_failed_id)]["status"] == "failed"
            assert "Timed out waiting 600s" in execs_by_id[str(exec_failed_id)]["error_message"]

            queued_only = client.get(
                f"/api/v1/agents/observatory?investigation_id={inv1_id}&status=waiting_in_queue"
            )
            assert queued_only.status_code == 200
            assert [item["id"] for item in queued_only.json()["executions"]] == [str(exec_waiting_id)]
            assert client.get(f"/api/v1/agents/observatory?investigation_id={missing_inv}").status_code == 404
            client.portal.call(app_engine.dispose)
    finally:
        async def cleanup():
            async with SessionFactory() as session:
                for inv_uuid in (inv1_id, inv2_id):
                    await session.execute(delete(AnalysisJob).where(AnalysisJob.investigation_id == inv_uuid))
                    src_ids = (
                        await session.scalars(select(Source.id).where(Source.investigation_id == inv_uuid))
                    ).all()
                    if src_ids:
                        await session.execute(delete(Evidence).where(Evidence.source_id.in_(src_ids)))
                        await session.execute(delete(Document).where(Document.source_id.in_(src_ids)))
                    await session.execute(delete(Claim).where(Claim.investigation_id == inv_uuid))
                    await session.execute(delete(Source).where(Source.investigation_id == inv_uuid))
                    await session.execute(delete(Investigation).where(Investigation.id == inv_uuid))
                await session.commit()
            await app_engine.dispose()

        asyncio.run(cleanup())


@pytest.mark.asyncio
async def test_duplicate_claim_argument_triggers_retry_and_adjudicator_enforces_consistency(isolated_session):
    inv = Investigation(question="Do automated checks prevent production regressions?", mode="quick")
    isolated_session.add(inv)
    await isolated_session.flush()
    src = Source(
        investigation_id=inv.id,
        title="Regression Control Study",
        canonical_url="https://example.org/reg",
        original_url="https://example.org/reg",
        source_type="academic",
        authors_json="[]",
    )
    isolated_session.add(src)
    await isolated_session.flush()
    ev = Evidence(
        source_id=src.id,
        exact_text="Automated checks caught regressions in staging trials.",
        evidence_type="supporting",
        extraction_method="test",
        relevance_score=0.9,
        traceable=True,
    )
    isolated_session.add(ev)
    await isolated_session.flush()
    job = AnalysisJob(investigation_id=inv.id, max_debate_rounds=1)
    isolated_session.add(job)
    await isolated_session.flush()

    seen_advocate_attempts = 0
    seen_adjudicator_attempts = 0

    class _CorrectableProvider:
        async def complete(self, messages, model=None):
            nonlocal seen_advocate_attempts, seen_adjudicator_attempts
            system = messages[0]["content"]
            request = json.loads(messages[1]["content"])
            if "claims array" in system:
                return {
                    "content": json.dumps(
                        {
                            "claims": [
                                {
                                    "text": "Automated checks catch regressions before production release.",
                                    "explanation": "Evaluates pre-release defect detection.",
                                    "priority": 1,
                                    "search_objectives": ["automated checks catch regressions"],
                                    "evidence_categories": ["supporting"],
                                }
                            ]
                        }
                    ),
                    "usage": {"total_tokens": 10},
                }
            if "arguments" in system and request.get("role"):
                role = request["role"]
                claim_id = request["claims"][0]["claim_id"]
                ev_item = request["claims"][0]["evidence"][0]
                if role == "advocate":
                    seen_advocate_attempts += 1
                    if seen_advocate_attempts == 1:
                        # First attempt emits duplicate claim arguments (Issue A)
                        arg = {
                            "claim_id": claim_id,
                            "argument_type": "supporting",
                            "text": "First duplicate.",
                            "evidence_ids": [ev_item["evidence_id"]],
                            "source_ids": [ev_item["source_id"]],
                            "evidence_basis": "direct",
                            "reasoning_summary": "Grounded.",
                            "limitations": [],
                            "confidence": {"level": "weak", "explanation": "One study."},
                        }
                        return {"content": json.dumps({"arguments": [arg, arg]}), "usage": {"total_tokens": 12}}
                arg_type = {
                    "advocate": "supporting",
                    "skeptic": "qualifying",
                    "methodology_auditor": "methodological_criticism",
                    "source_intelligence": "source_criticism",
                    "citation_genealogy": "source_criticism",
                    "temporal_intelligence": "temporal_qualification",
                }[role]
                return {
                    "content": json.dumps(
                        {
                            "arguments": [
                                {
                                    "claim_id": claim_id,
                                    "argument_type": arg_type,
                                    "text": f"{role} single valid argument.",
                                    "evidence_ids": [ev_item["evidence_id"]],
                                    "source_ids": [ev_item["source_id"]],
                                    "evidence_basis": "direct",
                                    "reasoning_summary": "Grounded in single study.",
                                    "limitations": ["Small scope"],
                                    "confidence": {"level": "weak", "explanation": "Limited."},
                                }
                            ]
                        }
                    ),
                    "usage": {"total_tokens": 15},
                }
            if "round_number" in system:
                return {
                    "content": json.dumps(
                        {
                            "round_number": request["round_number"],
                            "moderator_summary": "Support exists with scope limits.",
                            "unresolved_disagreements": [],
                            "requested_follow_up": [],
                        }
                    ),
                    "usage": {"total_tokens": 10},
                }
            if "decisions array" in system:
                seen_adjudicator_attempts += 1
                claim_id = request["claims"][0]["claim_id"]
                if seen_adjudicator_attempts == 1:
                    # Issue D: bogus contradictory label with empty evidence_ids & support-only explanation!
                    return {
                        "content": json.dumps(
                            {
                                "decisions": [
                                    {
                                        "claim_id": claim_id,
                                        "decision": "contradictory",
                                        "explanation": "The claim is supported by evidence with high relevance score.",
                                        "supporting_argument_ids": [],
                                        "evidence_ids": [],
                                        "unresolved_disagreements": [],
                                    }
                                ]
                            }
                        ),
                        "usage": {"total_tokens": 10},
                    }
                arg_ids = [item["argument_id"] for item in request["arguments"]]
                return {
                    "content": json.dumps(
                        {
                            "decisions": [
                                {
                                    "claim_id": claim_id,
                                    "decision": "weakly_supported",
                                    "explanation": "Supported by one persisted staging passage with limited external replication.",
                                    "supporting_argument_ids": arg_ids[:1],
                                    "evidence_ids": [str(ev.id)],
                                    "unresolved_disagreements": [],
                                }
                            ]
                        }
                    ),
                    "usage": {"total_tokens": 14},
                }
            return {
                "content": json.dumps(
                    {
                        "sections": [
                            {
                                "section_type": "claim_finding",
                                "title": request["claims"][0]["text"],
                                "content": "Weakly supported by one persisted passage.",
                                "claim_ids": [request["claims"][0]["claim_id"]],
                                "evidence_ids": [str(ev.id)],
                            }
                        ]
                    }
                ),
                "usage": {"total_tokens": 10},
            }

        async def close(self):
            return None

    cfg = ProviderConfigRequest(kind=ProviderKind.ollama, endpoint="http://mock", model="mock", allow_local_runtime=True)
    with patch("app.analysis.service.create_provider", return_value=_CorrectableProvider()):
        await run_analysis(isolated_session, EventBroker(), job, inv.question, cfg)

    assert job.status == "completed"
    assert seen_advocate_attempts == 2
    assert seen_adjudicator_attempts == 2
    claims = (await isolated_session.scalars(select(Claim).where(Claim.investigation_id == inv.id))).all()
    assert len(claims) == 1
    assert claims[0].status == "weakly_supported"
    adv_exec = await isolated_session.scalar(
        select(AnalysisAgentExecution).where(
            AnalysisAgentExecution.job_id == job.id,
            AnalysisAgentExecution.agent_identifier == "advocate",
        )
    )
    assert adv_exec is not None
    assert adv_exec.status == "completed"
    usage = json.loads(adv_exec.token_usage_json)
    assert "inference_duration_seconds" in usage


@pytest.mark.asyncio
async def test_failed_analysis_marks_waiting_or_running_executions_failed(isolated_session):
    inv = Investigation(question="Do uncaught stage failures clean up pending executions?", mode="quick")
    isolated_session.add(inv)
    await isolated_session.flush()
    src = Source(
        investigation_id=inv.id,
        title="Test source",
        canonical_url="https://example.org/src",
        original_url="https://example.org/src",
        source_type="academic",
        authors_json="[]",
    )
    isolated_session.add(src)
    await isolated_session.flush()
    job = AnalysisJob(investigation_id=inv.id, max_debate_rounds=1)
    isolated_session.add(job)
    await isolated_session.flush()

    class _FailingModeratorProvider:
        async def complete(self, messages, model=None):
            system = messages[0]["content"]
            if "claims array" in system:
                return {
                    "content": json.dumps(
                        {
                            "claims": [
                                {
                                    "text": "Automated regression checks fail loudly when broken.",
                                    "explanation": "Test claim.",
                                    "priority": 1,
                                    "search_objectives": ["regression checks"],
                                    "evidence_categories": ["supporting"],
                                }
                            ]
                        }
                    ),
                    "usage": {},
                }
            if "round_number" in system:
                return {"content": "not valid json", "usage": {}}
            return {"content": json.dumps({"arguments": []}), "usage": {}}

        async def close(self):
            return None

    cfg = ProviderConfigRequest(kind=ProviderKind.ollama, endpoint="http://mock", model="mock", allow_local_runtime=True)
    with patch("app.analysis.service.create_provider", return_value=_FailingModeratorProvider()):
        await run_analysis(isolated_session, EventBroker(), job, inv.question, cfg)

    assert job.status == "failed"
    execs = (
        await isolated_session.scalars(select(AnalysisAgentExecution).where(AnalysisAgentExecution.job_id == job.id))
    ).all()
    assert execs
    assert all(item.status in {"completed", "failed"} for item in execs)
