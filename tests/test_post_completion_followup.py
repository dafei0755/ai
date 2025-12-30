"""Tests for post-completion follow-up routing logic."""

from langgraph.graph import END

from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow
from intelligent_project_analyzer.core.state import StateManager


def _make_state():
    """Helper to produce a baseline workflow state."""
    return StateManager.create_initial_state("test input", "session-123")


def test_pdf_generator_routes_to_end_when_enabled():
    workflow = MainWorkflow()
    state = _make_state()

    route = workflow._route_after_pdf_generator(state)

    # Updated behavior: Workflow ends, frontend handles follow-up
    assert route == END


def test_pdf_generator_respects_followup_completion_flag():
    workflow = MainWorkflow()
    state = _make_state()
    state["post_completion_followup_completed"] = True

    route = workflow._route_after_pdf_generator(state)

    assert route == END


def test_pdf_generator_respects_config_toggle():
    workflow = MainWorkflow(config={"post_completion_followup_enabled": False})
    state = _make_state()

    route = workflow._route_after_pdf_generator(state)

    assert route == END
