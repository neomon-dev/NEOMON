import json
import uuid
from datetime import datetime, timezone
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
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
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="SET NULL"), nullable=True, index=True
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    workspace: Mapped["Workspace | None"] = relationship(back_populates="investigations")
    owner: Mapped["User | None"] = relationship(foreign_keys=[owner_id])
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
    autonomous_workflows: Mapped[list["AutonomousResearchWorkflow"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )
    comment_threads: Mapped[list["CommentThread"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )
    annotations: Mapped[list["EvidenceAnnotation"]] = relationship(
        back_populates="investigation", cascade="all, delete-orphan"
    )
    review_requests: Mapped[list["ReviewRequest"]] = relationship(
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
    annotations: Mapped[list["EvidenceAnnotation"]] = relationship(
        back_populates="evidence", cascade="all, delete-orphan"
    )

    @property
    def passage(self) -> str:
        return self.exact_text or ""


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


# ===========================================================================
# MILESTONE 9: AUTONOMOUS RESEARCH WORKFLOW ENGINE
# ===========================================================================

class AutonomousResearchWorkflow(Base):
    __tablename__ = "autonomous_research_workflows"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(300))
    research_objective: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), index=True, default="created")
    autonomy_mode: Mapped[str] = mapped_column(String(30), default="bounded")
    current_cycle_number: Mapped[int] = mapped_column(Integer, default=0)
    total_cycles_completed: Mapped[int] = mapped_column(Integer, default=0)
    stopping_reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    stopping_explanation: Mapped[str] = mapped_column(Text, default="")
    scientific_confidence: Mapped[str] = mapped_column(String(30), default="medium")

    # Budgets
    budget_max_cycles: Mapped[int] = mapped_column(Integer, default=5)
    budget_max_searches: Mapped[int] = mapped_column(Integer, default=20)
    budget_max_sources: Mapped[int] = mapped_column(Integer, default=50)
    budget_max_documents: Mapped[int] = mapped_column(Integer, default=20)
    budget_max_llm_calls: Mapped[int] = mapped_column(Integer, default=30)
    budget_max_duration_seconds: Mapped[int] = mapped_column(Integer, default=1800)
    budget_max_consecutive_low_value: Mapped[int] = mapped_column(Integer, default=2)

    # Resource Accounting
    spent_searches: Mapped[int] = mapped_column(Integer, default=0)
    spent_sources: Mapped[int] = mapped_column(Integer, default=0)
    spent_documents: Mapped[int] = mapped_column(Integer, default=0)
    spent_llm_calls: Mapped[int] = mapped_column(Integer, default=0)
    consecutive_low_value_cycles: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    investigation: Mapped[Investigation] = relationship(back_populates="autonomous_workflows")
    cycles: Mapped[list["ResearchWorkflowCycle"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan", order_by="ResearchWorkflowCycle.cycle_number"
    )
    actions: Mapped[list["ResearchAction"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    checkpoints: Mapped[list["ResearchWorkflowCheckpoint"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    query_history: Mapped[list["ResearchQueryHistory"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    report: Mapped["ResearchWorkflowReport | None"] = relationship(
        back_populates="workflow", uselist=False, cascade="all, delete-orphan"
    )


class ResearchWorkflowCycle(Base):
    __tablename__ = "research_workflow_cycles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("autonomous_research_workflows.id", ondelete="CASCADE"), index=True
    )
    cycle_number: Mapped[int] = mapped_column(Integer, index=True)
    cycle_goal: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), default="planned")
    actions_total: Mapped[int] = mapped_column(Integer, default=0)
    actions_completed: Mapped[int] = mapped_column(Integer, default=0)
    actions_failed: Mapped[int] = mapped_column(Integer, default=0)
    sources_acquired: Mapped[int] = mapped_column(Integer, default=0)
    evidence_acquired: Mapped[int] = mapped_column(Integer, default=0)
    claims_updated: Mapped[int] = mapped_column(Integer, default=0)
    contradictions_detected: Mapped[int] = mapped_column(Integer, default=0)
    gaps_updated: Mapped[int] = mapped_column(Integer, default=0)
    information_gain_score: Mapped[float] = mapped_column(Float, default=0.0)
    evaluation_summary: Mapped[str] = mapped_column(Text, default="")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workflow: Mapped[AutonomousResearchWorkflow] = relationship(back_populates="cycles")
    actions: Mapped[list["ResearchAction"]] = relationship(
        back_populates="cycle", cascade="all, delete-orphan"
    )
    query_history: Mapped[list["ResearchQueryHistory"]] = relationship(
        back_populates="cycle", cascade="all, delete-orphan"
    )


class ResearchAction(Base):
    __tablename__ = "research_actions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("autonomous_research_workflows.id", ondelete="CASCADE"), index=True
    )
    cycle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_workflow_cycles.id", ondelete="CASCADE"), index=True
    )
    action_type: Mapped[str] = mapped_column(String(60), index=True)
    target_entity_type: Mapped[str] = mapped_column(String(40), default="")
    target_entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    objective: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str] = mapped_column(Text)
    search_queries_json: Mapped[str] = mapped_column(Text, default="[]")
    target_providers_json: Mapped[str] = mapped_column(Text, default="[]")
    priority: Mapped[int] = mapped_column(Integer, default=3)
    expected_information_gain: Mapped[float] = mapped_column(Float, default=0.5)
    estimated_cost: Mapped[float] = mapped_column(Float, default=1.0)
    dependencies_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(40), index=True, default="pending")
    requires_approval: Mapped[bool] = mapped_column(Boolean, default=False)
    approval_notes: Mapped[str] = mapped_column(Text, default="")
    execution_result_json: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workflow: Mapped[AutonomousResearchWorkflow] = relationship(back_populates="actions")
    cycle: Mapped[ResearchWorkflowCycle] = relationship(back_populates="actions")
    query_history: Mapped[list["ResearchQueryHistory"]] = relationship(
        back_populates="action", cascade="all, delete-orphan"
    )


class ResearchWorkflowCheckpoint(Base):
    __tablename__ = "research_workflow_checkpoints"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("autonomous_research_workflows.id", ondelete="CASCADE"), index=True
    )
    checkpoint_type: Mapped[str] = mapped_column(String(50))
    cycle_number: Mapped[int] = mapped_column(Integer, default=0)
    state_snapshot_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    workflow: Mapped[AutonomousResearchWorkflow] = relationship(back_populates="checkpoints")


class ResearchQueryHistory(Base):
    __tablename__ = "research_query_histories"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("autonomous_research_workflows.id", ondelete="CASCADE"), index=True
    )
    cycle_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_workflow_cycles.id", ondelete="CASCADE"), index=True
    )
    action_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("research_actions.id", ondelete="CASCADE"), index=True
    )
    query_text: Mapped[str] = mapped_column(Text)
    normalized_query: Mapped[str] = mapped_column(Text, index=True)
    provider: Mapped[str] = mapped_column(String(50))
    results_count: Mapped[int] = mapped_column(Integer, default=0)
    relevant_count: Mapped[int] = mapped_column(Integer, default=0)
    effectiveness_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_counter_evidence_query: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    workflow: Mapped[AutonomousResearchWorkflow] = relationship(back_populates="query_history")
    cycle: Mapped[ResearchWorkflowCycle] = relationship(back_populates="query_history")
    action: Mapped[ResearchAction] = relationship(back_populates="query_history")


class ResearchWorkflowReport(Base):
    __tablename__ = "research_workflow_reports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workflow_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("autonomous_research_workflows.id", ondelete="CASCADE"), index=True, unique=True
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(300))
    executive_summary: Mapped[str] = mapped_column(Text)
    research_objective: Mapped[str] = mapped_column(Text)
    initial_state_json: Mapped[str] = mapped_column(Text, default="{}")
    final_state_json: Mapped[str] = mapped_column(Text, default="{}")
    cycles_summary_json: Mapped[str] = mapped_column(Text, default="[]")
    total_queries_executed: Mapped[int] = mapped_column(Integer, default=0)
    total_sources_acquired: Mapped[int] = mapped_column(Integer, default=0)
    total_evidence_extracted: Mapped[int] = mapped_column(Integer, default=0)
    claims_reassessed_count: Mapped[int] = mapped_column(Integer, default=0)
    contradictions_resolved_count: Mapped[int] = mapped_column(Integer, default=0)
    remaining_uncertainties_json: Mapped[str] = mapped_column(Text, default="[]")
    recommended_next_actions_json: Mapped[str] = mapped_column(Text, default="[]")
    stopping_reason: Mapped[str] = mapped_column(String(50))
    stopping_explanation: Mapped[str] = mapped_column(Text)
    calibrated_quality_tier: Mapped[str] = mapped_column(String(40), default="Moderate")
    calibrated_quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    workflow: Mapped[AutonomousResearchWorkflow] = relationship(back_populates="report")
    investigation: Mapped[Investigation] = relationship()


# ===========================================================================
# MILESTONE 10: COLLABORATIVE RESEARCH INTELLIGENCE & MULTI-USER WORKSPACES
# ===========================================================================

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120))
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(String(32), default="researcher")
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    sessions: Mapped[list["UserSession"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    memberships: Mapped[list["WorkspaceMember"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    owned_workspaces: Mapped[list["Workspace"]] = relationship(
        back_populates="owner", foreign_keys="[Workspace.owner_id]"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="user", foreign_keys="[Notification.user_id]", cascade="all, delete-orphan"
    )


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    session_token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="sessions")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship()


class Workspace(Base):
    __tablename__ = "workspaces"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    settings_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped[User] = relationship(foreign_keys=[owner_id], back_populates="owned_workspaces")
    members: Mapped[list["WorkspaceMember"]] = relationship(back_populates="workspace", cascade="all, delete-orphan")
    invitations: Mapped[list["WorkspaceInvitation"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )
    investigations: Mapped[list["Investigation"]] = relationship(back_populates="workspace")
    activities: Mapped[list["WorkspaceActivity"]] = relationship(
        back_populates="workspace", cascade="all, delete-orphan"
    )

    @property
    def settings(self) -> dict[str, Any]:
        if not self.settings_json:
            return {}
        try:
            return json.loads(self.settings_json)
        except Exception:
            return {}


class WorkspaceMember(Base):
    __tablename__ = "workspace_members"
    __table_args__ = (UniqueConstraint("workspace_id", "user_id", name="uq_workspace_member"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(32), default="researcher")
    joined_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    workspace: Mapped[Workspace] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships")


class WorkspaceInvitation(Base):
    __tablename__ = "workspace_invitations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    inviter_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[str] = mapped_column(String(32), default="researcher")
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    workspace: Mapped[Workspace] = relationship(back_populates="invitations")
    inviter: Mapped[User] = relationship(foreign_keys=[inviter_id])


class CommentThread(Base):
    __tablename__ = "comment_threads"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    investigation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("investigations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    target_entity_type: Mapped[str] = mapped_column(String(50), index=True)
    target_entity_id: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open")
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    resolved_by_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workspace: Mapped[Workspace] = relationship()
    investigation: Mapped[Investigation | None] = relationship(back_populates="comment_threads")
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])
    resolved_by: Mapped[User | None] = relationship(foreign_keys=[resolved_by_id])
    comments: Mapped[list["Comment"]] = relationship(back_populates="thread", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("comment_threads.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), nullable=True
    )
    content: Mapped[str] = mapped_column(Text)
    is_edited: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    thread: Mapped[CommentThread] = relationship(back_populates="comments")
    author: Mapped[User] = relationship()
    parent: Mapped["Comment | None"] = relationship(remote_side=[id])


class EvidenceAnnotation(Base):
    __tablename__ = "evidence_annotations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), index=True)
    evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    annotation_type: Mapped[str] = mapped_column(String(50))
    comment: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="open")
    reviewer_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    workspace: Mapped[Workspace] = relationship()
    investigation: Mapped[Investigation] = relationship(back_populates="annotations")
    evidence: Mapped[Evidence] = relationship(back_populates="annotations")
    author: Mapped[User] = relationship()


class ReviewRequest(Base):
    __tablename__ = "review_requests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), index=True)
    target_type: Mapped[str] = mapped_column(String(50), index=True)
    target_id: Mapped[str] = mapped_column(String(120), index=True)
    target_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    requester_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="submitted")
    requires_independent_review: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    workspace: Mapped[Workspace] = relationship()
    investigation: Mapped[Investigation] = relationship(back_populates="review_requests")
    requester: Mapped[User] = relationship(foreign_keys=[requester_id])
    decisions: Mapped[list["ReviewDecision"]] = relationship(
        back_populates="review_request", cascade="all, delete-orphan"
    )


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    review_request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("review_requests.id", ondelete="CASCADE"), index=True)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    decision: Mapped[str] = mapped_column(String(32))
    rationale: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())

    review_request: Mapped[ReviewRequest] = relationship(back_populates="decisions")
    reviewer: Mapped[User] = relationship()


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    link_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    user: Mapped[User] = relationship(foreign_keys=[user_id], back_populates="notifications")
    workspace: Mapped[Workspace | None] = relationship()
    actor: Mapped[User | None] = relationship(foreign_keys=[actor_id])


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    in_app_notifications_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship()


class WorkspaceActivity(Base):
    __tablename__ = "workspace_activities"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("workspaces.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action_type: Mapped[str] = mapped_column(String(50), index=True)
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    summary: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    workspace: Mapped[Workspace] = relationship(back_populates="activities")
    actor: Mapped[User | None] = relationship()

    @property
    def metadata_dict(self) -> dict[str, Any]:
        if not self.metadata_json:
            return {}
        try:
            return json.loads(self.metadata_json)
        except Exception:
            return {}


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_type: Mapped[str] = mapped_column(String(64), index=True)
    target_entity_type: Mapped[str] = mapped_column(String(64), default="investigation")
    target_entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    workspace_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True, index=True
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, index=True)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)
    current_step: Mapped[str | None] = mapped_column(String(255), nullable=True)
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=1800)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    workspace: Mapped["Workspace | None"] = relationship()
    owner: Mapped["User | None"] = relationship()

    @property
    def payload(self) -> dict[str, Any]:
        if not self.payload_json:
            return {}
        try:
            return json.loads(self.payload_json)
        except Exception:
            return {}

    @property
    def result(self) -> dict[str, Any]:
        if not self.result_json:
            return {}
        try:
            return json.loads(self.result_json)
        except Exception:
            return {}


# ==============================================================================
# MILESTONE 12: RESEARCH INTELLIGENCE VALIDATION & SCIENTIFIC REPRODUCIBILITY
# ==============================================================================

class EvidenceVerificationRecord(Base):
    """Explicit scientific verification relation between an evidence passage and a claim."""
    __tablename__ = "evidence_verification_records"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    exact_passage_text: Mapped[str] = mapped_column(Text)
    passage_location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    source_publication_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retrieval_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    relationship_classification: Mapped[str] = mapped_column(String(64), index=True)
    verification_status: Mapped[str] = mapped_column(String(32), default="verified", index=True)
    verification_method: Mapped[str] = mapped_column(String(64), default="heuristic")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_meaning: Mapped[str] = mapped_column(String(128), default="unverified")
    explanation: Mapped[str] = mapped_column(Text, default="")
    agent_or_process: Mapped[str] = mapped_column(String(64), default="verification_engine")
    model_provider_info: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_challenged: Mapped[bool] = mapped_column(Boolean, default=False)
    challenge_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_by_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    corrected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    investigation: Mapped["Investigation"] = relationship()
    claim: Mapped["Claim"] = relationship()
    evidence: Mapped["Evidence"] = relationship()
    source: Mapped["Source"] = relationship()
    corrected_by_user: Mapped["User | None"] = relationship()


class ClaimSynthesisResult(Base):
    """Synthesized evidence evaluation for an atomic claim with transparent rules."""
    __tablename__ = "claim_synthesis_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    relevant_sources_count: Mapped[int] = mapped_column(Integer, default=0)
    unique_underlying_studies_count: Mapped[int] = mapped_column(Integer, default=0)
    direct_supporting_count: Mapped[int] = mapped_column(Integer, default=0)
    partial_supporting_count: Mapped[int] = mapped_column(Integer, default=0)
    contradicting_count: Mapped[int] = mapped_column(Integer, default=0)
    contextual_count: Mapped[int] = mapped_column(Integer, default=0)
    unverified_count: Mapped[int] = mapped_column(Integer, default=0)
    methodological_limitations_json: Mapped[str] = mapped_column(Text, default="[]")
    publication_date_distribution_json: Mapped[str] = mapped_column(Text, default="{}")
    source_independence_score: Mapped[float] = mapped_column(Float, default=0.0)
    important_missing_evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    outstanding_verification_operations_json: Mapped[str] = mapped_column(Text, default="[]")
    synthesis_outcome: Mapped[str] = mapped_column(String(64), index=True)
    explanation: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    investigation: Mapped["Investigation"] = relationship()
    claim: Mapped["Claim"] = relationship()


class StudyIndependenceCluster(Base):
    """Clusters sources representing the same underlying empirical study or syndication."""
    __tablename__ = "study_independence_clusters"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), index=True)
    cluster_label: Mapped[str] = mapped_column(String(128))
    primary_source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    member_source_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    relationship_category: Mapped[str] = mapped_column(String(64), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_rationale: Mapped[str] = mapped_column(Text, default="")
    shared_attributes_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    investigation: Mapped["Investigation"] = relationship()
    primary_source: Mapped["Source | None"] = relationship()


class MethodologyAuditFinding(Base):
    """Defensible methodology assessment issue linked to empirical sources or gaps."""
    __tablename__ = "methodology_audit_findings"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), index=True)
    audit_dimension: Mapped[str] = mapped_column(String(64), index=True)
    issue_severity: Mapped[str] = mapped_column(String(32), index=True)
    finding_title: Mapped[str] = mapped_column(String(256))
    description: Mapped[str] = mapped_column(Text)
    linked_source_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"), nullable=True)
    linked_passage_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_data_condition: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    investigation: Mapped["Investigation"] = relationship()
    linked_source: Mapped["Source | None"] = relationship()


class ResearchExecutionManifest(Base):
    """Immutable machine-readable reproducibility record for a completed research run."""
    __tablename__ = "research_execution_manifests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), index=True)
    manifest_version: Mapped[str] = mapped_column(String(32), default="1.0")
    manifest_hash: Mapped[str] = mapped_column(String(64), index=True)
    research_question: Mapped[str] = mapped_column(Text)
    config_snapshot_json: Mapped[str] = mapped_column(Text, default="{}")
    claim_decomposition_version: Mapped[str] = mapped_column(String(32), default="1.0")
    search_queries_json: Mapped[str] = mapped_column(Text, default="[]")
    providers_used_json: Mapped[str] = mapped_column(Text, default="[]")
    execution_timeline_json: Mapped[str] = mapped_column(Text, default="[]")
    source_manifest_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_manifest_json: Mapped[str] = mapped_column(Text, default="[]")
    quality_assessment_snapshot_json: Mapped[str] = mapped_column(Text, default="{}")
    reproducibility_status: Mapped[str] = mapped_column(String(32), default="fully_reproducible")
    reproducibility_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_reproduced_manifest_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    investigation: Mapped["Investigation"] = relationship()


class BenchmarkDataset(Base):
    """Standardized versioned scientific benchmark dataset."""
    __tablename__ = "benchmark_datasets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128))
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    version: Mapped[str] = mapped_column(String(32), default="1.0")
    category: Mapped[str] = mapped_column(String(64), index=True)
    research_question: Mapped[str] = mapped_column(Text)
    expected_claims_json: Mapped[str] = mapped_column(Text, default="[]")
    verified_source_references_json: Mapped[str] = mapped_column(Text, default="[]")
    expected_support_classifications_json: Mapped[str] = mapped_column(Text, default="{}")
    known_counterevidence_json: Mapped[str] = mapped_column(Text, default="[]")
    known_methodological_limitations_json: Mapped[str] = mapped_column(Text, default="[]")
    expected_conclusion: Mapped[str] = mapped_column(Text, default="")
    evaluation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class BenchmarkRun(Base):
    """Execution and quantitative evaluation of a benchmark against an investigation."""
    __tablename__ = "benchmark_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    benchmark_dataset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("benchmark_datasets.id", ondelete="CASCADE"), index=True)
    investigation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("investigations.id", ondelete="SET NULL"), nullable=True)
    run_version: Mapped[str] = mapped_column(String(32), default="1.0")
    status: Mapped[str] = mapped_column(String(32), default="completed", index=True)
    retrieval_metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    evidence_metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    synthesis_metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    operations_metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    overall_evaluation_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    benchmark_dataset: Mapped["BenchmarkDataset"] = relationship()
    investigation: Mapped["Investigation | None"] = relationship()


class HumanEvidenceCorrection(Base):
    """Immutable audit record of researcher or reviewer correction to scientific findings."""
    __tablename__ = "human_evidence_corrections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), index=True)
    claim_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("claims.id", ondelete="CASCADE"), index=True)
    evidence_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    correction_type: Mapped[str] = mapped_column(String(64), index=True)
    original_value: Mapped[str] = mapped_column(Text)
    corrected_value: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(Text)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    investigation: Mapped["Investigation"] = relationship()
    claim: Mapped["Claim"] = relationship()
    evidence: Mapped["Evidence"] = relationship()
    user: Mapped["User"] = relationship()




