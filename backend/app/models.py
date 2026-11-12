import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Float, ForeignKey, String, Text, Uuid, func
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
