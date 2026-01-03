"""
动机识别系统 - 管理员路由
提供学习系统监控、人工审核、配置管理等功能
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from loguru import logger

from intelligent_project_analyzer.services.motivation_engine import (
    MotivationLearningSystem,
    MotivationTypeRegistry,
    UnmatchedCase,
)

router = APIRouter(prefix="/api/motivation-admin", tags=["Motivation Admin"])


# ==================== 学习系统监控 ====================


@router.get("/learning/stats")
async def get_learning_stats(days: int = 7) -> Dict[str, Any]:
    """
    获取学习系统统计数据

    返回：
    - 案例总数
    - 类型分布
    - 置信度分布
    - 趋势图数据
    """
    registry = MotivationTypeRegistry()
    learning = MotivationLearningSystem(registry)

    cases = learning.get_recent_cases(days=days)

    if not cases:
        return {"total_cases": 0, "message": "暂无学习案例"}

    # 统计类型分布
    type_distribution = {}
    confidence_distribution = {"high": 0, "medium": 0, "low": 0}
    method_distribution = {}
    daily_trend = {}

    for case in cases:
        # 类型统计
        type_distribution[case.assigned_type] = type_distribution.get(case.assigned_type, 0) + 1

        # 置信度统计
        if case.confidence >= 0.7:
            confidence_distribution["high"] += 1
        elif case.confidence >= 0.5:
            confidence_distribution["medium"] += 1
        else:
            confidence_distribution["low"] += 1

        # 方法统计
        method_distribution[case.method] = method_distribution.get(case.method, 0) + 1

        # 日趋势
        date_key = case.timestamp[:10]  # YYYY-MM-DD
        if date_key not in daily_trend:
            daily_trend[date_key] = {"total": 0, "low_confidence": 0}
        daily_trend[date_key]["total"] += 1
        if case.confidence < 0.7:
            daily_trend[date_key]["low_confidence"] += 1

    # 获取最近的分析报告
    latest_analysis = _get_latest_analysis_report()

    return {
        "total_cases": len(cases),
        "date_range": {
            "start": cases[-1].timestamp if cases else None,
            "end": cases[0].timestamp if cases else None,
            "days": days,
        },
        "type_distribution": type_distribution,
        "confidence_distribution": confidence_distribution,
        "method_distribution": method_distribution,
        "daily_trend": daily_trend,
        "latest_analysis": latest_analysis,
        "health_score": _calculate_health_score(cases),
    }


@router.get("/learning/cases")
async def get_unmatched_cases(
    days: int = 7, type_filter: Optional[str] = None, confidence_max: float = 1.0, limit: int = 50
) -> Dict[str, Any]:
    """
    获取待学习案例列表（支持筛选）

    参数：
    - days: 最近N天
    - type_filter: 类型过滤
    - confidence_max: 最大置信度（查看低置信度案例）
    - limit: 返回数量限制
    """
    registry = MotivationTypeRegistry()
    learning = MotivationLearningSystem(registry)

    cases = learning.get_recent_cases(days=days)

    # 过滤
    filtered_cases = []
    for case in cases:
        if type_filter and case.assigned_type != type_filter:
            continue
        if case.confidence > confidence_max:
            continue
        filtered_cases.append(case)

    # 限制数量
    filtered_cases = filtered_cases[:limit]

    # 转换为字典
    case_dicts = [
        {
            "timestamp": c.timestamp,
            "task_title": c.task_title,
            "task_description": c.task_description[:100] + "..."
            if len(c.task_description) > 100
            else c.task_description,
            "user_input_snippet": c.user_input_snippet,
            "assigned_type": c.assigned_type,
            "confidence": c.confidence,
            "method": c.method,
            "session_id": c.session_id,
        }
        for c in filtered_cases
    ]

    return {
        "total": len(filtered_cases),
        "cases": case_dicts,
        "filters_applied": {"days": days, "type_filter": type_filter, "confidence_max": confidence_max},
    }


# ==================== 周分析管理 ====================


@router.post("/learning/analyze")
async def trigger_weekly_analysis(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """
    手动触发周分析

    返回分析报告摘要
    """
    registry = MotivationTypeRegistry()
    learning = MotivationLearningSystem(registry)

    # 后台执行分析
    async def run_analysis():
        try:
            report = await learning.weekly_pattern_analysis()
            logger.info(f"✅ [Admin] 周分析完成: {report.get('case_count', 0)} 个案例")
        except Exception as e:
            logger.error(f"❌ [Admin] 周分析失败: {e}")

    background_tasks.add_task(run_analysis)

    return {"status": "triggered", "message": "周分析已在后台启动", "timestamp": datetime.now().isoformat()}


@router.get("/learning/analysis-history")
async def get_analysis_history(limit: int = 10) -> Dict[str, Any]:
    """
    获取历史分析报告列表
    """
    registry = MotivationTypeRegistry()
    learning = MotivationLearningSystem(registry)

    reports_dir = learning.feedback_log.parent

    # 查找所有分析报告
    analysis_files = sorted(reports_dir.glob("analysis_*.json"), reverse=True)[:limit]  # 最新的在前

    reports = []
    for file_path in analysis_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                report = json.load(f)
                reports.append(
                    {
                        "filename": file_path.name,
                        "timestamp": report.get("timestamp"),
                        "case_count": report.get("case_count", 0),
                        "status": report.get("status"),
                        "recommendation_priority": report.get("recommendation", {}).get("priority"),
                        "new_dimensions_count": len(report.get("llm_analysis", {}).get("new_dimensions", [])),
                        "patterns_count": len(report.get("llm_analysis", {}).get("discovered_patterns", [])),
                    }
                )
        except Exception as e:
            logger.warning(f"⚠️ 读取报告失败 {file_path}: {e}")

    return {"total": len(reports), "reports": reports}


@router.get("/learning/analysis/{filename}")
async def get_analysis_report(filename: str) -> Dict[str, Any]:
    """
    获取指定分析报告的详细内容
    """
    registry = MotivationTypeRegistry()
    learning = MotivationLearningSystem(registry)

    report_path = learning.feedback_log.parent / filename

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="报告文件不存在")

    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取报告失败: {e}")


# ==================== 人工审核和干预 ====================


@router.post("/suggestions/approve")
async def approve_suggestions(type_id: str, keywords_to_add: List[str], reason: str) -> Dict[str, Any]:
    """
    批准并应用关键词增强建议

    参数：
    - type_id: 动机类型ID
    - keywords_to_add: 要添加的关键词列表
    - reason: 批准原因
    """
    registry = MotivationTypeRegistry()

    # 验证类型是否存在
    motivation_type = registry.get_type(type_id)
    if not motivation_type:
        raise HTTPException(status_code=404, detail=f"动机类型 {type_id} 不存在")

    # TODO: 实际应用到配置文件
    # 这里需要修改YAML文件或数据库

    logger.info(f"✅ [Admin] 批准关键词添加: {type_id} + {keywords_to_add}")

    return {
        "status": "approved",
        "type_id": type_id,
        "keywords_added": keywords_to_add,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
        "note": "需要重启服务以生效（或实现热加载）",
    }


@router.post("/suggestions/reject")
async def reject_suggestions(type_id: str, keywords: List[str], reason: str) -> Dict[str, Any]:
    """
    拒绝关键词建议
    """
    logger.info(f"⚠️ [Admin] 拒绝关键词建议: {type_id} - {keywords}")

    return {
        "status": "rejected",
        "type_id": type_id,
        "keywords": keywords,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/cases/{session_id}/review")
async def review_case(session_id: str, correct_type: str, feedback: str) -> Dict[str, Any]:
    """
    人工审核案例并提供正确分类

    用于训练数据收集
    """
    registry = MotivationTypeRegistry()

    # 验证类型
    if not registry.get_type(correct_type):
        raise HTTPException(status_code=400, detail=f"无效的动机类型: {correct_type}")

    # 记录人工审核结果
    review_log_path = Path("logs/motivation_human_reviews.jsonl")
    review_log_path.parent.mkdir(parents=True, exist_ok=True)

    review_record = {
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id,
        "correct_type": correct_type,
        "feedback": feedback,
        "reviewer": "admin",  # TODO: 从认证信息获取
    }

    try:
        with open(review_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(review_record, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"❌ [Admin] 记录审核失败: {e}")

    logger.info(f"✅ [Admin] 案例审核完成: {session_id} -> {correct_type}")

    return {"status": "reviewed", "session_id": session_id, "correct_type": correct_type, "message": "审核已记录，将用于未来模型优化"}


# ==================== 配置管理 ====================


@router.get("/config/types")
async def get_motivation_types() -> Dict[str, Any]:
    """
    获取所有动机类型配置
    """
    registry = MotivationTypeRegistry()
    types_list = registry.get_all_types()

    return {
        "total": len(types_list),
        "types": [
            {
                "id": t.id,
                "label_zh": t.label_zh,
                "label_en": t.label_en,
                "priority": t.priority,
                "description": t.description,
                "keywords_count": len(t.keywords),
                "enabled": t.enabled,
                "color": t.color,
            }
            for t in types_list
        ],
    }


@router.get("/config/types/{type_id}")
async def get_motivation_type_detail(type_id: str) -> Dict[str, Any]:
    """
    获取指定动机类型的详细配置
    """
    registry = MotivationTypeRegistry()
    motivation_type = registry.get_type(type_id)

    if not motivation_type:
        raise HTTPException(status_code=404, detail=f"动机类型 {type_id} 不存在")

    return {
        "id": motivation_type.id,
        "label_zh": motivation_type.label_zh,
        "label_en": motivation_type.label_en,
        "priority": motivation_type.priority,
        "description": motivation_type.description,
        "keywords": motivation_type.keywords,
        "llm_examples": motivation_type.llm_examples,
        "enabled": motivation_type.enabled,
        "color": motivation_type.color,
    }


@router.put("/config/types/{type_id}/toggle")
async def toggle_motivation_type(type_id: str) -> Dict[str, Any]:
    """
    启用/禁用指定动机类型
    """
    registry = MotivationTypeRegistry()
    motivation_type = registry.get_type(type_id)

    if not motivation_type:
        raise HTTPException(status_code=404, detail=f"动机类型 {type_id} 不存在")

    # TODO: 实际修改配置文件
    new_state = not motivation_type.enabled

    logger.info(f"✅ [Admin] 切换类型状态: {type_id} -> {new_state}")

    return {"status": "updated", "type_id": type_id, "enabled": new_state, "message": "需要重启服务以生效"}


# ==================== 辅助函数 ====================


def _get_latest_analysis_report() -> Optional[Dict[str, Any]]:
    """获取最新的分析报告"""
    try:
        registry = MotivationTypeRegistry()
        learning = MotivationLearningSystem(registry)
        reports_dir = learning.feedback_log.parent

        analysis_files = sorted(reports_dir.glob("analysis_*.json"), reverse=True)

        if not analysis_files:
            return None

        with open(analysis_files[0], "r", encoding="utf-8") as f:
            report = json.load(f)

        return {
            "filename": analysis_files[0].name,
            "timestamp": report.get("timestamp"),
            "case_count": report.get("case_count", 0),
            "recommendation_priority": report.get("recommendation", {}).get("priority"),
            "new_dimensions_count": len(report.get("llm_analysis", {}).get("new_dimensions", [])),
        }
    except Exception as e:
        logger.warning(f"⚠️ 获取最新报告失败: {e}")
        return None


def _calculate_health_score(cases: List[UnmatchedCase]) -> Dict[str, Any]:
    """计算学习系统健康分数"""
    if not cases:
        return {"score": 100, "status": "excellent", "message": "暂无案例"}

    # 指标：
    # 1. 低置信度比例（越低越好）
    low_confidence_count = sum(1 for c in cases if c.confidence < 0.5)
    low_confidence_ratio = low_confidence_count / len(cases)

    # 2. mixed类型比例（越低越好）
    mixed_count = sum(1 for c in cases if c.assigned_type == "mixed")
    mixed_ratio = mixed_count / len(cases)

    # 3. LLM成功率（越高越好）
    llm_count = sum(1 for c in cases if c.method == "llm")
    llm_ratio = llm_count / len(cases)

    # 综合评分
    score = 100
    score -= low_confidence_ratio * 30  # 最多扣30分
    score -= mixed_ratio * 40  # 最多扣40分
    score += llm_ratio * 20  # 最多加20分
    score = max(0, min(100, score))

    if score >= 80:
        status = "excellent"
        message = "系统运行良好"
    elif score >= 60:
        status = "good"
        message = "识别准确度较高"
    elif score >= 40:
        status = "fair"
        message = "建议优化关键词配置"
    else:
        status = "poor"
        message = "需要立即检查配置"

    return {
        "score": round(score, 1),
        "status": status,
        "message": message,
        "metrics": {
            "low_confidence_ratio": round(low_confidence_ratio, 2),
            "mixed_ratio": round(mixed_ratio, 2),
            "llm_ratio": round(llm_ratio, 2),
        },
    }
