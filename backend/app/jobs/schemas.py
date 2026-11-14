"""Pydantic schemas for Background Jobs."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class JobCreateRequest(BaseModel):
    job_type: str = Field(..., min_length=1, max_length=64)
    target_entity_type: str = Field("investigation", max_length=64)
    target_entity_id: Optional[uuid.UUID] = None
    workspace_id: Optional[uuid.UUID] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(0, ge=0, le=10)
    timeout_seconds: int = Field(1800, ge=10, le=7200)
    max_retries: int = Field(3, ge=0, le=10)


class JobResponse(BaseModel):
    id: str
    job_type: str
    target_entity_type: str
    target_entity_id: Optional[str] = None
    workspace_id: Optional[str] = None
    owner_id: Optional[str] = None
    status: str
    priority: int
    progress_percent: float
    current_step: Optional[str] = None
    max_retries: int
    retry_count: int
    timeout_seconds: int
    payload: Dict[str, Any] = Field(default_factory=dict)
    result: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    worker_id: Optional[str] = None
    cancel_requested: bool
    queued_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    heartbeat_at: Optional[str] = None


class WorkerStatusResponse(BaseModel):
    worker_id: str
    is_running: bool
    concurrency_limit: int
    active_jobs: int
    queued_jobs: int
    completed_jobs: int
    failed_jobs: int
    uptime_seconds: float
