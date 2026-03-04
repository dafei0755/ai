"""
LT-4: Circuit Breaker for LLM providers

每个 LLM 提供商独立跟踪健康状态，自动熔断与恢复：
  CLOSED  ──[5 次失败]──► OPEN
  OPEN    ──[60s 超时]──► HALF_OPEN
  HALF_OPEN ──[2 次成功]──► CLOSED
  HALF_OPEN ──[任何失败]──► OPEN

环境变量配置：
  CB_FAILURE_THRESHOLD     失败次数触发 OPEN（默认 5）
  CB_RECOVERY_TIMEOUT      OPEN → HALF_OPEN 等待秒数（默认 60）
  CB_SUCCESS_THRESHOLD     HALF_OPEN 转 CLOSED 需要的成功次数（默认 2）
"""

from __future__ import annotations

import os
import threading
import time
from enum import Enum
from typing import Callable, Dict, TypeVar

from loguru import logger

T = TypeVar("T")

# ---------------------------------------------------------------------------
# 异常
# ---------------------------------------------------------------------------


class CircuitBreakerOpenError(Exception):
    """熔断器处于 OPEN 状态时抛出，阻止调用"""

    def __init__(self, provider: str, retry_after: float) -> None:
        self.provider = provider
        self.retry_after = retry_after  # 距离 HALF_OPEN 剩余秒数
        super().__init__(f"Circuit breaker OPEN for provider '{provider}'. " f"Retry after {retry_after:.1f}s")


# ---------------------------------------------------------------------------
# 状态枚举
# ---------------------------------------------------------------------------


class CircuitState(Enum):
    CLOSED = "closed"  # 正常，允许调用
    OPEN = "open"  # 熔断，拒绝调用
    HALF_OPEN = "half_open"  # 试探，允许少量调用


# ---------------------------------------------------------------------------
# 核心 Circuit Breaker
# ---------------------------------------------------------------------------


class CircuitBreaker:
    """
    线程安全的 Circuit Breaker。

    Args:
        provider:            提供商名称（仅用于日志）
        failure_threshold:   触发 OPEN 的连续失败次数（默认读 CB_FAILURE_THRESHOLD 环境变量，fallback = 5）
        recovery_timeout:    OPEN → HALF_OPEN 的等待秒数（默认读 CB_RECOVERY_TIMEOUT，fallback = 60）
        success_threshold:   HALF_OPEN → CLOSED 需要的连续成功次数（默认读 CB_SUCCESS_THRESHOLD，fallback = 2）
    """

    def __init__(
        self,
        provider: str,
        failure_threshold: int | None = None,
        recovery_timeout: float | None = None,
        success_threshold: int | None = None,
    ) -> None:
        self.provider = provider

        self.failure_threshold: int = failure_threshold or int(os.getenv("CB_FAILURE_THRESHOLD", "5"))
        self.recovery_timeout: float = recovery_timeout or float(os.getenv("CB_RECOVERY_TIMEOUT", "60"))
        self.success_threshold: int = success_threshold or int(os.getenv("CB_SUCCESS_THRESHOLD", "2"))

        self._state: CircuitState = CircuitState.CLOSED
        self._failure_count: int = 0
        self._success_count: int = 0
        self._opened_at: float = 0.0  # monotonic timestamp when OPEN started
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # 公共属性
    # ------------------------------------------------------------------

    @property
    def state(self) -> CircuitState:
        """返回当前（带超时检查的）状态"""
        with self._lock:
            return self._checked_state()

    def _checked_state(self) -> CircuitState:
        """在持锁状态下检查是否可以从 OPEN → HALF_OPEN；调用者须持锁。"""
        if self._state is CircuitState.OPEN and time.monotonic() - self._opened_at >= self.recovery_timeout:
            logger.info(
                f"[CB:{self.provider}] OPEN → HALF_OPEN " f"(recovery_timeout={self.recovery_timeout}s elapsed)"
            )
            self._state = CircuitState.HALF_OPEN
            self._success_count = 0
        return self._state

    # ------------------------------------------------------------------
    # 核心调用入口
    # ------------------------------------------------------------------

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        通过熔断器调用 `func(*args, **kwargs)`。

        - CLOSED / HALF_OPEN：执行并根据结果更新计数
        - OPEN：直接抛出 CircuitBreakerOpenError（不调用 func）

        Returns:
            func 的返回值

        Raises:
            CircuitBreakerOpenError: 熔断器处于 OPEN 状态
            任何 func 抛出的异常（同时记录失败）
        """
        with self._lock:
            current_state = self._checked_state()

            if current_state is CircuitState.OPEN:
                retry_after = max(
                    0.0,
                    self.recovery_timeout - (time.monotonic() - self._opened_at),
                )
                raise CircuitBreakerOpenError(self.provider, retry_after)

        # 执行调用（锁外，避免长时间持锁）
        try:
            result = func(*args, **kwargs)
        except Exception as exc:
            self._on_failure(exc)
            raise

        self._on_success()
        return result

    # ------------------------------------------------------------------
    # 结果记录
    # ------------------------------------------------------------------

    def _on_success(self) -> None:
        with self._lock:
            if self._state is CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    logger.info(
                        f"[CB:{self.provider}] HALF_OPEN → CLOSED " f"({self._success_count} consecutive successes)"
                    )
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
            elif self._state is CircuitState.CLOSED:
                # 成功时重置失败计数
                self._failure_count = 0

    def _on_failure(self, exc: Exception) -> None:
        with self._lock:
            self._failure_count += 1
            self._success_count = 0  # 在 HALF_OPEN 时任何失败都需重新计数

            if self._state is CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    logger.warning(
                        f"[CB:{self.provider}] CLOSED → OPEN "
                        f"(failures={self._failure_count}/{self.failure_threshold}): {exc}"
                    )
                    self._state = CircuitState.OPEN
                    self._opened_at = time.monotonic()
                else:
                    logger.debug(f"[CB:{self.provider}] failure {self._failure_count}/{self.failure_threshold}: {exc}")
            elif self._state is CircuitState.HALF_OPEN:
                logger.warning(f"[CB:{self.provider}] HALF_OPEN → OPEN (probe failed): {exc}")
                self._state = CircuitState.OPEN
                self._opened_at = time.monotonic()

    # ------------------------------------------------------------------
    # 便捷方法：手动记录（供外部包装器使用）
    # ------------------------------------------------------------------

    def record_success(self) -> None:
        """手动记录一次成功（当 call() 外部包装时使用）"""
        self._on_success()

    def record_failure(self, exc: Exception | None = None) -> None:
        """手动记录一次失败"""
        self._on_failure(exc or Exception("manual failure"))

    # ------------------------------------------------------------------
    # 调试 / 状态快照
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, object]:
        with self._lock:
            state = self._checked_state()
            return {
                "provider": self.provider,
                "state": state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "failure_threshold": self.failure_threshold,
                "success_threshold": self.success_threshold,
                "recovery_timeout": self.recovery_timeout,
                "seconds_until_half_open": (
                    max(0.0, self.recovery_timeout - (time.monotonic() - self._opened_at))
                    if state is CircuitState.OPEN
                    else 0.0
                ),
            }

    def __repr__(self) -> str:  # pragma: no cover
        with self._lock:
            return (
                f"<CircuitBreaker provider={self.provider!r} "
                f"state={self._state.value} "
                f"failures={self._failure_count}>"
            )


# ---------------------------------------------------------------------------
# 全局注册表（每个提供商单例）
# ---------------------------------------------------------------------------

_registry: Dict[str, CircuitBreaker] = {}
_registry_lock = threading.Lock()


def get_breaker(
    provider: str,
    failure_threshold: int | None = None,
    recovery_timeout: float | None = None,
    success_threshold: int | None = None,
) -> CircuitBreaker:
    """
    返回指定提供商的 CircuitBreaker 单例。

    首次调用时创建实例；后续相同 provider 直接返回已有实例（kwargs 不再生效）。
    """
    with _registry_lock:
        if provider not in _registry:
            _registry[provider] = CircuitBreaker(
                provider=provider,
                failure_threshold=failure_threshold,
                recovery_timeout=recovery_timeout,
                success_threshold=success_threshold,
            )
            logger.debug(f"[CB] New CircuitBreaker created for provider='{provider}'")
        return _registry[provider]


def reset_registry() -> None:
    """
    重置全局注册表（仅用于测试）。
    """
    global _registry
    with _registry_lock:
        _registry.clear()
    logger.debug("[CB] Registry reset (test only)")


def all_stats() -> Dict[str, Dict[str, object]]:
    """返回所有已注册 CB 的快照统计（用于监控端点）"""
    with _registry_lock:
        providers = list(_registry.keys())
    return {p: _registry[p].stats() for p in providers}
