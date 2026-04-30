"""
 P2优化: 请求超时监控装饰器

为关键操作（LLM调用、工具执行、数据库查询）添加超时监控
"""

import functools
import time
from typing import Any, Callable

from loguru import logger

from .error_reporter import report_slow_query, report_timeout


def monitor_timeout(operation_name: str, threshold_ms: float = 5000.0, log_args: bool = False):
    """
     P2优化: 超时监控装饰器

    用法:
        @monitor_timeout("LLM调用", threshold_ms=10000)
        async def call_llm(...):
            ...

    Args:
        operation_name: 操作名称
        threshold_ms: 超时阈值（毫秒）
        log_args: 是否记录函数参数
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                # 超时告警
                if duration_ms > threshold_ms:
                    details = {"function": func.__name__, "module": func.__module__}

                    if log_args:
                        details["args"] = str(args[:2]) if args else None  # 只记录前2个参数
                        details["kwargs_keys"] = list(kwargs.keys())

                    # 提取session_id（如果有）
                    session_id = kwargs.get("session_id") or (args[0] if args and isinstance(args[0], str) else None)

                    report_timeout(
                        operation=operation_name,
                        duration_ms=duration_ms,
                        threshold_ms=threshold_ms,
                        session_id=session_id,
                        details=details,
                    )
                else:
                    logger.debug(f" [{operation_name}] 完成: {duration_ms:.2f}ms")

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(f" [{operation_name}] 失败: {e} (耗时: {duration_ms:.2f}ms)")
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                if duration_ms > threshold_ms:
                    details = {"function": func.__name__, "module": func.__module__}

                    if log_args:
                        details["args"] = str(args[:2]) if args else None
                        details["kwargs_keys"] = list(kwargs.keys())

                    session_id = kwargs.get("session_id") or (args[0] if args and isinstance(args[0], str) else None)

                    report_timeout(
                        operation=operation_name,
                        duration_ms=duration_ms,
                        threshold_ms=threshold_ms,
                        session_id=session_id,
                        details=details,
                    )
                else:
                    logger.debug(f" [{operation_name}] 完成: {duration_ms:.2f}ms")

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(f" [{operation_name}] 失败: {e} (耗时: {duration_ms:.2f}ms)")
                raise

        # 根据函数类型返回不同的wrapper
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


def monitor_db_query(query_type: str, threshold_ms: float = 1000.0):
    """
     P2优化: 数据库慢查询监控装饰器

    用法:
        @monitor_db_query("Redis读取", threshold_ms=500)
        async def get_data(...):
            ...

    Args:
        query_type: 查询类型
        threshold_ms: 慢查询阈值（毫秒）
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                if duration_ms > threshold_ms:
                    query_details = {
                        "function": func.__name__,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys()),
                    }

                    session_id = kwargs.get("session_id") or (args[0] if args and isinstance(args[0], str) else None)

                    report_slow_query(
                        query_type=query_type,
                        duration_ms=duration_ms,
                        query_details=query_details,
                        session_id=session_id,
                        threshold_ms=threshold_ms,
                    )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(f" [{query_type}] 查询失败: {e} (耗时: {duration_ms:.2f}ms)")
                raise

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                if duration_ms > threshold_ms:
                    query_details = {
                        "function": func.__name__,
                        "args_count": len(args),
                        "kwargs_keys": list(kwargs.keys()),
                    }

                    session_id = kwargs.get("session_id") or (args[0] if args and isinstance(args[0], str) else None)

                    report_slow_query(
                        query_type=query_type,
                        duration_ms=duration_ms,
                        query_details=query_details,
                        session_id=session_id,
                        threshold_ms=threshold_ms,
                    )

                return result

            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(f" [{query_type}] 查询失败: {e} (耗时: {duration_ms:.2f}ms)")
                raise

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# 预设阈值
TIMEOUT_THRESHOLDS = {
    "llm_call": 30000,  # LLM调用: 30秒
    "tool_execution": 15000,  # 工具执行: 15秒
    "pdf_generation": 20000,  # PDF生成: 20秒
    "image_generation": 25000,  # 图片生成: 25秒
    "redis_query": 500,  # Redis查询: 0.5秒
    "db_query": 1000,  # 数据库查询: 1秒
}
