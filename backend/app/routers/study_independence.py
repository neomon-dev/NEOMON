"""API Router for Study Independence and Cluster Validation."""

import json
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Investigation, StudyIndependenceCluster, User
from app.auth.dependencies import get_current_user
from app.collaboration.permission_service import PermissionService
from app.schemas_m12 import StudyClusterResponse
from app.research.study_independence_service import StudyIndependenceService

router = APIRouter(prefix="/research/investigations/{investigation_id}/study-independence", tags=["study-independence"])


def _to_response(c: StudyIndependenceCluster) -> StudyClusterResponse:
    member_ids = []
    try:
        if c.member_source_ids_json:
            member_ids = json.loads(c.member_source_ids_json)
    except Exception:
        pass

    shared_attrs = {}
    try:
        if c.shared_attributes_json:
            shared_attrs = json.loads(c.shared_attributes_json)
    except Exception:
        pass

    return StudyClusterResponse(
        id=str(c.id),
        investigation_id=str(c.investigation_id),
        cluster_label=c.cluster_label,
        primary_source_id=str(c.primary_source_id) if c.primary_source_id else None,
        member_source_ids=member_ids,
        relationship_category=c.relationship_category,
        confidence=c.confidence,
        evidence_rationale=c.evidence_rationale,
        shared_attributes=shared_attrs,
        created_at=c.created_at.isoformat() if c.created_at else "",
    )


@router.get("", response_model=List[StudyClusterResponse])
async def list_study_clusters(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Retrieve study independence clusters."""
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    perm = PermissionService(db)
    if inv.workspace_id:
        await perm.require_workspace_membership(user.id, inv.workspace_id, min_role="viewer")

    service = StudyIndependenceService(db)
    clusters = await service.list_study_clusters(investigation_id)
    if not clusters:
        clusters = await service.analyze_and_persist_clusters(investigation_id)

    return [_to_response(c) for c in clusters]


@router.post("/analyze", response_model=List[StudyClusterResponse])
async def analyze_study_independence(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Re-run study independence clustering on all sources."""
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    perm = PermissionService(db)
    if inv.workspace_id:
        await perm.require_workspace_membership(user.id, inv.workspace_id, min_role="researcher")

    service = StudyIndependenceService(db)
    clusters = await service.analyze_and_persist_clusters(investigation_id)
    return [_to_response(c) for c in clusters]
