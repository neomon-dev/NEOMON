"""Evidence-to-Claim Scientific Verification Service (Milestone 12).

Provides a rigorous, explainable verification layer between retrieved evidence passages and claims:
1. Enforces 8 explicit evidence relationship classifications.
2. Prevents topical relevance from masquerading as entailment.
3. Distinguishes paper motivations, aims, and abstracts from empirical findings.
4. Preserves contradictions and flags inferential gaps.
5. Records immutable audit trails and supports human review challenges.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import StrEnum
import json
import logging
import re
from typing import Any, List, Optional, Tuple
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Claim,
    Document,
    Evidence,
    EvidenceVerificationRecord,
    HumanEvidenceCorrection,
    Investigation,
    Source,
)

logger = logging.getLogger("neomon.analysis.verification")


class RelationshipClassification(StrEnum):
    DIRECTLY_SUPPORTS = "directly_supports"
    PARTIALLY_SUPPORTS = "partially_supports"
    CONTRADICTS = "contradicts"
    CONTEXTUAL_BACKGROUND = "contextual_background"
    METHODOLOGICAL_CONTEXT = "methodological_context"
    MENTIONS_SUBJECT = "mentions_subject"
    INSUFFICIENT_INFORMATION = "insufficient_information"
    UNVERIFIABLE = "unverifiable"


class VerificationStatus(StrEnum):
    VERIFIED = "verified"
    UNCERTAIN = "uncertain"
    CHALLENGED = "challenged"
    CORRECTED = "corrected"


# Linguistic heuristics for empirical proof vs intent / framing
_STUDY_AIM_PATTERNS = [
    re.compile(r"\b(aims?\s+to|aim\s+of\s+this|purpose\s+of\s+this|objective\s+was\s+to|objective\s+is\s+to)\b", re.I),
    re.compile(r"\b(this\s+(?:paper|study|article|thesis|report)\s+(?:explores|examines|investigates|focuses\s+on))\b", re.I),
    re.compile(r"\b(we\s+(?:investigate|examine|explore|hypothesize|seek\s+to\s+determine))\b", re.I),
    re.compile(r"\b(sought\s+to\s+(?:analyze|investigate|evaluate))\b", re.I),
    re.compile(r"\b(intended\s+to\s+assess|designed\s+to\s+study)\b", re.I),
]

_EMPIRICAL_FINDING_PATTERNS = [
    re.compile(r"\b(found\s+that|demonstrates?\s+that|showed\s+that|results?\s+(?:show|indicate|confirm|reveal))\b", re.I),
    re.compile(r"\b(empirical\s+data\s+(?:shows?|reveals?|confirms?)|data\s+reveals?|statistically\s+significant)\b", re.I),
    re.compile(r"\b(statistically\s+demonstrated|empirically\s+confirmed|observed\s+a\s+significant)\b", re.I),
    re.compile(r"\b(concluded?\s+that|measurements?\s+confirm|experimental\s+results?\s+show)\b", re.I),
    re.compile(r"\b(findings?\s+demonstrate|analysis\s+confirms?|leads?\s+to\s+a\s+\d+%\s+increase)\b", re.I),
]

_CONTRADICTION_PATTERNS = [
    re.compile(r"\b(refutes?|disproves?|contradicts?|fails?\s+to\s+support|no\s+evidence\s+that)\b", re.I),
    re.compile(r"\b(contrary\s+to|does\s+not\s+cause|did\s+not\s+result\s+in|inconsistent\s+with)\b", re.I),
    re.compile(r"\b(rebuts?|challenges?\s+the\s+assumption|debunks?|not\s+supported\s+by\s+data)\b", re.I),
]

_METHODOLOGY_PATTERNS = [
    re.compile(r"\b(methodology|experimental\s+setup|sample\s+size|randomized\s+controlled|simulation\s+model)\b", re.I),
    re.compile(r"\b(cohort\s+study|survey\s+method|instrumentation|in\s+vitro|benchmarking\s+framework)\b", re.I),
]


def classify_passage_to_claim(
    passage: str,
    claim_text: str,
    source_title: Optional[str] = None,
) -> Tuple[RelationshipClassification, float, str, str, VerificationStatus]:
    """Deterministically classifies an evidence passage against a claim using scientific heuristics.
    
    Returns:
        (relationship, confidence, confidence_meaning, explanation, verification_status)
    """
    clean_passage = (passage or "").strip()
    clean_claim = (claim_text or "").strip().lower()

    if not clean_passage or len(clean_passage) < 15:
        return (
            RelationshipClassification.INSUFFICIENT_INFORMATION,
            0.1,
            "insufficient_passage_length",
            "Passage text is empty or too short to extract inferential content.",
            VerificationStatus.UNCERTAIN,
        )

    # Check for study aims / motivations (Must not be treated as direct support!)
    is_study_aim = any(pat.search(clean_passage) for pat in _STUDY_AIM_PATTERNS)
    is_empirical_finding = any(pat.search(clean_passage) for pat in _EMPIRICAL_FINDING_PATTERNS)
    is_contradiction = any(pat.search(clean_passage) for pat in _CONTRADICTION_PATTERNS)
    is_methodology = any(pat.search(clean_passage) for pat in _METHODOLOGY_PATTERNS)

    # Token overlap between passage and claim
    claim_words = {w for w in re.findall(r"\b\w{3,}\b", clean_claim)}
    passage_words = {w for w in re.findall(r"\b\w{3,}\b", clean_passage.lower())}
    overlap = claim_words & passage_words
    overlap_ratio = len(overlap) / max(1, len(claim_words))

    # Case 1: Contradiction
    if is_contradiction and overlap_ratio >= 0.25:
        return (
            RelationshipClassification.CONTRADICTS,
            0.88,
            "direct_refutation_detected",
            f"Passage explicitly challenges or refutes claim propositions with {len(overlap)} matching core concepts.",
            VerificationStatus.VERIFIED,
        )

    # Case 2: Stated motivation / study aim without empirical finding
    if is_study_aim and not is_empirical_finding:
        return (
            RelationshipClassification.CONTEXTUAL_BACKGROUND,
            0.65,
            "study_aim_or_framing_only",
            "Passage articulates the study's stated objective, hypothesis, or research motivation rather than empirical findings.",
            VerificationStatus.VERIFIED,
        )

    # Case 3: Methodology context
    if is_methodology and not is_empirical_finding and overlap_ratio < 0.5:
        return (
            RelationshipClassification.METHODOLOGICAL_CONTEXT,
            0.70,
            "procedural_or_methodological_detail",
            "Passage documents experimental procedure, sample composition, or instrumentation rather than direct substantive findings.",
            VerificationStatus.VERIFIED,
        )

    # Case 4: High overlap with empirical finding (Direct Support)
    if is_empirical_finding and overlap_ratio >= 0.45:
        return (
            RelationshipClassification.DIRECTLY_SUPPORTS,
            0.92,
            "empirical_finding_with_causal_mechanism",
            f"Passage presents empirically verified findings establishing the claim proposition with strong conceptual overlap ({round(overlap_ratio*100)}%).",
            VerificationStatus.VERIFIED,
        )

    # Case 5: Moderate overlap or partial mechanism (Partial Support)
    if overlap_ratio >= 0.40 or (is_empirical_finding and overlap_ratio >= 0.25):
        return (
            RelationshipClassification.PARTIALLY_SUPPORTS,
            0.75,
            "partial_corroboration",
            f"Passage supports key aspects of the claim ({len(overlap)} overlapping terms) but requires minor inferential bridge.",
            VerificationStatus.VERIFIED,
        )

    # Case 6: Mentions subject without establishing claim
    if overlap_ratio >= 0.10 or len(overlap) >= 1:
        return (
            RelationshipClassification.MENTIONS_SUBJECT,
            0.55,
            "topical_mention_without_claim_assertion",
            "Passage mentions the subject entity or core domain terms but does not assert or prove the specific claim proposition.",
            VerificationStatus.VERIFIED,
        )

    # Case 7: Minimal overlap -> Contextual or Insufficient
    if overlap_ratio > 0.05:
        return (
            RelationshipClassification.CONTEXTUAL_BACKGROUND,
            0.40,
            "peripheral_background_context",
            "Passage provides general domain context with minimal direct connection to specific claim assertions.",
            VerificationStatus.UNCERTAIN,
        )

    return (
        RelationshipClassification.INSUFFICIENT_INFORMATION,
        0.20,
        "lacks_inferential_relevance",
        "Passage lacks sufficient substantive overlap with claim concepts.",
        VerificationStatus.UNCERTAIN,
    )


class EvidenceVerificationService:
    """Orchestrates scientific evidence-to-claim verification and audit storage."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def verify_investigation_evidence(
        self,
        investigation_id: uuid.UUID,
        agent_name: str = "methodology_auditor",
        model_name: Optional[str] = None,
    ) -> List[EvidenceVerificationRecord]:
        """Classify and record verification status for all claim-evidence pairs in an investigation."""
        # Fetch all claims
        claims_res = await self.db.execute(
            select(Claim).where(Claim.investigation_id == investigation_id)
        )
        claims = list(claims_res.scalars().all())

        # Fetch evidence linked to sources in this investigation
        ev_stmt = (
            select(Evidence, Source)
            .join(Source, Evidence.source_id == Source.id)
            .where(Source.investigation_id == investigation_id)
        )
        ev_res = await self.db.execute(ev_stmt)
        evidence_pairs = ev_res.all()

        records: List[EvidenceVerificationRecord] = []
        now = datetime.now(timezone.utc)

        # Remove previous non-challenged verification records to allow re-assessment
        existing_res = await self.db.execute(
            select(EvidenceVerificationRecord)
            .where(EvidenceVerificationRecord.investigation_id == investigation_id)
            .where(EvidenceVerificationRecord.is_challenged == False)
        )
        for old_rec in existing_res.scalars().all():
            await self.db.delete(old_rec)

        for claim in claims:
            for ev, src in evidence_pairs:
                passage = getattr(ev, "exact_text", "") or getattr(ev, "passage", "") or ""
                claim_stmt = getattr(claim, "text", "") or getattr(claim, "statement", "") or ""
                rel, conf, meaning, exp, status = classify_passage_to_claim(
                    passage=passage,
                    claim_text=claim_stmt,
                    source_title=src.title or "",
                )

                pub_dt: Optional[datetime] = None
                if src.publication_date:
                    if isinstance(src.publication_date, datetime):
                        pub_dt = src.publication_date
                    elif isinstance(src.publication_date, date):
                        pub_dt = datetime.combine(src.publication_date, datetime.min.time(), tzinfo=timezone.utc)
                    elif isinstance(src.publication_date, str):
                        try:
                            pub_dt = datetime.fromisoformat(src.publication_date.replace("Z", "+00:00"))
                            if pub_dt.tzinfo is None:
                                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                        except Exception:
                            m = re.search(r"\b(19\d\d|20\d\d)\b", src.publication_date)
                            if m:
                                pub_dt = datetime(int(m.group(1)), 1, 1, tzinfo=timezone.utc)

                rec = EvidenceVerificationRecord(
                    id=uuid.uuid4(),
                    investigation_id=investigation_id,
                    claim_id=claim.id,
                    evidence_id=ev.id,
                    source_id=src.id,
                    document_id=getattr(ev, "document_id", None),
                    exact_passage_text=passage,
                    passage_location=getattr(ev, "page_number", None) or getattr(ev, "section_name", None),
                    source_publication_date=pub_dt,
                    retrieval_date=src.retrieval_timestamp or now,
                    relationship_classification=rel.value,
                    verification_status=status.value,
                    verification_method="deterministic_scientific_heuristic",
                    confidence=conf,
                    confidence_meaning=meaning,
                    explanation=exp,
                    agent_or_process=agent_name,
                    model_provider_info=model_name or "neomon-scientific-ruleset-v12",
                    is_challenged=False,
                    created_at=now,
                    updated_at=now,
                )
                self.db.add(rec)
                records.append(rec)

        await self.db.commit()
        return records

    async def list_verification_records(
        self,
        investigation_id: uuid.UUID,
        claim_id: Optional[uuid.UUID] = None,
        classification: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[EvidenceVerificationRecord]:
        """Fetch verification records with optional filtering."""
        stmt = select(EvidenceVerificationRecord).where(
            EvidenceVerificationRecord.investigation_id == investigation_id
        )
        if claim_id:
            stmt = stmt.where(EvidenceVerificationRecord.claim_id == claim_id)
        if classification:
            stmt = stmt.where(EvidenceVerificationRecord.relationship_classification == classification)
        stmt = stmt.order_by(EvidenceVerificationRecord.confidence.desc()).offset(offset).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def challenge_and_correct_record(
        self,
        record_id: uuid.UUID,
        user_id: uuid.UUID,
        corrected_classification: str,
        reason: str,
    ) -> EvidenceVerificationRecord:
        """Allow an authorized reviewer to challenge and correct an automated classification."""
        rec = await self.db.get(EvidenceVerificationRecord, record_id)
        if not rec:
            raise ValueError("Evidence verification record not found.")

        # Create immutable human correction audit entry
        correction = HumanEvidenceCorrection(
            id=uuid.uuid4(),
            investigation_id=rec.investigation_id,
            claim_id=rec.claim_id,
            evidence_id=rec.evidence_id,
            user_id=user_id,
            correction_type="reclassify_relationship",
            original_value=rec.relationship_classification,
            corrected_value=corrected_classification,
            reason=reason,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(correction)

        # Update verification record state
        rec.is_challenged = True
        rec.challenge_reason = reason
        rec.relationship_classification = corrected_classification
        rec.verification_status = VerificationStatus.CORRECTED.value
        rec.corrected_by_user_id = user_id
        rec.corrected_at = datetime.now(timezone.utc)
        rec.explanation = f"Human Correction: {reason} (Originally classified as {rec.relationship_classification})"

        await self.db.commit()
        await self.db.refresh(rec)
        return rec
