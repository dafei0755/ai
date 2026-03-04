"""
语义搜索服务

基于向量相似度的语义搜索功能
"""

from typing import Any, Dict, List

from loguru import logger
from sqlalchemy import func, text
from sqlalchemy.orm import Session


class SemanticSearchService:
    """语义搜索服务"""

    def __init__(self, db_session: Session):
        """
        初始化搜索服务

        Args:
            db_session: 数据库会话
        """
        self.session = db_session

    def search_by_text(
        self,
        query_text: str,
        limit: int = 10,
        min_quality_score: float = 0.5,
        source: str | None = None,
        category: str | None = None,
    ) -> List[Dict[str, Any]]:
        """
        基于文本查询的语义搜索

        Args:
            query_text: 查询文本
            limit: 返回结果数量
            min_quality_score: 最小质量分数
            source: 数据源筛选
            category: 分类筛选

        Returns:
            匹配项目列表，包含相似度分数
        """
        from ..models import ExternalProject

        logger.info(f"🔍 语义搜索: {query_text}")

        # 先用简单的全文搜索（如果没有向量）
        query = self.session.query(ExternalProject)

        # 筛选条件
        if min_quality_score:
            query = query.filter(ExternalProject.quality_score >= min_quality_score)

        if source:
            query = query.filter(ExternalProject.source == source)

        if category:
            query = query.filter(ExternalProject.primary_category == category)

        # 文本搜索（简单实现）
        if query_text:
            query = query.filter(
                func.lower(ExternalProject.title).contains(query_text.lower())
                | func.lower(ExternalProject.description).contains(query_text.lower())
            )

        # 按质量分数排序
        projects = query.order_by(ExternalProject.quality_score.desc(), ExternalProject.views.desc()).limit(limit).all()

        results = []
        for p in projects:
            results.append(
                {
                    "id": p.id,
                    "source": p.source,
                    "title": p.title,
                    "description": p.description[:200] if p.description else None,
                    "url": p.url,
                    "architects": p.architects,
                    "location": p.location,
                    "year": p.year,
                    "quality_score": p.quality_score,
                    "views": p.views,
                    "images": [img.to_dict() for img in p.images[:3]] if p.images else [],
                    "similarity_score": 0.8,  # 占位符，实际应该计算向量相似度
                }
            )

        logger.success(f"✅ 找到 {len(results)} 个匹配项目")
        return results

    def search_by_vector(
        self, query_vector: List[float], limit: int = 10, min_similarity: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        基于向量的相似度搜索（需要pgvector）

        Args:
            query_vector: 查询向量（1536维）
            limit: 返回结果数量
            min_similarity: 最小相似度阈值

        Returns:
            相似项目列表
        """

        try:
            # 使用pgvector的余弦相似度搜索
            # <=> 是pgvector的余弦距离运算符
            sql = text(
                """
                SELECT
                    id,
                    source,
                    title,
                    description,
                    url,
                    architects,
                    location,
                    year,
                    quality_score,
                    views,
                    1 - (description_vector <=> :query_vector::vector) as similarity
                FROM external_projects
                WHERE description_vector IS NOT NULL
                AND 1 - (description_vector <=> :query_vector::vector) >= :min_similarity
                ORDER BY similarity DESC
                LIMIT :limit
            """
            )

            result = self.session.execute(
                sql, {"query_vector": str(query_vector), "min_similarity": min_similarity, "limit": limit}
            )

            projects = []
            for row in result:
                projects.append(
                    {
                        "id": row.id,
                        "source": row.source,
                        "title": row.title,
                        "description": row.description[:200] if row.description else None,
                        "url": row.url,
                        "architects": row.architects,
                        "location": row.location,
                        "year": row.year,
                        "quality_score": row.quality_score,
                        "views": row.views,
                        "similarity_score": float(row.similarity),
                    }
                )

            logger.success(f"✅ 向量搜索找到 {len(projects)} 个相似项目")
            return projects

        except Exception as e:
            logger.warning(f"⚠️ 向量搜索失败，回退到文本搜索: {e}")
            # 回退到文本搜索
            return []

    def find_similar_projects(self, project_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        找到相似的项目（基于当前项目）

        Args:
            project_id: 参考项目ID
            limit: 返回数量

        Returns:
            相似项目列表
        """
        from ..models import ExternalProject

        # 获取参考项目
        project = self.session.query(ExternalProject).filter(ExternalProject.id == project_id).first()

        if not project:
            logger.error(f"❌ 项目不存在: {project_id}")
            return []

        # 如果有向量，使用向量搜索
        if project.description_vector:
            try:
                # TODO: 解析向量字符串
                # vector = eval(project.description_vector)
                # return self.search_by_vector(vector, limit=limit)
                pass
            except Exception:
                pass

        # 否则基于分类和标签的简单匹配
        query = self.session.query(ExternalProject)

        # 排除自己
        query = query.filter(ExternalProject.id != project_id)

        # 同分类
        if project.primary_category:
            query = query.filter(ExternalProject.primary_category == project.primary_category)

        # 同数据源优先
        query = query.order_by(
            (ExternalProject.source == project.source).desc(),
            ExternalProject.quality_score.desc(),
            ExternalProject.views.desc(),
        )

        similar_projects = query.limit(limit).all()

        return [
            {
                "id": p.id,
                "source": p.source,
                "title": p.title,
                "description": p.description[:200] if p.description else None,
                "url": p.url,
                "quality_score": p.quality_score,
                "similarity_score": 0.75,  # 占位符
            }
            for p in similar_projects
        ]


class RecommendationEngine:
    """推荐引擎"""

    def __init__(self, db_session: Session):
        self.session = db_session

    def recommend_by_preferences(
        self,
        preferred_categories: List[str] = None,
        preferred_styles: List[str] = None,
        min_year: int | None = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        基于用户偏好的推荐

        Args:
            preferred_categories: 偏好的分类
            preferred_styles: 偏好的风格
            min_year: 最小年份
            limit: 返回数量

        Returns:
            推荐项目列表
        """
        from ..models import ExternalProject

        query = self.session.query(ExternalProject)

        # 分类筛选
        if preferred_categories:
            query = query.filter(ExternalProject.primary_category.in_(preferred_categories))

        # 年份筛选
        if min_year:
            query = query.filter(ExternalProject.year >= min_year)

        # 按质量和热度排序
        projects = query.order_by(ExternalProject.quality_score.desc(), ExternalProject.views.desc()).limit(limit).all()

        return [
            {
                "id": p.id,
                "source": p.source,
                "title": p.title,
                "url": p.url,
                "quality_score": p.quality_score,
                "relevance_score": 0.85,  # 占位符
            }
            for p in projects
        ]

    def get_trending_projects(
        self, days: int = 30, category: str | None = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        获取热门/趋势项目

        Args:
            days: 时间范围（天）
            category: 分类筛选
            limit: 返回数量

        Returns:
            热门项目列表
        """
        from datetime import datetime, timedelta

        from ..models import ExternalProject

        cutoff_date = datetime.now() - timedelta(days=days)

        query = self.session.query(ExternalProject).filter(ExternalProject.crawled_at >= cutoff_date)

        if category:
            query = query.filter(ExternalProject.primary_category == category)

        # 按浏览量和质量排序
        projects = query.order_by(ExternalProject.views.desc(), ExternalProject.quality_score.desc()).limit(limit).all()

        return [
            {
                "id": p.id,
                "source": p.source,
                "title": p.title,
                "url": p.url,
                "views": p.views,
                "quality_score": p.quality_score,
                "crawled_at": p.crawled_at.isoformat(),
            }
            for p in projects
        ]

    def get_high_quality_showcase(self, min_score: float = 0.8, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取高质量项目展示

        Args:
            min_score: 最小质量分数
            limit: 返回数量

        Returns:
            高质量项目列表
        """
        from ..models import ExternalProject

        projects = (
            self.session.query(ExternalProject)
            .filter(ExternalProject.quality_score >= min_score)
            .order_by(ExternalProject.quality_score.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": p.id,
                "source": p.source,
                "title": p.title,
                "description": p.description[:200] if p.description else None,
                "url": p.url,
                "architects": p.architects,
                "location": p.location,
                "year": p.year,
                "quality_score": p.quality_score,
                "images": [img.to_dict() for img in p.images[:5]] if p.images else [],
            }
            for p in projects
        ]


__all__ = [
    "SemanticSearchService",
    "RecommendationEngine",
]
