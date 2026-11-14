"""Evidence annotation service for NEOMON Milestone 10."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    User,
    EvidenceAnnotation,
    Evidence,
    Source,
    Investigation,
)
from app.collaboration.permission_service import PermissionService
from app.collaboration.activity_service import ActivityService


class AnnotationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.perm = PermissionService(db)
        self.act = ActivityService(db)

    async def create_annotation(
        self,
        workspace_id: uuid.UUID,
        investigation_id: uuid.UUID,
        evidence_id: uuid.UUID,
        author: User,
        annotation_type: str,
        comment: str,
        reviewer_rationale: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a collaborative annotation on an evidence item without altering evidence.evidence_type."""
        await self.perm.require_workspace_membership(author.id, workspace_id, min_role="reviewer")

        # Verify evidence exists and belongs to this investigation
        ev_stmt = (
            select(Evidence)
            .join(Source, Source.id == Evidence.source_id)
            .where(Evidence.id == evidence_id, Source.investigation_id == investigation_id)
        )
        ev_res = await self.db.execute(ev_stmt)
        evidence = ev_res.scalar_one_or_none()
        if not evidence:
            raise HTTPException(status_code=404, detail="Evidence item not found in this investigation.")

        clean_type = annotation_type.strip().lower()
        valid_types = {
            "supporting",
            "contradicting",
            "methodological_concern",
            "credibility_concern",
            "relevance_question",
            "general_note",
        }
        if clean_type not in valid_types:
            raise HTTPException(status_code=400, detail=f"Invalid annotation_type. Allowed: {sorted(valid_types)}")

        clean_comment = comment.strip()
        if not clean_comment:
            raise HTTPException(status_code=400, detail="Annotation comment cannot be empty.")

        annotation = EvidenceAnnotation(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            investigation_id=investigation_id,
            evidence_id=evidence_id,
            author_id=author.id,
            annotation_type=clean_type,
            comment=clean_comment,
            reviewer_rationale=reviewer_rationale,
            status="open",
        )
        self.db.add(annotation)
        await self.db.flush()

        # Log activity
        await self.act.log_activity(
            workspace_id=workspace_id,
            actor_id=author.id,
            action_type="evidence_annotated",
            entity_type="evidence_annotation",
            entity_id=str(annotation.id),
            summary=f"{author.display_name} added '{clean_type}' annotation to evidence {str(evidence_id)[:8]}.",
            metadata={"evidence_id": str(evidence_id), "annotation_type": clean_type},
        )
        await self.db.commit()

        return {
            "id": str(annotation.id),
            "workspace_id": str(annotation.workspace_id),
            "investigation_id": str(annotation.investigation_id),
            "evidence_id": str(annotation.evidence_id),
            "author_id": str(annotation.author_id),
            "author_name": author.display_name,
            "annotation_type": annotation.annotation_type,
            "comment": annotation.comment,
            "reviewer_rationale": annotation.reviewer_rationale,
            "status": annotation.status,
            "created_at": annotation.created_at.isoformat() if annotation.created_at else None,
        }

    async def list_annotations(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        investigation_id: Optional[uuid.UUID] = None,
        evidence_id: Optional[uuid.UUID] = None,
        status_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List annotations in a workspace with optional investigation/evidence filtering."""
        await self.perm.require_workspace_membership(user_id, workspace_id)

        stmt = (
            select(EvidenceAnnotation, User.display_name)
            .join(User, User.id == EvidenceAnnotation.author_id)
            .where(EvidenceAnnotation.workspace_id == workspace_id)
        )
        if investigation_id:
            stmt = stmt.where(EvidenceAnnotation.investigation_id == investigation_id)
        if evidence_id:
            stmt = stmt.where(EvidenceAnnotation.evidence_id == evidence_id)
        if status_filter:
            stmt = stmt.where(EvidenceAnnotation.status == status_filter)

        stmt = stmt.order_by(EvidenceAnnotation.created_at.desc())
        res = await self.db.execute(stmt)
        rows = res.all()

        annotations = []
        for ann, author_name in rows:
            annotations.append({
                "id": str(ann.id),
                "workspace_id": str(ann.workspace_id),
                "investigation_id": str(ann.investigation_id),
                "evidence_id": str(ann.evidence_id),
                "author_id": str(ann.author_id),
                "author_name": author_name,
                "annotation_type": ann.annotation_type,
                "comment": ann.comment,
                "reviewer_rationale": ann.reviewer_rationale,
                "status": ann.status,
                "created_at": ann.created_at.isoformat() if ann.created_at else None,
                "updated_at": ann.updated_at.isoformat() if ann.updated_at else None,
            })
        return annotations

    async def update_annotation_status(
        self,
        annotation_id: uuid.UUID,
        user: User,
        new_status: str,
        reviewer_rationale: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update annotation status (open, resolved, dismissed)."""
        clean_status = new_status.strip().lower()
        if clean_status not in ("open", "resolved", "dismissed"):
            raise HTTPException(status_code=400, detail="Invalid status. Allowed: open, resolved, dismissed.")

        stmt = select(EvidenceAnnotation).where(EvidenceAnnotation.id == annotation_id)
        res = await self.db.execute(stmt)
        ann = res.scalar_one_or_none()
        if not ann:
            raise HTTPException(status_code=404, detail="Annotation not found.")

        member = await self.perm.require_workspace_membership(user.id, ann.workspace_id)
        if ann.author_id != user.id and member.role not in ("reviewer", "admin", "owner"):
            raise HTTPException(status_code=403, detail="Not authorized to update this annotation.")

        ann.status = clean_status
        if reviewer_rationale:
            ann.reviewer_rationale = reviewer_rationale
        ann.updated_at = datetime.now(timezone.utc)
        await self.db.commit()

        return {
            "id": str(ann.id),
            "status": ann.status,
            "reviewer_rationale": ann.reviewer_rationale,
            "updated_at": ann.updated_at.isoformat(),
        }

    async def delete_annotation(self, annotation_id: uuid.UUID, user: User) -> bool:
        """Delete an annotation (author, admin, or owner)."""
        stmt = select(EvidenceAnnotation).where(EvidenceAnnotation.id == annotation_id)
        res = await self.db.execute(stmt)
        ann = res.scalar_one_or_none()
        if not ann:
            raise HTTPException(status_code=404, detail="Annotation not found.")

        member = await self.perm.require_workspace_membership(user.id, ann.workspace_id)
        if ann.author_id != user.id and member.role not in ("admin", "owner"):
            raise HTTPException(status_code=403, detail="Not authorized to delete this annotation.")

        await self.db.delete(ann)
        await self.db.commit()
        return True
