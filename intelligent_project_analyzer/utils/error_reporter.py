"""
🆕 P2优化: 结构化错误上报工具

提供统一的错误日志格式，便于监控系统聚合和追踪
"""

import json
import traceback
from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger


class StructuredErrorReporter:
    """结构化错误上报器"""

    @staticmethod
    def report_error(
        error: Exception,
        *,
        context: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        severity: str = "error",
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        🆕 P2优化: 上报结构化错误

        Args:
            error: 异常对象
            context: 错误上下文（如"LLM调用"、"PDF生成"）
            session_id: 会话ID
            user_id: 用户ID
            severity: 严重级别 (debug/info/warning/error/critical)
            extra: 额外上下文信息

        Returns:
            结构化错误字典
        """
        error_data = {
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "context": context,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "stack_trace": traceback.format_exc(),
            "session_id": session_id,
            "user_id": user_id,
            "extra": extra or {},
        }

        # 根据严重级别选择日志方法
        log_method = getattr(logger, severity, logger.error)
        log_method(
            f"[{context}] {type(error).__name__}: {error}",
            extra={"structured_error": error_data, "session_id": session_id, "user_id": user_id},
        )

        return error_data

    @staticmethod
    def report_timeout(
        operation: str,
        duration_ms: float,
        threshold_ms: float,
        *,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        🆕 P2优化: 上报超时事件

        Args:
            operation: 操作名称（如"LLM调用"、"工具执行"）
            duration_ms: 实际耗时（毫秒）
            threshold_ms: 超时阈值（毫秒）
            session_id: 会话ID
            user_id: 用户ID
            details: 详细信息

        Returns:
            超时事件字典
        """
        timeout_data = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "timeout_warning",
            "operation": operation,
            "duration_ms": round(duration_ms, 2),
            "threshold_ms": threshold_ms,
            "exceeded_by_ms": round(duration_ms - threshold_ms, 2),
            "session_id": session_id,
            "user_id": user_id,
            "details": details or {},
        }

        logger.warning(
            f"⏱️ [{operation}] 操作超时: {duration_ms:.2f}ms (阈值: {threshold_ms}ms)",
            extra={"timeout_event": timeout_data, "session_id": session_id, "user_id": user_id},
        )

        return timeout_data

    @staticmethod
    def report_slow_query(
        query_type: str,
        duration_ms: float,
        *,
        query_details: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        threshold_ms: float = 1000.0,
    ) -> Dict[str, Any]:
        """
        🆕 P2优化: 上报慢查询

        Args:
            query_type: 查询类型（如"Redis读取"、"数据库查询"）
            duration_ms: 查询耗时（毫秒）
            query_details: 查询详情
            session_id: 会话ID
            threshold_ms: 慢查询阈值（毫秒）

        Returns:
            慢查询事件字典
        """
        if duration_ms < threshold_ms:
            return {}

        slow_query_data = {
            "timestamp": datetime.now().isoformat(),
            "event_type": "slow_query",
            "query_type": query_type,
            "duration_ms": round(duration_ms, 2),
            "threshold_ms": threshold_ms,
            "query_details": query_details or {},
            "session_id": session_id,
        }

        logger.warning(
            f"🐌 [{query_type}] 慢查询检测: {duration_ms:.2f}ms",
            extra={"slow_query": slow_query_data, "session_id": session_id},
        )

        return slow_query_data


# 全局实例
error_reporter = StructuredErrorReporter()


# 便捷函数
def report_error(error: Exception, context: str, **kwargs) -> Dict[str, Any]:
    """便捷错误上报函数"""
    return error_reporter.report_error(error, context=context, **kwargs)


def report_timeout(operation: str, duration_ms: float, threshold_ms: float, **kwargs) -> Dict[str, Any]:
    """便捷超时上报函数"""
    return error_reporter.report_timeout(operation, duration_ms, threshold_ms, **kwargs)


def report_slow_query(query_type: str, duration_ms: float, **kwargs) -> Dict[str, Any]:
    """便捷慢查询上报函数"""
    return error_reporter.report_slow_query(query_type, duration_ms, **kwargs)
