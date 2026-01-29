"""
搜索质量监控 API 路由 (v7.216)

提供搜索质量相关的监控指标：
- 搜索成功率
- 内容质量评分
- SSL错误统计
- 搜索引擎性能对比
- 实时质量趋势

作者: AI Assistant
创建日期: 2026-01-16
"""

import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from loguru import logger

from intelligent_project_analyzer.api.auth_middleware import require_admin
from intelligent_project_analyzer.services.adaptive_quality_controller import adaptive_quality_controller
from intelligent_project_analyzer.services.redis_session_manager import get_session_manager
from intelligent_project_analyzer.services.session_quality_baseline import (
    SessionQualityBaseline,
    session_quality_analyzer,
)
from intelligent_project_analyzer.services.user_experience_optimizer import user_experience_optimizer
from intelligent_project_analyzer.utils.monitoring import global_metrics_collector

router = APIRouter()


class SearchQualityMonitor:
    """搜索质量监控器"""

    def __init__(self):
        self.metrics_collector = global_metrics_collector

    async def get_search_quality_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取搜索质量汇总"""
        # 从Redis会话管理器获取搜索会话数据
        session_manager = get_session_manager()

        # 计算时间范围
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)

        # 搜索工具统计
        tools_stats = self.metrics_collector.get_statistics(window_minutes=hours * 60)

        # 构建质量汇总
        summary = {
            "time_range_hours": hours,
            "timestamp": datetime.now().isoformat(),
            # 整体搜索统计
            "overall": {
                "total_searches": 0,
                "success_rate": 0.0,
                "avg_response_time": 0.0,
                "total_errors": 0,
                "ssl_errors": 0,
            },
            # 按搜索引擎分组
            "by_engine": {},
            # 内容质量统计
            "content_quality": {
                "avg_extraction_rate": 0.0,
                "avg_content_length": 0,
                "successful_extractions": 0,
                "failed_extractions": 0,
            },
            # 错误分类
            "error_breakdown": {
                "ssl_errors": 0,
                "timeout_errors": 0,
                "connection_errors": 0,
                "other_errors": 0,
            },
            # 实时趋势（按小时）
            "hourly_trend": [],
        }

        # 处理工具统计
        for tool_operation, stats in tools_stats.items():
            if not stats["success_count"] and not stats["error_count"]:
                continue

            tool_name = tool_operation.split(".")[0] if "." in tool_operation else tool_operation

            if tool_name in ["tavily", "bocha", "serper", "arxiv"]:
                summary["by_engine"][tool_name] = {
                    "total_calls": stats["success_count"] + stats["error_count"],
                    "success_rate": stats["success_rate"],
                    "avg_response_time": stats["avg_execution_time"],
                    "total_results": stats.get("total_results", 0),
                }

                # 累计到总体统计
                summary["overall"]["total_searches"] += stats["success_count"] + stats["error_count"]

        # 计算总体成功率
        if summary["overall"]["total_searches"] > 0:
            total_success = sum(
                engine["total_calls"] * engine["success_rate"] / 100 for engine in summary["by_engine"].values()
            )
            summary["overall"]["success_rate"] = total_success / summary["overall"]["total_searches"] * 100

            # 计算平均响应时间
            total_weighted_time = sum(
                engine["total_calls"] * engine["avg_response_time"] for engine in summary["by_engine"].values()
            )
            summary["overall"]["avg_response_time"] = total_weighted_time / summary["overall"]["total_searches"]

        return summary

    async def get_ssl_error_analysis(self, hours: int = 24) -> Dict[str, Any]:
        """SSL错误分析（v7.216新增）"""
        # 这里会从日志系统或错误记录中获取SSL错误统计
        # 简化实现，实际中需要集成错误日志分析

        return {
            "time_range_hours": hours,
            "ssl_error_stats": {
                "total_ssl_errors": 0,
                "ssl_timeout_errors": 0,
                "certificate_errors": 0,
                "handshake_failures": 0,
                "fallback_successes": 0,  # v7.216: SSL降级成功数
            },
            "affected_domains": [],
            "recovery_rate": 0.0,  # SSL错误后的恢复率
        }

    async def get_content_extraction_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """内容提取质量指标"""
        return {
            "time_range_hours": hours,
            "extraction_stats": {
                "total_extractions": 0,
                "trafilatura_success": 0,
                "playwright_success": 0,
                "extraction_failures": 0,
                "avg_content_length": 0,
                "cache_hit_rate": 0.0,
            },
            "by_method": {
                "trafilatura": {
                    "success_count": 0,
                    "avg_time": 0.0,
                    "avg_content_length": 0,
                },
                "playwright": {
                    "success_count": 0,
                    "avg_time": 0.0,
                    "avg_content_length": 0,
                },
            },
            "problem_domains": [],  # 经常失败的域名
        }

    async def get_search_engine_comparison(self, hours: int = 24) -> Dict[str, Any]:
        """搜索引擎性能对比"""
        tools_stats = self.metrics_collector.get_statistics(window_minutes=hours * 60)

        comparison = {
            "time_range_hours": hours,
            "engines": {},
            "rankings": {
                "by_success_rate": [],
                "by_response_time": [],
                "by_result_quality": [],
            },
        }

        for tool_operation, stats in tools_stats.items():
            tool_name = tool_operation.split(".")[0] if "." in tool_operation else tool_operation

            if tool_name in ["tavily", "bocha", "serper", "arxiv"]:
                comparison["engines"][tool_name] = {
                    "success_rate": stats["success_rate"],
                    "avg_response_time": stats["avg_execution_time"],
                    "total_calls": stats["success_count"] + stats["error_count"],
                    "p95_response_time": stats.get("p95_execution_time", 0),
                    "error_rate": 100 - stats["success_rate"],
                }

        # 生成排名
        if comparison["engines"]:
            # 按成功率排名
            comparison["rankings"]["by_success_rate"] = sorted(
                comparison["engines"].items(), key=lambda x: x[1]["success_rate"], reverse=True
            )

            # 按响应时间排名（越小越好）
            comparison["rankings"]["by_response_time"] = sorted(
                comparison["engines"].items(), key=lambda x: x[1]["avg_response_time"]
            )

        return comparison


# 创建监控器实例
search_quality_monitor = SearchQualityMonitor()


@router.get("/search/quality/summary")
async def get_search_quality_summary(
    hours: int = Query(default=24, ge=1, le=168), admin: dict = Depends(require_admin)
):
    """
    获取搜索质量汇总 (v7.216)

    Args:
        hours: 时间范围（小时）

    Returns:
        搜索质量汇总数据
    """
    try:
        summary = await search_quality_monitor.get_search_quality_summary(hours)
        return summary
    except Exception as e:
        logger.error(f"❌ 获取搜索质量汇总失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/ssl-errors")
async def get_ssl_error_analysis(hours: int = Query(default=24, ge=1, le=168), admin: dict = Depends(require_admin)):
    """
    SSL错误分析 (v7.216新增)

    Args:
        hours: 时间范围（小时）

    Returns:
        SSL错误统计和分析
    """
    try:
        analysis = await search_quality_monitor.get_ssl_error_analysis(hours)
        return analysis
    except Exception as e:
        logger.error(f"❌ 获取SSL错误分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/content-extraction")
async def get_content_extraction_metrics(
    hours: int = Query(default=24, ge=1, le=168), admin: dict = Depends(require_admin)
):
    """
    内容提取质量指标

    Args:
        hours: 时间范围（小时）

    Returns:
        内容提取质量统计
    """
    try:
        metrics = await search_quality_monitor.get_content_extraction_metrics(hours)
        return metrics
    except Exception as e:
        logger.error(f"❌ 获取内容提取指标失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/engine-comparison")
async def get_search_engine_comparison(
    hours: int = Query(default=24, ge=1, le=168), admin: dict = Depends(require_admin)
):
    """
    搜索引擎性能对比

    Args:
        hours: 时间范围（小时）

    Returns:
        搜索引擎性能对比数据
    """
    try:
        comparison = await search_quality_monitor.get_search_engine_comparison(hours)
        return comparison
    except Exception as e:
        logger.error(f"❌ 获取搜索引擎对比失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search/quality/realtime")
async def get_realtime_quality_metrics(admin: dict = Depends(require_admin)):
    """
    实时搜索质量指标 (v7.216)

    Returns:
        最近5分钟的实时质量指标
    """
    try:
        # 获取最近5分钟的统计
        stats = global_metrics_collector.get_statistics(window_minutes=5)

        realtime_data = {
            "timestamp": datetime.now().isoformat(),
            "window_minutes": 5,
            "active_searches": 0,
            "success_rate": 0.0,
            "avg_response_time": 0.0,
            "error_count": 0,
            "ssl_error_count": 0,
            "engines_status": {},
        }

        # 处理统计数据
        for tool_operation, tool_stats in stats.items():
            tool_name = tool_operation.split(".")[0] if "." in tool_operation else tool_operation

            if tool_name in ["tavily", "bocha", "serper", "arxiv"]:
                realtime_data["active_searches"] += tool_stats["success_count"] + tool_stats["error_count"]
                realtime_data["error_count"] += tool_stats["error_count"]

                realtime_data["engines_status"][tool_name] = {
                    "active": tool_stats["success_count"] + tool_stats["error_count"] > 0,
                    "success_rate": tool_stats["success_rate"],
                    "avg_response_time": tool_stats["avg_execution_time"],
                }

        # 计算总体成功率
        if realtime_data["active_searches"] > 0:
            total_success = sum(engine["success_rate"] * 0.01 for engine in realtime_data["engines_status"].values())
            realtime_data["success_rate"] = (total_success / len(realtime_data["engines_status"])) * 100

        return realtime_data

    except Exception as e:
        logger.error(f"❌ 获取实时质量指标失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/quality/{session_id}")
async def analyze_session_quality(session_id: str, admin: dict = Depends(require_admin)):
    """
    分析特定会话质量 (v7.216)

    Args:
        session_id: 会话ID

    Returns:
        会话质量分析结果
    """
    try:
        analysis = session_quality_analyzer.analyze_search_session_quality(session_id)
        return analysis
    except Exception as e:
        logger.error(f"❌ 分析会话质量失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quality/baseline/calculate")
async def calculate_quality_baseline(
    session_ids: List[str] = Body(..., description="会话ID列表"), admin: dict = Depends(require_admin)
):
    """
    计算质量基线 (v7.216)

    Args:
        session_ids: 用于计算基线的会话ID列表

    Returns:
        质量基线计算结果
    """
    try:
        # 收集会话数据
        sessions_data = []
        for session_id in session_ids:
            session_data = session_quality_analyzer._get_session_data(session_id)
            if session_data:
                sessions_data.append(session_data)

        if not sessions_data:
            raise HTTPException(status_code=400, detail="未找到有效的会话数据")

        # 计算基线
        baseline_metrics = SessionQualityBaseline.calculate_baseline_metrics(sessions_data)

        return baseline_metrics

    except Exception as e:
        logger.error(f"❌ 计算质量基线失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quality/thresholds")
async def get_quality_thresholds(admin: dict = Depends(require_admin)):
    """
    获取质量阈值配置 (v7.216)

    Returns:
        当前的质量评估阈值
    """
    try:
        return {
            "thresholds": SessionQualityBaseline.QUALITY_THRESHOLDS,
            "description": {
                "content_extraction_rate": "内容提取成功率 (%)",
                "information_aspects_count": "信息面提取数量",
                "llm_filter_accuracy": "LLM过滤准确率 (%)",
                "search_round_completion": "完成搜索轮次数",
                "avg_response_time": "平均响应时间 (秒)",
            },
            "grades": {
                "excellent": "优秀 (80-100分)",
                "good": "良好 (65-80分)",
                "acceptable": "可接受 (45-65分)",
                "poor": "差 (<45分)",
            },
        }
    except Exception as e:
        logger.error(f"❌ 获取质量阈值失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quality/adaptive-control")
async def trigger_adaptive_control(
    session_id: str = Body(..., description="会话ID"), admin: dict = Depends(require_admin)
):
    """
    触发自适应质量控制 (v7.216)

    Args:
        session_id: 要分析的会话ID

    Returns:
        自适应质量控制结果
    """
    try:
        # 获取会话数据
        session_manager = get_session_manager()
        session_data = await session_manager.get_session_history(session_id)

        if not session_data:
            raise HTTPException(status_code=404, detail="会话未找到")

        # 执行自适应质量控制
        control_result = await adaptive_quality_controller.monitor_and_adapt(session_data)

        return {
            "session_id": session_id,
            "timestamp": control_result["timestamp"],
            "quality_metrics": control_result["quality_metrics"],
            "control_decision": control_result["control_decision"],
            "execution_result": control_result["execution_result"],
            "system_state": control_result["system_state"],
            "recommendations": control_result["recommendations"],
            "success": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 自适应质量控制失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quality/control-status")
async def get_quality_control_status(admin: dict = Depends(require_admin)):
    """
    获取质量控制系统状态 (v7.216)

    Returns:
        当前质量控制系统的状态信息
    """
    try:
        control_status = adaptive_quality_controller.get_control_status()

        return {
            "control_status": control_status,
            "health": {
                "emergency_mode": control_status["emergency_mode"],
                "last_adaptation": datetime.fromtimestamp(control_status["last_adaptation_time"]).isoformat()
                if control_status["last_adaptation_time"]
                else None,
                "quality_history_health": "healthy"
                if control_status["quality_history_size"] > 5
                else "insufficient_data",
            },
            "configuration": {"adaptation_window": 10, "quality_check_interval": 30, "recovery_wait_time": 300},
            "success": True,
        }

    except Exception as e:
        logger.error(f"❌ 获取质量控制状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/quality/optimize-experience")
async def optimize_user_experience(
    session_id: str = Body(..., description="会话ID"), admin: dict = Depends(require_admin)
):
    """
    优化用户体验 (v7.216)

    Args:
        session_id: 要优化的会话ID

    Returns:
        用户体验优化结果和建议
    """
    try:
        # 获取会话数据
        session_manager = get_session_manager()
        session_data = await session_manager.get_session_history(session_id)

        if not session_data:
            raise HTTPException(status_code=404, detail="会话未找到")

        # 执行用户体验优化
        optimization_result = await user_experience_optimizer.optimize_user_experience(session_data)

        return {
            "session_id": session_id,
            "timestamp": optimization_result["timestamp"],
            "experience_metrics": optimization_result["experience_metrics"],
            "experience_level": optimization_result["experience_level"],
            "optimization_plan": optimization_result["optimization_plan"],
            "optimization_result": optimization_result["optimization_result"],
            "personalization": optimization_result["personalization"],
            "recommendations": optimization_result["recommendations"],
            "success": optimization_result["success"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 用户体验优化失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quality/experience-status")
async def get_experience_optimization_status(admin: dict = Depends(require_admin)):
    """
    获取用户体验优化状态 (v7.216)

    Returns:
        用户体验优化器的当前状态
    """
    try:
        optimization_status = user_experience_optimizer.get_optimization_status()

        return {
            "optimization_status": optimization_status,
            "health": {
                "system_health": optimization_status["health_status"],
                "active_optimizations": optimization_status["active_optimizations"],
            },
            "thresholds": {
                "excellent": "响应时间 ≤10s, 成功率 ≥90%, 错误率 ≤5%",
                "good": "响应时间 ≤20s, 成功率 ≥75%, 错误率 ≤15%",
                "acceptable": "响应时间 ≤30s, 成功率 ≥60%, 错误率 ≤25%",
                "poor": "低于可接受标准",
            },
            "features": {
                "adaptive_response_optimization": True,
                "intelligent_progress_feedback": True,
                "enhanced_error_handling": True,
                "personalized_recommendations": True,
                "real_time_performance_monitoring": True,
            },
            "success": True,
        }

    except Exception as e:
        logger.error(f"❌ 获取用户体验优化状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
