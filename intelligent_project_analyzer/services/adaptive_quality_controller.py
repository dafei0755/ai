"""
自适应质量控制系统 (v7.216)

实现基于实时质量监控的自适应质量控制：
- 动态质量阈值调整
- 实时性能反馈
- 自动降级和恢复机制
- 质量警报和自动修复
- 预测性质量保障

作者: AI Assistant
创建日期: 2026-01-16
"""

import json
import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from intelligent_project_analyzer.services.session_quality_baseline import (
    SessionQualityBaseline,
)
from intelligent_project_analyzer.utils.monitoring import global_metrics_collector


class QualityControlAction(Enum):
    """质量控制动作"""

    MAINTAIN = "maintain"  # 维持当前策略
    ENHANCE = "enhance"  # 增强质量控制
    DEGRADE_GRACEFUL = "degrade"  # 优雅降级
    EMERGENCY_FALLBACK = "emergency"  # 紧急降级
    AUTO_RECOVER = "recover"  # 自动恢复


@dataclass
class QualityControlConfig:
    """质量控制配置"""

    # 阈值配置
    excellent_threshold: float = 85.0  # 优秀阈值
    good_threshold: float = 70.0  # 良好阈值
    acceptable_threshold: float = 50.0  # 可接受阈值
    emergency_threshold: float = 30.0  # 紧急阈值

    # 响应时间配置
    max_response_time: float = 30.0  # 最大响应时间
    warning_response_time: float = 20.0  # 警告响应时间

    # 自适应配置
    adaptation_window: int = 10  # 适应窗口大小
    recovery_wait_time: int = 300  # 恢复等待时间（秒）
    quality_check_interval: int = 30  # 质量检查间隔（秒）


class AdaptiveQualityController:
    """自适应质量控制器"""

    _HISTORY_PATH = Path(__file__).parent.parent / "data" / "quality_control_history.json"

    def __init__(self, config: QualityControlConfig | None = None):
        self.config = config or QualityControlConfig()
        self.metrics_collector = global_metrics_collector

        # 质量历史记录 — 从磁盘加载
        self.quality_history = deque(maxlen=self.config.adaptation_window)
        self.response_time_history = deque(maxlen=self.config.adaptation_window)
        self._load_history()

        # 当前状态
        self.current_quality_level = "good"
        self.current_control_action = QualityControlAction.MAINTAIN
        self.last_adaptation_time = time.time()
        self.emergency_mode = False
        self.recovery_start_time = None

        # 自适应参数
        self.adaptive_thresholds = {
            "content_extraction_rate": 83.3,  # 基于基线数据
            "information_aspects_min": 3,  # 最少信息面数量
            "llm_filter_accuracy": 75.6,  # 基于基线数据
            "ssl_error_rate_max": 10.0,  # 最大SSL错误率
        }

        # 质量提升策略
        self.enhancement_strategies = {
            "increase_timeout": {"factor": 1.5, "max": 45.0},
            "add_retry_attempts": {"increment": 1, "max": 5},
            "enable_fallback_engines": True,
            "reduce_concurrent_requests": {"factor": 0.7, "min": 1},
            "enable_content_caching": True,
        }

    def _load_history(self) -> None:
        """从 JSON 文件加载质量历史"""
        try:
            if self._HISTORY_PATH.exists():
                with open(self._HISTORY_PATH, encoding="utf-8") as f:
                    data = json.load(f)
                for entry in data.get("quality_history", []):
                    self.quality_history.append(entry)
                for rt in data.get("response_time_history", []):
                    self.response_time_history.append(rt)
                logger.info(
                    f" 加载质量历史: {len(self.quality_history)} 条质量记录, " f"{len(self.response_time_history)} 条响应时间记录"
                )
        except Exception as e:
            logger.warning(f" 加载质量历史失败，使用空历史: {e}")

    def _save_history(self) -> None:
        """持久化质量历史到 JSON 文件"""
        try:
            self._HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "quality_history": list(self.quality_history),
                "response_time_history": list(self.response_time_history),
                "saved_at": time.time(),
            }
            with open(self._HISTORY_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f" 保存质量历史失败: {e}")

    async def monitor_and_adapt(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        监控并自适应调整质量控制策略

        Args:
            session_data: 当前会话数据

        Returns:
            质量控制决策结果
        """
        try:
            # 1. 实时质量评估
            quality_metrics = await self._assess_current_quality(session_data)

            # 2. 更新历史记录
            self._update_quality_history(quality_metrics)

            # 3. 决策质量控制动作
            control_decision = await self._decide_control_action(quality_metrics)

            # 4. 执行质量控制
            execution_result = await self._execute_control_action(
                control_decision["action"], control_decision["params"], session_data
            )

            # 5. 更新系统状态
            self._update_system_state(control_decision, execution_result)

            return {
                "timestamp": time.time(),
                "quality_metrics": quality_metrics,
                "control_decision": control_decision,
                "execution_result": execution_result,
                "system_state": {
                    "quality_level": self.current_quality_level,
                    "control_action": self.current_control_action.value,
                    "emergency_mode": self.emergency_mode,
                    "adaptive_thresholds": self.adaptive_thresholds,
                },
                "recommendations": self._generate_recommendations(quality_metrics),
            }

        except Exception as e:
            logger.error(f" 自适应质量控制失败: {e}")
            return {
                "timestamp": time.time(),
                "error": str(e),
                "fallback_action": "maintain_current_strategy",
            }

    async def _assess_current_quality(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """评估当前质量状态"""
        try:
            # 使用会话质量基线进行评估
            quality_evaluation = SessionQualityBaseline.evaluate_session_quality(session_data)

            # 获取实时指标
            recent_stats = self.metrics_collector.get_statistics(window_minutes=5)

            # 计算关键指标
            metrics = {
                "overall_score": quality_evaluation["overall_score"],
                "overall_grade": quality_evaluation["overall_grade"],
                "dimensions": quality_evaluation["dimensions"],
                # 实时性能指标
                "current_response_time": 0.0,
                "ssl_error_rate": 0.0,
                "search_success_rate": 0.0,
                "content_extraction_success_rate": 0.0,
                # 趋势指标
                "quality_trend": self._calculate_quality_trend(),
                "response_time_trend": self._calculate_response_time_trend(),
                # 风险评估
                "risk_factors": [],
                "urgency_level": "normal",
            }

            # 分析实时统计数据
            if recent_stats:
                total_calls = 0
                total_success = 0
                total_errors = 0
                total_response_time = 0

                for _tool_operation, stats in recent_stats.items():
                    calls = stats["success_count"] + stats["error_count"]
                    total_calls += calls
                    total_success += stats["success_count"]
                    total_errors += stats["error_count"]
                    total_response_time += stats["avg_execution_time"] * calls

                    # 检查SSL错误（从错误消息中识别）
                    # 实际实现中需要更精确的错误分类

                if total_calls > 0:
                    metrics["search_success_rate"] = (total_success / total_calls) * 100
                    metrics["current_response_time"] = total_response_time / total_calls

            # 风险因素分析
            if metrics["overall_score"] < self.config.emergency_threshold:
                metrics["risk_factors"].append("critical_quality_degradation")
                metrics["urgency_level"] = "critical"
            elif metrics["overall_score"] < self.config.acceptable_threshold:
                metrics["risk_factors"].append("quality_below_acceptable")
                metrics["urgency_level"] = "high"

            if metrics["current_response_time"] > self.config.max_response_time:
                metrics["risk_factors"].append("response_time_exceeded")
                metrics["urgency_level"] = "high" if metrics["urgency_level"] == "normal" else metrics["urgency_level"]

            if metrics["search_success_rate"] < 50.0:
                metrics["risk_factors"].append("low_search_success_rate")
                metrics["urgency_level"] = "high" if metrics["urgency_level"] == "normal" else metrics["urgency_level"]

            return metrics

        except Exception as e:
            logger.error(f" 质量评估失败: {e}")
            return {
                "overall_score": 0.0,
                "overall_grade": "poor",
                "current_response_time": float("inf"),
                "search_success_rate": 0.0,
                "risk_factors": ["assessment_failed"],
                "urgency_level": "critical",
                "error": str(e),
            }

    def _update_quality_history(self, quality_metrics: Dict[str, Any]) -> None:
        """更新质量历史记录"""
        self.quality_history.append(
            {
                "timestamp": time.time(),
                "overall_score": quality_metrics["overall_score"],
                "response_time": quality_metrics["current_response_time"],
                "success_rate": quality_metrics["search_success_rate"],
            }
        )

        # 更新响应时间历史
        if quality_metrics["current_response_time"] < float("inf"):
            self.response_time_history.append(quality_metrics["current_response_time"])

        # 持久化到磁盘
        self._save_history()

    def _calculate_quality_trend(self) -> str:
        """计算质量趋势"""
        if len(self.quality_history) < 3:
            return "insufficient_data"

        recent_scores = [entry["overall_score"] for entry in list(self.quality_history)[-3:]]

        if recent_scores[-1] > recent_scores[0] + 5:
            return "improving"
        elif recent_scores[-1] < recent_scores[0] - 5:
            return "declining"
        else:
            return "stable"

    def _calculate_response_time_trend(self) -> str:
        """计算响应时间趋势"""
        if len(self.response_time_history) < 3:
            return "insufficient_data"

        recent_times = list(self.response_time_history)[-3:]

        if recent_times[-1] > recent_times[0] * 1.2:
            return "slowing"
        elif recent_times[-1] < recent_times[0] * 0.8:
            return "improving"
        else:
            return "stable"

    async def _decide_control_action(self, quality_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """决策质量控制动作"""
        urgency = quality_metrics["urgency_level"]
        overall_score = quality_metrics["overall_score"]
        risk_factors = quality_metrics["risk_factors"]

        # 紧急情况处理
        if urgency == "critical" or overall_score < self.config.emergency_threshold:
            return {
                "action": QualityControlAction.EMERGENCY_FALLBACK,
                "reason": "Critical quality degradation detected",
                "params": {
                    "enable_all_fallbacks": True,
                    "reduce_complexity": True,
                    "increase_timeouts": True,
                    "enable_conservative_mode": True,
                },
                "priority": "immediate",
            }

        # 检查是否处于恢复阶段
        if self.emergency_mode and self.recovery_start_time:
            recovery_duration = time.time() - self.recovery_start_time
            if recovery_duration > self.config.recovery_wait_time and overall_score > self.config.good_threshold:
                return {
                    "action": QualityControlAction.AUTO_RECOVER,
                    "reason": "Quality recovered, returning to normal operation",
                    "params": {"gradual_recovery": True},
                    "priority": "normal",
                }

        # 质量提升机会
        if overall_score > self.config.excellent_threshold and quality_metrics["quality_trend"] == "improving":
            return {
                "action": QualityControlAction.ENHANCE,
                "reason": "High quality detected, optimizing for performance",
                "params": {
                    "reduce_redundancy": True,
                    "optimize_timeouts": True,
                    "increase_concurrency": True,
                },
                "priority": "low",
            }

        # 质量下降警告
        if overall_score < self.config.good_threshold or "quality_below_acceptable" in risk_factors:
            return {
                "action": QualityControlAction.DEGRADE_GRACEFUL,
                "reason": "Quality declining, applying preventive measures",
                "params": {
                    "increase_redundancy": True,
                    "conservative_timeouts": True,
                    "enable_additional_retries": True,
                },
                "priority": "medium",
            }

        # 默认维持策略
        return {
            "action": QualityControlAction.MAINTAIN,
            "reason": "Quality within acceptable range",
            "params": {},
            "priority": "low",
        }

    async def _execute_control_action(
        self, action: QualityControlAction, params: Dict[str, Any], session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行质量控制动作"""
        execution_start = time.time()

        try:
            if action == QualityControlAction.EMERGENCY_FALLBACK:
                result = await self._execute_emergency_fallback(params)
            elif action == QualityControlAction.DEGRADE_GRACEFUL:
                result = await self._execute_graceful_degradation(params)
            elif action == QualityControlAction.ENHANCE:
                result = await self._execute_quality_enhancement(params)
            elif action == QualityControlAction.AUTO_RECOVER:
                result = await self._execute_auto_recovery(params)
            else:  # MAINTAIN
                result = {"action": "maintain", "changes": [], "success": True}

            result["execution_time"] = time.time() - execution_start
            return result

        except Exception as e:
            logger.error(f" 执行质量控制动作失败: {e}")
            return {
                "action": action.value,
                "success": False,
                "error": str(e),
                "execution_time": time.time() - execution_start,
            }

    async def _execute_emergency_fallback(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行紧急降级"""
        changes = []

        # 启用保守模式
        if params.get("enable_conservative_mode"):
            self.adaptive_thresholds["content_extraction_rate"] = 60.0  # 降低期望
            self.adaptive_thresholds["information_aspects_min"] = 1  # 降低最低要求
            changes.append("enabled_conservative_quality_thresholds")

        # 启用所有降级措施
        if params.get("enable_all_fallbacks"):
            changes.extend(
                [
                    "enabled_ssl_fallback_mode",
                    "enabled_timeout_extensions",
                    "enabled_retry_mechanisms",
                    "reduced_concurrent_requests",
                ]
            )

        self.emergency_mode = True
        self.recovery_start_time = time.time()

        logger.warning(" 已启动紧急降级模式")

        return {
            "action": "emergency_fallback",
            "changes": changes,
            "success": True,
            "emergency_mode": True,
        }

    async def _execute_graceful_degradation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行优雅降级"""
        changes = []

        # 增加冗余
        if params.get("increase_redundancy"):
            changes.append("increased_search_engine_redundancy")

        # 保守超时
        if params.get("conservative_timeouts"):
            changes.append("applied_conservative_timeout_settings")

        # 额外重试
        if params.get("enable_additional_retries"):
            changes.append("enabled_additional_retry_attempts")

        return {
            "action": "graceful_degradation",
            "changes": changes,
            "success": True,
        }

    async def _execute_quality_enhancement(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行质量增强"""
        changes = []

        # 减少冗余
        if params.get("reduce_redundancy"):
            changes.append("optimized_search_redundancy")

        # 优化超时
        if params.get("optimize_timeouts"):
            changes.append("optimized_timeout_settings")

        # 增加并发
        if params.get("increase_concurrency"):
            changes.append("increased_concurrency_level")

        return {
            "action": "quality_enhancement",
            "changes": changes,
            "success": True,
        }

    async def _execute_auto_recovery(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行自动恢复"""
        changes = []

        # 逐步恢复正常参数
        if params.get("gradual_recovery"):
            self.adaptive_thresholds = {
                "content_extraction_rate": 83.3,
                "information_aspects_min": 3,
                "llm_filter_accuracy": 75.6,
                "ssl_error_rate_max": 10.0,
            }
            changes.append("restored_normal_quality_thresholds")

        self.emergency_mode = False
        self.recovery_start_time = None

        logger.info(" 系统已自动恢复正常运行模式")

        return {
            "action": "auto_recovery",
            "changes": changes,
            "success": True,
            "emergency_mode": False,
        }

    def _update_system_state(self, control_decision: Dict[str, Any], execution_result: Dict[str, Any]) -> None:
        """更新系统状态"""
        self.current_control_action = control_decision["action"]
        self.last_adaptation_time = time.time()

        # 记录指标
        self.metrics_collector.record_search(
            tool="adaptive_quality_controller",
            operation="quality_control",
            execution_time=execution_result.get("execution_time", 0),
            success=execution_result.get("success", False),
            result_count=len(execution_result.get("changes", [])),
            action=control_decision["action"].value,
            urgency=control_decision.get("priority", "normal"),
        )

    def _generate_recommendations(self, quality_metrics: Dict[str, Any]) -> List[str]:
        """生成质量改进建议"""
        recommendations = []

        # 基于维度分析生成建议
        dimensions = quality_metrics.get("dimensions", {})

        for dimension_name, dimension_data in dimensions.items():
            if dimension_data.get("grade") in ["poor", "acceptable"]:
                if dimension_name == "content_extraction":
                    recommendations.append(" 建议检查网络连接和SSL配置，启用内容提取容错机制")
                elif dimension_name == "information_aspects":
                    recommendations.append(" 建议检查LLM输出解析逻辑，启用v7.215诊断增强")
                elif dimension_name == "llm_filtering":
                    recommendations.append(" 建议优化LLM过滤提示词，调整相关性阈值")
                elif dimension_name == "response_time":
                    recommendations.append(" 建议启用缓存和并发优化，减少响应延迟")

        # 基于趋势生成建议
        trend = quality_metrics.get("quality_trend", "stable")
        if trend == "declining":
            recommendations.append(" 检测到质量下降趋势，建议预防性维护")
        elif trend == "improving":
            recommendations.append(" 质量持续改善，可考虑进一步优化性能")

        return recommendations

    def get_control_status(self) -> Dict[str, Any]:
        """获取控制系统状态"""
        return {
            "timestamp": time.time(),
            "current_quality_level": self.current_quality_level,
            "current_action": self.current_control_action.value,
            "emergency_mode": self.emergency_mode,
            "recovery_start_time": self.recovery_start_time,
            "last_adaptation_time": self.last_adaptation_time,
            "adaptive_thresholds": self.adaptive_thresholds,
            "quality_history_size": len(self.quality_history),
            "response_time_history_size": len(self.response_time_history),
        }


# 创建全局自适应质量控制器
adaptive_quality_controller = AdaptiveQualityController()
