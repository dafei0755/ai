"""
性能监控指标 - v7.502
使用简单的内存计数器（无需Prometheus依赖）
"""

import time
from typing import Dict, Any, Optional
from collections import defaultdict
from loguru import logger


class MetricsCollector:
    """简单的内存指标收集器"""

    def __init__(self):
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self.histograms = defaultdict(list)
        self.timers = {}

    def increment_counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None):
        """增加计数器"""
        key = self._make_key(name, labels)
        self.counters[key] += value

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """设置仪表值"""
        key = self._make_key(name, labels)
        self.gauges[key] = value

    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """记录直方图值"""
        key = self._make_key(name, labels)
        self.histograms[key].append(value)

    def start_timer(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """开始计时"""
        key = self._make_key(name, labels)
        self.timers[key] = time.time()
        return key

    def stop_timer(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """停止计时并记录"""
        key = self._make_key(name, labels)
        if key not in self.timers:
            logger.warning(f"Timer {key} not started")
            return 0.0

        elapsed = time.time() - self.timers[key]
        del self.timers[key]

        # 记录到直方图
        self.record_histogram(name, elapsed, labels)
        return elapsed

    def _make_key(self, name: str, labels: Optional[Dict[str, str]] = None) -> str:
        """生成指标键"""
        if not labels:
            return name
        label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
        return f"{name}{{{label_str}}}"

    def get_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        summary = {"counters": dict(self.counters), "gauges": dict(self.gauges), "histograms": {}}

        # 计算直方图统计
        for key, values in self.histograms.items():
            if values:
                summary["histograms"][key] = {
                    "count": len(values),
                    "sum": sum(values),
                    "avg": sum(values) / len(values),
                    "min": min(values),
                    "max": max(values),
                }

        return summary

    def reset(self):
        """重置所有指标"""
        self.counters.clear()
        self.gauges.clear()
        self.histograms.clear()
        self.timers.clear()


# 全局指标收集器
_metrics = MetricsCollector()


# ============================================================================
# 性能指标 (Performance Metrics)
# ============================================================================


def analysis_duration(phase: str, mode: str = "default") -> str:
    """
    开始分析计时

    Args:
        phase: 阶段名称 (precheck/phase1/phase2)
        mode: 模式 (parallel/serial)

    Returns:
        计时器键
    """
    return _metrics.start_timer("analysis_duration_seconds", {"phase": phase, "mode": mode})


def record_analysis_duration(phase: str, duration: float, mode: str = "default"):
    """
    记录分析耗时

    Args:
        phase: 阶段名称
        duration: 耗时（秒）
        mode: 模式
    """
    _metrics.record_histogram("analysis_duration_seconds", duration, {"phase": phase, "mode": mode})
    logger.info(f"[Metrics] {phase} completed in {duration:.2f}s (mode={mode})")


# ============================================================================
# 质量指标 (Quality Metrics)
# ============================================================================


def theory_validation_success(count: int = 1):
    """记录理论验证成功"""
    _metrics.increment_counter("theory_validation_success_total", count)


def theory_validation_failure(error_type: str, count: int = 1):
    """
    记录理论验证失败

    Args:
        error_type: 错误类型 (InvalidTheory/CategoryMismatch/ValidationError)
        count: 计数
    """
    _metrics.increment_counter("theory_validation_failure_total", count, {"error_type": error_type})
    logger.warning(f"[Metrics] Theory validation failed: {error_type}")


def hallucination_rate(rate: float):
    """
    设置幻觉率

    Args:
        rate: 幻觉率 (0.0-1.0)
    """
    _metrics.set_gauge("theory_hallucination_rate", rate)
    if rate > 0.05:
        logger.warning(f"[Metrics] High hallucination rate detected: {rate:.2%}")


# ============================================================================
# 资源指标 (Resource Metrics)
# ============================================================================


def llm_tokens_used(phase: str, model: str, tokens: int):
    """
    记录LLM Token消耗

    Args:
        phase: 阶段名称
        model: 模型名称
        tokens: Token数量
    """
    _metrics.increment_counter("llm_tokens_used_total", tokens, {"phase": phase, "model": model})


def cache_hit_rate(rate: float):
    """
    设置缓存命中率

    Args:
        rate: 命中率 (0.0-1.0)
    """
    _metrics.set_gauge("semantic_cache_hit_rate", rate)
    logger.info(f"[Metrics] Cache hit rate: {rate:.2%}")


def record_cache_hit(hit: bool):
    """
    记录单次缓存命中/未命中

    Args:
        hit: 是否命中
    """
    if hit:
        _metrics.increment_counter("cache_hits_total")
    else:
        _metrics.increment_counter("cache_misses_total")


# ============================================================================
# 辅助函数
# ============================================================================


def get_metrics_summary() -> Dict[str, Any]:
    """
    获取所有指标摘要

    Returns:
        指标摘要字典
    """
    summary = _metrics.get_summary()

    # 计算派生指标
    cache_hits = summary["counters"].get("cache_hits_total", 0)
    cache_misses = summary["counters"].get("cache_misses_total", 0)
    total_cache_requests = cache_hits + cache_misses

    if total_cache_requests > 0:
        summary["derived"] = {
            "cache_hit_rate": cache_hits / total_cache_requests,
            "total_cache_requests": total_cache_requests,
        }

    # 计算验证成功率
    validation_success = summary["counters"].get("theory_validation_success_total", 0)
    validation_failure_keys = [k for k in summary["counters"].keys() if "theory_validation_failure_total" in k]
    validation_failures = sum(summary["counters"][k] for k in validation_failure_keys)
    total_validations = validation_success + validation_failures

    if total_validations > 0:
        if "derived" not in summary:
            summary["derived"] = {}
        summary["derived"]["validation_success_rate"] = validation_success / total_validations
        summary["derived"]["total_validations"] = total_validations

    return summary


def reset_metrics():
    """重置所有指标（用于测试）"""
    _metrics.reset()
    logger.info("[Metrics] All metrics reset")


# ============================================================================
# 上下文管理器
# ============================================================================


class TimerContext:
    """计时上下文管理器"""

    def __init__(self, name: str, labels: Optional[Dict[str, str]] = None):
        self.name = name
        self.labels = labels
        self.start_time = None
        self.elapsed = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.elapsed = time.time() - self.start_time
        _metrics.record_histogram(self.name, self.elapsed, self.labels)

        # 如果有异常，记录失败
        if exc_type is not None:
            logger.error(f"[Metrics] {self.name} failed after {self.elapsed:.2f}s: {exc_val}")
        else:
            logger.debug(f"[Metrics] {self.name} completed in {self.elapsed:.2f}s")

        return False  # 不抑制异常


def timer(name: str, **labels):
    """
    创建计时上下文管理器

    Usage:
        with timer("phase1_analysis", mode="parallel"):
            # 执行分析
            pass
    """
    return TimerContext(name, labels)
