"""
节点追踪装饰器 - 自动更新 active_steps

用于 v8.2 动态步骤条功能，自动追踪工作流节点执行状态
"""
import asyncio
import functools
import inspect
from typing import Any, Callable, Dict

from loguru import logger


def track_active_step(step_id: str):
    """
    装饰器：自动将节点添加到 active_steps 列表

    支持同步和异步函数，自动检测函数类型。
    支持类方法和独立函数，自动检测参数签名。
    支持返回 dict 或 Command 类型。

    用法：
        # 类方法
        @track_active_step("requirements_analyst")
        def _requirements_analyst_node(self, state: ProjectAnalysisState):
            return result

        # 独立函数
        @track_active_step("output_intent_detection")
        def output_intent_detection_node(state: dict, store=None) -> Command:
            return Command(goto="next_node")

    Args:
        step_id: 节点ID，用于前端步骤条显示

    Returns:
        装饰后的函数
    """

    def decorator(func: Callable) -> Callable:
        # 检测函数签名
        sig = inspect.signature(func)
        params = list(sig.parameters.keys())
        has_self = len(params) > 0 and params[0] == "self"

        # 检测函数是否为异步
        is_async = asyncio.iscoroutinefunction(func)

        if is_async:
            # 异步包装器
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # 提取 state 参数
                if has_self:
                    state = args[1] if len(args) > 1 else kwargs.get("state", {})
                else:
                    state = args[0] if len(args) > 0 else kwargs.get("state", {})

                # 获取当前 active_steps 列表
                current_steps = state.get("active_steps") or []

                # 添加当前步骤（去重）
                if step_id not in current_steps:
                    current_steps = current_steps + [step_id]
                    logger.debug(f"✨ [NodeTracker] 添加异步步骤: {step_id}")

                # 执行原始节点函数
                result = await func(*args, **kwargs)

                # 更新 active_steps
                result = _update_active_steps(result, current_steps, step_id)

                return result

            return async_wrapper
        else:
            # 同步包装器
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # 提取 state 参数
                if has_self:
                    state = args[1] if len(args) > 1 else kwargs.get("state", {})
                else:
                    state = args[0] if len(args) > 0 else kwargs.get("state", {})

                # 获取当前 active_steps 列表
                current_steps = state.get("active_steps") or []

                # 添加当前步骤（去重）
                if step_id not in current_steps:
                    current_steps = current_steps + [step_id]
                    logger.debug(f"✨ [NodeTracker] 添加同步步骤: {step_id}")

                # 执行原始节点函数
                result = func(*args, **kwargs)

                # 更新 active_steps
                result = _update_active_steps(result, current_steps, step_id)

                return result

            return sync_wrapper

    return decorator


def _update_active_steps(result: Any, current_steps: list, step_id: str) -> Any:
    """
    更新结果中的 active_steps 字段

    支持 dict 和 Command 类型
    """
    if isinstance(result, dict):
        # 直接修改字典
        result["active_steps"] = current_steps
        return result

    # 检查是否为 Command 类型
    if hasattr(result, "update") and hasattr(result, "goto"):
        # LangGraph Command 对象
        from langgraph.types import Command

        if isinstance(result, Command):
            # 创建新的 Command，合并 active_steps 到 update
            update_dict = result.update or {}
            update_dict["active_steps"] = current_steps

            return Command(
                update=update_dict, goto=result.goto, graph=result.graph if hasattr(result, "graph") else None
            )

    # 其他类型，无法更新，只记录日志
    logger.debug(f"⚠️ [NodeTracker] {step_id} 返回不可修改类型: {type(result)}")
    return result


def remove_from_active_steps(step_id: str):
    """
    装饰器：从 active_steps 中移除节点（通常用于完成后清理）

    用法（可选，一般不需要）：
        @remove_from_active_steps("batch_executor")
        async def _after_batch_node(self, state):
            # ...后续逻辑

    Args:
        step_id: 要移除的节点ID
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, state: Dict[str, Any]):
            result = await func(self, state)

            current_steps = state.get("active_steps") or []
            if step_id in current_steps:
                current_steps = [s for s in current_steps if s != step_id]
                logger.debug(f"🗑️ [NodeTracker] 从 active_steps 移除: {step_id}")

                if isinstance(result, dict):
                    result["active_steps"] = current_steps
                else:
                    result = {"active_steps": current_steps}

            return result

        return wrapper

    return decorator
