import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class ExecutionStatus(StrEnum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class Investigation(Base):
    __tablename__ = "investigations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    question: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String(16), default="quick")
    timeframe: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="created")
    quality_status: Mapped[str] = mapped_column(String(32), default="insufficient_evidence")
    quality_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevant_source_count: Mapped[int] = mapped_column(default=0)
    full_text_count: Mapped[int] = mapped_column(default=0)
    evidence_gap: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    executions: Mapped[list["AgentExecution"]] = relationship(back_populates="investigation")
    events: Mapped[list["ResearchEvent"]] = relationship(back_populates="investigation")
    queries: Mapped[list["ResearchQuery"]] = relationship(back_populates="investigation")
    sources: Mapped[list["Source"]] = relationship(back_populates="investigation")
    claims: Mapped[list["Claim"]] = relationship(back_populates="investigation")
    analysis_jobs: Mapped[list["AnalysisJob"]] = relationship(back_populates="investigation")
    gap_analyses: Mapped[list["ResearchGapAnalysis"]] = relationship(back_populates="investigation")
    hypotheses: Mapped[list["ResearchHypothesis"]] = relationship(back_populates="investigation")
    source_cross_relationships: Mapped[list["CrossInvestigationRelationship"]] = relationship(
        foreign_keys="[CrossInvestigationRelationship.source_investigation_id]", back_populates="source_investigation"
    )
    target_cross_relationships: Mapped[list["CrossInvestigationRelationship"]] = relationship(
        foreign_keys="[CrossInvestigationRelationship.target_investigation_id]", back_populates="target_investigation"
    )
    contradictions_as_primary: Mapped[list["ResearchContradiction"]] = relationship(
        foreign_keys="[ResearchContradiction.primary_investigation_id]", back_populates="primary_investigation"
    )
    contradictions_as_secondary: Mapped[list["ResearchContradiction"]] = relationship(
        foreign_keys="[ResearchContradiction.secondary_investigation_id]", back_populates="secondary_investigation"
    )
    quality_calibration: Mapped["ResearchQualityCalibration | None"] = relationship(
        back_populates="investigation", uselist=False, cascade="all, delete-orphan"
    )
    failure_impacts: Mapped[list["ProviderFailureImpact"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )
    claim_validations: Mapped[list["EvidenceClaimValidation"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    identifier: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    executions: Mapped[list["AgentExecution"]] = relationship(back_populates="agent")


class ModelConfiguration(Base):
    __tablename__ = "model_configurations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    provider: Mapped[str] = mapped_column(String(32))
    endpoint: Mapped[str] = mapped_column(String(500))
    model: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    executions: Mapped[list["AgentExecution"]] = relationship(back_populates="model_configuration")


class AgentExecution(Base):
    __tablename__ = "agent_executions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("investigations.id", ondelete="SET NULL"), nullable=True
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id", ondelete="RESTRICT"))
    model_configuration_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("model_configurations.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[ExecutionStatus] = mapped_column(String(32), default=ExecutionStatus.queued)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    agent: Mapped[Agent] = relationship(back_populates="executions")
    investigation: Mapped[Investigation | None] = relationship(back_populates="executions")
    model_configuration: Mapped[ModelConfiguration | None] = relationship(back_populates="executions")


class ResearchEvent(Base):
    __tablename__ = "research_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    investigation: Mapped[Investigation | None] = relationship(back_populates="events")


class ResearchQuery(Base):
    __tablename__ = "research_queries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), index=True)
    query: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    investigation: Mapped[Investigation] = relationship(back_populates="queries")


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(Text)
    canonical_url: Mapped[str] = mapped_column(String(1000), index=True)
    original_url: Mapped[str] = mapped_column(String(1000))
    source_type: Mapped[str] = mapped_column(String(32))
    publisher: Mapped[str | None] = mapped_column(String(300), nullable=True)
    authors_json: Mapped[str] = mapped_column(Text, default="[]")
    publication_date: Mapped[str | None] = mapped_column(String(80), nullable=True)
    doi: Mapped[str | None] = mapped_column(String(300), nullable=True, index=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    retrieval_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    relevance_reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    inclusion_status: Mapped[str] = mapped_column(String(24), default="included")
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    open_access_status: Mapped[str] = mapped_column(String(32), default="not_checked")
    selected_document_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    study_identity_key: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    investigation: Mapped[Investigation] = relationship(back_populates="sources")
    documents: Mapped[list["Document"]] = relationship(back_populates="source")
    open_access_locations: Mapped[list["OpenAccessLocation"]] = relationship(back_populates="source")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="source")
    credibility_assessment: Mapped["SourceCredibilityAssessment | None"] = relationship(
        back_populates="source", uselist=False, cascade="all, delete-orphan"
    )
    lineage_out: Mapped[list["SourceLineageRelationship"]] = relationship(
        foreign_keys="[SourceLineageRelationship.source_id]", back_populates="source", cascade="all, delete-orphan"
    )
    lineage_in: Mapped[list["SourceLineageRelationship"]] = relationship(
        foreign_keys="[SourceLineageRelationship.related_source_id]", back_populates="related_source", cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    content_type: Mapped[str] = mapped_column(String(120))
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text)
    headings_json: Mapped[str] = mapped_column(Text, default="[]")
    page_count: Mapped[int | None] = mapped_column(nullable=True)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    access_level: Mapped[str] = mapped_column(String(24), default="metadata_only")
    extraction_quality: Mapped[str] = mapped_column(String(24), default="low")
    document_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    version_type: Mapped[str] = mapped_column(String(32), default="unknown")
    access_route: Mapped[str] = mapped_column(String(32), default="original")
    metadata_match_status: Mapped[str] = mapped_column(String(24), default="unknown")
    source: Mapped[Source] = relationship(back_populates="documents")


class OpenAccessLocation(Base):
    __tablename__ = "open_access_locations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    url: Mapped[str] = mapped_column(String(1000))
    repository: Mapped[str | None] = mapped_column(String(300), nullable=True)
    version_type: Mapped[str] = mapped_column(String(32), default="unknown")
    license: Mapped[str | None] = mapped_column(String(120), nullable=True)
    match_status: Mapped[str] = mapped_column(String(24), default="unassessed")
    match_reason: Mapped[str] = mapped_column(Text, default="")
    acquisition_status: Mapped[str] = mapped_column(String(24), default="pending")
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[Source] = relationship(back_populates="open_access_locations")


class DocumentVersionRelationship(Base):
    __tablename__ = "document_version_relationships"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    related_document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(32))


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="unassessed")
    explanation: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[int] = mapped_column(default=3)
    search_objectives_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_categories_json: Mapped[str] = mapped_column(Text, default="[]")
    dependencies_json: Mapped[str] = mapped_column(Text, default="[]")
    investigation: Mapped[Investigation] = relationship(back_populates="claims")
    evidence_relationships: Mapped[list["ClaimEvidenceRelationship"]] = relationship(back_populates="claim")
    validations: Mapped[list["EvidenceClaimValidation"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan"
    )


class AnalysisJob(Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), unique=True
    )
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    max_debate_rounds: Mapped[int] = mapped_column(default=2)
    max_concurrent_agents: Mapped[int] = mapped_column(default=1)
    provider_kind: Mapped[str | None] = mapped_column(String(32), nullable=True)
    default_model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    role_models_json: Mapped[str] = mapped_column(Text, default="{}")
    cancel_requested: Mapped[bool] = mapped_column(default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    investigation: Mapped[Investigation] = relationship(back_populates="analysis_jobs")
    executions: Mapped[list["AnalysisAgentExecution"]] = relationship(back_populates="job")
    debate_rounds: Mapped[list["DebateRound"]] = relationship(back_populates="job")
    decisions: Mapped[list["AdjudicationDecision"]] = relationship(back_populates="job")
    report: Mapped["ResearchReport | None"] = relationship(back_populates="job", uselist=False)


class AnalysisAgentExecution(Base):
    __tablename__ = "analysis_agent_executions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analysis_jobs.id", ondelete="CASCADE"), index=True)
    agent_identifier: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(24), default="queued")
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    output_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    token_usage_json: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    job: Mapped[AnalysisJob] = relationship(back_populates="executions")
    arguments: Mapped[list["AgentArgument"]] = relationship(back_populates="execution")


class AgentArgument(Base):
    __tablename__ = "agent_arguments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analysis_jobs.id", ondelete="CASCADE"), index=True)
    execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analysis_agent_executions.id", ondelete="CASCADE"), index=True
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    agent_identifier: Mapped[str] = mapped_column(String(80), index=True)
    argument_type: Mapped[str] = mapped_column(String(40))
    text: Mapped[str] = mapped_column(Text)
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    source_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_basis: Mapped[str] = mapped_column(String(16), default="none")
    reasoning_summary: Mapped[str] = mapped_column(Text)
    limitations_json: Mapped[str] = mapped_column(Text, default="[]")
    confidence_level: Mapped[str] = mapped_column(String(24))
    confidence_explanation: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    execution: Mapped[AnalysisAgentExecution] = relationship(back_populates="arguments")


class DebateRound(Base):
    __tablename__ = "debate_rounds"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analysis_jobs.id", ondelete="CASCADE"), index=True)
    round_number: Mapped[int] = mapped_column()
    moderator_summary: Mapped[str] = mapped_column(Text)
    unresolved_disagreements_json: Mapped[str] = mapped_column(Text, default="[]")
    requested_follow_up_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    job: Mapped[AnalysisJob] = relationship(back_populates="debate_rounds")


class AdjudicationDecision(Base):
    __tablename__ = "adjudication_decisions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analysis_jobs.id", ondelete="CASCADE"), index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    decision: Mapped[str] = mapped_column(String(32))
    explanation: Mapped[str] = mapped_column(Text)
    supporting_argument_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    unresolved_disagreements_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    job: Mapped[AnalysisJob] = relationship(back_populates="decisions")


class ResearchReport(Base):
    __tablename__ = "research_reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analysis_jobs.id", ondelete="CASCADE"), unique=True)
    executive_summary: Mapped[str] = mapped_column(Text)
    overall_assessment: Mapped[str] = mapped_column(String(32))
    evidence_gap: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    job: Mapped[AnalysisJob] = relationship(back_populates="report")
    sections: Mapped[list["ReportSection"]] = relationship(back_populates="report")


class ReportSection(Base):
    __tablename__ = "report_sections"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("research_reports.id", ondelete="CASCADE"), index=True)
    section_type: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    claim_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    provenance_json: Mapped[str] = mapped_column(Text, default="[]")
    position: Mapped[int] = mapped_column(default=0)
    report: Mapped[ResearchReport] = relationship(back_populates="sections")


class ReportVersion(Base):
    __tablename__ = "report_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"), index=True
    )
    version_number: Mapped[int] = mapped_column(default=1)
    executive_summary: Mapped[str] = mapped_column(Text)
    overall_assessment: Mapped[str] = mapped_column(String(32))
    evidence_gap: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_strength_score: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_strength_tier: Mapped[str] = mapped_column(String(32), default="moderate")
    evidence_strength_json: Mapped[str] = mapped_column(Text, default="{}")
    sections_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    claim_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("claims.id", ondelete="SET NULL"), nullable=True, index=True)
    exact_text: Mapped[str] = mapped_column(Text)
    surrounding_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_type: Mapped[str] = mapped_column(String(24))
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    extraction_method: Mapped[str] = mapped_column(String(80))
    page_number: Mapped[int | None] = mapped_column(nullable=True)
    section_name: Mapped[str | None] = mapped_column(String(300), nullable=True)
    retrieval_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    relevance_reason: Mapped[str] = mapped_column(Text, default="")
    traceable: Mapped[bool] = mapped_column(default=True)
    source: Mapped[Source] = relationship(back_populates="evidence")
    validations: Mapped[list["EvidenceClaimValidation"]] = relationship(
        back_populates="evidence", cascade="all, delete-orphan"
    )


class ClaimEvidenceRelationship(Base):
    __tablename__ = "claim_evidence_relationships"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(24))
    explanation: Mapped[str] = mapped_column(Text)
    claim: Mapped[Claim] = relationship(back_populates="evidence_relationships")


class SearchProviderExecution(Base):
    __tablename__ = "search_provider_executions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(64))
    query: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24))
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExtractionExecution(Base):
    __tablename__ = "extraction_executions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(24))
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ResearchGapAnalysis(Base):
    __tablename__ = "research_gap_analyses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    version_number: Mapped[int] = mapped_column(default=1)
    summary: Mapped[str] = mapped_column(Text)
    critical_count: Mapped[int] = mapped_column(default=0)
    high_count: Mapped[int] = mapped_column(default=0)
    moderate_count: Mapped[int] = mapped_column(default=0)
    low_count: Mapped[int] = mapped_column(default=0)
    coverage_score: Mapped[float] = mapped_column(Float, default=0.0)
    coverage_summary_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    investigation: Mapped[Investigation] = relationship(back_populates="gap_analyses")
    gaps: Mapped[list["ResearchGap"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class ResearchGap(Base):
    __tablename__ = "research_gaps"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_gap_analyses.id", ondelete="CASCADE"), index=True
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(40), index=True)
    gap_type: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(250))
    description: Mapped[str] = mapped_column(Text)
    claim_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    source_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    supporting_explanation: Mapped[str] = mapped_column(Text)
    missing_information: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    research_priority: Mapped[float] = mapped_column(Float, default=5.0)
    confidence: Mapped[str] = mapped_column(String(20), default="medium")
    is_observed: Mapped[bool] = mapped_column(default=True)
    recommended_action_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    analysis: Mapped[ResearchGapAnalysis] = relationship(back_populates="gaps")


# ===========================================================================
# MILESTONE 8B: EVIDENCE-GROUNDED HYPOTHESIS GENERATION
# ===========================================================================

class ResearchHypothesis(Base):
    __tablename__ = "research_hypotheses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(300))
    statement: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True, default="proposed")
    claim_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    gap_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    supporting_evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    challenging_evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    proposed_mechanism: Mapped[str] = mapped_column(Text, default="")
    independent_variables_json: Mapped[str] = mapped_column(Text, default="[]")
    dependent_variables_json: Mapped[str] = mapped_column(Text, default="[]")
    expected_outcome: Mapped[str] = mapped_column(Text, default="")
    boundary_conditions: Mapped[str] = mapped_column(Text, default="")
    assumptions_json: Mapped[str] = mapped_column(Text, default="[]")
    confounding_variables_json: Mapped[str] = mapped_column(Text, default="[]")
    suggested_methodology: Mapped[str] = mapped_column(Text, default="")
    falsification_criteria: Mapped[str] = mapped_column(Text, default="")
    generation_method: Mapped[str] = mapped_column(String(40), default="deterministic")
    confidence_level: Mapped[str] = mapped_column(String(20), default="medium")
    testability_score: Mapped[float] = mapped_column(Float, default=7.0)
    novelty_score: Mapped[float] = mapped_column(Float, default=6.0)
    evidence_grounding_score: Mapped[float] = mapped_column(Float, default=7.0)
    falsifiability_score: Mapped[float] = mapped_column(Float, default=8.0)
    evaluation_notes: Mapped[str] = mapped_column(Text, default="")
    version_number: Mapped[int] = mapped_column(default=1)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    investigation: Mapped[Investigation] = relationship(back_populates="hypotheses")
    evaluations: Mapped[list["HypothesisEvaluation"]] = relationship(
        back_populates="hypothesis", cascade="all, delete-orphan"
    )


class HypothesisEvaluation(Base):
    __tablename__ = "hypothesis_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    hypothesis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_hypotheses.id", ondelete="CASCADE"), index=True
    )
    reviewer_role: Mapped[str] = mapped_column(String(60), default="hypothesis_evaluator")
    status: Mapped[str] = mapped_column(String(40), default="reviewed")
    evidence_grounding_score: Mapped[float] = mapped_column(Float, default=5.0)
    novelty_score: Mapped[float] = mapped_column(Float, default=5.0)
    logical_consistency_score: Mapped[float] = mapped_column(Float, default=5.0)
    falsifiability_score: Mapped[float] = mapped_column(Float, default=5.0)
    testability_score: Mapped[float] = mapped_column(Float, default=5.0)
    methodological_feasibility_score: Mapped[float] = mapped_column(Float, default=5.0)
    review_comments: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    hypothesis: Mapped[ResearchHypothesis] = relationship(back_populates="evaluations")


# ===========================================================================
# MILESTONE 8C: CROSS-INVESTIGATION KNOWLEDGE SYNTHESIS
# ===========================================================================

class CrossInvestigationRelationship(Base):
    __tablename__ = "cross_investigation_relationships"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    target_investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(50), index=True)
    explanation: Mapped[str] = mapped_column(Text)
    confidence: Mapped[str] = mapped_column(String(20), default="medium")
    detection_method: Mapped[str] = mapped_column(String(40), default="deterministic")
    claim_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    shared_evidence_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    source_investigation: Mapped[Investigation] = relationship(
        foreign_keys=[source_investigation_id], back_populates="source_cross_relationships"
    )
    target_investigation: Mapped[Investigation] = relationship(
        foreign_keys=[target_investigation_id], back_populates="target_cross_relationships"
    )


class InvestigationSynthesisReport(Base):
    __tablename__ = "investigation_synthesis_reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text)
    investigation_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    shared_themes_json: Mapped[str] = mapped_column(Text, default="[]")
    common_findings_json: Mapped[str] = mapped_column(Text, default="[]")
    complementary_findings_json: Mapped[str] = mapped_column(Text, default="[]")
    conflicting_findings_json: Mapped[str] = mapped_column(Text, default="[]")
    shared_evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    independent_corroboration_json: Mapped[str] = mapped_column(Text, default="[]")
    methodological_differences_json: Mapped[str] = mapped_column(Text, default="[]")
    unresolved_questions_json: Mapped[str] = mapped_column(Text, default="[]")
    cross_investigation_gaps_json: Mapped[str] = mapped_column(Text, default="[]")
    recommended_future_investigations_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ===========================================================================
# MILESTONE 8D: CONTRADICTION INTELLIGENCE
# ===========================================================================

class ResearchContradiction(Base):
    __tablename__ = "research_contradictions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    primary_investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    secondary_investigation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("investigations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True, default="moderate")
    confidence: Mapped[str] = mapped_column(String(20), default="medium")
    detection_method: Mapped[str] = mapped_column(String(40), default="deterministic")
    status: Mapped[str] = mapped_column(String(40), index=True, default="newly_detected")
    claim_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    source_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    supporting_passages_json: Mapped[str] = mapped_column(Text, default="[]")
    conflicting_passages_json: Mapped[str] = mapped_column(Text, default="[]")
    scope_differences: Mapped[str] = mapped_column(Text, default="")
    methodological_differences: Mapped[str] = mapped_column(Text, default="")
    resolution_explanation: Mapped[str] = mapped_column(Text, default="")
    recommended_research_action: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    primary_investigation: Mapped[Investigation] = relationship(
        foreign_keys=[primary_investigation_id], back_populates="contradictions_as_primary"
    )
    secondary_investigation: Mapped[Investigation | None] = relationship(
        foreign_keys=[secondary_investigation_id], back_populates="contradictions_as_secondary"
    )
    resolution_logs: Mapped[list["ContradictionResolutionLog"]] = relationship(
        back_populates="contradiction", cascade="all, delete-orphan"
    )


class ContradictionResolutionLog(Base):
    __tablename__ = "contradiction_resolution_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    contradiction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_contradictions.id", ondelete="CASCADE"), index=True
    )
    previous_status: Mapped[str] = mapped_column(String(40))
    new_status: Mapped[str] = mapped_column(String(40))
    resolution_rationale: Mapped[str] = mapped_column(Text)
    resolving_evidence_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    contradiction: Mapped[ResearchContradiction] = relationship(back_populates="resolution_logs")


# ===========================================================================
# MILESTONE 8E: RESEARCH TREND INTELLIGENCE
# ===========================================================================

class ResearchTrendAnalysis(Base):
    __tablename__ = "research_trend_analyses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text)
    total_investigations_analyzed: Mapped[int] = mapped_column(default=0)
    total_sources_analyzed: Mapped[int] = mapped_column(default=0)
    total_evidence_analyzed: Mapped[int] = mapped_column(default=0)
    temporal_span_start: Mapped[str | None] = mapped_column(String(80), nullable=True)
    temporal_span_end: Mapped[str | None] = mapped_column(String(80), nullable=True)
    trend_topics_json: Mapped[str] = mapped_column(Text, default="[]")
    emerging_themes_json: Mapped[str] = mapped_column(Text, default="[]")
    consensus_shifts_json: Mapped[str] = mapped_column(Text, default="[]")
    persistent_gaps_json: Mapped[str] = mapped_column(Text, default="[]")
    active_contradictions_count: Mapped[int] = mapped_column(default=0)
    recommendations_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    topics: Mapped[list["ResearchTrendTopic"]] = relationship(
        back_populates="analysis", cascade="all, delete-orphan"
    )


class ResearchTrendTopic(Base):
    __tablename__ = "research_trend_topics"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_trend_analyses.id", ondelete="CASCADE"), index=True
    )
    topic_name: Mapped[str] = mapped_column(String(200), index=True)
    classification: Mapped[str] = mapped_column(String(50), index=True)
    activity_score: Mapped[float] = mapped_column(Float, default=50.0)
    quality_score: Mapped[float] = mapped_column(Float, default=50.0)
    independence_score: Mapped[float] = mapped_column(Float, default=50.0)
    growth_rate: Mapped[float] = mapped_column(Float, default=0.0)
    contradiction_count: Mapped[int] = mapped_column(default=0)
    gap_count: Mapped[int] = mapped_column(default=0)
    temporal_observations_count: Mapped[int] = mapped_column(default=0)
    investigation_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    source_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    summary_narrative: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    analysis: Mapped[ResearchTrendAnalysis] = relationship(back_populates="topics")


# ===========================================================================
# MILESTONE 8G: RESEARCH QUALITY CALIBRATION & SCIENTIFIC EVIDENCE VALIDATION
# ===========================================================================

class SourceCredibilityAssessment(Base):
    __tablename__ = "source_credibility_assessments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), index=True
    )
    source_type: Mapped[str] = mapped_column(String(60), index=True)
    verification_status: Mapped[str] = mapped_column(String(40), index=True, default="unverified")
    venue: Mapped[str | None] = mapped_column(String(300), nullable=True)
    is_peer_reviewed: Mapped[bool] = mapped_column(Boolean, default=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    assessed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    source: Mapped[Source] = relationship(back_populates="credibility_assessment")


class SourceLineageRelationship(Base):
    __tablename__ = "source_lineage_relationships"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), index=True
    )
    related_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sources.id", ondelete="CASCADE"), index=True
    )
    relationship_type: Mapped[str] = mapped_column(String(60), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    shared_identifiers_json: Mapped[str] = mapped_column(Text, default="[]")
    explanation: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    source: Mapped[Source] = relationship(
        foreign_keys=[source_id], back_populates="lineage_out"
    )
    related_source: Mapped[Source] = relationship(
        foreign_keys=[related_source_id], back_populates="lineage_in"
    )


class EvidenceClaimValidation(Base):
    __tablename__ = "evidence_claim_validations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("claims.id", ondelete="CASCADE"), index=True
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evidence.id", ondelete="CASCADE"), index=True
    )
    entailment_classification: Mapped[str] = mapped_column(String(60), index=True)
    entailment_strength: Mapped[float] = mapped_column(Float, default=0.5)
    explanation: Mapped[str] = mapped_column(Text, default="")
    missing_inferential_steps_json: Mapped[str] = mapped_column(Text, default="[]")
    correlation_vs_causation_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_method: Mapped[str] = mapped_column(String(40), default="deterministic_heuristic")
    validator_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="validated")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    investigation: Mapped[Investigation] = relationship(back_populates="claim_validations")
    claim: Mapped[Claim] = relationship(back_populates="validations")
    evidence: Mapped[Evidence] = relationship(back_populates="validations")


class ResearchQualityCalibration(Base):
    __tablename__ = "research_quality_calibrations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True, unique=True
    )
    calibrated_tier: Mapped[str] = mapped_column(String(40), index=True, default="Moderate")
    raw_score: Mapped[float] = mapped_column(Float, default=0.0)
    calibrated_score: Mapped[float] = mapped_column(Float, default=0.0)
    coverage_score: Mapped[float] = mapped_column(Float, default=0.0)
    failure_penalty: Mapped[float] = mapped_column(Float, default=0.0)
    dimension_breakdown_json: Mapped[str] = mapped_column(Text, default="{}")
    calibration_reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    investigation: Mapped[Investigation] = relationship(back_populates="quality_calibration")


class ProviderFailureImpact(Base):
    __tablename__ = "provider_failure_impacts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(60))
    operation: Mapped[str] = mapped_column(String(80))
    query: Mapped[str] = mapped_column(Text)
    failure_type: Mapped[str] = mapped_column(String(60))
    retry_attempts: Mapped[int] = mapped_column(Integer, default=0)
    impact_severity: Mapped[str] = mapped_column(String(40), index=True, default="harmless_optional")
    missing_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    explanation: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    investigation: Mapped[Investigation] = relationship(back_populates="failure_impacts")

