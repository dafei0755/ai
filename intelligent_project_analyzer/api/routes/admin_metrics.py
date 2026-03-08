"""系统监控 API — metrics, tools, concept-maps, conversations"""

import json
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from ..auth_middleware import require_admin
from ..performance_monitor import performance_monitor
from .admin_shared import extract_meaningful_keywords, metrics_cache

router = APIRouter()


@router.get("/metrics/summary")
async def get_metrics_summary(admin: dict = Depends(require_admin)):
    """
    获取系统监控摘要

    返回：
    - CPU使用率
    - 内存使用率
    - 活跃会话数
    - 请求统计

    缓存策略：5秒内重复请求返回缓存
    """
    cache_key = "metrics_summary"

    # 检查缓存
    if cache_key in metrics_cache:
        logger.debug(" 返回缓存的监控数据")
        return metrics_cache[cache_key]

    try:
        import psutil

        # 计算实时指标 - 增加容错处理和诊断日志
        cpu_percent = 0.0
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            logger.debug(f" CPU: {cpu_percent}%")
        except Exception as e:
            logger.warning(f"️ CPU监控失败: {type(e).__name__}")

        memory_info = {"percent": 0, "used": 0, "total": 0}
        try:
            mem = psutil.virtual_memory()
            memory_info = {"percent": mem.percent, "used": mem.used, "total": mem.total}
            logger.debug(f" 内存: {mem.percent}%")
        except Exception as e:
            logger.warning(f"️ 内存监控失败: {type(e).__name__}")

        disk_info = {"percent": 0, "used": 0, "total": 0}
        try:
            #  v7.122: 增强Windows兼容性（Python 3.13 + psutil修复）
            import os
            import platform

            if platform.system() == "Windows":
                # 尝试多种路径格式
                disk_path_candidates = [
                    os.path.abspath(os.sep),  # 当前驱动器根目录
                    "C:\\",  # Windows系统盘
                    "C:/",  # 备用格式
                ]

                disk = None
                for path in disk_path_candidates:
                    try:
                        disk = psutil.disk_usage(path)
                        logger.debug(f" 磁盘路径成功: {path}")
                        break
                    except Exception:
                        continue

                if disk is None:
                    raise RuntimeError("所有磁盘路径尝试均失败")
            else:
                disk = psutil.disk_usage("/")

            disk_info = {"percent": disk.percent, "used": disk.used, "total": disk.total}
            logger.debug(f" 磁盘: {disk.percent}%")
        except Exception as e:
            logger.warning(f"️ 磁盘监控失败: {type(e).__name__} - {str(e)[:50]}")
            # 降级处理：返回None，前端显示"不可用"
            disk_info = None

        # 活跃会话数 (从Redis获取所有会话)
        active_sessions = 0
        try:
            # 从 server.py 导入全局 session_manager
            from ..api.server import session_manager as global_session_manager

            if global_session_manager:
                all_sessions = await global_session_manager.get_all_sessions()
                active_sessions = len([s for s in all_sessions if s.get("status") == "active"])
                logger.debug(f" 活跃会话: {active_sessions}")
            else:
                logger.warning("️ session_manager 未初始化")
        except Exception as e:
            logger.warning(f"️ 会话监控失败: {type(e).__name__}")

        # 性能指标
        perf_stats = performance_monitor.get_stats_summary()
        logger.debug(f" 性能统计: {perf_stats}")

        result = {
            "system": {
                "cpu_percent": round(cpu_percent, 2),
                "memory_percent": round(memory_info["percent"], 2),
                "memory_used_gb": round(memory_info["used"] / (1024**3), 2),
                "memory_total_gb": round(memory_info["total"] / (1024**3), 2),
                "disk_percent": round(disk_info["percent"], 2),
                "disk_used_gb": round(disk_info["used"] / (1024**3), 2),
                "disk_total_gb": round(disk_info["total"] / (1024**3), 2),
            },
            "sessions": {
                "active_count": active_sessions,
            },
            "performance": {
                "total_requests": perf_stats.get("total_requests", 0),
                "avg_response_time": perf_stats.get("avg_response_time", 0),
                "requests_per_minute": perf_stats.get("requests_per_minute", 0),
                "error_count": perf_stats.get("error_count", 0),
            },
            "timestamp": datetime.now().isoformat(),
        }

        # 写入缓存
        metrics_cache[cache_key] = result
        return result

    except Exception:
        # 极度保守的错误处理，避免 SystemError 导致 500
        logger.error("获取监控数据发生未知错误")
        return {
            "system": {
                "cpu_percent": 0,
                "memory_percent": 0,
                "memory_used_gb": 0,
                "memory_total_gb": 0,
                "disk_percent": 0,
                "disk_used_gb": 0,
                "disk_total_gb": 0,
            },
            "sessions": {"active_count": 0},
            "performance": {"total_requests": 0, "avg_response_time": 0, "requests_per_minute": 0, "error_count": 0},
            "timestamp": datetime.now().isoformat(),
            "error": "Internal Monitoring Error",
        }


@router.get("/metrics/performance/details")
async def get_performance_details(hours: int = Query(default=1, ge=1, le=24), admin: dict = Depends(require_admin)):
    """
    获取详细性能指标

    Args:
        hours: 查询时间范围（小时）
    """
    try:
        details = performance_monitor.get_detailed_stats(hours=hours)
        return {"time_range_hours": hours, "data": details, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f" 获取性能详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/slow-requests")
async def get_slow_requests(limit: int = Query(default=20, ge=1, le=100), admin: dict = Depends(require_admin)):
    """
    获取慢请求列表

    Args:
        limit: 返回数量限制
    """
    try:
        slow_requests = performance_monitor.get_slow_requests(limit=limit)
        return {"slow_requests": slow_requests, "count": len(slow_requests), "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f" 获取慢请求失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools/stats")
async def get_tools_stats(hours: int = Query(default=24, ge=1, le=168), admin: dict = Depends(require_admin)):
    """
    获取搜索工具调用统计

    统计指标：
    - 各工具调用次数、成功率、平均响应时间
    - Top查询、错误分布

    Args:
        hours: 统计时间范围（小时，默认24小时）

    Returns:
        工具统计数据
    """
    cache_key = f"tools_stats_{hours}"

    # 检查缓存（60秒TTL）
    if cache_key in metrics_cache:
        logger.debug(" 返回缓存的工具统计数据")
        return metrics_cache[cache_key]

    try:
        # 读取工具调用日志
        log_file = Path("logs/tool_calls.jsonl")
        if not log_file.exists():
            return {
                "tools": [],
                "total_calls": 0,
                "time_range_hours": hours,
                "timestamp": datetime.now().isoformat(),
                "message": "暂无工具调用记录",
            }

        # 计算时间范围
        cutoff_time = datetime.now() - timedelta(hours=hours)

        # 解析日志
        tool_data = {}
        total_calls = 0

        with open(log_file, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    timestamp = datetime.fromisoformat(entry["timestamp"])

                    # 过滤时间范围
                    if timestamp < cutoff_time:
                        continue

                    tool_name = entry["tool_name"]
                    if tool_name not in tool_data:
                        tool_data[tool_name] = {
                            "name": tool_name,
                            "total_calls": 0,
                            "success_count": 0,
                            "fail_count": 0,
                            "total_duration_ms": 0,
                            "queries": [],
                        }

                    tool_data[tool_name]["total_calls"] += 1
                    total_calls += 1

                    if entry["status"] == "completed":
                        tool_data[tool_name]["success_count"] += 1
                    else:
                        tool_data[tool_name]["fail_count"] += 1

                    duration = entry.get("duration_ms", 0)
                    tool_data[tool_name]["total_duration_ms"] += duration

                    # 记录查询（用于Top查询统计）
                    if entry.get("input_query"):
                        tool_data[tool_name]["queries"].append(entry["input_query"])

                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    logger.warning(f"解析日志行失败: {e}")
                    continue

        # 汇总统计
        tools_summary = []
        for tool_name, data in tool_data.items():
            total = data["total_calls"]
            success_rate = (data["success_count"] / total * 100) if total > 0 else 0
            avg_duration = (data["total_duration_ms"] / total) if total > 0 else 0

            # Top 5 查询（简单计数）
            from collections import Counter

            query_counter = Counter(data["queries"])
            top_queries = [{"query": q[:100], "count": c} for q, c in query_counter.most_common(5)]

            tools_summary.append(
                {
                    "tool_name": tool_name,
                    "total_calls": total,
                    "success_count": data["success_count"],
                    "fail_count": data["fail_count"],
                    "success_rate": round(success_rate, 2),
                    "avg_duration_ms": round(avg_duration, 2),
                    "top_queries": top_queries,
                }
            )

        # 按调用次数降序排序
        tools_summary.sort(key=lambda x: x["total_calls"], reverse=True)

        result = {
            "tools": tools_summary,
            "total_calls": total_calls,
            "time_range_hours": hours,
            "timestamp": datetime.now().isoformat(),
        }

        # 写入缓存
        metrics_cache[cache_key] = result
        return result

    except Exception as e:
        logger.error(f" 获取工具统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tools/call-rate")
async def get_tool_call_rate(hours: int = Query(default=24, ge=1, le=168), admin: dict = Depends(require_admin)):
    """
     v7.153: 获取工具调用率统计

    统计指标：
    - 各角色的工具调用率（调用次数 / 会话数）
    - 无工具调用的会话比例
    - 工具调用失败率

    Args:
        hours: 统计时间范围（小时，默认24小时）

    Returns:
        工具调用率统计数据
    """
    cache_key = f"tool_call_rate_{hours}"

    # 检查缓存（60秒TTL）
    if cache_key in metrics_cache:
        logger.debug(" 返回缓存的工具调用率数据")
        return metrics_cache[cache_key]

    try:
        # 读取工具调用日志
        log_file = Path("logs/tool_calls.jsonl")
        cutoff_time = datetime.now() - timedelta(hours=hours)

        # 统计数据结构
        role_stats = {}  # role_id -> { sessions: set, total_calls: int, success_calls: int }
        session_tool_usage = {}  # session_id -> { has_tool_call: bool, tool_count: int }

        if log_file.exists():
            with open(log_file, encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        timestamp = datetime.fromisoformat(entry["timestamp"])

                        # 过滤时间范围
                        if timestamp < cutoff_time:
                            continue

                        role_id = entry.get("role_id", "unknown")
                        deliverable_id = entry.get("deliverable_id", "")
                        # 从 deliverable_id 提取 session_id（格式：session_id_deliverable）
                        session_id = deliverable_id.split("_")[0] if "_" in deliverable_id else deliverable_id

                        # 初始化角色统计
                        if role_id not in role_stats:
                            role_stats[role_id] = {
                                "sessions": set(),
                                "total_calls": 0,
                                "success_calls": 0,
                            }

                        role_stats[role_id]["sessions"].add(session_id)
                        role_stats[role_id]["total_calls"] += 1
                        if entry.get("status") == "completed":
                            role_stats[role_id]["success_calls"] += 1

                        # 会话工具使用统计
                        if session_id not in session_tool_usage:
                            session_tool_usage[session_id] = {"has_tool_call": False, "tool_count": 0}
                        session_tool_usage[session_id]["has_tool_call"] = True
                        session_tool_usage[session_id]["tool_count"] += 1

                    except (json.JSONDecodeError, KeyError):
                        continue

        # 计算角色调用率
        role_call_rates = []
        for role_id, stats in role_stats.items():
            session_count = len(stats["sessions"])
            total_calls = stats["total_calls"]
            success_calls = stats["success_calls"]

            call_rate = (total_calls / session_count) if session_count > 0 else 0
            success_rate = (success_calls / total_calls * 100) if total_calls > 0 else 0

            role_call_rates.append(
                {
                    "role_id": role_id,
                    "session_count": session_count,
                    "total_calls": total_calls,
                    "calls_per_session": round(call_rate, 2),
                    "success_rate": round(success_rate, 2),
                }
            )

        # 按调用率降序排序
        role_call_rates.sort(key=lambda x: x["calls_per_session"], reverse=True)

        # 计算总体统计
        total_sessions = len(session_tool_usage)
        sessions_with_tools = sum(1 for s in session_tool_usage.values() if s["has_tool_call"])
        sessions_without_tools = total_sessions - sessions_with_tools

        overall_call_rate = (sessions_with_tools / total_sessions * 100) if total_sessions > 0 else 0

        result = {
            "role_call_rates": role_call_rates,
            "overall": {
                "total_sessions": total_sessions,
                "sessions_with_tools": sessions_with_tools,
                "sessions_without_tools": sessions_without_tools,
                "tool_usage_rate": round(overall_call_rate, 2),
            },
            "time_range_hours": hours,
            "timestamp": datetime.now().isoformat(),
        }

        # 写入缓存
        metrics_cache[cache_key] = result
        return result

    except Exception as e:
        logger.error(f" 获取工具调用率失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/concept-maps/stats")
async def get_concept_maps_stats(days: int = Query(default=7, ge=1, le=30), admin: dict = Depends(require_admin)):
    """
    获取概念图生成统计

    统计指标：
    - 总生成数量、会话分布、专家分布
    - 平均尺寸、宽高比分布
    - 存储占用、时间趋势

    Args:
        days: 统计时间范围（天，默认7天）

    Returns:
        概念图统计数据
    """
    cache_key = f"concept_maps_stats_{days}"

    # 检查缓存（60秒TTL）
    if cache_key in metrics_cache:
        logger.debug(" 返回缓存的概念图统计数据")
        return metrics_cache[cache_key]

    try:
        from collections import Counter, defaultdict

        from intelligent_project_analyzer.services.image_storage_manager import ImageStorageManager

        # 计算时间范围
        cutoff_time = datetime.now() - timedelta(days=days)

        # 扫描所有会话目录
        base_dir = ImageStorageManager.BASE_DIR
        if not base_dir.exists():
            return {
                "total_images": 0,
                "total_sessions": 0,
                "total_storage_mb": 0,
                "time_range_days": days,
                "timestamp": datetime.now().isoformat(),
                "message": "暂无概念图数据",
            }

        # 统计数据容器
        total_images = 0
        total_size_bytes = 0
        sessions_with_images = []
        images_by_expert = Counter()
        images_by_aspect_ratio = Counter()
        images_by_date = defaultdict(int)
        all_sessions = []

        # 遍历所有会话目录
        for session_dir in base_dir.iterdir():
            if not session_dir.is_dir():
                continue

            metadata_file = session_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            try:
                with open(metadata_file, encoding="utf-8") as f:
                    metadata = json.load(f)

                session_id = metadata.get("session_id", session_dir.name)
                session_created = datetime.fromisoformat(metadata.get("created_at", cutoff_time.isoformat()))

                # 过滤时间范围
                if session_created < cutoff_time:
                    continue

                images = metadata.get("images", [])
                if not images:
                    continue

                # 统计会话信息
                session_image_count = len(images)
                session_size = sum(img.get("file_size_bytes", 0) for img in images)

                sessions_with_images.append(
                    {
                        "session_id": session_id,
                        "image_count": session_image_count,
                        "total_size_mb": round(session_size / (1024 * 1024), 2),
                        "created_at": session_created.isoformat(),
                    }
                )

                all_sessions.append(session_id)

                # 统计图片详情
                for img in images:
                    total_images += 1
                    total_size_bytes += img.get("file_size_bytes", 0)

                    # 按专家统计
                    expert = img.get("owner_role", "unknown")
                    images_by_expert[expert] += 1

                    # 按宽高比统计
                    aspect_ratio = img.get("aspect_ratio", "16:9")
                    images_by_aspect_ratio[aspect_ratio] += 1

                    # 按日期统计
                    created_at = datetime.fromisoformat(img.get("created_at", session_created.isoformat()))
                    date_key = created_at.strftime("%Y-%m-%d")
                    images_by_date[date_key] += 1

            except Exception as e:
                logger.warning(f"️ 解析会话 {session_dir.name} 失败: {e}")
                continue

        # 按图片数量排序会话
        sessions_with_images.sort(key=lambda x: x["image_count"], reverse=True)

        # 转换专家统计为列表
        expert_stats = [{"expert_role": role, "image_count": count} for role, count in images_by_expert.most_common()]

        # 转换宽高比统计
        aspect_ratio_stats = [
            {"aspect_ratio": ratio, "count": count} for ratio, count in images_by_aspect_ratio.most_common()
        ]

        # 转换日期趋势（最近7天）
        date_trend = [
            {"date": date, "count": count} for date, count in sorted(images_by_date.items(), reverse=True)[:7]
        ]

        result = {
            "total_images": total_images,
            "total_sessions": len(all_sessions),
            "total_storage_mb": round(total_size_bytes / (1024 * 1024), 2),
            "avg_images_per_session": round(total_images / len(all_sessions), 2) if all_sessions else 0,
            "expert_distribution": expert_stats,
            "aspect_ratio_distribution": aspect_ratio_stats,
            "date_trend": date_trend,
            "top_sessions": sessions_with_images[:10],  # Top 10 会话
            "time_range_days": days,
            "timestamp": datetime.now().isoformat(),
        }

        # 写入缓存
        metrics_cache[cache_key] = result
        return result

    except Exception as e:
        logger.error(f" 获取概念图统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/analytics")
async def get_conversations_analytics(
    days: int = Query(default=30, ge=1, le=365), admin: dict = Depends(require_admin)
):
    """
    获取对话分析统计

     v7.201: 合并Redis活跃会话和SQLite归档会话

    统计指标：
    - 时间趋势：每天、每周、每月的对话数量
    - 类型分布：项目类型分布
    - 状态分布：completed/failed/active
    - 关键词分析：用户输入的高频关键词

    Args:
        days: 统计时间范围（天，默认30天）

    Returns:
        对话分析数据
    """
    cache_key = f"conversations_analytics_{days}"

    # 检查缓存（60秒TTL）
    if cache_key in metrics_cache:
        logger.debug(" 返回缓存的对话分析数据")
        return metrics_cache[cache_key]

    try:
        all_sessions = []

        # 1. 获取Redis活跃会话
        from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

        redis_manager = RedisSessionManager()

        # 确保Redis连接
        if not redis_manager.is_connected:
            await redis_manager.connect()

        redis_sessions = await redis_manager.get_all_sessions()
        all_sessions.extend(redis_sessions)
        logger.debug(f" 对话分析 - Redis活跃会话: {len(redis_sessions)} 条")

        # 2. 获取SQLite归档会话
        from ..api.server import archive_manager

        if archive_manager:
            archived_sessions = await archive_manager.list_archived_sessions(
                limit=10000,  # 获取足够多的数据
                offset=0,
                user_id=None,  # 管理员查看所有用户
            )
            all_sessions.extend(archived_sessions)
            logger.debug(f" 对话分析 - 归档会话: {len(archived_sessions)} 条")

        # 3. 去重
        seen_ids = set()
        unique_sessions = []
        for session in all_sessions:
            session_id = session.get("session_id")
            if session_id and session_id not in seen_ids:
                seen_ids.add(session_id)
                unique_sessions.append(session)
        all_sessions = unique_sessions

        # 计算时间范围
        cutoff_time = datetime.now() - timedelta(days=days)

        # 统计数据容器
        from collections import Counter, defaultdict

        daily_counts = defaultdict(int)
        weekly_counts = defaultdict(int)
        monthly_counts = defaultdict(int)
        yearly_counts = defaultdict(int)

        type_distribution = Counter()
        status_distribution = Counter()
        all_keywords = []

        total_conversations = 0

        for session in all_sessions:
            # 解析创建时间
            created_at_str = session.get("created_at", "")
            if not created_at_str:
                continue

            try:
                created_at = datetime.fromisoformat(created_at_str)
            except (ValueError, TypeError):
                continue

            # 过滤时间范围
            if created_at < cutoff_time:
                continue

            total_conversations += 1

            # 时间趋势统计
            date_key = created_at.strftime("%Y-%m-%d")
            week_key = created_at.strftime("%Y-W%W")
            month_key = created_at.strftime("%Y-%m")
            year_key = created_at.strftime("%Y")

            daily_counts[date_key] += 1
            weekly_counts[week_key] += 1
            monthly_counts[month_key] += 1
            yearly_counts[year_key] += 1

            # 类型分布
            project_type = session.get("project_type", "未分类")
            type_distribution[project_type] += 1

            # 状态分布
            status = session.get("status", "unknown")
            status_distribution[status] += 1

            # 关键词提取（从user_input）
            user_input = session.get("user_input", "")
            if user_input:
                # 使用智能分词提取关键词
                keywords = extract_meaningful_keywords(user_input)
                all_keywords.extend(keywords)

        # 关键词统计（Top 50）
        keyword_counter = Counter(all_keywords)
        top_keywords = [{"word": word, "count": count} for word, count in keyword_counter.most_common(50)]

        # 转换为前端友好的格式
        daily_trend = [
            {"date": date, "count": count} for date, count in sorted(daily_counts.items(), reverse=True)[:30]  # 最近30天
        ]

        weekly_trend = [
            {"week": week, "count": count} for week, count in sorted(weekly_counts.items(), reverse=True)[:12]  # 最近12周
        ]

        monthly_trend = [
            {"month": month, "count": count}
            for month, count in sorted(monthly_counts.items(), reverse=True)[:12]  # 最近12月
        ]

        yearly_trend = [{"year": year, "count": count} for year, count in sorted(yearly_counts.items(), reverse=True)]

        type_dist = [{"type": type_name, "count": count} for type_name, count in type_distribution.most_common()]

        status_dist = [{"status": status, "count": count} for status, count in status_distribution.most_common()]

        result = {
            "total_conversations": total_conversations,
            "time_range_days": days,
            "daily_trend": daily_trend,
            "weekly_trend": weekly_trend,
            "monthly_trend": monthly_trend,
            "yearly_trend": yearly_trend,
            "type_distribution": type_dist,
            "status_distribution": status_dist,
            "top_keywords": top_keywords,
            "timestamp": datetime.now().isoformat(),
        }

        # 写入缓存
        metrics_cache[cache_key] = result
        return result

    except Exception as e:
        logger.error(f" 获取对话分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
