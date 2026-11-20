"""Workspace router for NEOMON Milestone 10."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import User
from app.auth.dependencies import get_current_user
from app.collaboration.workspace_service import WorkspaceService
from app.collaboration.activity_service import ActivityService
from app.collaboration.schemas import (
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
    WorkspaceResponse,
    WorkspaceMemberResponse,
    WorkspaceMemberRoleUpdateRequest,
    TransferOwnershipRequest,
    ActivityResponse,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    req: WorkspaceCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Create a new research workspace."""
    service = WorkspaceService(db)
    ws = await service.create_workspace(
        user=user,
        name=req.name,
        description=req.description,
        settings=req.settings,
    )
    details = await service.get_workspace(ws.id, user.id)
    return WorkspaceResponse(**details)


@router.get("", response_model=List[WorkspaceResponse])
async def list_workspaces(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List all workspaces accessible to the authenticated user."""
    service = WorkspaceService(db)
    items = await service.list_user_workspaces(user.id)
    return [WorkspaceResponse(**item) for item in items]


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Get single workspace metadata and current user's membership."""
    service = WorkspaceService(db)
    details = await service.get_workspace(workspace_id, user.id)
    return WorkspaceResponse(**details)


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: uuid.UUID,
    req: WorkspaceUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Update workspace name, description, or policy settings."""
    service = WorkspaceService(db)
    details = await service.update_workspace(
        workspace_id=workspace_id,
        user=user,
        name=req.name,
        description=req.description,
        settings=req.settings,
    )
    return WorkspaceResponse(**details)


@router.post("/{workspace_id}/archive")
async def archive_workspace(
    workspace_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Archive a workspace (requires ADMIN or OWNER)."""
    service = WorkspaceService(db)
    await service.archive_workspace(workspace_id, user)
    return {"message": "Workspace archived successfully."}


@router.post("/{workspace_id}/restore")
async def restore_workspace(
    workspace_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Restore an archived workspace."""
    service = WorkspaceService(db)
    await service.restore_workspace(workspace_id, user)
    return {"message": "Workspace restored successfully."}


@router.get("/{workspace_id}/members", response_model=List[WorkspaceMemberResponse])
async def list_members(
    workspace_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List members of a workspace."""
    service = WorkspaceService(db)
    members = await service.list_members(workspace_id, user.id)
    return [WorkspaceMemberResponse(**m) for m in members]


@router.patch("/{workspace_id}/members/{target_user_id}")
async def update_member_role(
    workspace_id: uuid.UUID,
    target_user_id: uuid.UUID,
    req: WorkspaceMemberRoleUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Change role of a workspace member."""
    service = WorkspaceService(db)
    return await service.update_member_role(workspace_id, target_user_id, req.role, user)


@router.delete("/{workspace_id}/members/{target_user_id}")
async def remove_member(
    workspace_id: uuid.UUID,
    target_user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Remove a member from the workspace."""
    service = WorkspaceService(db)
    await service.remove_member(workspace_id, target_user_id, user)
    return {"message": "Member removed from workspace."}


@router.post("/{workspace_id}/transfer-ownership")
async def transfer_ownership(
    workspace_id: uuid.UUID,
    req: TransferOwnershipRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Transfer ownership of the workspace to another member (OWNER only)."""
    service = WorkspaceService(db)
    await service.transfer_ownership(workspace_id, req.new_owner_id, user)
    return {"message": "Workspace ownership transferred successfully."}


@router.get("/{workspace_id}/activity", response_model=List[ActivityResponse])
async def get_workspace_activity(
    workspace_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=200),
    action_type: Optional[str] = None,
    entity_type: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Fetch immutable activity audit trail for the workspace."""
    act_service = ActivityService(db)
    activities = await act_service.list_workspace_activity(
        workspace_id=workspace_id,
        user_id=user.id,
        limit=limit,
        action_type=action_type,
        entity_type=entity_type,
    )
    return [ActivityResponse(**a) for a in activities]
