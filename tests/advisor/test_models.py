import pytest
from datetime import datetime
from intelligent_project_analyzer.advisor.models import (
    Project, ProjectContext, AlignedBrief, AdvisorActionDraft,
    ProjectBasePatch, SyncExecutionTicket, AuditLogEntry,
    ObjectState, ExecutionState,
)


def test_project_default_state():
    p = Project(
        project_id="proj-001",
        name="测试项目",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    assert p.object_state == "draft"
    assert p.object_version == "0.1.0"


def test_project_context_default_evidence():
    ctx = ProjectContext(
        project_id="proj-001",
        raw_description="民宿设计项目",
    )
    assert ctx.evidence_status == "none"
    assert ctx.structured_data == {}


def test_advisor_action_draft_fields():
    draft = AdvisorActionDraft(
        draft_id="draft-001",
        project_id="proj-001",
        trace_id="trace-001",
        actor="user-1",
        action="create_project_base_patch",
        payload={"name": "HAY 七里坪"},
        created_at=datetime.utcnow(),
    )
    assert draft.object_state == "draft"


def test_sync_execution_ticket_initial_state():
    ticket = SyncExecutionTicket(
        ticket_id="ticket-001",
        trace_id="trace-001",
        draft_id="draft-001",
        actor="user-1",
        action="create_project_base_patch",
        object_id="proj-001",
        object_version="0.1.0",
        execution_state="pending",
        created_at=datetime.utcnow(),
    )
    assert ticket.completed_at is None
    assert ticket.error is None


def test_audit_log_entry_fields():
    entry = AuditLogEntry(
        log_id="log-001",
        trace_id="trace-001",
        ticket_id="ticket-001",
        actor="user-1",
        action="create_project_base_patch",
        object_id="proj-001",
        object_version_before="0.1.0",
        object_version_after="0.1.1",
        result="success",
        created_at=datetime.utcnow(),
    )
    assert entry.detail == {}
