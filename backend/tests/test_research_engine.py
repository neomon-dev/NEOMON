import pytest

from app.research.evidence import extract_evidence
from app.research.normalization import deduplicate_results, normalize_url
from app.research.open_access import assess_location, normalize_doi
from app.research.query_planner import generate_queries
from app.research.providers import OpenAccessLocation, SearchResult
from app.research.relevance import assess_result
from app.research.retrieval import RetrievalError, _HTMLTextParser, retrieve_document
from app.schemas import ResearchMode


def test_query_planner_deduplicates_and_adds_deep_strategies():
    queries = generate_queries("impact of solar energy", ResearchMode.deep, "since 2020")
    assert len(queries) == 7
    assert {query.category for query in queries} == {
        "broad",
        "primary",
        "academic",
        "counter_evidence",
        "institutional",
        "methodology",
    }


def test_normalization_removes_tracking_query_parameters():
    assert normalize_url("HTTPS://Example.com/path/?utm_source=x&valid=1#fragment") == "https://example.com/path?valid=1"


def test_source_deduplication_preserves_first_result():
    results = [
        SearchResult(title="A Study", url="https://example.com/a?utm_source=x"),
        SearchResult(title="A Study", url="https://example.com/b"),
    ]
    assert len(deduplicate_results(results)) == 1


def test_relevant_software_research_ranks_above_medical_research():
    question = "What are the effects of artificial intelligence on software developer productivity?"
    relevant = SearchResult(
        title="GitHub Copilot and software developer productivity: a controlled study",
        url="https://example.com/copilot",
        snippet="We measure developer task completion time, code quality, and defects in a controlled experiment.",
        source_type="academic",
    )
    irrelevant = SearchResult(
        title="Artificial intelligence for ECG diagnosis in nursing education",
        url="https://example.com/medical",
        snippet="This study evaluates diagnostic accuracy and clinical training outcomes.",
        source_type="academic",
    )
    assert assess_result(question, relevant).score > assess_result(question, irrelevant).score
    assert assess_result(question, irrelevant).status == "rejected"


def test_html_parser_excludes_publisher_chrome_but_keeps_abstract():
    parser = _HTMLTextParser()
    parser.feed(
        "<html><body><nav>Browse journals</nav><main><h1>Study title</h1>"
        "<div class='abstract'><p>Developers completed tasks faster with the coding assistant.</p></div>"
        "<footer>Copyright notice and privacy policy</footer></main></body></html>"
    )
    extracted = " ".join(text for _, text in parser.parts)
    assert "Developers completed tasks faster" in extracted
    assert "Browse journals" not in extracted
    assert "Copyright notice" not in extracted


def test_evidence_contains_only_retrieved_sentences():
    evidence = extract_evidence(
        "Solar energy lowered costs in the trial. This sentence is unrelated. "
        "The study reports solar energy adoption increased after 2020.",
        "solar energy adoption",
    )
    assert evidence
    assert all(item.exact_text in item.surrounding_context for item in evidence)
    assert all("solar" in item.exact_text.casefold() for item in evidence)


def test_evidence_preserves_pages_and_classifies_findings():
    evidence = extract_evidence(
        "",
        "AI coding assistants affect software developer productivity",
        passages=[
            (2, "Developers completed tasks faster with the assistant in the controlled experiment.", "Results"),
            (3, "The study found no significant improvement in code quality.", "Limitations"),
        ],
    )
    assert evidence[0].page_number == 2
    assert {item.evidence_type for item in evidence} == {"supporting", "contradicting"}
    assert all(item.exact_text in item.surrounding_context for item in evidence)


def test_generic_ai_productivity_result_without_developers_is_not_relevant():
    assessment = assess_result(
        "What are the effects of artificial intelligence on software developer productivity?",
        SearchResult(
            title="Artificial intelligence and productivity in hospital administration",
            url="https://example.com/hospital",
            snippet="Productivity improved for administrative workers after automation.",
        ),
    )
    assert assessment.status in {"low_relevance", "rejected"}


def test_open_access_candidate_requires_matching_metadata():
    result = SearchResult(
        title="GitHub Copilot and software developer productivity",
        url="https://doi.org/10.1000/example",
        doi="10.1000/example",
        authors=["Ada Lovelace"],
        publication_date="2024",
    )
    matching = OpenAccessLocation(
        url="https://repository.example.edu/copilot.pdf",
        repository="Institutional repository",
        version_type="accepted_manuscript",
        doi="https://doi.org/10.1000/example",
        title=result.title,
        authors=["Ada Lovelace"],
        publication_date="2024",
    )
    incorrect = OpenAccessLocation(
        url="https://repository.example.edu/medical.pdf",
        title="AI-assisted ECG diagnosis",
        authors=["Grace Hopper"],
        publication_date="2021",
    )
    assert normalize_doi(matching.doi) == "10.1000/example"
    assert assess_location(result, matching).status == "matched"
    assert assess_location(result, incorrect).status == "rejected"


def test_arxiv_or_repository_copy_is_a_version_not_a_new_study():
    result = SearchResult(
        title="AI coding assistants and developers",
        url="https://doi.org/10.1000/study",
        doi="10.1000/study",
    )
    location = OpenAccessLocation(
        url="https://arxiv.org/pdf/2401.00001.pdf",
        repository="arXiv",
        version_type="preprint",
        doi="10.1000/study",
        title=result.title,
    )
    assert assess_location(result, location).status == "matched"
    assert location.version_type == "preprint"


@pytest.mark.asyncio
async def test_retrieval_rejects_private_hosts():
    with pytest.raises(RetrievalError, match="Private"):
        await retrieve_document("http://127.0.0.1:8000/private")


def test_research_api_validates_question(client):
    response = client.post("/api/v1/research/investigations", json={"question": "short"})
    assert response.status_code == 422
    assert response.json()["error"] == "validation_error"


@pytest.mark.asyncio
async def test_openalex_reconstructs_inverted_index_in_order():
    from unittest.mock import AsyncMock
    import httpx
    from app.research.providers import OpenAlexProvider, SearchQuery

    payload = {
        "results": [
            {
                "title": "Ordered Abstract Study",
                "doi": "https://doi.org/10.1000/ordered",
                "publication_date": "2025-01-15",
                "abstract_inverted_index": {
                    "study": [1, 5],
                    "This": [0],
                    "shows": [2],
                    "clear": [3],
                    "evidence": [4],
                    "results.": [6],
                },
                "authorships": [],
                "locations": [],
            }
        ]
    }
    provider = OpenAlexProvider()
    provider.request_json = AsyncMock(return_value=payload)
    try:
        results = await provider.search(SearchQuery("ordered abstract", "core"), limit=5)
    finally:
        await provider.close()
    assert len(results) == 1
    assert results[0].snippet == "This study shows clear evidence study results."


def test_refresh_source_persists_orm_document_and_enforces_investigation_scope():
    import asyncio
    import uuid
    from unittest.mock import AsyncMock, patch
    from fastapi.testclient import TestClient
    from app.db import SessionFactory, engine
    from app.main import app
    from app.models import Investigation, Source
    from app.research.retrieval import RetrievedDocument

    async def seed():
        async with SessionFactory() as session:
            investigation = Investigation(question="How does source refresh work?", mode="quick")
            other_investigation = Investigation(question="Other investigation?", mode="quick")
            session.add_all([investigation, other_investigation])
            await session.flush()
            source = Source(
                investigation_id=investigation.id,
                title="Refreshable Source",
                canonical_url="https://example.org/paper",
                original_url="https://example.org/paper",
                source_type="academic",
                authors_json="[]",
            )
            session.add(source)
            await session.commit()
            ids = (str(investigation.id), str(other_investigation.id), str(source.id))
        await engine.dispose()
        return ids

    inv_id, other_id, src_id = asyncio.run(seed())
    try:
        from tests.conftest import authed_client
        with authed_client() as client:
            retrieved = RetrievedDocument(
                url="https://example.org/paper",
                final_url="https://example.org/paper.pdf",
                content_type="application/pdf",
                title="Refreshable Source",
                content="Refreshed full text content from PDF.",
                headings=[],
                passages=[(1, "Refreshed full text content from PDF.", None)],
                access_level="full_text",
                extraction_quality="high",
                page_count=1,
            )
            with patch("app.routers.research.retrieve_document", new=AsyncMock(return_value=retrieved)):
                wrong_scope = client.post(f"/api/v1/research/sources/{src_id}/refresh?investigation_id={other_id}")
                assert wrong_scope.status_code == 404
                ok_response = client.post(f"/api/v1/research/sources/{src_id}/refresh?investigation_id={inv_id}")
                assert ok_response.status_code == 200
                data = ok_response.json()
                assert data["access_level"] == "full_text"
                assert data["extraction_quality"] == "high"
                assert data["document_url"] == "https://example.org/paper.pdf"

            list_response = client.get("/api/v1/research/investigations")
            assert list_response.status_code == 200
            matched = [item for item in list_response.json() if item["id"] == inv_id]
            assert len(matched) == 1
            assert matched[0]["source_count"] == 1
            client.portal.call(engine.dispose)
    finally:
        async def cleanup():
            from sqlalchemy import delete
            inv_uuids = [uuid.UUID(inv_id), uuid.UUID(other_id)]
            async with SessionFactory() as session:
                await session.execute(delete(Source).where(Source.investigation_id.in_(inv_uuids)))
                await session.execute(delete(Investigation).where(Investigation.id.in_(inv_uuids)))
                await session.commit()
            await engine.dispose()

        asyncio.run(cleanup())

        asyncio.run(cleanup())
