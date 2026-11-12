import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ArgumentType(StrEnum):
    supporting = "supporting"
    contradicting = "contradicting"
    qualifying = "qualifying"
    methodological_criticism = "methodological_criticism"
    source_criticism = "source_criticism"
    temporal_qualification = "temporal_qualification"


class ClaimPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: uuid.UUID | None = None
    text: str = Field(min_length=10, max_length=4000)
    explanation: str = Field(min_length=1, max_length=4000)
    priority: int = Field(ge=1, le=5)
    search_objectives: list[str] = Field(min_length=1, max_length=10)
    evidence_categories: list[str] = Field(min_length=1, max_length=10)
    dependencies: list[uuid.UUID] = Field(default_factory=list, max_length=10)


class ConfidenceAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: str = Field(pattern="^(strong|moderate|weak|insufficient|contested)$")
    explanation: str = Field(min_length=1, max_length=2000)


class ArgumentPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    argument_id: uuid.UUID | None = None
    claim_id: uuid.UUID
    argument_type: ArgumentType
    text: str = Field(min_length=1, max_length=8000)
    evidence_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    source_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    evidence_basis: str = Field(default="none", pattern="^(direct|indirect|none)$")
    reasoning_summary: str = Field(min_length=1, max_length=3000)
    limitations: list[str] = Field(default_factory=list, max_length=20)
    confidence: ConfidenceAssessment


class DebatePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round_number: int = Field(ge=1, le=10)
    moderator_summary: str = Field(min_length=1, max_length=6000)
    unresolved_disagreements: list[str] = Field(default_factory=list, max_length=20)
    requested_follow_up: list[str] = Field(default_factory=list, max_length=10)


class PlannerPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claims: list[ClaimPayload] = Field(min_length=1, max_length=20)


class DecisionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: uuid.UUID
    decision: str = Field(pattern="^(strongly_supported|moderately_supported|weakly_supported|contradictory|insufficient_evidence)$")
    explanation: str = Field(min_length=1, max_length=6000)
    supporting_argument_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    evidence_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    unresolved_disagreements: list[str] = Field(default_factory=list, max_length=20)


class EvidenceProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: uuid.UUID
    source_url: str
    access_level: str
    document_url: str | None = None
    version_type: str | None = None
    page_number: int | None = None
    section_name: str | None = None


class ReportSectionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section_type: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=12000)
    claim_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    evidence_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    provenance: list[EvidenceProvenance] = Field(default_factory=list, max_length=100)


class AgentExecutionView(BaseModel):
    id: uuid.UUID
    agent_identifier: str
    status: str
    model: str | None
    output: dict[str, object] | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    queue_wait_seconds: float | None = None
    inference_duration_seconds: float | None = None
    queue_position: int | None = None


class ClaimAnalysisView(BaseModel):
    id: uuid.UUID
    text: str
    explanation: str
    priority: int
    search_objectives: list[str]
    evidence_categories: list[str]
    dependencies: list[uuid.UUID]
    status: str


class ArgumentView(BaseModel):
    id: uuid.UUID
    claim_id: uuid.UUID
    agent_identifier: str
    argument_type: ArgumentType
    text: str
    evidence_ids: list[uuid.UUID]
    source_ids: list[uuid.UUID]
    evidence_basis: str
    reasoning_summary: str
    limitations: list[str]
    confidence: ConfidenceAssessment


class DebateRoundView(BaseModel):
    id: uuid.UUID
    round_number: int
    moderator_summary: str
    unresolved_disagreements: list[str]
    requested_follow_up: list[str]


class DecisionView(BaseModel):
    id: uuid.UUID
    claim_id: uuid.UUID
    decision: str
    explanation: str
    supporting_argument_ids: list[uuid.UUID]
    evidence_ids: list[uuid.UUID]
    unresolved_disagreements: list[str]


class ReportSectionView(BaseModel):
    id: uuid.UUID
    section_type: str
    title: str
    content: str
    claim_ids: list[uuid.UUID]
    evidence_ids: list[uuid.UUID]
    provenance: list[EvidenceProvenance]
