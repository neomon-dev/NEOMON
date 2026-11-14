"""API Router for Methodology Audit Findings."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Investigation, MethodologyAuditFinding, User
from app.auth.dependencies import get_current_user
from app.collaboration.permission_service import PermissionService
from app.schemas_m12 import MethodologyAuditFindingResponse
from app.analysis.methodology_audit_service import MethodologyAuditService

router = APIRouter(prefix="/api/v1/research/investigations/{investigation_id}/methodology-audit", tags=["methodology-audit"])


def _to_response(f: MethodologyAuditFinding) -> MethodologyAuditFindingResponse:
    return MethodologyAuditFindingResponse(
        id=str(f.id),
        investigation_id=str(f.investigation_id),
        audit_dimension=f.audit_dimension,
        issue_severity=f.issue_severity,
        finding_title=f.finding_title,
        description=f.description,
        linked_source_id=str(f.linked_source_id) if f.linked_source_id else None,
        linked_passage_text=f.linked_passage_text,
        missing_data_condition=f.missing_data_condition,
        suggested_action=f.suggested_action,
        created_at=f.created_at.isoformat() if f.created_at else "",
    )


@router.get("", response_model=List[MethodologyAuditFindingResponse])
async def list_methodology_findings(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Retrieve methodology audit findings across all 15 scientific dimensions."""
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    perm = PermissionService(db)
    if inv.workspace_id:
        await perm.require_workspace_membership(user.id, inv.workspace_id, min_role="viewer")

    service = MethodologyAuditService(db)
    findings = await service.list_methodology_findings(investigation_id)
    if not findings:
        findings = await service.audit_investigation(investigation_id)

    return [_to_response(f) for f in findings]


@router.post("/run", response_model=List[MethodologyAuditFindingResponse])
async def run_methodology_audit(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Re-run comprehensive methodology audit."""
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    perm = PermissionService(db)
    if inv.workspace_id:
        await perm.require_workspace_membership(user.id, inv.workspace_id, min_role="researcher")

    service = MethodologyAuditService(db)
    findings = await service.audit_investigation(investigation_id)
    return [_to_response(f) for f in findings]
