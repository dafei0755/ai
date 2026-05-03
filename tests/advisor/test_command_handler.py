import pytest
from datetime import datetime
from intelligent_project_analyzer.advisor.database import init_db, get_session
from intelligent_project_analyzer.advisor.object_gateway import ObjectGateway
from intelligent_project_analyzer.advisor.gate import MVPGate
from intelligent_project_analyzer.advisor.state_transition import StateTransitionService
from intelligent_project_analyzer.advisor.command_handler import CommandHandler
from intelligent_project_analyzer.advisor.models import Project, AdvisorActionDraft


@pytest.fixture
def handler():
    engine = init_db("sqlite:///:memory:")
    with get_session(engine) as session:
        gw = ObjectGateway(session)
        gate = MVPGate(gw)
        svc = StateTransitionService(gw)
        project = Project(
            project_id="proj-1", name="HAY 七里坪", object_state="draft",
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        gw.save_project(project)
        yield CommandHandler(gw, gate, svc), gw


def _draft():
    return AdvisorActionDraft(
        draft_id="d-001", project_id="proj-1", trace_id="trace-001",
        actor="user-1", action="create_project_base_patch",
        payload={"name": "HAY 七里坪"},
        created_at=datetime.utcnow(),
    )


def test_execute_creates_patch(handler):
    ch, gw = handler
    result = ch.execute(_draft())
    assert result.execution_state == "succeeded"
    ticket = gw.get_ticket(result.ticket_id)
    assert ticket is not None
    assert ticket.execution_state == "succeeded"


def test_execute_writes_audit_log(handler):
    ch, gw = handler
    ch.execute(_draft())
    logs = gw.get_audit_log("proj-1")
    assert len(logs) >= 1
    assert logs[-1].result == "success"
    assert logs[-1].trace_id == "trace-001"


def test_execute_trace_id_in_ticket(handler):
    """trace_id 贯穿：ticket 携带 trace_id"""
    ch, gw = handler
    result = ch.execute(_draft())
    ticket = gw.get_ticket(result.ticket_id)
    assert ticket.trace_id == "trace-001"


def test_frozen_object_not_written(handler):
    """红线：冻结对象 Gate 阻断后不写 Patch"""
    ch, gw = handler
    gw.update_project_state("proj-1", "frozen")
    with pytest.raises(PermissionError):
        ch.execute(_draft())
    # 确认没有成功 Patch 写入
    logs = gw.get_audit_log("proj-1")
    assert all(log.result == "failure" for log in logs)
