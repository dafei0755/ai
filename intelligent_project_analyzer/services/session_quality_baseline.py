"""
会话质量评估基线系统 (v7.216)

建立搜索会话质量评估的标准基线，用于：
- 识别低质量会话
- 设定质量阈值
- 进行质量趋势分析
- 提供改进建议

质量评估维度：
1. 信息面提取完整性
2. 搜索结果相关性
3. 内容提取成功率
4. 响应时间性能
5. 用户满意度指标

作者: AI Assistant
创建日期: 2026-01-16
"""

import asyncio
import statistics
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger


class SessionQualityBaseline:
    """会话质量评估基线"""

    # v7.216: 基于深度分析报告的质量标准
    QUALITY_THRESHOLDS = {
        "content_extraction_rate": {
            "excellent": 90.0,  # 优秀：>90%
            "good": 83.3,  # 良好：83.3%（当前基线）
            "acceptable": 70.0,  # 可接受：>70%
            "poor": 50.0,  # 差：>50%
        },
        "information_aspects_count": {
            "excellent": 5,  # 优秀：>=5个信息面
            "good": 3,  # 良好：>=3个信息面
            "acceptable": 1,  # 可接受：>=1个信息面
            "poor": 0,  # 差：0个信息面（需要修复）
        },
        "llm_filter_accuracy": {
            "excellent": 85.0,  # 优秀：>85%
            "good": 75.6,  # 良好：75.6%（当前基线）
            "acceptable": 65.0,  # 可接受：>65%
            "poor": 50.0,  # 差：>50%
        },
        "search_round_completion": {
            "excellent": 10,  # 优秀：完成10轮
            "good": 8,  # 良好：完成8轮
            "acceptable": 6,  # 可接受：完成6轮
            "poor": 3,  # 差：<3轮
        },
        "avg_response_time": {
            "excellent": 8.0,  # 优秀：<8秒
            "good": 12.23,  # 良好：12.23秒（当前基线）
            "acceptable": 20.0,  # 可接受：<20秒
            "poor": 30.0,  # 差：>30秒
        },
    }

    @classmethod
    def evaluate_session_quality(cls, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估单个会话质量

        Args:
            session_data: 会话数据，包含搜索结果、时间等信息

        Returns:
            质量评估结果
        """
        evaluation = {
            "session_id": session_data.get("session_id", "unknown"),
            "evaluation_time": datetime.now().isoformat(),
            "overall_score": 0.0,
            "overall_grade": "poor",
            "dimensions": {},
            "recommendations": [],
            "is_baseline_quality": False,
        }

        # 1. 内容提取成功率评估
        content_score, content_grade = cls._evaluate_content_extraction(session_data)
        evaluation["dimensions"]["content_extraction"] = {
            "score": content_score,
            "grade": content_grade,
            "weight": 0.25,
        }

        # 2. 信息面完整性评估
        aspects_score, aspects_grade = cls._evaluate_information_aspects(session_data)
        evaluation["dimensions"]["information_aspects"] = {
            "score": aspects_score,
            "grade": aspects_grade,
            "weight": 0.30,  # 最高权重，这是当前主要问题
        }

        # 3. LLM过滤准确性评估
        filter_score, filter_grade = cls._evaluate_llm_filtering(session_data)
        evaluation["dimensions"]["llm_filtering"] = {
            "score": filter_score,
            "grade": filter_grade,
            "weight": 0.20,
        }

        # 4. 搜索轮次完成度评估
        rounds_score, rounds_grade = cls._evaluate_search_rounds(session_data)
        evaluation["dimensions"]["search_rounds"] = {
            "score": rounds_score,
            "grade": rounds_grade,
            "weight": 0.15,
        }

        # 5. 响应时间性能评估
        time_score, time_grade = cls._evaluate_response_time(session_data)
        evaluation["dimensions"]["response_time"] = {
            "score": time_score,
            "grade": time_grade,
            "weight": 0.10,
        }

        # 计算加权总分
        total_weighted_score = 0.0
        for dimension, data in evaluation["dimensions"].items():
            total_weighted_score += data["score"] * data["weight"]

        evaluation["overall_score"] = total_weighted_score
        evaluation["overall_grade"] = cls._score_to_grade(total_weighted_score)
        evaluation["is_baseline_quality"] = evaluation["overall_grade"] in ["good", "excellent"]

        # 生成改进建议
        evaluation["recommendations"] = cls._generate_recommendations(evaluation)

        return evaluation

    @classmethod
    def _evaluate_content_extraction(cls, session_data: Dict[str, Any]) -> Tuple[float, str]:
        """评估内容提取成功率"""
        # 模拟计算，实际需要从会话数据中提取
        successful_extractions = session_data.get("successful_extractions", 0)
        total_extractions = session_data.get("total_extractions", 1)

        if total_extractions == 0:
            return 0.0, "poor"

        extraction_rate = (successful_extractions / total_extractions) * 100

        thresholds = cls.QUALITY_THRESHOLDS["content_extraction_rate"]
        if extraction_rate >= thresholds["excellent"]:
            return 100.0, "excellent"
        elif extraction_rate >= thresholds["good"]:
            return 75.0, "good"
        elif extraction_rate >= thresholds["acceptable"]:
            return 50.0, "acceptable"
        else:
            return 25.0, "poor"

    @classmethod
    def _evaluate_information_aspects(cls, session_data: Dict[str, Any]) -> Tuple[float, str]:
        """评估信息面提取完整性"""
        aspects_count = session_data.get("information_aspects_count", 0)

        thresholds = cls.QUALITY_THRESHOLDS["information_aspects_count"]
        if aspects_count >= thresholds["excellent"]:
            return 100.0, "excellent"
        elif aspects_count >= thresholds["good"]:
            return 75.0, "good"
        elif aspects_count >= thresholds["acceptable"]:
            return 50.0, "acceptable"
        else:
            return 0.0, "poor"  # 0个信息面是严重问题

    @classmethod
    def _evaluate_llm_filtering(cls, session_data: Dict[str, Any]) -> Tuple[float, str]:
        """评估LLM过滤准确性"""
        filter_accuracy = session_data.get("llm_filter_accuracy", 0.0)

        thresholds = cls.QUALITY_THRESHOLDS["llm_filter_accuracy"]
        if filter_accuracy >= thresholds["excellent"]:
            return 100.0, "excellent"
        elif filter_accuracy >= thresholds["good"]:
            return 75.0, "good"
        elif filter_accuracy >= thresholds["acceptable"]:
            return 50.0, "acceptable"
        else:
            return 25.0, "poor"

    @classmethod
    def _evaluate_search_rounds(cls, session_data: Dict[str, Any]) -> Tuple[float, str]:
        """评估搜索轮次完成度"""
        completed_rounds = session_data.get("completed_search_rounds", 0)

        thresholds = cls.QUALITY_THRESHOLDS["search_round_completion"]
        if completed_rounds >= thresholds["excellent"]:
            return 100.0, "excellent"
        elif completed_rounds >= thresholds["good"]:
            return 75.0, "good"
        elif completed_rounds >= thresholds["acceptable"]:
            return 50.0, "acceptable"
        else:
            return 25.0, "poor"

    @classmethod
    def _evaluate_response_time(cls, session_data: Dict[str, Any]) -> Tuple[float, str]:
        """评估响应时间性能"""
        avg_response_time = session_data.get("avg_response_time", float("inf"))

        thresholds = cls.QUALITY_THRESHOLDS["avg_response_time"]
        if avg_response_time <= thresholds["excellent"]:
            return 100.0, "excellent"
        elif avg_response_time <= thresholds["good"]:
            return 75.0, "good"
        elif avg_response_time <= thresholds["acceptable"]:
            return 50.0, "acceptable"
        else:
            return 25.0, "poor"

    @classmethod
    def _score_to_grade(cls, score: float) -> str:
        """将分数转换为等级"""
        if score >= 80.0:
            return "excellent"
        elif score >= 65.0:
            return "good"
        elif score >= 45.0:
            return "acceptable"
        else:
            return "poor"

    @classmethod
    def _generate_recommendations(cls, evaluation: Dict[str, Any]) -> List[str]:
        """生成改进建议"""
        recommendations = []

        # 检查各个维度并生成建议
        dimensions = evaluation["dimensions"]

        # 信息面提取问题
        if dimensions["information_aspects"]["grade"] == "poor":
            recommendations.append(" 紧急：信息面提取失败，需要检查LLM输出格式解析")
            recommendations.append(" 建议启用v7.215诊断增强功能，获取详细错误信息")

        # 内容提取问题
        if dimensions["content_extraction"]["grade"] in ["poor", "acceptable"]:
            recommendations.append(" 建议启用SSL容错机制，提高网页提取成功率")
            recommendations.append(" 考虑调整Playwright超时设置")

        # LLM过滤问题
        if dimensions["llm_filtering"]["grade"] in ["poor", "acceptable"]:
            recommendations.append(" 建议优化LLM提示词，提高过滤准确性")
            recommendations.append(" 考虑调整相关性阈值参数")

        # 搜索轮次问题
        if dimensions["search_rounds"]["grade"] in ["poor", "acceptable"]:
            recommendations.append(" 建议检查搜索策略，确保完整执行10轮搜索")
            recommendations.append("️ 检查是否有超时或错误导致搜索中断")

        # 响应时间问题
        if dimensions["response_time"]["grade"] in ["poor", "acceptable"]:
            recommendations.append(" 建议启用缓存机制，减少重复计算")
            recommendations.append(" 考虑优化搜索并发数，提高响应速度")

        return recommendations

    @classmethod
    def calculate_baseline_metrics(cls, sessions_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        计算基线指标

        Args:
            sessions_data: 多个会话的数据列表

        Returns:
            基线指标统计
        """
        if not sessions_data:
            return {"baseline_calculated": False, "error": "没有会话数据"}

        # 收集所有会话的评估结果
        evaluations = [cls.evaluate_session_quality(session) for session in sessions_data]

        # 统计分析
        scores = [eval_result["overall_score"] for eval_result in evaluations]
        grades = [eval_result["overall_grade"] for eval_result in evaluations]

        baseline_metrics = {
            "baseline_calculated": True,
            "calculation_time": datetime.now().isoformat(),
            "sample_size": len(sessions_data),
            # 总体质量统计
            "overall_quality": {
                "mean_score": statistics.mean(scores) if scores else 0.0,
                "median_score": statistics.median(scores) if scores else 0.0,
                "std_deviation": statistics.stdev(scores) if len(scores) > 1 else 0.0,
                "min_score": min(scores) if scores else 0.0,
                "max_score": max(scores) if scores else 0.0,
            },
            # 等级分布
            "grade_distribution": {
                grade: grades.count(grade) / len(grades) * 100 for grade in ["excellent", "good", "acceptable", "poor"]
            },
            # 基线质量会话占比
            "baseline_quality_rate": sum(1 for eval_result in evaluations if eval_result["is_baseline_quality"])
            / len(evaluations)
            * 100,
            # 各维度统计
            "dimension_analysis": {},
            # 推荐改进措施
            "improvement_priorities": [],
        }

        # 分析各个维度
        for dimension in [
            "content_extraction",
            "information_aspects",
            "llm_filtering",
            "search_rounds",
            "response_time",
        ]:
            dimension_scores = [eval_result["dimensions"][dimension]["score"] for eval_result in evaluations]
            dimension_grades = [eval_result["dimensions"][dimension]["grade"] for eval_result in evaluations]

            baseline_metrics["dimension_analysis"][dimension] = {
                "mean_score": statistics.mean(dimension_scores),
                "poor_rate": dimension_grades.count("poor") / len(dimension_grades) * 100,
                "excellent_rate": dimension_grades.count("excellent") / len(dimension_grades) * 100,
            }

        # 生成改进优先级
        poor_rates = {dim: data["poor_rate"] for dim, data in baseline_metrics["dimension_analysis"].items()}
        sorted_issues = sorted(poor_rates.items(), key=lambda x: x[1], reverse=True)

        for dimension, poor_rate in sorted_issues[:3]:  # 取前3个最严重的问题
            if poor_rate > 20:  # 超过20%的会话在该维度表现差
                baseline_metrics["improvement_priorities"].append(
                    {
                        "dimension": dimension,
                        "poor_rate": poor_rate,
                        "priority": "high" if poor_rate > 50 else "medium",
                    }
                )

        return baseline_metrics

    @classmethod
    def is_session_above_baseline(cls, session_data: Dict[str, Any], baseline_metrics: Dict[str, Any]) -> bool:
        """
        判断会话是否达到基线质量

        Args:
            session_data: 会话数据
            baseline_metrics: 基线指标

        Returns:
            是否达到基线质量
        """
        evaluation = cls.evaluate_session_quality(session_data)

        # 简单判断：总分超过基线均值且等级为good或excellent
        baseline_mean = baseline_metrics.get("overall_quality", {}).get("mean_score", 50.0)

        return evaluation["overall_score"] >= baseline_mean and evaluation["overall_grade"] in ["good", "excellent"]


class SessionQualityAnalyzer:
    """会话质量分析器"""

    def __init__(self):
        self.baseline = SessionQualityBaseline()

    def analyze_search_session_quality(self, session_id: str) -> Dict[str, Any]:
        """
        分析特定搜索会话的质量

        Args:
            session_id: 会话ID

        Returns:
            质量分析结果
        """
        session_data = self._get_session_data(session_id)

        if not session_data:
            return {"analysis_completed": False, "error": f"未找到会话 {session_id}"}

        # 进行质量评估
        evaluation = self.baseline.evaluate_session_quality(session_data)

        # 添加详细分析
        analysis = {
            **evaluation,
            "analysis_completed": True,
            "session_metadata": {
                "duration": session_data.get("duration", 0),
                "user_input": session_data.get("user_input", "")[:100] + "...",
                "search_tools_used": session_data.get("search_tools_used", []),
            },
            "quality_insights": self._generate_quality_insights(evaluation),
        }

        return analysis

    def _get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        从 Redis 会话管理器和 MetricsCollector 获取真实会话数据。

        数据来源：
        1. RedisSessionManager: 会话元数据、搜索结果、轮次信息
        2. MetricsCollector: 工具级别的成功率、响应时间统计
        """
        try:
            # 尝试从 Redis 获取真实会话数据
            redis_data = self._fetch_session_from_redis(session_id)
            if redis_data:
                return self._build_quality_data_from_session(session_id, redis_data)

            # Redis 无数据时，从 MetricsCollector 构建近似数据
            metrics_data = self._build_quality_data_from_metrics(session_id)
            if metrics_data:
                return metrics_data

            logger.warning(f"无法获取会话 {session_id} 的质量数据（Redis 和 MetricsCollector 均无数据）")
            return None

        except Exception as e:
            logger.error(f"获取会话数据失败: {session_id}, 错误: {e}")
            return None

    def _fetch_session_from_redis(self, session_id: str) -> Optional[Dict[str, Any]]:
        """从 Redis 同步获取会话数据"""
        try:
            from intelligent_project_analyzer.services.redis_session_manager import get_session_manager

            # 在已有事件循环中运行异步调用
            try:
                asyncio.get_running_loop()
                # 已在异步上下文中，创建 future
                asyncio.ensure_future(get_session_manager())
                # 无法在运行中的循环里同步等待，返回 None 让调用方用异步路径
                # 这种情况下由 search_quality_routes 的异步端点直接传入 session_data
                return None
            except RuntimeError:
                # 没有运行中的事件循环，可以安全使用 asyncio.run
                pass

            async def _fetch():
                manager = await get_session_manager()
                return await manager.get(session_id)

            return asyncio.run(_fetch())

        except Exception as e:
            logger.debug(f"从 Redis 获取会话数据失败: {session_id}, {e}")
            return None

    def _build_quality_data_from_session(self, session_id: str, redis_data: Dict[str, Any]) -> Dict[str, Any]:
        """从 Redis 会话数据中提取质量评估所需的指标"""
        # 搜索结果统计
        all_sources = redis_data.get("all_sources", [])
        search_results = redis_data.get("search_results", [])
        sources = all_sources or search_results

        total_extractions = len(sources)
        successful_extractions = sum(
            1 for s in sources if s.get("content") or s.get("extracted_content") or s.get("snippet")
        )

        # 信息面统计
        information_aspects = redis_data.get("information_aspects", [])
        information_aspects_count = len(information_aspects) if isinstance(information_aspects, list) else 0
        # 也检查 dimensions_found 字段
        if information_aspects_count == 0:
            dimensions_found = redis_data.get("dimensions_found", [])
            if isinstance(dimensions_found, list):
                information_aspects_count = len(dimensions_found)

        # 搜索轮次
        rounds = redis_data.get("rounds", {})
        completed_search_rounds = len(rounds) if isinstance(rounds, dict) else 0
        # 也检查 rounds_completed 字段
        if completed_search_rounds == 0:
            completed_search_rounds = redis_data.get("rounds_completed", 0)

        # 执行时间
        execution_time = redis_data.get("execution_time", 0)
        avg_response_time = execution_time / max(completed_search_rounds, 1)

        # LLM 过滤准确率：从过滤结果中计算
        llm_filter_results = redis_data.get("llm_filter_results", {})
        if llm_filter_results and isinstance(llm_filter_results, dict):
            total_filtered = llm_filter_results.get("total", 0)
            relevant = llm_filter_results.get("relevant", 0)
            llm_filter_accuracy = (relevant / total_filtered * 100) if total_filtered > 0 else 75.0
        else:
            # 从 MetricsCollector 获取近似值
            llm_filter_accuracy = self._get_llm_filter_accuracy_from_metrics()

        # 搜索工具
        search_tools_used = list(
            set(s.get("source_tool", s.get("tool", "unknown")) for s in sources if isinstance(s, dict))
        )

        # 持续时间
        created_at = redis_data.get("created_at", "")
        duration = execution_time
        if not duration and created_at:
            try:
                created = datetime.fromisoformat(created_at)
                duration = (datetime.now() - created).total_seconds()
            except (ValueError, TypeError):
                duration = 0

        return {
            "session_id": session_id,
            "successful_extractions": successful_extractions,
            "total_extractions": max(total_extractions, 1),
            "information_aspects_count": information_aspects_count,
            "llm_filter_accuracy": llm_filter_accuracy,
            "completed_search_rounds": completed_search_rounds,
            "avg_response_time": avg_response_time,
            "duration": duration,
            "user_input": redis_data.get("user_input", redis_data.get("query", "")),
            "search_tools_used": search_tools_used,
        }

    def _build_quality_data_from_metrics(self, session_id: str) -> Optional[Dict[str, Any]]:
        """从 MetricsCollector 全局统计构建近似质量数据"""
        from intelligent_project_analyzer.utils.monitoring import global_metrics_collector

        stats = global_metrics_collector.get_statistics(window_minutes=30)
        if not stats:
            return None

        total_success = 0
        total_calls = 0
        total_response_time = 0
        tools_used = []

        for tool_op, tool_stats in stats.items():
            tool_name = tool_op.split(".")[0] if "." in tool_op else tool_op
            calls = tool_stats.get("total_requests", 0)
            successes = tool_stats.get("successful_requests", 0)

            if calls > 0:
                total_calls += calls
                total_success += successes
                total_response_time += tool_stats.get("avg_execution_time", 0) * calls
                if tool_name not in tools_used:
                    tools_used.append(tool_name)

        if total_calls == 0:
            return None

        avg_response_time = total_response_time / total_calls
        success_rate = total_success / total_calls

        return {
            "session_id": session_id,
            "successful_extractions": total_success,
            "total_extractions": max(total_calls, 1),
            "information_aspects_count": 3 if success_rate > 0.7 else 1,
            "llm_filter_accuracy": success_rate * 100,
            "completed_search_rounds": min(total_calls, 10),
            "avg_response_time": avg_response_time,
            "duration": total_response_time,
            "user_input": f"metrics-based estimate for {session_id}",
            "search_tools_used": tools_used,
        }

    def _get_llm_filter_accuracy_from_metrics(self) -> float:
        """从 MetricsCollector 获取 LLM 过滤准确率的近似值"""
        from intelligent_project_analyzer.utils.monitoring import global_metrics_collector

        stats = global_metrics_collector.get_statistics(window_minutes=30)
        for tool_op, tool_stats in stats.items():
            if "filter" in tool_op or "llm" in tool_op:
                rate = tool_stats.get("success_rate", 0)
                if rate > 0:
                    return rate * 100
        # 无数据时返回保守默认值
        return 70.0

    def _generate_quality_insights(self, evaluation: Dict[str, Any]) -> List[str]:
        """生成质量洞察"""
        insights = []

        overall_grade = evaluation["overall_grade"]
        evaluation["overall_score"]

        # 总体评价
        if overall_grade == "excellent":
            insights.append(" 该会话质量优秀，各项指标均表现良好")
        elif overall_grade == "good":
            insights.append(" 该会话质量良好，达到基线标准")
        elif overall_grade == "acceptable":
            insights.append("️ 该会话质量可接受，但有改进空间")
        else:
            insights.append(" 该会话质量较差，需要重点关注")

        # 关键维度洞察
        dimensions = evaluation["dimensions"]

        # 找出最好和最差的维度
        best_dim = max(dimensions.keys(), key=lambda k: dimensions[k]["score"])
        worst_dim = min(dimensions.keys(), key=lambda k: dimensions[k]["score"])

        insights.append(f" 表现最佳维度：{best_dim}（{dimensions[best_dim]['grade']}）")
        insights.append(f" 需要改进维度：{worst_dim}（{dimensions[worst_dim]['grade']}）")

        # 特定问题洞察
        if dimensions["information_aspects"]["score"] == 0.0:
            insights.append(" 关键问题：信息面提取完全失败，强烈建议启用v7.215诊断功能")

        if dimensions["response_time"]["score"] < 50.0:
            insights.append("️ 性能问题：响应时间过长，建议优化缓存和并发策略")

        return insights


# 创建全局分析器实例
session_quality_analyzer = SessionQualityAnalyzer()
