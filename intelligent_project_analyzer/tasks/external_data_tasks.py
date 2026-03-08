"""
Celery异步任务

定义外部数据同步的异步任务
"""

import os

from celery import Celery
from loguru import logger

# Celery配置
celery_app = Celery(
    "external_data_tasks",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600 * 2,  # 2小时超时
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)


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
        from intelligent_project_analyzer.external_data_system.spiders.spider_manager import (
            SpiderManager,
        )

        # 创建管理器
        manager = SpiderManager()

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


@celery_app.task(name="generate_embeddings")
def generate_embeddings_task(project_id: int):
    """
    生成项目描述的向量嵌入

    Args:
        project_id: 项目ID
    """
    logger.info(f"🚀 生成向量嵌入: project_id={project_id}")

    try:
        import os

        from openai import OpenAI

        from intelligent_project_analyzer.external_data_system.models.external_projects import (
            ExternalProject,
            get_external_db,
        )

        # OpenAI客户端
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # 查询项目
        db = get_external_db()
        with db.get_session() as session:
            project = session.query(ExternalProject).filter(ExternalProject.id == project_id).first()

            if not project:
                logger.error(f"❌ 项目不存在: {project_id}")
                return {"status": "error", "message": "项目不存在"}

            if not project.description:
                logger.warning(f"⚠️ 项目无描述: {project_id}")
                return {"status": "skipped", "message": "项目无描述"}

            # 生成嵌入
            response = client.embeddings.create(
                model="text-embedding-3-small", input=project.description[:8000]  # 限制长度
            )

            embedding = response.data[0].embedding

            # 保存到数据库
            project.description_vector = str(embedding)  # PostgreSQL pgvector格式
            session.commit()

            logger.success(f"✅ 向量嵌入已生成: project_id={project_id}")
            return {"status": "success", "project_id": project_id}

    except Exception as e:
        logger.exception(f"❌ 向量嵌入生成失败: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(name="quality_check")
def quality_check_task(project_id: int):
    """
    执行数据质量检查

    Args:
        project_id: 项目ID
    """
    logger.info(f"🚀 质量检查: project_id={project_id}")

    try:
        from datetime import datetime

        from intelligent_project_analyzer.external_data_system.models.external_projects import (
            ExternalProject,
            QualityIssue,
            get_external_db,
        )

        db = get_external_db()
        with db.get_session() as session:
            project = session.query(ExternalProject).filter(ExternalProject.id == project_id).first()

            if not project:
                return {"status": "error", "message": "项目不存在"}

            issues = []

            # 检查1: 描述缺失或过短
            if not project.description or len(project.description) < 100:
                issues.append({"issue_type": "missing_description", "severity": "high"})

            # 检查2: 图片缺失
            if not project.images or len(project.images) == 0:
                issues.append({"issue_type": "missing_images", "severity": "medium"})

            # 检查3: 关键元数据缺失
            if not project.year:
                issues.append({"issue_type": "missing_year", "severity": "medium"})

            if not project.architects:
                issues.append({"issue_type": "missing_architect", "severity": "low"})

            # 保存问题
            for issue in issues:
                quality_issue = QualityIssue(
                    project_id=project_id,
                    issue_type=issue["issue_type"],
                    severity=issue["severity"],
                    detected_at=datetime.now(),
                )
                session.add(quality_issue)

            logger.success(f"✅ 质量检查完成: {len(issues)} 个问题")
            return {"status": "success", "issues_count": len(issues)}

    except Exception as e:
        logger.exception(f"❌ 质量检查失败: {e}")
        return {"status": "error", "message": str(e)}


# ============================================================================
# Celery Beat定时任务配置
# ============================================================================

celery_app.conf.beat_schedule = {
    # 每天凌晨2点同步Archdaily
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


# ============================================================================
# 导出
# ============================================================================

__all__ = ["celery_app", "sync_external_source", "generate_embeddings_task", "quality_check_task"]
