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
from app.research.query_planner import generate_queries, generate_web_queries
from app.research.retrieval import RetrievalError, RetrievedDocument, retrieve_document
from app.research.relevance import assess_result
from app.research.scientific_integrity import (
    assess_source_credibility,
    detect_source_independence_clusters,
    verify_evidence_provenance,
)
from app.research.telemetry import tavily_telemetry
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

    web_queries = generate_web_queries(investigation.question, request.timeframe)
    try:
        tasks = []
        for provider in providers:
            p_queries = web_queries if provider.name == "tavily" else queries
            for query in p_queries:
                tasks.append(search_one(provider, query))
        batches = await asyncio.gather(*tasks)
        results = deduplicate_results([item for batch in batches for item in batch])
        for result in results:
            assessment = assess_result(investigation.question, result, investigation.timeframe)
            result.relevance_score = assessment.score
            result.relevance_status = assessment.status
            result.relevance_reasons = list(assessment.reasons)
        results = sorted(results, key=lambda item: item.relevance_score, reverse=True)[: request.max_sources]
        for r in results:
            if r.provider == "tavily":
                tavily_telemetry.results_retained += 1
    finally:
        await asyncio.gather(*(provider.close() for provider in providers))
        await unpaywall.close()

    claim = Claim(investigation_id=investigation.id, text=(investigation.question or "").replace("\x00", ""))
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
        clean_content = (document.content or "").replace("\x00", "")
        clean_title = (document.title or "").replace("\x00", "") if document.title else None
        clean_headings = [(h or "").replace("\x00", "") for h in (document.headings or [])]
        source.content_hash = content_hash(clean_content)
        stored_document = Document(
            source_id=source.id,
            content_type=document.content_type,
            title=clean_title,
            content=clean_content,
            headings_json=json.dumps(clean_headings),
            page_count=document.page_count,
            retrieved_at=datetime.now(UTC),
            access_level=document.access_level,
            extraction_quality=document.extraction_quality,
            document_url=document.final_url.replace("\x00", ""),
            version_type=location.version_type if location else "unknown",
            access_route="open_access" if location else "original",
            metadata_match_status=match_status,
        )
        session.add(stored_document)
        await session.flush()
        source.selected_document_url = document.final_url.replace("\x00", "")
        source.open_access_status = "full_text_available" if document.access_level == "full_text" else "abstract_only"
        if document.access_level == "full_text":
            full_text_count += 1
        is_tavily = any(r.url == source.canonical_url and r.provider == "tavily" for r in results)
        if is_tavily:
            if document.access_level == "full_text":
                tavily_telemetry.full_text_successes += 1
            else:
                tavily_telemetry.full_text_failures += 1
        await publish(broker, EventType.research_document_retrieved, investigation.id, session=session, source_id=str(source.id))
        for item in extract_evidence(document.content, claim.text, passages=document.passages):
            # Strict provenance verification before evidence acceptance
            prov_check = verify_evidence_provenance(
                exact_text=item.exact_text,
                document_content=document.content,
                section_name=item.section_name,
                document_headings=document.headings,
                page_number=item.page_number,
                page_count=document.page_count,
            )
            is_traceable = prov_check.is_verified
            if is_traceable:
                evidence_count += 1
                rel_reason = item.relevance_reason
            else:
                rel_reason = f"[UNRESOLVED PROVENANCE: {prov_check.reason}] {item.relevance_reason}"

            if is_tavily and is_traceable:
                tavily_telemetry.evidence_passages_extracted += 1

            clean_exact_text = (item.exact_text or "").replace("\x00", "")
            clean_surrounding_context = (item.surrounding_context or "").replace("\x00", "") if item.surrounding_context else None
            clean_section_name = (item.section_name or "").replace("\x00", "")[:300] if item.section_name else None
            clean_rel_reason = (rel_reason or "").replace("\x00", "")
            clean_extraction_method = (item.extraction_method or "unknown").replace("\x00", "")[:120]
            clean_evidence_type = (item.evidence_type or "contextual").replace("\x00", "")[:64]

            session.add(
                Evidence(
                    source_id=source.id,
                    claim_id=claim.id,
                    document_id=stored_document.id,
                    exact_text=clean_exact_text,
                    surrounding_context=clean_surrounding_context,
                    evidence_type=clean_evidence_type,
                    relevance_score=item.relevance_score,
                    extraction_method=clean_extraction_method,
                    page_number=item.page_number,
                    section_name=clean_section_name,
                    retrieval_timestamp=datetime.now(UTC),
                    relevance_reason=clean_rel_reason,
                    traceable=is_traceable,
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

    all_included_sources: list[dict[str, object]] = []
    for result in results:
        included = result.relevance_status == "relevant"
        if result.provider == "tavily":
            if included:
                tavily_telemetry.sources_accepted += 1
            else:
                tavily_telemetry.sources_rejected += 1
        if included:
            relevant_source_count += 1
            all_included_sources.append({
                "id": result.url,
                "title": result.title,
                "url": result.url,
                "doi": result.doi,
                "publisher": result.publisher,
                "authors": result.authors,
            })

        cred_eval = assess_source_credibility(
            publisher=result.publisher,
            url=result.url,
            doi=result.doi,
            source_type_declared=result.source_type,
            authors=result.authors,
            publication_date=result.publication_date,
        )
        combined_reasons = list(result.relevance_reasons)
        combined_reasons.append(f"Credibility tier: {cred_eval.credibility_tier.upper()} ({cred_eval.credibility_score:.2f})")
        combined_reasons.extend(cred_eval.reasons)

        clean_title = (result.title or "").replace("\x00", "")
        clean_url = (result.url or "").replace("\x00", "")
        clean_publisher = (result.publisher or "").replace("\x00", "") if result.publisher else None
        clean_authors = [(a or "").replace("\x00", "") for a in (result.authors or []) if isinstance(a, str)]
        clean_reasons = [(r or "").replace("\x00", "") for r in combined_reasons if isinstance(r, str)]

        source = Source(
            investigation_id=investigation.id,
            title=clean_title,
            canonical_url=clean_url,
            original_url=clean_url,
            source_type=cred_eval.source_type.value,
            publisher=clean_publisher,
            authors_json=json.dumps(clean_authors),
            publication_date=result.publication_date,
            doi=result.doi,
            retrieval_timestamp=datetime.now(UTC),
            relevance_score=result.relevance_score,
            relevance_reasons_json=json.dumps(clean_reasons),
            inclusion_status="included" if included else "filtered",
            rejection_reason=None if included else "; ".join(result.relevance_reasons).replace("\x00", ""),
            open_access_status="not_checked" if included else "not_applicable",
            study_identity_key=(result.doi or result.title.casefold()).replace("\x00", ""),
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
    clusters = detect_source_independence_clusters(all_included_sources) if all_included_sources else []
    cluster_count = len(clusters)
    peer_reviewed_count = sum(
        1 for s in all_included_sources if getattr(s, "source_type", "") in {"peer_reviewed", "academic"} or bool(getattr(s, "doi", ""))
    )
    primary_source_count = sum(
        1 for s in all_included_sources if getattr(s, "source_type", "") in {"peer_reviewed", "preprint", "government_institutional", "research_organization"}
    )
    investigation.relevant_source_count = relevant_source_count
    investigation.full_text_count = full_text_count

    # Scientific calibration gate: 'strong' requires verified peer-review/primary literature, full-text, and independent clusters
    if relevant_source_count == 0 or evidence_count == 0:
        investigation.quality_status = "insufficient_evidence"
    elif (
        relevant_source_count >= 4
        and evidence_count >= 4
        and full_text_count >= 1
        and cluster_count >= 2
        and (peer_reviewed_count >= 1 or primary_source_count >= 2)
    ):
        investigation.quality_status = "strong"
    elif relevant_source_count >= 2 and evidence_count >= 2 and cluster_count >= 1:
        investigation.quality_status = "moderate"
    else:
        investigation.quality_status = "limited"

    gaps: list[str] = []
    if not relevant_source_count:
        gaps.append("No sources met the transparent relevance threshold.")
    if not evidence_count:
        gaps.append("No traceable relevant passages were extracted.")
    if peer_reviewed_count == 0 and relevant_source_count > 0:
        gaps.append("Corpus lacks verified peer-reviewed publications; findings rest on preprints or secondary sources.")
    if cluster_count < 2 and relevant_source_count > 1:
        gaps.append("Multiple sources originate from the same cluster or syndicated publisher, limiting independence.")
    if errors:
        gaps.append(f"{len(errors)} provider or retrieval operation(s) failed.")
    investigation.evidence_gap = " ".join(gaps) or None
    investigation.quality_summary = (
        f"{relevant_source_count} relevant source(s) ({peer_reviewed_count} peer-reviewed/DOI-verified, "
        f"{cluster_count} independent cluster(s)), {full_text_count} full-text document(s), and {evidence_count} traceable passage(s)."
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
