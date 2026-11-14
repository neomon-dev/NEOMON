"""Pydantic schemas for Milestone 12 Research Validation, Reproducibility & Benchmarks."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, Field


# ==========================================
# EVIDENCE VERIFICATION SCHEMAS
# ==========================================

class EvidenceVerificationRecordResponse(BaseModel):
    id: str
    investigation_id: str
    claim_id: str
    evidence_id: str
    source_id: str
    document_id: Optional[str] = None
    exact_passage_text: str
    passage_location: Optional[str] = None
    source_publication_date: Optional[str] = None
    retrieval_date: str
    relationship_classification: str
    verification_status: str
    verification_method: str
    confidence: float
    confidence_meaning: str
    explanation: str
    agent_or_process: str
    model_provider_info: Optional[str] = None
    is_challenged: bool
    challenge_reason: Optional[str] = None
    corrected_by_user_id: Optional[str] = None
    corrected_at: Optional[str] = None
    created_at: str


class ChallengeCorrectionRequest(BaseModel):
    corrected_classification: str = Field(..., min_length=1, max_length=64)
    reason: str = Field(..., min_length=5, max_length=1000)


# ==========================================
# CLAIM SYNTHESIS SCHEMAS
# ==========================================

class ClaimSynthesisResultResponse(BaseModel):
    id: str
    investigation_id: str
    claim_id: str
    relevant_sources_count: int
    unique_underlying_studies_count: int
    direct_supporting_count: int
    partial_supporting_count: int
    contradicting_count: int
    contextual_count: int
    unverified_count: int
    methodological_limitations: List[str]
    publication_date_distribution: Dict[str, int]
    source_independence_score: float
    important_missing_evidence: List[str]
    outstanding_verification_operations: List[str]
    synthesis_outcome: str
    explanation: str
    created_at: str


# ==========================================
# STUDY INDEPENDENCE SCHEMAS
# ==========================================

class StudyClusterResponse(BaseModel):
    id: str
    investigation_id: str
    cluster_label: str
    primary_source_id: Optional[str] = None
    member_source_ids: List[str]
    relationship_category: str
    confidence: float
    evidence_rationale: str
    shared_attributes: Dict[str, Any]
    created_at: str


# ==========================================
# METHODOLOGY AUDIT SCHEMAS
# ==========================================

class MethodologyAuditFindingResponse(BaseModel):
    id: str
    investigation_id: str
    audit_dimension: str
    issue_severity: str
    finding_title: str
    description: str
    linked_source_id: Optional[str] = None
    linked_passage_text: Optional[str] = None
    missing_data_condition: Optional[str] = None
    suggested_action: Optional[str] = None
    created_at: str


# ==========================================
# REPRODUCIBILITY SCHEMAS
# ==========================================

class ResearchExecutionManifestResponse(BaseModel):
    id: str
    investigation_id: str
    manifest_version: str
    manifest_hash: str
    research_question: str
    config_snapshot: Dict[str, Any]
    claim_decomposition_version: str
    search_queries: List[Dict[str, Any]]
    providers_used: List[str]
    execution_timeline: List[Dict[str, Any]]
    source_manifest: List[Dict[str, Any]]
    evidence_manifest: List[Dict[str, Any]]
    quality_assessment_snapshot: Dict[str, Any]
    reproducibility_status: str
    reproducibility_notes: Optional[str] = None
    parent_reproduced_manifest_id: Optional[str] = None
    created_at: str


class ManifestIntegrityResponse(BaseModel):
    manifest_id: str
    stored_hash: str
    computed_hash: str
    is_tamper_free: bool
    status: str


# ==========================================
# BENCHMARK SCHEMAS
# ==========================================

class BenchmarkDatasetResponse(BaseModel):
    id: str
    name: str
    slug: str
    version: str
    category: str
    research_question: str
    expected_claims: List[str]
    verified_source_references: List[str]
    expected_support_classifications: Dict[str, str]
    known_counterevidence: List[str]
    known_methodological_limitations: List[str]
    expected_conclusion: str
    evaluation_notes: Optional[str] = None
    is_active: bool
    created_at: str


class BenchmarkRunResponse(BaseModel):
    id: str
    benchmark_dataset_id: str
    investigation_id: Optional[str] = None
    run_version: str
    status: str
    retrieval_metrics: Dict[str, Any]
    evidence_metrics: Dict[str, Any]
    synthesis_metrics: Dict[str, Any]
    operations_metrics: Dict[str, Any]
    overall_evaluation_summary: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


# ==========================================
# HUMAN CORRECTION SCHEMAS
# ==========================================

class HumanEvidenceCorrectionCreate(BaseModel):
    claim_id: uuid.UUID
    evidence_id: uuid.UUID
    correction_type: str = Field(..., max_length=64)
    corrected_value: str
    reason: str = Field(..., min_length=5, max_length=1000)


class HumanEvidenceCorrectionResponse(BaseModel):
    id: str
    investigation_id: str
    claim_id: str
    evidence_id: str
    user_id: str
    correction_type: str
    original_value: str
    corrected_value: str
    reason: str
    version_number: int
    is_active: bool
    created_at: str
