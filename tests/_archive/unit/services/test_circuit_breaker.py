# -*- coding: utf-8 -*-
"""
LT-4: Circuit Breaker 单元测试

覆盖：
- 状态机转换（CLOSED → OPEN → HALF_OPEN → CLOSED）
- 失败阈值触发
- recovery_timeout 超时检测
- success_threshold 恢复
- 熔断时快速失败
- 注册表单例行为
- 环境变量配置覆盖
"""
from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from intelligent_project_analyzer.services.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    CircuitState,
    all_stats,
    get_breaker,
    reset_registry,
)


# ---------------------------------------------------------------------------
# Fixture: 每个测试用独立 CB 实例，不依赖注册表
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def clean_registry():
    """每个测试前后清理全局注册表"""
    reset_registry()
    yield
    reset_registry()


def make_cb(**kwargs) -> CircuitBreaker:
    """工厂：创建默认阈值很小的 CB，方便测试"""
    defaults = dict(
        provider="test-provider",
        failure_threshold=3,
        recovery_timeout=60.0,
        success_threshold=2,
    )
    defaults.update(kwargs)
    return CircuitBreaker(**defaults)


# ---------------------------------------------------------------------------
# 1. 初始状态
# ---------------------------------------------------------------------------


class TestInitialState:
    def test_initial_state_is_closed(self):
        cb = make_cb()
        assert cb.state is CircuitState.CLOSED

    def test_call_succeeds_in_closed_state(self):
        cb = make_cb()
        result = cb.call(lambda: "ok")
        assert result == "ok"

    def test_failure_count_starts_at_zero(self):
        cb = make_cb()
        assert cb.stats()["failure_count"] == 0


# ---------------------------------------------------------------------------
# 2. CLOSED → OPEN
# ---------------------------------------------------------------------------


class TestClosedToOpen:
    def test_transitions_to_open_after_threshold(self):
        cb = make_cb(failure_threshold=3)
        for _ in range(3):
            with pytest.raises(RuntimeError):
                cb.call(_raise)
        assert cb.state is CircuitState.OPEN

    def test_not_open_before_threshold(self):
        cb = make_cb(failure_threshold=3)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(_raise)
        assert cb.state is CircuitState.CLOSED

    def test_success_resets_failure_count(self):
        cb = make_cb(failure_threshold=3)
        with pytest.raises(RuntimeError):
            cb.call(_raise)
        cb.call(lambda: "ok")  # success resets count
        # Another failure should not yet open
        with pytest.raises(RuntimeError):
            cb.call(_raise)
        assert cb.state is CircuitState.CLOSED
        assert cb.stats()["failure_count"] == 1


# ---------------------------------------------------------------------------
# 3. OPEN 状态阻断调用
# ---------------------------------------------------------------------------


class TestOpenState:
    def _open_cb(self):
        cb = make_cb(failure_threshold=2)
        for _ in range(2):
            with pytest.raises(RuntimeError):
                cb.call(_raise)
        assert cb.state is CircuitState.OPEN
        return cb

    def test_open_raises_circuit_breaker_open_error(self):
        cb = self._open_cb()
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            cb.call(lambda: "won't run")
        assert exc_info.value.provider == "test-provider"

    def test_open_retry_after_is_positive(self):
        cb = self._open_cb()
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            cb.call(lambda: "won't run")
        assert exc_info.value.retry_after >= 0

    def test_function_not_called_when_open(self):
        cb = self._open_cb()
        called = MagicMock()
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(called)
        called.assert_not_called()

    def test_stats_shows_open(self):
        cb = self._open_cb()
        s = cb.stats()
        assert s["state"] == "open"
        assert s["seconds_until_half_open"] > 0


# ---------------------------------------------------------------------------
# 4. OPEN → HALF_OPEN (recovery_timeout 到期)
# ---------------------------------------------------------------------------


class TestOpenToHalfOpen:
    def test_transitions_to_half_open_after_timeout(self):
        cb = make_cb(failure_threshold=1, recovery_timeout=0.05)
        with pytest.raises(RuntimeError):
            cb.call(_raise)
        assert cb.state is CircuitState.OPEN
        time.sleep(0.1)
        # 访问 state 属性触发检查
        assert cb.state is CircuitState.HALF_OPEN

    def test_half_open_allows_calls(self):
        cb = make_cb(failure_threshold=1, recovery_timeout=0.05)
        with pytest.raises(RuntimeError):
            cb.call(_raise)
        time.sleep(0.1)
        result = cb.call(lambda: "probe ok")
        assert result == "probe ok"

    def test_stats_seconds_zero_after_timeout(self):
        cb = make_cb(failure_threshold=1, recovery_timeout=0.05)
        with pytest.raises(RuntimeError):
            cb.call(_raise)
        time.sleep(0.1)
        _ = cb.state  # trigger transition
        s = cb.stats()
        assert s["seconds_until_half_open"] == 0.0


# ---------------------------------------------------------------------------
# 5. HALF_OPEN → CLOSED
# ---------------------------------------------------------------------------


class TestHalfOpenToClosed:
    def _half_open_cb(self):
        cb = make_cb(failure_threshold=1, recovery_timeout=0.05, success_threshold=2)
        with pytest.raises(RuntimeError):
            cb.call(_raise)
        time.sleep(0.1)
        assert cb.state is CircuitState.HALF_OPEN
        return cb

    def test_two_successes_close_circuit(self):
        cb = self._half_open_cb()
        cb.call(lambda: "s1")
        assert cb.state is CircuitState.HALF_OPEN  # still half_open after 1
        cb.call(lambda: "s2")
        assert cb.state is CircuitState.CLOSED

    def test_closed_after_recovery_resets_failure_count(self):
        cb = self._half_open_cb()
        cb.call(lambda: None)
        cb.call(lambda: None)
        assert cb.stats()["failure_count"] == 0


# ---------------------------------------------------------------------------
# 6. HALF_OPEN 失败 → 重新 OPEN
# ---------------------------------------------------------------------------


class TestHalfOpenFailure:
    def test_failure_in_half_open_reopens(self):
        cb = make_cb(failure_threshold=1, recovery_timeout=0.05, success_threshold=2)
        with pytest.raises(RuntimeError):
            cb.call(_raise)
        time.sleep(0.1)
        # probe fails
        with pytest.raises(RuntimeError):
            cb.call(_raise)
        assert cb.state is CircuitState.OPEN

    def test_reopened_blocks_calls(self):
        cb = make_cb(failure_threshold=1, recovery_timeout=0.05, success_threshold=2)
        with pytest.raises(RuntimeError):
            cb.call(_raise)
        time.sleep(0.1)
        with pytest.raises(RuntimeError):
            cb.call(_raise)
        with pytest.raises(CircuitBreakerOpenError):
            cb.call(lambda: "blocked")


# ---------------------------------------------------------------------------
# 7. 注册表单例
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_get_breaker_returns_same_instance(self):
        b1 = get_breaker("openai")
        b2 = get_breaker("openai")
        assert b1 is b2

    def test_different_providers_get_different_instances(self):
        ba = get_breaker("openai")
        bb = get_breaker("deepseek")
        assert ba is not bb

    def test_reset_registry_clears_instances(self):
        b1 = get_breaker("openai")
        reset_registry()
        b2 = get_breaker("openai")
        assert b1 is not b2

    def test_all_stats_returns_all_registered(self):
        get_breaker("openai")
        get_breaker("deepseek")
        stats = all_stats()
        assert "openai" in stats
        assert "deepseek" in stats

    def test_registry_uses_first_config(self):
        """首次创建实例后，后续调用 kwargs 不生效"""
        b1 = get_breaker("qwen", failure_threshold=10)
        b2 = get_breaker("qwen", failure_threshold=99)
        # 两次 get_breaker 得到同一实例，threshold 以首次为准
        assert b1 is b2
        assert b1.failure_threshold == 10


# ---------------------------------------------------------------------------
# 8. 环境变量配置
# ---------------------------------------------------------------------------


class TestEnvConfig:
    def test_reads_failure_threshold_from_env(self, monkeypatch):
        monkeypatch.setenv("CB_FAILURE_THRESHOLD", "7")
        cb = CircuitBreaker(provider="env-test")
        assert cb.failure_threshold == 7

    def test_reads_recovery_timeout_from_env(self, monkeypatch):
        monkeypatch.setenv("CB_RECOVERY_TIMEOUT", "120")
        cb = CircuitBreaker(provider="env-test2")
        assert cb.recovery_timeout == 120.0

    def test_reads_success_threshold_from_env(self, monkeypatch):
        monkeypatch.setenv("CB_SUCCESS_THRESHOLD", "4")
        cb = CircuitBreaker(provider="env-test3")
        assert cb.success_threshold == 4

    def test_explicit_kwargs_override_env(self, monkeypatch):
        monkeypatch.setenv("CB_FAILURE_THRESHOLD", "10")
        cb = CircuitBreaker(provider="override-test", failure_threshold=3)
        assert cb.failure_threshold == 3


# ---------------------------------------------------------------------------
# 9. manual record_success / record_failure
# ---------------------------------------------------------------------------


class TestManualRecord:
    def test_manual_record_failure_triggers_open(self):
        cb = make_cb(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state is CircuitState.OPEN

    def test_manual_record_success_closes_half_open(self):
        cb = make_cb(failure_threshold=1, recovery_timeout=0.05, success_threshold=1)
        cb.record_failure()
        time.sleep(0.1)
        _ = cb.state  # transition to HALF_OPEN
        cb.record_success()
        assert cb.state is CircuitState.CLOSED


# ---------------------------------------------------------------------------
# 10. FallbackLLM 集成（轻量 mock，不调用真实 LLM）
# ---------------------------------------------------------------------------


class TestFallbackLLMIntegration:
    """验证 FallbackLLM.invoke() 在 CB OPEN 时跳过提供商"""

    def test_skips_open_provider_and_uses_fallback(self):
        from intelligent_project_analyzer.services.circuit_breaker import get_breaker

        # 强制 openai 熔断器 OPEN
        cb_openai = get_breaker("openai", failure_threshold=1)
        cb_openai.record_failure()
        assert cb_openai.state is CircuitState.OPEN

        # 把 deepseek 的熔断器保持 CLOSED
        get_breaker("deepseek")  # 注册即可

        # Mock FallbackLLM 的预创建 LLM 实例
        from intelligent_project_analyzer.services.multi_llm_factory import FallbackLLM

        mock_openai_llm = MagicMock()
        mock_deepseek_llm = MagicMock()
        mock_deepseek_llm.invoke.return_value = "deepseek response"

        fb = object.__new__(FallbackLLM)
        fb.llm_instances = {"openai": mock_openai_llm, "deepseek": mock_deepseek_llm}

        result = fb.invoke("hello")

        assert result == "deepseek response"
        mock_openai_llm.invoke.assert_not_called()  # openai 被熔断，未调用
        mock_deepseek_llm.invoke.assert_called_once()


# ---------------------------------------------------------------------------
# 辅助函数
# ---------------------------------------------------------------------------


def _raise(*args, **kwargs):
    raise RuntimeError("simulated LLM failure")
