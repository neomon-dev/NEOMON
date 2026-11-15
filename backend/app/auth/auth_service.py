"""Authentication service for NEOMON Milestone 10."""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    User,
    UserSession,
    PasswordResetToken,
    Workspace,
    WorkspaceMember,
    NotificationPreference,
)
from app.auth.security import (
    hash_password,
    verify_password,
    generate_session_token,
    hash_token,
    validate_password_strength,
    validate_email_format,
)


def _is_expired(dt: Optional[datetime]) -> bool:
    if not dt:
        return True
    now = datetime.now(timezone.utc)
    target = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    return target < now


_sse_tickets: dict[str, tuple[uuid.UUID, datetime]] = {}


def create_stream_ticket(user_id: uuid.UUID) -> str:
    """Issue a single-use stream ticket valid for 60 seconds."""
    now = datetime.now(timezone.utc)
    expired = [k for k, (_, exp) in _sse_tickets.items() if exp < now]
    for k in expired:
        _sse_tickets.pop(k, None)
    ticket = f"st_{uuid.uuid4().hex}"
    _sse_tickets[ticket] = (user_id, now + timedelta(seconds=60))
    return ticket


def consume_stream_ticket(ticket: str) -> Optional[uuid.UUID]:
    """Validate and immediately consume (delete) a single-use stream ticket."""
    now = datetime.now(timezone.utc)
    entry = _sse_tickets.pop(ticket, None)
    if not entry:
        return None
    user_id, expires_at = entry
    if expires_at < now:
        return None
    return user_id


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(
        self,
        email: str,
        password: str,
        display_name: str,
        bio: Optional[str] = None,
        role: str = "researcher",
    ) -> Tuple[User, str]:
        """Register a new user, create their personal workspace, and issue a session token."""
        email_clean = email.strip().lower()
        if not validate_email_format(email_clean):
            raise ValueError("Invalid email format.")

        is_valid, msg = validate_password_strength(password)
        if not is_valid:
            raise ValueError(msg)

        # Check existing user
        stmt = select(User).where(User.email == email_clean)
        res = await self.db.execute(stmt)
        if res.scalar_one_or_none() is not None:
            raise ValueError("A user with this email address already exists.")

        user_id = uuid.uuid4()
        user = User(
            id=user_id,
            email=email_clean,
            password_hash=hash_password(password),
            display_name=display_name.strip() or email_clean.split("@")[0],
            bio=bio,
            role=role if role in ("admin", "researcher", "reviewer", "viewer") else "researcher",
            status="active",
        )
        self.db.add(user)
        await self.db.flush()

        # Create default personal workspace
        ws_name = f"{user.display_name}'s Workspace"
        base_slug = f"{user.display_name.lower().replace(' ', '-')}-workspace"[:100]
        ws_slug = f"{base_slug}-{str(uuid.uuid4())[:8]}"
        workspace = Workspace(
            id=uuid.uuid4(),
            name=ws_name,
            slug=ws_slug,
            description="Personal research workspace.",
            owner_id=user.id,
            status="active",
            settings_json='{"require_independent_review": false, "max_autonomous_budget": 50}',
        )
        self.db.add(workspace)
        await self.db.flush()

        # Add as owner of workspace
        member = WorkspaceMember(
            id=uuid.uuid4(),
            workspace_id=workspace.id,
            user_id=user.id,
            role="owner",
        )
        self.db.add(member)

        # Default notification preferences
        pref = NotificationPreference(
            id=uuid.uuid4(),
            user_id=user.id,
            email_notifications_enabled=True,
            in_app_notifications_enabled=True,
        )
        self.db.add(pref)

        # Create session
        token = generate_session_token()
        session = UserSession(
            id=uuid.uuid4(),
            user_id=user.id,
            session_token_hash=hash_token(token),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(user)

        return user, token

    async def login_user(
        self,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[User, str]:
        """Authenticate user credentials and issue a new session token."""
        email_clean = email.strip().lower()
        stmt = select(User).where(User.email == email_clean)
        res = await self.db.execute(stmt)
        user = res.scalar_one_or_none()

        if not user or not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password.")

        if user.status != "active":
            raise ValueError("This account has been deactivated. Please contact an administrator.")

        token = generate_session_token()
        session = UserSession(
            id=uuid.uuid4(),
            user_id=user.id,
            session_token_hash=hash_token(token),
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(user)

        return user, token

    async def validate_session(self, token: str) -> Optional[User]:
        """Validate session token and return the active User, or None if invalid/expired."""
        if not token:
            return None
        token_hash = hash_token(token)

        stmt = (
            select(User, UserSession)
            .join(UserSession, UserSession.user_id == User.id)
            .where(
                UserSession.session_token_hash == token_hash,
                UserSession.revoked_at.is_(None),
                User.status == "active",
            )
        )
        res = await self.db.execute(stmt)
        row = res.first()
        if not row:
            return None
        user, sess = row
        if _is_expired(sess.expires_at):
            return None
        return user

    async def logout_session(self, token: str) -> bool:
        """Revoke a specific session."""
        if not token:
            return False
        token_hash = hash_token(token)
        stmt = (
            update(UserSession)
            .where(UserSession.session_token_hash == token_hash, UserSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        res = await self.db.execute(stmt)
        await self.db.commit()
        return res.rowcount > 0

    async def change_password(self, user_id: uuid.UUID, old_password: str, new_password: str) -> bool:
        """Change user password, verifying current password first."""
        stmt = select(User).where(User.id == user_id)
        res = await self.db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user or not verify_password(old_password, user.password_hash):
            raise ValueError("Current password is incorrect.")

        is_valid, msg = validate_password_strength(new_password)
        if not is_valid:
            raise ValueError(msg)

        user.password_hash = hash_password(new_password)
        user.updated_at = datetime.now(timezone.utc)

        # Revoke other sessions
        revoke_stmt = (
            update(UserSession)
            .where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
            .values(revoked_at=datetime.now(timezone.utc))
        )
        await self.db.execute(revoke_stmt)
        await self.db.commit()
        return True

    async def request_password_reset(self, email: str) -> Optional[str]:
        """Create a password reset token. Returns raw token for email/dev display."""
        email_clean = email.strip().lower()
        stmt = select(User).where(User.email == email_clean)
        res = await self.db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            return None

        raw_token = generate_session_token()
        token_record = PasswordResetToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        self.db.add(token_record)
        await self.db.commit()
        return raw_token

    async def confirm_password_reset(self, token: str, new_password: str) -> bool:
        """Confirm password reset using single-use token."""
        is_valid, msg = validate_password_strength(new_password)
        if not is_valid:
            raise ValueError(msg)

        t_hash = hash_token(token)
        stmt = select(PasswordResetToken).where(
            PasswordResetToken.token_hash == t_hash,
            PasswordResetToken.used_at.is_(None),
        )
        res = await self.db.execute(stmt)
        record = res.scalar_one_or_none()
        if not record or _is_expired(record.expires_at):
            raise ValueError("Invalid, expired, or previously used reset token.")

        now = datetime.now(timezone.utc)

        # Update user password
        user_stmt = select(User).where(User.id == record.user_id)
        user_res = await self.db.execute(user_stmt)
        user = user_res.scalar_one_or_none()
        if not user:
            raise ValueError("User associated with token not found.")

        user.password_hash = hash_password(new_password)
        user.updated_at = now
        record.used_at = now

        # Revoke active sessions
        revoke_stmt = (
            update(UserSession)
            .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await self.db.execute(revoke_stmt)
        await self.db.commit()
        return True
