"""Peer review and decision management service for NEOMON Milestone 10."""

import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    User,
    ReviewRequest,
    ReviewDecision,
    Workspace,
    WorkspaceMember,
)
from app.collaboration.permission_service import PermissionService
from app.collaboration.notification_service import NotificationService
from app.collaboration.activity_service import ActivityService


class ReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.perm = PermissionService(db)
        self.notif = NotificationService(db)
        self.act = ActivityService(db)

    async def create_review_request(
        self,
        workspace_id: uuid.UUID,
        investigation_id: uuid.UUID,
        requester: User,
        target_type: str,
        target_id: str,
        title: str,
        description: Optional[str] = None,
        target_version: Optional[str] = None,
        requires_independent_review: bool = True,
    ) -> Dict[str, Any]:
        """Submit an investigation or report artifact for formal peer review."""
        await self.perm.require_workspace_membership(requester.id, workspace_id, min_role="researcher")

        clean_title = title.strip()
        if not clean_title:
            raise HTTPException(status_code=400, detail="Review request title cannot be empty.")

        clean_target_type = target_type.strip().lower()
        valid_targets = {"investigation", "report", "hypothesis", "claim_synthesis"}
        if clean_target_type not in valid_targets:
            raise HTTPException(status_code=400, detail=f"Invalid target_type. Allowed: {sorted(valid_targets)}")

        # Check workspace policy: if workspace setting enforces independent review, ensure flag is set
        ws_stmt = select(Workspace).where(Workspace.id == workspace_id)
        ws_res = await self.db.execute(ws_stmt)
        ws = ws_res.scalar_one_or_none()
        if ws and ws.settings.get("require_independent_review", True):
            requires_independent_review = True

        review_req = ReviewRequest(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            investigation_id=investigation_id,
            target_type=clean_target_type,
            target_id=str(target_id),
            target_version=target_version,
            requester_id=requester.id,
            title=clean_title,
            description=description,
            status="submitted",
            requires_independent_review=requires_independent_review,
        )
        self.db.add(review_req)
        await self.db.flush()

        # Log activity
        await self.act.log_activity(
            workspace_id=workspace_id,
            actor_id=requester.id,
            action_type="review_requested",
            entity_type="review_request",
            entity_id=str(review_req.id),
            summary=f"{requester.display_name} requested review for '{clean_title}'.",
            metadata={"target_type": clean_target_type, "target_id": str(target_id)},
        )

        # Notify workspace reviewers and admins
        reviewers_stmt = (
            select(User.id)
            .join(WorkspaceMember, WorkspaceMember.user_id == User.id)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.role.in_(["reviewer", "admin", "owner"]),
                User.id != requester.id,
            )
        )
        r_res = await self.db.execute(reviewers_stmt)
        for (r_user_id,) in r_res.all():
            await self.notif.create_notification(
                user_id=r_user_id,
                workspace_id=workspace_id,
                actor_id=requester.id,
                event_type="review_request_created",
                title=f"Review Requested: {clean_title}",
                message=f"{requester.display_name} requested review for {clean_target_type}.",
                link_url=f"/reviews?request_id={review_req.id}",
            )

        await self.db.commit()
        return await self.get_review_request(review_req.id, requester.id)

    async def list_review_requests(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        investigation_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List review requests in a workspace."""
        await self.perm.require_workspace_membership(user_id, workspace_id)

        stmt = (
            select(ReviewRequest, User.display_name)
            .join(User, User.id == ReviewRequest.requester_id)
            .where(ReviewRequest.workspace_id == workspace_id)
        )
        if investigation_id:
            stmt = stmt.where(ReviewRequest.investigation_id == investigation_id)
        if status_filter:
            stmt = stmt.where(ReviewRequest.status == status_filter)

        stmt = stmt.order_by(ReviewRequest.created_at.desc())
        res = await self.db.execute(stmt)
        rows = res.all()

        results = []
        for req, requester_name in rows:
            results.append({
                "id": str(req.id),
                "workspace_id": str(req.workspace_id),
                "investigation_id": str(req.investigation_id),
                "target_type": req.target_type,
                "target_id": req.target_id,
                "target_version": req.target_version,
                "requester_id": str(req.requester_id),
                "requester_name": requester_name,
                "title": req.title,
                "description": req.description,
                "status": req.status,
                "requires_independent_review": req.requires_independent_review,
                "created_at": req.created_at.isoformat() if req.created_at else None,
                "updated_at": req.updated_at.isoformat() if req.updated_at else None,
            })
        return results

    async def get_review_request(self, review_request_id: uuid.UUID, user_id: uuid.UUID) -> Dict[str, Any]:
        """Fetch single review request with all its decisions."""
        stmt = (
            select(ReviewRequest, User.display_name)
            .join(User, User.id == ReviewRequest.requester_id)
            .where(ReviewRequest.id == review_request_id)
        )
        res = await self.db.execute(stmt)
        row = res.first()
        if not row:
            raise HTTPException(status_code=404, detail="Review request not found.")

        req, requester_name = row
        await self.perm.require_workspace_membership(user_id, req.workspace_id)

        # Get decisions
        dec_stmt = (
            select(ReviewDecision, User.display_name)
            .join(User, User.id == ReviewDecision.reviewer_id)
            .where(ReviewDecision.review_request_id == req.id)
            .order_by(ReviewDecision.created_at.asc())
        )
        dec_res = await self.db.execute(dec_stmt)
        decisions = []
        for dec, reviewer_name in dec_res.all():
            decisions.append({
                "id": str(dec.id),
                "reviewer_id": str(dec.reviewer_id),
                "reviewer_name": reviewer_name,
                "decision": dec.decision,
                "rationale": dec.rationale,
                "created_at": dec.created_at.isoformat() if dec.created_at else None,
            })

        return {
            "id": str(req.id),
            "workspace_id": str(req.workspace_id),
            "investigation_id": str(req.investigation_id),
            "target_type": req.target_type,
            "target_id": req.target_id,
            "target_version": req.target_version,
            "requester_id": str(req.requester_id),
            "requester_name": requester_name,
            "title": req.title,
            "description": req.description,
            "status": req.status,
            "requires_independent_review": req.requires_independent_review,
            "decisions": decisions,
            "created_at": req.created_at.isoformat() if req.created_at else None,
            "updated_at": req.updated_at.isoformat() if req.updated_at else None,
        }

    async def submit_review_decision(
        self,
        review_request_id: uuid.UUID,
        reviewer: User,
        decision: str,
        rationale: str,
    ) -> Dict[str, Any]:
        """Submit approval, changes requested, or rejection with self-approval enforcement."""
        stmt = select(ReviewRequest).where(ReviewRequest.id == review_request_id)
        res = await self.db.execute(stmt)
        req = res.scalar_one_or_none()
        if not req:
            raise HTTPException(status_code=404, detail="Review request not found.")

        # Require reviewer/admin/owner
        await self.perm.require_workspace_membership(reviewer.id, req.workspace_id, min_role="reviewer")

        clean_decision = decision.strip().lower()
        if clean_decision not in ("approved", "rejected", "changes_requested"):
            raise HTTPException(status_code=400, detail="Invalid decision. Allowed: approved, rejected, changes_requested.")

        clean_rationale = rationale.strip()
        if not clean_rationale:
            raise HTTPException(status_code=400, detail="Decision rationale is required.")

        # Enforce self-approval guard: if approving and requires independent review, requester cannot self-approve!
        if clean_decision == "approved":
            self.perm.validate_self_approval_guard(
                reviewer.id, req, require_independent=req.requires_independent_review
            )

        # Create decision
        dec = ReviewDecision(
            id=uuid.uuid4(),
            review_request_id=req.id,
            reviewer_id=reviewer.id,
            decision=clean_decision,
            rationale=clean_rationale,
        )
        self.db.add(dec)

        # Update request status
        req.status = clean_decision
        req.updated_at = datetime.now(timezone.utc)

        # Log activity
        await self.act.log_activity(
            workspace_id=req.workspace_id,
            actor_id=reviewer.id,
            action_type="review_decision_submitted",
            entity_type="review_request",
            entity_id=str(req.id),
            summary=f"{reviewer.display_name} marked review '{req.title}' as {clean_decision}.",
            metadata={"decision": clean_decision, "review_request_id": str(req.id)},
        )

        # Notify requester
        await self.notif.create_notification(
            user_id=req.requester_id,
            workspace_id=req.workspace_id,
            actor_id=reviewer.id,
            event_type="review_decision",
            title=f"Review Decision: {clean_decision.replace('_', ' ').title()}",
            message=f"{reviewer.display_name} evaluated '{req.title}': {clean_decision}.",
            link_url=f"/reviews?request_id={req.id}",
        )

        await self.db.commit()
        return await self.get_review_request(req.id, reviewer.id)

    async def withdraw_review_request(self, review_request_id: uuid.UUID, user: User) -> bool:
        """Allow requester to withdraw their own pending review request."""
        stmt = select(ReviewRequest).where(ReviewRequest.id == review_request_id)
        res = await self.db.execute(stmt)
        req = res.scalar_one_or_none()
        if not req:
            raise HTTPException(status_code=404, detail="Review request not found.")

        if req.requester_id != user.id:
            raise HTTPException(status_code=403, detail="You can only withdraw your own review request.")

        if req.status in ("approved", "rejected"):
            raise HTTPException(status_code=400, detail="Cannot withdraw a finalized review request.")

        req.status = "withdrawn"
        req.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        return True
