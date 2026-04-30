"""
爬虫监控&管理后台API

功能：
1. WebSocket实时推送进度&日志
2. 启动/暂停/停止爬虫任务
3. 查看爬虫统计和历史
4. 调整爬虫配置
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from loguru import logger
import asyncio
import threading

from ..auth_middleware import require_admin
from ...external_data_system.crawler_scheduler import (
    IntelligentCrawlerScheduler
)
from ...external_data_system.discovery_manager import ProjectDiscoveryManager
from ...external_data_system.spiders.archdaily_spider import ArchdailySpider
from ...external_data_system.spiders.gooood_spider import GoooodSpider
from ...external_data_system.spiders.dezeen_spider import DezeenSpider
from ...external_data_system.models import ExternalProject
from ...external_data_system import get_external_db

router = APIRouter()

# 全局调度器实例
scheduler: Optional[IntelligentCrawlerScheduler] = None
active_connections: List[WebSocket] = []
# 保存主事件循环引用（在第一次WebSocket连接时捕获）
_main_loop: Optional[asyncio.AbstractEventLoop] = None


def get_scheduler() -> IntelligentCrawlerScheduler:
    """获取调度器实例（单例）"""
    global scheduler
    if scheduler is None:
        scheduler = IntelligentCrawlerScheduler()
        scheduler.register_progress_callback(sync_broadcast_progress)
        scheduler.register_log_callback(sync_broadcast_log)
        logger.info("爬虫调度器初始化完成")
    return scheduler


def sync_broadcast_progress(data: Dict[str, Any]):
    """同步方式广播进度（从后台线程调用）"""
    if _main_loop and _main_loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_progress(data), _main_loop)


def sync_broadcast_log(data: Dict[str, Any]):
    """同步方式广播日志（从后台线程调用）"""
    if _main_loop and _main_loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_log(data), _main_loop)


async def broadcast_progress(data: Dict[str, Any]):
    await broadcast_message({"type": "progress", "data": data})


async def broadcast_log(data: Dict[str, Any]):
    await broadcast_message({"type": "log", "data": data})


async def broadcast_message(message: Dict[str, Any]):
    disconnected = []
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"发送WebSocket消息失败: {e}")
            disconnected.append(connection)
    for conn in disconnected:
        if conn in active_connections:
            active_connections.remove(conn)


# ==================== WebSocket ====================

@router.websocket("/ws/monitor")
async def websocket_monitor(websocket: WebSocket):
    """爬虫实时监控WebSocket"""
    global _main_loop
    _main_loop = asyncio.get_event_loop()

    await websocket.accept()
    active_connections.append(websocket)
    logger.info(f"WebSocket连接建立，当前连接数: {len(active_connections)}")

    try:
        scheduler_instance = get_scheduler()
        all_progress = scheduler_instance.get_all_progress()
        await websocket.send_json({"type": "initial_state", "data": all_progress})

        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        logger.info("WebSocket连接断开")
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)
        logger.info(f"WebSocket连接移除，当前连接数: {len(active_connections)}")


# ==================== API Models ====================

class CrawlTaskRequest(BaseModel):
    """爬取任务请求"""
    source: str  # archdaily, gooood, dezeen
    category: Optional[str] = None
    limit: Optional[int] = None
    auto_translate: bool = False
    translation_engine: str = "deepseek"
    resume: bool = True


class BatchConfigUpdate(BaseModel):
    """批次配置更新"""
    batch_size: Optional[int] = None
    min_delay: Optional[float] = None
    max_delay: Optional[float] = None
    batch_rest: Optional[float] = None
    max_requests_per_hour: Optional[int] = None
    max_requests_per_day: Optional[int] = None


# ==================== 任务管理 ====================

def _create_spider(source: str):
    """根据数据源创建Spider实例"""
    if source == "archdaily":
        return ArchdailySpider()
    elif source == "gooood":
        return GoooodSpider(use_playwright=True)
    elif source == "dezeen":
        return DezeenSpider(use_playwright=True)
    else:
        raise ValueError(f"未知数据源: {source}")


@router.post("/start", dependencies=[Depends(require_admin)])
async def start_crawl_task(request: CrawlTaskRequest):
    """启动爬取任务"""
    scheduler_instance = get_scheduler()
    discovery_manager = ProjectDiscoveryManager()

    task_id = f"{request.source}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    projects = discovery_manager.get_uncrawled_projects(
        source=request.source,
        category=request.category,
        limit=request.limit,
    )

    if not projects:
        raise HTTPException(status_code=404, detail="没有待爬取的项目")

    logger.info(f"启动爬取任务: {task_id}, 共 {len(projects)} 个项目")

    resume_from = 0
    if request.resume:
        checkpoint = scheduler_instance.load_checkpoint(task_id)
        if checkpoint is not None:
            resume_from = checkpoint
            logger.info(f"从断点恢复: 位置 {resume_from}")

    # 创建ONE spider实例，在整个批次中复用
    spider = _create_spider(request.source)
    source = request.source

    def crawl_batch_with_spider():
        """在独立线程中运行整个爬取批次（spider生命周期在此管理）"""
        db = get_external_db()
        dm = ProjectDiscoveryManager(db)

        with spider:  # __enter__ 启动浏览器, __exit__ 关闭浏览器
            def crawl_func(project):
                try:
                    project_data = spider.parse_project_page(project.url)

                    if not project_data:
                        dm.mark_as_crawled(project.url, success=False, error="返回空数据")
                        return False

                    with db.get_session() as session:
                        existing = session.query(ExternalProject).filter(
                            ExternalProject.url == project_data.url
                        ).first()

                        if existing:
                            dm.mark_as_crawled(project.url, success=True)
                            return True

                        is_chinese_source = source in {'gooood'}

                        if is_chinese_source:
                            title = title_zh = project_data.title
                            title_en = None
                            description = description_zh = project_data.description
                            description_en = None
                        else:
                            title = title_en = project_data.title
                            title_zh = None
                            description = description_en = project_data.description
                            description_zh = None

                        external_project = ExternalProject(
                            source=project_data.source,
                            source_id=project_data.source_id,
                            url=project_data.url,
                            title=title,
                            title_en=title_en,
                            title_zh=title_zh,
                            description=description,
                            description_en=description_en,
                            description_zh=description_zh,
                            architects=project_data.architects,
                            location=project_data.location,
                            year=project_data.year,
                            area_sqm=project_data.area_sqm,
                            primary_category=project_data.primary_category,
                            sub_categories=[],
                            tags=project_data.tags,
                        )
                        session.add(external_project)

                    dm.mark_as_crawled(project.url, success=True)
                    return True

                except Exception as e:
                    logger.error(f"爬取失败: {project.url}, 错误: {e}")
                    dm.mark_as_crawled(project.url, success=False, error=str(e))
                    return False

            scheduler_instance.crawl_batch(
                task_id=task_id,
                source=source,
                items=projects,
                crawl_func=crawl_func,
                resume_from=resume_from,
            )

    # 在独立线程中运行（避免与FastAPI asyncio事件循环冲突）
    thread = threading.Thread(
        target=crawl_batch_with_spider,
        daemon=True,
        name=f"crawl-{task_id}",
    )
    thread.start()

    return {
        "task_id": task_id,
        "status": "started",
        "total_items": len(projects),
        "resume_from": resume_from,
        "message": f"爬取任务已启动: {task_id}",
    }


@router.post("/pause/{task_id}", dependencies=[Depends(require_admin)])
async def pause_task(task_id: str):
    """暂停任务"""
    scheduler_instance = get_scheduler()
    scheduler_instance.pause_task(task_id)
    return {"task_id": task_id, "status": "paused"}


@router.post("/resume/{task_id}", dependencies=[Depends(require_admin)])
async def resume_task(task_id: str):
    """恢复任务"""
    scheduler_instance = get_scheduler()
    scheduler_instance.resume_task(task_id)
    return {"task_id": task_id, "status": "resumed"}


@router.post("/stop/{task_id}", dependencies=[Depends(require_admin)])
async def stop_task(task_id: str):
    """停止任务"""
    scheduler_instance = get_scheduler()
    scheduler_instance.stop_task(task_id)
    return {"task_id": task_id, "status": "stopped"}


# ==================== 查询 ====================

@router.get("/progress/{task_id}")
async def get_task_progress(task_id: str):
    """获取任务进度"""
    scheduler_instance = get_scheduler()
    progress = scheduler_instance.get_progress(task_id)
    if not progress:
        raise HTTPException(status_code=404, detail="任务不存在")
    return progress


@router.get("/progress")
async def get_all_progress():
    """获取所有任务进度"""
    scheduler_instance = get_scheduler()
    return scheduler_instance.get_all_progress()


@router.get("/stats")
async def get_crawler_stats():
    """获取爬虫统计"""
    db = get_external_db()
    discovery_manager = ProjectDiscoveryManager(db)

    with db.get_session() as session:
        total_projects = session.query(ExternalProject).count()
        by_source = {}
        for source in ['archdaily', 'gooood', 'dezeen']:
            count = session.query(ExternalProject).filter(
                ExternalProject.source == source
            ).count()
            by_source[source] = count

    index_stats = discovery_manager.get_statistics()

    return {
        "database": {
            "total_projects": total_projects,
            "by_source": by_source,
        },
        "index": index_stats,
        "timestamp": datetime.now().isoformat(),
    }


# ==================== 配置管理 ====================

@router.get("/config")
async def get_crawler_config():
    """获取爬虫配置"""
    scheduler_instance = get_scheduler()
    config = scheduler_instance.config
    return {
        "batch_size": config.batch_size,
        "min_delay": config.min_delay,
        "max_delay": config.max_delay,
        "batch_rest": config.batch_rest,
        "max_requests_per_hour": config.max_requests_per_hour,
        "max_requests_per_day": config.max_requests_per_day,
        "work_hours": config.work_hours,
        "weekend_enabled": config.weekend_enabled,
    }


@router.patch("/config", dependencies=[Depends(require_admin)])
async def update_crawler_config(update: BatchConfigUpdate):
    """更新爬虫配置"""
    scheduler_instance = get_scheduler()
    config = scheduler_instance.config

    if update.batch_size is not None:
        config.batch_size = update.batch_size
    if update.min_delay is not None:
        config.min_delay = update.min_delay
    if update.max_delay is not None:
        config.max_delay = update.max_delay
    if update.batch_rest is not None:
        config.batch_rest = update.batch_rest
    if update.max_requests_per_hour is not None:
        config.max_requests_per_hour = update.max_requests_per_hour
    if update.max_requests_per_day is not None:
        config.max_requests_per_day = update.max_requests_per_day

    logger.info(f"爬虫配置已更新: {update.dict(exclude_none=True)}")
    return {"message": "配置已更新", "config": config.__dict__}


# ==================== 调度计划 ====================

import json
from pathlib import Path

_SCHEDULE_STATE_FILE = Path(__file__).resolve().parents[3] / "data" / "crawler_state" / "schedule_state.json"
_CHECKPOINT_FILE     = Path(__file__).resolve().parents[3] / "data" / "crawl_checkpoints.json"
_SITE_TOTALS_FILE2   = Path(__file__).resolve().parents[3] / "data" / "category_site_totals.json"


@router.get("/schedule", summary="获取调度计划状态")
async def get_schedule_state():
    """
    读取 crawl_scheduler.py 持久化的调度状态文件。
    包括：全量爬取进度、上次/下次增量时间、历史记录。
    """
    if not _SCHEDULE_STATE_FILE.exists():
        return {
            "exists": False,
            "message": "调度状态文件不存在，请先启动 scripts/crawl_scheduler.py",
        }
    try:
        with open(_SCHEDULE_STATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["exists"] = True
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取状态文件失败: {e}")


class ScheduleTriggerRequest(BaseModel):
    """手动触发调度请求"""
    mode: str = "incremental"  # full | incremental
    source: str = "archdaily_cn"  # archdaily_cn | gooood | dezeen（全量 all 表示全部）


@router.post("/schedule/trigger", dependencies=[Depends(require_admin)], summary="手动触发爬取")
async def trigger_schedule(request: ScheduleTriggerRequest):
    """
    在后台线程立即触发一次全量或增量爬取。
    进度实时写入 schedule_state.json，可通过 GET /schedule 轮询。
    """
    if request.mode not in ("full", "incremental"):
        raise HTTPException(status_code=400, detail="mode 必须是 full 或 incremental")

    valid_sources = {"archdaily_cn", "gooood", "dezeen", "all"}
    if request.source not in valid_sources:
        raise HTTPException(status_code=400, detail=f"source 必须是: {', '.join(sorted(valid_sources))}")

    # 检查数据源是否已启用
    if request.source != "all":
        try:
            import importlib.util as _ilu
            _sched_path = Path(__file__).resolve().parents[3] / "scripts" / "crawl_scheduler.py"
            _spec = _ilu.spec_from_file_location("_sched_check", _sched_path)
            _mod = _ilu.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)
            _src_cfg = _mod.SOURCES.get(request.source, {})
            if not _src_cfg.get("enabled", True):
                return {
                    "status": "disabled",
                    "message": f"数据源 {request.source} 尚未开放，请先完成 archdaily_cn 全量爬取后再启用",
                }
        except Exception:
            pass  # 无法加载时放行，由调度器内部守卫    

    # 检查是否已有调度任务在运行
    if _SCHEDULE_STATE_FILE.exists():
        try:
            with open(_SCHEDULE_STATE_FILE, "r", encoding="utf-8") as f:
                current = json.load(f)
            if current.get("phase") in ("full_crawling", "incremental_crawling"):
                return {
                    "status": "already_running",
                    "message": f"当前已有任务运行中: {current.get('running_task')}",
                    "phase": current.get("phase"),
                }
        except Exception:
            pass

    # 在后台线程触发（不阻塞 API 请求）
    import importlib.util
    _mode = request.mode
    _source = request.source

    def _run():
        # ── 挂 loguru sink，把爬虫日志实时推送到 WebSocket ──────────────
        def _ws_sink(message):
            record = message.record
            level = record["level"].name.lower()
            text = record["message"]
            sync_broadcast_log({"level": level, "message": text, "source": _source})

        sink_id = logger.add(_ws_sink, level="INFO", format="{message}")

        # ── 定期推送 schedule_state.json 中的 running_task 作为进度日志 ─
        import time as _time
        _state_file = Path(__file__).resolve().parents[3] / "data" / "crawler_state" / "schedule_state.json"
        _last_task: list = [None]  # 用列表模拟可变闭包

        def _poll_state():
            while True:
                _time.sleep(3)
                try:
                    import json as _json
                    with open(_state_file, "r", encoding="utf-8") as _f:
                        _s = _json.load(_f)
                    task = _s.get("running_task")
                    phase = _s.get("phase", "idle")
                    if task and task != _last_task[0]:
                        _last_task[0] = task
                        sync_broadcast_log({"level": "info", "message": f"▶ {task}", "source": _source})
                    if phase == "idle":
                        break
                except Exception:
                    pass

        _poll_thread = threading.Thread(target=_poll_state, daemon=True, name="state-poller")
        _poll_thread.start()

        try:
            spec = importlib.util.spec_from_file_location(
                "crawl_scheduler",
                Path(__file__).resolve().parents[3] / "scripts" / "crawl_scheduler.py",
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if _mode == "full":
                if _source == "all":
                    mod._run_full_crawl_all()
                else:
                    mod._run_full_crawl(_source)
            else:
                if _source == "all":
                    # 依次对每个源运行增量爬取
                    for src in ("archdaily_cn", "gooood", "dezeen"):
                        mod._run_incremental_crawl(src)
                else:
                    mod._run_incremental_crawl(_source)
        except Exception as exc:
            logger.error(f"手动触发爬取失败 ({_mode}/{_source}): {exc}")
        finally:
            logger.remove(sink_id)
            sync_broadcast_log({"level": "info", "message": f"✓ {_source} 爬取任务结束", "source": _source})

    thread = threading.Thread(target=_run, daemon=True, name=f"manual-{_mode}-{_source}")
    thread.start()

    mode_label = "全量" if _mode == "full" else "增量"
    src_label = "所有源" if _source == "all" else _source
    return {
        "status": "triggered",
        "mode": _mode,
        "source": _source,
        "message": f"已在后台启动 {src_label} {mode_label}爬取",
        "poll_url": "/api/crawler/schedule",
    }


# ==================== APScheduler 任务管理 ====================

from ...external_data_system.job_scheduler_service import JobSchedulerService


def _get_job_service() -> JobSchedulerService:
    return JobSchedulerService.get_instance()


@router.get("/jobs", summary="列出所有定时任务")
async def list_jobs():
    """
    列出 FastAPI 进程内 APScheduler 的所有任务。
    包括：任务名、Cron 触发器、下次运行时间、状态（active/paused）。
    """
    svc = _get_job_service()
    return {
        "scheduler_running": svc.is_running(),
        "jobs": svc.get_jobs(),
    }


@router.get("/jobs/{job_id}", summary="查询单个定时任务")
async def get_job(job_id: str):
    svc = _get_job_service()
    job = svc.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"任务不存在: {job_id}")
    return job


@router.post("/jobs/{job_id}/pause", dependencies=[Depends(require_admin)], summary="暂停定时任务")
async def pause_job(job_id: str):
    svc = _get_job_service()
    try:
        return svc.pause_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/jobs/{job_id}/resume", dependencies=[Depends(require_admin)], summary="恢复定时任务")
async def resume_job(job_id: str):
    svc = _get_job_service()
    try:
        return svc.resume_job(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/jobs/{job_id}/run-now", dependencies=[Depends(require_admin)], summary="立即触发任务执行")
async def run_job_now(job_id: str):
    svc = _get_job_service()
    try:
        return svc.run_job_now(job_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


class ModifyJobCronRequest(BaseModel):
    """修改 Cron 触发器请求"""
    day_of_week: Optional[str] = None   # mon/tue/wed/thu/fri/sat/sun 或 0-6
    hour: Optional[int] = None           # 0-23
    minute: Optional[int] = None         # 0-59
    second: Optional[int] = None         # 0-59


@router.patch("/jobs/{job_id}/cron", dependencies=[Depends(require_admin)], summary="修改任务 Cron 触发器")
async def modify_job_cron(job_id: str, req: ModifyJobCronRequest):
    """
    修改已有 Cron 任务的触发时间。只需传要修改的字段，其余保持原值。
    示例：将每周一改为每周三执行 → {"day_of_week": "wed"}
    """
    svc = _get_job_service()
    try:
        return svc.modify_job_cron(
            job_id,
            day_of_week=req.day_of_week,
            hour=req.hour,
            minute=req.minute,
            second=req.second,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/schedule/pre-scan", dependencies=[Depends(require_admin)], summary="预扫描：获取网站分类配置与现有数据统计")
async def get_pre_scan(source: str = "archdaily_cn"):
    """
    快速预扫描（不启动浏览器）：
    1. 读取 spider 的静态分类列表
    2. 查询本地 DB 该源各分类现有条数 + 日期范围
    返回管理员确认全量前所需的摘要信息。
    """
    valid_sources = {"archdaily_cn", "gooood", "dezeen"}
    if source not in valid_sources:
        raise HTTPException(status_code=400, detail=f"source 必须是: {', '.join(sorted(valid_sources))}")

    # 未启用的源也允许预扫描查看配置（只读，不触发）

    # ── 1. 读取 spider 静态分类配置 ───────────────────────────────────────
    try:
        import importlib.util as _ilu
        _spider_modules = {
            "archdaily_cn": ("intelligent_project_analyzer.external_data_system.spiders.archdaily_cn_spider", "ArchdailyCNSpider"),
            "gooood":       ("intelligent_project_analyzer.external_data_system.spiders.gooood_spider",       "GoooodSpider"),
            "dezeen":       ("intelligent_project_analyzer.external_data_system.spiders.dezeen_spider",       "DezeenSpider"),
        }
        mod_path, cls_name = _spider_modules[source]
        import importlib as _il
        mod = _il.import_module(mod_path)
        spider_cls = getattr(mod, cls_name)
        # 只需要 CATEGORIES，不启动浏览器
        if hasattr(spider_cls, "CATEGORIES"):
            categories: dict = spider_cls.CATEGORIES
        else:
            # fallback：实例化（不会启动浏览器，直到 start() 被调用）
            tmp = spider_cls.__new__(spider_cls)
            tmp.__init__()
            categories = tmp.get_categories()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"加载 spider 分类失败: {e}")

    # ── 2. 查询 DB 各分类现有条数 + 日期范围 ─────────────────────────────
    cat_counts: dict[str, int] = {cat: 0 for cat in categories}
    date_earliest: str | None = None
    date_latest: str | None = None
    db_total = 0

    try:
        from sqlalchemy import func as _func
        from intelligent_project_analyzer.external_data_system.models.external_projects import (
            ExternalProject, get_external_db,
        )
        db = get_external_db()
        with db.get_session() as sess:
            # 各分类条数
            rows = (
                sess.query(ExternalProject.primary_category, _func.count(ExternalProject.id))
                .filter(ExternalProject.source == source)
                .group_by(ExternalProject.primary_category)
                .all()
            )
            for cat_name, cnt in rows:
                if cat_name in cat_counts:
                    cat_counts[cat_name] = cnt
                db_total += cnt

            # 日期范围
            date_row = sess.query(
                _func.min(ExternalProject.publish_date),
                _func.max(ExternalProject.publish_date),
            ).filter(
                ExternalProject.source == source,
                ExternalProject.publish_date.isnot(None),
            ).first()
            if date_row and date_row[0]:
                date_earliest = date_row[0].strftime("%Y-%m") if hasattr(date_row[0], "strftime") else str(date_row[0])[:7]
                date_latest   = date_row[1].strftime("%Y-%m") if hasattr(date_row[1], "strftime") else str(date_row[1])[:7]
    except Exception as e:
        logger.warning(f"[pre-scan] DB 查询失败（可能 DB 未就绪）: {e}")

    # ── 读取 spider 的 CATEGORY_TOTALS（静态参考基准）────────────────────
    category_totals_static: dict = {}
    if hasattr(spider_cls, "CATEGORY_TOTALS"):
        category_totals_static = spider_cls.CATEGORY_TOTALS

    # ── 读取爬虫自动检测的分类总量（data/category_site_totals.json）──────
    # 优先使用 7 天内自动更新的数据，否则回退到静态 CATEGORY_TOTALS
    _SITE_TOTALS_FILE = __import__("pathlib").Path(__file__).parents[4] / "data" / "category_site_totals.json"
    auto_totals: dict = {}
    try:
        if _SITE_TOTALS_FILE.exists():
            raw = __import__("json").loads(_SITE_TOTALS_FILE.read_text(encoding="utf-8"))
            src_data = raw.get(source, {})
            updated_at_str = src_data.get("_updated_at")
            if updated_at_str:
                updated_at = __import__("datetime").datetime.fromisoformat(updated_at_str)
                age_days = (__import__("datetime").datetime.now() - updated_at).days
                if age_days <= 7:
                    auto_totals = {k: v for k, v in src_data.items() if k != "_updated_at"}
                    logger.info(f"[pre-scan] 使用自动检测总量缓存（{age_days} 天前更新，{len(auto_totals)} 个分类）")
                else:
                    logger.info(f"[pre-scan] 自动检测总量缓存已过期（{age_days} 天），回退到静态配置")
    except Exception as e:
        logger.warning(f"[pre-scan] 读取 site_totals 缓存失败: {e}")

    def _get_site_total(name: str) -> __import__("builtins").object:
        """优先用自动检测值，其次用静态配置，找不到返回 None"""
        return auto_totals.get(name) or category_totals_static.get(name) or None

    return {
        "source": source,
        "categories": [
            {
                "name": name,
                "url": url,
                "db_count": cat_counts.get(name, 0),
                "site_total": _get_site_total(name),
            }
            for name, url in categories.items()
        ],
        "total_categories": len(categories),
        "db_total": db_total,
        "date_range": {
            "earliest": date_earliest,
            "latest": date_latest,
        },
        "totals_source": "auto" if auto_totals else "static",  # 前端可据此显示数据来源
        "scanned_at": __import__("datetime").datetime.now().isoformat(),
    }


@router.delete("/schedule/reset-full", dependencies=[Depends(require_admin)], summary="重置全量爬取状态")
async def reset_full_crawl(source: str = "all"):
    """
    将指定数据源（或所有源）的全量爬取状态重置为 pending。
    - source=all：重置所有源的全量状态
    - source=archdaily_cn|gooood|dezeen：只重置指定源
    不影响已入库数据。
    """
    valid_sources = {"archdaily_cn", "gooood", "dezeen", "all"}
    if source not in valid_sources:
        raise HTTPException(status_code=400, detail=f"source 必须是: {', '.join(sorted(valid_sources))}")

    if not _SCHEDULE_STATE_FILE.exists():
        raise HTTPException(status_code=404, detail="状态文件不存在")
    try:
        with open(_SCHEDULE_STATE_FILE, "r", encoding="utf-8") as f:
            state = json.load(f)

        _blank_full_crawl = {
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            # 重置同时清除基线快照，下次全量会重新扫描
            "target_categories": None,
            "total_categories": None,
            "baseline_count": None,
            "scan_at": None,
            "categories_done": [],
            "category_stats": {},
            "total_stats": {"total": 0, "new": 0, "skipped": 0, "failed": 0},
            "error": None,
        }

        from datetime import datetime as _dt

        if state.get("version", 1) >= 2:
            # v2 多源格式
            sources_to_reset = list(state.get("sources", {}).keys()) if source == "all" else [source]
            for src in sources_to_reset:
                if src in state.get("sources", {}):
                    state["sources"][src]["full_crawl"] = _blank_full_crawl.copy()
        else:
            # v1 兼容
            state["full_crawl"] = _blank_full_crawl

        state["phase"] = "idle"
        state["running_task"] = None
        state["last_updated"] = _dt.now().isoformat()

        with open(_SCHEDULE_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

        label = "所有源" if source == "all" else source
        return {"status": "ok", "message": f"{label} 全量爬取状态已重置"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/schedule/source-status", summary="获取数据源 checkpoint 同步状态")
async def get_source_status(source: str = "gooood"):
    """
    返回指定数据源的综合同步状态：
    - checkpoint 覆盖情况（各分类是否有 checkpoint URL）
    - DB 各分类当前条数
    - 网站总量（auto-detected 或静态参考）
    - schedule_state.json 中的 is_running
    """
    valid_sources = {"archdaily_cn", "gooood", "dezeen"}
    if source not in valid_sources:
        raise HTTPException(status_code=400, detail=f"source 必须是: {', '.join(sorted(valid_sources))}")

    import datetime as _dt_mod
    import importlib as _il

    # ── 1. 读取 checkpoints ──────────────────────────────────────────────
    checkpoints: dict = {}
    try:
        if _CHECKPOINT_FILE.exists():
            raw = json.loads(_CHECKPOINT_FILE.read_text(encoding="utf-8"))
            checkpoints = raw.get(source, {})
    except Exception as e:
        logger.warning(f"[source-status] 读取 checkpoint 失败: {e}")

    # ── 2. 读取网站总量缓存 ──────────────────────────────────────────────
    site_totals: dict = {}
    totals_source_flag = "static"
    try:
        if _SITE_TOTALS_FILE2.exists():
            raw2 = json.loads(_SITE_TOTALS_FILE2.read_text(encoding="utf-8"))
            src_data = raw2.get(source, {})
            updated_at_str = src_data.get("_updated_at")
            if updated_at_str:
                updated_at = _dt_mod.datetime.fromisoformat(updated_at_str)
                age_days = (_dt_mod.datetime.now() - updated_at).days
                if age_days <= 7:
                    site_totals = {k: v for k, v in src_data.items() if k != "_updated_at"}
                    totals_source_flag = "auto"
    except Exception as e:
        logger.warning(f"[source-status] 读取 site_totals 失败: {e}")

    # 若 auto 未满，回退静态
    if not site_totals:
        try:
            _spider_modules4 = {
                "archdaily_cn": ("intelligent_project_analyzer.external_data_system.spiders.archdaily_cn_spider", "ArchdailyCNSpider"),
                "gooood":       ("intelligent_project_analyzer.external_data_system.spiders.gooood_spider",       "GoooodSpider"),
                "dezeen":       ("intelligent_project_analyzer.external_data_system.spiders.dezeen_spider",       "DezeenSpider"),
            }
            mod_path4, cls_name4 = _spider_modules4[source]
            mod4 = _il.import_module(mod_path4)
            spider_cls4 = getattr(mod4, cls_name4)
            if hasattr(spider_cls4, "CATEGORY_TOTALS"):
                site_totals = spider_cls4.CATEGORY_TOTALS
        except Exception:
            pass

    # ── 3. 读取 spider 分类列表 ──────────────────────────────────────────
    categories_meta: dict = {}
    try:
        _spider_mods5 = {
            "archdaily_cn": ("intelligent_project_analyzer.external_data_system.spiders.archdaily_cn_spider", "ArchdailyCNSpider"),
            "gooood":       ("intelligent_project_analyzer.external_data_system.spiders.gooood_spider",       "GoooodSpider"),
            "dezeen":       ("intelligent_project_analyzer.external_data_system.spiders.dezeen_spider",       "DezeenSpider"),
        }
        mod_path5, cls_name5 = _spider_mods5[source]
        mod5 = _il.import_module(mod_path5)
        spider_cls5 = getattr(mod5, cls_name5)
        if hasattr(spider_cls5, "CATEGORIES"):
            categories_meta = spider_cls5.CATEGORIES
    except Exception as e:
        logger.warning(f"[source-status] 读取 spider CATEGORIES 失败: {e}")

    # ── 4. 查询 DB 各分类条数 ────────────────────────────────────────────
    cat_db_counts: dict = {cat: 0 for cat in categories_meta}
    db_total = 0
    last_sync_from_db: str | None = None
    try:
        from sqlalchemy import func as _func
        from intelligent_project_analyzer.external_data_system.models.external_projects import (
            ExternalProject, get_external_db,
        )
        db_ext = get_external_db()
        with db_ext.get_session() as sess:
            rows = (
                sess.query(ExternalProject.primary_category, _func.count(ExternalProject.id))
                .filter(ExternalProject.source == source)
                .group_by(ExternalProject.primary_category)
                .all()
            )
            for cat_name, cnt in rows:
                if cat_name in cat_db_counts:
                    cat_db_counts[cat_name] = cnt
                db_total += cnt

            # 最近同步时间
            latest_row = (
                sess.query(_func.max(ExternalProject.crawled_at))
                .filter(ExternalProject.source == source)
                .scalar()
            )
            if latest_row:
                last_sync_from_db = latest_row.isoformat() if hasattr(latest_row, "isoformat") else str(latest_row)
    except Exception as e:
        logger.warning(f"[source-status] DB 查询失败: {e}")

    # ── 5. 读取 schedule_state.json ─────────────────────────────────────
    is_running = False
    last_sync: str | None = last_sync_from_db
    try:
        if _SCHEDULE_STATE_FILE.exists():
            state5 = json.loads(_SCHEDULE_STATE_FILE.read_text(encoding="utf-8"))
            phase5 = state5.get("phase", "idle")
            is_running = phase5 in ("full_crawling", "incremental_crawling")
            src_state5 = state5.get("sources", {}).get(source, {})
            incr5 = src_state5.get("incremental", {})
            if incr5.get("last_run_at"):
                last_sync = incr5["last_run_at"]
    except Exception as e:
        logger.warning(f"[source-status] 读取 schedule_state 失败: {e}")

    # ── 组合结果 ─────────────────────────────────────────────────────────
    cat_list = []
    for cat_name, cat_url in categories_meta.items():
        ckpt_raw = checkpoints.get(cat_name)
        cat_list.append({
            "name": cat_name,
            "url": cat_url,
            "db_count": cat_db_counts.get(cat_name, 0),
            "site_total": site_totals.get(cat_name),
            "has_checkpoint": cat_name in checkpoints,
            "checkpoint_url": ckpt_raw,
        })

    site_total_estimated = sum(v for v in site_totals.values() if isinstance(v, (int, float)))

    # 读取该数据源的启用状态
    source_enabled = True
    try:
        _sched_path2 = Path(__file__).resolve().parents[3] / "scripts" / "crawl_scheduler.py"
        import importlib.util as _ilu2
        _spec2 = _ilu2.spec_from_file_location("_sched_enabled", _sched_path2)
        _mod2 = _ilu2.module_from_spec(_spec2)
        _spec2.loader.exec_module(_mod2)
        source_enabled = _mod2.SOURCES.get(source, {}).get("enabled", True)
    except Exception:
        pass

    return {
        "source": source,
        "enabled": source_enabled,
        "db_total": db_total,
        "site_total_estimated": site_total_estimated,
        "totals_source": totals_source_flag,
        "last_sync": last_sync,
        "is_running": is_running,
        "checkpoint_count": len(checkpoints),
        "total_categories": len(categories_meta),
        "categories": cat_list,
        "scanned_at": _dt_mod.datetime.now().isoformat(),
    }


@router.post("/schedule/reset-checkpoint", dependencies=[Depends(require_admin)], summary="清空数据源 checkpoint（下次同步将重新全量）")
async def reset_checkpoint_endpoint(source: str):
    """
    清除指定数据源在 data/crawl_checkpoints.json 中存储的全部分类 checkpoint。
    清除后，下次调用 trigger（mode=full 或 incremental）时，爬虫将从头爬取所有历史内容。
    不影响已入库数据。
    """
    valid_sources = {"archdaily_cn", "gooood", "dezeen"}
    if source not in valid_sources:
        raise HTTPException(status_code=400, detail=f"source 必须是: {', '.join(sorted(valid_sources))}")

    try:
        all_data: dict = {}
        if _CHECKPOINT_FILE.exists():
            all_data = json.loads(_CHECKPOINT_FILE.read_text(encoding="utf-8"))

        cleared_count = len(all_data.get(source, {}))
        all_data.pop(source, None)

        _CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CHECKPOINT_FILE.write_text(json.dumps(all_data, ensure_ascii=False, indent=2), encoding="utf-8")

        logger.info(f"[reset-checkpoint] 已清除 {source} 的 {cleared_count} 个分类 checkpoint")
        return {
            "status": "ok",
            "source": source,
            "cleared": cleared_count,
            "message": f"已清除 {source} 全部 {cleared_count} 个分类 checkpoint，下次同步将重新全量爬取",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
