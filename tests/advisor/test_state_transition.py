import pytest
from datetime import datetime
from intelligent_project_analyzer.advisor.database import init_db, get_session
from intelligent_project_analyzer.advisor.object_gateway import ObjectGateway
from intelligent_project_analyzer.advisor.state_transition import StateTransitionService, InvalidStateTransitionError
from intelligent_project_analyzer.advisor.models import Project


@pytest.fixture
def svc():
    engine = init_db("sqlite:///:memory:")
    with get_session(engine) as session:
        gw = ObjectGateway(session)
        yield StateTransitionService(gw), gw


def _make_project(project_id: str, state: str) -> Project:
    return Project(
        project_id=project_id, name="Test",
        object_state=state,
        created_at=datetime.utcnow(), updated_at=datetime.utcnow(),
    )


def test_draft_to_pending_confirmation(svc):
    service, gw = svc
    gw.save_project(_make_project("proj-1", "draft"))
    service.transition("proj-1", "pending_confirmation")
    assert gw.get_project("proj-1").object_state == "pending_confirmation"


def test_pending_to_frozen(svc):
    service, gw = svc
    gw.save_project(_make_project("proj-2", "pending_confirmation"))
    service.transition("proj-2", "frozen")
    assert gw.get_project("proj-2").object_state == "frozen"


def test_pending_back_to_draft(svc):
    service, gw = svc
    gw.save_project(_make_project("proj-3", "pending_confirmation"))
    service.transition("proj-3", "draft")
    assert gw.get_project("proj-3").object_state == "draft"


# ── 架构红线：非法迁移必须被拒绝 ──────────────────────────────
def test_frozen_to_draft_raises_409(svc):
    """红线：冻结对象不得直接回到草案状态"""
    service, gw = svc
    gw.save_project(_make_project("proj-4", "frozen"))
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        service.transition("proj-4", "draft")
    assert exc_info.value.status_code == 409


def test_draft_to_frozen_raises_409(svc):
    """红线：草案对象不得跳过 pending_confirmation 直接冻结"""
    service, gw = svc
    gw.save_project(_make_project("proj-5", "draft"))
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        service.transition("proj-5", "frozen")
    assert exc_info.value.status_code == 409


def test_frozen_to_stale_allowed(svc):
    """上游升版时允许 frozen → stale"""
    service, gw = svc
    gw.save_project(_make_project("proj-6", "frozen"))
    service.transition("proj-6", "stale")
    assert gw.get_project("proj-6").object_state == "stale"
