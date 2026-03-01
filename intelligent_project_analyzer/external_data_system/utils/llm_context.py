"""
LLM上下文提供器 (RAG)

为LLM提供相关案例作为上下文，增强生成质量
"""

from typing import List, Dict, Any
from loguru import logger


class ProjectContextProvider:
    """项目案例上下文提供器"""

    def __init__(self, db):
        """
        初始化上下文提供器

        Args:
            db: ExternalProjectDatabase 实例
        """
        self.db = db

    def get_context_for_query(self, query: str, max_projects: int = 5, min_quality: float = 0.7) -> Dict[str, Any]:
        """
        根据查询获取相关项目作为上下文

        Args:
            query: 用户查询（如"现代住宅设计"）
            max_projects: 最多返回项目数
            min_quality: 最低质量分数

        Returns:
            包含项目列表和格式化文本的字典
        """
        from ..utils import SemanticSearchService

        logger.info(f"🔍 获取LLM上下文：{query}")

        # 使用语义搜索查找相关项目
        with self.db.get_session() as session:
            search_service = SemanticSearchService(session)

            projects = search_service.search_by_text(
                query_text=query, limit=max_projects, min_quality_score=min_quality
            )

        if not projects:
            logger.warning("⚠️ 未找到相关项目")
            return {"projects": [], "context_text": "", "project_count": 0}

        # 格式化为LLM可读文本
        context_text = self._format_context(projects)

        logger.success(f"✅ 找到 {len(projects)} 个相关项目")

        return {"projects": projects, "context_text": context_text, "project_count": len(projects)}

    def get_context_for_style(self, style: str, project_type: str = None, max_projects: int = 5) -> Dict[str, Any]:
        """
        根据风格获取项目案例

        Args:
            style: 风格（如'modern', 'minimalist'）
            project_type: 项目类型（如'residential'）
            max_projects: 最多返回项目数

        Returns:
            上下文字典
        """
        from ..models import ExternalProject

        logger.info(f"🎨 获取风格上下文：{style} ({project_type or 'all types'})")

        with self.db.get_session() as session:
            query = session.query(ExternalProject).filter(ExternalProject.quality_score >= 0.7)

            # 按风格筛选（标签包含）
            if style:
                # JSONB contains 查询（PostgreSQL GIN 索引支持）
                query = query.filter(ExternalProject.tags.contains([style.lower()]))

            # 按类型筛选
            if project_type:
                query = query.filter(ExternalProject.primary_category == project_type)

            # 排序并限制数量
            projects = query.order_by(ExternalProject.quality_score.desc()).limit(max_projects).all()

            project_dicts = [self._project_to_dict(p) for p in projects]

        context_text = self._format_context(project_dicts)

        return {"projects": project_dicts, "context_text": context_text, "project_count": len(project_dicts)}

    def get_context_for_location(self, city: str = None, country: str = None, max_projects: int = 5) -> Dict[str, Any]:
        """
        根据地点获取项目案例

        Args:
            city: 城市
            country: 国家
            max_projects: 最多返回项目数

        Returns:
            上下文字典
        """
        from ..models import ExternalProject

        logger.info(f"📍 获取地点上下文：{city or ''}, {country or ''}")

        with self.db.get_session() as session:
            query = session.query(ExternalProject).filter(ExternalProject.quality_score >= 0.7)

            # 位置筛选（需要JSON query支持）
            # 简化版：通过description文本搜索
            if city:
                query = query.filter(ExternalProject.description.contains(city))

            if country:
                query = query.filter(ExternalProject.description.contains(country))

            projects = query.order_by(ExternalProject.quality_score.desc()).limit(max_projects).all()

            project_dicts = [self._project_to_dict(p) for p in projects]

        context_text = self._format_context(project_dicts)

        return {"projects": project_dicts, "context_text": context_text, "project_count": len(project_dicts)}

    def _format_context(self, projects: List[Dict[str, Any]]) -> str:
        """
        将项目列表格式化为LLM可读的上下文文本

        Args:
            projects: 项目列表

        Returns:
            格式化的文本
        """
        if not projects:
            return ""

        context_parts = ["# 相关建筑案例参考\n", f"以下是 {len(projects)} 个相关建筑项目案例，可作为设计参考：\n"]

        for i, project in enumerate(projects, 1):
            # 基本信息
            title = project.get("title", "Untitled")
            description = project.get("description", "")[:300]  # 限制长度

            # 元数据
            architects = project.get("architects", [])
            architect_str = architects[0].get("name", "Unknown") if architects else "Unknown"

            location = project.get("location", {})
            location_str = f"{location.get('city', '')}, {location.get('country', '')}".strip(", ")

            year = project.get("year", "N/A")
            area = project.get("area_sqm")
            area_str = f"{area}㎡" if area else "N/A"

            # 格式化单个项目
            context_parts.append(f"\n## 案例 {i}: {title}\n")
            context_parts.append(f"- **建筑师**: {architect_str}\n")
            context_parts.append(f"- **位置**: {location_str}\n")
            context_parts.append(f"- **年份**: {year}\n")
            context_parts.append(f"- **面积**: {area_str}\n")

            if description:
                context_parts.append(f"- **简介**: {description}...\n")

            # 分类标签
            categories = project.get("categories", [])
            if categories:
                context_parts.append(f"- **分类**: {', '.join(categories)}\n")

            # 设计特点（从标签提取）
            tags = project.get("tags", [])
            if tags:
                context_parts.append(f"- **特点**: {', '.join(tags[:5])}\n")

        return "".join(context_parts)

    def _project_to_dict(self, project) -> Dict[str, Any]:
        """将数据库模型转为字典"""
        return {
            "id": project.id,
            "title": project.title,
            "description": project.description,
            "url": project.url,
            "architects": project.architects or [],
            "location": project.location or {},
            "year": project.year,
            "area_sqm": project.area_sqm,
            "primary_category": project.primary_category,
            "categories": [project.primary_category] if project.primary_category else [],
            "tags": project.tags or [],
            "quality_score": project.quality_score,
        }


class TrendAnalyzer:
    """趋势分析器"""

    def __init__(self, db):
        self.db = db

    def analyze_style_trends(self, days: int = 90) -> Dict[str, Any]:
        """
        分析设计风格趋势

        Args:
            days: 分析最近N天的数据

        Returns:
            趋势分析结果
        """
        from datetime import datetime, timedelta
        from collections import Counter
        from ..models import ExternalProject

        logger.info(f"📈 分析最近 {days} 天的风格趋势")

        cutoff_date = datetime.now() - timedelta(days=days)

        with self.db.get_session() as session:
            # 查询最近的项目
            projects = session.query(ExternalProject).filter(ExternalProject.crawled_at >= cutoff_date).all()

            # 统计标签出现频率
            tag_counter = Counter()
            category_counter = Counter()

            for project in projects:
                if project.tags:
                    tag_counter.update(project.tags)

                if project.primary_category:
                    category_counter[project.primary_category] += 1

            # 获取Top 10
            top_tags = tag_counter.most_common(10)
            top_categories = category_counter.most_common(10)

            return {
                "period_days": days,
                "total_projects": len(projects),
                "top_styles": [
                    {"name": tag, "count": count, "percentage": count / len(projects) * 100} for tag, count in top_tags
                ],
                "top_categories": [
                    {"name": cat, "count": count, "percentage": count / len(projects) * 100}
                    for cat, count in top_categories
                ],
            }

    def get_popular_projects(self, days: int = 30, limit: int = 20) -> List[Dict[str, Any]]:
        """
        获取热门项目

        Args:
            days: 时间范围
            limit: 返回数量

        Returns:
            热门项目列表
        """
        from ..utils import RecommendationEngine

        logger.info(f"🔥 获取最近 {days} 天的热门项目")

        with self.db.get_session() as session:
            engine = RecommendationEngine(session)
            projects = engine.get_trending_projects(days=days, limit=limit)

        return projects


__all__ = [
    "ProjectContextProvider",
    "TrendAnalyzer",
]
