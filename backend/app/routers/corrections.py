"""API Router for Human Evidence Corrections and Versioned Reassessment."""

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import HumanEvidenceCorrection, Investigation, User
from app.auth.dependencies import get_current_user
from app.collaboration.permission_service import PermissionService
from app.schemas_m12 import HumanEvidenceCorrectionCreate, HumanEvidenceCorrectionResponse
from app.analysis.human_review_service import HumanReviewService

router = APIRouter(prefix="/api/v1/research/investigations/{investigation_id}/corrections", tags=["corrections"])


def _to_response(c: HumanEvidenceCorrection) -> HumanEvidenceCorrectionResponse:
    return HumanEvidenceCorrectionResponse(
        id=str(c.id),
        investigation_id=str(c.investigation_id),
        claim_id=str(c.claim_id),
        evidence_id=str(c.evidence_id),
        user_id=str(c.user_id),
        correction_type=c.correction_type,
        original_value=c.original_value,
        corrected_value=c.corrected_value,
        reason=c.reason,
        version_number=c.version_number,
        is_active=c.is_active,
        created_at=c.created_at.isoformat() if c.created_at else "",
    )


@router.get("", response_model=List[HumanEvidenceCorrectionResponse])
async def list_corrections(
    investigation_id: uuid.UUID,
    claim_id: Optional[uuid.UUID] = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Retrieve immutable audit trail of human corrections."""
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    perm = PermissionService(db)
    if inv.workspace_id:
        await perm.require_workspace_membership(user.id, inv.workspace_id, min_role="viewer")

    service = HumanReviewService(db)
    corrections = await service.list_investigation_corrections(investigation_id, claim_id=claim_id)
    return [_to_response(c) for c in corrections]


@router.post("", response_model=HumanEvidenceCorrectionResponse, status_code=status.HTTP_201_CREATED)
async def submit_correction(
    investigation_id: uuid.UUID,
    payload: HumanEvidenceCorrectionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Submit a challenge or correction to an evidence classification."""
    service = HumanReviewService(db)
    try:
        correction = await service.submit_evidence_correction(
            investigation_id=investigation_id,
            claim_id=payload.claim_id,
            evidence_id=payload.evidence_id,
            user=user,
            correction_type=payload.correction_type,
            corrected_value=payload.corrected_value,
            reason=payload.reason,
        )
        return _to_response(correction)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reassess")
async def trigger_versioned_reassessment(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Trigger explicit versioned reassessment propagating human corrections to claim synthesis and quality calibration."""
    service = HumanReviewService(db)
    try:
        return await service.trigger_versioned_reassessment(investigation_id, user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
