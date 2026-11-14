"""Workspace activity feed and audit trail service for NEOMON Milestone 10."""

import json
import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import WorkspaceActivity, User
from app.collaboration.permission_service import PermissionService


class ActivityService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.perm = PermissionService(db)

    async def log_activity(
        self,
        workspace_id: uuid.UUID,
        actor_id: Optional[uuid.UUID],
        action_type: str,
        entity_type: str,
        entity_id: Optional[str],
        summary: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> WorkspaceActivity:
        """Create an immutable activity log entry."""
        activity = WorkspaceActivity(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            actor_id=actor_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary,
            metadata_json=json.dumps(metadata or {}),
        )
        self.db.add(activity)
        await self.db.commit()
        await self.db.refresh(activity)
        return activity

    async def list_workspace_activity(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 50,
        action_type: Optional[str] = None,
        entity_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch activity log stream for a workspace."""
        await self.perm.require_workspace_membership(user_id, workspace_id)

        stmt = (
            select(WorkspaceActivity, User.display_name, User.email)
            .outerjoin(User, User.id == WorkspaceActivity.actor_id)
            .where(WorkspaceActivity.workspace_id == workspace_id)
        )
        if action_type:
            stmt = stmt.where(WorkspaceActivity.action_type == action_type)
        if entity_type:
            stmt = stmt.where(WorkspaceActivity.entity_type == entity_type)

        stmt = stmt.order_by(WorkspaceActivity.created_at.desc()).limit(limit)
        res = await self.db.execute(stmt)
        rows = res.all()

        activities = []
        for act, actor_name, actor_email in rows:
            activities.append({
                "id": str(act.id),
                "workspace_id": str(act.workspace_id),
                "actor_id": str(act.actor_id) if act.actor_id else None,
                "actor_name": actor_name or "System",
                "actor_email": actor_email,
                "action_type": act.action_type,
                "entity_type": act.entity_type,
                "entity_id": act.entity_id,
                "summary": act.summary,
                "metadata": act.metadata_dict,
                "created_at": act.created_at.isoformat() if act.created_at else None,
            })
        return activities
