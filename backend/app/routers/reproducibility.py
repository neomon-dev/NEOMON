"""API Router for Research Execution Manifests and Reproducibility."""

import json
import uuid
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import Investigation, ResearchExecutionManifest, User
from app.auth.dependencies import get_current_user
from app.collaboration.permission_service import PermissionService
from app.schemas_m12 import ManifestIntegrityResponse, ResearchExecutionManifestResponse
from app.research.reproducibility_service import ReproducibilityService

router = APIRouter(prefix="/api/v1/research/investigations/{investigation_id}/reproducibility", tags=["reproducibility"])


def _to_response(m: ResearchExecutionManifest) -> ResearchExecutionManifestResponse:
    def _parse(field_val, default):
        if not field_val:
            return default
        try:
            return json.loads(field_val)
        except Exception:
            return default

    return ResearchExecutionManifestResponse(
        id=str(m.id),
        investigation_id=str(m.investigation_id),
        manifest_version=m.manifest_version,
        manifest_hash=m.manifest_hash,
        research_question=m.research_question,
        config_snapshot=_parse(m.config_snapshot_json, {}),
        claim_decomposition_version=m.claim_decomposition_version,
        search_queries=_parse(m.search_queries_json, []),
        providers_used=_parse(m.providers_used_json, []),
        execution_timeline=_parse(m.execution_timeline_json, []),
        source_manifest=_parse(m.source_manifest_json, []),
        evidence_manifest=_parse(m.evidence_manifest_json, []),
        quality_assessment_snapshot=_parse(m.quality_assessment_snapshot_json, {}),
        reproducibility_status=m.reproducibility_status,
        reproducibility_notes=m.reproducibility_notes,
        parent_reproduced_manifest_id=str(m.parent_reproduced_manifest_id) if m.parent_reproduced_manifest_id else None,
        created_at=m.created_at.isoformat() if m.created_at else "",
    )


@router.get("/manifest", response_model=ResearchExecutionManifestResponse)
async def get_execution_manifest(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Retrieve the latest machine-readable reproducibility manifest."""
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    perm = PermissionService(db)
    if inv.workspace_id:
        await perm.require_workspace_membership(user.id, inv.workspace_id, min_role="viewer")

    service = ReproducibilityService(db)
    manifest = await service.get_latest_manifest(investigation_id)
    if not manifest:
        manifest = await service.generate_manifest(investigation_id)

    return _to_response(manifest)


@router.post("/manifest", response_model=ResearchExecutionManifestResponse)
async def generate_execution_manifest(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Generate and snapshot a new immutable research execution manifest with SHA-256 integrity hash."""
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    perm = PermissionService(db)
    if inv.workspace_id:
        await perm.require_workspace_membership(user.id, inv.workspace_id, min_role="researcher")

    service = ReproducibilityService(db)
    manifest = await service.generate_manifest(investigation_id)
    return _to_response(manifest)


@router.get("/manifest/verify", response_model=ManifestIntegrityResponse)
@router.post("/manifest/verify", response_model=ManifestIntegrityResponse)
async def verify_latest_manifest_integrity(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Verify cryptographic SHA-256 integrity of the latest manifest for this investigation."""
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    perm = PermissionService(db)
    if inv.workspace_id:
        await perm.require_workspace_membership(user.id, inv.workspace_id, min_role="viewer")

    service = ReproducibilityService(db)
    latest = await service.get_latest_manifest(investigation_id)
    if not latest:
        raise HTTPException(status_code=404, detail="No execution manifest found for this investigation")

    res = await service.verify_manifest_integrity(latest.id)
    return ManifestIntegrityResponse(**res)


@router.post("/manifest/{manifest_id}/verify", response_model=ManifestIntegrityResponse)
async def verify_manifest_integrity(
    investigation_id: uuid.UUID,
    manifest_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Verify cryptographic SHA-256 integrity of a research manifest."""
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    perm = PermissionService(db)
    if inv.workspace_id:
        await perm.require_workspace_membership(user.id, inv.workspace_id, min_role="viewer")

    service = ReproducibilityService(db)
    try:
        res = await service.verify_manifest_integrity(manifest_id)
        return ManifestIntegrityResponse(**res)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reproduce")
async def reproduce_investigation_run(
    investigation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Spawn a new reproduction investigation linked to the parent manifest without overwriting original history."""
    inv = await db.get(Investigation, investigation_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Investigation not found")

    perm = PermissionService(db)
    if inv.workspace_id:
        await perm.require_workspace_membership(user.id, inv.workspace_id, min_role="researcher")

    service = ReproducibilityService(db)
    try:
        new_inv = await service.reproduce_investigation_run(investigation_id, user.id)
        return {
            "status": "reproduction_created",
            "original_investigation_id": str(investigation_id),
            "reproduced_investigation_id": str(new_inv.id),
            "question": new_inv.question,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
