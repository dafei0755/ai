"""
管理员后台 API 路由
提供系统监控、配置管理、会话管理、日志查询等功能

仅限管理员访问
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import psutil
from cachetools import TTLCache
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from loguru import logger

from ..services.redis_session_manager import RedisSessionManager
from ..utils.config_manager import config_manager
from .auth_middleware import require_admin
from .performance_monitor import performance_monitor

router = APIRouter(prefix="/api/admin", tags=["admin"])

# API响应缓存（5秒TTL，避免频繁计算）
metrics_cache = TTLCache(maxsize=10, ttl=5)

# 全局会话管理器实例 - 在路由函数中动态获取
session_manager = None  # 将在请求时从 server.py 获取


# ============================================================================
# 系统监控 API
# ============================================================================


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
        logger.debug("📦 返回缓存的监控数据")
        return metrics_cache[cache_key]

    try:
        # 计算实时指标 - 增加容错处理和诊断日志
        cpu_percent = 0.0
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            logger.debug(f"✅ CPU: {cpu_percent}%")
        except Exception as e:
            logger.warning(f"⚠️ CPU监控失败: {type(e).__name__}")

        memory_info = {"percent": 0, "used": 0, "total": 0}
        try:
            mem = psutil.virtual_memory()
            memory_info = {"percent": mem.percent, "used": mem.used, "total": mem.total}
            logger.debug(f"✅ 内存: {mem.percent}%")
        except Exception as e:
            logger.warning(f"⚠️ 内存监控失败: {type(e).__name__}")

        disk_info = {"percent": 0, "used": 0, "total": 0}
        try:
            # 🔧 v7.122: 增强Windows兼容性（Python 3.13 + psutil修复）
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
                        logger.debug(f"✅ 磁盘路径成功: {path}")
                        break
                    except Exception:
                        continue

                if disk is None:
                    raise RuntimeError("所有磁盘路径尝试均失败")
            else:
                disk = psutil.disk_usage("/")

            disk_info = {"percent": disk.percent, "used": disk.used, "total": disk.total}
            logger.debug(f"✅ 磁盘: {disk.percent}%")
        except Exception as e:
            logger.warning(f"⚠️ 磁盘监控失败: {type(e).__name__} - {str(e)[:50]}")
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
                logger.debug(f"✅ 活跃会话: {active_sessions}")
            else:
                logger.warning("⚠️ session_manager 未初始化")
        except Exception as e:
            logger.warning(f"⚠️ 会话监控失败: {type(e).__name__}")

        # 性能指标
        perf_stats = performance_monitor.get_stats_summary()
        logger.debug(f"✅ 性能统计: {perf_stats}")

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

    except Exception as e:
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
        logger.error(f"❌ 获取性能详情失败: {e}")
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
        logger.error(f"❌ 获取慢请求失败: {e}")
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
        logger.debug("📦 返回缓存的工具统计数据")
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

        with open(log_file, "r", encoding="utf-8") as f:
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
        logger.error(f"❌ 获取工具统计失败: {e}")
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
        logger.debug("📦 返回缓存的概念图统计数据")
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
                with open(metadata_file, "r", encoding="utf-8") as f:
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
                logger.warning(f"⚠️ 解析会话 {session_dir.name} 失败: {e}")
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
        logger.error(f"❌ 获取概念图统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversations/analytics")
async def get_conversations_analytics(
    days: int = Query(default=30, ge=1, le=365), admin: dict = Depends(require_admin)
):
    """
    获取对话分析统计

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
        logger.debug("📦 返回缓存的对话分析数据")
        return metrics_cache[cache_key]

    try:
        # 获取所有会话
        from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

        redis_manager = RedisSessionManager()

        # 确保Redis连接
        if not redis_manager.is_connected:
            await redis_manager.connect()

        all_sessions = await redis_manager.get_all_sessions()

        # 计算时间范围
        cutoff_time = datetime.now() - timedelta(days=days)

        # 统计数据容器
        import re
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
                # 简单的中文分词（提取2-4字的词汇）
                words = re.findall(r"[\u4e00-\u9fff]{2,4}", user_input)
                all_keywords.extend(words)

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
        logger.error(f"❌ 获取对话分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 配置管理 API
# ============================================================================


@router.get("/config/current")
async def get_current_config(admin: dict = Depends(require_admin)):
    """
    获取当前配置（脱敏）

    不返回敏感信息（API Key、密码等）
    """
    try:
        sanitized_config = config_manager.get_sanitized_config()
        return {"config": sanitized_config, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"❌ 获取配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/reload")
async def reload_config(admin: dict = Depends(require_admin)):
    """
    手动触发配置重载

    重新加载 .env 文件和配置对象
    """
    try:
        success = config_manager.reload()

        if success:
            logger.info(f"✅ 管理员 {admin.get('username')} 触发配置重载")
            return {"status": "success", "message": "配置已重载", "timestamp": datetime.now().isoformat()}
        else:
            raise HTTPException(status_code=500, detail="配置重载失败")

    except Exception as e:
        logger.error(f"❌ 配置重载失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/env")
async def get_env_content(admin: dict = Depends(require_admin)):
    """
    获取 .env 文件内容（脱敏）

    用于配置编辑器展示
    """
    try:
        env_path = Path(__file__).parent.parent.parent.parent / ".env"

        if not env_path.exists():
            raise HTTPException(status_code=404, detail=".env 文件不存在")

        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 脱敏处理：隐藏敏感值
        lines = []
        for line in content.split("\n"):
            if "=" in line and not line.strip().startswith("#"):
                key, value = line.split("=", 1)
                # 隐藏 API Key、密码等敏感信息
                if any(sensitive in key.upper() for sensitive in ["KEY", "SECRET", "PASSWORD", "TOKEN"]):
                    lines.append(f"{key}=***HIDDEN***")
                else:
                    lines.append(line)
            else:
                lines.append(line)

        return {"content": "\n".join(lines), "file_path": str(env_path), "timestamp": datetime.now().isoformat()}

    except Exception as e:
        logger.error(f"❌ 读取 .env 文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 会话管理 API
# ============================================================================


@router.get("/sessions")
async def list_all_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None),
    admin: dict = Depends(require_admin),
):
    """
    获取所有用户的会话列表（管理员视图）

    Args:
        page: 页码
        page_size: 每页数量
        status: 筛选状态
        search: 搜索关键词
    """
    try:
        # 从 server.py 导入全局 session_manager
        from ..api.server import session_manager as global_session_manager

        if not global_session_manager:
            return {"sessions": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}

        # 获取所有会话（不限用户）
        all_sessions = await global_session_manager.get_all_sessions()

        # 增强用户信息显示
        for session in all_sessions:
            # 如果会话中已经有 username/display_name，直接使用
            if "username" not in session or "display_name" not in session:
                user_id = session.get("user_id", "")
                # 从 session_id 提取用户标识作为fallback
                session_parts = session.get("session_id", "").split("-")
                username_fallback = session_parts[0] if session_parts else user_id

                session["username"] = session.get(
                    "username", username_fallback if username_fallback != "web_user" else "匿名用户"
                )
                session["display_name"] = session.get("display_name", session["username"])

        # 状态过滤
        if status:
            all_sessions = [s for s in all_sessions if s.get("status") == status]

        # 搜索过滤
        if search:
            search_lower = search.lower()
            all_sessions = [
                s
                for s in all_sessions
                if search_lower in str(s.get("session_id", "")).lower()
                or search_lower in str(s.get("user_id", "")).lower()
                or search_lower in str(s.get("input_text", "")).lower()
            ]

        # 排序（最新的在前）
        all_sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        # 分页
        total = len(all_sessions)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_sessions = all_sessions[start:end]

        return {
            "sessions": paginated_sessions,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ 获取会话列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sessions/{session_id}")
async def get_session_detail(session_id: str, admin: dict = Depends(require_admin)):
    """
    获取会话详细信息

    Args:
        session_id: 会话ID

    Returns:
        dict: 完整的会话数据（包括状态、输入、输出等）
    """
    try:
        logger.info(f"🔍 管理员 {admin.get('username')} 请求查看会话详情: {session_id}")

        # 从 server.py 导入全局 session_manager
        from ..api.server import session_manager as global_session_manager

        if not global_session_manager:
            logger.error("❌ session_manager 未初始化")
            raise HTTPException(status_code=503, detail="会话管理器未初始化")

        # 获取会话数据
        logger.debug(f"📦 正在从 Redis 获取会话: {session_id}")
        session_data = await global_session_manager.get(session_id)

        if not session_data:
            logger.warning(f"⚠️ 会话不存在: {session_id}")
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")

        logger.success(f"✅ 成功获取会话详情: {session_id} (数据大小: {len(str(session_data))} bytes)")

        return session_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取会话详情失败 ({session_id}): {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"内部错误: {str(e)}")


@router.post("/sessions/{session_id}/force-stop")
async def force_stop_session(session_id: str, admin: dict = Depends(require_admin)):
    """
    强制终止会话

    Args:
        session_id: 会话ID
    """
    try:
        # 从 server.py 导入全局 session_manager
        from ..api.server import session_manager as global_session_manager

        if not global_session_manager:
            raise HTTPException(status_code=503, detail="会话管理器未初始化")

        # 获取会话
        session_data = await global_session_manager.get(session_id)

        if not session_data:
            raise HTTPException(status_code=404, detail="会话不存在")

        # 更新会话状态为终止
        updates = {
            "status": "terminated",
            "terminated_at": datetime.now().isoformat(),
            "terminated_by": admin.get("username"),
        }

        await global_session_manager.update(session_id, updates)

        logger.warning(f"⚠️ 管理员 {admin.get('username')} 强制终止会话: {session_id}")
        return {"status": "success", "message": f"会话 {session_id} 已强制终止", "timestamp": datetime.now().isoformat()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 强制终止会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/sessions/batch")
async def batch_delete_sessions(session_ids: List[str], admin: dict = Depends(require_admin)):
    """
    批量删除会话

    Args:
        session_ids: 会话ID列表
    """
    try:
        # 从 server.py 导入全局 session_manager
        from ..api.server import session_manager as global_session_manager

        if not global_session_manager:
            raise HTTPException(status_code=503, detail="会话管理器未初始化")

        deleted_count = 0
        failed_count = 0

        for session_id in session_ids:
            try:
                await global_session_manager.delete_session(session_id)
                deleted_count += 1
            except Exception as e:
                logger.error(f"❌ 删除会话 {session_id} 失败: {e}")
                failed_count += 1

        logger.warning(f"⚠️ 管理员 {admin.get('username')} 批量删除会话: " f"{deleted_count} 成功, {failed_count} 失败")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "total_requested": len(session_ids),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ 批量删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 日志查询 API
# ============================================================================


@router.get("/logs")
async def query_logs(
    log_type: str = Query(default="server", regex="^(server|auth|errors|performance|admin_operations)$"),
    lines: int = Query(default=100, ge=1, le=1000),
    search: Optional[str] = Query(default=None),
    admin: dict = Depends(require_admin),
):
    """
    查询日志

    Args:
        log_type: 日志类型（server/auth/errors/performance/admin_operations）
        lines: 返回行数
        search: 搜索关键词
    """
    try:
        log_dir = Path(__file__).parent.parent.parent.parent / "logs"
        log_file_map = {
            "server": "server.log",
            "auth": "auth_service.log",
            "errors": "errors.log",
            "performance": "performance.log",
            "admin_operations": "admin_operations.log",
        }

        log_file = log_dir / log_file_map.get(log_type, "server.log")

        if not log_file.exists():
            return {
                "logs": [],
                "count": 0,
                "message": f"日志文件 {log_file.name} 不存在",
                "timestamp": datetime.now().isoformat(),
            }

        # 读取日志文件（尾部N行）
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
            all_lines = f.readlines()

        # 获取尾部N行
        log_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

        # 搜索过滤
        if search:
            log_lines = [line for line in log_lines if search.lower() in line.lower()]

        return {
            "logs": log_lines,
            "count": len(log_lines),
            "log_type": log_type,
            "file_path": str(log_file),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ 查询日志失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/files")
async def list_log_files(admin: dict = Depends(require_admin)):
    """
    列出所有日志文件
    """
    try:
        log_dir = Path(__file__).parent.parent.parent.parent / "logs"

        if not log_dir.exists():
            return {"files": [], "count": 0}

        log_files = []
        for log_file in log_dir.glob("*.log"):
            stat = log_file.stat()
            log_files.append(
                {
                    "name": log_file.name,
                    "size_mb": round(stat.st_size / (1024**2), 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                }
            )

        # 按修改时间排序
        log_files.sort(key=lambda x: x["modified"], reverse=True)

        return {"files": log_files, "count": len(log_files), "timestamp": datetime.now().isoformat()}

    except Exception as e:
        logger.error(f"❌ 列出日志文件失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 主动学习数据分析 API
# ============================================================================


@router.get("/dimension-learning/stats")
async def get_dimension_learning_stats(admin: dict = Depends(require_admin)):
    """
    获取主动学习数据统计

    返回维度选择效果、用户反馈等
    """
    try:
        # TODO: 从 Redis 读取维度学习历史数据
        # dimension_history = await redis_client.get("dimension:history:*")

        # 占位实现
        return {
            "status": "success",
            "message": "维度学习统计功能开发中",
            "placeholder_data": {"total_feedbacks": 0, "avg_score": 0, "top_dimensions": []},
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f"❌ 获取维度学习统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 系统健康检查
# ============================================================================


@router.get("/health")
async def admin_health_check(admin: dict = Depends(require_admin)):
    """
    管理员系统健康检查（详细版）

    返回更多内部状态信息
    """
    try:
        return {
            "status": "healthy",
            "admin": admin.get("username"),
            "components": {
                "api": "up",
                "redis": "up",  # TODO: 实际检查
                "config_manager": "up",
            },
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"❌ 健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 用户分析 API
# ============================================================================


@router.get("/users/analytics")
async def get_users_analytics(
    time_range: str = Query("7d", description="时间范围: 1d/7d/30d/365d"), admin: dict = Depends(require_admin)
):
    """
    获取用户分析数据

    返回：
    - 在线用户数量（按天/周/月/年统计）
    - 用户地区分布（基于session中的城市信息）
    - 用户对话数量排行（可按时间筛选）

    缓存策略：60秒TTL
    """
    cache_key = f"users_analytics_{time_range}"

    # 检查缓存
    if cache_key in metrics_cache:
        logger.debug(f"📦 返回缓存的用户分析数据: {time_range}")
        return metrics_cache[cache_key]

    try:
        # 计算时间范围
        time_ranges = {"1d": 1, "7d": 7, "30d": 30, "365d": 365}
        days = time_ranges.get(time_range, 7)
        cutoff_date = datetime.now() - timedelta(days=days)

        # 从 server.py 导入全局 session_manager
        from ..api.server import session_manager as global_session_manager

        if not global_session_manager:
            raise HTTPException(status_code=503, detail="Session manager 未初始化")

        # 获取所有会话
        all_sessions = await global_session_manager.get_all_sessions()

        # 过滤时间范围内的会话
        filtered_sessions = []
        for session in all_sessions:
            created_str = session.get("created_at")
            if created_str:
                try:
                    created_at = datetime.fromisoformat(created_str)
                    if created_at >= cutoff_date:
                        filtered_sessions.append(session)
                except:
                    continue

        # 1. 统计在线用户数量（按日期分组）
        daily_users = {}  # {date: set(user_ids)}
        weekly_users = {}  # {week_number: set(user_ids)}
        monthly_users = {}  # {month: set(user_ids)}
        yearly_users = {}  # {year: set(user_ids)}

        for session in filtered_sessions:
            user_id = session.get("user_id") or session.get("username", "guest")
            created_str = session.get("created_at")

            if not created_str:
                continue

            try:
                created_at = datetime.fromisoformat(created_str)

                # 按日统计
                date_key = created_at.strftime("%Y-%m-%d")
                if date_key not in daily_users:
                    daily_users[date_key] = set()
                daily_users[date_key].add(user_id)

                # 按周统计
                week_key = f"{created_at.year}-W{created_at.isocalendar()[1]:02d}"
                if week_key not in weekly_users:
                    weekly_users[week_key] = set()
                weekly_users[week_key].add(user_id)

                # 按月统计
                month_key = created_at.strftime("%Y-%m")
                if month_key not in monthly_users:
                    monthly_users[month_key] = set()
                monthly_users[month_key].add(user_id)

                # 按年统计
                year_key = str(created_at.year)
                if year_key not in yearly_users:
                    yearly_users[year_key] = set()
                yearly_users[year_key].add(user_id)
            except:
                continue

        # 转换为列表格式
        daily_trend = [{"date": k, "count": len(v)} for k, v in sorted(daily_users.items())]
        weekly_trend = [{"week": k, "count": len(v)} for k, v in sorted(weekly_users.items())]
        monthly_trend = [{"month": k, "count": len(v)} for k, v in sorted(monthly_users.items())]
        yearly_trend = [{"year": k, "count": len(v)} for k, v in sorted(yearly_users.items())]

        # 2. 地区分布（优先使用IP定位的metadata数据）
        region_distribution = {}
        region_coords = {}  # 存储经纬度用于地图可视化

        for session in filtered_sessions:
            metadata = session.get("metadata", {})

            # 🌍 优先使用IP定位的城市信息
            location = metadata.get("location")
            geo_info = metadata.get("geo_info", {})

            if not location or location == "未知":
                # 回退：从用户输入中检测城市（中国主要城市列表）
                user_input = session.get("user_input", "")
                cities = [
                    "北京",
                    "上海",
                    "广州",
                    "深圳",
                    "杭州",
                    "成都",
                    "重庆",
                    "武汉",
                    "西安",
                    "天津",
                    "南京",
                    "苏州",
                    "长沙",
                    "郑州",
                    "济南",
                    "青岛",
                    "厦门",
                    "福州",
                    "昆明",
                    "南宁",
                    "海口",
                    "兰州",
                    "银川",
                    "西宁",
                    "乌鲁木齐",
                    "拉萨",
                    "哈尔滨",
                    "长春",
                    "沈阳",
                    "大连",
                    "石家庄",
                    "太原",
                    "呼和浩特",
                    "合肥",
                    "南昌",
                    "贵阳",
                ]

                detected_city = None
                for city in cities:
                    if city in user_input:
                        detected_city = city
                        break

                location = detected_city or "未知地区"

            # 统计地区分布
            region_distribution[location] = region_distribution.get(location, 0) + 1

            # 收集经纬度数据（用于前端地图可视化）
            if geo_info.get("latitude") and geo_info.get("longitude"):
                if location not in region_coords:
                    region_coords[location] = {
                        "lat": geo_info["latitude"],
                        "lng": geo_info["longitude"],
                        "country": geo_info.get("country", ""),
                        "province": geo_info.get("province", ""),
                    }

        # 转换为列表格式并排序（附带经纬度信息）
        region_list = []
        for region, count in sorted(region_distribution.items(), key=lambda x: x[1], reverse=True):
            item = {"region": region, "count": count}
            if region in region_coords:
                item.update(region_coords[region])
            region_list.append(item)

        # 3. 用户对话数量排行
        user_conversation_counts = {}

        for session in filtered_sessions:
            user_id = session.get("user_id") or session.get("username", "guest")
            user_conversation_counts[user_id] = user_conversation_counts.get(user_id, 0) + 1

        # 排序并取Top 50
        user_rankings = sorted(
            [{"user_id": k, "conversation_count": v} for k, v in user_conversation_counts.items()],
            key=lambda x: x["conversation_count"],
            reverse=True,
        )[:50]

        # 构建响应
        result = {
            "status": "success",
            "time_range": time_range,
            "total_users": len(set(s.get("user_id") or s.get("username", "guest") for s in filtered_sessions)),
            "total_sessions": len(filtered_sessions),
            "date_range": {"start": cutoff_date.strftime("%Y-%m-%d"), "end": datetime.now().strftime("%Y-%m-%d")},
            "online_users": {
                "daily": daily_trend[-30:],  # 最近30天
                "weekly": weekly_trend[-12:],  # 最近12周
                "monthly": monthly_trend[-12:],  # 最近12个月
                "yearly": yearly_trend[-5:],  # 最近5年
            },
            "region_distribution": region_list,
            "user_rankings": user_rankings,
            "timestamp": datetime.now().isoformat(),
        }

        # 缓存结果（60秒）
        metrics_cache[cache_key] = result

        logger.info(f"✅ 用户分析数据生成完成: {len(filtered_sessions)} sessions, {result['total_users']} users")
        return result

    except Exception as e:
        logger.error(f"❌ 获取用户分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
