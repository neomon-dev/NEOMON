"""Pydantic schemas for NEOMON Milestone 10: Auth, Workspaces & Collaboration."""

import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, EmailStr


# ==========================================
# AUTH SCHEMAS
# ==========================================

class UserRegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=120)
    bio: Optional[str] = None


class UserLoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    bio: Optional[str] = None
    role: str
    status: str
    created_at: Optional[str] = None


class AuthTokenResponse(BaseModel):
    user: UserResponse
    session_token: str
    token_type: str = "bearer"


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8, max_length=128)


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)


class UserProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    bio: Optional[str] = None


# ==========================================
# WORKSPACE SCHEMAS
# ==========================================

class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class WorkspaceUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str] = None
    owner_id: str
    status: str
    settings: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    user_role: Optional[str] = None
    member_count: int = 0
    investigation_count: int = 0


class WorkspaceMemberResponse(BaseModel):
    id: str
    workspace_id: str
    user_id: str
    email: str
    display_name: str
    role: str
    status: str
    joined_at: Optional[str] = None


class WorkspaceMemberRoleUpdateRequest(BaseModel):
    role: str


class TransferOwnershipRequest(BaseModel):
    new_owner_id: uuid.UUID


# ==========================================
# INVITATION SCHEMAS
# ==========================================

class InvitationCreateRequest(BaseModel):
    email: str
    role: str = "researcher"


class InvitationResponse(BaseModel):
    id: str
    workspace_id: str
    email: str
    role: str
    status: str
    inviter_name: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: Optional[str] = None
    invite_token: Optional[str] = None
    invite_link: Optional[str] = None


class InvitationDetailResponse(BaseModel):
    id: str
    workspace_id: str
    workspace_name: str
    email: str
    role: str
    status: str
    expires_at: Optional[str] = None


# ==========================================
# COMMENT & DISCUSSION SCHEMAS
# ==========================================

class ThreadCreateRequest(BaseModel):
    target_entity_type: str
    target_entity_id: str
    title: Optional[str] = None
    content: str = Field(min_length=1)
    investigation_id: Optional[uuid.UUID] = None


class CommentCreateRequest(BaseModel):
    content: str = Field(min_length=1)
    parent_comment_id: Optional[uuid.UUID] = None


class CommentUpdateRequest(BaseModel):
    content: str = Field(min_length=1)


class CommentResponse(BaseModel):
    id: str
    thread_id: str
    author_id: str
    author_name: str
    parent_comment_id: Optional[str] = None
    content: str
    is_edited: bool = False
    is_deleted: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ThreadResponse(BaseModel):
    id: str
    workspace_id: str
    investigation_id: Optional[str] = None
    target_entity_type: str
    target_entity_id: str
    title: Optional[str] = None
    status: str
    created_by_id: str
    creator_name: str
    comment_count: int = 0
    comments: List[CommentResponse] = Field(default_factory=list)
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None


# ==========================================
# EVIDENCE ANNOTATION SCHEMAS
# ==========================================

class AnnotationCreateRequest(BaseModel):
    investigation_id: uuid.UUID
    evidence_id: uuid.UUID
    annotation_type: str  # supporting, contradicting, methodological_concern, credibility_concern, relevance_question, general_note
    comment: str = Field(min_length=1)
    reviewer_rationale: Optional[str] = None


class AnnotationStatusUpdateRequest(BaseModel):
    status: str  # open, resolved, dismissed
    reviewer_rationale: Optional[str] = None


class AnnotationResponse(BaseModel):
    id: str
    workspace_id: str
    investigation_id: str
    evidence_id: str
    author_id: str
    author_name: str
    annotation_type: str
    comment: str
    reviewer_rationale: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ==========================================
# REVIEW & DECISION SCHEMAS
# ==========================================

class ReviewRequestCreate(BaseModel):
    investigation_id: uuid.UUID
    target_type: str  # investigation, report, hypothesis, claim_synthesis
    target_id: str
    title: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    target_version: Optional[str] = None
    requires_independent_review: bool = True


class ReviewDecisionSubmit(BaseModel):
    decision: str  # approved, rejected, changes_requested
    rationale: str = Field(min_length=1)


class ReviewDecisionResponse(BaseModel):
    id: str
    reviewer_id: str
    reviewer_name: str
    decision: str
    rationale: str
    created_at: Optional[str] = None


class ReviewRequestResponse(BaseModel):
    id: str
    workspace_id: str
    investigation_id: str
    target_type: str
    target_id: str
    target_version: Optional[str] = None
    requester_id: str
    requester_name: str
    title: str
    description: Optional[str] = None
    status: str
    requires_independent_review: bool
    decisions: List[ReviewDecisionResponse] = Field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ==========================================
# NOTIFICATION & ACTIVITY SCHEMAS
# ==========================================

class NotificationResponse(BaseModel):
    id: str
    workspace_id: Optional[str] = None
    actor_id: Optional[str] = None
    actor_name: str
    event_type: str
    title: str
    message: str
    link_url: Optional[str] = None
    is_read: bool
    created_at: Optional[str] = None


class NotificationPreferenceResponse(BaseModel):
    user_id: str
    email_notifications_enabled: bool
    in_app_notifications_enabled: bool


class NotificationPreferenceUpdateRequest(BaseModel):
    email_notifications_enabled: bool
    in_app_notifications_enabled: bool


class ActivityResponse(BaseModel):
    id: str
    workspace_id: str
    actor_id: Optional[str] = None
    actor_name: str
    actor_email: Optional[str] = None
    action_type: str
    entity_type: str
    entity_id: Optional[str] = None
    summary: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[str] = None
