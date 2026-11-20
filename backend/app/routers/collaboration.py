"""Collaboration router for discussions, annotations, reviews, and notifications."""

import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.models import User
from app.auth.dependencies import get_current_user
from app.collaboration.comment_service import CommentService
from app.collaboration.annotation_service import AnnotationService
from app.collaboration.review_service import ReviewService
from app.collaboration.notification_service import NotificationService
from app.collaboration.schemas import (
    ThreadCreateRequest,
    CommentCreateRequest,
    CommentUpdateRequest,
    ThreadResponse,
    CommentResponse,
    AnnotationCreateRequest,
    AnnotationStatusUpdateRequest,
    AnnotationResponse,
    ReviewRequestCreate,
    ReviewDecisionSubmit,
    ReviewRequestResponse,
    NotificationResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdateRequest,
)

router = APIRouter(prefix="/collaboration", tags=["collaboration"])


# ==========================================
# THREADS & COMMENTS
# ==========================================

@router.post("/threads", response_model=ThreadResponse, status_code=status.HTTP_201_CREATED)
async def create_thread(
    req: ThreadCreateRequest,
    workspace_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Open a new discussion thread on an investigation or research artifact."""
    service = CommentService(db)
    thread = await service.create_thread(
        workspace_id=workspace_id,
        target_entity_type=req.target_entity_type,
        target_entity_id=req.target_entity_id,
        user=user,
        content=req.content,
        title=req.title,
        investigation_id=req.investigation_id,
    )
    return ThreadResponse(**thread)


@router.get("/threads", response_model=List[ThreadResponse])
async def list_threads(
    workspace_id: uuid.UUID = Query(...),
    investigation_id: Optional[uuid.UUID] = None,
    target_entity_type: Optional[str] = None,
    target_entity_id: Optional[str] = None,
    status: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List discussion threads."""
    service = CommentService(db)
    threads = await service.list_threads(
        workspace_id=workspace_id,
        user_id=user.id,
        investigation_id=investigation_id,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        status_filter=status,
    )
    return [ThreadResponse(**t) for t in threads]


@router.get("/threads/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Fetch complete discussion thread and its comments."""
    service = CommentService(db)
    thread = await service.get_thread(thread_id, user.id)
    return ThreadResponse(**thread)


@router.post("/threads/{thread_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
async def add_comment(
    thread_id: uuid.UUID,
    req: CommentCreateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Post a comment or reply in an existing thread."""
    service = CommentService(db)
    comment = await service.add_comment(
        thread_id=thread_id,
        user=user,
        content=req.content,
        parent_comment_id=req.parent_comment_id,
    )
    return CommentResponse(**comment)


@router.post("/threads/{thread_id}/resolve")
async def resolve_thread(
    thread_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Mark discussion thread as resolved."""
    service = CommentService(db)
    await service.resolve_thread(thread_id, user)
    return {"message": "Thread marked as resolved."}


@router.post("/threads/{thread_id}/reopen")
async def reopen_thread(
    thread_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Reopen a resolved discussion thread."""
    service = CommentService(db)
    await service.reopen_thread(thread_id, user)
    return {"message": "Thread reopened."}


@router.patch("/comments/{comment_id}", response_model=Dict[str, Any])
async def edit_comment(
    comment_id: uuid.UUID,
    req: CommentUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Edit comment text (author only)."""
    service = CommentService(db)
    return await service.edit_comment(comment_id, user, req.content)


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Soft-delete a comment."""
    service = CommentService(db)
    await service.delete_comment(comment_id, user)
    return {"message": "Comment deleted."}


# ==========================================
# EVIDENCE ANNOTATIONS
# ==========================================

@router.post("/annotations", response_model=AnnotationResponse, status_code=status.HTTP_201_CREATED)
async def create_annotation(
    req: AnnotationCreateRequest,
    workspace_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Add a collaborative peer annotation to an evidence item."""
    service = AnnotationService(db)
    ann = await service.create_annotation(
        workspace_id=workspace_id,
        investigation_id=req.investigation_id,
        evidence_id=req.evidence_id,
        author=user,
        annotation_type=req.annotation_type,
        comment=req.comment,
        reviewer_rationale=req.reviewer_rationale,
    )
    return AnnotationResponse(**ann)


@router.get("/annotations", response_model=List[AnnotationResponse])
async def list_annotations(
    workspace_id: uuid.UUID = Query(...),
    investigation_id: Optional[uuid.UUID] = None,
    evidence_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List evidence annotations."""
    service = AnnotationService(db)
    annotations = await service.list_annotations(
        workspace_id=workspace_id,
        user_id=user.id,
        investigation_id=investigation_id,
        evidence_id=evidence_id,
        status_filter=status,
    )
    return [AnnotationResponse(**a) for a in annotations]


@router.patch("/annotations/{annotation_id}", response_model=Dict[str, Any])
async def update_annotation_status(
    annotation_id: uuid.UUID,
    req: AnnotationStatusUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Update annotation status (open, resolved, dismissed)."""
    service = AnnotationService(db)
    return await service.update_annotation_status(
        annotation_id=annotation_id,
        user=user,
        new_status=req.status,
        reviewer_rationale=req.reviewer_rationale,
    )


@router.delete("/annotations/{annotation_id}")
async def delete_annotation(
    annotation_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Delete an evidence annotation."""
    service = AnnotationService(db)
    await service.delete_annotation(annotation_id, user)
    return {"message": "Annotation deleted."}


# ==========================================
# REVIEWS & DECISIONS
# ==========================================

@router.post("/reviews", response_model=ReviewRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_review_request(
    req: ReviewRequestCreate,
    workspace_id: uuid.UUID = Query(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Submit research findings or reports for formal review."""
    service = ReviewService(db)
    result = await service.create_review_request(
        workspace_id=workspace_id,
        investigation_id=req.investigation_id,
        requester=user,
        target_type=req.target_type,
        target_id=req.target_id,
        title=req.title,
        description=req.description,
        target_version=req.target_version,
        requires_independent_review=req.requires_independent_review,
    )
    return ReviewRequestResponse(**result)


@router.get("/reviews", response_model=List[ReviewRequestResponse])
async def list_review_requests(
    workspace_id: uuid.UUID = Query(...),
    investigation_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List review requests in a workspace."""
    service = ReviewService(db)
    items = await service.list_review_requests(
        workspace_id=workspace_id,
        user_id=user.id,
        investigation_id=investigation_id,
        status_filter=status,
    )
    return [ReviewRequestResponse(**r) for r in items]


@router.get("/reviews/{request_id}", response_model=ReviewRequestResponse)
async def get_review_request(
    request_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Get review request details including historical decisions."""
    service = ReviewService(db)
    details = await service.get_review_request(request_id, user.id)
    return ReviewRequestResponse(**details)


@router.post("/reviews/{request_id}/decisions", response_model=ReviewRequestResponse)
async def submit_review_decision(
    request_id: uuid.UUID,
    req: ReviewDecisionSubmit,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Submit formal review decision (approved, rejected, changes_requested). Enforces self-approval guard."""
    service = ReviewService(db)
    result = await service.submit_review_decision(
        review_request_id=request_id,
        reviewer=user,
        decision=req.decision,
        rationale=req.rationale,
    )
    return ReviewRequestResponse(**result)


@router.post("/reviews/{request_id}/withdraw")
async def withdraw_review_request(
    request_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Withdraw a pending review request."""
    service = ReviewService(db)
    await service.withdraw_review_request(request_id, user)
    return {"message": "Review request withdrawn."}


# ==========================================
# NOTIFICATIONS
# ==========================================

@router.get("/notifications", response_model=List[NotificationResponse])
async def list_notifications(
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = False,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """List in-app notifications for authenticated user."""
    service = NotificationService(db)
    items = await service.list_notifications(user.id, limit=limit, unread_only=unread_only)
    return [NotificationResponse(**n) for n in items]


@router.get("/notifications/unread-count")
async def get_unread_count(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Get unread notification count for user badge."""
    service = NotificationService(db)
    count = await service.get_unread_count(user.id)
    return {"unread_count": count}


@router.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Mark a notification as read."""
    service = NotificationService(db)
    await service.mark_as_read(notification_id, user.id)
    return {"message": "Notification marked as read."}


@router.post("/notifications/mark-all-read")
async def mark_all_notifications_read(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Mark all unread notifications as read."""
    service = NotificationService(db)
    count = await service.mark_all_as_read(user.id)
    return {"marked_read_count": count}


@router.get("/notifications/preferences", response_model=NotificationPreferenceResponse)
async def get_notification_preferences(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Get notification preferences."""
    service = NotificationService(db)
    pref = await service.get_or_create_preferences(user.id)
    return NotificationPreferenceResponse(
        user_id=str(pref.user_id),
        email_notifications_enabled=pref.email_notifications_enabled,
        in_app_notifications_enabled=pref.in_app_notifications_enabled,
    )


@router.patch("/notifications/preferences", response_model=NotificationPreferenceResponse)
async def update_notification_preferences(
    req: NotificationPreferenceUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Update notification preferences."""
    service = NotificationService(db)
    pref = await service.update_preferences(
        user.id,
        email_enabled=req.email_notifications_enabled,
        in_app_enabled=req.in_app_notifications_enabled,
    )
    return NotificationPreferenceResponse(
        user_id=str(pref.user_id),
        email_notifications_enabled=pref.email_notifications_enabled,
        in_app_notifications_enabled=pref.in_app_notifications_enabled,
    )
