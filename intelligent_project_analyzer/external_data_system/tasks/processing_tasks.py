"""
外部数据处理任务

定义向量生成、质量检查等数据处理任务
"""

from loguru import logger
import os

# 导入主Celery应用
from .sync_tasks import celery_app


@celery_app.task(name="generate_embeddings")
def generate_embeddings_task(project_id: int):
    """
    生成项目描述的向量嵌入

    Args:
        project_id: 项目ID
    """
    logger.info(f"🚀 生成向量嵌入: project_id={project_id}")

    try:
        from ..models import get_external_db, ExternalProject
        from openai import OpenAI

        # OpenAI客户端
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ OPENAI_API_KEY 未配置")
            return {"status": "error", "message": "OPENAI_API_KEY未配置"}

        client = OpenAI(api_key=api_key)

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

            # 保存到数据库（pgvector格式）
            project.description_vector = str(embedding)
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
        from ..models import get_external_db, ExternalProject, QualityIssue
        from datetime import datetime

        db = get_external_db()
        with db.get_session() as session:
            project = session.query(ExternalProject).filter(ExternalProject.id == project_id).first()

            if not project:
                return {"status": "error", "message": "项目不存在"}

            issues = []

            # 检查1: 描述缺失或过短
            if not project.description or len(project.description) < 100:
                issues.append(
                    {
                        "issue_type": "missing_description",
                        "severity": "high",
                        "description": f"描述过短: {len(project.description) if project.description else 0}字符",
                    }
                )

            # 检查2: 图片缺失
            if not project.images or len(project.images) == 0:
                issues.append({"issue_type": "missing_images", "severity": "medium", "description": "缺少项目图片"})

            # 检查3: 关键元数据缺失
            if not project.year:
                issues.append({"issue_type": "missing_year", "severity": "medium", "description": "缺少建成年份"})

            if not project.architects:
                issues.append({"issue_type": "missing_architect", "severity": "low", "description": "缺少建筑师信息"})

            # 检查4: 位置信息缺失
            if not project.location:
                issues.append({"issue_type": "missing_location", "severity": "low", "description": "缺少位置信息"})

            # 保存问题到数据库
            for issue in issues:
                quality_issue = QualityIssue(
                    project_id=project_id,
                    issue_type=issue["issue_type"],
                    severity=issue["severity"],
                    description=issue["description"],
                    detected_at=datetime.now(),
                    status="unresolved",
                )
                session.add(quality_issue)

            session.commit()

            logger.success(f"✅ 质量检查完成: {len(issues)} 个问题")
            return {"status": "success", "issues_count": len(issues), "issues": issues}

    except Exception as e:
        logger.exception(f"❌ 质量检查失败: {e}")
        return {"status": "error", "message": str(e)}


@celery_app.task(name="batch_generate_embeddings")
def batch_generate_embeddings_task(limit: int = 100):
    """
    批量生成向量嵌入（用于初始化或补充）

    Args:
        limit: 每次处理的项目数量
    """
    logger.info(f"🚀 批量生成向量嵌入: limit={limit}")

    try:
        from ..models import get_external_db, ExternalProject

        db = get_external_db()
        with db.get_session() as session:
            # 查询未生成向量的项目
            projects = (
                session.query(ExternalProject)
                .filter(ExternalProject.description_vector.is_(None))
                .filter(ExternalProject.description.isnot(None))
                .limit(limit)
                .all()
            )

            logger.info(f"📊 找到 {len(projects)} 个待处理项目")

            # 逐个生成（也可以改为并行）
            success_count = 0
            for project in projects:
                result = generate_embeddings_task(project.id)
                if result.get("status") == "success":
                    success_count += 1

            logger.success(f"✅ 批量处理完成: {success_count}/{len(projects)}")
            return {"status": "success", "processed": len(projects), "success": success_count}

    except Exception as e:
        logger.exception(f"❌ 批量生成失败: {e}")
        return {"status": "error", "message": str(e)}


__all__ = [
    "generate_embeddings_task",
    "quality_check_task",
    "batch_generate_embeddings_task",
]
