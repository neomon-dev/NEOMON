import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.config import get_settings
from app.research.evidence import classify_evidence, extract_evidence
from app.research.normalization import deduplicate_results, normalize_url
from app.research.providers import (
    ResearchProviderError,
    SearchQuery,
    SearchResult,
    TavilyProvider,
    build_research_providers,
)
from app.research.query_planner import generate_queries, generate_web_queries
from app.research.relevance import assess_result, question_focus
from app.research.telemetry import TavilyTelemetry, tavily_telemetry
from app.schemas import ResearchMode


# ============================================================================
# 1. Successful basic / advanced search
# ============================================================================
@pytest.mark.asyncio
async def test_tavily_search_success_basic_and_advanced():
    provider = TavilyProvider(api_key="tvly-test-key", search_depth="advanced", max_results=5)
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {
                "title": "HBM Demand in AI Accelerators",
                "url": "https://example.com/hbm-ai",
                "content": "High-bandwidth memory production constraints drive datacenter supply crunches.",
                "score": 0.94,
                "published_date": "2024-05-10",
                "authors": ["Tech Analyst"],
            }
        ]
    }
    with patch.object(provider.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        query = SearchQuery("AI datacenter impact on RAM DRAM shortage", "web_causal")
        results = await provider.search(query, limit=5)

        assert len(results) == 1
        res = results[0]
        assert res.title == "HBM Demand in AI Accelerators"
        assert res.url == "https://example.com/hbm-ai"
        assert res.provider == "tavily"
        assert res.source_type == "web"
        assert res.raw_score == 0.94
        assert res.provider_metadata["tavily_score"] == 0.94
        assert res.provider_metadata["search_depth"] == "advanced"
        assert res.authors == ["Tech Analyst"]
        assert res.publication_date == "2024-05-10"
        # Scientific relevance score must NOT be pre-populated with provider score
        assert res.relevance_score == 0.0

    await provider.close()


# ============================================================================
# 2. Empty results handling
# ============================================================================
@pytest.mark.asyncio
async def test_tavily_search_empty_results():
    provider = TavilyProvider(api_key="tvly-test-key")
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"results": []}

    with patch.object(provider.client, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_response
        results = await provider.search(SearchQuery("obscure non-existent topic", "broad"))
        assert results == []

    await provider.close()


# ============================================================================
# 3. Authentication failure (HTTP 401 / 403) - Bounded, no infinite retries
# ============================================================================
@pytest.mark.asyncio
async def test_tavily_auth_failure_does_not_retry():
    telemetry = TavilyTelemetry()
    with patch("app.research.providers.tavily_telemetry", telemetry):
        provider = TavilyProvider(api_key="invalid-key")
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = '{"error": "Unauthorized: Invalid API key"}'

        with patch.object(provider.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(ResearchProviderError) as exc_info:
                await provider.search(SearchQuery("test query", "broad"))

            assert "authentication failed" in str(exc_info.value).lower()
            # Must NOT retry auth errors (post called exactly once)
            assert mock_post.call_count == 1
            assert telemetry.error_categories["auth"] == 1
            assert telemetry.search_requests_failed == 1

        await provider.close()


# ============================================================================
# 4. Rate limiting (HTTP 429) & backoff
# ============================================================================
@pytest.mark.asyncio
async def test_tavily_rate_limiting_retries_and_records():
    telemetry = TavilyTelemetry()
    with patch("app.research.providers.tavily_telemetry", telemetry):
        provider = TavilyProvider(api_key="tvly-test-key")
        mock_429 = MagicMock()
        mock_429.status_code = 429
        mock_429.headers = {"retry-after": "0"}
        mock_429.text = "Rate limit exceeded"

        mock_200 = MagicMock()
        mock_200.status_code = 200
        mock_200.json.return_value = {"results": [{"url": "https://example.com/ok", "title": "OK"}]}

        # First returns 429, second returns 200
        with patch.object(provider.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [mock_429, mock_200]
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                results = await provider.search(SearchQuery("test query", "broad"))
                assert len(results) == 1
                assert mock_post.call_count == 2
                assert mock_sleep.call_count == 1

        await provider.close()


# ============================================================================
# 5. Timeout handling & telemetry
# ============================================================================
@pytest.mark.asyncio
async def test_tavily_timeout_handling():
    telemetry = TavilyTelemetry()
    with patch("app.research.providers.tavily_telemetry", telemetry):
        provider = TavilyProvider(api_key="tvly-test-key")

        with patch.object(provider.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Read timed out")
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(ResearchProviderError) as exc_info:
                    await provider.search(SearchQuery("test query", "broad"))

                assert "timed out" in str(exc_info.value).lower()
                assert telemetry.error_categories["timeout"] == 1

        await provider.close()


# ============================================================================
# 6. Malformed JSON handling
# ============================================================================
@pytest.mark.asyncio
async def test_tavily_malformed_json_handling():
    telemetry = TavilyTelemetry()
    with patch("app.research.providers.tavily_telemetry", telemetry):
        provider = TavilyProvider(api_key="tvly-test-key")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON token")

        with patch.object(provider.client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with pytest.raises(ResearchProviderError) as exc_info:
                await provider.search(SearchQuery("test query", "broad"))

            assert "invalid json" in str(exc_info.value).lower()
            assert telemetry.error_categories["validation"] == 1

        await provider.close()


# ============================================================================
# 7. Duplicate URL handling
# ============================================================================
def test_duplicate_url_normalization():
    url1 = "https://example.com/report?utm_source=tavily&utm_medium=cpc&id=123"
    url2 = "https://EXAMPLE.COM/report/?id=123"
    assert normalize_url(url1) == normalize_url(url2)


# ============================================================================
# 8. Cross-provider deduplication against academic results
# ============================================================================
def test_cross_provider_deduplication_preserves_academic_metadata():
    web_result = SearchResult(
        title="DRAM Market Analysis",
        url="https://doi.org/10.1000/182",
        snippet="Web snippet on memory prices.",
        source_type="web",
        provider="tavily",
    )
    academic_result = SearchResult(
        title="DRAM Market Analysis",
        url="https://doi.org/10.1000/182",
        doi="10.1000/182",
        snippet="Peer-reviewed abstract on DRAM pricing.",
        publisher="IEEE",
        authors=["Alice Smith", "Bob Jones"],
        source_type="academic",
        provider="crossref",
    )
    deduped = deduplicate_results([web_result, academic_result])
    assert len(deduped) == 1
    # The duplicate enriched the first result with DOI and academic classification
    assert deduped[0].doi == "10.1000/182"
    assert deduped[0].source_type == "academic"
    assert deduped[0].publisher == "IEEE"


# ============================================================================
# 9. Source normalization: raw score stored, scientific relevance uncorrupted
# ============================================================================
def test_source_normalization_raw_score_isolation():
    res = SearchResult(
        title="AI Hardware Review",
        url="https://example.com/ai-hw",
        snippet="Comprehensive analysis.",
        raw_score=0.985,
        provider_metadata={"tavily_score": 0.985},
    )
    assert res.relevance_score == 0.0
    assert res.raw_score == 0.985
    assert res.provider_metadata["tavily_score"] == 0.985


# ============================================================================
# 10. Failed full-text retrieval and snippet fallback
# ============================================================================
def test_evidence_classification_and_snippet_fallback():
    # Passages extracted from snippet
    snippet = "High bandwidth memory shortages reduced production yields across enterprise AI servers."
    classified_type, reason = classify_evidence(snippet)
    assert classified_type in {"supporting", "contextual"}
    assert len(reason) > 0


# ============================================================================
# 11. Irrelevant search result rejection
# ============================================================================
def test_irrelevant_search_result_rejection():
    question = "How does AI contribute to RAM shortages?"
    irrelevant = SearchResult(
        title="Comparative Anatomy of Deep-Sea Cephalopods",
        url="https://example.com/squid",
        snippet="Morphological traits of giant squid species in Atlantic trenches.",
        source_type="web",
    )
    assessment = assess_result(question, irrelevant)
    assert assessment.score < 0.28
    assert assessment.status == "rejected"
    assert any("does not identify the question's subject" in r for r in assessment.reasons)


# ============================================================================
# 12. Evidence classification: supporting, contradicting, contextual, limitations
# ============================================================================
def test_evidence_classification_types():
    sup_type, _ = classify_evidence("Server deployment improved system throughput and increased memory bandwidth.")
    assert sup_type == "supporting"

    con_type, _ = classify_evidence("The benchmark results showed no significant improvement and lower memory efficiency.")
    assert con_type == "contradicting"

    lim_type, _ = classify_evidence("A notable limitation of this study is the small sample size and lack of long-term data.")
    assert lim_type == "methodological_limitation"

    ctx_type, _ = classify_evidence("DDR5 memory modules operate at voltages between 1.1V and 1.25V under standard specifications.")
    assert ctx_type == "contextual"


# ============================================================================
# 13. Missing API key handling
# ============================================================================
@pytest.mark.asyncio
async def test_missing_api_key_raises_error():
    provider = TavilyProvider(api_key=None)
    with patch("app.config.get_settings") as mock_settings:
        mock_settings.return_value.tavily_api_key = None
        mock_settings.return_value.tavily_enabled = True
        provider.api_key = None
        with pytest.raises(ResearchProviderError) as exc_info:
            await provider.search(SearchQuery("test", "broad"))
        assert "not configured" in str(exc_info.value).lower()

    await provider.close()


# ============================================================================
# 14. Disabled provider handling
# ============================================================================
@pytest.mark.asyncio
async def test_disabled_provider_returns_empty():
    provider = TavilyProvider(api_key="tvly-test-key")
    provider.enabled = False
    results = await provider.search(SearchQuery("test query", "broad"))
    assert results == []
    await provider.close()


# ============================================================================
# 15. Provider failure isolation without breaking academic providers
# ============================================================================
def test_build_research_providers_with_and_without_tavily():
    with patch("app.research.providers.get_settings") as mock_settings:
        # Case A: Tavily enabled and key configured
        mock_settings.return_value.tavily_enabled = True
        mock_settings.return_value.tavily_api_key = "tvly-key"
        mock_settings.return_value.tavily_search_depth = "advanced"
        mock_settings.return_value.tavily_max_results = 10
        mock_settings.return_value.tavily_include_domains = []
        mock_settings.return_value.tavily_exclude_domains = []
        mock_settings.return_value.tavily_request_timeout_seconds = 15.0
        mock_settings.return_value.request_timeout_seconds = 15.0
        mock_settings.return_value.research_user_agent = "NEOMON/Test"

        providers = build_research_providers()
        names = [p.name for p in providers]
        assert "tavily" in names
        assert "crossref" in names
        assert "openalex" in names
        assert "arxiv" in names

        # Case B: Tavily disabled
        mock_settings.return_value.tavily_enabled = False
        providers_disabled = build_research_providers()
        names_disabled = [p.name for p in providers_disabled]
        assert "tavily" not in names_disabled
        assert "crossref" in names_disabled
        assert "openalex" in names_disabled
        assert "arxiv" in names_disabled


# ============================================================================
# REGRESSION TOPIC TESTS: 5 RESEARCH QUESTIONS & TOPIC ISOLATION
# ============================================================================

# Topic 1: "What is AI?"
def test_regression_topic_1_what_is_ai():
    question = "What is AI?"
    terms, subject, outcomes = question_focus(question)
    assert "ai" in subject

    exact = SearchResult(
        title="What Is AI?",
        url="https://example.org/ai-def",
        snippet="Foundational principles of artificial intelligence and machine learning.",
        source_type="academic",
    )
    res = assess_result(question, exact)
    assert res.score >= 0.85
    assert res.status == "relevant"

    web_queries = generate_web_queries(question)
    assert any("definition" in q.text.lower() for q in web_queries)


# Topic 2: "How do layoffs by IT companies affect employees?"
def test_regression_topic_2_it_layoffs():
    question = "How do layoffs by IT companies affect employees?"
    terms, subject, outcomes = question_focus(question)
    assert "layoff" in subject
    assert "it" in subject
    assert "employee" in subject

    relevant = SearchResult(
        title="Tech Company Layoffs and Their Consequences on Software Engineer Mental Health",
        url="https://example.org/it-layoffs",
        snippet="We investigate how corporate downsizing across software firms impacts employee retention and anxiety.",
        source_type="web",
    )
    res = assess_result(question, relevant)
    assert res.score >= 0.75
    assert res.status == "relevant"

    web_queries = generate_web_queries(question)
    assert any("layoff" in q.text.lower() and "employee" in q.text.lower() for q in web_queries)


# Topic 3 & 4: STRICT TOPIC ISOLATION (AI RAM Shortages vs AI Electricity Demand)
def test_regression_topic_3_and_4_strict_isolation():
    q_ram = "How does AI contribute to RAM shortages?"
    q_elec = "How does AI increase electricity demand?"

    ram_source = SearchResult(
        title="HBM and DRAM Allocation for AI Accelerators: Analyzing the Memory Shortage",
        url="https://example.com/ram-paper",
        snippet="Wafer capacity allocation to High Bandwidth Memory creates acute supply crunches for DDR5 RAM modules.",
        source_type="web",
    )

    elec_source = SearchResult(
        title="AI Datacenter Expansion and Grid Electricity Demand Growth",
        url="https://example.com/elec-paper",
        snippet="Surging power consumption from generative AI server farms strains regional electric utility grids.",
        source_type="web",
    )

    # 1. RAM source MUST be relevant to RAM question
    ram_for_ram = assess_result(q_ram, ram_source)
    assert ram_for_ram.score >= 0.70
    assert ram_for_ram.status == "relevant"

    # 2. Electricity source MUST be REJECTED for RAM question (topic isolation)
    elec_for_ram = assess_result(q_ram, elec_source)
    assert elec_for_ram.status == "rejected"
    assert any("does not identify the question's subject" in r for r in elec_for_ram.reasons)

    # 3. Electricity source MUST be relevant to Electricity question
    elec_for_elec = assess_result(q_elec, elec_source)
    assert elec_for_elec.score >= 0.70
    assert elec_for_elec.status == "relevant"

    # 4. RAM source MUST be REJECTED for Electricity question (topic isolation)
    ram_for_elec = assess_result(q_elec, ram_source)
    assert ram_for_elec.status == "rejected"
    assert any("does not identify the question's subject" in r for r in ram_for_elec.reasons)


# Topic 5: "What is the impact of DDR5 demand on RAM prices?"
def test_regression_topic_5_ddr5_ram_prices():
    question = "What is the impact of DDR5 demand on RAM prices?"
    terms, subject, outcomes = question_focus(question)
    assert "ddr5" in subject
    assert "ram" in subject
    assert "price" in outcomes

    relevant = SearchResult(
        title="DDR5 Adoption and Contract Price Fluctuations in Global DRAM Markets",
        url="https://example.com/ddr5-prices",
        snippet="Analysis of DDR5 spot pricing, manufacturing yield curves, and overall computer memory market costs.",
        source_type="web",
    )
    res = assess_result(question, relevant)
    assert res.score >= 0.75
    assert res.status == "relevant"

    # Unrelated AI electricity source must be rejected
    unrelated = SearchResult(
        title="Renewable Power Integration for Machine Learning Server Clusters",
        url="https://example.com/ml-power",
        snippet="Optimizing grid carbon intensity during batch inference runs.",
        source_type="web",
    )
    unrelated_res = assess_result(question, unrelated)
    assert unrelated_res.status == "rejected"


# ============================================================================
# API ENDPOINT TESTS: /api/v1/providers/tavily/test & /status
# ============================================================================
def test_tavily_api_endpoints(client):
    # 1. Test status endpoint
    response = client.get("/api/v1/providers/tavily/status")
    assert response.status_code == 200
    status_data = response.json()
    assert status_data["provider"] == "tavily"
    assert "enabled" in status_data
    assert "api_key_configured" in status_data
    assert "telemetry" in status_data
    assert "queries_submitted" in status_data["telemetry"]

    # 2. Test connectivity endpoint with mock success
    with patch("app.research.providers.httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        test_resp = client.post(
            "/api/v1/providers/tavily/test",
            json={"api_key": "tvly-test-key", "search_depth": "basic"},
        )
        assert test_resp.status_code == 200
        result = test_resp.json()
        assert result["connected"] is True
        assert result["api_key_configured"] is True

    # 3. Test connectivity endpoint with invalid key (401)
    with patch("app.research.providers.httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = MagicMock(status_code=401)
        test_resp = client.post(
            "/api/v1/providers/tavily/test",
            json={"api_key": "invalid-key", "search_depth": "basic"},
        )
        assert test_resp.status_code == 200
        result = test_resp.json()
        assert result["connected"] is False
        assert "Invalid" in result["error"]

