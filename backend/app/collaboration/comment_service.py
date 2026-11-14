"""Comment and threaded discussion service for NEOMON Milestone 10."""

import re
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    User,
    CommentThread,
    Comment,
    WorkspaceMember,
)
from app.collaboration.permission_service import PermissionService
from app.collaboration.notification_service import NotificationService
from app.collaboration.activity_service import ActivityService


class CommentService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.perm = PermissionService(db)
        self.notif = NotificationService(db)
        self.act = ActivityService(db)

    async def create_thread(
        self,
        workspace_id: uuid.UUID,
        target_entity_type: str,
        target_entity_id: str,
        user: User,
        content: str,
        title: Optional[str] = None,
        investigation_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Create a new discussion thread and post the initial comment."""
        await self.perm.require_workspace_membership(user.id, workspace_id, min_role="reviewer")

        clean_content = content.strip()
        if not clean_content:
            raise HTTPException(status_code=400, detail="Comment content cannot be empty.")

        thread_id = uuid.uuid4()
        thread = CommentThread(
            id=thread_id,
            workspace_id=workspace_id,
            investigation_id=investigation_id,
            target_entity_type=target_entity_type.lower(),
            target_entity_id=str(target_entity_id),
            title=title or f"Discussion on {target_entity_type}",
            status="open",
            created_by_id=user.id,
        )
        self.db.add(thread)
        await self.db.flush()

        comment = Comment(
            id=uuid.uuid4(),
            thread_id=thread.id,
            author_id=user.id,
            content=clean_content,
            is_edited=False,
            is_deleted=False,
        )
        self.db.add(comment)
        await self.db.flush()

        # Parse mentions and notify
        await self._notify_mentions(workspace_id, clean_content, user, thread.title)

        # Activity log
        await self.act.log_activity(
            workspace_id=workspace_id,
            actor_id=user.id,
            action_type="comment_thread_created",
            entity_type="comment_thread",
            entity_id=str(thread.id),
            summary=f"{user.display_name} opened discussion thread '{thread.title}' on {target_entity_type}.",
            metadata={"target_type": target_entity_type, "target_id": str(target_entity_id)},
        )
        await self.db.commit()

        return await self.get_thread(thread.id, user.id)

    async def add_comment(
        self,
        thread_id: uuid.UUID,
        user: User,
        content: str,
        parent_comment_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Add a comment or reply to an existing thread."""
        stmt = select(CommentThread).where(CommentThread.id == thread_id)
        res = await self.db.execute(stmt)
        thread = res.scalar_one_or_none()
        if not thread:
            raise HTTPException(status_code=404, detail="Comment thread not found.")

        await self.perm.require_workspace_membership(user.id, thread.workspace_id, min_role="reviewer")

        clean_content = content.strip()
        if not clean_content:
            raise HTTPException(status_code=400, detail="Comment content cannot be empty.")

        comment = Comment(
            id=uuid.uuid4(),
            thread_id=thread.id,
            author_id=user.id,
            parent_comment_id=parent_comment_id,
            content=clean_content,
            is_edited=False,
            is_deleted=False,
        )
        self.db.add(comment)
        await self.db.flush()

        # Notify thread creator if different from commenter
        if thread.created_by_id != user.id:
            await self.notif.create_notification(
                user_id=thread.created_by_id,
                workspace_id=thread.workspace_id,
                actor_id=user.id,
                event_type="comment_reply",
                title=f"New reply from {user.display_name}",
                message=f"{user.display_name} replied to thread '{thread.title}'.",
                link_url=f"/investigations/{thread.investigation_id}?tab=collaboration" if thread.investigation_id else None,
            )

        # Notify mentions
        await self._notify_mentions(thread.workspace_id, clean_content, user, thread.title)

        await self.db.commit()

        return {
            "id": str(comment.id),
            "thread_id": str(comment.thread_id),
            "author_id": str(comment.author_id),
            "author_name": user.display_name,
            "parent_comment_id": str(comment.parent_comment_id) if comment.parent_comment_id else None,
            "content": comment.content,
            "is_edited": comment.is_edited,
            "is_deleted": comment.is_deleted,
            "created_at": comment.created_at.isoformat() if comment.created_at else None,
            "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
        }

    async def list_threads(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        investigation_id: Optional[uuid.UUID] = None,
        target_entity_type: Optional[str] = None,
        target_entity_id: Optional[str] = None,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List threads matching filters in a workspace."""
        await self.perm.require_workspace_membership(user_id, workspace_id)

        stmt = (
            select(CommentThread, User.display_name)
            .join(User, User.id == CommentThread.created_by_id)
            .where(CommentThread.workspace_id == workspace_id)
        )
        if investigation_id:
            stmt = stmt.where(CommentThread.investigation_id == investigation_id)
        if target_entity_type:
            stmt = stmt.where(CommentThread.target_entity_type == target_entity_type.lower())
        if target_entity_id:
            stmt = stmt.where(CommentThread.target_entity_id == str(target_entity_id))
        if status_filter:
            stmt = stmt.where(CommentThread.status == status_filter)

        stmt = stmt.order_by(CommentThread.created_at.desc())
        res = await self.db.execute(stmt)
        rows = res.all()

        threads = []
        for thread, creator_name in rows:
            # Comment count
            c_count_res = await self.db.execute(
                select(func.count(Comment.id)).where(Comment.thread_id == thread.id)
            )
            c_count = c_count_res.scalar_one()

            threads.append({
                "id": str(thread.id),
                "workspace_id": str(thread.workspace_id),
                "investigation_id": str(thread.investigation_id) if thread.investigation_id else None,
                "target_entity_type": thread.target_entity_type,
                "target_entity_id": thread.target_entity_id,
                "title": thread.title,
                "status": thread.status,
                "created_by_id": str(thread.created_by_id),
                "creator_name": creator_name,
                "comment_count": c_count,
                "created_at": thread.created_at.isoformat() if thread.created_at else None,
                "resolved_at": thread.resolved_at.isoformat() if thread.resolved_at else None,
            })
        return threads

    async def get_thread(self, thread_id: uuid.UUID, user_id: uuid.UUID) -> Dict[str, Any]:
        """Fetch single thread with all its comments."""
        stmt = (
            select(CommentThread, User.display_name)
            .join(User, User.id == CommentThread.created_by_id)
            .where(CommentThread.id == thread_id)
        )
        res = await self.db.execute(stmt)
        row = res.first()
        if not row:
            raise HTTPException(status_code=404, detail="Thread not found.")

        thread, creator_name = row
        await self.perm.require_workspace_membership(user_id, thread.workspace_id)

        # Fetch comments
        c_stmt = (
            select(Comment, User.display_name)
            .join(User, User.id == Comment.author_id)
            .where(Comment.thread_id == thread.id)
            .order_by(Comment.created_at.asc())
        )
        c_res = await self.db.execute(c_stmt)
        c_rows = c_res.all()

        comments = []
        for c, author_name in c_rows:
            comments.append({
                "id": str(c.id),
                "thread_id": str(c.thread_id),
                "author_id": str(c.author_id),
                "author_name": author_name,
                "parent_comment_id": str(c.parent_comment_id) if c.parent_comment_id else None,
                "content": "[Comment deleted]" if c.is_deleted else c.content,
                "is_edited": c.is_edited,
                "is_deleted": c.is_deleted,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            })

        return {
            "id": str(thread.id),
            "workspace_id": str(thread.workspace_id),
            "investigation_id": str(thread.investigation_id) if thread.investigation_id else None,
            "target_entity_type": thread.target_entity_type,
            "target_entity_id": thread.target_entity_id,
            "title": thread.title,
            "status": thread.status,
            "created_by_id": str(thread.created_by_id),
            "creator_name": creator_name,
            "comments": comments,
            "created_at": thread.created_at.isoformat() if thread.created_at else None,
            "resolved_at": thread.resolved_at.isoformat() if thread.resolved_at else None,
        }

    async def resolve_thread(self, thread_id: uuid.UUID, user: User) -> bool:
        """Mark thread as resolved."""
        stmt = select(CommentThread).where(CommentThread.id == thread_id)
        res = await self.db.execute(stmt)
        thread = res.scalar_one_or_none()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found.")

        member = await self.perm.require_workspace_membership(user.id, thread.workspace_id)
        # Allowed if creator, reviewer, admin, or owner
        if thread.created_by_id != user.id and member.role not in ("reviewer", "admin", "owner"):
            raise HTTPException(status_code=403, detail="Not authorized to resolve this thread.")

        thread.status = "resolved"
        thread.resolved_by_id = user.id
        thread.resolved_at = datetime.now(timezone.utc)
        await self.db.commit()
        return True

    async def reopen_thread(self, thread_id: uuid.UUID, user: User) -> bool:
        """Reopen a resolved thread."""
        stmt = select(CommentThread).where(CommentThread.id == thread_id)
        res = await self.db.execute(stmt)
        thread = res.scalar_one_or_none()
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found.")

        await self.perm.require_workspace_membership(user.id, thread.workspace_id, min_role="reviewer")
        thread.status = "open"
        thread.resolved_at = None
        thread.resolved_by_id = None
        await self.db.commit()
        return True

    async def edit_comment(self, comment_id: uuid.UUID, user: User, new_content: str) -> Dict[str, Any]:
        """Edit comment text (only author)."""
        stmt = select(Comment).where(Comment.id == comment_id)
        res = await self.db.execute(stmt)
        comment = res.scalar_one_or_none()
        if not comment:
            raise HTTPException(status_code=404, detail="Comment not found.")

        if comment.author_id != user.id:
            raise HTTPException(status_code=403, detail="You can only edit your own comments.")

        if comment.is_deleted:
            raise HTTPException(status_code=400, detail="Cannot edit a deleted comment.")

        comment.content = new_content.strip()
        comment.is_edited = True
        comment.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return {"id": str(comment.id), "content": comment.content, "is_edited": True}

    async def delete_comment(self, comment_id: uuid.UUID, user: User) -> bool:
        """Soft-delete a comment."""
        stmt = (
            select(Comment, CommentThread)
            .join(CommentThread, CommentThread.id == Comment.thread_id)
            .where(Comment.id == comment_id)
        )
        res = await self.db.execute(stmt)
        row = res.first()
        if not row:
            raise HTTPException(status_code=404, detail="Comment not found.")

        comment, thread = row
        member = await self.perm.require_workspace_membership(user.id, thread.workspace_id)

        if comment.author_id != user.id and member.role not in ("admin", "owner"):
            raise HTTPException(status_code=403, detail="Cannot delete other users' comments.")

        comment.is_deleted = True
        comment.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return True

    async def _notify_mentions(
        self, workspace_id: uuid.UUID, content: str, actor: User, thread_title: str
    ) -> None:
        """Find @mentions and notify referenced workspace members."""
        mentions = re.findall(r"@([\w.-]+)", content)
        if not mentions:
            return

        for handle in mentions:
            # Match by email or display_name prefix
            u_stmt = (
                select(User)
                .join(WorkspaceMember, WorkspaceMember.user_id == User.id)
                .where(
                    WorkspaceMember.workspace_id == workspace_id,
                    (User.email.ilike(f"{handle}%") | User.display_name.ilike(f"%{handle}%")),
                )
            )
            u_res = await self.db.execute(u_stmt)
            target_user = u_res.scalars().first()
            if target_user and target_user.id != actor.id:
                await self.notif.create_notification(
                    user_id=target_user.id,
                    workspace_id=workspace_id,
                    actor_id=actor.id,
                    event_type="mention",
                    title=f"Mentioned by {actor.display_name}",
                    message=f"{actor.display_name} mentioned you in discussion '{thread_title}'.",
                )
