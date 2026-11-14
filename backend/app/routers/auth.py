"""Authentication and user account router for NEOMON Milestone 10."""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_session
from app.config import get_settings
from app.models import User
from app.auth.auth_service import AuthService
from app.auth.dependencies import get_current_user, get_token_from_request
from app.auth.rate_limiter import rate_limit_auth
from app.collaboration.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    AuthTokenResponse,
    ChangePasswordRequest,
    PasswordResetRequest,
    PasswordResetConfirmRequest,
    UserProfileUpdateRequest,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        bio=user.bio,
        role=user.role,
        status=user.status,
        created_at=user.created_at.isoformat() if user.created_at else None,
    )


@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(rate_limit_auth())])
async def register(
    req: UserRegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    """Register a new user account and receive an authenticated session."""
    auth_service = AuthService(db)
    try:
        user, token = await auth_service.register_user(
            email=req.email,
            password=req.password,
            display_name=req.display_name,
            bio=req.bio,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # Set HttpOnly cookie for browser sessions
    is_prod = get_settings().environment.lower() == "production"
    response.set_cookie(
        key="neomon_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=is_prod,
        max_age=30 * 24 * 3600,
        path="/",
    )
    return AuthTokenResponse(user=_user_to_response(user), session_token=token)


@router.post("/login", response_model=AuthTokenResponse, dependencies=[Depends(rate_limit_auth())])
async def login(
    req: UserLoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    """Authenticate with email and password to receive a session."""
    auth_service = AuthService(db)
    try:
        user, token = await auth_service.login_user(
            email=req.email,
            password=req.password,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    is_prod = get_settings().environment.lower() == "production"
    response.set_cookie(
        key="neomon_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=is_prod,
        max_age=30 * 24 * 3600,
        path="/",
    )
    return AuthTokenResponse(user=_user_to_response(user), session_token=token)


@router.post("/logout")
async def logout(
    response: Response,
    token: Optional[str] = Depends(get_token_from_request),
    db: AsyncSession = Depends(get_session),
):
    """Revoke the current session and clear auth cookies."""
    if token:
        auth_service = AuthService(db)
        await auth_service.logout_session(token)
    is_prod = get_settings().environment.lower() == "production"
    response.delete_cookie(
        "neomon_session",
        path="/",
        httponly=True,
        samesite="lax",
        secure=is_prod,
    )
    return {"message": "Logged out successfully."}


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Fetch profile of current authenticated user."""
    return _user_to_response(user)


@router.patch("/profile", response_model=UserResponse)
async def update_profile(
    req: UserProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Update profile details for the authenticated user."""
    if req.display_name is not None:
        user.display_name = req.display_name.strip()
    if req.bio is not None:
        user.bio = req.bio
    await db.commit()
    await db.refresh(user)
    return _user_to_response(user)


@router.post("/password/change")
async def change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Change account password."""
    auth_service = AuthService(db)
    try:
        await auth_service.change_password(user.id, req.old_password, req.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"message": "Password updated successfully. Other active sessions revoked."}


@router.post("/password/reset-request", dependencies=[Depends(rate_limit_auth())])
async def request_password_reset(
    req: PasswordResetRequest,
    db: AsyncSession = Depends(get_session),
):
    """Request a password reset token."""
    auth_service = AuthService(db)
    token = await auth_service.request_password_reset(req.email)
    # Returns reset token in response to allow easy testing and dev workflows
    return {
        "message": "If this email is registered, a password reset token has been generated.",
        "reset_token": token,
        "reset_link": f"/reset-password?token={token}" if token else None,
    }


@router.post("/password/reset-confirm", dependencies=[Depends(rate_limit_auth())])
async def confirm_password_reset(
    req: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_session),
):
    """Complete password reset using token."""
    auth_service = AuthService(db)
    try:
        await auth_service.confirm_password_reset(req.token, req.new_password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return {"message": "Password has been reset successfully. Please login with your new password."}
