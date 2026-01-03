"""
日志工具 (v7.119+)

提供敏感信息脱敏、采样日志、结构化日志等功能
"""

import os
import random
import re
from functools import wraps
from typing import Any, Dict, Optional

from loguru import logger


class LogDataSanitizer:
    """日志数据脱敏器"""

    # 敏感字段模式
    SENSITIVE_PATTERNS = {
        "api_key": r"(api[_-]?key|apikey|key)",
        "token": r"(token|access[_-]?token|refresh[_-]?token|bearer)",
        "password": r"(password|passwd|pwd)",
        "secret": r"(secret|client[_-]?secret)",
        "authorization": r"(authorization|auth)",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b\d{3}[-.]?\d{3,4}[-.]?\d{4}\b",
        "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
    }

    @classmethod
    def sanitize(cls, data: Any, deep: bool = True) -> Any:
        """
        脱敏数据

        Args:
            data: 待脱敏的数据（dict, list, str等）
            deep: 是否深度脱敏（递归处理嵌套结构）

        Returns:
            脱敏后的数据
        """
        if isinstance(data, dict):
            return cls._sanitize_dict(data, deep)
        elif isinstance(data, list):
            return cls._sanitize_list(data, deep) if deep else data
        elif isinstance(data, str):
            return cls._sanitize_string(data)
        else:
            return data

    @classmethod
    def _sanitize_dict(cls, data: Dict[str, Any], deep: bool) -> Dict[str, Any]:
        """脱敏字典"""
        sanitized = {}

        for key, value in data.items():
            key_lower = key.lower()

            # 检查键名是否匹配敏感模式
            is_sensitive = False
            for pattern_type, pattern in cls.SENSITIVE_PATTERNS.items():
                if re.search(pattern, key_lower, re.IGNORECASE):
                    is_sensitive = True
                    break

            if is_sensitive:
                # 脱敏敏感字段
                if isinstance(value, str) and len(value) > 8:
                    sanitized[key] = value[:4] + "***" + value[-4:]
                else:
                    sanitized[key] = "***REDACTED***"
            elif deep:
                # 递归处理嵌套结构
                sanitized[key] = cls.sanitize(value, deep=True)
            else:
                sanitized[key] = value

        return sanitized

    @classmethod
    def _sanitize_list(cls, data: list, deep: bool) -> list:
        """脱敏列表"""
        return [cls.sanitize(item, deep=deep) for item in data]

    @classmethod
    def _sanitize_string(cls, data: str) -> str:
        """脱敏字符串中的敏感信息"""
        sanitized = data

        # 脱敏邮箱
        sanitized = re.sub(
            cls.SENSITIVE_PATTERNS["email"],
            lambda m: m.group(0)[:3] + "***@***." + m.group(0).split(".")[-1],
            sanitized,
        )

        # 脱敏电话
        sanitized = re.sub(cls.SENSITIVE_PATTERNS["phone"], "***-***-****", sanitized)

        return sanitized


class SampledLogger:
    """采样日志器"""

    def __init__(self, sample_rate: Optional[float] = None):
        """
        Args:
            sample_rate: 采样率（0.0-1.0），默认从环境变量读取
        """
        if sample_rate is None:
            sample_rate = float(os.getenv("LOG_SAMPLE_RATE", "0.1"))

        self.sample_rate = max(0.0, min(1.0, sample_rate))

    def should_log(self) -> bool:
        """是否应该记录此次日志"""
        return random.random() < self.sample_rate

    def debug(self, message: str, **kwargs):
        """采样DEBUG日志"""
        if self.should_log():
            logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs):
        """采样INFO日志（不推荐对INFO采样）"""
        if self.should_log():
            logger.info(message, **kwargs)


class StructuredLogger:
    """结构化日志器"""

    def __init__(self, component: str):
        """
        Args:
            component: 组件名称（如 "tavily_search", "arxiv_search"）
        """
        self.component = component

    def log(self, level: str, event: str, message: str = "", sanitize_data: bool = True, **extra_data):
        """
        记录结构化日志

        Args:
            level: 日志级别 ("debug", "info", "warning", "error")
            event: 事件名称（如 "search_started", "search_completed"）
            message: 可选的人类可读消息
            sanitize_data: 是否脱敏extra_data
            **extra_data: 额外的结构化数据
        """

        # 脱敏数据
        if sanitize_data:
            extra_data = LogDataSanitizer.sanitize(extra_data, deep=True)

        # 构建结构化上下文
        log_context = logger.bind(component=self.component, event=event, **extra_data)

        # 记录日志
        log_method = getattr(log_context, level.lower(), log_context.info)
        log_method(message or event)

    def search_started(self, tool: str, query: str, **params):
        """搜索开始"""
        self.log("info", "search_started", f"🔍 [{tool}] Starting search", tool=tool, query=query, **params)

    def search_completed(self, tool: str, execution_time: float, result_count: int, **metrics):
        """搜索完成"""
        self.log(
            "info",
            "search_completed",
            f"✅ [{tool}] Search completed in {execution_time:.2f}s",
            tool=tool,
            execution_time=execution_time,
            result_count=result_count,
            **metrics,
        )

    def search_failed(self, tool: str, error: str, query: str = "", **context):
        """搜索失败"""
        self.log(
            "error",
            "search_failed",
            f"❌ [{tool}] Search failed: {error}",
            tool=tool,
            error=error,
            query=query,
            **context,
        )


class ConditionalLogger:
    """条件日志器"""

    def __init__(self):
        self.enable_detailed = os.getenv("ENABLE_DETAILED_LOGGING", "false").lower() == "true"
        self.slow_query_threshold = float(os.getenv("SLOW_QUERY_THRESHOLD", "3.0"))

    def debug_if_enabled(self, message: str, **kwargs):
        """仅在启用详细日志时记录DEBUG"""
        if self.enable_detailed:
            logger.debug(message, **kwargs)

    def warn_if_slow(self, operation: str, execution_time: float, **context):
        """如果操作过慢则记录警告"""
        if execution_time > self.slow_query_threshold:
            logger.warning(
                f"⚠️ Slow operation detected: {operation} took {execution_time:.2f}s (threshold: {self.slow_query_threshold}s)",
                **context,
            )


# 全局实例
sampled_logger = SampledLogger()
conditional_logger = ConditionalLogger()


def log_function_call(sanitize_args: bool = True):
    """
    装饰器：自动记录函数调用

    Args:
        sanitize_args: 是否脱敏参数
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            func_name = f"{func.__module__}.{func.__name__}"

            # 记录开始
            args_repr = repr(args) if not sanitize_args else "***"
            kwargs_repr = repr(LogDataSanitizer.sanitize(kwargs)) if sanitize_args else repr(kwargs)

            logger.debug(f"🔧 Calling {func_name}(args={args_repr}, kwargs={kwargs_repr})")

            try:
                result = func(*args, **kwargs)
                logger.debug(f"✅ {func_name} completed successfully")
                return result
            except Exception as e:
                logger.error(f"❌ {func_name} failed: {str(e)}", exc_info=True)
                raise

        return wrapper

    return decorator
