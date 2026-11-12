import asyncio
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.events import EventBroker
from app.models import Claim, Document, Evidence, Investigation, OpenAccessLocation as OpenAccessLocationRow, ResearchQuery, Source
from app.research.evidence import extract_evidence
from app.research.normalization import content_hash, deduplicate_results
from app.research.open_access import assess_location
from app.research.providers import (
    OpenAccessLocation,
    ResearchProvider,
    ResearchProviderError,
    SearchQuery,
    SearchResult,
    UnpaywallProvider,
    build_research_providers,
)
from app.research.query_planner import generate_queries
from app.research.retrieval import RetrievalError, RetrievedDocument, retrieve_document
from app.research.relevance import assess_result
from app.schemas import EventType, InvestigationCreate, ResearchMode


async def publish(
    broker: EventBroker,
    event_type: EventType,
    investigation_id: uuid.UUID,
    *,
    session: AsyncSession | None = None,
    **payload: object,
) -> None:
    await broker.publish(event_type, {"investigation_id": str(investigation_id), **payload}, session=session)


async def run_investigation(
    session: AsyncSession,
    broker: EventBroker,
    investigation: Investigation,
    request: InvestigationCreate,
) -> tuple[list[ResearchQuery], list[str]]:
    investigation_id = investigation.id
    investigation.status = "running"
    await session.commit()
    try:
        return await _run_investigation_impl(session, broker, investigation, request)
    except Exception as exc:
        await session.rollback()
        failed = await session.get(Investigation, investigation_id)
        if failed is not None:
            failed.status = "failed"
            failed.evidence_gap = f"Research execution failed: {exc}"
            await session.commit()
        await publish(
            broker,
            EventType.research_failed,
            investigation_id,
            source_count=0,
            errors=[str(exc)],
        )
        raise


async def _run_investigation_impl(
    session: AsyncSession,
    broker: EventBroker,
    investigation: Investigation,
    request: InvestigationCreate,
) -> tuple[list[ResearchQuery], list[str]]:
    await publish(broker, EventType.research_started, investigation.id, question=investigation.question)
    queries = generate_queries(investigation.question, request.mode, request.timeframe)[: request.max_queries]
    query_rows = [
        ResearchQuery(investigation_id=investigation.id, query=item.text, category=item.category)
        for item in queries
    ]
    session.add_all(query_rows)
    await session.commit()
    await publish(broker, EventType.research_query_generated, investigation.id, count=len(queries))
    providers = build_research_providers()
    unpaywall = UnpaywallProvider()
    errors: list[str] = []
    results: list[SearchResult] = []

    async def search_one(provider: ResearchProvider, query: SearchQuery) -> list[SearchResult]:
        try:
            await publish(broker, EventType.research_search_started, investigation.id, provider=provider.name, query=query.text)
            found = await provider.search(query, min(request.max_sources, 10))
            await publish(broker, EventType.research_search_completed, investigation.id, provider=provider.name, count=len(found))
            return found
        except ResearchProviderError as exc:
            errors.append(f"{provider.name}: {exc}")
            return []

    try:
        tasks = [search_one(provider, query) for provider in providers for query in queries]
        batches = await asyncio.gather(*tasks)
        results = deduplicate_results([item for batch in batches for item in batch])
        for result in results:
            assessment = assess_result(investigation.question, result, investigation.timeframe)
            result.relevance_score = assessment.score
            result.relevance_status = assessment.status
            result.relevance_reasons = list(assessment.reasons)
        results = sorted(results, key=lambda item: item.relevance_score, reverse=True)[: request.max_sources]
    finally:
        await asyncio.gather(*(provider.close() for provider in providers))
        await unpaywall.close()

    claim = Claim(investigation_id=investigation.id, text=investigation.question)
    session.add(claim)
    await session.flush()
    relevant_source_count = 0
    full_text_count = 0
    evidence_count = 0

    async def persist_document(
        source: Source,
        document: RetrievedDocument,
        location: OpenAccessLocation | None = None,
        match_status: str = "unknown",
    ) -> None:
        nonlocal full_text_count, evidence_count
        source.content_hash = content_hash(document.content)
        stored_document = Document(
            source_id=source.id,
            content_type=document.content_type,
            title=document.title,
            content=document.content,
            headings_json=json.dumps(document.headings),
            page_count=document.page_count,
            retrieved_at=datetime.now(UTC),
            access_level=document.access_level,
            extraction_quality=document.extraction_quality,
            document_url=document.final_url,
            version_type=location.version_type if location else "unknown",
            access_route="open_access" if location else "original",
            metadata_match_status=match_status,
        )
        session.add(stored_document)
        await session.flush()
        source.selected_document_url = document.final_url
        source.open_access_status = "full_text_available" if document.access_level == "full_text" else "abstract_only"
        if document.access_level == "full_text":
            full_text_count += 1
        await publish(broker, EventType.research_document_retrieved, investigation.id, session=session, source_id=str(source.id))
        for item in extract_evidence(document.content, claim.text, passages=document.passages):
            evidence_count += 1
            session.add(
                Evidence(
                    source_id=source.id,
                    claim_id=claim.id,
                    document_id=stored_document.id,
                    exact_text=item.exact_text,
                    surrounding_context=item.surrounding_context,
                    evidence_type=item.evidence_type,
                    relevance_score=item.relevance_score,
                    extraction_method=item.extraction_method,
                    page_number=item.page_number,
                    section_name=item.section_name,
                    retrieval_timestamp=datetime.now(UTC),
                    relevance_reason=item.relevance_reason,
                    traceable=True,
                )
            )
            await publish(
                broker,
                EventType.research_evidence_extracted,
                investigation.id,
                session=session,
                source_id=str(source.id),
                evidence_type=item.evidence_type,
                page_number=item.page_number,
            )

    for result in results:
        included = result.relevance_status == "relevant"
        if included:
            relevant_source_count += 1
        source = Source(
            investigation_id=investigation.id,
            title=result.title,
            canonical_url=result.url,
            original_url=result.url,
            source_type=result.source_type,
            publisher=result.publisher,
            authors_json=json.dumps(result.authors),
            publication_date=result.publication_date,
            doi=result.doi,
            retrieval_timestamp=datetime.now(UTC),
            relevance_score=result.relevance_score,
            relevance_reasons_json=json.dumps(result.relevance_reasons),
            inclusion_status="included" if included else "filtered",
            rejection_reason=None if included else "; ".join(result.relevance_reasons),
            open_access_status="not_checked" if included else "not_applicable",
            study_identity_key=result.doi or result.title.casefold(),
        )
        session.add(source)
        await session.flush()
        locations = list(result.open_access_locations)
        if result.doi:
            try:
                locations.extend(await unpaywall.lookup(result.doi))
            except ResearchProviderError as exc:
                errors.append(f"unpaywall: {exc}")
        original_location = OpenAccessLocation(
            url=source.original_url,
            repository=result.publisher,
            version_type="published_version",
            doi=result.doi,
            title=result.title,
            authors=result.authors,
            publication_date=result.publication_date,
        )
        locations.append(original_location)
        unique_locations: list[OpenAccessLocation] = []
        location_rows: dict[str, OpenAccessLocationRow] = {}
        seen_urls: set[str] = set()
        for location in locations:
            if location.url in seen_urls:
                continue
            seen_urls.add(location.url)
            assessment = assess_location(result, location)
            location_row = OpenAccessLocationRow(
                source_id=source.id,
                url=location.url,
                repository=location.repository,
                version_type=location.version_type,
                license=location.license,
                match_status=assessment.status,
                match_reason=assessment.reason,
            )
            session.add(location_row)
            location_rows[location.url] = location_row
            if assessment.status != "rejected":
                unique_locations.append(location)
        source.open_access_status = "candidates_found" if unique_locations else "unavailable"
        await publish(broker, EventType.research_source_discovered, investigation.id, session=session, source_id=str(source.id), title=source.title, url=source.original_url)
        if not included:
            await publish(
                broker,
                EventType.research_source_discovered,
                investigation.id,
                session=session,
                source_id=str(source.id),
                title=source.title,
                url=source.original_url,
                inclusion_status=source.inclusion_status,
                relevance_score=source.relevance_score,
            )
            continue
        acquired = False
        for location in unique_locations:
            try:
                document = await retrieve_document(location.url)
                assessment = assess_location(result, location)
                await persist_document(source, document, location, assessment.status)
                location_rows[location.url].acquisition_status = "acquired"
                acquired = True
                break
            except RetrievalError as exc:
                location_rows[location.url].acquisition_status = "failed"
                location_rows[location.url].failure_reason = str(exc)
                errors.append(f"{location.url}: {exc}")
        if not acquired:
            source.open_access_status = "access_restricted" if unique_locations else "unavailable"
            if result.snippet.strip():
                abstract = RetrievedDocument(
                    url=source.original_url,
                    final_url=source.original_url,
                    content_type="text/plain",
                    title=source.title,
                    content=result.snippet,
                    headings=[],
                    passages=[(None, result.snippet, "Abstract")],
                    access_level="abstract_only",
                    extraction_quality="medium",
                )
                await persist_document(source, abstract)
    investigation.relevant_source_count = relevant_source_count
    investigation.full_text_count = full_text_count
    investigation.quality_status = (
        "strong"
        if relevant_source_count >= 3 and evidence_count >= 3 and full_text_count >= 1
        else "limited"
        if relevant_source_count and evidence_count
        else "insufficient_evidence"
    )
    gaps: list[str] = []
    if not relevant_source_count:
        gaps.append("No sources met the transparent relevance threshold.")
    if not evidence_count:
        gaps.append("No traceable relevant passages were extracted.")
    if errors:
        gaps.append(f"{len(errors)} provider or retrieval operation(s) failed.")
    investigation.evidence_gap = " ".join(gaps) or None
    investigation.quality_summary = (
        f"{relevant_source_count} relevant source(s), {full_text_count} full-text document(s), "
        f"and {evidence_count} traceable evidence passage(s)."
    )
    investigation.status = "completed" if results else "failed"
    await session.commit()
    await publish(
        broker,
        EventType.research_completed if results else EventType.research_failed,
        investigation.id,
        source_count=len(results),
        errors=errors,
    )
    return query_rows, errors
