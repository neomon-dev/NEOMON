"""Research Quality Calibration and Scientific Evidence Validation Router (Milestone 8G)."""

import json
from typing import Any
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.entailment_service import validate_evidence_claim_entailment_heuristic
from app.analysis.quality_calibration_service import calibrate_investigation_quality
from app.auth.dependencies import get_current_user
from app.collaboration.permission_service import PermissionService, DEFAULT_GLOBAL_WORKSPACE_ID
from app.db import get_session
from app.errors import BackendError
from app.models import (
    Claim,
    Evidence,
    Investigation,
    ProviderFailureImpact,
    ResearchQualityCalibration,
    Source,
    SourceCredibilityAssessment,
    SourceLineageRelationship,
    User,
)
from app.research.source_credibility import evaluate_canonical_credibility
from app.research.source_lineage import analyze_source_lineage
from app.schemas import (
    EvidenceClaimValidationView,
    InvestigationQualityAuditItem,
    ProviderFailureImpactView,
    QualityCalibrationAuditView,
    SourceLineageClusterView,
    SourceLineageOverviewResponse,
    SourceLineageRelationshipView,
)

router = APIRouter(prefix="/research", tags=["quality_audit"])


@router.get("/quality/audits", response_model=list[InvestigationQualityAuditItem])
async def list_quality_audits(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[InvestigationQualityAuditItem]:
    """List research quality calibration status for all investigations accessible to user."""
    perm = PermissionService(session)
    user_workspaces = await perm.get_user_workspaces(user.id)
    if not user_workspaces:
        user_workspaces = [DEFAULT_GLOBAL_WORKSPACE_ID]

    scope_cond = Investigation.workspace_id.in_(user_workspaces)
    if DEFAULT_GLOBAL_WORKSPACE_ID in user_workspaces:
        from sqlalchemy import or_
        scope_cond = or_(scope_cond, Investigation.workspace_id.is_(None))

    inv_res = await session.execute(
        select(Investigation)
        .where(scope_cond)
        .order_by(Investigation.updated_at.desc())
    )
    invs = list(inv_res.scalars().all())

    items: list[InvestigationQualityAuditItem] = []
    for inv in invs:
        # Load calibration if exists
        cal_res = await session.execute(
            select(ResearchQualityCalibration).where(
                ResearchQualityCalibration.investigation_id == inv.id
            )
        )
        cal = cal_res.scalar_one_or_none()

        src_count_res = await session.execute(
            select(func.count(Source.id)).where(Source.investigation_id == inv.id)
        )
        src_count = src_count_res.scalar() or 0

        ev_count_res = await session.execute(
            select(func.count(Evidence.id)).join(Source).where(Source.investigation_id == inv.id)
        )
        ev_count = ev_count_res.scalar() or 0

        calibrated_tier = cal.calibrated_tier if cal else "Uncalibrated"
        calibrated_score = cal.calibrated_score if cal else 0.0
        raw_score = cal.raw_score if cal else 0.0
        coverage_score = cal.coverage_score if cal else 0.0
        failure_penalty = cal.failure_penalty if cal else 0.0
        op_comp = max(0.0, round(100.0 - (failure_penalty * 2.5), 1))

        items.append(
            InvestigationQualityAuditItem(
                investigation_id=inv.id,
                question=inv.question,
                quality_status=inv.quality_status,
                calibrated_tier=calibrated_tier,
                calibrated_score=calibrated_score,
                raw_score=raw_score,
                coverage_score=coverage_score,
                failure_penalty=failure_penalty,
                operational_completeness=op_comp,
                research_coverage=coverage_score,
                evidence_strength=calibrated_score,
                source_count=src_count,
                evidence_count=ev_count,
                updated_at=inv.updated_at,
            )
        )
    return items


@router.post("/investigations/{investigation_id}/quality/calibrate", response_model=QualityCalibrationAuditView)
async def calibrate_quality(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> QualityCalibrationAuditView:
    """Trigger complete calibration of research quality for an investigation."""
    perm = PermissionService(session)
    await perm.check_investigation_access(user, investigation_id, "write")

    cal_dict = await calibrate_investigation_quality(session, investigation_id)
    return await get_quality_audit(investigation_id, user, session)


@router.get("/investigations/{investigation_id}/quality/audit", response_model=QualityCalibrationAuditView)
async def get_quality_audit(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> QualityCalibrationAuditView:
    """Retrieve full calibrated research quality audit for an investigation."""
    perm = PermissionService(session)
    inv = await perm.check_investigation_access(user, investigation_id, "read")

    cal_res = await session.execute(
        select(ResearchQualityCalibration).where(
            ResearchQualityCalibration.investigation_id == investigation_id
        )
    )
    cal = cal_res.scalar_one_or_none()

    # Load sources, claims, evidence
    sources_res = await session.execute(
        select(Source).where(Source.investigation_id == investigation_id)
    )
    sources = list(sources_res.scalars().all())

    claims_res = await session.execute(
        select(Claim).where(Claim.investigation_id == investigation_id)
    )
    claims = list(claims_res.scalars().all())

    ev_count_res = await session.execute(
        select(func.count(Evidence.id)).join(Source).where(Source.investigation_id == investigation_id)
    )
    total_ev = ev_count_res.scalar() or 0

    # If no calibration exists yet, run calibration
    if not cal:
        await calibrate_investigation_quality(session, investigation_id)
        cal_res = await session.execute(
            select(ResearchQualityCalibration).where(
                ResearchQualityCalibration.investigation_id == investigation_id
            )
        )
        cal = cal_res.scalar_one_or_none()

    dim_breakdown = {}
    reasons = []
    if cal:
        try:
            dim_breakdown = json.loads(cal.dimension_breakdown_json)
        except Exception:
            dim_breakdown = {}
        try:
            reasons = json.loads(cal.calibration_reasons_json)
        except Exception:
            reasons = []

    # Assess source credibility counts
    peer_count = 0
    primary_count = 0
    for s in sources:
        cred = evaluate_canonical_credibility(
            url=s.canonical_url or s.original_url,
            publisher=s.publisher,
            doi=s.doi,
            source_type_declared=s.source_type,
            title=s.title,
        )
        if cred.is_peer_reviewed:
            peer_count += 1
        if cred.is_primary:
            primary_count += 1

    op_comp = dim_breakdown.get("operational_completeness", max(0.0, round(100.0 - ((cal.failure_penalty if cal else 0.0) * 2.5), 1)))
    cov_score = cal.coverage_score if cal else 0.0
    ev_strength = cal.calibrated_score if cal else 0.0

    return QualityCalibrationAuditView(
        investigation_id=inv.id,
        investigation_question=inv.question,
        calibrated_tier=cal.calibrated_tier if cal else "Inconclusive",
        raw_score=cal.raw_score if cal else 0.0,
        calibrated_score=cal.calibrated_score if cal else 0.0,
        coverage_score=cov_score,
        failure_penalty=cal.failure_penalty if cal else 0.0,
        operational_completeness=float(op_comp),
        research_coverage=float(cov_score),
        evidence_strength=float(ev_strength),
        dimension_breakdown=dim_breakdown,
        calibration_reasons=reasons,
        verified_peer_reviewed_count=peer_count,
        primary_source_count=primary_count,
        total_sources=len(sources),
        total_claims=len(claims),
        total_evidence=total_ev,
        created_at=cal.created_at if cal else inv.created_at,
        updated_at=cal.updated_at if cal else inv.updated_at,
    )


@router.get("/investigations/{investigation_id}/quality/lineage", response_model=SourceLineageOverviewResponse)
async def get_source_lineage(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SourceLineageOverviewResponse:
    """Retrieve publication lineage analysis and explainable independent clusters."""
    perm = PermissionService(session)
    inv = await perm.check_investigation_access(user, investigation_id, "read")

    sources_res = await session.execute(
        select(Source).where(Source.investigation_id == investigation_id)
    )
    sources = list(sources_res.scalars().all())

    lineage_res = analyze_source_lineage(sources)

    cluster_views = [
        SourceLineageClusterView(
            cluster_id=c.cluster_id,
            cluster_name=c.cluster_name,
            primary_source_id=c.primary_source_id,
            member_source_ids=c.member_source_ids,
            relationship_type=c.relationship_type,
            explanation=c.explanation,
            effective_independence_weight=c.effective_independence_weight,
        )
        for c in lineage_res.clusters
    ]

    rel_views = [
        SourceLineageRelationshipView(
            id=uuid.uuid4(),
            source_id=uuid.UUID(r.source_id),
            related_source_id=uuid.UUID(r.related_source_id),
            relationship_type=r.relationship_type.value,
            confidence=r.confidence,
            shared_identifiers=r.shared_identifiers,
            explanation=r.explanation,
            created_at=inv.created_at,
        )
        for r in lineage_res.relationships
        if len(r.source_id) == 36 and len(r.related_source_id) == 36
    ]

    return SourceLineageOverviewResponse(
        investigation_id=inv.id,
        total_sources=lineage_res.total_sources,
        effective_independent_count=lineage_res.effective_independent_count,
        independence_ratio=lineage_res.independence_ratio,
        lineage_summary=lineage_res.lineage_summary,
        clusters=cluster_views,
        relationships=rel_views,
    )


@router.get("/investigations/{investigation_id}/quality/validations", response_model=list[EvidenceClaimValidationView])
async def get_entailment_validations(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[EvidenceClaimValidationView]:
    """Retrieve evidence-to-claim entailment validations with correlation flags and missing steps."""
    perm = PermissionService(session)
    inv = await perm.check_investigation_access(user, investigation_id, "read")

    claims_res = await session.execute(
        select(Claim).where(Claim.investigation_id == investigation_id)
    )
    claims = list(claims_res.scalars().all())
    claim_dict = {c.id: c.text for c in claims}

    sources_res = await session.execute(
        select(Source).where(Source.investigation_id == investigation_id)
    )
    sources = list(sources_res.scalars().all())
    source_ids = [s.id for s in sources]

    if not source_ids:
        return []

    ev_res = await session.execute(
        select(Evidence).where(Evidence.source_id.in_(source_ids))
    )
    evidence_list = list(ev_res.scalars().all())

    results: list[EvidenceClaimValidationView] = []
    for ev in evidence_list:
        cid = ev.claim_id or (claims[0].id if claims else None)
        if not cid:
            continue
        c_text = claim_dict.get(cid, "General research question")

        val = validate_evidence_claim_entailment_heuristic(
            claim_id=str(cid),
            claim_text=c_text,
            evidence_id=str(ev.id),
            evidence_text=ev.exact_text,
            surrounding_context=ev.surrounding_context,
        )

        results.append(
            EvidenceClaimValidationView(
                id=uuid.uuid4(),
                investigation_id=inv.id,
                claim_id=cid,
                claim_text=c_text,
                evidence_id=ev.id,
                evidence_text=ev.exact_text,
                entailment_classification=val.entailment_classification.value,
                entailment_strength=val.entailment_strength,
                explanation=val.explanation,
                missing_inferential_steps=val.missing_inferential_steps,
                correlation_vs_causation_flag=val.correlation_vs_causation_flag,
                validation_method=val.validation_method,
                validator_model=val.validator_model,
                status=val.status,
                created_at=inv.created_at,
            )
        )

    return results


@router.get("/investigations/{investigation_id}/quality/failures", response_model=list[ProviderFailureImpactView])
async def get_provider_failures(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ProviderFailureImpactView]:
    """Retrieve provider retrieval failures and their assessed impact severity."""
    perm = PermissionService(session)
    inv = await perm.check_investigation_access(user, investigation_id, "read")

    fails_res = await session.execute(
        select(ProviderFailureImpact).where(
            ProviderFailureImpact.investigation_id == investigation_id
        ).order_by(ProviderFailureImpact.created_at.desc())
    )
    failures = list(fails_res.scalars().all())

    return [
        ProviderFailureImpactView(
            id=f.id,
            investigation_id=f.investigation_id,
            provider=f.provider,
            operation=f.operation,
            query=f.query,
            failure_type=f.failure_type,
            retry_attempts=f.retry_attempts,
            impact_severity=f.impact_severity,
            missing_category=f.missing_category,
            explanation=f.explanation,
            created_at=f.created_at,
        )
        for f in failures
    ]
