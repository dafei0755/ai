"""会话管理 + 日志查询 + 主动学习 API"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from loguru import logger

from ..auth_middleware import require_admin

router = APIRouter()


@router.get("/sessions")
async def list_all_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status: str | None = Query(default=None),
    search: str | None = Query(default=None),
    source: str | None = Query(default=None, description="数据源: redis/archived/all"),
    admin: dict = Depends(require_admin),
):
    """
    获取所有用户的会话列表（管理员视图）

     v7.201: 合并Redis活跃会话和SQLite归档会话

    Args:
        page: 页码
        page_size: 每页数量
        status: 筛选状态
        search: 搜索关键词
        source: 数据源过滤 (redis/archived/all，默认all)
    """
    try:
        all_sessions = []

        # 1. 获取Redis活跃会话
        if source in (None, "all", "redis"):
            from ..api.server import session_manager as global_session_manager

            if global_session_manager:
                redis_sessions = await global_session_manager.get_all_sessions()
                # 标记来源
                for session in redis_sessions:
                    session["_source"] = "redis"
                all_sessions.extend(redis_sessions)
                logger.debug(f" Redis活跃会话: {len(redis_sessions)} 条")

        # 2. 获取SQLite归档会话
        if source in (None, "all", "archived"):
            from ..api.server import archive_manager

            if archive_manager:
                # 获取所有归档会话（不限用户，管理员视图）
                archived_sessions = await archive_manager.list_archived_sessions(
                    limit=10000,  # 获取足够多的数据用于分页
                    offset=0,
                    status=status,
                    user_id=None,  # 管理员查看所有用户
                )
                # 标记来源
                for session in archived_sessions:
                    session["_source"] = "archived"
                all_sessions.extend(archived_sessions)
                logger.debug(f" 归档会话: {len(archived_sessions)} 条")

        # 3. 去重（同一个session_id可能同时存在于Redis和归档中）
        seen_ids = set()
        unique_sessions = []
        for session in all_sessions:
            session_id = session.get("session_id")
            if session_id and session_id not in seen_ids:
                seen_ids.add(session_id)
                unique_sessions.append(session)
        all_sessions = unique_sessions

        # 4. 增强用户信息显示
        for session in all_sessions:
            if "username" not in session or "display_name" not in session:
                user_id = session.get("user_id", "")
                session_parts = session.get("session_id", "").split("-")
                username_fallback = session_parts[0] if session_parts else user_id

                session["username"] = session.get(
                    "username", username_fallback if username_fallback != "web_user" else "匿名用户"
                )
                session["display_name"] = session.get("display_name", session["username"])

        # 5. 状态过滤（如果source不是archived，因为archived已经在查询时过滤了）
        if status and source != "archived":
            all_sessions = [s for s in all_sessions if s.get("status") == status]

        # 6. 搜索过滤
        if search:
            search_lower = search.lower()
            all_sessions = [
                s
                for s in all_sessions
                if search_lower in str(s.get("session_id", "")).lower()
                or search_lower in str(s.get("user_id", "")).lower()
                or search_lower in str(s.get("user_input", "")).lower()
            ]

        # 7. 排序（最新的在前）
        all_sessions.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        # 8. 分页
        total = len(all_sessions)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_sessions = all_sessions[start:end]

        logger.info(
            f" 管理后台会话列表: 总计 {total} 条 (页 {page}/{(total + page_size - 1) // page_size if page_size > 0 else 0})"
        )

        return {
            "sessions": paginated_sessions,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f" 获取会话列表失败: {e}")
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
        logger.info(f" 管理员 {admin.get('username')} 请求查看会话详情: {session_id}")

        # 从 server.py 导入全局 session_manager
        from ..api.server import session_manager as global_session_manager

        if not global_session_manager:
            logger.error(" session_manager 未初始化")
            raise HTTPException(status_code=503, detail="会话管理器未初始化")

        # 获取会话数据
        logger.debug(f" 正在从 Redis 获取会话: {session_id}")
        session_data = await global_session_manager.get(session_id)

        if not session_data:
            logger.warning(f"️ 会话不存在: {session_id}")
            raise HTTPException(status_code=404, detail=f"会话 {session_id} 不存在")

        logger.success(f" 成功获取会话详情: {session_id} (数据大小: {len(str(session_data))} bytes)")

        return session_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 获取会话详情失败 ({session_id}): {type(e).__name__}: {str(e)}")
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

        logger.warning(f"️ 管理员 {admin.get('username')} 强制终止会话: {session_id}")
        return {"status": "success", "message": f"会话 {session_id} 已强制终止", "timestamp": datetime.now().isoformat()}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f" 强制终止会话失败: {e}")
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
                logger.error(f" 删除会话 {session_id} 失败: {e}")
                failed_count += 1

        logger.warning(f"️ 管理员 {admin.get('username')} 批量删除会话: " f"{deleted_count} 成功, {failed_count} 失败")

        return {
            "status": "success",
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "total_requested": len(session_ids),
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f" 批量删除会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 日志查询 API
# ============================================================================


@router.get("/logs")
async def query_logs(
    log_type: str = Query(default="server", regex="^(server|auth|errors|performance|admin_operations)$"),
    lines: int = Query(default=100, ge=1, le=1000),
    search: str | None = Query(default=None),
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
        with open(log_file, encoding="utf-8", errors="ignore") as f:
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
        logger.error(f" 查询日志失败: {e}")
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
        logger.error(f" 列出日志文件失败: {e}")
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
        logger.error(f" 获取维度学习统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
