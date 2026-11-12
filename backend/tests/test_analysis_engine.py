import json
import uuid
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import select

from app.analysis.protocol import ArgumentPayload, ArgumentType, ConfidenceAssessment
from app.analysis.service import _add_argument, _associate_evidence, _validate_planner_claims, run_analysis
from app.db import SessionFactory
from app.events import EventBroker
from app.models import (
    AnalysisAgentExecution,
    AnalysisJob,
    Claim,
    ClaimEvidenceRelationship,
    Evidence,
    Investigation,
    Source,
)
from app.schemas import ProviderConfigRequest, ProviderKind


@pytest_asyncio.fixture
async def async_session():
    from app.db import Base, engine
    import app.models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionFactory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


def test_argument_protocol_rejects_unknown_argument_types():
    with pytest.raises(ValueError):
        ArgumentPayload(
            claim_id=uuid.uuid4(),
            argument_type="invented",
            text="This is not a valid structured argument.",
            reasoning_summary="invalid",
            confidence=ConfidenceAssessment(level="weak", explanation="invalid"),
        )


@pytest.mark.asyncio
async def test_argument_persistence_rejects_nonexistent_evidence(async_session):
    investigation = Investigation(question="How does automation affect developer productivity?", mode="quick")
    async_session.add(investigation)
    await async_session.flush()
    claim = Claim(investigation_id=investigation.id, text=investigation.question)
    async_session.add(claim)
    source = Source(
        investigation_id=investigation.id,
        title="A source",
        canonical_url="https://example.org/source",
        original_url="https://example.org/source",
        source_type="academic",
        authors_json="[]",
    )
    async_session.add(source)
    await async_session.flush()
    job = AnalysisJob(investigation_id=investigation.id)
    execution = AnalysisAgentExecution(job=job, agent_identifier="advocate", status="running")
    async_session.add(execution)
    await async_session.flush()
    payload = ArgumentPayload(
        claim_id=claim.id,
        argument_type=ArgumentType.supporting,
        text="This argument cites an evidence identifier that was not persisted.",
        reasoning_summary="The reference must be rejected.",
        evidence_ids=[uuid.uuid4()],
        confidence=ConfidenceAssessment(level="insufficient", explanation="No valid evidence exists."),
    )
    with pytest.raises(ValueError, match="outside"):
        await _add_argument(async_session, job, execution, claim, "advocate", payload, set(), {source.id})


def test_report_citations_are_serializable():
    evidence_id = uuid.uuid4()
    payload = {"evidence_ids": [str(evidence_id)]}
    assert json.loads(json.dumps(payload))["evidence_ids"] == [str(evidence_id)]


def test_planner_rejects_duplicate_claims():
    duplicate = {
        "claims": [
            {
                "text": "AI tools improve software developer productivity.",
                "explanation": "Measures the reported effect.",
                "priority": 1,
                "search_objectives": ["AI developer productivity outcome"],
                "evidence_categories": ["supporting"],
            },
            {
                "text": "AI tools improve software developer productivity.",
                "explanation": "Repeats the same claim.",
                "priority": 2,
                "search_objectives": ["developer productivity"],
                "evidence_categories": ["supporting"],
            },
        ]
    }
    with pytest.raises(ValueError, match="duplicate"):
        _validate_planner_claims(duplicate)


@pytest.mark.asyncio
async def test_claim_evidence_association_is_claim_specific(async_session):
    investigation = Investigation(question="How do AI tools affect developers?", mode="quick")
    async_session.add(investigation)
    await async_session.flush()
    source = Source(
        investigation_id=investigation.id,
        title="Productivity study",
        canonical_url="https://example.org/study",
        original_url="https://example.org/study",
        source_type="academic",
        authors_json="[]",
    )
    async_session.add(source)
    await async_session.flush()
    claims = [
        Claim(
            investigation_id=investigation.id,
            text="AI tools improve developer productivity.",
            search_objectives_json='["developer productivity"]',
        ),
        Claim(
            investigation_id=investigation.id,
            text="AI tools change software defect rates.",
            search_objectives_json='["software defect rates"]',
        ),
    ]
    async_session.add_all(claims)
    await async_session.flush()
    evidence = [
        Evidence(
            source_id=source.id,
            exact_text="AI tools improved developer productivity in the measured task.",
            evidence_type="supporting",
            extraction_method="test",
            relevance_score=0.8,
            traceable=True,
        ),
        Evidence(
            source_id=source.id,
            exact_text="The study reported no change in software defect rates.",
            evidence_type="contradicting",
            extraction_method="test",
            relevance_score=0.8,
            traceable=True,
        ),
    ]
    async_session.add_all(evidence)
    await async_session.flush()
    associated = await _associate_evidence(async_session, investigation.id, claims, evidence)
    assert [item.id for item in associated[claims[0].id]] == [evidence[0].id]
    assert [item.id for item in associated[claims[1].id]] == [evidence[1].id]
    relationships = (
        await async_session.scalars(
            select(ClaimEvidenceRelationship).where(
                ClaimEvidenceRelationship.claim_id.in_([item.id for item in claims])
            )
        )
    ).all()
    assert {(item.claim_id, item.evidence_id) for item in relationships} == {
        (claims[0].id, evidence[0].id),
        (claims[1].id, evidence[1].id),
    }


class _MockAnalysisProvider:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def complete(self, messages, model=None):
        system = messages[0]["content"]
        request = json.loads(messages[1]["content"])
        self.calls.append((system, request))
        if "claims array" in system:
            response = {
                "claims": [
                    {
                        "text": "AI coding assistants improve developer productivity.",
                        "explanation": "Tests the direction of the reported productivity effect.",
                        "priority": 1,
                        "search_objectives": ["AI coding assistants developer productivity"],
                        "evidence_categories": ["supporting", "contradicting"],
                    },
                    {
                        "text": "AI coding assistants alter software defect rates.",
                        "explanation": "Tests a distinct quality outcome.",
                        "priority": 2,
                        "search_objectives": ["AI coding assistants software defects"],
                        "evidence_categories": ["supporting", "contradicting"],
                    },
                ]
            }
        elif "arguments" in system and request.get("role"):
            arguments = []
            for claim in request["claims"]:
                evidence = claim["evidence"]
                selected = evidence[:1]
                role = request["role"]
                argument_type = {
                    "advocate": "supporting",
                    "skeptic": "contradicting",
                    "methodology_auditor": "methodological_criticism",
                    "source_intelligence": "source_criticism",
                    "citation_genealogy": "source_criticism",
                    "temporal_intelligence": "temporal_qualification",
                }[role]
                arguments.append(
                    {
                        "claim_id": claim["claim_id"],
                        "argument_type": argument_type,
                        "text": f"{role} assessment grounded in the supplied passage.",
                        "evidence_ids": [item["evidence_id"] for item in selected],
                        "source_ids": [item["source_id"] for item in selected],
                        "evidence_basis": "direct" if selected else "none",
                        "reasoning_summary": "Only supplied persisted evidence was considered.",
                        "limitations": ["The mocked provider does not infer unavailable details."],
                        "confidence": {"level": "weak", "explanation": "Limited test evidence."},
                    }
                )
            response = {"arguments": arguments}
        elif "round_number" in system:
            response = {
                "round_number": request["round_number"],
                "moderator_summary": "The supplied Advocate and Skeptic passages disagree on direction.",
                "unresolved_disagreements": ["The effect direction remains unresolved."],
                "requested_follow_up": ["Compare study populations and outcome definitions."],
            }
        elif "decisions array" in system:
            decisions = []
            for claim in request["claims"]:
                claim_arguments = [item for item in request["arguments"] if item["claim_id"] == claim["claim_id"]]
                evidence_ids = [
                    evidence_id
                    for item in claim_arguments
                    for evidence_id in item["evidence_ids"]
                ]
                decisions.append(
                    {
                        "claim_id": claim["claim_id"],
                        "decision": "contradictory",
                        "explanation": "The supplied supporting and challenging evidence differ in direction.",
                        "supporting_argument_ids": [item["argument_id"] for item in claim_arguments],
                        "evidence_ids": list(dict.fromkeys(evidence_ids)),
                        "unresolved_disagreements": ["The disagreement cannot be resolved from this corpus."],
                    }
                )
            response = {"decisions": decisions}
        else:
            first_evidence = request["evidence"][0]["evidence_id"]
            response = {
                "sections": [
                    {
                        "section_type": "claim_finding",
                        "title": request["claims"][0]["text"],
                        "content": "The finding remains contested in the supplied evidence.",
                        "claim_ids": [request["claims"][0]["claim_id"]],
                        "evidence_ids": [first_evidence],
                    }
                ]
            }
        return {"content": json.dumps(response), "usage": {"total_tokens": 1}, "model": model or "mock"}

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_provider_workflow_runs_independent_roles_and_persists_claims(async_session):
    investigation = Investigation(question="What are the effects of AI on developers?", mode="quick")
    async_session.add(investigation)
    await async_session.flush()
    source = Source(
        investigation_id=investigation.id,
        title="AI developer study",
        canonical_url="https://example.org/ai-study",
        original_url="https://example.org/ai-study",
        source_type="academic",
        authors_json="[]",
    )
    async_session.add(source)
    await async_session.flush()
    async_session.add_all(
        [
            Evidence(
                source_id=source.id,
                exact_text="AI coding assistants improved developer productivity in the measured task.",
                evidence_type="supporting",
                extraction_method="test",
                relevance_score=0.9,
                traceable=True,
            ),
            Evidence(
                source_id=source.id,
                exact_text="AI coding assistants did not improve developer productivity in the replication.",
                evidence_type="contradicting",
                extraction_method="test",
                relevance_score=0.8,
                traceable=True,
            ),
        ]
    )
    await async_session.flush()
    job = AnalysisJob(investigation_id=investigation.id, max_debate_rounds=2)
    async_session.add(job)
    await async_session.flush()
    provider = _MockAnalysisProvider()
    config = ProviderConfigRequest(kind=ProviderKind.ollama, endpoint="http://mock", model="mock")
    with patch("app.analysis.service.create_provider", return_value=provider):
        await run_analysis(async_session, EventBroker(), job, investigation.question, config)
    assert job.status == "completed", (job.error_message, provider.calls)
    executions = (
        await async_session.scalars(
            select(AnalysisAgentExecution).where(AnalysisAgentExecution.job_id == job.id)
        )
    ).all()
    identifiers = {item.agent_identifier for item in executions}
    assert {"intelligence_planner", "advocate", "skeptic", "debate_moderator", "conflict_adjudicator", "report_intelligence"} <= identifiers
    role_prompts = {request["role"] for system, request in provider.calls if "arguments" in system and request.get("role")}
    assert "advocate" in role_prompts and "skeptic" in role_prompts
    role_system_prompts = {
        request["role"]: system
        for system, request in provider.calls
        if "arguments" in system and request.get("role")
    }
    assert len(set(role_system_prompts.values())) == 6
    assert "Advocate agent" in role_system_prompts["advocate"]
    assert "Skeptic agent" in role_system_prompts["skeptic"]
    moderator_calls = [
        request for system, request in provider.calls if "round_number" in system
    ]
    assert [item["round_number"] for item in moderator_calls] == [1, 2]
    adjudicator_calls = [
        request for system, request in provider.calls if "decisions array" in system
    ]
    assert adjudicator_calls
    assert all("evidence" in item for item in adjudicator_calls)
    decisions = (
        await async_session.scalars(
            select(AnalysisAgentExecution).where(
                AnalysisAgentExecution.job_id == job.id,
                AnalysisAgentExecution.agent_identifier == "conflict_adjudicator",
            )
        )
    ).all()
    assert decisions[0].status == "completed"


@pytest.mark.asyncio
async def test_analysis_manager_cancel_handles_uuid_strings(async_session):
    from contextlib import asynccontextmanager
    from app.analysis.manager import AnalysisManager

    investigation = Investigation(question="Can cancel handle UUID strings?", mode="quick")
    async_session.add(investigation)
    await async_session.flush()
    job = AnalysisJob(investigation_id=investigation.id, status="queued")
    async_session.add(job)
    await async_session.flush()

    @asynccontextmanager
    async def fake_session_factory():
        yield async_session

    manager = AnalysisManager(EventBroker())
    with patch("app.analysis.manager.SessionFactory", fake_session_factory):
        assert await manager.cancel(str(job.id)) is True
        assert await manager.cancel("not-a-uuid") is False
    assert job.cancel_requested is True
    assert job.status == "cancelled"


def test_analysis_api_claims_arguments_rerun_and_cancel_endpoints():
    import asyncio
    from fastapi.testclient import TestClient
    from app.db import SessionFactory, engine
    from app.main import app
    from app.models import Evidence, Investigation, Source

    async def seed():
        async with SessionFactory() as session:
            investigation = Investigation(question="Do typed contracts improve reliability?", mode="quick")
            session.add(investigation)
            await session.flush()
            source = Source(
                investigation_id=investigation.id,
                title="Typed Contracts Study",
                canonical_url="https://example.org/contracts",
                original_url="https://example.org/contracts",
                source_type="academic",
                authors_json="[]",
            )
            session.add(source)
            await session.flush()
            evidence = Evidence(
                source_id=source.id,
                exact_text="Typed contracts reduced integration defects in controlled trials.",
                evidence_type="supporting",
                extraction_method="test",
                relevance_score=0.9,
                traceable=True,
            )
            session.add(evidence)
            await session.commit()
            inv_id = str(investigation.id)
        await engine.dispose()
        return inv_id

    inv_id = asyncio.run(seed())
    try:
        with TestClient(app) as client:
            with patch("app.analysis.manager.AnalysisManager.schedule"):
                start_resp = client.post(
                    f"/api/v1/research/investigations/{inv_id}/analysis",
                    json={"max_debate_rounds": 2, "max_concurrent_agents": 2},
                )
                assert start_resp.status_code == 202
                job_data = start_resp.json()
                assert job_data["provider_kind"] is None
                job_id = job_data["id"]

                cancel_resp = client.post(f"/api/v1/research/analysis/{job_id}/cancel")
                assert cancel_resp.status_code == 200
                assert cancel_resp.json()["cancel_requested"] is True
                assert cancel_resp.json()["status"] == "cancelled"

                rerun_resp = client.post(
                    f"/api/v1/research/investigations/{inv_id}/analysis",
                    json={
                        "max_debate_rounds": 2,
                        "max_concurrent_agents": 2,
                        "provider": {
                            "kind": "ollama",
                            "endpoint": "http://127.0.0.1:11434",
                            "model": "llama3.2",
                            "allow_local_runtime": True,
                        },
                    },
                )
                assert rerun_resp.status_code == 202
                assert rerun_resp.json()["provider_kind"] == "ollama"
                assert rerun_resp.json()["default_model"] == "llama3.2"
                assert rerun_resp.json()["status"] == "queued"

                claims_resp = client.get(f"/api/v1/research/analysis/{job_id}/claims")
                args_resp = client.get(f"/api/v1/research/analysis/{job_id}/arguments")
                assert claims_resp.status_code == 200
                assert args_resp.status_code == 200
            client.portal.call(engine.dispose)
    finally:
        async def cleanup():
            from sqlalchemy import delete, select
            from app.models import AnalysisJob, Evidence, Source
            inv_uuid = uuid.UUID(inv_id)
            async with SessionFactory() as session:
                await session.execute(delete(AnalysisJob).where(AnalysisJob.investigation_id == inv_uuid))
                source_ids = (
                    await session.scalars(select(Source.id).where(Source.investigation_id == inv_uuid))
                ).all()
                if source_ids:
                    await session.execute(delete(Evidence).where(Evidence.source_id.in_(source_ids)))
                await session.execute(delete(Source).where(Source.investigation_id == inv_uuid))
                await session.execute(delete(Investigation).where(Investigation.id == inv_uuid))
                await session.commit()
            await engine.dispose()

        asyncio.run(cleanup())


def test_duplicate_analysis_start_returns_409_conflict():
    import asyncio
    from fastapi.testclient import TestClient
    from app.db import SessionFactory, engine
    from app.main import app
    from app.models import AnalysisJob, Investigation

    async def seed():
        async with SessionFactory() as session:
            inv = Investigation(question="Does duplicate analysis start fail cleanly?", mode="quick")
            session.add(inv)
            await session.flush()
            session.add(AnalysisJob(investigation_id=inv.id, status="planning"))
            await session.commit()
            inv_id = str(inv.id)
        await engine.dispose()
        return inv_id

    inv_id = asyncio.run(seed())
    try:
        with TestClient(app) as client:
            conflict = client.post(
                f"/api/v1/research/investigations/{inv_id}/analysis",
                json={"max_debate_rounds": 2, "max_concurrent_agents": 2},
            )
            assert conflict.status_code == 409
            assert conflict.json()["error"] == "analysis_active"
            client.portal.call(engine.dispose)
    finally:
        async def cleanup():
            from sqlalchemy import delete
            inv_uuid = uuid.UUID(inv_id)
            async with SessionFactory() as session:
                await session.execute(delete(AnalysisJob).where(AnalysisJob.investigation_id == inv_uuid))
                await session.execute(delete(Investigation).where(Investigation.id == inv_uuid))
                await session.commit()
            await engine.dispose()

        asyncio.run(cleanup())


@pytest.mark.asyncio
async def test_backend_restart_recovery_handles_rule_based_provider_and_stale_investigations(async_session):
    from contextlib import asynccontextmanager
    from app.analysis.manager import AnalysisManager

    stale_inv = Investigation(question="Stale running investigation?", mode="quick", status="running")
    provider_inv = Investigation(question="Provider analysis interrupted?", mode="quick", status="completed")
    rule_inv = Investigation(question="Rule-based analysis interrupted?", mode="quick", status="completed")
    cancel_inv = Investigation(question="Cancelled analysis interrupted?", mode="quick", status="completed")
    async_session.add_all([stale_inv, provider_inv, rule_inv, cancel_inv])
    await async_session.flush()

    provider_job = AnalysisJob(
        investigation_id=provider_inv.id, status="researching", provider_kind="ollama", default_model="llama3"
    )
    rule_job = AnalysisJob(investigation_id=rule_inv.id, status="debating", provider_kind=None)
    cancel_job = AnalysisJob(investigation_id=cancel_inv.id, status="planning", cancel_requested=True)
    async_session.add_all([provider_job, rule_job, cancel_job])
    await async_session.flush()

    @asynccontextmanager
    async def fake_session_factory():
        yield async_session

    manager = AnalysisManager(EventBroker())
    scheduled: list[str] = []
    with (
        patch("app.analysis.manager.SessionFactory", fake_session_factory),
        patch.object(manager, "schedule", side_effect=lambda jid, *_: scheduled.append(jid)),
    ):
        await manager.recover()

    assert stale_inv.status == "failed"
    assert "backend restart" in (stale_inv.evidence_gap or "").lower()
    assert provider_job.status == "failed"
    assert "re-enter provider credentials" in (provider_job.error_message or "").lower()
    assert cancel_job.status == "cancelled"
    assert rule_job.status == "queued"
    assert str(rule_job.id) in scheduled
