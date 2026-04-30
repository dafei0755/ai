"""LLM 重试策略：认证错误快速失败回归测试。"""

import pytest

from intelligent_project_analyzer.utils.llm_retry import (
    LLMRetryConfig,
    ainvoke_llm_with_retry,
    invoke_llm_with_retry,
)


class _AuthFailLLM:
    def __init__(self):
        self.invoke_calls = 0
        self.ainvoke_calls = 0

    def invoke(self, *_args, **_kwargs):
        self.invoke_calls += 1
        raise Exception("AuthenticationError: 401 User not found")

    async def ainvoke(self, *_args, **_kwargs):
        self.ainvoke_calls += 1
        raise Exception("AuthenticationError: 401 User not found")


def test_invoke_llm_with_retry_auth_401_fail_fast():
    llm = _AuthFailLLM()
    cfg = LLMRetryConfig(max_attempts=3, timeout=None)

    with pytest.raises(RuntimeError, match="LLM_AUTH_401"):
        invoke_llm_with_retry(llm, "ping", config=cfg)

    # 401 认证错误应快速失败，不做多次无效重试
    assert llm.invoke_calls == 1


@pytest.mark.asyncio
async def test_ainvoke_llm_with_retry_auth_401_fail_fast():
    llm = _AuthFailLLM()
    cfg = LLMRetryConfig(max_attempts=3, timeout=None)

    with pytest.raises(RuntimeError, match="LLM_AUTH_401"):
        await ainvoke_llm_with_retry(llm, "ping", config=cfg)

    # 401 认证错误应快速失败，不做多次无效重试
    assert llm.ainvoke_calls == 1
