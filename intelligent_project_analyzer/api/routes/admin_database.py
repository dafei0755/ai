"""数据库监控与维护 + 能力边界详情 API"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from ..auth_middleware import require_admin

router = APIRouter()


# ============================================================================
# 数据库监控与维护 API (v7.200)
# ============================================================================


@router.get("/database/stats")
async def get_database_stats(_admin=Depends(require_admin)):
    """
    获取数据库统计信息

    返回：
    - file_size_mb: 数据库文件大小（MB）
    - total_records: 总记录数
    - status_distribution: 状态分布
    - avg_size_mb: 平均记录大小（MB）
    - health_status: 健康状态（HEALTHY/WARNING/CRITICAL）
    """
    try:
        from intelligent_project_analyzer.services.session_archive_manager import (
            get_archive_manager,
        )

        manager = get_archive_manager()
        stats = await manager.get_database_stats()

        return {
            "status": "success",
            "data": stats,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f" 获取数据库统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database/health")
async def get_database_health(_admin=Depends(require_admin)):
    """
    数据库健康检查（带阈值警告）

    返回：
    - health_status: HEALTHY/WARNING/CRITICAL
    - alerts: 警告信息列表
    - recommendations: 维护建议
    """
    try:
        from intelligent_project_analyzer.services.session_archive_manager import (
            get_archive_manager,
        )

        manager = get_archive_manager()
        stats = await manager.get_database_stats()

        # 兼容处理：优先使用 file_size_mb，否则使用 size_mb
        file_size_mb = stats.get("file_size_mb") or stats.get("size_mb", 0)
        health_status = stats.get("health_status", "UNKNOWN").upper()
        total_records = stats.get("total_records") or stats.get("total_sessions", 0)

        # 生成警告和建议
        alerts = []
        recommendations = []

        if health_status == "CRITICAL":
            alerts.append(
                {
                    "level": "critical",
                    "message": f"数据库大小已达 {file_size_mb:.2f} MB，超过50GB阈值，严重影响性能！",
                }
            )
            recommendations.append("立即执行归档：将旧会话导出到冷存储")
            recommendations.append("执行VACUUM压缩：释放未使用的空间")
            recommendations.append("清理失败会话：删除90天前的失败记录")

        elif health_status == "WARNING":
            alerts.append(
                {
                    "level": "warning",
                    "message": f"数据库大小为 {file_size_mb:.2f} MB，已超过10GB，建议维护",
                }
            )
            recommendations.append("考虑归档90天前的旧会话")
            recommendations.append("定期执行VACUUM压缩")

        else:
            alerts.append(
                {
                    "level": "info",
                    "message": f"数据库健康状态良好（{file_size_mb:.2f} MB）",
                }
            )

        return {
            "status": "success",
            "data": {
                "health_status": health_status,
                "file_size_mb": file_size_mb,
                "total_records": total_records,
                "alerts": alerts,
                "recommendations": recommendations,
                "thresholds": {
                    "healthy": "< 10 GB",
                    "warning": "10 GB - 50 GB",
                    "critical": "> 50 GB",
                },
            },
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f" 数据库健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/database/vacuum")
async def vacuum_database(_admin=Depends(require_admin)):
    """
    执行数据库VACUUM压缩

    释放未使用空间，优化查询性能
    """
    try:
        from intelligent_project_analyzer.services.session_archive_manager import (
            get_archive_manager,
        )

        manager = get_archive_manager()
        result = await manager.vacuum_database()

        return {
            "status": "success",
            "data": result,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f" 数据库VACUUM失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/database/archive")
async def archive_old_sessions(
    days: int = Query(90, ge=30, le=365, description="归档天数阈值"),
    dry_run: bool = Query(True, description="是否模拟运行（不实际删除）"),
    _admin=Depends(require_admin),
):
    """
    归档旧会话到冷存储

    将N天前的会话导出为JSON文件，并从数据库删除

    参数：
    - days: 归档天数阈值（默认90天）
    - dry_run: 是否模拟运行（默认true，不实际删除）
    """
    try:
        from intelligent_project_analyzer.services.session_archive_manager import (
            get_archive_manager,
        )

        manager = get_archive_manager()
        result = await manager.archive_old_sessions_to_cold_storage(days=days, dry_run=dry_run)

        return {
            "status": "success",
            "data": result,
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as e:
        logger.error(f" 归档旧会话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capability-boundary/violations")
async def get_capability_boundary_violations(
    node: str | None = Query(None), limit: int = Query(100, le=500), _admin=Depends(require_admin)
):
    """
    获取能力边界违规详细记录

    Args:
        node: 节点名称筛选（可选）
        limit: 返回记录数限制

    Returns:
        违规记录列表
    """
    try:
        # TODO: 从数据库查询实际记录
        logger.info(f" [能力边界监控] 获取违规记录，节点: {node}, 限制: {limit}")

        return {"violations": [], "total": 0, "node_filter": node, "limit": limit}

    except Exception as e:
        logger.error(f" [能力边界监控] 获取违规记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
