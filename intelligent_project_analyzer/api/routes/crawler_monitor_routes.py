"""
爬虫监控&管理后台API

功能：
1. WebSocket实时推送进度&日志
2. 启动/暂停/停止爬虫任务
3. 查看爬虫统计和历史
4. 调整爬虫配置
"""

import asyncio
import threading
from datetime import datetime
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import func as _sqla_func

from ...external_data_system import get_external_db
from ...external_data_system.crawler_scheduler import IntelligentCrawlerScheduler
from ...external_data_system.discovery_manager import ProjectDiscoveryManager
from ...external_data_system.models import ExternalProject
from ...external_data_system.spiders.archdaily_cn_spider import ArchdailyCNSpider
from ...external_data_system.spiders.dezeen_spider import DezeenSpider
from ...external_data_system.spiders.gooood_spider import GoooodSpider
from ..auth_middleware import require_admin

router = APIRouter()

# 全局调度器实例
scheduler: IntelligentCrawlerScheduler | None = None
active_connections: List[WebSocket] = []
# 保存主事件循环引用（在第一次WebSocket连接时捕获）
_main_loop: asyncio.AbstractEventLoop | None = None


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
    category: str | None = None
    limit: int | None = None
    auto_translate: bool = False
    translation_engine: str = "deepseek"
    resume: bool = True


class BatchConfigUpdate(BaseModel):
    """批次配置更新"""

    batch_size: int | None = None
    min_delay: float | None = None
    max_delay: float | None = None
    batch_rest: float | None = None
    max_requests_per_hour: int | None = None
    max_requests_per_day: int | None = None


# ==================== 任务管理 ====================


def _create_spider(source: str):
    """根据数据源创建Spider实例"""
    if source in ("archdaily", "archdaily_cn"):
        return ArchdailyCNSpider()
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

                    # ── primary_category fallback：页面解析未提取时用发现索引分类 ──
                    if not project_data.primary_category and getattr(project, "category", None):
                        project_data.primary_category = project.category

                    with db.get_session() as session:
                        existing = (
                            session.query(ExternalProject).filter(ExternalProject.url == project_data.url).first()
                        )

                        if existing:
                            dm.mark_as_crawled(project.url, success=True)
                            return True

                        is_chinese_source = source in {"gooood"}

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
        # 注意：源名已从 'archdaily' 迁移为 'archdaily_cn'（archdaily_spider.py 已删除）
        for source in ["archdaily_cn", "gooood", "dezeen"]:
            count = session.query(ExternalProject).filter(ExternalProject.source == source).count()
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


# ==================== 失败重试 ====================


class RetryFailedRequest(BaseModel):
    """失败 URL 重试请求"""

    source: str  # archdaily_cn | gooood | dezeen
    max_retries: int = 3  # 最大重试轮次（超过则放弃）
    limit: int = 100  # 本次最多重试条数


@router.post("/retry-failed", dependencies=[Depends(require_admin)], summary="重试失败 URL")
async def retry_failed_urls(request: RetryFailedRequest):
    """
    调用 SpiderManager.retry_failed_urls() 对 project_discovery 表中
    is_crawled=False 且 crawl_attempts < max_retries 的 URL 发起重试。
    在独立线程运行，立即返回，进度通过 WebSocket 推送。
    """
    valid_sources = {"archdaily_cn", "gooood", "dezeen"}
    if request.source not in valid_sources:
        raise HTTPException(status_code=400, detail=f"source 必须是: {', '.join(sorted(valid_sources))}")

    from ...external_data_system.spiders.spider_manager import SpiderManager

    def _run():
        db = get_external_db()
        manager = SpiderManager(db)
        try:
            logger.info(
                f"[retry-failed] 开始重试: {request.source} max_retries={request.max_retries} limit={request.limit}"
            )
            manager.retry_failed_urls(
                source=request.source,
                max_retries=request.max_retries,
                limit=request.limit,
            )
            sync_broadcast_log(
                {"level": "info", "message": f"✓ retry-failed 完成: {request.source}", "source": request.source}
            )
        except Exception as exc:
            logger.error(f"[retry-failed] {request.source} 出错: {exc}")
            sync_broadcast_log({"level": "error", "message": f"retry-failed 失败: {exc}", "source": request.source})

    thread = threading.Thread(target=_run, daemon=True, name=f"retry-{request.source}")
    thread.start()
    return {
        "status": "triggered",
        "source": request.source,
        "max_retries": request.max_retries,
        "limit": request.limit,
        "message": f"已在后台启动重试: {request.source}，进度通过 WebSocket 推送",
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
_CHECKPOINT_FILE = Path(__file__).resolve().parents[3] / "data" / "crawl_checkpoints.json"
_SITE_TOTALS_FILE2 = Path(__file__).resolve().parents[3] / "data" / "category_site_totals.json"

# ── 僵尸运行状态自动检测与恢复 ──────────────────────────────────────────
_STALE_THRESHOLD_SECONDS = 600  # 10 分钟无状态更新认为是僵尸状态


def _auto_recover_stale_state(state: dict) -> bool:
    """
    检测僵尸运行状态：phase 显示 running 但：
      1. last_updated 超过 10 分钟未更新，且
      2. 当前进程中没有活跃的爬虫线程
    如果检测到，自动重置为 idle 并写回文件。
    返回 True 表示进行了修复。
    """
    phase = state.get("phase", "idle")
    if phase not in ("full_crawling", "incremental_crawling"):
        return False

    # 检查是否有活跃的爬虫线程
    crawl_threads = [t for t in threading.enumerate() if t.name and t.name.startswith("manual-") and t.is_alive()]
    if crawl_threads:
        return False  # 确实有线程在跑，不是僵尸

    # 检查 last_updated 是否太久
    last_updated_str = state.get("last_updated")
    if last_updated_str:
        try:
            from datetime import datetime as _dt_stale

            last_updated = _dt_stale.fromisoformat(last_updated_str)
            elapsed = (_dt_stale.now() - last_updated).total_seconds()
            if elapsed < _STALE_THRESHOLD_SECONDS:
                return False  # 最近更新过，可能外部进程在跑
        except Exception:
            pass  # 解析失败，按照僵尸处理

    # ── 确认为僵尸状态，自动修复 ──────────────────────────────────────
    old_phase = state.get("phase")
    old_task = state.get("running_task")
    state["phase"] = "idle"
    state["running_task"] = None
    state["stop_requested"] = False
    from datetime import datetime as _dt_fix

    state["last_updated"] = _dt_fix.now().isoformat()
    try:
        tmp = _SCHEDULE_STATE_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2, default=str)
        tmp.replace(_SCHEDULE_STATE_FILE)
        logger.warning(f"[自动恢复] 检测到僵尸运行状态 (phase={old_phase}, task={old_task})，" f"已自动重置为 idle")
    except Exception as e:
        logger.error(f"[自动恢复] 写回状态文件失败: {e}")
    return True


@router.get("/schedule", summary="获取调度计划状态")
async def get_schedule_state():
    """
    读取 crawl_scheduler.py 持久化的调度状态文件。
    包括：全量爬取进度、上次/下次增量时间、历史记录。
    自动检测并恢复僵尸运行状态（进程崩溃后残留的 running 状态）。
    """
    if not _SCHEDULE_STATE_FILE.exists():
        return {
            "exists": False,
            "message": "调度状态文件不存在，请先启动 scripts/crawl_scheduler.py",
        }
    try:
        with open(_SCHEDULE_STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        _auto_recover_stale_state(data)
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
                    "message": f"数据源 {request.source} 尚未启用，请修改 crawl_scheduler.py 中对应 enabled 为 True",
                }
        except Exception:
            pass  # 无法加载时放行，由调度器内部守卫

    # 检查是否已有调度任务在运行
    if _SCHEDULE_STATE_FILE.exists():
        try:
            with open(_SCHEDULE_STATE_FILE, encoding="utf-8") as f:
                current = json.load(f)
            _auto_recover_stale_state(current)  # 自动修复僵尸状态
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

                    with open(_state_file, encoding="utf-8") as _f:
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


@router.post("/schedule/force-stop", dependencies=[Depends(require_admin)], summary="强制停止当前爬取任务")
async def force_stop_schedule():
    """
    向正在运行的爬取任务发送停止信号，并立即将 phase 重置为 idle。
    爬虫线程会在下一次项目间隔时检测到停止信号并退出。
    """
    if not _SCHEDULE_STATE_FILE.exists():
        return {"status": "ok", "message": "无运行中的任务"}
    try:
        with open(_SCHEDULE_STATE_FILE, encoding="utf-8") as f:
            state = json.load(f)
        phase = state.get("phase", "idle")
        if phase == "idle":
            return {"status": "ok", "message": "当前无运行中的任务"}
        state["stop_requested"] = True
        state["phase"] = "idle"
        state["running_task"] = None
        from datetime import datetime as _dt

        state["last_updated"] = _dt.now().isoformat()
        with open(_SCHEDULE_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        sync_broadcast_log({"level": "warning", "message": "⛔ 用户请求停止爬取，已发送停止信号", "source": "system"})
        return {"status": "ok", "message": "已发送停止信号，爬虫将在当前项目完成后停止"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

    day_of_week: str | None = None  # mon/tue/wed/thu/fri/sat/sun 或 0-6
    hour: int | None = None  # 0-23
    minute: int | None = None  # 0-59
    second: int | None = None  # 0-59


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

        _spider_modules = {
            "archdaily_cn": (
                "intelligent_project_analyzer.external_data_system.spiders.archdaily_cn_spider",
                "ArchdailyCNSpider",
            ),
            "gooood": ("intelligent_project_analyzer.external_data_system.spiders.gooood_spider", "GoooodSpider"),
            "dezeen": ("intelligent_project_analyzer.external_data_system.spiders.dezeen_spider", "DezeenSpider"),
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
            ExternalProject,
            get_external_db,
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
            date_row = (
                sess.query(
                    _func.min(ExternalProject.publish_date),
                    _func.max(ExternalProject.publish_date),
                )
                .filter(
                    ExternalProject.source == source,
                    ExternalProject.publish_date.isnot(None),
                )
                .first()
            )
            if date_row and date_row[0]:
                date_earliest = (
                    date_row[0].strftime("%Y-%m") if hasattr(date_row[0], "strftime") else str(date_row[0])[:7]
                )
                date_latest = (
                    date_row[1].strftime("%Y-%m") if hasattr(date_row[1], "strftime") else str(date_row[1])[:7]
                )
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
        with open(_SCHEDULE_STATE_FILE, encoding="utf-8") as f:
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


@router.get("/schedule/errors", summary="获取爬取错误诊断日志")
async def get_crawl_errors(
    limit: int = 50,
    source: str | None = None,
    error_type: str | None = None,
    hours: int = 24,
):
    """
    获取结构化爬取错误日志，支持按数据源、错误类型、时间范围筛选。

    返回：
    - errors: 最近 N 条错误记录
    - summary: 按 error_type 分组的计数统计
    - diagnosis: 自动诊断建议（基于错误模式）
    """
    import json as _json
    from datetime import datetime as _dt
    from datetime import timedelta as _td
    from pathlib import Path as _Path

    errors_file = _Path(__file__).parents[4] / "data" / "crawler_errors.jsonl"
    all_errors: list = []
    if errors_file.exists():
        try:
            cutoff = (_dt.now() - _td(hours=hours)).isoformat()
            for line in errors_file.read_text(encoding="utf-8").strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    rec = _json.loads(line)
                except _json.JSONDecodeError:
                    continue
                # 时间范围过滤
                if rec.get("ts", "") < cutoff:
                    continue
                # 数据源过滤
                if source and rec.get("source") != source:
                    continue
                # 错误类型过滤
                if error_type and rec.get("error_type") != error_type:
                    continue
                all_errors.append(rec)
        except Exception as e:
            logger.error(f"读取错误日志失败: {e}")

    # 取最近 N 条（倒序）
    recent = list(reversed(all_errors[-limit:]))

    # 按错误类型汇总
    type_counts: dict = {}
    source_counts: dict = {}
    for r in all_errors:
        t = r.get("error_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
        s = r.get("source", "unknown")
        source_counts[s] = source_counts.get(s, 0) + 1

    # 自动诊断建议
    diagnosis: list = []
    total = len(all_errors)
    if total == 0:
        diagnosis.append({"level": "ok", "text": f"最近 {hours} 小时内无爬取错误"})
    else:
        if type_counts.get("timeout", 0) > total * 0.5:
            diagnosis.append(
                {
                    "level": "critical",
                    "text": f"超时错误占比 {type_counts['timeout']}/{total} ({type_counts['timeout']*100//total}%) — 目标网站可能响应缓慢或 Playwright 超时配置过短",
                }
            )
        if type_counts.get("parse_empty", 0) > total * 0.3:
            diagnosis.append(
                {
                    "level": "high",
                    "text": f"解析为空占比 {type_counts['parse_empty']}/{total} — 页面可能是 SPA 未渲染完成，检查 wait_for_selector 设置",
                }
            )
        if type_counts.get("validation_failed", 0) > total * 0.3:
            diagnosis.append(
                {
                    "level": "high",
                    "text": f"数据验证失败占比 {type_counts['validation_failed']}/{total} — 描述提取逻辑可能需要调整",
                }
            )
        if type_counts.get("http_error", 0) > 3:
            diagnosis.append(
                {
                    "level": "high",
                    "text": f"HTTP 错误 {type_counts['http_error']} 次 — 可能触发了反爬保护 (403/429/503)，需增加请求间隔",
                }
            )
        if type_counts.get("network_error", 0) > 3:
            diagnosis.append(
                {
                    "level": "medium",
                    "text": f"网络错误 {type_counts['network_error']} 次 — 检查网络连接或目标站点是否可达",
                }
            )
        if not diagnosis:
            diagnosis.append(
                {
                    "level": "info",
                    "text": f"最近 {hours} 小时共 {total} 个错误，无明显异常模式",
                }
            )

    return {
        "errors": recent,
        "total": total,
        "summary": {
            "by_type": type_counts,
            "by_source": source_counts,
        },
        "diagnosis": diagnosis,
    }


@router.get("/schedule/alerts", summary="获取爬虫告警（熔断、连续失败等）")
async def get_crawler_alerts(limit: int = 20):
    """获取爬虫告警记录，最近 N 条"""
    import json as _json
    from pathlib import Path as _Path

    alert_file = _Path(__file__).parents[4] / "data" / "crawler_alerts.jsonl"
    alerts = []
    if alert_file.exists():
        try:
            lines = alert_file.read_text(encoding="utf-8").strip().split("\n")
            for line in reversed(lines[-limit:]):
                if line.strip():
                    alerts.append(_json.loads(line))
        except Exception as e:
            logger.error(f"读取告警文件失败: {e}")
    return {"alerts": alerts}


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
                "archdaily_cn": (
                    "intelligent_project_analyzer.external_data_system.spiders.archdaily_cn_spider",
                    "ArchdailyCNSpider",
                ),
                "gooood": ("intelligent_project_analyzer.external_data_system.spiders.gooood_spider", "GoooodSpider"),
                "dezeen": ("intelligent_project_analyzer.external_data_system.spiders.dezeen_spider", "DezeenSpider"),
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
            "archdaily_cn": (
                "intelligent_project_analyzer.external_data_system.spiders.archdaily_cn_spider",
                "ArchdailyCNSpider",
            ),
            "gooood": ("intelligent_project_analyzer.external_data_system.spiders.gooood_spider", "GoooodSpider"),
            "dezeen": ("intelligent_project_analyzer.external_data_system.spiders.dezeen_spider", "DezeenSpider"),
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
            ExternalProject,
            get_external_db,
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
                sess.query(_func.max(ExternalProject.crawled_at)).filter(ExternalProject.source == source).scalar()
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
            _auto_recover_stale_state(state5)  # 自动修复僵尸状态
            phase5 = state5.get("phase", "idle")
            is_running = phase5 in ("full_crawling", "incremental_crawling")
            src_state5 = state5.get("sources", {}).get(source, {})
            incr5 = src_state5.get("incremental", {})
            # 优先取最近一条 history 的 completed_at（最精确的完成时间）
            history5 = incr5.get("history", [])
            if history5 and history5[0].get("completed_at"):
                last_sync = history5[0]["completed_at"]
            elif incr5.get("last_run_at"):
                last_sync = incr5["last_run_at"]
    except Exception as e:
        logger.warning(f"[source-status] 读取 schedule_state 失败: {e}")

    # ── 组合结果 ─────────────────────────────────────────────────────────
    cat_list = []
    for cat_name, cat_url in categories_meta.items():
        ckpt_raw = checkpoints.get(cat_name)
        cat_list.append(
            {
                "name": cat_name,
                "url": cat_url,
                "db_count": cat_db_counts.get(cat_name, 0),
                "site_total": site_totals.get(cat_name),
                "has_checkpoint": cat_name in checkpoints,
                "checkpoint_url": ckpt_raw,
            }
        )

    site_total_estimated = sum(v for v in site_totals.values() if isinstance(v, int | float))

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


# ==================== 质检清单 ====================


def _build_quality_query(session, source: str | None, category: str | None, keyword: str | None):
    """构建质检查询（共享逻辑）"""
    q = session.query(ExternalProject)
    if source:
        q = q.filter(ExternalProject.source == source)
    if category:
        q = q.filter(ExternalProject.primary_category == category)
    if keyword:
        q = q.filter(ExternalProject.title.ilike(f"%{keyword}%"))
    return q


@router.get("/quality-list", summary="质检清单：爬取成功的项目列表")
async def get_quality_list(
    source: str | None = Query(None, description="数据源过滤：archdaily_cn / gooood / dezeen"),
    category: str | None = Query(None, description="分类过滤"),
    keyword: str | None = Query(None, description="标题关键词搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=10, le=200, description="每页条数"),
    sort: str = Query("crawled_at", description="排序字段：crawled_at / publish_date / title"),
    order: str = Query("desc", description="排序方向：asc / desc"),
):
    """
    返回已成功爬取入库的项目清单，用于数据质检。
    包含：标题、URL、数据源、分类、爬取时间、发布日期、质量评分等。
    """
    db = get_external_db()
    with db.get_session() as session:
        q = _build_quality_query(session, source, category, keyword)

        # 统计
        total = q.count()

        # 分源统计
        source_counts_raw = (
            session.query(ExternalProject.source, _sqla_func.count(ExternalProject.id))
            .group_by(ExternalProject.source)
            .all()
        )
        source_counts = {s: c for s, c in source_counts_raw}

        # 分类统计（取当前源）
        cat_query = session.query(ExternalProject.primary_category, _sqla_func.count(ExternalProject.id))
        if source:
            cat_query = cat_query.filter(ExternalProject.source == source)
        cat_counts_raw = cat_query.group_by(ExternalProject.primary_category).all()
        category_counts = {c or "(无分类)": n for c, n in cat_counts_raw}

        # 排序
        sort_col_map = {
            "crawled_at": ExternalProject.crawled_at,
            "publish_date": ExternalProject.publish_date,
            "title": ExternalProject.title,
            "quality_score": ExternalProject.quality_score,
            "source": ExternalProject.source,
        }
        sort_col = sort_col_map.get(sort, ExternalProject.crawled_at)
        if order == "asc":
            q = q.order_by(sort_col.asc().nullslast())
        else:
            q = q.order_by(sort_col.desc().nullslast())

        # 分页
        offset = (page - 1) * page_size
        projects = q.offset(offset).limit(page_size).all()

        items = []
        for p in projects:
            items.append(
                {
                    "id": p.id,
                    "source": p.source,
                    "title": p.title or p.title_zh or p.title_en or "(无标题)",
                    "title_zh": p.title_zh,
                    "title_en": p.title_en,
                    "url": p.url,
                    "primary_category": p.primary_category or "",
                    "publish_date": p.publish_date.strftime("%Y-%m-%d") if p.publish_date else None,
                    "crawled_at": p.crawled_at.strftime("%Y-%m-%d %H:%M") if p.crawled_at else None,
                    "quality_score": round(p.quality_score, 2) if p.quality_score else None,
                    "has_description": bool(p.description or p.description_zh or p.description_en),
                    "image_count": len(p.images) if p.images else 0,
                    "year": p.year,
                    "area_sqm": p.area_sqm,
                }
            )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
        "source_counts": source_counts,
        "category_counts": category_counts,
    }


@router.get("/quality-list/export", summary="导出质检清单为 TXT")
async def export_quality_list_txt(
    source: str | None = Query(None, description="数据源过滤"),
    category: str | None = Query(None, description="分类过滤"),
    keyword: str | None = Query(None, description="标题关键词搜索"),
):
    """
    导出所有符合条件的爬取成功项目为 TXT 文件。
    格式：序号 | 爬取日期 | 数据源 | 分类 | 标题 | URL
    """
    return _build_quality_export(
        source=source,
        category=category,
        keyword=keyword,
        ids=None,
    )


class _QualityExportByIds(BaseModel):
    ids: list[int]


@router.post("/quality-list/export", summary="按选中 ID 导出质检清单为 TXT")
async def export_quality_list_txt_by_ids(body: _QualityExportByIds):
    """
    导出用户勾选的项目为 TXT 文件。
    前端传入 { "ids": [1, 2, 3] }。
    """
    return _build_quality_export(ids=body.ids)


def _build_quality_export(
    *,
    source: str | None = None,
    category: str | None = None,
    keyword: str | None = None,
    ids: list[int] | None = None,
) -> PlainTextResponse:
    db = get_external_db()
    with db.get_session() as session:
        if ids:
            # 按指定 ID 查询
            q = session.query(ExternalProject).filter(ExternalProject.id.in_(ids))
        else:
            q = _build_quality_query(session, source, category, keyword)
        q = q.order_by(ExternalProject.crawled_at.desc().nullslast())
        projects = q.all()

        # ⚠️ 必须在 session 内访问 ORM 属性，否则 DetachedInstanceError
        lines = []
        lines.append("=" * 100)
        lines.append(f"爬取数据质检清单    导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        filter_parts = []
        if ids:
            filter_parts.append(f"手动选中 {len(ids)} 项")
        if source:
            filter_parts.append(f"数据源={source}")
        if category:
            filter_parts.append(f"分类={category}")
        if keyword:
            filter_parts.append(f"关键词={keyword}")
        lines.append(f"筛选条件: {', '.join(filter_parts) if filter_parts else '全部'}")
        lines.append(f"总计: {len(projects)} 条记录")
        lines.append("=" * 100)
        lines.append("")
        lines.append(f"{'序号':<6} {'爬取日期':<18} {'数据源':<15} {'分类':<12} {'质量':<6} {'标题'}")
        lines.append("-" * 100)

        for idx, p in enumerate(projects, 1):
            crawled = p.crawled_at.strftime("%Y-%m-%d %H:%M") if p.crawled_at else "未知"
            title = p.title or p.title_zh or p.title_en or "(无标题)"
            cat = p.primary_category or "-"
            qs = f"{p.quality_score:.1f}" if p.quality_score is not None else "-"
            desc_raw = p.description_zh or p.description or p.description_en or ""
            desc_len = len(desc_raw.strip())
            desc_tag = f" [描述: {desc_len}字]" if desc_len > 0 else " [无描述]"
            lines.append(f"{idx:<6} {crawled:<18} {p.source:<15} {cat:<12} {qs:<6} {title}{desc_tag}")
            lines.append(f"       URL: {p.url}")
            if p.publish_date:
                lines.append(f"       发布日期: {p.publish_date.strftime('%Y-%m-%d')}")
            # 建筑师
            if p.architects:
                arch_names = []
                for a in p.architects if isinstance(p.architects, list) else []:
                    name = a.get("name", "") if isinstance(a, dict) else str(a)
                    if name:
                        arch_names.append(name)
                if arch_names:
                    lines.append(f"       建筑师: {', '.join(arch_names)}")
            # 地点
            if p.location:
                loc = p.location if isinstance(p.location, dict) else {}
                loc_parts = [v for v in [loc.get("country"), loc.get("city")] if v]
                if loc_parts:
                    lines.append(f"       地点: {', '.join(loc_parts)}")
            # 面积 & 年份
            detail_parts = []
            if p.area_sqm:
                detail_parts.append(f"面积: {p.area_sqm:.0f}㎡")
            if p.year:
                detail_parts.append(f"年份: {p.year}")
            if detail_parts:
                lines.append(f"       {' | '.join(detail_parts)}")
            # 描述（完整版）
            desc = p.description_zh or p.description or p.description_en or ""
            if desc:
                desc_clean = desc.strip()
                lines.append(f"       描述: {desc_clean}")
            # 图片 & 标签
            img_count = len(p.images) if p.images else 0
            tags = p.tags if isinstance(p.tags, list) else []
            meta_parts = []
            if img_count > 0:
                meta_parts.append(f"图片: {img_count}张")
            if tags:
                meta_parts.append(f"标签: {', '.join(str(t) for t in tags[:5])}")
            if meta_parts:
                lines.append(f"       {' | '.join(meta_parts)}")
            lines.append("")

        lines.append("=" * 100)
        lines.append(f"--- 结束 ({len(projects)} 条) ---")
        len(projects)

    content = "\n".join(lines)

    # 生成文件名
    fname_parts = ["crawl_quality"]
    if ids:
        fname_parts.append(f"selected_{len(ids)}")
    if source:
        fname_parts.append(source)
    if category:
        fname_parts.append(category)
    fname_parts.append(datetime.now().strftime("%Y%m%d_%H%M%S"))
    filename = "_".join(fname_parts) + ".txt"

    return PlainTextResponse(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
