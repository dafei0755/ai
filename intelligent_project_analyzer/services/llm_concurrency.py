"""
LLM 并发控制模块

提供全局 Semaphore，限制同时发出的 LLM HTTP 连接数，防止高负载下限流与超时。

用法：
    from .llm_concurrency import get_llm_semaphore

    async with get_llm_semaphore():
        result = await llm_call(...)

配置：
    环境变量 LLM_GLOBAL_CONCURRENCY（默认 8）控制全局并发上限。

see ADR-002
"""

import asyncio
import os

_semaphore: asyncio.Semaphore | None = None
_active_calls: int = 0


def get_llm_semaphore() -> asyncio.Semaphore:
    """返回全局 LLM 并发 Semaphore（懒加载单例）。

    大小由环境变量 LLM_GLOBAL_CONCURRENCY 控制（默认 8）。
    在首次调用时创建，此后复用同一实例。
    """
    global _semaphore
    if _semaphore is None:
        limit = int(os.getenv("LLM_GLOBAL_CONCURRENCY", "8"))
        _semaphore = asyncio.Semaphore(limit)
    return _semaphore


def increment_active() -> None:
    """当前正在执行的 LLM 调用数 +1（在 acquire semaphore 后调用）。"""
    global _active_calls
    _active_calls += 1


def decrement_active() -> None:
    """当前正在执行的 LLM 调用数 -1（在 release semaphore 前调用）。"""
    global _active_calls
    _active_calls = max(0, _active_calls - 1)


def get_llm_stats() -> dict:
    """返回当前 LLM 并发状态（供 /api/metrics/llm 使用）。"""
    limit = int(os.getenv("LLM_GLOBAL_CONCURRENCY", "8"))
    return {
        "llm_active_calls": _active_calls,
        "llm_concurrency_limit": limit,
    }


def reset_semaphore() -> None:
    """重置 Semaphore 和计数器（测试用，生产环境无需调用）。"""
    global _semaphore, _active_calls
    _semaphore = None
    _active_calls = 0
