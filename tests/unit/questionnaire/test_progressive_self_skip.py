import pytest

from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import ProgressiveQuestionnaireNode


def test_self_skip_strategy_intent_skips_gap_and_radar():
    state = {
        "task_intent_profile": {
            "intent_type": "strategy_thinking",
            "is_project_bound": False,
        },
        "routing_scores": {},
    }

    decision = ProgressiveQuestionnaireNode._build_self_skip_decision(state)

    assert decision["flow_route_name"] == "strategy_light_flow"
    assert decision["decisions"]["should_run_step3_gap"] is False
    assert decision["decisions"]["should_run_step2_radar"] is False
    assert "requirements_insight" in decision["active_steps"]


def test_self_skip_fastpath_skips_gap_when_high_completeness():
    state = {
        "task_intent_profile": {
            "intent_type": "project_design_task",
            "is_project_bound": True,
            "info_completeness": 0.9,
            "ambiguity": 0.2,
            "needs_preference_radar": False,
        },
        "routing_scores": {"risk": 0.2},
    }

    decision = ProgressiveQuestionnaireNode._build_self_skip_decision(state)

    assert decision["flow_route_name"] == "project_fastpath_flow"
    assert decision["decisions"]["should_run_step3_gap"] is False
    assert decision["decisions"]["should_run_step2_radar"] is False


def test_self_skip_default_full_progressive():
    state = {
        "task_intent_profile": {
            "intent_type": "project_design_task",
            "is_project_bound": True,
            "info_completeness": 0.4,
            "ambiguity": 0.7,
        },
        "routing_scores": {"risk": 0.6},
    }

    decision = ProgressiveQuestionnaireNode._build_self_skip_decision(state)

    assert decision["flow_route_name"] == "project_full_progressive_flow"
    assert decision["decisions"]["should_run_step3_gap"] is True
    assert decision["decisions"]["should_run_step2_radar"] is True
