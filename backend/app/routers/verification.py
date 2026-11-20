"""API Router for Evidence-to-Claim Verification."""

import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import EvidenceVerificationRecord, Investigation, User
from app.auth.dependencies import get_current_user
from app.collaboration.permission_service import PermissionService
from app.schemas_m12 import ChallengeCorrectionRequest, EvidenceVerificationRecordResponse
from app.analysis.evidence_verification_service import EvidenceVerificationService

router = APIRouter(prefix="/research/investigations/{investigation_id}/verification", tags=["verification"])


def _to_response(rec: EvidenceVerificationRecord) -> EvidenceVerificationRecordResponse:
    return EvidenceVerificationRecordResponse(
        id=str(rec.id),
        investigation_id=str(rec.investigation_id),
        claim_id=str(rec.claim_id),
        evidence_id=str(rec.evidence_id),
        source_id=str(rec.source_id),
        document_id=str(rec.document_id) if rec.document_id else None,
        exact_passage_text=rec.exact_passage_text,
        passage_location=str(rec.passage_location) if rec.passage_location is not None else None,
        source_publication_date=rec.source_publication_date.isoformat() if rec.source_publication_date else None,
        retrieval_date=rec.retrieval_date.isoformat() if rec.retrieval_date else "",
        relationship_classification=rec.relationship_classification,
        verification_status=rec.verification_status,
        verification_method=rec.verification_method,
        confidence=rec.confidence,
        confidence_meaning=rec.confidence_meaning,
        explanation=rec.explanation,
        agent_or_process=rec.agent_or_process,
        model_provider_info=rec.model_provider_info,
        is_challenged=rec.is_challenged,
        challenge_reason=rec.challenge_reason,
        corrected_by_user_id=str(rec.corrected_by_user_id) if rec.corrected_by_user_id else None,
        corrected_at=rec.corrected_at.isoformat() if rec.corrected_at else None,
        created_at=rec.created_at.isoformat() if rec.created_at else "",
    )


@router.get("", response_model=List[EvidenceVerificationRecordResponse])
async def list_verification_records(
    investigation_id: uuid.UUID,
    claim_id: Optional[uuid.UUID] = Query(None),
    classification: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List scientific evidence-to-claim verification records with filters."""
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    perm = PermissionService(db)
    if inv.workspace_id:
        await perm.require_workspace_membership(user.id, inv.workspace_id, min_role="viewer")

    service = EvidenceVerificationService(db)
    records = await service.list_verification_records(
        investigation_id=investigation_id,
        claim_id=claim_id,
        classification=classification,
        limit=limit,
        offset=offset,
    )
    return [_to_response(r) for r in records]


@router.post("/verify", response_model=List[EvidenceVerificationRecordResponse])
async def trigger_evidence_verification(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Trigger deterministic scientific evidence verification across all claims."""
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    perm = PermissionService(db)
    if inv.workspace_id:
        await perm.require_workspace_membership(user.id, inv.workspace_id, min_role="researcher")

    service = EvidenceVerificationService(db)
    records = await service.verify_investigation_evidence(investigation_id)
    return [_to_response(r) for r in records]


@router.post("/{record_id}/challenge", response_model=EvidenceVerificationRecordResponse)
async def challenge_verification_record(
    investigation_id: uuid.UUID,
    record_id: uuid.UUID,
    payload: ChallengeCorrectionRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Challenge and correct an automated classification as an authorized reviewer."""
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    perm = PermissionService(db)
    if inv.workspace_id:
        await perm.require_workspace_membership(user.id, inv.workspace_id, min_role="reviewer")

    service = EvidenceVerificationService(db)
    try:
        updated = await service.challenge_and_correct_record(
            record_id=record_id,
            user_id=user.id,
            corrected_classification=payload.corrected_classification,
            reason=payload.reason,
        )
        return _to_response(updated)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
