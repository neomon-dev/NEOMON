"""Workspace management service for NEOMON Milestone 10."""

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    User,
    Workspace,
    WorkspaceMember,
    Investigation,
    WorkspaceActivity,
)
from app.collaboration.permission_service import PermissionService


class WorkspaceService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.perm = PermissionService(db)

    async def create_workspace(
        self,
        user: User,
        name: str,
        description: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Workspace:
        """Create a new workspace and make the user its OWNER."""
        name_clean = name.strip()
        if not name_clean:
            raise HTTPException(status_code=400, detail="Workspace name cannot be empty.")

        base_slug = name_clean.lower().replace(" ", "-")[:80]
        slug = f"{base_slug}-{str(uuid.uuid4())[:8]}"

        default_settings = {
            "require_independent_review": True,
            "max_autonomous_budget": 50,
            "allow_member_invitations": True,
        }
        if settings:
            default_settings.update(settings)

        ws_id = uuid.uuid4()
        workspace = Workspace(
            id=ws_id,
            name=name_clean,
            slug=slug,
            description=description,
            owner_id=user.id,
            status="active",
            settings_json=json.dumps(default_settings),
        )
        self.db.add(workspace)
        await self.db.flush()

        member = WorkspaceMember(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            user_id=user.id,
            role="owner",
        )
        self.db.add(member)

        # Log activity
        activity = WorkspaceActivity(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            actor_id=user.id,
            action_type="workspace_created",
            entity_type="workspace",
            entity_id=str(workspace.id),
            summary=f"Workspace '{workspace.name}' was created by {user.display_name}.",
            metadata_json=json.dumps({"name": workspace.name, "slug": workspace.slug}),
        )
        self.db.add(activity)

        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace

    async def list_user_workspaces(self, user_id: uuid.UUID) -> List[Dict[str, Any]]:
        """List all workspaces the user is a member of, including membership role and stats."""
        stmt = (
            select(
                Workspace,
                WorkspaceMember.role,
                func.count(Investigation.id).label("investigation_count"),
            )
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .outerjoin(Investigation, Investigation.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .group_by(Workspace.id, WorkspaceMember.role)
            .order_by(Workspace.created_at.desc())
        )
        res = await self.db.execute(stmt)
        rows = res.all()

        workspaces = []
        for ws, role, inv_count in rows:
            # Get member count
            member_stmt = select(func.count(WorkspaceMember.id)).where(WorkspaceMember.workspace_id == ws.id)
            mem_count_res = await self.db.execute(member_stmt)
            mem_count = mem_count_res.scalar_one()

            workspaces.append({
                "id": str(ws.id),
                "name": ws.name,
                "slug": ws.slug,
                "description": ws.description,
                "owner_id": str(ws.owner_id),
                "status": ws.status,
                "settings": ws.settings,
                "created_at": ws.created_at.isoformat() if ws.created_at else None,
                "user_role": role,
                "member_count": mem_count,
                "investigation_count": inv_count,
            })
        return workspaces

    async def get_workspace(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> Dict[str, Any]:
        """Get details of a single workspace if the user has access."""
        member = await self.perm.require_workspace_membership(user_id, workspace_id)
        stmt = select(Workspace).where(Workspace.id == workspace_id)
        res = await self.db.execute(stmt)
        ws = res.scalar_one_or_none()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found.")

        # Counts
        inv_count_res = await self.db.execute(
            select(func.count(Investigation.id)).where(Investigation.workspace_id == ws.id)
        )
        inv_count = inv_count_res.scalar_one()

        mem_count_res = await self.db.execute(
            select(func.count(WorkspaceMember.id)).where(WorkspaceMember.workspace_id == ws.id)
        )
        mem_count = mem_count_res.scalar_one()

        return {
            "id": str(ws.id),
            "name": ws.name,
            "slug": ws.slug,
            "description": ws.description,
            "owner_id": str(ws.owner_id),
            "status": ws.status,
            "settings": ws.settings,
            "created_at": ws.created_at.isoformat() if ws.created_at else None,
            "updated_at": ws.updated_at.isoformat() if ws.updated_at else None,
            "user_role": member.role,
            "member_count": mem_count,
            "investigation_count": inv_count,
        }

    async def update_workspace(
        self,
        workspace_id: uuid.UUID,
        user: User,
        name: Optional[str] = None,
        description: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update workspace details or settings (requires ADMIN or OWNER)."""
        await self.perm.require_workspace_membership(user.id, workspace_id, min_role="admin")
        stmt = select(Workspace).where(Workspace.id == workspace_id)
        res = await self.db.execute(stmt)
        ws = res.scalar_one_or_none()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found.")

        if name is not None:
            clean_name = name.strip()
            if not clean_name:
                raise HTTPException(status_code=400, detail="Workspace name cannot be empty.")
            ws.name = clean_name

        if description is not None:
            ws.description = description

        if settings is not None:
            current_settings = ws.settings
            current_settings.update(settings)
            ws.settings_json = json.dumps(current_settings)

        ws.updated_at = datetime.now(timezone.utc)

        activity = WorkspaceActivity(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            actor_id=user.id,
            action_type="workspace_updated",
            entity_type="workspace",
            entity_id=str(ws.id),
            summary=f"Workspace settings updated by {user.display_name}.",
            metadata_json=json.dumps({"updated_by": str(user.id)}),
        )
        self.db.add(activity)
        await self.db.commit()
        return await self.get_workspace(workspace_id, user.id)

    async def archive_workspace(self, workspace_id: uuid.UUID, user: User) -> bool:
        """Archive workspace (requires ADMIN or OWNER)."""
        await self.perm.require_workspace_membership(user.id, workspace_id, min_role="admin")
        stmt = select(Workspace).where(Workspace.id == workspace_id)
        res = await self.db.execute(stmt)
        ws = res.scalar_one_or_none()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found.")

        ws.status = "archived"
        ws.updated_at = datetime.now(timezone.utc)

        activity = WorkspaceActivity(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            actor_id=user.id,
            action_type="workspace_archived",
            entity_type="workspace",
            entity_id=str(ws.id),
            summary=f"Workspace '{ws.name}' was archived by {user.display_name}.",
            metadata_json="{}",
        )
        self.db.add(activity)
        await self.db.commit()
        return True

    async def restore_workspace(self, workspace_id: uuid.UUID, user: User) -> bool:
        """Restore archived workspace (requires ADMIN or OWNER)."""
        await self.perm.require_workspace_membership(user.id, workspace_id, min_role="admin")
        stmt = select(Workspace).where(Workspace.id == workspace_id)
        res = await self.db.execute(stmt)
        ws = res.scalar_one_or_none()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found.")

        ws.status = "active"
        ws.updated_at = datetime.now(timezone.utc)

        activity = WorkspaceActivity(
            id=uuid.uuid4(),
            workspace_id=ws.id,
            actor_id=user.id,
            action_type="workspace_restored",
            entity_type="workspace",
            entity_id=str(ws.id),
            summary=f"Workspace '{ws.name}' was restored by {user.display_name}.",
            metadata_json="{}",
        )
        self.db.add(activity)
        await self.db.commit()
        return True

    async def list_members(self, workspace_id: uuid.UUID, user_id: uuid.UUID) -> List[Dict[str, Any]]:
        """List members of a workspace."""
        await self.perm.require_workspace_membership(user_id, workspace_id)
        stmt = (
            select(WorkspaceMember, User)
            .join(User, User.id == WorkspaceMember.user_id)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .order_by(WorkspaceMember.joined_at.asc())
        )
        res = await self.db.execute(stmt)
        rows = res.all()

        members = []
        for mem, u in rows:
            members.append({
                "id": str(mem.id),
                "workspace_id": str(mem.workspace_id),
                "user_id": str(u.id),
                "email": u.email,
                "display_name": u.display_name,
                "role": mem.role,
                "status": u.status,
                "joined_at": mem.joined_at.isoformat() if mem.joined_at else None,
            })
        return members

    async def update_member_role(
        self, workspace_id: uuid.UUID, target_user_id: uuid.UUID, new_role: str, actor: User
    ) -> Dict[str, Any]:
        """Update role of a member in workspace (requires ADMIN or OWNER)."""
        actor_mem = await self.perm.require_workspace_membership(actor.id, workspace_id, min_role="admin")
        clean_role = new_role.strip().lower()
        if clean_role not in ("admin", "researcher", "reviewer", "viewer"):
            raise HTTPException(status_code=400, detail="Invalid role specified.")

        stmt = select(Workspace).where(Workspace.id == workspace_id)
        ws_res = await self.db.execute(stmt)
        ws = ws_res.scalar_one_or_none()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found.")

        # Prevent changing owner's role through this method
        if ws.owner_id == target_user_id:
            raise HTTPException(
                status_code=400,
                detail="Cannot change role of workspace owner. Use transfer ownership instead.",
            )

        # Only owner can promote/demote admins
        if clean_role == "admin" and actor_mem.role != "owner":
            raise HTTPException(status_code=403, detail="Only workspace owner can promote members to admin.")

        target_stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == target_user_id,
        )
        target_res = await self.db.execute(target_stmt)
        target_mem = target_res.scalar_one_or_none()
        if not target_mem:
            raise HTTPException(status_code=404, detail="Target user is not a member of this workspace.")

        old_role = target_mem.role
        target_mem.role = clean_role
        target_mem.updated_at = datetime.now(timezone.utc)

        activity = WorkspaceActivity(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            actor_id=actor.id,
            action_type="member_role_updated",
            entity_type="workspace_member",
            entity_id=str(target_user_id),
            summary=f"Role for user {target_user_id} was updated from {old_role} to {clean_role} by {actor.display_name}.",
            metadata_json=json.dumps({"target_user_id": str(target_user_id), "old_role": old_role, "new_role": clean_role}),
        )
        self.db.add(activity)
        await self.db.commit()

        return {"user_id": str(target_user_id), "role": clean_role}

    async def remove_member(
        self, workspace_id: uuid.UUID, target_user_id: uuid.UUID, actor: User
    ) -> bool:
        """Remove a member from the workspace (requires ADMIN or OWNER, or user leaving voluntarily)."""
        actor_mem = await self.perm.require_workspace_membership(actor.id, workspace_id)
        is_self_removal = actor.id == target_user_id

        if not is_self_removal and actor_mem.role not in ("owner", "admin"):
            raise HTTPException(status_code=403, detail="Requires admin or owner privileges to remove members.")

        stmt = select(Workspace).where(Workspace.id == workspace_id)
        ws_res = await self.db.execute(stmt)
        ws = ws_res.scalar_one_or_none()
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace not found.")

        if ws.owner_id == target_user_id:
            raise HTTPException(status_code=400, detail="Workspace owner cannot be removed. Transfer ownership first.")

        del_stmt = delete(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == target_user_id,
        )
        await self.db.execute(del_stmt)

        activity = WorkspaceActivity(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            actor_id=actor.id,
            action_type="member_removed",
            entity_type="workspace_member",
            entity_id=str(target_user_id),
            summary=f"Member {target_user_id} was removed from workspace by {actor.display_name}.",
            metadata_json=json.dumps({"target_user_id": str(target_user_id)}),
        )
        self.db.add(activity)
        await self.db.commit()
        return True

    async def transfer_ownership(
        self, workspace_id: uuid.UUID, new_owner_id: uuid.UUID, current_owner: User
    ) -> bool:
        """Transfer workspace ownership from current owner to another member (requires OWNER)."""
        await self.perm.require_workspace_membership(current_owner.id, workspace_id, min_role="owner")

        if current_owner.id == new_owner_id:
            raise HTTPException(status_code=400, detail="Target user is already the owner.")

        # Check new owner is a member
        new_mem_stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == new_owner_id,
        )
        new_mem_res = await self.db.execute(new_mem_stmt)
        new_mem = new_mem_res.scalar_one_or_none()
        if not new_mem:
            raise HTTPException(status_code=404, detail="New owner must already be an active member of the workspace.")

        # Check current owner membership
        curr_mem_stmt = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_owner.id,
        )
        curr_mem_res = await self.db.execute(curr_mem_stmt)
        curr_mem = curr_mem_res.scalar_one_or_none()

        ws_stmt = select(Workspace).where(Workspace.id == workspace_id)
        ws_res = await self.db.execute(ws_stmt)
        ws = ws_res.scalar_one()

        ws.owner_id = new_owner_id
        ws.updated_at = datetime.now(timezone.utc)
        new_mem.role = "owner"
        if curr_mem:
            curr_mem.role = "admin"  # Previous owner becomes admin

        activity = WorkspaceActivity(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            actor_id=current_owner.id,
            action_type="ownership_transferred",
            entity_type="workspace",
            entity_id=str(workspace_id),
            summary=f"Workspace ownership transferred to user {new_owner_id} by {current_owner.display_name}.",
            metadata_json=json.dumps({"new_owner_id": str(new_owner_id), "previous_owner_id": str(current_owner.id)}),
        )
        self.db.add(activity)
        await self.db.commit()
        return True
