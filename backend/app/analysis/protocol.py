import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    model_config = ConfigDict(extra="ignore")

    level: str = Field(pattern="^(strong|moderate|weak|insufficient|contested)$")
    explanation: str = Field(default="Confidence assessed from supplied evidence.", min_length=1, max_length=2000)

    @model_validator(mode="before")
    @classmethod
    def normalize_confidence(cls, data: Any) -> Any:
        level_map = {
            "high": "strong",
            "strong": "strong",
            "medium": "moderate",
            "moderate": "moderate",
            "low": "weak",
            "weak": "weak",
            "insufficient": "insufficient",
            "none": "insufficient",
            "contested": "contested",
        }
        if isinstance(data, str):
            mapped = level_map.get(data.lower().strip(), "moderate")
            return {"level": mapped, "explanation": f"Assessed at {mapped} confidence level."}
        if isinstance(data, dict):
            raw_lvl = str(data.get("level") or data.get("confidence_level") or data.get("confidence") or "moderate").lower().strip()
            mapped_lvl = level_map.get(raw_lvl, "moderate")
            expl = data.get("explanation") or data.get("reasoning") or f"Assessed at {mapped_lvl} confidence level."
            return {"level": mapped_lvl, "explanation": str(expl)[:2000]}
        return data


class ArgumentPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    argument_id: uuid.UUID | None = None
    claim_id: uuid.UUID
    argument_type: ArgumentType
    text: str = Field(default="Evidence-grounded analysis.", min_length=1, max_length=8000)
    evidence_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    source_ids: list[uuid.UUID] = Field(default_factory=list, max_length=100)
    evidence_basis: str = Field(default="none", pattern="^(direct|indirect|none)$")
    reasoning_summary: str = Field(default="Summary of evidence.", min_length=1, max_length=3000)
    limitations: list[str] = Field(default_factory=list, max_length=20)
    confidence: ConfidenceAssessment

    @model_validator(mode="before")
    @classmethod
    def normalize_argument(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)

        # Normalize text and reasoning_summary
        text = d.get("text") or d.get("argument") or d.get("reasoning_summary") or d.get("explanation") or d.get("summary")
        summary = d.get("reasoning_summary") or d.get("explanation") or d.get("summary") or text
        if text:
            d["text"] = str(text)
        elif not d.get("text"):
            d["text"] = "Evidence-grounded analysis for the claim."
        if summary:
            d["reasoning_summary"] = str(summary)
        elif not d.get("reasoning_summary"):
            d["reasoning_summary"] = str(d.get("text", "Evidence assessment."))

        # Normalize evidence_basis
        basis = str(d.get("evidence_basis", "")).lower().strip()
        if basis in {"direct", "indirect", "none"}:
            d["evidence_basis"] = basis
        elif d.get("evidence_ids") and len(d.get("evidence_ids", [])) > 0:
            d["evidence_basis"] = "direct"
        else:
            d["evidence_basis"] = "none"

        # Normalize confidence from flat fields
        raw_conf = d.get("confidence")
        conf_lvl = d.get("confidence_level")
        if raw_conf is None and conf_lvl is not None:
            d["confidence"] = conf_lvl
        elif raw_conf is None:
            d["confidence"] = {"level": "moderate", "explanation": "Assessed from supplied evidence."}

        # Normalize argument_type if missing or slightly varied
        arg_type = str(d.get("argument_type", "")).lower().strip()
        type_map = {
            "supporting": ArgumentType.supporting,
            "support": ArgumentType.supporting,
            "contradicting": ArgumentType.contradicting,
            "contradict": ArgumentType.contradicting,
            "counter": ArgumentType.contradicting,
            "qualifying": ArgumentType.qualifying,
            "methodological_criticism": ArgumentType.methodological_criticism,
            "methodology": ArgumentType.methodological_criticism,
            "source_criticism": ArgumentType.source_criticism,
            "source": ArgumentType.source_criticism,
            "temporal_qualification": ArgumentType.temporal_qualification,
            "temporal": ArgumentType.temporal_qualification,
        }
        if arg_type in type_map:
            d["argument_type"] = type_map[arg_type]
        elif "argument_type" not in d or not d["argument_type"]:
            d["argument_type"] = ArgumentType.qualifying

        return d


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
    execution_device: str | None = None
    tokens_per_second: float | None = None
    ttft_ms: float | None = None


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
