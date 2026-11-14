"""Notification service for NEOMON Milestone 10."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification, NotificationPreference, User


class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_preferences(self, user_id: uuid.UUID) -> NotificationPreference:
        """Fetch or initialize notification preferences for user."""
        stmt = select(NotificationPreference).where(NotificationPreference.user_id == user_id)
        res = await self.db.execute(stmt)
        pref = res.scalar_one_or_none()
        if not pref:
            pref = NotificationPreference(
                id=uuid.uuid4(),
                user_id=user_id,
                email_notifications_enabled=True,
                in_app_notifications_enabled=True,
            )
            self.db.add(pref)
            await self.db.commit()
            await self.db.refresh(pref)
        return pref

    async def create_notification(
        self,
        user_id: uuid.UUID,
        workspace_id: Optional[uuid.UUID],
        event_type: str,
        title: str,
        message: str,
        actor_id: Optional[uuid.UUID] = None,
        link_url: Optional[str] = None,
    ) -> Optional[Notification]:
        """Emit an in-app notification if user preferences allow."""
        # Don't notify oneself
        if actor_id and actor_id == user_id:
            return None

        pref = await self.get_or_create_preferences(user_id)
        if not pref.in_app_notifications_enabled:
            return None

        notif = Notification(
            id=uuid.uuid4(),
            user_id=user_id,
            workspace_id=workspace_id,
            actor_id=actor_id,
            event_type=event_type,
            title=title,
            message=message,
            link_url=link_url,
            is_read=False,
        )
        self.db.add(notif)
        await self.db.commit()
        await self.db.refresh(notif)
        return notif

    async def list_notifications(
        self, user_id: uuid.UUID, limit: int = 50, unread_only: bool = False
    ) -> List[Dict[str, Any]]:
        """List notifications for a user."""
        stmt = (
            select(Notification, User.display_name)
            .outerjoin(User, User.id == Notification.actor_id)
            .where(Notification.user_id == user_id)
        )
        if unread_only:
            stmt = stmt.where(Notification.is_read.is_(False))

        stmt = stmt.order_by(Notification.created_at.desc()).limit(limit)
        res = await self.db.execute(stmt)
        rows = res.all()

        notifications = []
        for notif, actor_name in rows:
            notifications.append({
                "id": str(notif.id),
                "workspace_id": str(notif.workspace_id) if notif.workspace_id else None,
                "actor_id": str(notif.actor_id) if notif.actor_id else None,
                "actor_name": actor_name or "System",
                "event_type": notif.event_type,
                "title": notif.title,
                "message": notif.message,
                "link_url": notif.link_url,
                "is_read": notif.is_read,
                "created_at": notif.created_at.isoformat() if notif.created_at else None,
            })
        return notifications

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        """Get number of unread notifications for user."""
        stmt = select(func.count(Notification.id)).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
        res = await self.db.execute(stmt)
        return res.scalar_one()

    async def mark_as_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Mark a single notification as read."""
        stmt = (
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(is_read=True)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.rowcount > 0

    async def mark_all_as_read(self, user_id: uuid.UUID) -> int:
        """Mark all notifications as read for a user."""
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read.is_(False))
            .values(is_read=True)
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.rowcount

    async def update_preferences(
        self, user_id: uuid.UUID, email_enabled: bool, in_app_enabled: bool
    ) -> NotificationPreference:
        """Update notification settings for user."""
        pref = await self.get_or_create_preferences(user_id)
        pref.email_notifications_enabled = email_enabled
        pref.in_app_notifications_enabled = in_app_enabled
        pref.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(pref)
        return pref
