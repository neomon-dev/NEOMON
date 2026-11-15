"""Authentication dependencies for FastAPI route handlers."""

import uuid
from typing import Optional
from fastapi import Depends, Header, Cookie, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import User
from app.auth.auth_service import AuthService, consume_stream_ticket


async def get_token_from_request(
    authorization: Optional[str] = Header(None),
    neomon_session: Optional[str] = Cookie(None),
    ticket: Optional[str] = Query(None),
    token: Optional[str] = Query(None),
) -> Optional[str]:
    """Extract raw token or single-use ticket from Authorization header (Bearer), Cookie, or Query parameter."""
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    if neomon_session:
        return neomon_session.strip()
    if ticket:
        return f"ticket:{ticket.strip()}"
    if token:
        return token.strip()
    return None


async def get_current_user(
    token: Optional[str] = Depends(get_token_from_request),
    db: AsyncSession = Depends(get_session),
) -> User:
    """Resolve authenticated User or raise 401 Unauthorized.

    Strict security invariants:
    - Missing token -> 401 Unauthorized
    - Invalid token -> 401 Unauthorized
    - Expired session -> 401 Unauthorized
    - Revoked session -> 401 Unauthorized
    - Inactive / deactivated user -> 401 Unauthorized
    - Single-use ticket consumed immediately; replay -> 401 Unauthorized
    - No silent fallback to default administrator
    - No unauthenticated header impersonation
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Missing Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if token.startswith("ticket:"):
        raw_ticket = token[7:]
        user_id = consume_stream_ticket(raw_ticket)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid, expired, or already consumed stream ticket.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        user = await db.get(User, user_id)
        if not user or user.status != "active":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account associated with ticket is invalid or deactivated.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    auth_service = AuthService(db)
    user = await auth_service.validate_session(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked authentication session.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_optional_user(
    token: Optional[str] = Depends(get_token_from_request),
    db: AsyncSession = Depends(get_session),
) -> Optional[User]:
    """Resolve current user if authenticated with valid token, else return None without raising error."""
    if not token:
        return None
    try:
        auth_service = AuthService(db)
        user = await auth_service.validate_session(token)
        if user and user.status == "active":
            return user
        return None
    except Exception:
        return None
