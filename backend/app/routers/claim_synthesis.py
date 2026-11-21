"""API Router for Claim-Level Evidence Synthesis."""

import json
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import ClaimSynthesisResult, Investigation, User
from app.auth.dependencies import get_current_user
from app.collaboration.permission_service import PermissionService
from app.schemas_m12 import ClaimSynthesisResultResponse
from app.analysis.claim_synthesis_service import ClaimSynthesisService

router = APIRouter(prefix="/research/investigations/{investigation_id}/claim-synthesis", tags=["claim-synthesis"])


def _to_response(res: ClaimSynthesisResult) -> ClaimSynthesisResultResponse:
    methodological_limits = []
    try:
        if res.methodological_limitations_json:
            methodological_limits = json.loads(res.methodological_limitations_json)
    except Exception:
        pass

    pub_dist = {}
    try:
        if res.publication_date_distribution_json:
            pub_dist = json.loads(res.publication_date_distribution_json)
    except Exception:
        pass

    missing_ev = []
    try:
        if res.important_missing_evidence_json:
            missing_ev = json.loads(res.important_missing_evidence_json)
    except Exception:
        pass

    outstanding_ops = []
    try:
        if res.outstanding_verification_operations_json:
            outstanding_ops = json.loads(res.outstanding_verification_operations_json)
    except Exception:
        pass

    return ClaimSynthesisResultResponse(
        id=str(res.id),
        investigation_id=str(res.investigation_id),
        claim_id=str(res.claim_id),
        relevant_sources_count=res.relevant_sources_count,
        unique_underlying_studies_count=res.unique_underlying_studies_count,
        direct_supporting_count=res.direct_supporting_count,
        partial_supporting_count=res.partial_supporting_count,
        contradicting_count=res.contradicting_count,
        contextual_count=res.contextual_count,
        unverified_count=res.unverified_count,
        methodological_limitations=methodological_limits,
        publication_date_distribution=pub_dist,
        source_independence_score=res.source_independence_score,
        important_missing_evidence=missing_ev,
        outstanding_verification_operations=outstanding_ops,
        synthesis_outcome=res.synthesis_outcome,
        explanation=res.explanation,
        created_at=res.created_at.isoformat() if res.created_at else "",
    )


@router.get("", response_model=List[ClaimSynthesisResultResponse])
async def list_claim_syntheses(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Retrieve synthesized evidence evaluation for all atomic claims."""
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    perm = PermissionService(db)
    if inv.workspace_id:
        await perm.require_workspace_membership(user.id, inv.workspace_id, min_role="viewer")

    service = ClaimSynthesisService(db)
    results = await service.list_claim_synthesis_results(investigation_id)
    if not results:
        results = await service.synthesize_investigation_claims(investigation_id)

    return [_to_response(r) for r in results]


@router.post("/run", response_model=List[ClaimSynthesisResultResponse])
async def run_claim_synthesis(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Recompute claim-level synthesis evaluations."""
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    perm = PermissionService(db)
    if inv.workspace_id:
        await perm.require_workspace_membership(user.id, inv.workspace_id, min_role="researcher")

    service = ClaimSynthesisService(db)
    results = await service.synthesize_investigation_claims(investigation_id)
    return [_to_response(r) for r in results]
