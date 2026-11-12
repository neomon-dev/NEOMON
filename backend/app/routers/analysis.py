import json
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.protocol import (
    AgentExecutionView,
    ArgumentView,
    ClaimAnalysisView,
    ConfidenceAssessment,
    DebateRoundView,
    DecisionView,
    EvidenceProvenance,
    ReportSectionPayload,
    ReportSectionView,
)
from app.analysis.report_service import (
    build_18_report_sections,
    compute_evidence_strength,
    get_report_version,
    list_report_versions,
    save_report_version,
)
from app.analysis.service import compute_analysis_coverage
from app.db import get_session
from app.errors import BackendError
from app.models import (
    AdjudicationDecision,
    AgentArgument,
    AnalysisAgentExecution,
    AnalysisJob,
    Claim,
    DebateRound,
    Document,
    Evidence,
    Investigation,
    ReportSection,
    ReportVersion,
    ResearchReport,
    Source,
)
from app.schemas import (
    AnalysisCoverageSummary,
    AnalysisJobResponse,
    AnalysisReportResponse,
    AnalysisStartRequest,
    EvidenceStrengthSummary,
    ReportVersionView,
)

router = APIRouter(prefix="/research", tags=["analysis"])


async def _investigation(session: AsyncSession, investigation_id: uuid.UUID) -> Investigation:
    result = await session.get(Investigation, investigation_id)
    if result is None:
        raise BackendError("Investigation not found.", 404, "not_found")
    return result


async def _job(session: AsyncSession, job_id: uuid.UUID) -> AnalysisJob:
    result = await session.get(AnalysisJob, job_id)
    if result is None:
        raise BackendError("Analysis job not found.", 404, "analysis_not_found")
    return result


async def _build_job_response(session: AsyncSession, job: AnalysisJob) -> AnalysisJobResponse:
    claims = list((await session.scalars(select(Claim).where(Claim.investigation_id == job.investigation_id))).all())
    executions = list((await session.scalars(select(AnalysisAgentExecution).where(AnalysisAgentExecution.job_id == job.id))).all())
    arguments = list((await session.scalars(select(AgentArgument).where(AgentArgument.job_id == job.id))).all())
    decisions = list((await session.scalars(select(AdjudicationDecision).where(AdjudicationDecision.job_id == job.id))).all())
    evidence = list((await session.scalars(select(Evidence).join(Source).where(Source.investigation_id == job.investigation_id))).all())
    coverage = compute_analysis_coverage(claims, executions, arguments, decisions, evidence)
    return AnalysisJobResponse(
        id=job.id,
        investigation_id=job.investigation_id,
        status=job.status,
        max_debate_rounds=job.max_debate_rounds,
        max_concurrent_agents=job.max_concurrent_agents,
        provider_kind=job.provider_kind,
        default_model=job.default_model,
        cancel_requested=job.cancel_requested,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        coverage=coverage,
    )


def _job_response(job: AnalysisJob) -> AnalysisJobResponse:
    return AnalysisJobResponse(
        id=job.id,
        investigation_id=job.investigation_id,
        status=job.status,
        max_debate_rounds=job.max_debate_rounds,
        max_concurrent_agents=job.max_concurrent_agents,
        provider_kind=job.provider_kind,
        default_model=job.default_model,
        cancel_requested=job.cancel_requested,
        error_message=job.error_message,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


@router.post("/investigations/{investigation_id}/analysis", response_model=AnalysisJobResponse, status_code=202)
async def start_analysis(
    investigation_id: uuid.UUID,
    payload: AnalysisStartRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AnalysisJobResponse:
    investigation = await _investigation(session, investigation_id)
    if payload.provider is not None:
        from app.providers.base import ProviderRequestError, validate_provider_endpoint

        try:
            await validate_provider_endpoint(
                payload.provider.endpoint,
                payload.provider.kind,
                allow_local_runtime=payload.provider.allow_local_runtime,
            )
        except ProviderRequestError as exc:
            raise BackendError(str(exc), 422, "invalid_provider_endpoint") from exc
    existing = await session.scalar(select(AnalysisJob).where(AnalysisJob.investigation_id == investigation_id))
    if existing and existing.status not in {"completed", "completed_with_warnings", "failed", "cancelled"}:
        raise BackendError("An analysis job is already active for this investigation.", 409, "analysis_active")
    if existing:
        report_ids = select(ResearchReport.id).where(ResearchReport.job_id == existing.id)
        await session.execute(delete(ReportSection).where(ReportSection.report_id.in_(report_ids)))
        await session.execute(delete(ResearchReport).where(ResearchReport.job_id == existing.id))
        await session.execute(delete(AdjudicationDecision).where(AdjudicationDecision.job_id == existing.id))
        await session.execute(delete(DebateRound).where(DebateRound.job_id == existing.id))
        await session.execute(delete(AgentArgument).where(AgentArgument.job_id == existing.id))
        await session.execute(delete(AnalysisAgentExecution).where(AnalysisAgentExecution.job_id == existing.id))
        job = existing
        job.status = "queued"
        job.error_message = None
        job.cancel_requested = False
        job.max_debate_rounds = payload.max_debate_rounds
        job.max_concurrent_agents = payload.max_concurrent_agents
        job.provider_kind = payload.provider.kind.value if payload.provider else None
        job.default_model = payload.provider.model if payload.provider else None
        job.role_models_json = json.dumps(payload.role_models)
        job.started_at = None
        job.completed_at = None
    else:
        job = AnalysisJob(
            investigation_id=investigation_id,
            max_debate_rounds=payload.max_debate_rounds,
            max_concurrent_agents=payload.max_concurrent_agents,
            provider_kind=payload.provider.kind.value if payload.provider else None,
            default_model=payload.provider.model if payload.provider else None,
            role_models_json=json.dumps(payload.role_models),
            status="queued",
        )
        session.add(job)
    await session.commit()
    request.app.state.analysis_manager.schedule(
        str(job.id), investigation.question, payload.provider, payload.role_models
    )
    return _job_response(job)


@router.get("/investigations/{investigation_id}/analysis", response_model=AnalysisJobResponse)
async def read_analysis(
    investigation_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> AnalysisJobResponse:
    await _investigation(session, investigation_id)
    job = await session.scalar(select(AnalysisJob).where(AnalysisJob.investigation_id == investigation_id))
    if job is None:
        raise BackendError("No analysis job exists for this investigation.", 404, "analysis_not_found")
    return await _build_job_response(session, job)


@router.get("/analysis/{job_id}/coverage", response_model=AnalysisCoverageSummary)
async def read_analysis_coverage(
    job_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> AnalysisCoverageSummary:
    job = await _job(session, job_id)
    claims = list((await session.scalars(select(Claim).where(Claim.investigation_id == job.investigation_id))).all())
    executions = list((await session.scalars(select(AnalysisAgentExecution).where(AnalysisAgentExecution.job_id == job.id))).all())
    arguments = list((await session.scalars(select(AgentArgument).where(AgentArgument.job_id == job.id))).all())
    decisions = list((await session.scalars(select(AdjudicationDecision).where(AdjudicationDecision.job_id == job.id))).all())
    evidence = list((await session.scalars(select(Evidence).join(Source).where(Source.investigation_id == job.investigation_id))).all())
    return compute_analysis_coverage(claims, executions, arguments, decisions, evidence)


@router.post("/analysis/{job_id}/cancel", response_model=AnalysisJobResponse)
async def cancel_analysis(job_id: uuid.UUID, request: Request) -> AnalysisJobResponse:
    if not await request.app.state.analysis_manager.cancel(str(job_id)):
        raise BackendError("Analysis job not found.", 404, "analysis_not_found")
    from app.db import SessionFactory

    async with SessionFactory() as session:
        job = await session.get(AnalysisJob, job_id)
        if job is None:
            raise BackendError("Analysis job not found.", 404, "analysis_not_found")
        return await _build_job_response(session, job)


@router.get("/analysis/{job_id}/executions", response_model=list[AgentExecutionView])
async def list_executions(job_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[AgentExecutionView]:
    await _job(session, job_id)
    rows = (await session.scalars(select(AnalysisAgentExecution).where(AnalysisAgentExecution.job_id == job_id))).all()
    views: list[AgentExecutionView] = []
    for row in rows:
        usage = json.loads(row.token_usage_json) if row.token_usage_json else {}
        queue_wait = usage.get("queue_wait_seconds") if isinstance(usage, dict) else None
        inference_dur = usage.get("inference_duration_seconds") if isinstance(usage, dict) else None
        queue_pos = usage.get("queue_position") if isinstance(usage, dict) else None
        views.append(
            AgentExecutionView(
                id=row.id,
                agent_identifier=row.agent_identifier,
                status=row.status,
                model=row.model,
                output=json.loads(row.output_json) if row.output_json else None,
                error_message=row.error_message,
                started_at=row.started_at,
                completed_at=row.completed_at,
                queue_wait_seconds=float(queue_wait) if isinstance(queue_wait, (int, float)) else None,
                inference_duration_seconds=float(inference_dur) if isinstance(inference_dur, (int, float)) else None,
                queue_position=int(queue_pos) if isinstance(queue_pos, int) else None,
            )
        )
    return views


@router.get("/analysis/{job_id}/claims", response_model=list[ClaimAnalysisView])
async def list_analysis_claims(job_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[ClaimAnalysisView]:
    job = await _job(session, job_id)
    claims = (
        await session.scalars(select(Claim).where(Claim.investigation_id == job.investigation_id).order_by(Claim.id))
    ).all()
    return [
        ClaimAnalysisView(
            id=item.id,
            text=item.text,
            explanation=item.explanation,
            priority=item.priority,
            search_objectives=json.loads(item.search_objectives_json),
            evidence_categories=json.loads(item.evidence_categories_json),
            dependencies=[uuid.UUID(value) for value in json.loads(item.dependencies_json)],
            status=item.status,
        )
        for item in claims
    ]


@router.get("/analysis/{job_id}/arguments", response_model=list[ArgumentView])
async def list_arguments(job_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[ArgumentView]:
    await _job(session, job_id)
    rows = (await session.scalars(select(AgentArgument).where(AgentArgument.job_id == job_id))).all()
    return [
        ArgumentView(
            id=row.id,
            claim_id=row.claim_id,
            agent_identifier=row.agent_identifier,
            argument_type=row.argument_type,
            text=row.text,
            evidence_ids=[uuid.UUID(value) for value in json.loads(row.evidence_ids_json)],
            source_ids=[uuid.UUID(value) for value in json.loads(row.source_ids_json)],
            evidence_basis=row.evidence_basis,
            reasoning_summary=row.reasoning_summary,
            limitations=json.loads(row.limitations_json),
            confidence=ConfidenceAssessment(level=row.confidence_level, explanation=row.confidence_explanation),
        )
        for row in rows
    ]


@router.get("/analysis/{job_id}/debates", response_model=list[DebateRoundView])
async def list_debates(job_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[DebateRoundView]:
    await _job(session, job_id)
    rows = (await session.scalars(select(DebateRound).where(DebateRound.job_id == job_id).order_by(DebateRound.round_number))).all()
    return [
        DebateRoundView(
            id=row.id,
            round_number=row.round_number,
            moderator_summary=row.moderator_summary,
            unresolved_disagreements=json.loads(row.unresolved_disagreements_json),
            requested_follow_up=json.loads(row.requested_follow_up_json),
        )
        for row in rows
    ]


@router.get("/analysis/{job_id}/decisions", response_model=list[DecisionView])
async def list_decisions(job_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> list[DecisionView]:
    await _job(session, job_id)
    rows = (await session.scalars(select(AdjudicationDecision).where(AdjudicationDecision.job_id == job_id))).all()
    return [
        DecisionView(
            id=row.id,
            claim_id=row.claim_id,
            decision=row.decision,
            explanation=row.explanation,
            supporting_argument_ids=[uuid.UUID(value) for value in json.loads(row.supporting_argument_ids_json)],
            evidence_ids=[uuid.UUID(value) for value in json.loads(row.evidence_ids_json)],
            unresolved_disagreements=json.loads(row.unresolved_disagreements_json),
        )
        for row in rows
    ]


@router.get("/analysis/{job_id}/report", response_model=AnalysisReportResponse)
async def read_report(job_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> AnalysisReportResponse:
    job = await _job(session, job_id)
    report = await session.scalar(select(ResearchReport).where(ResearchReport.job_id == job_id))
    if report is None:
        raise BackendError("Analysis report is not available.", 404, "report_not_found")
    sections = (
        await session.scalars(select(ReportSection).where(ReportSection.report_id == report.id).order_by(ReportSection.position))
    ).all()

    versions = await list_report_versions(session, job.investigation_id)
    if versions:
        evidence_strength = versions[0].evidence_strength
        version_num = versions[0].version_number
    else:
        claims = list((await session.scalars(select(Claim).where(Claim.investigation_id == job.investigation_id))).all())
        sources = list((await session.scalars(select(Source).where(Source.investigation_id == job.investigation_id))).all())
        evidence = list((await session.scalars(select(Evidence).join(Source).where(Source.investigation_id == job.investigation_id))).all())
        decisions = list((await session.scalars(select(AdjudicationDecision).where(AdjudicationDecision.job_id == job_id))).all())
        documents = list((await session.scalars(select(Document).join(Source).where(Source.investigation_id == job.investigation_id))).all())
        evidence_strength = compute_evidence_strength(claims, sources, documents, evidence, decisions)
        version_num = 1

    return AnalysisReportResponse(
        id=report.id,
        job_id=report.job_id,
        executive_summary=report.executive_summary,
        overall_assessment=report.overall_assessment,
        evidence_gap=report.evidence_gap,
        version_number=version_num,
        evidence_strength=evidence_strength,
        versions=versions,
        sections=[
            ReportSectionView(
                id=item.id,
                section_type=item.section_type,
                title=item.title,
                content=item.content,
                claim_ids=[uuid.UUID(value) for value in json.loads(item.claim_ids_json)],
                evidence_ids=[uuid.UUID(value) for value in json.loads(item.evidence_ids_json)],
                provenance=json.loads(item.provenance_json),
            )
            for item in sections
        ],
    )


@router.get("/investigations/{investigation_id}/reports", response_model=list[ReportVersionView])
async def list_investigation_reports(
    investigation_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> list[ReportVersionView]:
    await _investigation(session, investigation_id)
    return await list_report_versions(session, investigation_id)


@router.get("/investigations/{investigation_id}/reports/{version_or_id}", response_model=AnalysisReportResponse)
async def read_investigation_report_version(
    investigation_id: uuid.UUID,
    version_or_id: str,
    session: AsyncSession = Depends(get_session),
) -> AnalysisReportResponse:
    await _investigation(session, investigation_id)
    row, raw_sections = await get_report_version(session, investigation_id, version_or_id)
    if row is None:
        raise BackendError("Report version not found.", 404, "version_not_found")

    strength_dict = {}
    try:
        strength_dict = json.loads(row.evidence_strength_json)
    except Exception:
        pass
    strength = EvidenceStrengthSummary.model_validate(
        strength_dict if strength_dict else {"score": row.evidence_strength_score, "tier": row.evidence_strength_tier}
    )
    versions = await list_report_versions(session, investigation_id)

    parsed_sections: list[ReportSectionView] = []
    for s in raw_sections:
        parsed_sections.append(
            ReportSectionView(
                id=uuid.UUID(s.get("id")) if s.get("id") else uuid.uuid4(),
                section_type=s.get("section_type", "section"),
                title=s.get("title", "Untitled Section"),
                content=s.get("content", ""),
                claim_ids=[uuid.UUID(str(cid)) for cid in s.get("claim_ids", [])],
                evidence_ids=[uuid.UUID(str(eid)) for eid in s.get("evidence_ids", [])],
                provenance=s.get("provenance", []),
            )
        )

    return AnalysisReportResponse(
        id=row.id,
        job_id=row.job_id,
        executive_summary=row.executive_summary,
        overall_assessment=row.overall_assessment,
        evidence_gap=row.evidence_gap,
        version_number=row.version_number,
        evidence_strength=strength,
        versions=versions,
        sections=parsed_sections,
    )


@router.post("/investigations/{investigation_id}/reports/generate", response_model=AnalysisReportResponse)
async def regenerate_investigation_report(
    investigation_id: uuid.UUID, session: AsyncSession = Depends(get_session)
) -> AnalysisReportResponse:
    inv = await _investigation(session, investigation_id)
    job = await session.scalar(
        select(AnalysisJob)
        .where(AnalysisJob.investigation_id == investigation_id)
        .order_by(desc(AnalysisJob.created_at))
    )
    if job is None:
        raise BackendError("No analysis job found for investigation.", 404, "analysis_not_found")

    claims = list((await session.scalars(select(Claim).where(Claim.investigation_id == investigation_id))).all())
    sources_list = list((await session.scalars(select(Source).where(Source.investigation_id == investigation_id))).all())
    sources = {s.id: s for s in sources_list}
    documents_list = list((await session.scalars(select(Document).join(Source).where(Source.investigation_id == investigation_id))).all())
    documents = {d.id: d for d in documents_list}
    evidence = list((await session.scalars(select(Evidence).join(Source).where(Source.investigation_id == investigation_id))).all())
    decisions = list((await session.scalars(select(AdjudicationDecision).where(AdjudicationDecision.job_id == job.id))).all())
    arguments = list((await session.scalars(select(AgentArgument).where(AgentArgument.job_id == job.id))).all())

    def provenance_for(evidence_ids: list[uuid.UUID]) -> list[EvidenceProvenance]:
        res = []
        for eid in evidence_ids:
            ev = next((e for e in evidence if e.id == eid), None)
            if not ev:
                continue
            src = sources.get(ev.source_id)
            doc = documents.get(ev.document_id) if ev.document_id else None
            res.append(
                EvidenceProvenance(
                    evidence_id=ev.id,
                    source_url=src.canonical_url or src.original_url if src else "",
                    access_level=doc.access_level if doc else "metadata_only",
                    document_url=doc.document_url if doc else None,
                    version_type=doc.version_type if doc else None,
                    page_number=ev.page_number,
                    section_name=ev.section_name,
                )
            )
        return res

    sections_payload = build_18_report_sections(
        question=inv.question,
        claims=claims,
        decisions=decisions,
        evidence=evidence,
        sources=sources,
        documents=documents,
        arguments=arguments,
        warnings=[],
        provenance_for_fn=provenance_for,
    )
    strength = compute_evidence_strength(claims, sources, documents, evidence, decisions)

    version = await save_report_version(
        session=session,
        investigation_id=investigation_id,
        job_id=job.id,
        executive_summary=sections_payload[0].content if sections_payload else "Executive summary",
        overall_assessment="qualified",
        evidence_gap=None,
        sections=sections_payload,
        evidence_strength=strength,
    )

    active_report = await session.scalar(select(ResearchReport).where(ResearchReport.job_id == job.id))
    if active_report is None:
        active_report = ResearchReport(
            job_id=job.id,
            executive_summary=version.executive_summary,
            overall_assessment=version.overall_assessment,
            evidence_gap=version.evidence_gap,
        )
        session.add(active_report)
        await session.flush()
    else:
        active_report.executive_summary = version.executive_summary
        active_report.overall_assessment = version.overall_assessment
        active_report.evidence_gap = version.evidence_gap
        await session.execute(delete(ReportSection).where(ReportSection.report_id == active_report.id))

    for pos, sec in enumerate(sections_payload):
        session.add(
            ReportSection(
                report_id=active_report.id,
                section_type=sec.section_type,
                title=sec.title,
                content=sec.content,
                claim_ids_json=json.dumps([str(c) for c in sec.claim_ids]),
                evidence_ids_json=json.dumps([str(e) for e in sec.evidence_ids]),
                provenance_json=json.dumps([p.model_dump(mode="json") for p in sec.provenance]),
                position=pos,
            )
        )
    await session.commit()

    return await read_report(job.id, session)
