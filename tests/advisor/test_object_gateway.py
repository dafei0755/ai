import pytest
from datetime import datetime
from intelligent_project_analyzer.advisor.database import init_db, get_session
from intelligent_project_analyzer.advisor.object_gateway import ObjectGateway
from intelligent_project_analyzer.advisor.models import Project, ProjectContext


@pytest.fixture
def gateway():
    engine = init_db("sqlite:///:memory:")
    with get_session(engine) as session:
        yield ObjectGateway(session)


def test_create_and_get_project(gateway):
    project = Project(
        project_id="proj-001",
        name="HAY 七里坪",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    gateway.save_project(project)
    result = gateway.get_project("proj-001")
    assert result is not None
    assert result.name == "HAY 七里坪"
    assert result.object_state == "draft"


def test_get_project_returns_none_if_missing(gateway):
    result = gateway.get_project("nonexistent")
    assert result is None


def test_save_and_get_project_context(gateway):
    ctx = ProjectContext(
        project_id="proj-001",
        raw_description="民宿设计，山地，300㎡",
    )
    gateway.save_project_context(ctx)
    result = gateway.get_project_context("proj-001")
    assert result.raw_description == "民宿设计，山地，300㎡"


def test_update_project_state(gateway):
    project = Project(
        project_id="proj-002",
        name="Test",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    gateway.save_project(project)
    gateway.update_project_state("proj-002", "pending_confirmation")
    result = gateway.get_project("proj-002")
    assert result.object_state == "pending_confirmation"
