import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from intelligent_project_analyzer.api.advisor_routes import router
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)
client = TestClient(app)


def _mock_advisor_result():
    return {
        "project_id": "proj-1", "trace_id": "trace-001", "session_id": "sess-1",
        "user_message": "民宿设计", "module": "project_base",
        "user_action": "ask", "dispatch_level": "L1",
        "bound_object_id": "proj-1", "object_state": "draft", "object_version": "0.1.0",
        "evidence_status": "internal_hint",
        "judgment_content": "项目类型：民宿；缺失信息：面积",
        "judgment_confidence": "medium",
        "action_chips": [{"type": "ask", "label": "补充信息", "isPrimary": True,
                          "payload": {"question": "面积是多少？"}}],
        "activated_capabilities": [
            {"type": "ontology", "name": "本体论", "status": "placeholder", "summary": ""}
        ],
        "skill_output": {}, "action_draft": None, "confirmed": False,
        "ticket_id": None, "error": None,
    }


@patch("intelligent_project_analyzer.api.advisor_routes.run_advisor")
def test_post_intents_returns_200(mock_run):
    mock_run.return_value = _mock_advisor_result()
    response = client.post("/v1/advisor/intents", json={
        "project_id": "proj-1", "trace_id": "trace-001",
        "scene_context": {"module": "project_base", "user_action": "ask", "dispatch_level": "L1"},
        "message": "民宿设计",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["trace_id"] == "trace-001"
    assert data["object_state"] == "draft"
    assert data["evidence_status"] == "internal_hint"


@patch("intelligent_project_analyzer.api.advisor_routes.run_advisor")
def test_response_has_action_chips(mock_run):
    mock_run.return_value = _mock_advisor_result()
    response = client.post("/v1/advisor/intents", json={
        "project_id": "proj-1", "trace_id": "trace-001",
        "scene_context": {"module": "project_base", "user_action": "ask", "dispatch_level": "L1"},
        "message": "民宿",
    })
    data = response.json()
    assert len(data["action_chips"]) >= 1


def test_missing_project_id_returns_422():
    response = client.post("/v1/advisor/intents", json={
        "trace_id": "trace-001",
        "scene_context": {"module": "project_base", "user_action": "ask", "dispatch_level": "L1"},
        "message": "民宿",
    })
    assert response.status_code == 422


def test_post_project_returns_201():
    from intelligent_project_analyzer.api import advisor_routes
    from intelligent_project_analyzer.advisor.database import init_db
    test_engine = init_db("sqlite:///:memory:")
    original = advisor_routes._engine
    advisor_routes._engine = test_engine
    try:
        response = client.post("/v1/projects", json={"name": "测试项目"})
        assert response.status_code == 201
        assert "project_id" in response.json()
    finally:
        advisor_routes._engine = original
