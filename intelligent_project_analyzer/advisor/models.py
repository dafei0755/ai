from datetime import datetime
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field

ObjectState = Literal["draft", "pending_confirmation", "frozen", "stale"]
ExecutionState = Literal["pending", "running", "succeeded", "failed", "cancelled", "timeout"]
EvidenceStatus = Literal["none", "internal_hint", "verified"]


class Project(BaseModel):
    project_id: str
    name: str
    object_state: ObjectState = "draft"
    object_version: str = "0.1.0"
    created_at: datetime
    updated_at: datetime


class ProjectContext(BaseModel):
    project_id: str
    raw_description: str
    structured_data: dict[str, Any] = Field(default_factory=dict)
    evidence_status: EvidenceStatus = "none"


class AlignedBrief(BaseModel):
    project_id: str
    object_state: ObjectState = "draft"
    content: dict[str, Any] = Field(default_factory=dict)


class AdvisorActionDraft(BaseModel):
    draft_id: str
    project_id: str
    trace_id: str
    actor: str
    action: str
    payload: dict[str, Any]
    object_state: ObjectState = "draft"
    created_at: datetime


class ProjectBasePatch(BaseModel):
    patch_id: str
    project_id: str
    draft_id: str
    content: dict[str, Any]
    object_state: Literal["draft", "applied", "discarded"] = "draft"
    created_at: datetime


class SyncExecutionTicket(BaseModel):
    ticket_id: str
    trace_id: str
    draft_id: str
    actor: str
    action: str
    object_id: str
    object_version: str
    execution_state: ExecutionState
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class AuditLogEntry(BaseModel):
    log_id: str
    trace_id: str
    ticket_id: str
    actor: str
    action: str
    object_id: str
    object_version_before: str
    object_version_after: str
    result: Literal["success", "failure"]
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
