"""
全链路追踪上下文 (v7.129)
为每个会话生成trace_id，便于日志追踪
"""

import contextvars
from uuid import uuid4

# Context变量（协程安全）
trace_id_var = contextvars.ContextVar("trace_id", default="no-trace")
session_id_var = contextvars.ContextVar("session_id", default=None)


class TraceContext:
    """全链路追踪上下文"""

    @staticmethod
    def init_trace(session_id: str) -> str:
        """初始化trace"""
        trace_id = f"{session_id[:8]}-{uuid4().hex[:8]}"
        trace_id_var.set(trace_id)
        session_id_var.set(session_id)
        return trace_id

    @staticmethod
    def get_trace_id() -> str:
        """获取当前trace_id"""
        return trace_id_var.get()

    @staticmethod
    def get_session_id() -> str:
        """获取当前session_id"""
        return session_id_var.get()

    @staticmethod
    def clear():
        """清除trace上下文"""
        trace_id_var.set("no-trace")
        session_id_var.set(None)


def trace_filter(record):
    """Loguru过滤器：添加trace_id"""
    record["extra"]["trace_id"] = TraceContext.get_trace_id()
    return True
