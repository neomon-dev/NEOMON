import json
import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.export_service import (
    generate_evidence_csv,
    generate_json_ld_export,
    generate_markdown_export,
    generate_pdf_export,
    generate_sources_csv,
    generate_standalone_html_graph,
    generate_structured_json_export,
    generate_svg_graph_export,
)
from app.analysis.report_service import compute_evidence_strength
from app.analysis.service import compute_analysis_coverage
from app.auth.dependencies import get_current_user
from app.auth.rate_limiter import rate_limit_export
from app.collaboration.permission_service import PermissionService
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
    ResearchReport,
    Source,
    User,
)

router = APIRouter(
    prefix="/research/investigations/{investigation_id}/export",
    tags=["export"],
    dependencies=[Depends(rate_limit_export())],
)


async def _load_investigation_bundle(session: AsyncSession, investigation_id: uuid.UUID, user: User):
    perm = PermissionService(session)
    await perm.check_investigation_access(user, investigation_id, "read")

    inv = await session.get(Investigation, investigation_id)
    if inv is None:
        raise BackendError("Investigation not found.", 404, "not_found")

    job = await session.scalar(
        select(AnalysisJob)
        .where(AnalysisJob.investigation_id == investigation_id)
        .order_by(desc(AnalysisJob.created_at))
    )

    claims = list((await session.scalars(select(Claim).where(Claim.investigation_id == investigation_id))).all())
    sources = list((await session.scalars(select(Source).where(Source.investigation_id == investigation_id))).all())
    evidence = list((await session.scalars(select(Evidence).join(Source).where(Source.investigation_id == investigation_id))).all())
    documents = list((await session.scalars(select(Document).join(Source).where(Source.investigation_id == investigation_id))).all())

    arguments: list[AgentArgument] = []
    debates: list[DebateRound] = []
    decisions: list[AdjudicationDecision] = []
    report: ResearchReport | None = None
    sections: list[ReportSection] = []
    coverage = None

    if job is not None:
        arguments = list((await session.scalars(select(AgentArgument).where(AgentArgument.job_id == job.id))).all())
        debates = list((await session.scalars(select(DebateRound).where(DebateRound.job_id == job.id))).all())
        decisions = list((await session.scalars(select(AdjudicationDecision).where(AdjudicationDecision.job_id == job.id))).all())
        report = await session.scalar(select(ResearchReport).where(ResearchReport.job_id == job.id))
        if report is not None:
            sections = list(
                (await session.scalars(select(ReportSection).where(ReportSection.report_id == report.id).order_by(ReportSection.position))).all()
            )
        executions = list((await session.scalars(select(AnalysisAgentExecution).where(AnalysisAgentExecution.job_id == job.id))).all())
        coverage = compute_analysis_coverage(claims, executions, arguments, decisions, evidence)

    strength = compute_evidence_strength(claims, sources, documents, evidence, decisions)

    return {
        "investigation": inv,
        "job": job,
        "claims": claims,
        "sources": sources,
        "evidence": evidence,
        "documents": documents,
        "arguments": arguments,
        "debates": debates,
        "decisions": decisions,
        "report": report,
        "sections": sections,
        "coverage": coverage,
        "strength": strength,
    }


@router.get("/manifest")
async def get_export_manifest(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    bundle = await _load_investigation_bundle(session, investigation_id, user)
    inv = bundle["investigation"]
    base_path = f"/api/v1/research/investigations/{investigation_id}/export"
    return {
        "investigation_id": str(investigation_id),
        "title": inv.question,
        "formats": [
            {
                "format": "markdown",
                "label": "Research Report (Markdown)",
                "description": "Full 18-section research report with frontmatter and citations",
                "extension": ".md",
                "content_type": "text/markdown",
                "download_url": f"{base_path}/markdown",
            },
            {
                "format": "pdf",
                "label": "Printable Intelligence Report (PDF)",
                "description": "Standard PDF document with multi-page typography and evidence scores",
                "extension": ".pdf",
                "content_type": "application/pdf",
                "download_url": f"{base_path}/pdf",
            },
            {
                "format": "json",
                "label": "Research Snapshot (JSON)",
                "description": "Complete machine-readable snapshot with claims, evidence, and arguments",
                "extension": ".json",
                "content_type": "application/json",
                "download_url": f"{base_path}/json",
            },
            {
                "format": "html-graph",
                "label": "Interactive Knowledge Graph (Standalone HTML)",
                "description": "Single-file interactive graph with pan, zoom, search, and zero CDN dependencies",
                "extension": ".html",
                "content_type": "text/html",
                "download_url": f"{base_path}/html-graph",
            },
            {
                "format": "svg",
                "label": "Vector Knowledge Graph (SVG)",
                "description": "High-resolution vector graphic for publications or vector editors",
                "extension": ".svg",
                "content_type": "image/svg+xml",
                "download_url": f"{base_path}/svg",
            },
            {
                "format": "json-ld",
                "label": "Linked Data (JSON-LD)",
                "description": "Schema.org ScholarlyArticle & ClaimReview semantic web metadata",
                "extension": ".jsonld",
                "content_type": "application/ld+json",
                "download_url": f"{base_path}/json-ld",
            },
            {
                "format": "evidence-csv",
                "label": "Evidence Dataset (CSV)",
                "description": "Tabular export of all extracted evidence passages with provenance",
                "extension": ".csv",
                "content_type": "text/csv",
                "download_url": f"{base_path}/evidence-csv",
            },
            {
                "format": "sources-csv",
                "label": "Source Catalog (CSV)",
                "description": "Tabular export of all discovered sources with DOIs and status",
                "extension": ".csv",
                "content_type": "text/csv",
                "download_url": f"{base_path}/sources-csv",
            },
        ],
    }


@router.get("/markdown")
async def export_markdown_endpoint(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    b = await _load_investigation_bundle(session, investigation_id, user)
    md = generate_markdown_export(
        b["investigation"],
        b["job"],
        b["report"],
        b["sections"],
        b["claims"],
        b["sources"],
        b["evidence"],
        b["decisions"],
        b["strength"],
    )
    filename = f"neomon-report-{investigation_id}.md"
    return Response(
        content=md,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/pdf")
async def export_pdf_endpoint(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    b = await _load_investigation_bundle(session, investigation_id, user)
    pdf_bytes = generate_pdf_export(
        b["investigation"],
        b["report"],
        b["sections"],
        b["strength"],
    )
    filename = f"neomon-report-{investigation_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/json")
async def export_json_endpoint(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    b = await _load_investigation_bundle(session, investigation_id, user)
    data = generate_structured_json_export(
        b["investigation"],
        b["job"],
        b["report"],
        b["sections"],
        b["claims"],
        b["sources"],
        b["documents"],
        b["evidence"],
        b["arguments"],
        b["debates"],
        b["decisions"],
        b["coverage"],
        b["strength"],
    )
    filename = f"neomon-snapshot-{investigation_id}.json"
    return Response(
        content=json.dumps(data, indent=2, default=str),
        media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/html-graph")
async def export_html_graph_endpoint(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    b = await _load_investigation_bundle(session, investigation_id, user)
    html_str = generate_standalone_html_graph(
        b["investigation"],
        b["claims"],
        b["sources"],
        b["evidence"],
        b["decisions"],
    )
    filename = f"neomon-graph-{investigation_id}.html"
    return Response(
        content=html_str,
        media_type="text/html; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/svg")
async def export_svg_endpoint(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    b = await _load_investigation_bundle(session, investigation_id, user)
    svg_str = generate_svg_graph_export(
        b["investigation"],
        b["claims"],
        b["sources"],
        b["evidence"],
    )
    filename = f"neomon-graph-{investigation_id}.svg"
    return Response(
        content=svg_str,
        media_type="image/svg+xml; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/json-ld")
async def export_json_ld_endpoint(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    b = await _load_investigation_bundle(session, investigation_id, user)
    ld_data = generate_json_ld_export(
        b["investigation"],
        b["report"],
        b["claims"],
        b["sources"],
        b["evidence"],
        b["decisions"],
    )
    filename = f"neomon-{investigation_id}.jsonld"
    return Response(
        content=json.dumps(ld_data, indent=2, default=str),
        media_type="application/ld+json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/evidence-csv")
async def export_evidence_csv_endpoint(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    b = await _load_investigation_bundle(session, investigation_id, user)
    csv_str = generate_evidence_csv(
        b["claims"],
        b["sources"],
        b["evidence"],
    )
    filename = f"neomon-evidence-{investigation_id}.csv"
    return Response(
        content=csv_str,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sources-csv")
async def export_sources_csv_endpoint(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    b = await _load_investigation_bundle(session, investigation_id, user)
    csv_str = generate_sources_csv(b["sources"])
    filename = f"neomon-sources-{investigation_id}.csv"
    return Response(
        content=csv_str,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
