"""
ST-3 (2026-03-01): 节点 Fallback 守卫装饰器

为无 try/except 保护的节点函数提供统一的异常捕获与 fallback 机制。

关键规则:
- GraphInterrupt 必须重新抛出（LangGraph 交互中断，不能被吞掉）
- asyncio.TimeoutError 被捕获并记录
- 通用 Exception 被捕获并记录
- 返回 fallback dict（含 `errors` 字段供下游检测）

用法::

    from intelligent_project_analyzer.workflow.node_guard import node_guard

    @node_guard(fallback={"errors": []})
    def _my_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        ...

    @node_guard(fallback={"errors": []})
    async def _my_async_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        ...

回滚参考: git tag pre-st2-cleanup
"""
from __future__ import annotations

import asyncio
import functools
import logging
import traceback
from typing import Any, Callable, Dict

logger = logging.getLogger(__name__)

# LangGraph 交互中断异常必须透传，不能被装饰器捕获
try:
    from langgraph.errors import GraphInterrupt as _GraphInterrupt

    _INTERRUPT_EXC: tuple[type[BaseException], ...] = (_GraphInterrupt,)
except ImportError:  # pragma: no cover
    _INTERRUPT_EXC = ()


def node_guard(fallback: Dict[str, Any]) -> Callable:
    """
    节点 Fallback 守卫装饰器工厂。

    捕获节点执行时的非预期异常，返回安全的 fallback 状态字典，
    避免单节点失败导致整个工作流崩溃。

    Args:
        fallback: 发生异常时返回的默认 dict（**必须**含 `errors` 键，值为 list）

    Returns:
        装饰器，兼容 sync / async 节点方法。
    """
    if "errors" not in fallback:
        raise ValueError("node_guard: fallback dict must contain 'errors' key (list)")

    def decorator(fn: Callable) -> Callable:
        if asyncio.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def async_wrapper(self: Any, state: Any, *args: Any, **kwargs: Any) -> Any:
                try:
                    return await fn(self, state, *args, **kwargs)
                except BaseException as exc:
                    _maybe_reraise(exc)
                    _log_node_error(fn.__name__, exc)
                    return _build_fallback(fallback, fn.__name__, exc)

            return async_wrapper
        else:

            @functools.wraps(fn)
            def sync_wrapper(self: Any, state: Any, *args: Any, **kwargs: Any) -> Any:
                try:
                    return fn(self, state, *args, **kwargs)
                except BaseException as exc:
                    _maybe_reraise(exc)
                    _log_node_error(fn.__name__, exc)
                    return _build_fallback(fallback, fn.__name__, exc)

            return sync_wrapper

    return decorator


# ---------------------------------------------------------------------------
# 内部辅助函数
# ---------------------------------------------------------------------------


def _maybe_reraise(exc: BaseException) -> None:
    """如果是 GraphInterrupt（LangGraph 交互中断），必须重新抛出。"""
    # 1. 精确类型匹配（已成功导入 GraphInterrupt）
    if _INTERRUPT_EXC and isinstance(exc, _INTERRUPT_EXC):
        raise exc
    # 2. 名称匹配兜底（导入失败时保险）
    if type(exc).__name__ in {"GraphInterrupt", "NodeInterrupt", "Interrupt"}:
        raise exc


def _log_node_error(node_name: str, exc: BaseException) -> None:
    """记录节点异常到 error 日志。"""
    logger.error(
        "node_guard: node '%s' raised %s: %s\n%s",
        node_name,
        type(exc).__name__,
        exc,
        traceback.format_exc(),
    )


def _build_fallback(
    fallback: Dict[str, Any],
    node_name: str,
    exc: BaseException,
) -> Dict[str, Any]:
    """将异常信息追加到 fallback['errors'] 并返回副本。"""
    result = dict(fallback)
    existing: list = list(result.get("errors", []))
    existing.append(f"[{node_name}] {type(exc).__name__}: {exc}")
    result["errors"] = existing
    return result
