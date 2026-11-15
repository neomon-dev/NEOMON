import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import SessionFactory, engine as app_engine
from app.main import app
from app.models import (
    AdjudicationDecision,
    AgentArgument,
    AnalysisAgentExecution,
    AnalysisJob,
    Base,
    Claim,
    ClaimEvidenceRelationship,
    Document,
    DocumentVersionRelationship,
    Evidence,
    Investigation,
    OpenAccessLocation,
    ResearchQuery,
    Source,
)


@pytest_asyncio.fixture
async def isolated_session(tmp_path):
    db_path = tmp_path / "graph_test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", connect_args={"timeout": 5})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


def test_knowledge_graph_endpoints_nodes_edges_filters_and_isolation():
    import asyncio

    inv1_id = uuid.uuid4()
    inv2_id = uuid.uuid4()
    src1_id = uuid.uuid4()
    src2_orphan_id = uuid.uuid4()
    src_other_id = uuid.uuid4()
    doc1_id = uuid.uuid4()
    doc2_version_id = uuid.uuid4()
    claim1_id = uuid.uuid4()
    claim2_id = uuid.uuid4()
    claim_other_id = uuid.uuid4()
    ev1_supp_id = uuid.uuid4()
    ev2_contra_id = uuid.uuid4()
    ev3_nodoc_id = uuid.uuid4()
    ev_other_id = uuid.uuid4()
    job1_id = uuid.uuid4()
    exec1_id = uuid.uuid4()
    arg1_id = uuid.uuid4()
    arg2_id = uuid.uuid4()
    dec1_id = uuid.uuid4()

    async def seed():
        now = datetime.now(UTC)
        async with SessionFactory() as session:
            inv1 = Investigation(
                id=inv1_id,
                workspace_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
                question="How does asynchronous code review affect bug escape rates?",
                mode="deep",
                status="completed",
                quality_status="strong",
                quality_summary="Multiple controlled studies examine code review and defect escapes.",
                relevant_source_count=2,
                full_text_count=2,
            )
            inv2 = Investigation(
                id=inv2_id,
                question="Completely unrelated second investigation for isolation checks?",
                mode="quick",
                status="created",
            )
            session.add_all([inv1, inv2])
            await session.flush()

            session.add(
                ResearchQuery(
                    investigation_id=inv1_id,
                    query="code review defect escape rate",
                    category="broad",
                    provider="tavily",
                )
            )

            src1 = Source(
                id=src1_id,
                investigation_id=inv1_id,
                title="Empirical Study on Pull Request Reviews",
                canonical_url="https://example.org/pr-study",
                original_url="https://example.org/pr-study",
                source_type="academic",
                publisher="ACM Transactions",
                authors_json=json.dumps(["Dr. E. Baker", "M. Stone"]),
                publication_date="2024-10-01",
                doi="10.1145/review.2024",
                relevance_score=0.94,
                relevance_reasons_json=json.dumps(["Direct defect escape measurement"]),
                inclusion_status="included",
                open_access_status="resolved",
                selected_document_url="https://repo.example.org/pr-study.pdf",
            )
            src2 = Source(
                id=src2_orphan_id,
                investigation_id=inv1_id,
                title="Industry Survey of Developer Tools",
                canonical_url="https://example.org/tools-survey",
                original_url="https://example.org/tools-survey",
                source_type="institutional",
                relevance_score=0.62,
                inclusion_status="included",
                open_access_status="metadata_only",
            )
            src_other = Source(
                id=src_other_id,
                investigation_id=inv2_id,
                title="Secret Foreign Source",
                canonical_url="https://example.org/secret",
                original_url="https://example.org/secret",
                source_type="academic",
                relevance_score=0.88,
                inclusion_status="included",
            )
            session.add_all([src1, src2, src_other])
            await session.flush()

            doc1 = Document(
                id=doc1_id,
                source_id=src1_id,
                content_type="application/pdf",
                title="Published Version of PR Study",
                content="Asynchronous reviews reduced defect escapes by 34% across 40 teams.",
                page_count=18,
                access_level="full_text",
                extraction_quality="high",
                document_url="https://repo.example.org/pr-study.pdf",
                version_type="publishedVersion",
                metadata_match_status="verified",
                retrieved_at=now - timedelta(minutes=20),
            )
            doc2 = Document(
                id=doc2_version_id,
                source_id=src1_id,
                content_type="application/pdf",
                title="Preprint Version of PR Study",
                content="Preliminary draft of PR study.",
                page_count=16,
                access_level="full_text",
                extraction_quality="medium",
                document_url="https://arxiv.example.org/pr-study.pdf",
                version_type="submittedVersion",
                retrieved_at=now - timedelta(minutes=25),
            )
            session.add_all([doc1, doc2])
            session.add(
                DocumentVersionRelationship(
                    source_id=src1_id,
                    document_id=doc1_id,
                    related_document_id=doc2_version_id,
                    relationship_type="predecessor_version",
                )
            )
            session.add(
                OpenAccessLocation(
                    source_id=src1_id,
                    url="https://repo.example.org/pr-study.pdf",
                    repository="ACM Open",
                    version_type="publishedVersion",
                    acquisition_status="downloaded",
                )
            )
            await session.flush()

            cl1 = Claim(
                id=claim1_id,
                investigation_id=inv1_id,
                text="Asynchronous code review reduces defect escape rates into production.",
                status="moderately_supported",
                priority=1,
            )
            cl2 = Claim(
                id=claim2_id,
                investigation_id=inv1_id,
                text="Turnaround latency increases defect leakage in fast-paced teams.",
                status="unassessed",
                priority=2,
            )
            cl_other = Claim(
                id=claim_other_id,
                investigation_id=inv2_id,
                text="Cross-investigation claim that must never appear in inv1 graph.",
                status="unassessed",
            )
            session.add_all([cl1, cl2, cl_other])
            await session.flush()

            ev1 = Evidence(
                id=ev1_supp_id,
                source_id=src1_id,
                claim_id=claim1_id,
                document_id=doc1_id,
                exact_text="Asynchronous reviews reduced defect escapes by 34% across 40 teams.",
                evidence_type="supporting",
                relevance_score=0.91,
                relevance_reason="Direct empirical metric match.",
                extraction_method="pdf_sentence_match",
                page_number=7,
                section_name="Empirical Findings",
                traceable=True,
            )
            ev2 = Evidence(
                id=ev2_contra_id,
                source_id=src1_id,
                claim_id=claim1_id,
                document_id=doc1_id,
                exact_text="In trivial single-line changes, review did not significantly reduce escape rates.",
                evidence_type="contradicting",
                relevance_score=0.74,
                relevance_reason="Null finding on trivial edits.",
                extraction_method="pdf_sentence_match",
                page_number=9,
                section_name="Subgroup Analysis",
                traceable=True,
            )
            # Evidence without document_id (extracted directly from source) and without page_number
            ev3 = Evidence(
                id=ev3_nodoc_id,
                source_id=src2_orphan_id,
                claim_id=claim2_id,
                document_id=None,
                exact_text="Survey respondents noted review fatigue delayed releases without catching bugs.",
                evidence_type="methodological_limitation",
                relevance_score=0.58,
                relevance_reason="Self-reported survey limitation.",
                extraction_method="html_snippet",
                page_number=None,
                section_name=None,
                traceable=True,
            )
            ev_other = Evidence(
                id=ev_other_id,
                source_id=src_other_id,
                claim_id=claim_other_id,
                exact_text="Foreign investigation passage.",
                evidence_type="supporting",
                relevance_score=0.99,
                extraction_method="test",
                traceable=True,
            )
            session.add_all([ev1, ev2, ev3, ev_other])
            await session.flush()

            session.add_all(
                [
                    ClaimEvidenceRelationship(
                        claim_id=claim1_id,
                        evidence_id=ev1_supp_id,
                        relationship_type="supporting",
                        explanation="Controlled trial finding.",
                    ),
                    ClaimEvidenceRelationship(
                        claim_id=claim1_id,
                        evidence_id=ev2_contra_id,
                        relationship_type="contradicting",
                        explanation="Subgroup null result.",
                    ),
                    # Foreign relationship that must be filtered out for isolation
                    ClaimEvidenceRelationship(
                        claim_id=claim_other_id,
                        evidence_id=ev_other_id,
                        relationship_type="supporting",
                        explanation="Foreign relationship.",
                    ),
                ]
            )

            job1 = AnalysisJob(
                id=job1_id,
                investigation_id=inv1_id,
                status="completed",
                provider_kind="lm_studio",
                default_model="gemma-coder",
            )
            session.add(job1)
            await session.flush()

            exec1 = AnalysisAgentExecution(
                id=exec1_id,
                job_id=job1_id,
                agent_identifier="advocate",
                status="completed",
                model="gemma-coder",
            )
            session.add(exec1)
            await session.flush()

            arg1 = AgentArgument(
                id=arg1_id,
                job_id=job1_id,
                execution_id=exec1_id,
                claim_id=claim1_id,
                agent_identifier="advocate",
                argument_type="supporting",
                text="Advocate: empirical evidence confirms a 34% reduction in production escapes.",
                evidence_ids_json=json.dumps([str(ev1_supp_id)]),
                source_ids_json=json.dumps([str(src1_id)]),
                evidence_basis="direct",
                reasoning_summary="Supported by 40-team controlled study.",
                limitations_json="[]",
                confidence_level="strong",
                confidence_explanation="High source quality.",
            )
            arg2 = AgentArgument(
                id=arg2_id,
                job_id=job1_id,
                execution_id=exec1_id,
                claim_id=claim1_id,
                agent_identifier="skeptic",
                argument_type="contradicting",
                text="Skeptic: trivial edits showed no defect escape reduction.",
                evidence_ids_json=json.dumps([str(ev2_contra_id)]),
                source_ids_json=json.dumps([str(src1_id)]),
                evidence_basis="direct",
                reasoning_summary="Null finding subgroup.",
                limitations_json="[]",
                confidence_level="moderate",
                confidence_explanation="Subgroup limitation.",
            )
            dec1 = AdjudicationDecision(
                id=dec1_id,
                job_id=job1_id,
                claim_id=claim1_id,
                decision="moderately_supported",
                explanation="Strong defect reduction overall, qualified by no effect on trivial changes.",
                supporting_argument_ids_json=json.dumps([str(arg1_id), str(arg2_id)]),
                evidence_ids_json=json.dumps([str(ev1_supp_id), str(ev2_contra_id)]),
                unresolved_disagreements_json=json.dumps(["Effect on trivial edits remains bounded."]),
            )
            session.add_all([arg1, arg2, dec1])
            await session.commit()
        await app_engine.dispose()

    asyncio.run(seed())
    try:
        from tests.conftest import authed_client
        with authed_client() as client:
            # 1. Full investigation graph retrieval
            resp = client.get(f"/api/v1/research/investigations/{inv1_id}/graph?expand_all=true")
            assert resp.status_code == 200
            data = resp.json()
            assert data["investigation_id"] == str(inv1_id)
            assert data["investigation_status"] == "completed"
            assert data["total_counts"]["claims"] == 2
            assert data["total_counts"]["evidence"] == 3
            assert data["total_counts"]["documents"] == 2
            assert data["total_counts"]["sources"] == 2
            assert data["total_counts"]["arguments"] == 2
            assert data["total_counts"]["decisions"] == 1

            nodes_by_id = {node["id"]: node for node in data["nodes"]}
            edges_by_id = {edge["id"]: edge for edge in data["edges"]}

            # Verify node types present
            expected_node_types = {
                "investigation",
                "research_question",
                "claim",
                "evidence",
                "document",
                "source",
                "agent_argument",
                "adjudication_decision",
            }
            assert {node["type"] for node in data["nodes"]} == expected_node_types

            # Verify node stability & metadata
            claim_node = nodes_by_id[f"claim:{claim1_id}"]
            assert claim_node["status"] == "moderately_supported"
            assert claim_node["metadata"]["supporting_evidence"][0]["id"] == str(ev1_supp_id)
            assert claim_node["metadata"]["contradicting_evidence"][0]["id"] == str(ev2_contra_id)
            assert claim_node["metadata"]["adjudication_decision"]["decision"] == "moderately_supported"

            evidence_nodoc = nodes_by_id[f"evidence:{ev3_nodoc_id}"]
            assert "missing_document" in evidence_nodoc["missing_provenance"]
            assert "missing_page_number" in evidence_nodoc["missing_provenance"]
            assert evidence_nodoc["metadata"]["document_id"] is None
            assert evidence_nodoc["metadata"]["page_number"] is None

            # Verify relationship distinctions on edges
            edge_rels = {edge["relationship_type"] for edge in data["edges"]}
            assert "supports" in edge_rels
            assert "contradicts" in edge_rels
            assert "methodological_limitation" in edge_rels
            assert "evidenced_in" in edge_rels
            assert "published_by" in edge_rels
            assert "document_version" in edge_rels
            assert "adjudicated_by" in edge_rels
            assert "weighs_argument" in edge_rels
            assert "extracted_from_source" in edge_rels

            # Verify direct source edge when document is missing
            nodoc_edge_id = f"evidence:{ev3_nodoc_id}->source:{src2_orphan_id}:extracted_from_source"
            assert nodoc_edge_id in edges_by_id

            # Verify version relationship edge
            version_edge_id = f"document:{doc1_id}->document:{doc2_version_id}:document_version"
            assert version_edge_id in edges_by_id

            # 2. Strict investigation isolation: no inv2 nodes or edges leaked
            inv2_entities = {str(inv2_id), str(src_other_id), str(claim_other_id), str(ev_other_id)}
            for node in data["nodes"]:
                assert str(node["entity_id"]) not in inv2_entities
                assert str(node["investigation_id"]) == str(inv1_id)
            for edge in data["edges"]:
                for inv2_item in inv2_entities:
                    assert inv2_item not in edge["source"]
                    assert inv2_item not in edge["target"]

            # 3. Progressive expansion via focus_node_id
            focus_claim_resp = client.get(
                f"/api/v1/research/graph?investigation_id={inv1_id}&focus_node_id=claim:{claim1_id}"
            )
            assert focus_claim_resp.status_code == 200
            focus_data = focus_claim_resp.json()
            focus_node_types = {node["type"] for node in focus_data["nodes"]}
            assert "claim" in focus_node_types
            assert "evidence" in focus_node_types
            # Claim 2 is omitted in focused claim slice
            assert f"claim:{claim2_id}" not in {node["id"] for node in focus_data["nodes"]}

            # 4. Filtering by node_types and relationship_types
            filtered_resp = client.get(
                f"/api/v1/research/graph?investigation_id={inv1_id}&node_types=claim,evidence&relationship_types=supports"
            )
            assert filtered_resp.status_code == 200
            filt_data = filtered_resp.json()
            assert all(node["type"] in {"claim", "evidence"} for node in filt_data["nodes"])
            assert all(edge["relationship_type"] == "supports" for edge in filt_data["edges"])

            # 5. Search query filtering
            search_resp = client.get(f"/api/v1/research/graph?investigation_id={inv1_id}&q=escape")
            assert search_resp.status_code == 200
            search_data = search_resp.json()
            assert len(search_data["nodes"]) >= 2
            assert all(
                "escape" in (n["label"] + " " + n["description"] + " " + n["status"]).casefold()
                for n in search_data["nodes"]
            )

            # 6. Default route without investigation_id selects most recent investigation
            default_resp = client.get("/api/v1/research/graph")
            assert default_resp.status_code == 200
            assert default_resp.json()["investigation_id"] is not None
            assert "nodes" in default_resp.json()
            assert "edges" in default_resp.json()

            # 7. Nonexistent investigation returns 404
            assert client.get(f"/api/v1/research/graph?investigation_id={uuid.uuid4()}").status_code == 404

            # 8. Empty investigation returns empty state reason without crashing
            empty_resp = client.get(f"/api/v1/research/graph?investigation_id={inv2_id}")
            assert empty_resp.status_code == 200
            empty_data = empty_resp.json()
            assert empty_data["empty_reason"] is None or "not persisted" in empty_data["empty_reason"]
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
                        await session.execute(delete(OpenAccessLocation).where(OpenAccessLocation.source_id.in_(src_ids)))
                    await session.execute(delete(Claim).where(Claim.investigation_id == inv_uuid))
                    await session.execute(delete(ResearchQuery).where(ResearchQuery.investigation_id == inv_uuid))
                    await session.execute(delete(Source).where(Source.investigation_id == inv_uuid))
                    await session.execute(delete(Investigation).where(Investigation.id == inv_uuid))
                await session.commit()
            await app_engine.dispose()

        asyncio.run(cleanup())
