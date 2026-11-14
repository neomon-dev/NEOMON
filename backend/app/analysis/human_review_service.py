"""Human Scientific Review and Evidence Correction Service (Milestone 12).

Provides controlled, audited mechanisms for authorized researchers and reviewers to:
1. Challenge automated evidence classifications.
2. Mark passages as irrelevant or contextual.
3. Flag duplicate studies or source credibility problems.
4. Record an immutable review audit trail without overwriting original AI evaluations.
5. Trigger explicit versioned reassessment.
"""

from datetime import datetime, timezone
from enum import StrEnum
import logging
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Claim,
    Evidence,
    EvidenceVerificationRecord,
    HumanEvidenceCorrection,
    Investigation,
    User,
)
from app.collaboration.permission_service import PermissionService
from app.analysis.claim_synthesis_service import ClaimSynthesisService
from app.analysis.methodology_audit_service import MethodologyAuditService
from app.analysis.quality_calibration_service import calibrate_investigation_quality

logger = logging.getLogger("neomon.analysis.human_review")


class CorrectionType(StrEnum):
    RECLASSIFY_RELATIONSHIP = "reclassify_relationship"
    MARK_IRRELEVANT = "mark_irrelevant"
    MARK_CONTEXTUAL = "mark_contextual"
    MARK_DUPLICATE_STUDY = "mark_duplicate_study"
    FLAG_SOURCE_CREDIBILITY = "flag_source_credibility"
    CHALLENGE_CLAIM_SYNTHESIS = "challenge_claim_synthesis"
    REQUEST_ADDITIONAL_RESEARCH = "request_additional_research"


class HumanReviewService:
    """Manages researcher challenges, corrections, and versioned reassessment."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.perm = PermissionService(db)

    async def submit_evidence_correction(
        self,
        investigation_id: uuid.UUID,
        claim_id: uuid.UUID,
        evidence_id: uuid.UUID,
        user: User,
        correction_type: str,
        corrected_value: str,
        reason: str,
    ) -> HumanEvidenceCorrection:
        """Submit a challenge or correction to an evidence passage or classification."""
        inv = await self.db.get(Investigation, investigation_id)
        if not inv:
            raise ValueError("Investigation not found.")

        # Require at least 'reviewer' role in the investigation's workspace
        if inv.workspace_id:
            await self.perm.require_workspace_membership(user.id, inv.workspace_id, min_role="reviewer")

        # Find existing verification record
        vr_stmt = select(EvidenceVerificationRecord).where(
            EvidenceVerificationRecord.investigation_id == investigation_id,
            EvidenceVerificationRecord.claim_id == claim_id,
            EvidenceVerificationRecord.evidence_id == evidence_id,
        )
        vr_res = await self.db.execute(vr_stmt)
        record = vr_res.scalars().first()
        original_value = record.relationship_classification if record else "unrecorded"

        # Determine next version number for this pair
        history_stmt = select(HumanEvidenceCorrection).where(
            HumanEvidenceCorrection.investigation_id == investigation_id,
            HumanEvidenceCorrection.claim_id == claim_id,
            HumanEvidenceCorrection.evidence_id == evidence_id,
        )
        history_res = await self.db.execute(history_stmt)
        version_num = len(list(history_res.scalars().all())) + 1

        now = datetime.now(timezone.utc)
        correction = HumanEvidenceCorrection(
            id=uuid.uuid4(),
            investigation_id=investigation_id,
            claim_id=claim_id,
            evidence_id=evidence_id,
            user_id=user.id,
            correction_type=correction_type,
            original_value=original_value,
            corrected_value=corrected_value,
            reason=reason.strip(),
            version_number=version_num,
            is_active=True,
            created_at=now,
        )
        self.db.add(correction)

        # Update verification record state
        if record:
            record.is_challenged = True
            record.challenge_reason = reason
            record.relationship_classification = corrected_value
            record.verification_status = "corrected"
            record.corrected_by_user_id = user.id
            record.corrected_at = now
            record.explanation = f"Human Correction by {user.display_name or user.email}: {reason} (Originally classified as {original_value})"

        await self.db.commit()
        await self.db.refresh(correction)
        return correction

    async def list_investigation_corrections(
        self,
        investigation_id: uuid.UUID,
        claim_id: Optional[uuid.UUID] = None,
    ) -> List[HumanEvidenceCorrection]:
        """Fetch audit log of all human corrections for an investigation."""
        stmt = select(HumanEvidenceCorrection).where(
            HumanEvidenceCorrection.investigation_id == investigation_id
        )
        if claim_id:
            stmt = stmt.where(HumanEvidenceCorrection.claim_id == claim_id)
        stmt = stmt.order_by(HumanEvidenceCorrection.created_at.desc())
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def trigger_versioned_reassessment(
        self,
        investigation_id: uuid.UUID,
        user: User,
    ) -> Dict[str, Any]:
        """Re-run claim synthesis, methodology audit, and quality calibration using corrected evidence."""
        inv = await self.db.get(Investigation, investigation_id)
        if not inv:
            raise ValueError("Investigation not found.")

        if inv.workspace_id:
            await self.perm.require_workspace_membership(user.id, inv.workspace_id, min_role="reviewer")

        synth_service = ClaimSynthesisService(self.db)
        syntheses = await synth_service.synthesize_investigation_claims(investigation_id)

        audit_service = MethodologyAuditService(self.db)
        findings = await audit_service.audit_investigation(investigation_id)

        calib = await calibrate_investigation_quality(self.db, investigation_id)

        return {
            "status": "reassessed",
            "investigation_id": str(investigation_id),
            "synthesized_claims_count": len(syntheses),
            "methodology_findings_count": len(findings),
            "calibrated_quality_tier": calib.get("calibrated_tier") if isinstance(calib, dict) else getattr(calib, "calibrated_tier", "Inconclusive"),
            "calibrated_quality_score": calib.get("calibrated_score") if isinstance(calib, dict) else getattr(calib, "calibrated_score", 0.0),
            "reassessed_by": str(user.id),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
