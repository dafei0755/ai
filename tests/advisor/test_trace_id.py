"""trace_id 回放测试：单次请求 trace_id 必须出现在 4 处。

Phase A 硬验收：
□ 所有写操作必须产生 AuditLog
□ Draft 对象缺必填字段返回 422
□ 非法状态迁移返回 409
□ 冻结对象直写、Gate 阻断、越权调用必须有失败用例
"""
import pytest
import uuid
from datetime import datetime
from intelligent_project_analyzer.advisor.database import init_db, get_session
from intelligent_project_analyzer.advisor.object_gateway import ObjectGateway
from intelligent_project_analyzer.advisor.gate import MVPGate
from intelligent_project_analyzer.advisor.state_transition import StateTransitionService, InvalidStateTransitionError
from intelligent_project_analyzer.advisor.command_handler import CommandHandler
from intelligent_project_analyzer.advisor.models import Project, AdvisorActionDraft


@pytest.fixture
def full_stack():
    engine = init_db("sqlite:///:memory:")
    with get_session(engine) as session:
        gw = ObjectGateway(session)
        gate = MVPGate(gw)
        state_svc = StateTransitionService(gw)
        ch = CommandHandler(gw, gate, state_svc)
        project = Project(
            project_id="proj-trace", name="Trace Test",
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        gw.save_project(project)
        yield ch, gw, state_svc


def _draft(trace_id: str) -> AdvisorActionDraft:
    return AdvisorActionDraft(
        draft_id=str(uuid.uuid4()),
        project_id="proj-trace",
        trace_id=trace_id,
        actor="user-1",
        action="create_project_base_patch",
        payload={"name": "Trace Test"},
        created_at=datetime.utcnow(),
    )


def test_trace_id_in_ticket(full_stack):
    """trace_id 必须出现在 SyncExecutionTicket 中"""
    ch, gw, _ = full_stack
    trace_id = f"trace-{uuid.uuid4().hex[:8]}"
    ticket = ch.execute(_draft(trace_id))
    stored = gw.get_ticket(ticket.ticket_id)
    assert stored.trace_id == trace_id


def test_trace_id_in_audit_log(full_stack):
    """trace_id 必须出现在 AuditLogEntry 中"""
    ch, gw, _ = full_stack
    trace_id = f"trace-{uuid.uuid4().hex[:8]}"
    ch.execute(_draft(trace_id))
    logs = gw.get_audit_log("proj-trace")
    assert any(log.trace_id == trace_id for log in logs)


def test_audit_log_written_on_success(full_stack):
    """所有写操作必须产生 AuditLog（Phase A 硬验收）"""
    ch, gw, _ = full_stack
    before = len(gw.get_audit_log("proj-trace"))
    ch.execute(_draft("trace-x"))
    after = len(gw.get_audit_log("proj-trace"))
    assert after > before


def test_audit_log_written_on_failure(full_stack):
    """Gate 阻断时也必须产生失败 AuditLog"""
    ch, gw, _ = full_stack
    gw.update_project_state("proj-trace", "frozen")
    before = len(gw.get_audit_log("proj-trace"))
    with pytest.raises(PermissionError):
        ch.execute(_draft("trace-fail"))
    after = len(gw.get_audit_log("proj-trace"))
    assert after > before
    logs = gw.get_audit_log("proj-trace")
    assert logs[-1].result == "failure"


# ── Phase A 硬验收：架构红线汇总 ──────────────────────────────────

def test_hardgate_frozen_write_rejected(full_stack):
    """硬验收：冻结对象直写返回 409"""
    ch, gw, _ = full_stack
    gw.update_project_state("proj-trace", "frozen")
    with pytest.raises(PermissionError) as exc:
        ch.execute(_draft("trace-frozen"))
    assert "frozen" in str(exc.value).lower() or "Gate blocked" in str(exc.value)


def test_hardgate_schema_missing_name(full_stack):
    """硬验收：Draft 缺必填字段 name 返回 422"""
    ch, gw, _ = full_stack
    # 重置状态
    gw.update_project_state("proj-trace", "draft")
    bad_draft = AdvisorActionDraft(
        draft_id=str(uuid.uuid4()), project_id="proj-trace",
        trace_id="trace-422", actor="user-1",
        action="create_project_base_patch",
        payload={},  # 缺少 name
        created_at=datetime.utcnow(),
    )
    with pytest.raises(ValueError) as exc:
        ch.execute(bad_draft)
    assert "422" in str(exc.value)


def test_hardgate_unauthorized_actor(full_stack):
    """硬验收：跨域越权调用返回 403"""
    ch, gw, _ = full_stack
    gw.update_project_state("proj-trace", "draft")
    unauthorized_draft = AdvisorActionDraft(
        draft_id=str(uuid.uuid4()), project_id="proj-trace",
        trace_id="trace-403", actor="hacker",
        action="create_project_base_patch",
        payload={"name": "hack"},
        created_at=datetime.utcnow(),
    )
    with pytest.raises(PermissionError):
        ch.execute(unauthorized_draft)


def test_hardgate_illegal_state_transition(full_stack):
    """硬验收：非法状态迁移返回 409"""
    _, gw, state_svc = full_stack
    gw.update_project_state("proj-trace", "frozen")
    with pytest.raises(InvalidStateTransitionError) as exc:
        state_svc.transition("proj-trace", "draft")
    assert exc.value.status_code == 409
