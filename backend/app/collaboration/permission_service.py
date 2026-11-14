"""Central Role-Based Access Control (RBAC) and Security Authority for NEOMON Workspaces."""

import uuid
from typing import Optional, List
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    User,
    Workspace,
    WorkspaceMember,
    Investigation,
    ReviewRequest,
)

# Role privilege hierarchy (higher integer = higher authority)
ROLE_HIERARCHY = {
    "viewer": 10,
    "reviewer": 20,
    "researcher": 30,
    "admin": 40,
    "owner": 50,
}

DEFAULT_GLOBAL_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


class PermissionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_user_workspace_membership(
        self, user_id: uuid.UUID, workspace_id: uuid.UUID
    ) -> Optional[WorkspaceMember]:
        """Fetch active membership record for user in workspace."""
        stmt = (
            select(WorkspaceMember)
            .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
                Workspace.status != "deleted",
            )
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_workspaces(self, user_id: uuid.UUID) -> List[uuid.UUID]:
        """Return list of workspace IDs where the user has active membership."""
        stmt = (
            select(WorkspaceMember.workspace_id)
            .join(Workspace, Workspace.id == WorkspaceMember.workspace_id)
            .where(
                WorkspaceMember.user_id == user_id,
                Workspace.status != "deleted",
            )
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def require_workspace_membership(
        self, user_id: uuid.UUID, workspace_id: uuid.UUID, min_role: Optional[str] = None
    ) -> WorkspaceMember:
        """Enforce that user is a member of the workspace with at least min_role."""
        member = await self.get_user_workspace_membership(user_id, workspace_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not a member of this workspace.",
            )

        if min_role:
            required_level = ROLE_HIERARCHY.get(min_role.lower(), 100)
            user_level = ROLE_HIERARCHY.get(member.role.lower(), 0)
            if user_level < required_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: Requires at least '{min_role}' role in this workspace.",
                )

        return member

    async def check_investigation_access(
        self,
        user: User,
        investigation_id: uuid.UUID,
        required_capability: str = "read",  # "read", "write", "comment", "review"
    ) -> Investigation:
        """Validate that user has access to the target investigation within its workspace."""
        stmt = select(Investigation).where(Investigation.id == investigation_id)
        res = await self.db.execute(stmt)
        investigation = res.scalar_one_or_none()
        if not investigation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Investigation not found.",
            )

        # Enforce tenancy: resolve workspace (fall back to default global workspace if unassigned)
        ws_id = investigation.workspace_id or DEFAULT_GLOBAL_WORKSPACE_ID
        member = await self.get_user_workspace_membership(user.id, ws_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You are not a member of the workspace owning this investigation.",
            )

        user_level = ROLE_HIERARCHY.get(member.role.lower(), 0)

        if required_capability == "read":
            if user_level < ROLE_HIERARCHY["viewer"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions to view this investigation.",
                )
        elif required_capability == "comment":
            if user_level < ROLE_HIERARCHY["reviewer"] and member.role.lower() != "researcher":
                # Both reviewer and researcher can comment
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Viewers cannot participate in discussions or annotations.",
                )
        elif required_capability == "write":
            # Must be researcher, admin, or owner to run research, add claims/evidence, modify investigation
            if user_level < ROLE_HIERARCHY["researcher"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Requires 'researcher', 'admin', or 'owner' role to modify this investigation.",
                )
        elif required_capability == "review":
            # Must be reviewer, admin, or owner
            if user_level < ROLE_HIERARCHY["reviewer"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Requires 'reviewer', 'admin', or 'owner' role to review investigations.",
                )

        return investigation

    def validate_self_approval_guard(
        self,
        user_id: uuid.UUID,
        review_request: ReviewRequest,
        require_independent: bool = True,
    ) -> None:
        """Enforces that a user cannot approve their own review request if independent review is required."""
        if require_independent and review_request.requester_id == user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Self-approval guard: Independent peer review is required. You cannot approve your own review request.",
            )

    def can_review_request(self, user: User, review_request: ReviewRequest) -> bool:
        """Return True if user can submit a decision on this review request, False if self-approval blocked."""
        if review_request.requires_independent_review and review_request.requester_id == user.id:
            return False
        return True
