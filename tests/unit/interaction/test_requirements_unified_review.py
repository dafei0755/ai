import pytest

from intelligent_project_analyzer.interaction.nodes import requirements_unified_review as rur


pytestmark = [pytest.mark.unit]


def _base_state():
    return {
        "user_input": "做一套高端住宅软装",
        "restructured_requirements": {
            "project_essence": "高端但克制的生活方式",
            "project_objectives": {"primary_goal": "提升居住舒适与空间气质"},
            "deliverable_expectations": ["风格策略包", "关键空间概念方案"],
        },
        "confirmed_core_tasks": [
            {"id": "t1", "title": "风格定义", "description": "确定整体风格方向"},
            {"id": "t2", "title": "空间优先级", "description": "明确客厅与主卧优先"},
        ],
        "selected_dimensions": [{"label": "功能效率"}, {"label": "情绪氛围"}],
    }


def test_requirements_unified_review_approve_payload_and_route(monkeypatch):
    captured = {}

    def _fake_interrupt(payload):
        captured["payload"] = payload
        return {"action": "approve"}

    monkeypatch.setattr(rur, "interrupt", _fake_interrupt)

    cmd = rur.RequirementsUnifiedReviewNode.execute(_base_state())

    assert cmd.goto == "project_director"
    assert cmd.update["requirements_unified_review_status"] == "approved"
    assert cmd.update["role_selection_approved"] is True
    assert cmd.update["task_assignment_approved"] is True

    payload = captured["payload"]
    assert payload["interaction_type"] == "role_and_task_unified_review"
    assert "role_selection" in payload
    assert "task_assignment" in payload
    assert payload["close_previous_modal"] is True


def test_requirements_unified_review_modify_tasks_should_forward_request(monkeypatch):
    monkeypatch.setattr(
        rur,
        "interrupt",
        lambda _payload: {
            "action": "modify_tasks",
            "modifications": {"REQ-UNIFIED": ["重排任务A", "重排任务B"]},
            "note": "任务粒度需要更细",
        },
    )

    cmd = rur.RequirementsUnifiedReviewNode.execute(_base_state())

    assert cmd.goto == "project_director"
    assert cmd.update["requirements_unified_review_status"] == "approved"
    assert cmd.update["task_modification_request"] == {"REQ-UNIFIED": ["重排任务A", "重排任务B"]}
    assert "任务" in cmd.update["retry_reason"]


def test_requirements_unified_review_reject_should_back_to_requirements_analyst(monkeypatch):
    monkeypatch.setattr(
        rur,
        "interrupt",
        lambda _payload: {"action": "reject", "reason": "交付物边界不清晰"},
    )

    cmd = rur.RequirementsUnifiedReviewNode.execute(_base_state())

    assert cmd.goto == "requirements_analyst"
    assert cmd.update["requirements_unified_review_status"] == "rejected"
    assert cmd.update["requirements_confirmed"] is False
    assert "统一审核反馈" in cmd.update["user_input"]
