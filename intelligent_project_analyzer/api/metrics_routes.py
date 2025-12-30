"""
性能和告警 API 端点
提供前端查询性能统计和告警历史的接口
"""

from fastapi import APIRouter, Query
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import json
from pathlib import Path
from loguru import logger

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

# 日志文件路径
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
PERFORMANCE_LOG = LOGS_DIR / "performance_metrics.jsonl"
LLM_LOG = LOGS_DIR / "llm_metrics.jsonl"
ALERTS_LOG = LOGS_DIR / "alerts.log"


def _read_jsonl(file_path: Path, limit: int = 1000) -> List[Dict[str, Any]]:
    """读取 JSONL 文件并返回最近的记录"""
    records = []
    try:
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line.strip())
                        records.append(record)
                    except json.JSONDecodeError:
                        continue
        return records[-limit:]  # 只返回最近的记录
    except Exception as e:
        logger.error(f"读取 JSONL 文件失败: {e}")
        return []


@router.get("/performance/summary")
async def get_performance_summary(
    hours: int = Query(default=1, ge=1, le=24, description="统计时长（小时）")
) -> Dict[str, Any]:
    """
    获取性能统计摘要
    
    返回：
    - total_requests: 总请求数
    - avg_duration: 平均响应时间（ms）
    - max_duration: 最大响应时间（ms）
    - min_duration: 最小响应时间（ms）
    - slow_requests: 慢请求数（>1000ms）
    - error_rate: 错误率（%）
    """
    records = _read_jsonl(PERFORMANCE_LOG, limit=10000)
    
    # 过滤指定时间范围内的记录
    cutoff_time = datetime.now() - timedelta(hours=hours)
    filtered_records = [
        r for r in records
        if datetime.fromisoformat(r.get("timestamp", "")) > cutoff_time
    ]
    
    if not filtered_records:
        return {
            "total_requests": 0,
            "avg_duration": 0,
            "max_duration": 0,
            "min_duration": 0,
            "slow_requests": 0,
            "error_rate": 0,
            "time_range_hours": hours
        }
    
    durations = [r.get("duration", 0) for r in filtered_records]
    status_codes = [r.get("status_code", 200) for r in filtered_records]
    
    total_requests = len(filtered_records)
    avg_duration = sum(durations) / total_requests
    max_duration = max(durations)
    min_duration = min(durations)
    slow_requests = sum(1 for d in durations if d > 1000)
    error_count = sum(1 for s in status_codes if s >= 400)
    error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
    
    return {
        "total_requests": total_requests,
        "avg_duration": round(avg_duration, 2),
        "max_duration": max_duration,
        "min_duration": min_duration,
        "slow_requests": slow_requests,
        "error_rate": round(error_rate, 2),
        "time_range_hours": hours
    }


@router.get("/performance/slow-requests")
async def get_slow_requests(
    limit: int = Query(default=10, ge=1, le=100, description="返回记录数")
) -> List[Dict[str, Any]]:
    """
    获取最近的慢请求（>1000ms）
    
    返回字段：
    - timestamp: 时间戳
    - path: 请求路径
    - method: 请求方法
    - duration: 响应时间（ms）
    - status_code: 状态码
    """
    records = _read_jsonl(PERFORMANCE_LOG, limit=10000)
    
    # 筛选慢请求并按时间倒序排列
    slow_requests = [
        {
            "timestamp": r.get("timestamp"),
            "path": r.get("path"),
            "method": r.get("method"),
            "duration": r.get("duration"),
            "status_code": r.get("status_code")
        }
        for r in records
        if r.get("duration", 0) > 1000
    ]
    
    slow_requests.sort(key=lambda x: x["timestamp"], reverse=True)
    return slow_requests[:limit]


@router.get("/performance/by-endpoint")
async def get_performance_by_endpoint(
    hours: int = Query(default=1, ge=1, le=24, description="统计时长（小时）")
) -> List[Dict[str, Any]]:
    """
    按 API 端点统计性能
    
    返回字段：
    - path: 请求路径
    - method: 请求方法
    - count: 请求次数
    - avg_duration: 平均响应时间（ms）
    - max_duration: 最大响应时间（ms）
    - slow_count: 慢请求数
    """
    records = _read_jsonl(PERFORMANCE_LOG, limit=10000)
    
    # 过滤时间范围
    cutoff_time = datetime.now() - timedelta(hours=hours)
    filtered_records = [
        r for r in records
        if datetime.fromisoformat(r.get("timestamp", "")) > cutoff_time
    ]
    
    # 按端点分组统计
    endpoint_stats = {}
    for r in filtered_records:
        key = (r.get("path", "unknown"), r.get("method", "GET"))
        if key not in endpoint_stats:
            endpoint_stats[key] = {
                "path": key[0],
                "method": key[1],
                "count": 0,
                "durations": [],
                "slow_count": 0
            }
        
        duration = r.get("duration", 0)
        endpoint_stats[key]["count"] += 1
        endpoint_stats[key]["durations"].append(duration)
        if duration > 1000:
            endpoint_stats[key]["slow_count"] += 1
    
    # 计算统计值
    result = []
    for stats in endpoint_stats.values():
        durations = stats["durations"]
        result.append({
            "path": stats["path"],
            "method": stats["method"],
            "count": stats["count"],
            "avg_duration": round(sum(durations) / len(durations), 2),
            "max_duration": max(durations),
            "slow_count": stats["slow_count"]
        })
    
    # 按请求数排序
    result.sort(key=lambda x: x["count"], reverse=True)
    return result


@router.get("/llm/summary")
async def get_llm_summary(
    hours: int = Query(default=1, ge=1, le=24, description="统计时长（小时）")
) -> Dict[str, Any]:
    """
    获取 LLM 调用统计摘要
    
    返回：
    - total_calls: 总调用次数
    - success_rate: 成功率（%）
    - avg_duration: 平均耗时（ms）
    - total_tokens: 总 Token 数
    - by_model: 按模型分组统计
    """
    records = _read_jsonl(LLM_LOG, limit=10000)
    
    # 过滤时间范围
    cutoff_time = datetime.now() - timedelta(hours=hours)
    filtered_records = [
        r for r in records
        if datetime.fromisoformat(r.get("timestamp", "")) > cutoff_time
    ]
    
    if not filtered_records:
        return {
            "total_calls": 0,
            "success_rate": 0,
            "avg_duration": 0,
            "total_tokens": 0,
            "by_model": {},
            "time_range_hours": hours
        }
    
    total_calls = len(filtered_records)
    success_count = sum(1 for r in filtered_records if r.get("success", False))
    success_rate = (success_count / total_calls * 100) if total_calls > 0 else 0
    
    durations = [r.get("duration", 0) for r in filtered_records]
    avg_duration = sum(durations) / total_calls
    
    total_tokens = sum(r.get("tokens", 0) for r in filtered_records)
    
    # 按模型分组
    by_model = {}
    for r in filtered_records:
        model = r.get("model", "unknown")
        if model not in by_model:
            by_model[model] = {
                "calls": 0,
                "success": 0,
                "tokens": 0,
                "duration": []
            }
        by_model[model]["calls"] += 1
        if r.get("success", False):
            by_model[model]["success"] += 1
        by_model[model]["tokens"] += r.get("tokens", 0)
        by_model[model]["duration"].append(r.get("duration", 0))
    
    # 计算每个模型的统计值
    model_stats = {}
    for model, stats in by_model.items():
        model_stats[model] = {
            "calls": stats["calls"],
            "success_rate": round((stats["success"] / stats["calls"] * 100), 2),
            "avg_duration": round(sum(stats["duration"]) / len(stats["duration"]), 2),
            "total_tokens": stats["tokens"]
        }
    
    return {
        "total_calls": total_calls,
        "success_rate": round(success_rate, 2),
        "avg_duration": round(avg_duration, 2),
        "total_tokens": total_tokens,
        "by_model": model_stats,
        "time_range_hours": hours
    }


@router.get("/alerts/recent")
async def get_recent_alerts(
    limit: int = Query(default=20, ge=1, le=100, description="返回记录数")
) -> List[Dict[str, Any]]:
    """
    获取最近的告警记录
    
    返回字段：
    - timestamp: 时间戳
    - message: 告警消息
    - error_detail: 错误详情（如果有）
    """
    alerts = []
    try:
        if ALERTS_LOG.exists():
            with open(ALERTS_LOG, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        alert = json.loads(line.strip())
                        alerts.append(alert)
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.error(f"读取告警日志失败: {e}")
    
    # 按时间倒序排列
    alerts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return alerts[:limit]


@router.get("/alerts/stats")
async def get_alert_stats(
    hours: int = Query(default=24, ge=1, le=168, description="统计时长（小时）")
) -> Dict[str, Any]:
    """
    获取告警统计
    
    返回：
    - total_alerts: 总告警数
    - alerts_per_hour: 每小时平均告警数
    - recent_trend: 最近趋势（数组，每小时告警数）
    """
    alerts = []
    try:
        if ALERTS_LOG.exists():
            with open(ALERTS_LOG, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        alert = json.loads(line.strip())
                        alerts.append(alert)
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.error(f"读取告警日志失败: {e}")
    
    # 过滤时间范围
    cutoff_time = datetime.now() - timedelta(hours=hours)
    filtered_alerts = [
        a for a in alerts
        if datetime.fromisoformat(a.get("timestamp", "")) > cutoff_time
    ]
    
    total_alerts = len(filtered_alerts)
    alerts_per_hour = total_alerts / hours if hours > 0 else 0
    
    # 计算每小时趋势（最近 24 小时）
    trend_hours = min(24, hours)
    trend = [0] * trend_hours
    for alert in filtered_alerts:
        alert_time = datetime.fromisoformat(alert.get("timestamp", ""))
        hours_ago = int((datetime.now() - alert_time).total_seconds() / 3600)
        if 0 <= hours_ago < trend_hours:
            trend[trend_hours - 1 - hours_ago] += 1
    
    return {
        "total_alerts": total_alerts,
        "alerts_per_hour": round(alerts_per_hour, 2),
        "recent_trend": trend,
        "time_range_hours": hours
    }
