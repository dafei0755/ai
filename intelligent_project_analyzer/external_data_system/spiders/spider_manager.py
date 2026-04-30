"""
爬虫管理器

统一管理多个数据源的爬虫，提供：
- 爬虫注册与调度
- 数据存储到数据库
- 同步历史记录
- 质量评分
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger

# checkpoint 文件路径（项目根目录/data/crawl_checkpoints.json）
_CHECKPOINT_FILE = Path(__file__).parents[4] / "data" / "crawl_checkpoints.json"
# 网站分类总量缓存（由爬虫自动检测更新）
_SITE_TOTALS_FILE = Path(__file__).parents[4] / "data" / "category_site_totals.json"

from .base_spider import BaseSpider, ProjectData
from ..models.external_projects import (
    ExternalProject, ExternalProjectImage, SyncHistory, QualityIssue,
    get_external_db, ExternalProjectDatabase
)

# PostgreSQL upsert 支持
from sqlalchemy.dialects.postgresql import insert as pg_insert


class SpiderManager:
    """爬虫管理器"""
    
    def __init__(self, db: Optional[ExternalProjectDatabase] = None):
        """
        初始化管理器
        
        Args:
            db: 数据库实例（可选，默认使用全局实例）
        """
        self.db = db or get_external_db()
        self.spiders: Dict[str, BaseSpider] = {}
        
        logger.info("✅ SpiderManager已初始化")

    def get_known_urls(self, source: str, category: Optional[str] = None) -> set:
        """
        获取数据库中已知的URL集合（用于增量去重）

        Args:
            source: 数据源名称
            category: 可选分类过滤

        Returns:
            已知URL的集合
        """
        with self.db.get_session() as session:
            query = session.query(ExternalProject.url).filter(
                ExternalProject.source == source
            )
            if category:
                query = query.filter(ExternalProject.primary_category == category)
            rows = query.all()
            return {row.url for row in rows}

    def get_latest_publish_date(self, source: str) -> Optional[datetime]:
        """
        获取该数据源最新的发布日期（用于增量判断截止点）

        Returns:
            最新发布日期，若无记录返回 None
        """
        from sqlalchemy import func
        with self.db.get_session() as session:
            result = session.query(
                func.max(ExternalProject.publish_date)
            ).filter(
                ExternalProject.source == source,
                ExternalProject.publish_date.isnot(None)
            ).scalar()
            return result

    # ========================================================================
    # Checkpoint 读写（data/crawl_checkpoints.json）
    # ========================================================================

    def _load_checkpoints(self, source: str) -> Dict[str, str]:
        """读取指定数据源的所有分类 checkpoint。
        返回 {分类名: 上次第1页第1条URL}，无记录则返回 {}。
        """
        try:
            if _CHECKPOINT_FILE.exists():
                data = json.loads(_CHECKPOINT_FILE.read_text(encoding="utf-8"))
                return data.get(source, {})
        except Exception as e:
            logger.warning(f"读取 checkpoint 文件失败，视为首次运行: {e}")
        return {}

    def _save_checkpoints(self, source: str, checkpoints: Dict[str, str]) -> None:
        """将分类 checkpoint 写回文件（原子更新，不影响其他数据源）。"""
        try:
            _CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
            if _CHECKPOINT_FILE.exists():
                data = json.loads(_CHECKPOINT_FILE.read_text(encoding="utf-8"))
            else:
                data = {}
            data[source] = checkpoints
            _CHECKPOINT_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"写入 checkpoint 文件失败: {e}")

    def _load_site_totals(self, source: str) -> Dict[str, int]:
        """读取爬虫自动检测的分类总量缓存。"""
        try:
            if _SITE_TOTALS_FILE.exists():
                data = json.loads(_SITE_TOTALS_FILE.read_text(encoding="utf-8"))
                return {k: v for k, v in data.get(source, {}).items() if k != "_updated_at"}
        except Exception as e:
            logger.warning(f"读取 site_totals 失败: {e}")
        return {}

    def _save_site_totals(self, source: str, totals: Dict[str, int]) -> None:
        """保存爬虫自动检测到的分类总量（附写入时间供前端判断新鲜度）。"""
        try:
            _SITE_TOTALS_FILE.parent.mkdir(parents=True, exist_ok=True)
            if _SITE_TOTALS_FILE.exists():
                data = json.loads(_SITE_TOTALS_FILE.read_text(encoding="utf-8"))
            else:
                data = {}
            existing = data.get(source, {})
            existing.update(totals)
            existing["_updated_at"] = datetime.now().isoformat()
            data[source] = existing
            _SITE_TOTALS_FILE.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            logger.debug(f"site_totals 已更新: {source} ({len(totals)} 个分类)")
        except Exception as e:
            logger.error(f"写入 site_totals 失败: {e}")

    def register_spider(self, spider: BaseSpider):
        """
        注册爬虫
        
        Args:
            spider: 爬虫实例
        """
        source = spider.get_name()
        self.spiders[source] = spider
        logger.info(f"✅ 已注册爬虫: {source}")
    
    def get_spider(self, source: str) -> Optional[BaseSpider]:
        """
        获取爬虫实例
        
        Args:
            source: 数据源名称
        
        Returns:
            爬虫实例
        """
        spider = self.spiders.get(source)
        if not spider:
            logger.error(f"❌ 爬虫未注册: {source}")
            return None
        
        return spider
    
    def sync_source(
        self,
        source: str,
        category: Optional[str] = None,
        max_pages: int = 500,
        max_items: Optional[int] = None,
    ) -> bool:
        """
        同步单个数据源（checkpoint 驱动，无需区分全量/增量）。

        - 首次运行：checkpoints 为空 → 自动爬完全部历史
        - 后续运行：加载 checkpoint stop_url → 仅爬到该 URL 为止（只取新内容）

        Args:
            source:     数据源名称（如 'gooood'）
            category:   分类名称（不指定则爬取所有分类）
            max_pages:  每个分类最多翻页数（保底上限，正常由 stop_url 决定停止）
            max_items:  本次最多入库条数（None=不限）

        Returns:
            是否成功
        """
        logger.info(f"🚀 开始同步: {source}")

        # 读取本数据源的全部 checkpoint
        checkpoints = self._load_checkpoints(source)
        new_checkpoints: Dict[str, str] = dict(checkpoints)

        # 创建同步历史记录
        with self.db.get_session() as session:
            sync_record = SyncHistory(
                source=source,
                category=category,
                started_at=datetime.now(),
                status='running'
            )
            session.add(sync_record)
            session.flush()
            sync_id = sync_record.id

        try:
            spider = self.get_spider(source)
            if not spider:
                raise Exception(f"爬虫未找到: {source}")

            with spider:
                if category:
                    categories = {category: spider.get_categories().get(category)}
                else:
                    categories = spider.get_categories()

                if not categories:
                    raise Exception(f"未找到分类: {source}")

                total_projects = 0
                new_projects = 0
                updated_projects = 0
                failed_projects = 0
                detected_totals: Dict[str, int] = {}  # 本次从哨兵中收集到的 site_total

                for cat_name, cat_url in categories.items():
                    if cat_url is None:
                        logger.warning(f"⚠️ 分类URL为空: {cat_name}")
                        continue

                    stop_url = checkpoints.get(cat_name)
                    label = "有 stop_url" if stop_url else "首次（无 checkpoint）"
                    logger.info(f"📂 分类: {cat_name}  [{label}]")

                    # crawl_category 返回 URL 列表，最后一项为哨兵 "__checkpoint__:<url>"
                    raw_urls = spider.crawl_category(
                        cat_url,
                        max_pages=max_pages,
                        stop_url=stop_url,
                    )

                    # 剔离哨兵并更新 checkpoint。
                    # 哨兵格式: "__checkpoint__:<first_url>[|total:<N>]"
                    project_urls: List[str] = []
                    for u in raw_urls:
                        if u.startswith("__checkpoint__:"):
                            payload = u[len("__checkpoint__:"):]
                            # 解析可选的 |total:<N>
                            if "|total:" in payload:
                                first_u, total_s = payload.split("|total:", 1)
                                try:
                                    detected_totals[cat_name] = int(total_s)
                                except ValueError:
                                    pass
                                new_checkpoints[cat_name] = first_u
                            else:
                                new_checkpoints[cat_name] = payload
                        else:
                            project_urls.append(u)

                    logger.info(f"  待处理: {len(project_urls)} 条")

                    for i, url in enumerate(project_urls, 1):
                        if max_items is not None and total_projects >= max_items:
                            logger.info(f"  已达 max_items={max_items}，停止")
                            break
                        try:
                            logger.info(f"  [{i}/{len(project_urls)}] {url}")
                            project_data = spider.parse_project_page(url)
                            if not project_data:
                                failed_projects += 1
                                continue
                            if not project_data.validate():
                                failed_projects += 1
                                logger.warning("  ⚠️ 数据验证失败")
                                self._create_quality_issue(project_data.url, "validation_failed", "high")
                                continue
                            created = self._save_project(project_data)
                            if created:
                                new_projects += 1
                            else:
                                updated_projects += 1
                            total_projects += 1
                        except Exception as e:
                            failed_projects += 1
                            logger.error(f"  ❌ 爬取失败: {url} - {e}")

                # 所有分类完成后保存 checkpoint
                self._save_checkpoints(source, new_checkpoints)
                # 保存本次自动检测到的分类总量
                if detected_totals:
                    self._save_site_totals(source, detected_totals)

                with self.db.get_session() as session:
                    sync_record = session.query(SyncHistory).filter(SyncHistory.id == sync_id).first()
                    sync_record.completed_at = datetime.now()
                    sync_record.status = 'completed'
                    sync_record.projects_total = total_projects
                    sync_record.projects_new = new_projects
                    sync_record.projects_updated = updated_projects
                    sync_record.projects_failed = failed_projects

                logger.success(f"✅ 同步完成: {source}")
                logger.info(
                    f"📊 总计: {total_projects}  新增: {new_projects}  "
                    f"更新: {updated_projects}  失败: {failed_projects}"
                )
                return True

        except Exception as e:
            with self.db.get_session() as session:
                sync_record = session.query(SyncHistory).filter(SyncHistory.id == sync_id).first()
                sync_record.completed_at = datetime.now()
                sync_record.status = 'failed'
                sync_record.error_message = str(e)
            logger.error(f"❌ 同步失败: {source} - {e}")
            return False
    
    def _save_project(self, project_data: ProjectData) -> bool:
        """
        保存项目到 PostgreSQL（原子 upsert，无锁等待，高并发友好）

        Returns:
            是否新创建（True=新建，False=更新）
        """
        return self._save_project_pg(project_data)

    def _save_project_pg(self, project_data: ProjectData) -> bool:
        """PostgreSQL 原子 upsert（无锁等待，高并发友好）"""
        values = {
            'source': project_data.source,
            'source_id': project_data.source_id,
            'url': project_data.url,
            'title': project_data.title,
            'description': project_data.description,
            'architects': project_data.architects,
            'location': project_data.location,
            'area_sqm': project_data.area_sqm,
            'year': project_data.year,
            'primary_category': project_data.primary_category,
            'sub_categories': project_data.sub_categories,
            'tags': project_data.tags,
            'views': project_data.views,
            'publish_date': project_data.publish_date,
            'crawled_at': datetime.now(),
            'updated_at': datetime.now(),
            'quality_score': self._calculate_quality_score(project_data),
        }
        with self.db.get_session() as session:
            stmt = pg_insert(ExternalProject).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=['url'],
                set_={
                    'title': stmt.excluded.title,
                    'description': stmt.excluded.description,
                    'architects': stmt.excluded.architects,
                    'location': stmt.excluded.location,
                    'area_sqm': stmt.excluded.area_sqm,
                    'year': stmt.excluded.year,
                    'primary_category': stmt.excluded.primary_category,
                    'sub_categories': stmt.excluded.sub_categories,
                    'tags': stmt.excluded.tags,
                    'views': stmt.excluded.views,
                    'publish_date': stmt.excluded.publish_date,
                    'updated_at': stmt.excluded.updated_at,
                    'quality_score': stmt.excluded.quality_score,
                }
            )
            result = session.execute(stmt)
            is_new = result.rowcount == 1  # INSERT 时 rowcount=1，UPDATE 时也是1但无法区分
            session.flush()
            project_id = session.execute(
                __import__('sqlalchemy').select(ExternalProject.id).where(ExternalProject.url == project_data.url)
            ).scalar()

            # 图片保存已禁用（不存储图片）

        return is_new

    def _calculate_quality_score(self, project_data: ProjectData) -> float:
        """
        计算项目质量评分（0-1）
        
        评分因子：
        - 描述长度（30%）
        - 图片数量（20%）
        - 元数据完整性（30%）
        - 标签数量（20%）
        """
        score = 0.0
        
        # 1. 描述长度（0-0.3）
        if project_data.description:
            desc_len = len(project_data.description)
            if desc_len >= 1000:
                score += 0.3
            elif desc_len >= 500:
                score += 0.2
            elif desc_len >= 200:
                score += 0.1
        
        # 2. 元数据完整性（0-0.4，原图片评分并入此项）
        metadata_fields = [
            project_data.architects,
            project_data.location,
            project_data.area_sqm,
            project_data.year,
            project_data.primary_category
        ]
        filled_count = sum(1 for field in metadata_fields if field)
        score += (filled_count / len(metadata_fields)) * 0.5

        # 3. 标签数量（0-0.2）
        tag_count = len(project_data.tags)
        if tag_count >= 10:
            score += 0.2
        elif tag_count >= 5:
            score += 0.15
        elif tag_count >= 3:
            score += 0.1
        
        return round(score, 2)
    
    def _create_quality_issue(self, url: str, issue_type: str, severity: str):
        """创建质量问题记录"""
        with self.db.get_session() as session:
            # 查找项目
            project = session.query(ExternalProject).filter(
                ExternalProject.url == url
            ).first()
            
            if project:
                issue = QualityIssue(
                    project_id=project.id,
                    issue_type=issue_type,
                    severity=severity,
                    detected_at=datetime.now()
                )
                session.add(issue)
    
    def get_sync_history(self, source: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """
        获取同步历史
        
        Args:
            source: 数据源（可选）
            limit: 返回数量
        
        Returns:
            同步历史列表
        """
        with self.db.get_session() as session:
            query = session.query(SyncHistory).order_by(SyncHistory.started_at.desc())
            
            if source:
                query = query.filter(SyncHistory.source == source)
            
            records = query.limit(limit).all()
            return [record.to_dict() for record in records]
    
    def get_source_stats(self) -> List[Dict]:
        """
        获取数据源统计
        
        Returns:
            [{"source": "archdaily", "total": 1000, "today": 5, "quality": 0.85}]
        """
        with self.db.get_session() as session:
            from sqlalchemy import func
            
            stats = []
            
            # 按数据源分组统计
            results = session.query(
                ExternalProject.source,
                func.count(ExternalProject.id).label('total'),
                func.avg(ExternalProject.quality_score).label('avg_quality')
            ).group_by(ExternalProject.source).all()
            
            for result in results:
                # 统计今日新增（用 datetime range 避免函数依赖）
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = today_start + timedelta(days=1)
                today_count = session.query(func.count(ExternalProject.id)).filter(
                    ExternalProject.source == result.source,
                    ExternalProject.crawled_at >= today_start,
                    ExternalProject.crawled_at < today_end,
                ).scalar()
                
                stats.append({
                    "source": result.source,
                    "total_projects": result.total,
                    "new_today": today_count,
                    "avg_quality_score": round(result.avg_quality, 2) if result.avg_quality else 0,
                })
            
            return stats


# ============================================================================
# 导出
# ============================================================================

__all__ = ['SpiderManager']
