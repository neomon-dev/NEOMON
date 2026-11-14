"""Workspace invitation service for NEOMON Milestone 10."""

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    User,
    Workspace,
    WorkspaceMember,
    WorkspaceInvitation,
    WorkspaceActivity,
)
from app.auth.security import generate_session_token, hash_token, validate_email_format
from app.collaboration.permission_service import PermissionService


def _is_expired(dt: Optional[datetime]) -> bool:
    if not dt:
        return True
    now = datetime.now(timezone.utc)
    target = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    return target < now


class InvitationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.perm = PermissionService(db)

    async def create_invitation(
        self,
        workspace_id: uuid.UUID,
        inviter: User,
        email: str,
        role: str = "researcher",
    ) -> Dict[str, Any]:
        """Invite a user by email to join the workspace."""
        ws = await self.db.get(Workspace, workspace_id)
        if not ws or ws.status == "deleted":
            raise HTTPException(status_code=404, detail="Workspace not found.")

        allow_researcher_invites = ws.settings.get("allow_member_invitations", False) if ws.settings else False
        min_role = "researcher" if allow_researcher_invites else "admin"
        inviter_member = await self.perm.require_workspace_membership(inviter.id, workspace_id, min_role=min_role)

        clean_email = email.strip().lower()
        if not validate_email_format(clean_email):
            raise HTTPException(status_code=400, detail="Invalid email format.")

        clean_role = role.strip().lower()
        if clean_role not in ("admin", "researcher", "reviewer", "viewer"):
            raise HTTPException(status_code=400, detail="Invalid role for invitation.")

        # Vertical escalation check: cannot invite someone with a role higher than caller's own role
        from app.collaboration.permission_service import ROLE_HIERARCHY
        inviter_level = ROLE_HIERARCHY.get(inviter_member.role.lower(), 0)
        target_level = ROLE_HIERARCHY.get(clean_role, 100)
        if target_level > inviter_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot invite user with role '{clean_role}' which is higher than your own role '{inviter_member.role}'.",
            )

        # Check if already a member
        existing_user_stmt = select(User).where(User.email == clean_email)
        res_u = await self.db.execute(existing_user_stmt)
        existing_user = res_u.scalar_one_or_none()
        if existing_user:
            mem_stmt = select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == existing_user.id,
            )
            mem_res = await self.db.execute(mem_stmt)
            if mem_res.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="This user is already a member of the workspace.")

        # Revoke any prior pending invitation for this email in this workspace
        revoke_old = (
            update(WorkspaceInvitation)
            .where(
                WorkspaceInvitation.workspace_id == workspace_id,
                WorkspaceInvitation.email == clean_email,
                WorkspaceInvitation.status == "pending",
            )
            .values(status="revoked")
        )
        await self.db.execute(revoke_old)

        raw_token = generate_session_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        invitation = WorkspaceInvitation(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            inviter_id=inviter.id,
            email=clean_email,
            role=clean_role,
            token_hash=hash_token(raw_token),
            status="pending",
            expires_at=expires_at,
        )
        self.db.add(invitation)

        activity = WorkspaceActivity(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            actor_id=inviter.id,
            action_type="invitation_sent",
            entity_type="workspace_invitation",
            entity_id=str(invitation.id),
            summary=f"Invitation sent to {clean_email} with role '{clean_role}' by {inviter.display_name}.",
            metadata_json=json.dumps({"email": clean_email, "role": clean_role}),
        )
        self.db.add(activity)
        await self.db.commit()

        # Generate invite link for local/dev workflows
        invite_link = f"/invitations?token={raw_token}"
        return {
            "id": str(invitation.id),
            "workspace_id": str(workspace_id),
            "email": clean_email,
            "role": clean_role,
            "status": "pending",
            "expires_at": expires_at.isoformat(),
            "invite_token": raw_token,
            "invite_link": invite_link,
        }

    async def list_workspace_invitations(
        self, workspace_id: uuid.UUID, user_id: uuid.UUID
    ) -> List[Dict[str, Any]]:
        """List all pending and historical invitations for a workspace."""
        await self.perm.require_workspace_membership(user_id, workspace_id, min_role="admin")
        stmt = (
            select(WorkspaceInvitation, User.display_name)
            .join(User, User.id == WorkspaceInvitation.inviter_id)
            .where(WorkspaceInvitation.workspace_id == workspace_id)
            .order_by(WorkspaceInvitation.created_at.desc())
        )
        res = await self.db.execute(stmt)
        rows = res.all()

        invites = []
        for inv, inviter_name in rows:
            invites.append({
                "id": str(inv.id),
                "workspace_id": str(inv.workspace_id),
                "email": inv.email,
                "role": inv.role,
                "status": inv.status,
                "inviter_name": inviter_name,
                "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
            })
        return invites

    async def get_invitation_by_token(self, token: str) -> Dict[str, Any]:
        """Fetch invitation details by raw token for acceptance review."""
        t_hash = hash_token(token)
        stmt = (
            select(WorkspaceInvitation, Workspace.name)
            .join(Workspace, Workspace.id == WorkspaceInvitation.workspace_id)
            .where(WorkspaceInvitation.token_hash == t_hash)
        )
        res = await self.db.execute(stmt)
        row = res.first()
        if not row:
            raise HTTPException(status_code=404, detail="Invitation not found or invalid token.")

        inv, ws_name = row
        is_expired = _is_expired(inv.expires_at)
        return {
            "id": str(inv.id),
            "workspace_id": str(inv.workspace_id),
            "workspace_name": ws_name,
            "email": inv.email,
            "role": inv.role,
            "status": "expired" if is_expired and inv.status == "pending" else inv.status,
            "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
        }

    async def accept_invitation(self, token: str, user: User) -> Dict[str, Any]:
        """Accept an invitation and add the user as a member of the workspace."""
        t_hash = hash_token(token)
        stmt = (
            select(WorkspaceInvitation, Workspace)
            .join(Workspace, Workspace.id == WorkspaceInvitation.workspace_id)
            .where(
                WorkspaceInvitation.token_hash == t_hash,
                WorkspaceInvitation.status == "pending",
            )
        )
        res = await self.db.execute(stmt)
        row = res.first()
        if not row:
            raise HTTPException(status_code=400, detail="Invitation is invalid, expired, or already used.")

        inv, ws = row
        if _is_expired(inv.expires_at):
            inv.status = "expired"
            await self.db.commit()
            raise HTTPException(status_code=400, detail="Invitation has expired.")

        # Check existing membership
        mem_stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == ws.id,
            WorkspaceMember.user_id == user.id,
        )
        mem_res = await self.db.execute(mem_stmt)
        existing_mem = mem_res.scalar_one_or_none()

        if existing_mem:
            # Upgrade role if invited role has higher or different privilege
            existing_mem.role = inv.role
        else:
            new_mem = WorkspaceMember(
                id=uuid.uuid4(),
                workspace_id=ws.id,
                user_id=user.id,
                role=inv.role,
            )
            self.db.add(new_mem)

        inv.status = "accepted"

        activity = WorkspaceActivity(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            actor_id=user.id,
            action_type="invitation_accepted",
            entity_type="workspace_member",
            entity_id=str(user.id),
            summary=f"{user.display_name} ({user.email}) joined workspace '{ws.name}' as {inv.role}.",
            metadata_json=json.dumps({"role": inv.role, "user_id": str(user.id)}),
        )
        self.db.add(activity)
        await self.db.commit()

        return {
            "success": True,
            "workspace_id": str(ws.id),
            "workspace_name": ws.name,
            "role": inv.role,
        }

    async def decline_invitation(self, token: str) -> bool:
        """Decline a pending invitation."""
        t_hash = hash_token(token)
        stmt = select(WorkspaceInvitation).where(
            WorkspaceInvitation.token_hash == t_hash,
            WorkspaceInvitation.status == "pending",
        )
        res = await self.db.execute(stmt)
        inv = res.scalar_one_or_none()
        if not inv:
            raise HTTPException(status_code=404, detail="Pending invitation not found.")

        inv.status = "declined"
        await self.db.commit()
        return True

    async def revoke_invitation(
        self, invitation_id: uuid.UUID, workspace_id: uuid.UUID, user: User
    ) -> bool:
        """Revoke a pending invitation (requires ADMIN or OWNER)."""
        await self.perm.require_workspace_membership(user.id, workspace_id, min_role="admin")
        stmt = select(WorkspaceInvitation).where(
            WorkspaceInvitation.id == invitation_id,
            WorkspaceInvitation.workspace_id == workspace_id,
        )
        res = await self.db.execute(stmt)
        inv = res.scalar_one_or_none()
        if not inv:
            raise HTTPException(status_code=404, detail="Invitation not found.")

        inv.status = "revoked"
        await self.db.commit()
        return True
