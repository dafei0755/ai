"""
智能搜索策略算法 v7.216

升级搜索策略算法，集成：
- 质量监控反馈
- 自适应策略调整
- SSL容错机制
- 搜索结果质量预测
- 动态权重优化

作者: AI Assistant
创建日期: 2026-01-16
"""

import time
from dataclasses import dataclass
from typing import Any, Dict

from loguru import logger

from intelligent_project_analyzer.agents.search_strategy import SearchStrategyGenerator
from intelligent_project_analyzer.utils.monitoring import global_metrics_collector


@dataclass
class SearchStrategyConfig:
    """搜索策略配置"""

    quality_threshold: float = 0.75  # 质量阈值
    ssl_retry_enabled: bool = True  # SSL重试
    adaptive_weights: bool = True  # 自适应权重
    max_iterations: int = 10  # 最大迭代数
    convergence_threshold: float = 0.85  # 收敛阈值


class IntelligentSearchStrategy:
    """智能搜索策略算法 v7.216"""

    def __init__(self, config: SearchStrategyConfig | None = None):
        self.config = config or SearchStrategyConfig()
        self.base_generator = SearchStrategyGenerator()
        self.metrics_collector = global_metrics_collector

        # v7.216: 动态权重系统
        self.dynamic_weights = {
            "relevance": 0.40,  # 相关性权重
            "timeliness": 0.20,  # 时效性权重
            "credibility": 0.25,  # 可信度权重
            "completeness": 0.15,  # 完整性权重
        }

        # 引擎性能历史
        self.engine_performance = {}

    async def generate_adaptive_strategy(
        self,
        agent_type: str,
        project_task: str,
        character_narrative: str,
        assigned_task: str,
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        生成自适应搜索策略

        Args:
            agent_type: 专家类型
            project_task: 项目任务
            character_narrative: 角色叙述
            assigned_task: 分配任务
            context: 上下文信息（包含历史质量数据等）

        Returns:
            增强的搜索策略
        """
        start_time = time.time()

        try:
            # 1. 基础策略生成
            base_queries = self.base_generator.generate_queries(
                agent_type=agent_type,
                project_task=project_task,
                character_narrative=character_narrative,
                assigned_task=assigned_task,
            )

            # 2. 质量预测和策略优化
            quality_prediction = await self._predict_search_quality(
                queries=base_queries, agent_type=agent_type, context=context
            )

            # 3. 动态权重调整
            adjusted_weights = await self._adjust_dynamic_weights(
                agent_type=agent_type, quality_prediction=quality_prediction, context=context
            )

            # 4. 引擎选择策略
            engine_strategy = await self._select_optimal_engines(
                queries=base_queries, quality_prediction=quality_prediction, context=context
            )

            # 5. SSL容错配置
            ssl_config = self._get_ssl_config(context)

            # 6. 构建增强策略
            enhanced_strategy = {
                "agent_type": agent_type,
                "generation_time": time.time() - start_time,
                # 基础查询
                "base_queries": base_queries,
                # 质量预测
                "quality_prediction": quality_prediction,
                # 动态配置
                "dynamic_weights": adjusted_weights,
                "engine_strategy": engine_strategy,
                "ssl_config": ssl_config,
                # 执行参数
                "execution_params": {
                    "max_results_per_query": self._calculate_max_results(quality_prediction),
                    "timeout_seconds": self._calculate_timeout(engine_strategy),
                    "retry_attempts": self._calculate_retry_attempts(ssl_config),
                    "quality_threshold": self.config.quality_threshold,
                },
                # 监控配置
                "monitoring": {
                    "track_quality": True,
                    "record_ssl_errors": True,
                    "measure_response_time": True,
                    "log_engine_performance": True,
                },
                # 自适应参数
                "adaptive_params": {
                    "enable_query_expansion": quality_prediction["confidence"] < 0.7,
                    "use_fallback_engines": quality_prediction["risk_level"] == "high",
                    "enable_content_extraction": True,
                    "enable_semantic_dedup": True,
                },
            }

            # 7. 记录策略生成指标
            self.metrics_collector.record_search(
                tool="intelligent_strategy",
                operation="generate_strategy",
                execution_time=enhanced_strategy["generation_time"],
                success=True,
                result_count=len(base_queries),
                agent_type=agent_type,
                quality_score=quality_prediction["predicted_score"],
            )

            return enhanced_strategy

        except Exception as e:
            logger.error(f" 智能策略生成失败: {e}")

            # 降级到基础策略
            fallback_strategy = {
                "agent_type": agent_type,
                "generation_time": time.time() - start_time,
                "base_queries": self.base_generator.generate_queries(
                    agent_type, project_task, character_narrative, assigned_task
                ),
                "quality_prediction": {"predicted_score": 0.5, "confidence": 0.3, "risk_level": "high"},
                "dynamic_weights": self.dynamic_weights,
                "engine_strategy": {"primary": ["tavily"], "fallback": ["milvus"]},
                "ssl_config": {"retry_enabled": True, "fallback_enabled": True},
                "execution_params": {
                    "max_results_per_query": 10,
                    "timeout_seconds": 30,
                    "retry_attempts": 3,
                    "quality_threshold": 0.5,
                },
                "is_fallback": True,
                "error": str(e),
            }

            return fallback_strategy

    async def _predict_search_quality(
        self, queries: Dict[str, str], agent_type: str, context: Dict[str, Any] | None
    ) -> Dict[str, Any]:
        """预测搜索质量"""
        try:
            # 获取历史数据
            historical_stats = self.metrics_collector.get_statistics(window_minutes=1440)  # 24小时

            # 计算基础预测分数
            base_score = 0.7  # 默认基准
            confidence = 0.6
            risk_level = "medium"

            # 根据历史成功率调整
            if historical_stats:
                avg_success_rate = sum(stats["success_rate"] for stats in historical_stats.values()) / len(
                    historical_stats
                )

                base_score = avg_success_rate / 100  # 转换为0-1范围
                confidence = min(0.9, base_score + 0.1)

                if avg_success_rate >= 80:
                    risk_level = "low"
                elif avg_success_rate < 50:
                    risk_level = "high"

            # 分析查询复杂度
            query_complexity = self._analyze_query_complexity(queries)
            if query_complexity > 0.7:
                base_score -= 0.1
                risk_level = "high" if base_score < 0.6 else risk_level

            # 考虑专家类型的历史表现
            agent_performance = self._get_agent_performance(agent_type, historical_stats)
            if agent_performance:
                base_score = (base_score + agent_performance["success_rate"] / 100) / 2

            return {
                "predicted_score": max(0.0, min(1.0, base_score)),
                "confidence": confidence,
                "risk_level": risk_level,
                "query_complexity": query_complexity,
                "historical_success_rate": avg_success_rate if historical_stats else 0,
                "factors": {
                    "historical_performance": agent_performance is not None,
                    "query_complexity_high": query_complexity > 0.7,
                    "sufficient_data": len(historical_stats) > 10 if historical_stats else False,
                },
            }

        except Exception as e:
            logger.warning(f"️ 质量预测失败，使用默认值: {e}")
            return {
                "predicted_score": 0.5,
                "confidence": 0.3,
                "risk_level": "high",
                "query_complexity": 0.5,
                "error": str(e),
            }

    def _analyze_query_complexity(self, queries: Dict[str, str]) -> float:
        """分析查询复杂度"""
        total_complexity = 0
        count = 0

        for query in queries.values():
            complexity = 0

            # 长度复杂度
            if len(query) > 100:
                complexity += 0.3
            elif len(query) > 50:
                complexity += 0.1

            # 特殊字符复杂度
            if any(char in query for char in ["(", ")", "[", "]", '"', "'"]):
                complexity += 0.2

            # 多语言复杂度
            if any("\u4e00" <= char <= "\u9fff" for char in query) and any(char.isalpha() for char in query):
                complexity += 0.3

            # 技术术语复杂度
            tech_terms = ["API", "SDK", "framework", "architecture", "algorithm", "implementation"]
            if any(term.lower() in query.lower() for term in tech_terms):
                complexity += 0.2

            total_complexity += min(1.0, complexity)
            count += 1

        return total_complexity / count if count > 0 else 0.5

    def _get_agent_performance(self, agent_type: str, historical_stats: Dict) -> Dict | None:
        """获取特定专家的历史表现"""
        total_calls = 0
        total_success = 0

        for _tool_operation, stats in historical_stats.items():
            # 查找包含agent_type的记录（如果有的话）
            if stats and stats.get("success_count", 0) > 0:
                total_calls += stats["success_count"] + stats["error_count"]
                total_success += stats["success_count"]

        if total_calls > 0:
            return {
                "success_rate": (total_success / total_calls) * 100,
                "total_calls": total_calls,
                "avg_response_time": sum(stats["avg_execution_time"] for stats in historical_stats.values())
                / len(historical_stats),
            }

        return None

    async def _adjust_dynamic_weights(
        self, agent_type: str, quality_prediction: Dict[str, Any], context: Dict[str, Any] | None
    ) -> Dict[str, float]:
        """动态调整权重"""
        weights = self.dynamic_weights.copy()

        # 根据质量预测调整
        if quality_prediction["risk_level"] == "high":
            # 高风险时更注重可信度
            weights["credibility"] += 0.1
            weights["relevance"] -= 0.05
            weights["timeliness"] -= 0.05
        elif quality_prediction["risk_level"] == "low":
            # 低风险时更注重相关性
            weights["relevance"] += 0.1
            weights["credibility"] -= 0.05
            weights["completeness"] -= 0.05

        # 根据专家类型调整
        agent_adjustments = {
            "V2": {"credibility": 0.05, "completeness": 0.05},  # 设计总监更重视质量
            "V4": {"relevance": 0.1, "timeliness": -0.05},  # 研究员更重视相关性
            "V5": {"timeliness": 0.1, "credibility": 0.05},  # 行业专家更重视时效性
            "V6": {"completeness": 0.1, "relevance": -0.05},  # 工程师更重视完整性
        }

        if agent_type in agent_adjustments:
            for weight_key, adjustment in agent_adjustments[agent_type].items():
                weights[weight_key] += adjustment

        # 归一化权重
        total_weight = sum(weights.values())
        normalized_weights = {k: v / total_weight for k, v in weights.items()}

        return normalized_weights

    async def _select_optimal_engines(
        self, queries: Dict[str, str], quality_prediction: Dict[str, Any], context: Dict[str, Any] | None
    ) -> Dict[str, Any]:
        """选择最优搜索引擎组合"""
        # 获取引擎历史表现
        engine_stats = {}
        historical_data = self.metrics_collector.get_statistics(window_minutes=1440)

        for tool_operation, stats in historical_data.items():
            engine_name = tool_operation.split(".")[0]
            if engine_name in ["tavily", "bocha", "serper", "arxiv", "milvus"]:
                engine_stats[engine_name] = {
                    "success_rate": stats["success_rate"],
                    "avg_response_time": stats["avg_execution_time"],
                    "total_calls": stats["success_count"] + stats["error_count"],
                }

        # 根据质量预测选择引擎策略
        if quality_prediction["risk_level"] == "low":
            # 低风险：优先选择快速引擎
            primary_engines = ["bocha", "tavily"]
            fallback_engines = ["milvus"]
        elif quality_prediction["risk_level"] == "high":
            # 高风险：多引擎并行
            primary_engines = ["bocha", "tavily", "milvus"]
            fallback_engines = ["serper"] if "serper" in engine_stats else []
        else:
            # 中等风险：平衡策略
            primary_engines = ["bocha", "tavily"]
            fallback_engines = ["milvus", "serper"] if "serper" in engine_stats else ["milvus"]

        # 根据历史表现排序
        if engine_stats:
            primary_engines.sort(key=lambda x: engine_stats.get(x, {}).get("success_rate", 0), reverse=True)
            fallback_engines.sort(key=lambda x: engine_stats.get(x, {}).get("success_rate", 0), reverse=True)

        return {
            "primary": primary_engines[:2],  # 最多2个主引擎
            "fallback": fallback_engines[:2],  # 最多2个备用引擎
            "parallel": quality_prediction["risk_level"] == "high",
            "engine_stats": engine_stats,
            "selection_reason": f"Based on {quality_prediction['risk_level']} risk level and historical performance",
        }

    def _get_ssl_config(self, context: Dict[str, Any] | None) -> Dict[str, Any]:
        """获取SSL配置"""
        return {
            "retry_enabled": self.config.ssl_retry_enabled,
            "fallback_enabled": True,
            "verify_certificates": True,
            "timeout_seconds": 15,
            "max_retries": 3,
            "exponential_backoff": True,
        }

    def _calculate_max_results(self, quality_prediction: Dict[str, Any]) -> int:
        """根据质量预测计算最大结果数"""
        base_results = 10

        if quality_prediction["risk_level"] == "high":
            return min(20, base_results + 5)  # 高风险时获取更多结果
        elif quality_prediction["risk_level"] == "low":
            return max(5, base_results - 3)  # 低风险时可以减少结果数

        return base_results

    def _calculate_timeout(self, engine_strategy: Dict[str, Any]) -> int:
        """计算超时时间"""
        base_timeout = 30

        # 如果使用多个引擎并行，增加超时时间
        if engine_strategy.get("parallel", False):
            return base_timeout + 15

        return base_timeout

    def _calculate_retry_attempts(self, ssl_config: Dict[str, Any]) -> int:
        """计算重试次数"""
        if ssl_config.get("retry_enabled", False):
            return ssl_config.get("max_retries", 3)
        return 1

    async def update_strategy_performance(self, strategy_id: str, execution_results: Dict[str, Any]) -> None:
        """更新策略性能数据"""
        try:
            # 记录策略执行结果
            success = execution_results.get("success", False)
            execution_time = execution_results.get("execution_time", 0)
            quality_score = execution_results.get("quality_score", 0)

            self.metrics_collector.record_search(
                tool="intelligent_strategy",
                operation="strategy_execution",
                execution_time=execution_time,
                success=success,
                result_count=execution_results.get("result_count", 0),
                strategy_id=strategy_id,
                quality_score=quality_score,
            )

            # 更新引擎性能记录
            engine_results = execution_results.get("engine_results", {})
            for engine, result in engine_results.items():
                if engine not in self.engine_performance:
                    self.engine_performance[engine] = []

                self.engine_performance[engine].append(
                    {
                        "timestamp": time.time(),
                        "success": result.get("success", False),
                        "response_time": result.get("response_time", 0),
                        "quality_score": result.get("quality_score", 0),
                    }
                )

                # 只保留最近100条记录
                self.engine_performance[engine] = self.engine_performance[engine][-100:]

            logger.info(f" 策略性能已更新: {strategy_id}")

        except Exception as e:
            logger.error(f" 更新策略性能失败: {e}")

    def get_strategy_analytics(self) -> Dict[str, Any]:
        """获取策略分析数据"""
        try:
            historical_data = self.metrics_collector.get_statistics(window_minutes=1440)

            analytics = {
                "timestamp": time.time(),
                "total_strategies_generated": 0,
                "success_rate": 0.0,
                "avg_quality_score": 0.0,
                "engine_performance": self.engine_performance,
                "current_weights": self.dynamic_weights,
            }

            # 计算策略统计
            strategy_stats = historical_data.get("intelligent_strategy.generate_strategy", {})
            if strategy_stats:
                analytics.update(
                    {
                        "total_strategies_generated": strategy_stats.get("success_count", 0)
                        + strategy_stats.get("error_count", 0),
                        "success_rate": strategy_stats.get("success_rate", 0.0),
                        "avg_response_time": strategy_stats.get("avg_execution_time", 0.0),
                    }
                )

            return analytics

        except Exception as e:
            logger.error(f" 获取策略分析数据失败: {e}")
            return {"error": str(e)}


# 创建全局智能策略实例
intelligent_search_strategy = IntelligentSearchStrategy()
