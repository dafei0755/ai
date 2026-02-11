"""
监控系统 (v7.119+)

收集和上报性能指标、慢查询、错误统计等监控数据
"""

import os
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, List, Optional

from loguru import logger


class MetricsCollector:
    """指标收集器"""

    def __init__(self):
        self._metrics = defaultdict(list)
        self._lock = Lock()
        self._enable_monitoring = os.getenv("ENABLE_MONITORING", "true").lower() == "true"

        # 慢查询阈值
        self.slow_query_threshold = float(os.getenv("SLOW_QUERY_THRESHOLD", "3.0"))

        # 滑动窗口统计（最近1小时）
        self._recent_metrics = defaultdict(lambda: deque(maxlen=1000))

    def record_search(
        self, tool: str, operation: str, execution_time: float, success: bool, result_count: int = 0, **extra_metrics
    ):
        """
        记录搜索操作指标

        Args:
            tool: 工具名称 ("tavily", "arxiv", "milvus", "bocha")
            operation: 操作类型 ("search", "search_for_deliverable")
            execution_time: 执行时间（秒）
            success: 是否成功
            result_count: 结果数量
            **extra_metrics: 额外指标
        """
        if not self._enable_monitoring:
            return

        metric = {
            "tool": tool,
            "operation": operation,
            "execution_time": execution_time,
            "success": success,
            "result_count": result_count,
            "timestamp": datetime.now().isoformat(),
            **extra_metrics,
        }

        with self._lock:
            # 持久化指标
            self._metrics[f"{tool}.{operation}"].append(metric)

            # 滑动窗口指标
            self._recent_metrics[f"{tool}.{operation}"].append(metric)

        # 检查慢查询
        if execution_time > self.slow_query_threshold:
            self._report_slow_query(tool, operation, execution_time, metric)

    def record_error(self, tool: str, operation: str, error_type: str, error_message: str, **context):
        """
        记录错误

        Args:
            tool: 工具名称
            operation: 操作类型
            error_type: 错误类型
            error_message: 错误信息
            **context: 额外上下文
        """
        if not self._enable_monitoring:
            return

        error_metric = {
            "tool": tool,
            "operation": operation,
            "error_type": error_type,
            "error_message": error_message,
            "timestamp": datetime.now().isoformat(),
            **context,
        }

        with self._lock:
            self._metrics[f"{tool}.errors"].append(error_metric)

    def get_statistics(self, tool: Optional[str] = None, window_minutes: int = 60) -> Dict[str, Any]:
        """
        获取统计信息

        Args:
            tool: 工具名称（None表示所有工具）
            window_minutes: 统计窗口（分钟）

        Returns:
            统计数据
        """
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        stats = {}

        with self._lock:
            for key, metrics in self._metrics.items():
                # 过滤时间窗口
                recent_metrics = [m for m in metrics if datetime.fromisoformat(m["timestamp"]) > cutoff_time]

                if not recent_metrics:
                    continue

                # 按工具过滤
                if tool and not key.startswith(tool):
                    continue

                # 计算统计
                execution_times = [m["execution_time"] for m in recent_metrics if "execution_time" in m]
                successes = [m for m in recent_metrics if m.get("success", False)]

                stats[key] = {
                    "total_requests": len(recent_metrics),
                    "successful_requests": len(successes),
                    "failed_requests": len(recent_metrics) - len(successes),
                    "success_rate": len(successes) / len(recent_metrics) if recent_metrics else 0,
                    "avg_execution_time": sum(execution_times) / len(execution_times) if execution_times else 0,
                    "min_execution_time": min(execution_times) if execution_times else 0,
                    "max_execution_time": max(execution_times) if execution_times else 0,
                    "p95_execution_time": self._calculate_percentile(execution_times, 0.95),
                    "p99_execution_time": self._calculate_percentile(execution_times, 0.99),
                }

        return stats

    def _calculate_percentile(self, values: List[float], percentile: float) -> float:
        """计算百分位数"""
        if not values:
            return 0
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile)
        return sorted_values[min(index, len(sorted_values) - 1)]

    def _report_slow_query(self, tool: str, operation: str, execution_time: float, metric: Dict):
        """上报慢查询"""
        logger.warning(
            f" Slow query detected",
            tool=tool,
            operation=operation,
            execution_time=execution_time,
            threshold=self.slow_query_threshold,
            query=metric.get("query", ""),
            result_count=metric.get("result_count", 0),
        )


class PerformanceMonitor:
    """性能监控器（上下文管理器）"""

    def __init__(self, tool: str, operation: str, metrics_collector: Optional[MetricsCollector] = None, **context):
        """
        Args:
            tool: 工具名称
            operation: 操作名称
            metrics_collector: 指标收集器实例
            **context: 额外上下文
        """
        self.tool = tool
        self.operation = operation
        self.context = context
        self.metrics_collector = metrics_collector or global_metrics_collector
        self.start_time = None
        self.success = False
        self.result_count = 0
        self.extra_metrics = {}

    def __enter__(self):
        """进入监控上下文"""
        self.start_time = time.time()
        logger.debug(f" [Monitor] Starting {self.tool}.{self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """退出监控上下文"""
        execution_time = time.time() - self.start_time

        # 判断是否成功
        self.success = exc_type is None

        # 记录指标
        self.metrics_collector.record_search(
            tool=self.tool,
            operation=self.operation,
            execution_time=execution_time,
            success=self.success,
            result_count=self.result_count,
            **{**self.context, **self.extra_metrics},
        )

        # 记录错误
        if not self.success:
            self.metrics_collector.record_error(
                tool=self.tool,
                operation=self.operation,
                error_type=exc_type.__name__ if exc_type else "Unknown",
                error_message=str(exc_val) if exc_val else "",
                **self.context,
            )

        logger.debug(
            f" [Monitor] Completed {self.tool}.{self.operation}: "
            f"success={self.success}, time={execution_time:.2f}s, results={self.result_count}"
        )

    def set_result_count(self, count: int):
        """设置结果数量"""
        self.result_count = count

    def add_metric(self, key: str, value: Any):
        """添加额外指标"""
        self.extra_metrics[key] = value


class HealthCheck:
    """健康检查"""

    def __init__(self, metrics_collector: Optional[MetricsCollector] = None):
        self.metrics_collector = metrics_collector or global_metrics_collector

    def check_health(self) -> Dict[str, Any]:
        """
        执行健康检查

        Returns:
            健康状态
        """
        stats = self.metrics_collector.get_statistics(window_minutes=5)

        # 计算整体健康状态
        overall_health = "healthy"
        warnings = []
        errors = []

        for tool_op, metrics in stats.items():
            # 检查成功率
            if metrics["success_rate"] < 0.9:  # 90%成功率阈值
                overall_health = "degraded"
                warnings.append(f"{tool_op}: low success rate ({metrics['success_rate']:.1%})")

            if metrics["success_rate"] < 0.5:  # 50%成功率阈值
                overall_health = "unhealthy"
                errors.append(f"{tool_op}: critical success rate ({metrics['success_rate']:.1%})")

            # 检查响应时间
            if metrics["p95_execution_time"] > 10.0:  # 10秒P95阈值
                warnings.append(f"{tool_op}: slow response (P95={metrics['p95_execution_time']:.1f}s)")

        return {
            "status": overall_health,
            "timestamp": datetime.now().isoformat(),
            "warnings": warnings,
            "errors": errors,
            "statistics": stats,
        }


# 全局指标收集器
global_metrics_collector = MetricsCollector()
