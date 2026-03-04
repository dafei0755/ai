from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import ProgressiveQuestionnaireNode


def _enable_self_skip(monkeypatch):
    monkeypatch.setattr(
        "intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.ENABLE_SMART_NODE_SELF_SKIP",
        True,
    )
    monkeypatch.setattr(
        "intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.ENABLE_SMART_NODE_SELF_SKIP_SHADOW",
        False,
    )


def test_step2_radar_skips_to_summary_for_strategy_intent(monkeypatch):
    _enable_self_skip(monkeypatch)

    state = {
        "task_intent_profile": {
            "intent_type": "strategy_thinking",
            "is_project_bound": False,
        },
        "routing_scores": {},
    }

    command = ProgressiveQuestionnaireNode.step2_radar(state)

    assert command.goto == "questionnaire_summary"
    assert "step2_radar_skipped" in command.update.get("flow_route_reason_codes", [])


def test_step3_gap_skips_to_radar_in_fastpath_when_radar_still_needed(monkeypatch):
    _enable_self_skip(monkeypatch)

    state = {
        "task_intent_profile": {
            "intent_type": "project_design_task",
            "is_project_bound": True,
            "info_completeness": 0.9,
            "ambiguity": 0.2,
        },
        "routing_scores": {"risk": 0.2},
    }

    command = ProgressiveQuestionnaireNode.step3_gap_filling(state)

    assert command.goto == "progressive_step2_radar"
    assert "step3_gap_skipped" in command.update.get("flow_route_reason_codes", [])


def test_step3_gap_skips_directly_to_summary_for_strategy_intent(monkeypatch):
    _enable_self_skip(monkeypatch)

    state = {
        "task_intent_profile": {
            "intent_type": "strategy_thinking",
            "is_project_bound": False,
        },
        "routing_scores": {},
    }

    command = ProgressiveQuestionnaireNode.step3_gap_filling(state)

    assert command.goto == "questionnaire_summary"
    assert "step3_gap_skipped" in command.update.get("flow_route_reason_codes", [])
