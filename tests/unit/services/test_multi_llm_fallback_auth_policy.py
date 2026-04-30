from typing import Any

import pytest

from intelligent_project_analyzer.services.multi_llm_factory import FallbackLLM


class _DummyLLM:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.calls = 0

    def invoke(self, *args: Any, **kwargs: Any):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return {"ok": True}


def test_fallbackllm_auth_401_should_fail_fast_without_trying_next_provider(monkeypatch):
    auth_error = RuntimeError(
        "AuthenticationError: Error code: 401 - {'error': {'message': 'User not found', 'code': 401}}"
    )

    first = _DummyLLM(error=auth_error)
    second = _DummyLLM(error=None)

    # 构造对象后覆盖实例映射，避免依赖真实 provider 初始化
    llm = FallbackLLM(providers=["openai"], max_retries=0)
    llm.llm_instances = {"openai": first, "deepseek": second}

    with pytest.raises(RuntimeError, match="LLM_AUTH_401"):
        llm.invoke("hello")

    assert first.calls == 1
    assert second.calls == 0
