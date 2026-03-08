"""
外部数据同步任务

定义爬虫同步的Celery异步任务（增量更新为主）
"""

import os  # noqa: F401  kept for env usage
from datetime import datetime, timedelta

from loguru import logger


def sync_archdaily_incremental(days: int = 7):
    """
    Archdaily 增量同步任务（每周执行）

    Args:
        days: 回溯天数（默认7天）
    """
    logger.info(f"🚀 开始 Archdaily 增量同步（最近{days}天）")

    try:
        from .. import get_external_db
        from ..spiders import get_spider_manager

        manager = get_spider_manager()
        get_external_db()

        last_sync = _get_last_sync_time("archdaily")
        logger.info(f"上次同步: {last_sync}")

        # 使用 SpiderManager 统一入口
        success = manager.sync_source(
            source="archdaily",
            max_pages=5,
        )

        _log_sync_history("archdaily", 0, 0)

        status = "success" if success else "failed"
        logger.success(f"✅ Archdaily 增量同步完成，状态: {status}") if success else logger.error("❌ Archdaily 增量同步失败")

        return {"source": "archdaily", "status": status}

    except Exception as e:
        logger.error(f"❌ Archdaily 增量同步失败: {e}")
        return {"source": "archdaily", "status": "failed", "error": str(e)}


def sync_gooood_incremental(days: int = 7):
    """
    Gooood 增量同步任务（每周执行）

    Args:
        days: 回溯天数（默认7天）
    """
    logger.info(f"🚀 开始 Gooood 增量同步（最近{days}天）")

    try:
        from .. import get_external_db
        from ..spiders import get_spider_manager

        manager = get_spider_manager()
        get_external_db()

        last_sync = _get_last_sync_time("gooood")
        logger.info(f"上次同步: {last_sync}")

        success = manager.sync_source(
            source="gooood",
            max_pages=3,
        )

        _log_sync_history("gooood", 0, 0)

        status = "success" if success else "failed"
        logger.success(f"✅ Gooood 增量同步完成，状态: {status}") if success else logger.error("❌ Gooood 增量同步失败")

        return {"source": "gooood", "status": status}

    except Exception as e:
        logger.error(f"❌ Gooood 增量同步失败: {e}")
        return {"source": "gooood", "status": "failed", "error": str(e)}


def _get_last_sync_time(source: str) -> datetime:
    """获取最后同步时间"""
    from .. import get_external_db
    from ..models import SyncHistory

    db = get_external_db()

    with db.get_session() as session:
        latest = (
            session.query(SyncHistory)
            .filter(SyncHistory.source == source, SyncHistory.status == "completed")
            .order_by(SyncHistory.completed_at.desc())
            .first()
        )

        if latest:
            return latest.completed_at
        else:
            # 默认回溯7天
            return datetime.now() - timedelta(days=7)


def _save_project_if_not_exists(db, project_data) -> bool:
    """
    保存项目（如果不存在）

    Returns:
        True if saved, False if already exists
    """
    from ..models import ExternalProject

    with db.get_session() as session:
        # 检查URL是否已存在
        existing = session.query(ExternalProject).filter(ExternalProject.url == project_data.url).first()

        if existing:
            return False

        # 创建新项目
        project = ExternalProject(
            source=project_data.source,
            source_id=project_data.source_id,
            url=project_data.url,
            title=project_data.title,
            description=project_data.description,
            architects=project_data.architects,
            location=project_data.location,
            year=project_data.year,
            area_sqm=project_data.area_sqm,
            primary_category=project_data.primary_category,
            sub_categories=project_data.sub_categories,
            tags=project_data.tags,
            quality_score=_calculate_quality_score(project_data),
        )

        session.add(project)
        session.commit()

        return True


def _calculate_quality_score(project_data) -> float:
    """计算质量分数"""
    from ..utils import DataValidator

    # 转为字典
    project_dict = {
        "title": project_data.title,
        "description": project_data.description,
        "source": project_data.source,
        "source_id": project_data.source_id,
        "url": project_data.url,
        "architects": project_data.architects,
        "location": project_data.location,
        "year": project_data.year,
        "area_sqm": project_data.area_sqm,
        "images": project_data.images,
        "tags": project_data.tags,
        "categories": [project_data.primary_category] + (project_data.sub_categories or []),
    }

    return DataValidator.calculate_completeness(project_dict)


def _log_sync_history(source: str, new_count: int, total_count: int):
    """记录同步历史"""
    from .. import get_external_db
    from ..models import SyncHistory

    db = get_external_db()

    with db.get_session() as session:
        history = SyncHistory(
            source=source,
            status="completed",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            projects_total=total_count,
            projects_new=new_count,
        )

        session.add(history)
        session.commit()


__all__ = [
    "sync_archdaily_incremental",
    "sync_gooood_incremental",
]


# ========== 以下是原有的Celery任务(已集成到celery_app.py) ==========
# 保留用于向后兼容

# 使用主 celery_app.py 中的 app 实例
from ..celery_app import app as celery_app  # noqa: F401 公开给外部定时任务读取


@celery_app.task(name="sync_external_source", bind=True)
def sync_external_source(
    self, source: str, category: str | None = None, max_pages: int = 20, mode: str = "incremental"
):
    """
    同步外部数据源任务

    Args:
        source: 数据源名称（archdaily/gooood/dezeen）
        category: 分类名称（可选）
        max_pages: 每个分类最大翻页数
        mode: 同步模式（incremental/full）
    """
    logger.info(f"🚀 Celery任务开始: sync_external_source({source}, {category})")

    try:
        from ..spiders import get_spider_manager

        # 获取管理器
        manager = get_spider_manager()

        # 执行同步
        success = manager.sync_source(
            source=source,
            category=category,
            max_pages=max_pages,
        )

        if success:
            logger.success(f"✅ Celery任务完成: {source}")
            return {"status": "success", "source": source, "category": category}
        else:
            logger.error(f"❌ Celery任务失败: {source}")
            return {"status": "failed", "source": source, "error": "同步失败"}

    except Exception as e:
        logger.exception(f"❌ Celery任务异常: {e}")
        self.retry(exc=e, countdown=60, max_retries=3)


# ============================================================================
# Celery Beat定时任务配置
# ============================================================================

celery_app.conf.beat_schedule = {
    # 每天凌晨2点同步Archdaily（增量模式）
    "sync-archdaily-daily": {
        "task": "sync_external_source",
        "schedule": 3600 * 24,  # 24小时
        "args": ("archdaily",),
        "kwargs": {"mode": "incremental", "max_pages": 5},
    },
    # 每周日凌晨3点全量同步
    "sync-all-weekly": {
        "task": "sync_external_source",
        "schedule": 3600 * 24 * 7,  # 7天
        "args": ("archdaily",),
        "kwargs": {"mode": "full", "max_pages": 50},
    },
}


__all__ = [
    "celery_app",
    "sync_external_source",
]
