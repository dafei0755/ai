"""
tests/integration/test_dual_mode_api.py
dual_mode_routes.py 集成测试（TestClient，无须启动真实服务器）
Created by GitHub Copilot · 2026-03-15

覆盖范围：
  - POST /api/v2/conversation/message
  - GET  /api/v2/conversation/{session_id}/drafts
  - POST /api/v2/conversation/{session_id}/upgrade
  - GET  /api/v2/session/{session_id}/mode
  - POST /api/v2/project/gate
  - GET  /api/v2/project/{session_id}/taskbook
  - GET  /api/v2/project/{session_id}/blueprint
  - POST /api/v2/project/{session_id}/delta
  - GET  /api/v2/project/{session_id}/archive
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, ANY


# ─────────────────────────────────────────────────────────────────────────────
# 导入守卫
# ─────────────────────────────────────────────────────────────────────────────

try:
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from intelligent_project_analyzer.api.dual_mode_routes import router as dual_mode_router
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="dual_mode_routes 未就绪")

# ─────────────────────────────────────────────────────────────────────────────
# 测试 App（最小化，仅挂载 dual_mode_router）
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def test_app():
    app = FastAPI()
    app.include_router(dual_mode_router)
    return app


@pytest.fixture(scope="module")
def client(test_app):
    return TestClient(test_app)


# ─────────────────────────────────────────────────────────────────────────────
# Mock session manager（内存 dict 模拟）
# ─────────────────────────────────────────────────────────────────────────────

_fake_sessions: dict = {}


class _FakeSM:
    async def connect(self): pass

    async def create(self, session_id: str, data: dict):
        _fake_sessions[session_id] = dict(data)

    async def get(self, session_id: str):
        return _fake_sessions.get(session_id)

    async def update(self, session_id: str, data: dict):
        if session_id in _fake_sessions:
            _fake_sessions[session_id].update(data)

    async def delete(self, session_id: str):
        _fake_sessions.pop(session_id, None)


@pytest.fixture(autouse=True)
def mock_session_manager():
    from intelligent_project_analyzer.api import dual_mode_routes as dm_routes
    _fake_sessions.clear()
    dm_routes._session_manager_instance = _FakeSM()
    yield
    dm_routes._session_manager_instance = None


# ─────────────────────────────────────────────────────────────────────────────
# Helper — 预先在 _fake_sessions 中插入会话
# ─────────────────────────────────────────────────────────────────────────────

def _seed_session(session_id: str, **kwargs):
    _fake_sessions[session_id] = {
        "session_id": session_id,
        "system_mode": "conversation",
        "status": "conversation_active",
        "conversation_drafts": [],
        "upgrade_signal": None,
        "cognition_indicators": None,
        "requirements_frozen": False,
        "design_task_book": None,
        "execution_blueprint": None,
        "project_archive": None,
        "metadata": {},
        **kwargs,
    }


# ─────────────────────────────────────────────────────────────────────────────
# router 注册完整性
# ─────────────────────────────────────────────────────────────────────────────

class TestRouterRegistration:
    def test_nine_endpoints_registered(self):
        assert len(dual_mode_router.routes) == 9

    def test_prefix_is_api_v2(self):
        assert dual_mode_router.prefix == "/api/v2"


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v2/conversation/message
# ─────────────────────────────────────────────────────────────────────────────

class TestConversationMessage:
    def test_creates_new_session_when_no_id(self, client):
        with patch(
            "intelligent_project_analyzer.workflow.conversation_engine.ConversationEngine.execute",
            new_callable=AsyncMock,
            return_value={
                "conversation_reply": "你好！",
                "conversation_intent": "knowledge_qa",
                "conversation_drafts": [],
            },
        ):
            resp = client.post("/api/v2/conversation/message", json={"message": "你好"})
        assert resp.status_code == 200
        data = resp.json()
        assert "session_id" in data
        assert data["session_id"].startswith("conv-")
        assert data["reply"] == "你好！"

    def test_uses_existing_session(self, client):
        _seed_session("existing-001")
        with patch(
            "intelligent_project_analyzer.workflow.conversation_engine.ConversationEngine.execute",
            new_callable=AsyncMock,
            return_value={
                "conversation_reply": "收到",
                "conversation_intent": "project_signal",
                "conversation_drafts": [],
            },
        ):
            resp = client.post(
                "/api/v2/conversation/message",
                json={"session_id": "existing-001", "message": "我的项目预算 500 万"},
            )
        assert resp.status_code == 200
        assert resp.json()["session_id"] == "existing-001"

    def test_404_for_nonexistent_session(self, client):
        resp = client.post(
            "/api/v2/conversation/message",
            json={"session_id": "nonexistent", "message": "test"},
        )
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v2/conversation/{session_id}/drafts
# ─────────────────────────────────────────────────────────────────────────────

class TestGetDrafts:
    def test_returns_empty_list(self, client):
        _seed_session("drafts-001")
        resp = client.get("/api/v2/conversation/drafts-001/drafts")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["drafts"] == []

    def test_returns_drafts(self, client):
        _seed_session("drafts-002", conversation_drafts=[
            {
                "draft_id": "d001",
                "draft_type": "intent_seed",
                "content": {"intent": "project"},
                "status": "draft",
                "created_at": "2026-03-15T10:00:00",
            }
        ])
        resp = client.get("/api/v2/conversation/drafts-002/drafts")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    def test_404_for_missing_session(self, client):
        resp = client.get("/api/v2/conversation/missing-session/drafts")
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v2/conversation/{session_id}/upgrade
# ─────────────────────────────────────────────────────────────────────────────

class TestConfirmUpgrade:
    def test_upgrade_with_drafts(self, client):
        _seed_session("upgrade-001", conversation_drafts=[
            {"draft_id": "d1", "raw_intent": "餐厅", "keywords": []}
        ])
        with patch(
            "intelligent_project_analyzer.workflow.mode_router.upgrade_compiler",
            return_value=MagicMock(model_dump=lambda: {"raw_user_prompt": "编译后的简报"}),
        ):
            resp = client.post(
                "/api/v2/conversation/upgrade-001/upgrade",
                json={"session_id": "upgrade-001", "confirmed": True},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "upgraded"
        assert data["system_mode"] == "project"

    def test_upgrade_requires_confirmed_true(self, client):
        _seed_session("upgrade-002")
        resp = client.post(
            "/api/v2/conversation/upgrade-002/upgrade",
            json={"session_id": "upgrade-002", "confirmed": False},
        )
        assert resp.status_code == 400

    def test_upgrade_without_drafts_returns_not_ready(self, client):
        _seed_session("upgrade-003", conversation_drafts=[])
        resp = client.post(
            "/api/v2/conversation/upgrade-003/upgrade",
            json={"session_id": "upgrade-003", "confirmed": True},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "not_ready"

    def test_already_in_project_mode(self, client):
        _seed_session("upgrade-004", system_mode="project")
        resp = client.post(
            "/api/v2/conversation/upgrade-004/upgrade",
            json={"session_id": "upgrade-004", "confirmed": True},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "already_in_project_mode"


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v2/session/{session_id}/mode
# ─────────────────────────────────────────────────────────────────────────────

class TestGetSessionMode:
    def test_returns_mode(self, client):
        _seed_session("mode-001", system_mode="project", requirements_frozen=True)
        resp = client.get("/api/v2/session/mode-001/mode")
        assert resp.status_code == 200
        data = resp.json()
        assert data["system_mode"] == "project"
        assert data["requirements_frozen"] is True

    def test_default_conversation_mode(self, client):
        _seed_session("mode-002")
        resp = client.get("/api/v2/session/mode-002/mode")
        assert resp.status_code == 200
        assert resp.json()["system_mode"] == "conversation"

    def test_404_for_missing(self, client):
        resp = client.get("/api/v2/session/missing/mode")
        assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v2/project/gate
# ─────────────────────────────────────────────────────────────────────────────

class TestRunGate:
    def test_gate_continue(self, client):
        _seed_session("gate-001", system_mode="project")
        mock_decision = MagicMock()
        mock_decision.model_dump.return_value = {
            "status": "CONTINUE",
            "interaction_state": "CLEAR",
            "gap_questions": [],
            "confidence": 0.92,
        }
        mock_command = MagicMock()
        mock_command.update = {"gate_decision": mock_decision}

        with patch(
            "intelligent_project_analyzer.workflow.nodes.gate_node.GateNode.execute",
            return_value=mock_command,
        ):
            resp = client.post("/api/v2/project/gate", json={
                "session_id": "gate-001",
                "raw_user_prompt": "设计 2000 平商业大堂，预算 800 万，8 个月完工",
            })
        assert resp.status_code == 200
        assert resp.json()["gate_status"] == "CONTINUE"


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v2/project/{session_id}/taskbook
# ─────────────────────────────────────────────────────────────────────────────

class TestGetTaskBook:
    def test_404_when_no_taskbook(self, client):
        _seed_session("tb-001", requirements_frozen=True)
        resp = client.get("/api/v2/project/tb-001/taskbook")
        assert resp.status_code == 404

    def test_returns_taskbook(self, client):
        _seed_session("tb-002", requirements_frozen=True, design_task_book={"session_id": "tb-002"})
        resp = client.get("/api/v2/project/tb-002/taskbook")
        assert resp.status_code == 200
        assert resp.json()["task_book"] is not None


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v2/project/{session_id}/blueprint
# ─────────────────────────────────────────────────────────────────────────────

class TestGetBlueprint:
    def test_returns_none_when_not_generated(self, client):
        _seed_session("bp-001")
        resp = client.get("/api/v2/project/bp-001/blueprint")
        assert resp.status_code == 200
        assert resp.json()["blueprint"] is None


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v2/project/{session_id}/delta
# ─────────────────────────────────────────────────────────────────────────────

class TestSubmitDelta:
    def test_400_when_not_frozen(self, client):
        _seed_session("delta-001", requirements_frozen=False)
        resp = client.post("/api/v2/project/delta-001/delta", json={
            "session_id": "delta-001",
            "modification_text": "改一下灯光",
        })
        assert resp.status_code == 400

    def test_routes_delta_modification(self, client):
        _seed_session("delta-002", requirements_frozen=True, system_mode="project")
        mock_ig = MagicMock()
        mock_ig.model_dump.return_value = {"requires_derived_project": False, "affected_node_ids": ["n1"]}
        mock_cmd = MagicMock()
        mock_cmd.update = {"impact_graph": mock_ig}
        mock_cmd.goto = "execution_orchestrator"

        with patch(
            "intelligent_project_analyzer.workflow.nodes.delta_router.DeltaRouter.route",
            return_value=mock_cmd,
        ):
            resp = client.post("/api/v2/project/delta-002/delta", json={
                "session_id": "delta-002",
                "modification_text": "微调 B 区灯光设计",
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["delta_type"] in ("delta", "derived")


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v2/project/{session_id}/archive
# ─────────────────────────────────────────────────────────────────────────────

class TestGetArchive:
    def test_404_when_no_archive(self, client):
        _seed_session("arch-001")
        resp = client.get("/api/v2/project/arch-001/archive")
        assert resp.status_code == 404

    def test_returns_archive(self, client):
        _seed_session("arch-002", project_archive={"session_id": "arch-002", "created_at": "2026-03-15"})
        resp = client.get("/api/v2/project/arch-002/archive")
        assert resp.status_code == 200
        assert resp.json()["archive"] is not None
