from typing import Any

import pytest
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from intelligent_project_analyzer.agents.base import LLMAgent
from intelligent_project_analyzer.core.state import AgentType


class _DummyLLM:
    def __init__(self, error: Exception):
        self.error = error
        self.calls = 0

    def invoke(self, *args: Any, **kwargs: Any):
        self.calls += 1
        raise self.error


class _TestLLMAgent(LLMAgent):
    def __init__(self, llm_model: Any):
        super().__init__(
            agent_type=AgentType.REQUIREMENTS_ANALYST,
            name="test_agent",
            description="test",
            llm_model=llm_model,
            tools=[],
            config={"llm": {"max_tokens": 128, "temperature": 0.1}},
        )

    def execute(self, state, config: RunnableConfig, store=None):  # pragma: no cover - 本测试不关注 execute
        raise NotImplementedError

    def validate_input(self, state) -> bool:  # pragma: no cover - 本测试不关注输入校验
        return True

    def get_task_description(self, state) -> str:  # pragma: no cover - 本测试不关注任务描述
        return "test task"


def test_invoke_llm_auth_401_should_fail_fast_without_retry(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_args, **_kwargs: None)

    auth_error = RuntimeError(
        "AuthenticationError: Error code: 401 - {'error': {'message': 'User not found', 'code': 401}}"
    )
    llm = _DummyLLM(auth_error)
    agent = _TestLLMAgent(llm_model=llm)

    with pytest.raises(RuntimeError):
        agent.invoke_llm([HumanMessage(content="hello")])

    assert llm.calls == 1


def test_invoke_llm_non_auth_error_should_keep_retrying(monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *_args, **_kwargs: None)

    transient_error = RuntimeError("network timeout")
    llm = _DummyLLM(transient_error)
    agent = _TestLLMAgent(llm_model=llm)

    with pytest.raises(RuntimeError):
        agent.invoke_llm([HumanMessage(content="hello")])

    assert llm.calls == 3
