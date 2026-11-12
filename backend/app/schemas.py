import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from app.analysis.protocol import ReportSectionView

class ErrorResponse(BaseModel):
    error: str
    message: str
    request_id: str


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    demo_mode: bool
    database: str


class ProviderKind(StrEnum):
    ollama = "ollama"
    lm_studio = "lm_studio"
    openai_compatible = "openai_compatible"


class ProviderConfigRequest(BaseModel):
    kind: ProviderKind
    endpoint: str = Field(min_length=1, max_length=500)
    model: str | None = Field(default=None, min_length=1, max_length=200)
    api_key: SecretStr | None = None
    allow_local_runtime: bool = False
    timeout_seconds: float | None = Field(default=None, gt=0, le=1800)
    queue_timeout_seconds: float | None = Field(default=None, gt=0, le=3600)
    inference_timeout_seconds: float | None = Field(default=None, gt=0, le=1800)
    retry_count: int = Field(default=2, ge=0, le=5)

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("endpoint must use http:// or https://")
        return value.rstrip("/")


class ProviderStatus(BaseModel):
    kind: ProviderKind
    endpoint: str
    connected: bool
    models: list[str] = Field(default_factory=list)
    error: str | None = None
    api_key_configured: bool = False


class AgentSummary(BaseModel):
    identifier: str
    name: str
    description: str
    status: str
    demo_mode: bool


class EventType(StrEnum):
    agent_started = "agent.started"
    agent_progress = "agent.progress"
    agent_completed = "agent.completed"
    agent_failed = "agent.failed"
    model_connected = "model.connected"
    investigation_status_changed = "investigation.status_changed"
    research_started = "research.started"
    research_query_generated = "research.query_generated"
    research_search_started = "research.search_started"
    research_search_completed = "research.search_completed"
    research_source_discovered = "research.source_discovered"
    research_document_retrieved = "research.document_retrieved"
    research_evidence_extracted = "research.evidence_extracted"
    research_claim_matched = "research.claim_matched"
    research_round_completed = "research.round_completed"
    research_failed = "research.failed"
    research_completed = "research.completed"
    analysis_queued = "analysis.queued"
    analysis_stage_changed = "analysis.stage_changed"
    analysis_agent_queued = "analysis.agent_queued"
    analysis_agent_started = "analysis.agent_started"
    analysis_agent_completed = "analysis.agent_completed"
    analysis_agent_failed = "analysis.agent_failed"
    analysis_agent_cancelled = "analysis.agent_cancelled"
    analysis_debate_round = "analysis.debate_round"
    analysis_completed = "analysis.completed"
    analysis_failed = "analysis.failed"


class ResearchEventMessage(BaseModel):
    id: uuid.UUID
    event_type: EventType
    payload: dict[str, Any]
    created_at: datetime


class AgentTask(BaseModel):
    task: str = Field(min_length=1, max_length=20_000)
    context: dict[str, Any] = Field(default_factory=dict)


class AgentResult(BaseModel):
    agent_id: str
    status: str
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    model_config = ConfigDict(extra="forbid")


class ResearchMode(StrEnum):
    quick = "quick"
    deep = "deep"


class InvestigationCreate(BaseModel):
    question: str = Field(min_length=10, max_length=10_000)
    mode: ResearchMode = ResearchMode.quick
    timeframe: str | None = Field(default=None, max_length=120)
    source_preferences: list[str] = Field(default_factory=list, max_length=20)
    max_queries: int = Field(default=8, ge=1, le=30)
    max_sources: int = Field(default=20, ge=1, le=100)


class InvestigationResponse(BaseModel):
    id: uuid.UUID
    question: str
    mode: ResearchMode
    status: str
    created_at: datetime | None
    source_count: int = 0
    evidence_count: int = 0
    quality_status: str = "insufficient_evidence"
    quality_summary: str | None = None
    relevant_source_count: int = 0
    full_text_count: int = 0
    evidence_gap: str | None = None


class ResearchQueryResponse(BaseModel):
    id: uuid.UUID
    query: str
    category: str
    provider: str | None
    executed_at: datetime | None


class SourceResponse(BaseModel):
    id: uuid.UUID
    title: str
    canonical_url: str
    original_url: str
    source_type: str
    publisher: str | None
    authors: list[str]
    publication_date: str | None
    doi: str | None
    retrieval_timestamp: datetime | None
    relevance_score: float
    relevance_reasons: list[str]
    inclusion_status: str
    rejection_reason: str | None
    access_level: str | None = None
    extraction_quality: str | None = None
    open_access_status: str = "not_checked"
    selected_document_url: str | None = None
    document_url: str | None = None
    version_type: str | None = None
    access_route: str | None = None
    metadata_match_status: str | None = None
    available_versions: list[str] = Field(default_factory=list)


class EvidenceResponse(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    claim_id: uuid.UUID | None
    exact_text: str
    surrounding_context: str | None
    evidence_type: str
    relevance_score: float
    extraction_method: str
    page_number: int | None
    section_name: str | None
    retrieval_timestamp: datetime | None
    document_id: uuid.UUID | None
    relevance_reason: str
    traceable: bool


class ClaimResponse(BaseModel):
    id: uuid.UUID
    text: str
    status: str


class ResearchStartResponse(BaseModel):
    investigation: InvestigationResponse
    queries: list[ResearchQueryResponse]
    source_count: int
    evidence_count: int
    errors: list[str] = Field(default_factory=list)


class AnalysisStartRequest(BaseModel):
    max_debate_rounds: int = Field(default=2, ge=1, le=10)
    max_concurrent_agents: int = Field(default=1, ge=1, le=10)
    provider: ProviderConfigRequest | None = None
    role_models: dict[str, str] = Field(default_factory=dict, max_length=12)


class AnalysisCoverageSummary(BaseModel):
    required_agents: list[str] = Field(default_factory=list)
    completed_agents: list[str] = Field(default_factory=list)
    failed_agents: list[str] = Field(default_factory=list)
    skipped_agents: list[str] = Field(default_factory=list)
    pending_agents: list[str] = Field(default_factory=list)
    claims_total: int = 0
    claims_evaluated: int = 0
    claims_without_arguments: int = 0
    claims_without_evidence: int = 0
    claims_with_supporting_evidence: int = 0
    claims_with_conflicting_evidence: int = 0
    coverage_percentage: float = 0.0
    is_partially_completed: bool = False


class AnalysisJobResponse(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    status: str
    max_debate_rounds: int
    max_concurrent_agents: int
    provider_kind: str | None
    default_model: str | None
    cancel_requested: bool
    error_message: str | None
    created_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    coverage: AnalysisCoverageSummary | None = None


class EvidenceStrengthBreakdown(BaseModel):
    source_independence: float = 0.0
    source_quality: float = 0.0
    full_text_coverage: float = 0.0
    methodological_rigor: float = 0.0
    conflict_resolution: float = 0.0


class EvidenceStrengthSummary(BaseModel):
    score: float = 0.0
    tier: str = "moderate"
    breakdown: EvidenceStrengthBreakdown = Field(default_factory=EvidenceStrengthBreakdown)


class ReportVersionView(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    job_id: uuid.UUID
    version_number: int
    executive_summary: str
    overall_assessment: str
    evidence_gap: str | None = None
    evidence_strength: EvidenceStrengthSummary
    created_at: datetime | None = None


class AnalysisReportResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    executive_summary: str
    overall_assessment: str
    evidence_gap: str | None
    sections: list["ReportSectionView"]
    version_number: int = 1
    evidence_strength: EvidenceStrengthSummary | None = None
    versions: list[ReportVersionView] = Field(default_factory=list)


class EvidenceClaimLink(BaseModel):
    claim_id: uuid.UUID
    claim_text: str
    claim_status: str
    relationship_type: str
    explanation: str


class WorkspaceEvidenceItem(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    investigation_question: str
    source_id: uuid.UUID
    source_title: str
    source_type: str
    source_url: str
    source_canonical_url: str
    source_publisher: str | None = None
    source_publication_date: str | None = None
    source_inclusion_status: str
    source_rejection_reason: str | None = None
    source_open_access_status: str
    document_id: uuid.UUID | None = None
    document_title: str | None = None
    document_url: str | None = None
    document_access_level: str | None = None
    document_extraction_quality: str | None = None
    document_version_type: str | None = None
    claim_id: uuid.UUID | None = None
    claim_text: str | None = None
    claim_status: str | None = None
    linked_claims: list[EvidenceClaimLink] = Field(default_factory=list)
    exact_text: str
    surrounding_context: str | None = None
    evidence_type: str
    relevance_score: float
    relevance_reason: str
    extraction_method: str
    page_number: int | None = None
    section_name: str | None = None
    retrieval_timestamp: datetime | None = None
    traceable: bool


class WorkspaceEvidencePageResponse(BaseModel):
    items: list[WorkspaceEvidenceItem]
    total: int
    limit: int
    offset: int


class SourceDocumentSummary(BaseModel):
    id: uuid.UUID
    title: str | None = None
    content_type: str
    access_level: str
    extraction_quality: str
    document_url: str | None = None
    version_type: str
    access_route: str
    metadata_match_status: str
    page_count: int | None = None
    retrieved_at: datetime | None = None
    headings: list[str] = Field(default_factory=list)


class OpenAccessLocationSummary(BaseModel):
    id: uuid.UUID
    url: str
    repository: str | None = None
    version_type: str
    license: str | None = None
    match_status: str
    match_reason: str
    acquisition_status: str
    failure_reason: str | None = None


class WorkspaceSourceItem(SourceResponse):
    investigation_id: uuid.UUID
    investigation_question: str
    evidence_count: int = 0
    document_count: int = 0
    extraction_status: str | None = None
    extraction_error: str | None = None
    documents: list[SourceDocumentSummary] = Field(default_factory=list)
    open_access_locations: list[OpenAccessLocationSummary] = Field(default_factory=list)


class WorkspaceSourcePageResponse(BaseModel):
    items: list[WorkspaceSourceItem]
    total: int
    limit: int
    offset: int


class AgentRosterSummary(BaseModel):
    identifier: str
    name: str
    description: str
    system_instructions: str
    demo_mode: bool
    total_executions: int = 0
    completed_count: int = 0
    failed_count: int = 0
    cancelled_count: int = 0
    waiting_in_queue_count: int = 0
    generating_count: int = 0
    latest_status: str = "ready"
    latest_model: str | None = None
    latest_provider_kind: str | None = None
    latest_job_id: uuid.UUID | None = None
    latest_investigation_id: uuid.UUID | None = None
    latest_started_at: datetime | None = None
    latest_completed_at: datetime | None = None
    latest_queue_wait_seconds: float | None = None
    latest_inference_duration_seconds: float | None = None
    latest_error_message: str | None = None


class AgentExecutionObservatoryItem(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    investigation_id: uuid.UUID
    investigation_question: str
    agent_identifier: str
    agent_name: str
    status: str
    model: str | None = None
    provider_kind: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    total_duration_seconds: float | None = None
    queue_wait_seconds: float | None = None
    inference_duration_seconds: float | None = None
    token_usage: dict[str, Any] = Field(default_factory=dict)
    argument_count: int = 0
    cited_evidence_count: int = 0
    claims_processed_count: int = 0
    error_message: str | None = None
    output: dict[str, Any] | None = None


class ObservatorySummary(BaseModel):
    total_jobs: int = 0
    active_jobs: int = 0
    total_executions: int = 0
    waiting_in_queue: int = 0
    generating: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0
    provider_queue_wait_timeout_seconds: float
    local_inference_timeout_seconds: float
    local_provider_max_concurrency: int


class AgentObservatoryResponse(BaseModel):
    summary: ObservatorySummary
    agents: list[AgentRosterSummary]
    executions: list[AgentExecutionObservatoryItem]
    executions_total: int
    limit: int
    offset: int


class GraphNodeType(StrEnum):
    investigation = "investigation"
    research_question = "research_question"
    claim = "claim"
    evidence = "evidence"
    document = "document"
    source = "source"
    agent_argument = "agent_argument"
    adjudication_decision = "adjudication_decision"


class GraphNodeView(BaseModel):
    id: str
    entity_id: uuid.UUID
    type: GraphNodeType
    label: str
    description: str
    investigation_id: uuid.UUID
    status: str
    missing_provenance: list[str] = Field(default_factory=list)
    has_hidden_neighbors: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphEdgeView(BaseModel):
    id: str
    source: str
    target: str
    relationship_type: str
    label: str
    classification: str | None = None
    explanation: str | None = None


class GraphTotalCounts(BaseModel):
    claims: int = 0
    evidence: int = 0
    documents: int = 0
    sources: int = 0
    arguments: int = 0
    decisions: int = 0


class InvestigationGraphResponse(BaseModel):
    investigation_id: uuid.UUID | None = None
    investigation_question: str | None = None
    investigation_status: str | None = None
    nodes: list[GraphNodeView]
    edges: list[GraphEdgeView]
    truncated: bool = False
    total_counts: GraphTotalCounts
    node_type_counts: dict[str, int] = Field(default_factory=dict)
    relationship_type_counts: dict[str, int] = Field(default_factory=dict)
    empty_reason: str | None = None
