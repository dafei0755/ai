import pytest
from datetime import datetime
from intelligent_project_analyzer.advisor.database import init_db, get_session
from intelligent_project_analyzer.advisor.object_gateway import ObjectGateway
from intelligent_project_analyzer.advisor.gate import MVPGate, GateError
from intelligent_project_analyzer.advisor.models import Project, AdvisorActionDraft


_SENTINEL = object()


def _draft(project_id="proj-1", actor="user-1", action="create_project_base_patch",
           payload=_SENTINEL) -> AdvisorActionDraft:
    if payload is _SENTINEL:
        payload = {"name": "HAY 七里坪"}
    return AdvisorActionDraft(
        draft_id="d-001", project_id=project_id, trace_id="t-001",
        actor=actor, action=action,
        payload=payload,
        created_at=datetime.utcnow(),
    )


@pytest.fixture
def setup():
    engine = init_db("sqlite:///:memory:")
    with get_session(engine) as session:
        gw = ObjectGateway(session)
        gate = MVPGate(gw)
        project = Project(
            project_id="proj-1", name="HAY 七里坪", object_state="draft",
            created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
        )
        gw.save_project(project)
        yield gate, gw


def test_schema_check_fails_on_empty_payload(setup):
    """红线：Draft 缺必填字段返回 422"""
    gate, _ = setup
    draft = _draft(payload={})
    result = gate.run(draft, actor="user-1")
    assert not result.passed
    assert any(e.code == 422 for e in result.errors)


def test_permission_check_fails_for_unknown_actor(setup):
    """权限校验：未知 actor 返回 403"""
    gate, _ = setup
    draft = _draft(actor="unknown-user")
    result = gate.run(draft, actor="unknown-user")
    assert not result.passed
    assert any(e.code == 403 for e in result.errors)


def test_object_state_check_fails_on_frozen(setup):
    """红线：冻结对象直写返回 409"""
    gate, gw = setup
    gw.update_project_state("proj-1", "frozen")
    draft = _draft()
    result = gate.run(draft, actor="user-1")
    assert not result.passed
    assert any(e.code == 409 for e in result.errors)


def test_object_state_not_changed_on_gate_failure(setup):
    """红线：Gate 阻断后对象状态不变"""
    gate, gw = setup
    gw.update_project_state("proj-1", "frozen")
    draft = _draft()
    gate.run(draft, actor="user-1")
    # 状态仍为 frozen，Gate 失败不改变对象状态
    assert gw.get_project("proj-1").object_state == "frozen"


def test_confirmation_required_returns_202(setup):
    """需要确认时返回 202 + pending_confirmation"""
    gate, _ = setup
    draft = _draft()
    result = gate.run(draft, actor="user-1")
    # schema OK, permission OK, state OK → needs confirmation
    assert result.needs_confirmation is True
    assert result.response_code == 202


def test_valid_payload_passes_schema_check(setup):
    """包含 name 字段的 payload 通过 schema 校验"""
    gate, _ = setup
    draft = _draft(payload={"name": "HAY 七里坪"})
    result = gate.run(draft, actor="user-1")
    assert not any(e.code == 422 for e in result.errors)
