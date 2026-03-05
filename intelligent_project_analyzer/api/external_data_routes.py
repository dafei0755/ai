"""
外部数据采集API路由

提供外部数据爬虫系统的监控和管理接口
"""

from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Query
from loguru import logger
from pydantic import BaseModel

router = APIRouter(prefix="/api/external", tags=["外部数据"])


# ============================================================================
# 数据模型
# ============================================================================


class SyncHistory(BaseModel):
    """同步历史记录"""

    id: int
    source: str
    category: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    status: str  # running/completed/failed
    projects_total: int
    projects_new: int
    projects_updated: int
    projects_failed: int
    error_message: str | None = None


class SourceStats(BaseModel):
    """数据源统计"""

    source: str
    total_projects: int
    new_today: int
    avg_quality_score: float
    last_sync: datetime


class QualityIssue(BaseModel):
    """质量问题"""

    id: int
    project_id: int
    issue_type: str
    severity: str  # low/medium/high/critical
    detected_at: datetime
    resolved_at: datetime | None = None


class TriggerSyncRequest(BaseModel):
    """触发同步请求"""

    source: str
    category: str | None = None
    mode: str = "incremental"  # incremental/full


# ============================================================================
# API端点
# ============================================================================


@router.get("/sync-history", summary="获取同步历史")
async def get_sync_history(
    limit: int = Query(10, ge=1, le=100),
) -> Dict[str, Any]:
    """
    获取同步历史记录

    Args:
        limit: 返回记录数（1-100）

    Returns:
        同步历史列表
    """

    try:
        from intelligent_project_analyzer.external_data_system.spiders.spider_manager import SpiderManager

        logger.info(f"📊 获取同步历史: limit={limit}")

        manager = SpiderManager()
        history = manager.get_sync_history(limit=limit)

        return {"status": "success", "history": history}

    except Exception as e:
        logger.error(f"❌ 获取同步历史失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/source-stats", summary="获取数据源统计")
async def get_source_stats() -> Dict[str, Any]:
    """
    获取数据源统计信息

    Returns:
        数据源统计列表
    """

    try:
        from intelligent_project_analyzer.external_data_system.spiders.spider_manager import SpiderManager

        logger.info("📊 获取数据源统计")

        manager = SpiderManager()
        stats = manager.get_source_stats()

        return {"status": "success", "stats": stats}

    except Exception as e:
        logger.error(f"❌ 获取数据源统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quality-issues", summary="获取质量问题")
async def get_quality_issues(
    resolved: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
) -> Dict[str, Any]:
    """
    获取数据质量问题列表

    Args:
        resolved: 是否只显示已解决的问题
        limit: 返回记录数（1-100）

    Returns:
        质量问题列表
    """

    try:
        # TODO: 从数据库查询
        # query = session.query(QualityIssue)
        # if not resolved:
        #     query = query.filter(QualityIssue.resolved_at.is_(None))
        # issues = query.order_by(
        #     QualityIssue.detected_at.desc()
        # ).limit(limit).all()

        logger.info(f"📊 获取质量问题: resolved={resolved}, limit={limit}")

        return {"status": "success", "issues": [], "message": "后端接口待实现，请参考 LARGE_SCALE_EXTERNAL_DATA_ARCHITECTURE.md"}

    except Exception as e:
        logger.error(f"❌ 获取质量问题失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-sync", summary="触发同步任务")
async def trigger_sync(request: TriggerSyncRequest) -> Dict[str, Any]:
    """
    手动触发数据同步任务

    Args:
        request: 同步请求（数据源、模式）

    Returns:
        任务ID和状态
    """

    try:
        logger.info(f"🚀 触发同步任务: {request.source} ({request.mode})")

        # 尝试使用Celery异步任务
        try:
            from intelligent_project_analyzer.tasks.external_data_tasks import sync_external_source

            task = sync_external_source.delay(
                source=request.source, category=request.category, mode=request.mode, max_pages=20
            )
            return {"status": "success", "message": f"已触发 {request.source} 的{request.mode}同步任务（异步）", "task_id": task.id}
        except ImportError as e:
            # Celery未安装，使用同步方式
            logger.warning(f"⚠️ Celery未安装，使用同步方式执行: {e}")
            from intelligent_project_analyzer.external_data_system.spiders.spider_manager import SpiderManager

            # 注意：这会阻塞当前请求，不推荐用于大规模爬取
            manager = SpiderManager()
            success = manager.sync_source(source=request.source, category=request.category, max_pages=5)
            return {
                "status": "success" if success else "failed",
                "message": f"同步任务{'成功' if success else '失败'}（同步模式）",
                "task_id": None,
                "warning": "建议安装Celery以支持异步任务",
            }

    except Exception as e:
        logger.error(f"❌ 触发同步失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}", summary="获取项目详情")
async def get_project_detail(project_id: int) -> Dict[str, Any]:
    """
    获取外部项目的详细信息

    Args:
        project_id: 项目ID

    Returns:
        项目详情
    """

    try:
        # TODO: 从数据库查询
        # project = session.query(Project).filter(Project.id == project_id).first()
        # if not project:
        #     raise HTTPException(status_code=404, detail="项目不存在")

        logger.info(f"📊 获取项目详情: {project_id}")

        return {
            "status": "success",
            "project": None,
            "message": "后端接口待实现，请参考 LARGE_SCALE_EXTERNAL_DATA_ARCHITECTURE.md",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 获取项目详情失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard-summary", summary="获取仪表板摘要")
async def get_dashboard_summary() -> Dict[str, Any]:
    """
    获取仪表板摘要数据（用于快速概览）

    Returns:
        摘要数据
    """

    try:
        # TODO: 从数据库计算
        # total_projects = session.query(Project).count()
        # total_sources = session.query(func.count(func.distinct(Project.source))).scalar()
        # syncing_tasks = session.query(SyncHistory).filter(
        #     SyncHistory.status == 'running'
        # ).count()
        # today_new = session.query(Project).filter(
        #     Project.crawled_at >= datetime.now() - timedelta(days=1)
        # ).count()

        logger.info("📊 获取仪表板摘要")

        return {
            "status": "success",
            "summary": {
                "total_projects": 0,
                "total_sources": 0,
                "syncing_tasks": 0,
                "today_new": 0,
                "avg_quality_score": 0.0,
            },
            "message": "后端接口待实现，请参考 LARGE_SCALE_EXTERNAL_DATA_ARCHITECTURE.md",
        }

    except Exception as e:
        logger.error(f"❌ 获取仪表板摘要失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 导出路由
# ============================================================================

__all__ = ["router"]
