"""
爬虫管理器

统一管理多个数据源的爬虫，提供：
- 爬虫注册与调度
- 数据存储到数据库
- 同步历史记录
- 质量评分
"""

import hashlib
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Set

from loguru import logger

# checkpoint 文件路径（项目根目录/data/crawl_checkpoints.json）
_CHECKPOINT_FILE = Path(__file__).parents[4] / "data" / "crawl_checkpoints.json"
# 网站分类总量缓存（由爬虫自动检测更新）
_SITE_TOTALS_FILE = Path(__file__).parents[4] / "data" / "category_site_totals.json"
# 结构化爬取错误日志（前端可通过 API 查询，自动排查问题）
_CRAWL_ERRORS_FILE = Path(__file__).parents[4] / "data" / "crawler_errors.jsonl"

# PostgreSQL upsert 支持
from sqlalchemy.dialects.postgresql import insert as pg_insert

from ..models.external_projects import (
    ExternalProject,
    ExternalProjectDatabase,
    ProjectDiscovery,
    QualityIssue,
    SyncHistory,
    get_external_db,
)
from .base_spider import BaseSpider, ProjectData


class SpiderManager:
    """爬虫管理器"""

    def __init__(self, db: ExternalProjectDatabase | None = None):
        """
        初始化管理器

        Args:
            db: 数据库实例（可选，默认使用全局实例）
        """
        self.db = db or get_external_db()
        self.spiders: Dict[str, BaseSpider] = {}

        logger.info("✅ SpiderManager已初始化")

    def get_known_urls(self, source: str, category: str | None = None) -> set:
        """
        获取数据库中已知的URL集合（用于增量去重）

        Args:
            source: 数据源名称
            category: 可选分类过滤

        Returns:
            已知URL的集合
        """
        with self.db.get_session() as session:
            query = session.query(ExternalProject.url).filter(ExternalProject.source == source)
            if category:
                query = query.filter(ExternalProject.primary_category == category)
            rows = query.all()
            return {row.url for row in rows}

    def get_latest_publish_date(self, source: str) -> datetime | None:
        """
        获取该数据源最新的发布日期（用于增量判断截止点）

        Returns:
            最新发布日期，若无记录返回 None
        """
        from sqlalchemy import func

        with self.db.get_session() as session:
            result = (
                session.query(func.max(ExternalProject.publish_date))
                .filter(ExternalProject.source == source, ExternalProject.publish_date.isnot(None))
                .scalar()
            )
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
            _CHECKPOINT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
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
            _SITE_TOTALS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
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

    def get_spider(self, source: str) -> BaseSpider | None:
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
        category: str | None = None,
        max_pages: int = 500,
        max_items: int | None = None,
        stop_check=None,  # callable() -> bool，返回 True 时中止爬取
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

        # ── 清理孤儿记录：将超过2小时仍处于 running 的记录标记为 crashed ──
        try:
            cutoff = datetime.now() - timedelta(hours=2)
            with self.db.get_session() as session:
                orphans = (
                    session.query(SyncHistory)
                    .filter(
                        SyncHistory.source == source,
                        SyncHistory.status == "running",
                        SyncHistory.started_at < cutoff,
                    )
                    .all()
                )
                for orphan in orphans:
                    orphan.status = "crashed"
                    orphan.completed_at = datetime.now()
                    orphan.error_message = "进程异常退出（Playwright崩溃/OOM），由后续同步自动清理"
                    logger.warning(f"🧹 清理孤儿同步记录: id={orphan.id}, started_at={orphan.started_at}")
        except Exception as e:
            logger.warning(f"清理孤儿记录时出错（不影响本次同步）: {e}")

        # 读取本数据源的全部 checkpoint
        checkpoints = self._load_checkpoints(source)
        new_checkpoints: Dict[str, str] = dict(checkpoints)

        # 会话级 URL 去重集合（防止同一 URL 在多分类中被重复 HTTP 请求）
        session_seen_urls: Set[str] = set()

        # 创建同步历史记录
        with self.db.get_session() as session:
            sync_record = SyncHistory(source=source, category=category, started_at=datetime.now(), status="running")
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
                            payload = u[len("__checkpoint__:") :]
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

                    # ── 发现索引：批量注册本次发现的所有 URL ─────────────────────────
                    if project_urls:
                        _new_disc = self._bulk_discover_urls(source, cat_name, project_urls)
                        logger.debug(f"  DiscoveryIndex: +{_new_disc} 条新 URL")

                    # ── 会话级去重：同次 sync 中跳过已处理 URL（多分类重叠时有效）──
                    _total_before_dedup = len(project_urls)
                    project_urls = [u for u in project_urls if u not in session_seen_urls]
                    session_seen_urls.update(project_urls)
                    _deduped = _total_before_dedup - len(project_urls)
                    if _deduped:
                        logger.debug(f"  会话去重: 跳过 {_deduped} 条")

                    logger.info(f"  待处理: {len(project_urls)} 条")

                    # ── 连续失败熔断器 ──────────────────────────────────
                    MAX_CONSECUTIVE_FAILURES = 5  # 连续失败 N 条即熔断
                    consecutive_failures = 0

                    for i, url in enumerate(project_urls, 1):
                        if max_items is not None and total_projects >= max_items:
                            logger.info(f"  已达 max_items={max_items}，停止")
                            break
                        # 每 5 条检查一次停止信号
                        if stop_check and i % 5 == 0 and stop_check():
                            logger.warning(f"  收到停止信号，在第 {i} 条处中止")
                            return False
                        try:
                            logger.debug(f"  [{i}/{len(project_urls)}] {url}")
                            project_data = spider.parse_project_page(url)
                            if not project_data:
                                failed_projects += 1
                                consecutive_failures += 1
                                self._mark_discovered_url_failed(url, "parse_returned_None")
                                self._emit_crawl_error(
                                    source=source,
                                    category=cat_name,
                                    url=url,
                                    error_type="parse_empty",
                                    message="解析返回空（页面未渲染或选择器失效）",
                                    consecutive=consecutive_failures,
                                )
                                logger.warning(f"  ⚠️ 解析返回空 (连续失败 {consecutive_failures}/{MAX_CONSECUTIVE_FAILURES})")
                                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                                    break
                                continue
                            if not project_data.validate():
                                failed_projects += 1
                                consecutive_failures += 1
                                # 收集验证失败的具体原因
                                _vf_detail = self._describe_validation_failure(project_data)
                                logger.warning(f"  ⚠️ 数据验证失败 (连续失败 {consecutive_failures}/{MAX_CONSECUTIVE_FAILURES})")
                                self._create_quality_issue(project_data.url, "validation_failed", "high")
                                self._mark_discovered_url_failed(url, "validation_failed")
                                self._emit_crawl_error(
                                    source=source,
                                    category=cat_name,
                                    url=url,
                                    error_type="validation_failed",
                                    message=_vf_detail,
                                    consecutive=consecutive_failures,
                                )
                                if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                                    break
                                continue
                            # ✅ 成功 → 重置连续失败计数
                            consecutive_failures = 0
                            # ── primary_category fallback：页面解析未提取时用当前分类名 ──
                            if not project_data.primary_category and cat_name:
                                project_data.primary_category = cat_name
                            created = self._save_project(project_data)
                            if created:
                                new_projects += 1
                            else:
                                updated_projects += 1
                            total_projects += 1
                            self._mark_discovered_url_crawled(url)
                        except Exception as e:
                            failed_projects += 1
                            consecutive_failures += 1
                            logger.error(f"  ❌ 爬取失败: {url} - {e}")
                            self._mark_discovered_url_failed(url, str(e)[:500])
                            # 自动分类异常类型
                            _etype = self._classify_exception(e)
                            self._emit_crawl_error(
                                source=source,
                                category=cat_name,
                                url=url,
                                error_type=_etype,
                                message=str(e)[:500],
                                consecutive=consecutive_failures,
                            )
                            if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                                break

                    # ── 熔断检查：停止当前数据源，通知管理员 ───────────
                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                        circuit_msg = (
                            f"🚨 爬虫熔断: {source}/{cat_name} "
                            f"连续 {MAX_CONSECUTIVE_FAILURES} 条失败，已停止爬取。"
                            f"已完成 {total_projects} 条，失败 {failed_projects} 条。"
                            f"请检查目标网站状态或爬虫解析逻辑。"
                        )
                        logger.error(circuit_msg)
                        self._notify_circuit_break(source, cat_name, circuit_msg, sync_id)
                        break  # 跳出分类循环，不再爬取后续分类

                # 所有分类完成后保存 checkpoint
                self._save_checkpoints(source, new_checkpoints)
                # 保存本次自动检测到的分类总量
                if detected_totals:
                    self._save_site_totals(source, detected_totals)

                _circuit_broken = consecutive_failures >= MAX_CONSECUTIVE_FAILURES
                final_status = "circuit_break" if _circuit_broken else "completed"

                with self.db.get_session() as session:
                    sync_record = session.query(SyncHistory).filter(SyncHistory.id == sync_id).first()
                    sync_record.completed_at = datetime.now()
                    sync_record.status = final_status
                    sync_record.projects_total = total_projects
                    sync_record.projects_new = new_projects
                    sync_record.projects_updated = updated_projects
                    sync_record.projects_failed = failed_projects
                    if _circuit_broken:
                        sync_record.error_message = (
                            f"熔断停止: 连续{MAX_CONSECUTIVE_FAILURES}条失败 " f"(总计{total_projects}成功/{failed_projects}失败)"
                        )

                if _circuit_broken:
                    logger.error(f"🚨 同步因熔断终止: {source}")
                else:
                    logger.success(f"✅ 同步完成: {source}")
                logger.info(
                    f"📊 总计: {total_projects}  新增: {new_projects}  " f"更新: {updated_projects}  失败: {failed_projects}"
                )
                # 输出 IP/限流统计（来自 base_spider）
                if spider:
                    _st = spider.stats
                    if _st.get("blocks_detected", 0) > 0 or _st.get("ip_rotations", 0) > 0:
                        logger.info(
                            f"🛡️ 封禁检测: {_st.get('blocks_detected', 0)} 次  " f"IP轮换: {_st.get('ip_rotations', 0)} 次"
                        )
                return not _circuit_broken

        except Exception as e:
            with self.db.get_session() as session:
                sync_record = session.query(SyncHistory).filter(SyncHistory.id == sync_id).first()
                sync_record.completed_at = datetime.now()
                sync_record.status = "failed"
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
        # ── content_hash：用于跳过无变化更新（减少写放大）─────────────────────
        _title = project_data.title or ""
        _desc_zh = getattr(project_data, "description_zh", None) or project_data.description or ""
        _desc_en = getattr(project_data, "description_en", None) or ""
        _content_hash = hashlib.sha256((_title + _desc_zh + _desc_en).encode("utf-8", errors="replace")).hexdigest()

        values = {
            "source": project_data.source,
            "source_id": project_data.source_id,
            "url": project_data.url,
            # ── 兼容字段（保持向后兼容）──────────────────────────────────────
            "title": _title,
            "description": project_data.description,
            # ── 双语字段 ─────────────────────────────────────────────────────
            "lang": getattr(project_data, "lang", None),
            "title_zh": getattr(project_data, "title_zh", None),
            "title_en": getattr(project_data, "title_en", None),
            "description_zh": getattr(project_data, "description_zh", None),
            "description_en": getattr(project_data, "description_en", None),
            # ── 元数据 ───────────────────────────────────────────────────────
            "architects": project_data.architects,
            "location": project_data.location,
            "area_sqm": project_data.area_sqm,
            "year": project_data.year,
            "primary_category": project_data.primary_category,
            "sub_categories": project_data.sub_categories,
            "tags": project_data.tags,
            "views": project_data.views,
            "publish_date": project_data.publish_date,
            "crawled_at": datetime.now(),
            "updated_at": datetime.now(),
            "quality_score": self._calculate_quality_score(project_data),
            "content_hash": _content_hash,
            "extra_fields": getattr(project_data, "extra_fields", None),
        }
        with self.db.get_session() as session:
            stmt = pg_insert(ExternalProject).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=["url"],
                set_={
                    "title": stmt.excluded.title,
                    "description": stmt.excluded.description,
                    "lang": stmt.excluded.lang,
                    "title_zh": stmt.excluded.title_zh,
                    "title_en": stmt.excluded.title_en,
                    "description_zh": stmt.excluded.description_zh,
                    "description_en": stmt.excluded.description_en,
                    "architects": stmt.excluded.architects,
                    "location": stmt.excluded.location,
                    "area_sqm": stmt.excluded.area_sqm,
                    "year": stmt.excluded.year,
                    "primary_category": stmt.excluded.primary_category,
                    "sub_categories": stmt.excluded.sub_categories,
                    "tags": stmt.excluded.tags,
                    "views": stmt.excluded.views,
                    "publish_date": stmt.excluded.publish_date,
                    "updated_at": stmt.excluded.updated_at,
                    "quality_score": stmt.excluded.quality_score,
                    "content_hash": stmt.excluded.content_hash,
                    "extra_fields": stmt.excluded.extra_fields,
                },
            )
            result = session.execute(stmt)
            is_new = result.rowcount == 1
            session.flush()

            # 图片保存已禁用（不存储图片）

        return is_new

    def _calculate_quality_score(self, project_data: ProjectData) -> float:
        """
        计算项目质量评分（0-1）

        评分因子：
        - 描述长度（0-0.3）：≥1000字 → 0.3，≥500字 → 0.2，≥200字 → 0.1
        - 元数据完整性（0-0.5）：architects/location/area_sqm/year/primary_category，
          每个字段占 0.1（图片已停止爬取，原图片权重并入元数据）
        - 标签数量（0-0.2）：≥10个 → 0.2，≥5个 → 0.15，≥3个 → 0.1
        - 满分阈值参考：质量合格线 ≥ 0.65
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
            project_data.primary_category,
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
            project = session.query(ExternalProject).filter(ExternalProject.url == url).first()

            if project:
                issue = QualityIssue(
                    project_id=project.id, issue_type=issue_type, severity=severity, detected_at=datetime.now()
                )
                session.add(issue)

    # ========================================================================
    # 结构化错误日志（自动诊断支持）
    # ========================================================================

    def _emit_crawl_error(
        self,
        source: str,
        category: str,
        url: str,
        error_type: str,
        message: str,
        consecutive: int = 0,
    ):
        """
        将爬取错误写入结构化日志 data/crawler_errors.jsonl。

        前端通过 GET /api/crawler/schedule/errors 查询，实现自动排查。
        error_type 分类：
          - parse_empty:        解析返回空（页面未渲染 / 选择器无效）
          - validation_failed:  数据验证失败（描述过短、标题为空等）
          - timeout:            请求/渲染超时
          - http_error:         HTTP 状态码异常（403/429/503 等）
          - network_error:      网络连接错误
          - exception:          未分类异常
        """
        try:
            _CRAWL_ERRORS_FILE.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "ts": datetime.now().isoformat(),
                "source": source,
                "category": category,
                "url": url,
                "error_type": error_type,
                "message": message,
                "consecutive_failures": consecutive,
            }
            with open(_CRAWL_ERRORS_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception:
            pass  # 日志写入不阻断爬取主流程

    @staticmethod
    def _classify_exception(exc: Exception) -> str:
        """根据异常类型自动分类错误。"""
        exc_name = type(exc).__name__.lower()
        exc_msg = str(exc).lower()
        if "timeout" in exc_name or "timeout" in exc_msg:
            return "timeout"
        if "403" in exc_msg or "429" in exc_msg or "503" in exc_msg:
            return "http_error"
        if any(k in exc_name for k in ("connection", "dns", "resolve", "socket")):
            return "network_error"
        if any(k in exc_msg for k in ("connection", "refused", "reset", "unreachable")):
            return "network_error"
        return "exception"

    @staticmethod
    def _describe_validation_failure(project_data: ProjectData) -> str:
        """生成验证失败的具体原因描述，便于自动诊断。"""
        reasons = []
        desc = max(
            len(getattr(project_data, "description_zh", None) or ""),
            len(getattr(project_data, "description_en", None) or ""),
            len(project_data.description or ""),
        )
        if desc < 50:
            reasons.append(f"描述过短({desc}字, 需≥50)")
        if not project_data.title or project_data.title == "Untitled":
            reasons.append("标题为空或未渲染")
        if not project_data.url:
            reasons.append("URL 为空")
        return "; ".join(reasons) if reasons else "数据验证失败(未知原因)"

    def _notify_circuit_break(self, source: str, category: str, message: str, sync_id: int):
        """
        熔断通知：记录到同步历史 + 写入告警文件。
        前端轮询 /api/crawler/schedule 或 /api/crawler/schedule/alerts 时可获取告警。
        """
        # 1. 更新同步记录状态为 circuit_break
        try:
            with self.db.get_session() as session:
                sync_record = session.query(SyncHistory).filter(SyncHistory.id == sync_id).first()
                if sync_record:
                    sync_record.status = "circuit_break"
                    sync_record.error_message = message
                    sync_record.completed_at = datetime.now()
        except Exception as e:
            logger.error(f"更新熔断状态失败: {e}")

        # 2. 写入告警文件（管理员可监控此文件，前端可通过 API 查询）
        alert_file = Path(__file__).parents[4] / "data" / "crawler_alerts.jsonl"
        try:
            alert_file.parent.mkdir(parents=True, exist_ok=True)
            alert = {
                "timestamp": datetime.now().isoformat(),
                "source": source,
                "category": category,
                "type": "circuit_break",
                "message": message,
                "sync_id": sync_id,
            }
            with open(alert_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(alert, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error(f"写入告警文件失败: {e}")

    def get_sync_history(self, source: str | None = None, limit: int = 10) -> List[Dict]:
        """
        获取同步历史

        Args:
            source: 数据源（可选）
            limit: 返回数量

        Returns:
            同步历史列表
        """
        with self.db.get_session() as session:
            # 主动清理：将超过2小时仍处于 running 的记录标记为 crashed
            try:
                cutoff = datetime.now() - timedelta(hours=2)
                orphans = (
                    session.query(SyncHistory)
                    .filter(
                        SyncHistory.status == "running",
                        SyncHistory.started_at < cutoff,
                    )
                    .all()
                )
                for orphan in orphans:
                    orphan.status = "crashed"
                    orphan.completed_at = datetime.now()
                    orphan.error_message = "超时自动清理（运行超过2小时，进程可能已崩溃）"
                    logger.warning(
                        f"🧹 查询时清理僵尸同步记录: id={orphan.id}, source={orphan.source}, started_at={orphan.started_at}"
                    )
                if orphans:
                    session.commit()
            except Exception as e:
                logger.warning(f"查询时清理僵尸记录出错（不影响查询）: {e}")

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
            results = (
                session.query(
                    ExternalProject.source,
                    func.count(ExternalProject.id).label("total"),
                    func.avg(ExternalProject.quality_score).label("avg_quality"),
                )
                .group_by(ExternalProject.source)
                .all()
            )

            for result in results:
                # 统计今日新增（用 datetime range 避免函数依赖）
                today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                today_end = today_start + timedelta(days=1)
                today_count = (
                    session.query(func.count(ExternalProject.id))
                    .filter(
                        ExternalProject.source == result.source,
                        ExternalProject.crawled_at >= today_start,
                        ExternalProject.crawled_at < today_end,
                    )
                    .scalar()
                )

                stats.append(
                    {
                        "source": result.source,
                        "total_projects": result.total,
                        "new_today": today_count,
                        "avg_quality_score": round(result.avg_quality, 2) if result.avg_quality else 0,
                    }
                )

            return stats

    # ========================================================================
    # URL 全生命周期追踪辅助方法
    # ========================================================================

    def _bulk_discover_urls(self, source: str, category: str, urls: List[str]) -> int:
        """
        批量注册 URL 到 ProjectDiscovery（INSERT ON CONFLICT DO NOTHING）。

        Returns:
            新增条数（基于 rowcount 估算，0 表示全部已存在或写入失败）
        """
        if not urls:
            return 0
        now = datetime.now()
        rows = [
            {
                "source": source,
                "source_id": u.rstrip("/").split("/")[-1],
                "url": u,
                "category": category,
                "discovered_at": now,
            }
            for u in urls
        ]
        try:
            with self.db.get_session() as session:
                stmt = pg_insert(ProjectDiscovery).values(rows)
                stmt = stmt.on_conflict_do_nothing(index_elements=["url"])
                result = session.execute(stmt)
                return result.rowcount
        except Exception as exc:
            logger.warning(f"_bulk_discover_urls 写入失败（非阻断）: {exc}")
            return 0

    def _mark_discovered_url_crawled(self, url: str) -> None:
        """将 ProjectDiscovery 中的 URL 标记为已成功爬取。"""
        try:
            with self.db.get_session() as session:
                session.query(ProjectDiscovery).filter_by(url=url).update(
                    {
                        "is_crawled": True,
                        "crawled_at": datetime.now(),
                        "crawl_attempts": ProjectDiscovery.crawl_attempts + 1,
                        "last_error": None,
                    }
                )
        except Exception as exc:
            logger.debug(f"_mark_discovered_url_crawled 失败（非阻断）: {exc}")

    def _mark_discovered_url_failed(self, url: str, error: str) -> None:
        """记录爬取失败次数（保留 is_crawled=False，允许后续重试）。"""
        try:
            with self.db.get_session() as session:
                session.query(ProjectDiscovery).filter_by(url=url).update(
                    {
                        "crawl_attempts": ProjectDiscovery.crawl_attempts + 1,
                        "last_error": (error or "")[:500],
                    }
                )
        except Exception as exc:
            logger.debug(f"_mark_discovered_url_failed 失败（非阻断）: {exc}")

    def retry_failed_urls(
        self,
        source: str,
        max_retries: int = 3,
        limit: int = 100,
    ) -> Dict[str, int]:
        """
        重试历史失败的 URL（is_crawled=False 且 crawl_attempts < max_retries）。

        Args:
            source:      数据源名称
            max_retries: 最大累计尝试次数（超过此值永久跳过）
            limit:       本次最多重试条数

        Returns:
            {"attempted": N, "success": M, "failed": K}
        """
        spider = self.get_spider(source)
        if not spider:
            return {"attempted": 0, "success": 0, "failed": 0}

        with self.db.get_session() as session:
            pending = (
                session.query(ProjectDiscovery)
                .filter(
                    ProjectDiscovery.source == source,
                    ProjectDiscovery.is_crawled == False,  # noqa: E712
                    ProjectDiscovery.crawl_attempts < max_retries,
                )
                .order_by(ProjectDiscovery.crawl_attempts.asc())
                .limit(limit)
                .all()
            )
            urls_to_retry = [p.url for p in pending]

        if not urls_to_retry:
            logger.info(f"[retry] {source}: 无待重试 URL")
            return {"attempted": 0, "success": 0, "failed": 0}

        logger.info(f"[retry] {source}: 待重试 {len(urls_to_retry)} 条 URL (max_retries={max_retries})")
        success = 0
        failed = 0

        with spider:
            for url in urls_to_retry:
                try:
                    project_data = spider.parse_project_page(url)
                    if project_data and project_data.validate():
                        self._save_project(project_data)
                        self._mark_discovered_url_crawled(url)
                        success += 1
                    else:
                        self._mark_discovered_url_failed(url, "data=None or invalid")
                        failed += 1
                except Exception as exc:
                    self._mark_discovered_url_failed(url, str(exc)[:500])
                    failed += 1

        logger.info(f"[retry] {source}: success={success}  failed={failed}")
        return {"attempted": len(urls_to_retry), "success": success, "failed": failed}


# ============================================================================
# 导出
# ============================================================================

__all__ = ["SpiderManager"]
