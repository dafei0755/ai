"""
项目发现管理器（线程安全）

替代原 ProjectIndexManager，使用统一数据库。
所有操作通过 get_session() 上下文管理器保证线程安全。
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List

from loguru import logger

from .models.external_projects import (
    ExternalProjectDatabase,
    ProjectDiscovery,
    get_external_db,
)


class ProjectDiscoveryManager:
    """线程安全的项目发现管理器"""

    def __init__(self, db: ExternalProjectDatabase | None = None):
        self.db = db or get_external_db()

    def add_project(
        self,
        source: str,
        url: str,
        source_id: str | None = None,
        title: str | None = None,
        category: str | None = None,
        sub_category: str | None = None,
        preview_image: str | None = None,
    ) -> bool:
        """
        添加项目到发现索引

        Returns:
            True=新增, False=已存在
        """
        with self.db.get_session() as session:
            existing = session.query(ProjectDiscovery).filter_by(url=url).first()
            if existing:
                return False

            project = ProjectDiscovery(
                source=source,
                source_id=source_id or self._extract_source_id(url),
                url=url,
                title=title,
                category=category,
                sub_category=sub_category,
                preview_image=preview_image,
                discovered_at=datetime.now(),
            )
            session.add(project)
            return True

    def bulk_add_projects(self, projects: List[Dict]) -> Dict[str, int]:
        """批量添加项目"""
        added = 0
        skipped = 0
        for proj in projects:
            if self.add_project(**proj):
                added += 1
            else:
                skipped += 1
        logger.info(f"批量添加: 新增 {added}, 跳过 {skipped}")
        return {"added": added, "skipped": skipped}

    def get_uncrawled_projects(
        self,
        source: str | None = None,
        category: str | None = None,
        limit: int | None = None,
    ) -> List[ProjectDiscovery]:
        """获取未爬取的项目"""
        with self.db.get_session() as session:
            query = session.query(ProjectDiscovery).filter_by(is_crawled=False)
            if source:
                query = query.filter_by(source=source)
            if category:
                query = query.filter_by(category=category)
            query = query.order_by(ProjectDiscovery.discovered_at)
            if limit:
                query = query.limit(limit)
            results = query.all()
            # Detach from session so they can be used outside the context
            session.expunge_all()
            return results

    def mark_as_crawled(self, url: str, success: bool = True, error: str | None = None):
        """标记项目为已爬取"""
        with self.db.get_session() as session:
            project = session.query(ProjectDiscovery).filter_by(url=url).first()
            if project:
                project.crawl_attempts += 1
                if success:
                    project.is_crawled = True
                    project.crawled_at = datetime.now()
                    project.last_error = None
                else:
                    project.last_error = error

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self.db.get_session() as session:
            total = session.query(ProjectDiscovery).count()
            crawled = session.query(ProjectDiscovery).filter_by(is_crawled=True).count()

            by_source = {}
            for source in ["archdaily", "gooood", "dezeen"]:
                source_total = session.query(ProjectDiscovery).filter_by(source=source).count()
                source_crawled = session.query(ProjectDiscovery).filter_by(source=source, is_crawled=True).count()
                by_source[source] = {
                    "total": source_total,
                    "crawled": source_crawled,
                    "uncrawled": source_total - source_crawled,
                }

            return {
                "total": total,
                "crawled": crawled,
                "uncrawled": total - crawled,
                "by_source": by_source,
            }

    def get_new_projects(self, source: str, since_days: int = 7) -> List[str]:
        """获取最近N天新发现的项目URL"""
        since_date = datetime.now() - timedelta(days=since_days)
        with self.db.get_session() as session:
            projects = (
                session.query(ProjectDiscovery)
                .filter(
                    ProjectDiscovery.source == source,
                    ProjectDiscovery.discovered_at >= since_date,
                )
                .all()
            )
            return [p.url for p in projects]

    def _extract_source_id(self, url: str) -> str:
        """从URL提取source_id"""
        parts = url.rstrip("/").split("/")

        if "archdaily" in url:
            for part in parts:
                if part.isdigit():
                    return part

        if "gooood" in url:
            return parts[-1].replace(".htm", "").replace(".html", "")

        if "dezeen" in url:
            return parts[-1] or parts[-2]

        return parts[-1] or parts[-2]


__all__ = ["ProjectDiscoveryManager"]
