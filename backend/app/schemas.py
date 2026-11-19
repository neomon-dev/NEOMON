import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator, model_validator

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
    kind: ProviderKind = Field(default=ProviderKind.ollama)
    endpoint: str = Field(default="", min_length=0, max_length=500)
    model: str | None = Field(default=None, min_length=1, max_length=200)
    api_key: SecretStr | None = None
    allow_local_runtime: bool = False
    timeout_seconds: float | None = Field(default=None, gt=0, le=1800)
    queue_timeout_seconds: float | None = Field(default=None, gt=0, le=3600)
    inference_timeout_seconds: float | None = Field(default=None, gt=0, le=1800)
    retry_count: int = Field(default=2, ge=0, le=5)

    @model_validator(mode="before")
    @classmethod
    def pre_validate(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "provider" in data and "kind" not in data:
                data["kind"] = data["provider"]
            kind = data.get("kind")
            endpoint = data.get("endpoint")
            if not endpoint:
                if kind in ("ollama", ProviderKind.ollama):
                    data["endpoint"] = "http://127.0.0.1:11434"
                    data.setdefault("allow_local_runtime", True)
                elif kind in ("lm_studio", ProviderKind.lm_studio):
                    data["endpoint"] = "http://127.0.0.1:1234"
                    data.setdefault("allow_local_runtime", True)
                elif kind in ("openai_compatible", ProviderKind.openai_compatible):
                    data["endpoint"] = "http://127.0.0.1:1234"
                    data.setdefault("allow_local_runtime", True)
        return data

    @field_validator("endpoint")
    @classmethod
    def validate_endpoint(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed.startswith(("http://", "https://")):
            raise ValueError("endpoint must use http:// or https://")
        return trimmed.rstrip("/")


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
    workspace_id: uuid.UUID | None = None


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
    workspace_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None


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
    explanation: str = ""
    reasons: list[str] = Field(default_factory=list)


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
    research_gap = "research_gap"
    hypothesis = "hypothesis"
    contradiction = "contradiction"
    cross_investigation = "cross_investigation"
    research_trend = "research_trend"
    autonomous_workflow = "autonomous_workflow"
    research_cycle = "research_cycle"
    research_action = "research_action"


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
    research_gaps: int = 0
    hypotheses: int = 0
    contradictions: int = 0
    cross_relationships: int = 0
    trends: int = 0
    autonomous_workflows: int = 0
    research_cycles: int = 0
    research_actions: int = 0


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


class TavilyTestRequest(BaseModel):
    api_key: str | None = None
    search_depth: str | None = "basic"


class TavilyTestResponse(BaseModel):
    connected: bool
    provider: str = "tavily"
    search_depth: str = "basic"
    api_key_configured: bool
    message: str | None = None
    error: str | None = None


class TavilyStatusResponse(BaseModel):
    provider: str = "tavily"
    enabled: bool
    api_key_configured: bool
    search_depth: str
    max_results: int
    include_domains: list[str] = Field(default_factory=list)
    exclude_domains: list[str] = Field(default_factory=list)
    telemetry: dict[str, Any] = Field(default_factory=dict)


class GapSeverity(StrEnum):
    critical = "critical"
    high = "high"
    moderate = "moderate"
    low = "low"


class GapCategory(StrEnum):
    claim_coverage = "claim_coverage"
    evidence_coverage = "evidence_coverage"
    perspective = "perspective"
    research_question = "research_question"


class GapConfidence(StrEnum):
    high = "high"
    medium = "medium"
    low = "low"


class RecommendedAction(BaseModel):
    action_type: str
    description: str
    suggested_queries: list[str] = Field(default_factory=list)
    target_source_types: list[str] = Field(default_factory=list)
    expected_contribution: str


class ResearchGapView(BaseModel):
    id: uuid.UUID
    analysis_id: uuid.UUID
    investigation_id: uuid.UUID
    category: str
    gap_type: str
    title: str
    description: str
    claim_ids: list[uuid.UUID] = Field(default_factory=list)
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    source_ids: list[uuid.UUID] = Field(default_factory=list)
    supporting_explanation: str
    missing_information: str
    severity: str
    research_priority: float = 5.0
    confidence: str = "medium"
    is_observed: bool = True
    recommended_action: RecommendedAction
    created_at: datetime | None = None


class ResearchCoverageSummary(BaseModel):
    coverage_score: float = 0.0
    total_claims: int = 0
    claims_with_direct_support: int = 0
    claims_with_conflicts: int = 0
    claims_unsupported: int = 0
    claims_single_source: int = 0
    total_sources: int = 0
    independent_clusters: int = 0
    full_text_count: int = 0
    unresolved_provenance_count: int = 0
    critical_gaps: int = 0
    high_gaps: int = 0
    moderate_gaps: int = 0
    low_gaps: int = 0
    narrative: str = ""


class ResearchGapAnalysisResponse(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    version_number: int = 1
    summary: str
    coverage: ResearchCoverageSummary
    gaps: list[ResearchGapView] = Field(default_factory=list)
    created_at: datetime | None = None


class ResearchGapVersionView(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    version_number: int
    summary: str
    coverage_score: float
    critical_count: int
    high_count: int
    moderate_count: int
    low_count: int
    created_at: datetime | None = None


class ResearchGapAnalyzeRequest(BaseModel):
    provider_kind: str | None = None
    model: str | None = None
    temperature: float | None = 0.2
    force_regenerate: bool = False


# ===========================================================================
# MILESTONE 8B: EVIDENCE-GROUNDED HYPOTHESIS GENERATION SCHEMAS
# ===========================================================================

class HypothesisCategory(StrEnum):
    causal = "causal"
    correlational = "correlational"
    comparative = "comparative"
    mechanistic = "mechanistic"
    predictive = "predictive"
    null = "null"
    exploratory = "exploratory"


class HypothesisStatus(StrEnum):
    proposed = "proposed"
    under_review = "under_review"
    supported_by_subsequent_evidence = "supported_by_subsequent_evidence"
    challenged_by_subsequent_evidence = "challenged_by_subsequent_evidence"
    inconclusive = "inconclusive"
    rejected = "rejected"
    superseded = "superseded"


class HypothesisEvaluationView(BaseModel):
    id: uuid.UUID
    hypothesis_id: uuid.UUID
    reviewer_role: str
    status: str
    evidence_grounding_score: float = 5.0
    novelty_score: float = 5.0
    logical_consistency_score: float = 5.0
    falsifiability_score: float = 5.0
    testability_score: float = 5.0
    methodological_feasibility_score: float = 5.0
    review_comments: str = ""
    created_at: datetime | None = None


class HypothesisView(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    title: str
    statement: str
    rationale: str
    category: str
    status: str = "proposed"
    claim_ids: list[uuid.UUID] = Field(default_factory=list)
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    gap_ids: list[uuid.UUID] = Field(default_factory=list)
    supporting_evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    challenging_evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    proposed_mechanism: str = ""
    independent_variables: list[str] = Field(default_factory=list)
    dependent_variables: list[str] = Field(default_factory=list)
    expected_outcome: str = ""
    boundary_conditions: str = ""
    assumptions: list[str] = Field(default_factory=list)
    confounding_variables: list[str] = Field(default_factory=list)
    suggested_methodology: str = ""
    falsification_criteria: str = ""
    generation_method: str = "deterministic"
    confidence_level: str = "medium"
    testability_score: float = 7.0
    novelty_score: float = 6.0
    evidence_grounding_score: float = 7.0
    falsifiability_score: float = 8.0
    evaluation_notes: str = ""
    version_number: int = 1
    evaluations: list[HypothesisEvaluationView] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class HypothesisGenerateRequest(BaseModel):
    provider_kind: str | None = None
    model: str | None = None
    temperature: float | None = 0.2
    force_regenerate: bool = False
    focus_gap_id: uuid.UUID | None = None


class HypothesisStatusUpdateRequest(BaseModel):
    status: str
    review_comments: str = ""


class HypothesisEvaluationRequest(BaseModel):
    reviewer_role: str = "hypothesis_evaluator"
    status: str = "reviewed"
    evidence_grounding_score: float = 7.0
    novelty_score: float = 6.0
    logical_consistency_score: float = 8.0
    falsifiability_score: float = 8.0
    testability_score: float = 7.0
    methodological_feasibility_score: float = 7.0
    review_comments: str = ""


class HypothesisGenerationResponse(BaseModel):
    investigation_id: uuid.UUID
    hypotheses: list[HypothesisView] = Field(default_factory=list)
    total: int = 0


# ===========================================================================
# MILESTONE 8C: CROSS-INVESTIGATION KNOWLEDGE SYNTHESIS SCHEMAS
# ===========================================================================

class CrossRelationshipType(StrEnum):
    supports = "supports"
    challenges = "challenges"
    extends = "extends"
    refines = "refines"
    overlaps_with = "overlaps_with"
    shares_evidence_with = "shares_evidence_with"
    provides_context_for = "provides_context_for"
    contradicts = "contradicts"
    depends_on = "depends_on"
    supersedes = "supersedes"


class CrossRelationshipView(BaseModel):
    id: uuid.UUID
    source_investigation_id: uuid.UUID
    source_investigation_question: str | None = None
    target_investigation_id: uuid.UUID
    target_investigation_question: str | None = None
    relationship_type: str
    explanation: str
    confidence: str = "medium"
    detection_method: str = "deterministic"
    claim_ids: list[uuid.UUID] = Field(default_factory=list)
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    shared_evidence_count: int = 0
    created_at: datetime | None = None


class InvestigationSynthesisReportView(BaseModel):
    id: uuid.UUID
    title: str
    summary: str
    investigation_ids: list[uuid.UUID] = Field(default_factory=list)
    shared_themes: list[dict[str, Any]] = Field(default_factory=list)
    common_findings: list[dict[str, Any]] = Field(default_factory=list)
    complementary_findings: list[dict[str, Any]] = Field(default_factory=list)
    conflicting_findings: list[dict[str, Any]] = Field(default_factory=list)
    shared_evidence: list[dict[str, Any]] = Field(default_factory=list)
    independent_corroboration: list[dict[str, Any]] = Field(default_factory=list)
    methodological_differences: list[dict[str, Any]] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    cross_investigation_gaps: list[str] = Field(default_factory=list)
    recommended_future_investigations: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class CrossInvestigationSynthesisRequest(BaseModel):
    investigation_ids: list[uuid.UUID]
    provider_kind: str | None = None
    model: str | None = None


class CrossInvestigationSynthesisResponse(BaseModel):
    report: InvestigationSynthesisReportView
    relationships: list[CrossRelationshipView]


class GlobalClaimSearchResult(BaseModel):
    claim_id: uuid.UUID
    investigation_id: uuid.UUID
    investigation_question: str
    claim_text: str
    status: str
    priority: int
    evidence_count: int = 0


class SharedEvidenceResult(BaseModel):
    evidence_id: uuid.UUID
    exact_text: str
    source_id: uuid.UUID
    source_title: str
    investigation_ids: list[uuid.UUID] = Field(default_factory=list)
    investigation_questions: list[str] = Field(default_factory=list)
    is_syndicated: bool = False


# ===========================================================================
# MILESTONE 8D: CONTRADICTION INTELLIGENCE SCHEMAS
# ===========================================================================

class ContradictionCategory(StrEnum):
    direct_factual = "direct_factual"
    quantitative = "quantitative"
    causal = "causal"
    methodological = "methodological"
    temporal = "temporal"
    population_specific = "population_specific"
    scope_dependent = "scope_dependent"
    definition_based = "definition_based"
    apparent = "apparent"
    unresolved = "unresolved"


class ContradictionSeverity(StrEnum):
    critical = "critical"
    high = "high"
    moderate = "moderate"
    low = "low"


class ContradictionStatus(StrEnum):
    newly_detected = "newly_detected"
    under_investigation = "under_investigation"
    scope_difference_identified = "scope_difference_identified"
    methodological_difference_identified = "methodological_difference_identified"
    partially_resolved = "partially_resolved"
    resolved_with_evidence = "resolved_with_evidence"
    unresolved = "unresolved"
    requires_human_review = "requires_human_review"


class ContradictionResolutionLogView(BaseModel):
    id: uuid.UUID
    contradiction_id: uuid.UUID
    previous_status: str
    new_status: str
    resolution_rationale: str
    resolving_evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    created_at: datetime | None = None


class ResearchContradictionView(BaseModel):
    id: uuid.UUID
    primary_investigation_id: uuid.UUID
    primary_investigation_question: str | None = None
    secondary_investigation_id: uuid.UUID | None = None
    secondary_investigation_question: str | None = None
    title: str
    description: str
    category: str
    severity: str = "moderate"
    confidence: str = "medium"
    detection_method: str = "deterministic"
    status: str = "newly_detected"
    claim_ids: list[uuid.UUID] = Field(default_factory=list)
    evidence_ids: list[uuid.UUID] = Field(default_factory=list)
    source_ids: list[uuid.UUID] = Field(default_factory=list)
    supporting_passages: list[dict[str, Any]] = Field(default_factory=list)
    conflicting_passages: list[dict[str, Any]] = Field(default_factory=list)
    scope_differences: str = ""
    methodological_differences: str = ""
    resolution_explanation: str = ""
    recommended_research_action: str = ""
    resolution_logs: list[ContradictionResolutionLogView] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ContradictionResolveRequest(BaseModel):
    new_status: str
    resolution_rationale: str
    resolving_evidence_ids: list[uuid.UUID] = Field(default_factory=list)


class ContradictionDetectRequest(BaseModel):
    investigation_id: uuid.UUID | None = None
    cross_investigation: bool = True
    provider_kind: str | None = None
    model: str | None = None


# ===========================================================================
# MILESTONE 8E: RESEARCH TREND INTELLIGENCE SCHEMAS
# ===========================================================================

class TrendClassification(StrEnum):
    emerging_topic = "emerging_topic"
    growing_activity = "growing_activity"
    stable_topic = "stable_topic"
    declining_activity = "declining_activity"
    changing_consensus = "changing_consensus"
    increasing_disagreement = "increasing_disagreement"
    breakthrough = "breakthrough"
    persistent_gap = "persistent_gap"
    insufficient_historical_data = "insufficient_historical_data"


class ResearchTrendTopicView(BaseModel):
    id: uuid.UUID
    analysis_id: uuid.UUID
    topic_name: str
    classification: str
    activity_score: float = 50.0
    quality_score: float = 50.0
    independence_score: float = 50.0
    growth_rate: float = 0.0
    contradiction_count: int = 0
    gap_count: int = 0
    temporal_observations_count: int = 0
    investigation_ids: list[uuid.UUID] = Field(default_factory=list)
    source_ids: list[uuid.UUID] = Field(default_factory=list)
    summary_narrative: str = ""
    created_at: datetime | None = None


class ResearchTrendAnalysisResponse(BaseModel):
    id: uuid.UUID
    title: str
    summary: str
    total_investigations_analyzed: int = 0
    total_sources_analyzed: int = 0
    total_evidence_analyzed: int = 0
    temporal_span_start: str | None = None
    temporal_span_end: str | None = None
    topics: list[ResearchTrendTopicView] = Field(default_factory=list)
    emerging_themes: list[dict[str, Any]] = Field(default_factory=list)
    consensus_shifts: list[dict[str, Any]] = Field(default_factory=list)
    persistent_gaps: list[dict[str, Any]] = Field(default_factory=list)
    active_contradictions_count: int = 0
    recommendations: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime | None = None


class ResearchTrendAnalyzeRequest(BaseModel):
    provider_kind: str | None = None
    model: str | None = None
    temperature: float | None = 0.2


# ===========================================================================
# MILESTONE 8F: UNIFIED RESEARCH INTELLIGENCE SCHEMAS
# ===========================================================================

class GlobalSearchCategory(StrEnum):
    all = "all"
    investigation = "investigation"
    claim = "claim"
    evidence = "evidence"
    source = "source"
    hypothesis = "hypothesis"
    gap = "gap"
    contradiction = "contradiction"
    topic = "topic"


class GlobalResearchSearchResultItem(BaseModel):
    id: str
    entity_type: str
    title: str
    snippet: str
    investigation_id: str | None = None
    investigation_question: str | None = None
    severity_or_status: str | None = None
    score: float | None = None
    created_at: datetime | None = None


class GlobalResearchSearchResponse(BaseModel):
    items: list[GlobalResearchSearchResultItem] = Field(default_factory=list)
    total: int = 0
    query: str


class UnifiedIntelligenceOverview(BaseModel):
    total_investigations: int = 0
    connected_investigations: int = 0
    total_claims: int = 0
    total_evidence: int = 0
    total_sources: int = 0
    total_gaps: int = 0
    total_hypotheses: int = 0
    active_contradictions: int = 0
    resolved_contradictions: int = 0
    total_cross_relationships: int = 0
    active_trends_count: int = 0
    system_status: str = "operational"
    last_updated: datetime | None = None


# ===========================================================================
# MILESTONE 8G: RESEARCH QUALITY CALIBRATION SCHEMAS
# ===========================================================================

class SourceCredibilityAssessmentView(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    source_type: str
    verification_status: str
    venue: str | None = None
    is_peer_reviewed: bool = False
    is_primary: bool = False
    confidence: float = 0.5
    reasons: list[str] = Field(default_factory=list)
    assessed_at: datetime | None = None


class SourceLineageRelationshipView(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    related_source_id: uuid.UUID
    relationship_type: str
    confidence: float = 0.5
    shared_identifiers: list[str] = Field(default_factory=list)
    explanation: str = ""
    created_at: datetime | None = None


class SourceLineageClusterView(BaseModel):
    cluster_id: str
    cluster_name: str
    primary_source_id: str | None = None
    member_source_ids: list[str] = Field(default_factory=list)
    relationship_type: str
    explanation: str
    effective_independence_weight: float = 1.0


class SourceLineageOverviewResponse(BaseModel):
    investigation_id: uuid.UUID
    total_sources: int
    effective_independent_count: float
    independence_ratio: float
    lineage_summary: str
    clusters: list[SourceLineageClusterView] = Field(default_factory=list)
    relationships: list[SourceLineageRelationshipView] = Field(default_factory=list)


class EvidenceClaimValidationView(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    claim_id: uuid.UUID
    claim_text: str = ""
    evidence_id: uuid.UUID
    evidence_text: str = ""
    entailment_classification: str
    entailment_strength: float = 0.5
    explanation: str = ""
    missing_inferential_steps: list[str] = Field(default_factory=list)
    correlation_vs_causation_flag: bool = False
    validation_method: str = "deterministic_heuristic"
    validator_model: str | None = None
    status: str = "validated"
    created_at: datetime | None = None


class ProviderFailureImpactView(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    provider: str
    operation: str
    query: str
    failure_type: str
    retry_attempts: int = 0
    impact_severity: str
    missing_category: str | None = None
    explanation: str = ""
    created_at: datetime | None = None


class QualityCalibrationAuditView(BaseModel):
    investigation_id: uuid.UUID
    investigation_question: str
    calibrated_tier: str
    raw_score: float
    calibrated_score: float
    coverage_score: float
    failure_penalty: float
    dimension_breakdown: dict[str, float] = Field(default_factory=dict)
    calibration_reasons: list[str] = Field(default_factory=list)
    verified_peer_reviewed_count: int = 0
    primary_source_count: int = 0
    total_sources: int = 0
    total_claims: int = 0
    total_evidence: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class InvestigationQualityAuditItem(BaseModel):
    investigation_id: uuid.UUID
    question: str
    quality_status: str
    calibrated_tier: str
    calibrated_score: float
    raw_score: float
    coverage_score: float
    failure_penalty: float
    source_count: int
    evidence_count: int
    updated_at: datetime | None = None


# ===========================================================================
# MILESTONE 9: AUTONOMOUS RESEARCH WORKFLOW SCHEMAS
# ===========================================================================

class AutonomousWorkflowCreateRequest(BaseModel):
    investigation_id: uuid.UUID
    title: str
    research_objective: str
    autonomy_mode: str = "bounded"  # "assisted", "supervised", "bounded"
    budget_max_cycles: int = 5
    budget_max_searches: int = 20
    budget_max_sources: int = 50
    budget_max_documents: int = 20
    budget_max_duration_seconds: int = 1800
    stop_on_sufficient_evidence: bool = True
    stop_on_diminishing_returns: bool = True

    model_config = ConfigDict(populate_by_name=True)

    @model_validator(mode="before")
    @classmethod
    def map_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "max_cycles" in data and "budget_max_cycles" not in data:
                data["budget_max_cycles"] = data["max_cycles"]
            if "max_searches" in data and "budget_max_searches" not in data:
                data["budget_max_searches"] = data["max_searches"]
            if "max_searches_per_cycle" in data and "budget_max_searches" not in data:
                data["budget_max_searches"] = data["max_searches_per_cycle"] * data.get("max_cycles", 5)
            if "max_sources" in data and "budget_max_sources" not in data:
                data["budget_max_sources"] = data["max_sources"]
            if "max_sources_total" in data and "budget_max_sources" not in data:
                data["budget_max_sources"] = data["max_sources_total"]
            if "max_documents" in data and "budget_max_documents" not in data:
                data["budget_max_documents"] = data["max_documents"]
            if "max_duration_seconds" in data and "budget_max_duration_seconds" not in data:
                data["budget_max_duration_seconds"] = data["max_duration_seconds"]
        return data


class ResearchActionView(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    cycle_id: uuid.UUID
    action_type: str
    target_entity_type: str = ""
    target_entity_id: uuid.UUID | None = None
    objective: str
    rationale: str
    search_queries: list[str] = Field(default_factory=list)
    target_providers: list[str] = Field(default_factory=list)
    priority: int = 3
    expected_information_gain: float = 0.5
    estimated_cost: float = 1.0
    status: str = "pending"
    requires_approval: bool = False
    approval_notes: str = ""
    execution_result: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    created_at: datetime | None = None
    completed_at: datetime | None = None


class ResearchWorkflowCycleView(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    cycle_number: int
    cycle_goal: str
    status: str
    actions_total: int = 0
    actions_completed: int = 0
    actions_failed: int = 0
    sources_acquired: int = 0
    evidence_acquired: int = 0
    claims_updated: int = 0
    contradictions_detected: int = 0
    gaps_updated: int = 0
    information_gain_score: float = 0.0
    evaluation_summary: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    actions: list[ResearchActionView] = Field(default_factory=list)


class AutonomousWorkflowView(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    investigation_question: str = ""
    title: str
    research_objective: str
    status: str
    autonomy_mode: str
    current_cycle_number: int = 0
    total_cycles_completed: int = 0
    stopping_reason: str | None = None
    stopping_explanation: str = ""
    scientific_confidence: str = "medium"

    # Budgets
    budget_max_cycles: int = 5
    budget_max_searches: int = 20
    budget_max_sources: int = 50
    budget_max_documents: int = 20
    budget_max_duration_seconds: int = 1800

    # Resource Accounting
    spent_searches: int = 0
    spent_sources: int = 0
    spent_documents: int = 0
    spent_llm_calls: int = 0
    consecutive_low_value_cycles: int = 0

    created_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cycles: list[ResearchWorkflowCycleView] = Field(default_factory=list)


class ActionApprovalRequest(BaseModel):
    rejection_reason: str | None = None


class WorkflowContinueRequest(BaseModel):
    additional_cycles: int = 2


class ResearchWorkflowReportView(BaseModel):
    id: uuid.UUID
    workflow_id: uuid.UUID
    investigation_id: uuid.UUID
    title: str
    executive_summary: str
    research_objective: str
    cycles_summary: list[dict[str, Any]] = Field(default_factory=list)
    total_queries_executed: int = 0
    total_sources_acquired: int = 0
    total_evidence_extracted: int = 0
    claims_reassessed_count: int = 0
    contradictions_resolved_count: int = 0
    remaining_uncertainties: list[str] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)
    stopping_reason: str
    stopping_explanation: str
    calibrated_quality_tier: str = "Moderate"
    calibrated_quality_score: float = 0.0
    created_at: datetime | None = None


# ===========================================================================
# MILESTONE 10: COLLABORATION & MULTI-USER WORKSPACE SCHEMAS
# ===========================================================================

from app.collaboration.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    AuthTokenResponse,
    ChangePasswordRequest,
    PasswordResetRequest,
    PasswordResetConfirmRequest,
    UserProfileUpdateRequest,
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
    WorkspaceResponse,
    WorkspaceMemberResponse,
    WorkspaceMemberRoleUpdateRequest,
    TransferOwnershipRequest,
    InvitationCreateRequest,
    InvitationResponse,
    InvitationDetailResponse,
    ThreadCreateRequest,
    CommentCreateRequest,
    CommentUpdateRequest,
    CommentResponse,
    ThreadResponse,
    AnnotationCreateRequest,
    AnnotationStatusUpdateRequest,
    AnnotationResponse,
    ReviewRequestCreate,
    ReviewDecisionSubmit,
    ReviewDecisionResponse,
    ReviewRequestResponse,
    NotificationResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdateRequest,
    ActivityResponse,
)


# Milestone 10 Collaboration Re-exports
from app.collaboration.schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    UserResponse,
    AuthTokenResponse,
    ChangePasswordRequest,
    PasswordResetRequest,
    PasswordResetConfirmRequest,
    UserProfileUpdateRequest,
    WorkspaceCreateRequest,
    WorkspaceUpdateRequest,
    WorkspaceResponse,
    WorkspaceMemberResponse,
    WorkspaceMemberRoleUpdateRequest,
    TransferOwnershipRequest,
    InvitationCreateRequest,
    InvitationResponse,
    InvitationDetailResponse,
    ThreadCreateRequest,
    CommentCreateRequest,
    CommentUpdateRequest,
    CommentResponse,
    ThreadResponse,
    AnnotationCreateRequest,
    AnnotationStatusUpdateRequest,
    AnnotationResponse,
    ReviewRequestCreate,
    ReviewDecisionSubmit,
    ReviewDecisionResponse,
    ReviewRequestResponse,
    NotificationResponse,
    NotificationPreferenceResponse,
    NotificationPreferenceUpdateRequest,
    ActivityResponse,
)


