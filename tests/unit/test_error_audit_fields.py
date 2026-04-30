from intelligent_project_analyzer.agents.result_aggregator_agent import ResultAggregatorAgentV2
from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow
from intelligent_project_analyzer.security.unified_input_validator_node import UnifiedInputValidatorNode
from intelligent_project_analyzer.security.report_guard_node import ReportGuardNode


class _FakeLLM:
    def invoke(self, *args, **kwargs):
        return None


def test_secondary_validation_should_keep_error_details(monkeypatch):
    workflow = MainWorkflow(llm_model=_FakeLLM())

    def _raise_secondary(*args, **kwargs):
        raise RuntimeError("secondary validator boom")

    monkeypatch.setattr(UnifiedInputValidatorNode, "execute_secondary_validation", _raise_secondary)
    result = workflow._unified_input_validator_secondary_node({"user_input": "test"})

    assert isinstance(result, dict)
    assert result.get("secondary_validation_skipped") is True
    assert result.get("secondary_validation_reason") == "error_occurred"
    assert "secondary_validation_error" in result
    assert isinstance(result["secondary_validation_error"], str)


def test_report_guard_should_keep_error_details(monkeypatch):
    workflow = MainWorkflow(llm_model=_FakeLLM())

    def _raise_report_guard(*args, **kwargs):
        raise RuntimeError("report guard boom")

    monkeypatch.setattr(ReportGuardNode, "execute", _raise_report_guard)
    result = workflow._report_guard_node({"user_input": "test", "final_report": {}})

    assert isinstance(result, dict)
    assert result.get("report_safety_status") == "error_passthrough"
    assert result.get("detail") == "报告审核异常"
    assert "report_guard_error" in result
    assert isinstance(result["report_guard_error"], str)


def test_result_aggregator_v2_should_mark_auth_401_error_category(monkeypatch):
    agent = ResultAggregatorAgentV2(llm_model=_FakeLLM())

    def _raise_auth(_state):
        raise RuntimeError("AuthenticationError: 401 User not found")

    monkeypatch.setattr(agent._graph, "invoke", _raise_auth)
    result = agent.execute({"user_input": "x", "agent_results": {}})

    assert result["structured_data"]["error_category"] == "auth_401"
    assert result["validation"]["error_category"] == "auth_401"


def test_result_aggregator_v2_should_mark_non_auth_error_category(monkeypatch):
    agent = ResultAggregatorAgentV2(llm_model=_FakeLLM())

    def _raise_other(_state):
        raise RuntimeError("network timeout")

    monkeypatch.setattr(agent._graph, "invoke", _raise_other)
    result = agent.execute({"user_input": "x", "agent_results": {}})

    assert result["structured_data"]["error_category"] == "other"
    assert result["validation"]["error_category"] == "other"
