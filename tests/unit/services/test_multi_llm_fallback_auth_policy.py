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


def test_fallbackllm_auth_401_should_try_next_provider_for_channel_resilience(monkeypatch):
    auth_error = RuntimeError(
        "AuthenticationError: Error code: 401 - {'error': {'message': 'User not found', 'code': 401}}"
    )

    first = _DummyLLM(error=auth_error)
    second = _DummyLLM(error=None)

    llm = FallbackLLM(
        providers=["qwen", "deepseek"],
        max_retries=0,
        llm_instances={"qwen": first, "deepseek": second},
    )

    assert llm.invoke("hello") == {"ok": True}

    assert first.calls == 1
    assert second.calls == 1
