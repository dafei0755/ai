import pytest

from intelligent_project_analyzer.core.state import StateManager
from intelligent_project_analyzer.interaction.nodes.calibration_questionnaire import (
    CalibrationQuestionnaireNode,
)


@pytest.fixture()
def baseline_state():
    state = StateManager.create_initial_state("初始需求", "session-1")
    state["agent_results"]["requirements_analyst"] = {
        "structured_data": {
            "calibration_questionnaire": {
                "introduction": "欢迎参与问卷",
                "questions": [
                    {"id": "Q1", "question": "产品定位偏好", "type": "single_choice"},
                    {"id": "Q2", "question": "设计风格", "type": "multiple_choice"},
                    {"id": "Q3", "question": "补充需求", "type": "open_ended"},
                ],
            }
        }
    }
    return state


def test_questionnaire_summary_integration(monkeypatch, baseline_state):
    responses_payload = {
        "answers": [
            {"question_id": "Q1", "answer": "移动优先"},
            {"question_id": "Q2", "answers": ["深色", "极简"]},
            {"question_id": "Q3", "response": "请优先完成 MVP"},
        ],
        "additional_info": "请强调品牌调性",
    }

    monkeypatch.setattr(
        "intelligent_project_analyzer.interaction.nodes.calibration_questionnaire.interrupt",
        lambda payload: responses_payload,
    )

    intent_result = {
        "intent": "approve",
        "method": "mock",
        "content": "",
        "additional_info": "",
        "answers": None,
        "modifications": "",
    }

    monkeypatch.setattr(
        "intelligent_project_analyzer.utils.intent_parser.parse_user_intent",
        lambda *args, **kwargs: intent_result,
    )

    command = CalibrationQuestionnaireNode.execute(baseline_state)
    update = command.update

    assert command.goto == "requirements_analyst"
    assert "questionnaire_summary" in update

    summary = update["questionnaire_summary"]
    assert summary["answers"]["Q1"] == "移动优先"
    assert summary["answers"]["Q2"] == ["深色", "极简"]
    assert summary["notes"] == "请强调品牌调性"
    assert summary["timestamp"] == summary["submitted_at"]

    entries = summary["entries"]
    assert entries[2]["value"] == "请优先完成 MVP"

    structured = update["structured_requirements"]["questionnaire_insights"]
    assert structured["insights"]["Q3"] == "请优先完成 MVP"

    assert "【问卷洞察】" in update["user_input"]
    assert update["calibration_processed"] is True
    assert update["questionnaire_responses"]["timestamp"] == summary["timestamp"]


def test_questionnaire_summary_used_by_aggregator():
    from intelligent_project_analyzer.report.result_aggregator import ResultAggregatorAgent

    summary_payload = {
        "entries": [
            {"id": "Q1", "question": "产品定位偏好", "value": "移动优先", "context": "", "type": "single_choice"},
            {"id": "Q2", "question": "设计风格", "value": ["深色", "极简"], "context": "", "type": "multiple_choice"},
        ],
        "answers": {"Q1": "移动优先", "Q2": ["深色", "极简"]},
        "submitted_at": "2024-01-01T00:00:00Z",
        "timestamp": "2024-01-01T00:00:00Z",
        "notes": "请强调品牌",
        "source": "calibration_questionnaire",
    }

    aggregator = ResultAggregatorAgent.__new__(ResultAggregatorAgent)
    aggregator._analyze_questionnaire_insights = lambda responses: f"共{len(responses)}项洞察"

    result = ResultAggregatorAgent._extract_questionnaire_data(
        aggregator,
        calibration_questionnaire={},
        questionnaire_responses=summary_payload,
        questionnaire_summary=summary_payload,
    )

    assert result["responses"][0]["answer"] == "移动优先"
    assert result["responses"][1]["answer"] == "深色、极简"
    assert result["timestamp"] == "2024-01-01T00:00:00Z"
    assert result["notes"] == "请强调品牌"
    assert result["analysis_insights"] == "共2项洞察"
