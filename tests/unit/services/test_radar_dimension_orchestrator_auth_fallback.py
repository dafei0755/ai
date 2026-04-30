import pytest

from intelligent_project_analyzer.services.radar_dimension_orchestrator import RadarDimensionOrchestrator


pytestmark = [pytest.mark.unit]


def _make_dims():
    return [
        {
            "id": "d1",
            "name": "预算倾向",
            "left_label": "保守",
            "right_label": "激进",
            "description": "预算偏好",
            "default_value": 30,
            "category": "resource",
            "source": "decision",
        },
        {
            "id": "d2",
            "name": "开放程度",
            "left_label": "私密",
            "right_label": "开放",
            "description": "空间开放度",
            "default_value": 60,
            "category": "experience",
            "source": "decision",
        },
        {
            "id": "d3",
            "name": "技术倾向",
            "left_label": "低技术",
            "right_label": "高技术",
            "description": "技术介入强度",
            "default_value": 50,
            "category": "technology",
            "source": "decision",
        },
        {
            "id": "d4",
            "name": "材料表达",
            "left_label": "克制",
            "right_label": "强调",
            "description": "材料表达力度",
            "default_value": 40,
            "category": "aesthetic",
            "source": "decision",
        },
        {
            "id": "d5",
            "name": "功能优先",
            "left_label": "体验优先",
            "right_label": "功能优先",
            "description": "功能导向",
            "default_value": 70,
            "category": "functional",
            "source": "decision",
        },
        {
            "id": "d6",
            "name": "文化表达",
            "left_label": "克制",
            "right_label": "鲜明",
            "description": "文化表达强度",
            "default_value": 55,
            "category": "aesthetic",
            "source": "decision",
        },
    ]


def test_orchestrator_sets_auth_fallback_diagnostics(monkeypatch):
    orch = RadarDimensionOrchestrator()

    monkeypatch.setattr(orch, "_collect_context", lambda state: {"user_input": "u", "project_type": "", "confirmed_tasks": [], "structured_data": {}, "special_scene": None})

    def _fail_attempt(_ctx, _cfg):
        return {
            "success": False,
            "error": "AuthenticationError: Error code: 401 - User not found",
            "error_code": "LLM_AUTH_401",
            "duration_ms": 5,
        }

    monkeypatch.setattr(orch, "_try_llm_generate", _fail_attempt)
    monkeypatch.setattr(orch, "_semi_dynamic_fallback", lambda _ctx, _state: {"dimensions": _make_dims()})
    monkeypatch.setattr(orch, "_inject_scene_dimensions", lambda _state, dims: dims)

    result = orch.orchestrate({})

    assert result["dimension_generation_method"] == "semi_dynamic"
    meta = result["dimension_meta"]
    assert meta["degraded"] is True
    assert meta["error_code"] == "LLM_AUTH_401"
    assert meta["generation_source"] == "fallback_auth_failed"
