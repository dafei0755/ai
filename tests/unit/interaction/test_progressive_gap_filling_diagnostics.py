import pytest

from intelligent_project_analyzer.interaction.nodes import progressive_questionnaire as pq


pytestmark = [pytest.mark.unit]


class _DummyAnalyzer:
    def analyze(self, *_args, **_kwargs):
        return {
            "completeness_score": 0.4,
            "covered_dimensions": ["目标"],
            "missing_dimensions": ["预算约束"],
            "critical_gaps": [{"dimension": "预算约束", "reason": "缺失", "priority": "high"}],
        }

    def generate_gap_questions(self, **_kwargs):
        return [
            {
                "id": "fallback_q1",
                "question": "预算范围是？",
                "type": "single_choice",
                "options": ["A", "B"],
                "is_required": True,
                "priority": 1,
                "weight": 10,
            }
        ]


class _DummyGenerator:
    def __init__(self):
        self.last_generation_metadata = {
            "generation_source": "fallback_auth_failed",
            "error_code": "LLM_AUTH_401",
            "error_message": "401 User not found",
        }

    def generate_sync(self, **_kwargs):
        return [
            {
                "id": "gap_q1",
                "question": "请补充预算范围",
                "type": "single_choice",
                "options": ["<50万", "50-100万"],
                "is_required": True,
                "priority": 1,
                "weight": 10,
            }
        ]


def test_step3_persists_gap_generation_diagnostics(monkeypatch):
    monkeypatch.setattr(
        "intelligent_project_analyzer.services.task_completeness_analyzer.TaskCompletenessAnalyzer",
        _DummyAnalyzer,
    )
    monkeypatch.setattr(
        "intelligent_project_analyzer.services.llm_gap_question_generator.LLMGapQuestionGenerator",
        _DummyGenerator,
    )
    monkeypatch.setattr(pq, "interrupt", lambda _payload: {"answers": {"gap_q1": "50-100万"}})

    state = {
        "progressive_questionnaire_completed": False,
        "confirmed_core_tasks": [{"id": "t1", "title": "任务1", "description": "描述"}],
        "user_input": "做一个住宅设计",
        "agent_results": {"requirements_analyst": {"structured_data": {}}},
        "active_projections": [],
    }

    cmd = pq.ProgressiveQuestionnaireNode.step3_gap_filling(state)

    assert cmd.goto == "progressive_step2_radar"
    assert cmd.update["gap_filling_generation_source"] == "fallback_auth_failed"
    assert cmd.update["gap_filling_error_code"] == "LLM_AUTH_401"
    assert cmd.update["task_gap_filling_questionnaire"]["generation_source"] == "fallback_auth_failed"
    assert cmd.update["task_gap_filling_questionnaire"]["error_code"] == "LLM_AUTH_401"
