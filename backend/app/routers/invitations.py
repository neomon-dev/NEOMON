"""Workspace invitations router for NEOMON Milestone 10."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db import get_session
from app.models import User
from app.auth.dependencies import get_current_user
from app.auth.rate_limiter import rate_limit_auth
from app.collaboration.invitation_service import InvitationService
from app.collaboration.schemas import (
    InvitationCreateRequest,
    InvitationResponse,
    InvitationDetailResponse,
)

router = APIRouter(tags=["invitations"])


class AcceptInvitationRequest(BaseModel):
    token: str


class DeclineInvitationRequest(BaseModel):
    token: str


@router.post("/workspaces/{workspace_id}/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    workspace_id: uuid.UUID,
    req: InvitationCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Invite a new researcher, reviewer, or viewer to join the workspace."""
    service = InvitationService(db)
    result = await service.create_invitation(
        workspace_id=workspace_id,
        inviter=user,
        email=req.email,
        role=req.role,
    )
    return InvitationResponse(**result)


@router.get("/workspaces/{workspace_id}/invitations", response_model=List[InvitationResponse])
async def list_workspace_invitations(
    workspace_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List invitations for a workspace (requires ADMIN or OWNER)."""
    service = InvitationService(db)
    invites = await service.list_workspace_invitations(workspace_id, user.id)
    return [InvitationResponse(**i) for i in invites]


@router.get("/invitations/lookup", response_model=InvitationDetailResponse)
async def lookup_invitation(
    token: str = Query(..., min_length=1),
    db: AsyncSession = Depends(get_session),
):
    """Look up workspace invitation information before accepting."""
    service = InvitationService(db)
    details = await service.get_invitation_by_token(token)
    return InvitationDetailResponse(**details)


@router.post("/invitations/accept", dependencies=[Depends(rate_limit_auth())])
async def accept_invitation(
    req: AcceptInvitationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Accept an invitation to join a workspace as the authenticated user."""
    service = InvitationService(db)
    return await service.accept_invitation(req.token, user)


@router.post("/invitations/decline")
async def decline_invitation(
    req: DeclineInvitationRequest,
    db: AsyncSession = Depends(get_session),
):
    """Decline a pending workspace invitation."""
    service = InvitationService(db)
    await service.decline_invitation(req.token)
    return {"message": "Invitation declined."}


@router.delete("/workspaces/{workspace_id}/invitations/{invitation_id}")
async def revoke_invitation(
    workspace_id: uuid.UUID,
    invitation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Revoke a pending workspace invitation."""
    service = InvitationService(db)
    await service.revoke_invitation(invitation_id, workspace_id, user)
    return {"message": "Invitation revoked."}
