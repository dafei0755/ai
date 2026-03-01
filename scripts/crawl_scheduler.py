"""
多网站全量 + 每周增量爬取调度器

支持的网站:
    archdaily_cn  每周一 02:00 增量
    gooood        每周二 02:00 增量
    dezeen        每周三 02:00 增量

运行方式:
    python scripts/crawl_scheduler.py daemon          # 启动持续守护进程
    python scripts/crawl_scheduler.py full            # 所有源全量爬取
    python scripts/crawl_scheduler.py full archdaily_cn  # 指定源全量
    python scripts/crawl_scheduler.py incr archdaily_cn  # 指定源增量
    python scripts/crawl_scheduler.py status          # 查看状态JSON

设计原则:
    1. 每个网站独立状态跟踪（全量进度 + 增量历史）
    2. 全量按分类串行，断点续爬（已完成分类跳过）
    3. 增量：每分类 max_pages 小 + 连续N条已知URL早停
    4. 反爬：分类间/网站间随机休息
    5. 不同网站错开不同星期几执行，避免同时撞服务器
"""

import sys
import os
import json
import time
import random
import signal
import importlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault(
    "EXTERNAL_DB_URL",
    "postgresql://postgres:password@localhost:5432/external_projects",
)

from loguru import logger

LOG_FILE = ROOT / "logs" / "crawl_scheduler.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logger.add(
    LOG_FILE,
    rotation="50 MB",
    retention="30 days",
    encoding="utf-8",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
)

STATE_DIR = ROOT / "data" / "crawler_state"
STATE_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = STATE_DIR / "schedule_state.json"

# ================== 多网站配置 ==========================================

SOURCES: Dict[str, Dict[str, Any]] = {
    "archdaily_cn": {
        "display_name": "ArchDaily 中文站",
        "enabled": True,  # ✅ 已开放
        "module": "intelligent_project_analyzer.external_data_system.spiders.archdaily_cn_spider",
        "class": "ArchdailyCNSpider",
        "full_max_pages": 200,
        "incr_max_pages": 5,
        "incr_stop_consecutive": 10,
        "inter_category_rest": (60, 120),
        "incr_schedule": {"day_of_week": "mon", "hour": 2, "minute": 0},
        "incr_schedule_label": "每周一 02:00",
    },
    "gooood": {
        "display_name": "谷德 gooood.cn",
        "enabled": True,  # ✅ 已开放
        "module": "intelligent_project_analyzer.external_data_system.spiders.gooood_spider",
        "class": "GoooodSpider",
        "full_max_pages": 100,
        "incr_max_pages": 5,
        "incr_stop_consecutive": 5,
        "inter_category_rest": (90, 180),
        "incr_schedule": {"day_of_week": "tue", "hour": 2, "minute": 0},
        "incr_schedule_label": "每周二 02:00",
    },
    "dezeen": {
        "display_name": "Dezeen",
        "enabled": False,  # 🔒 待开放（archdaily_cn 完成后启用）
        "module": "intelligent_project_analyzer.external_data_system.spiders.dezeen_spider",
        "class": "DezeenSpider",
        "full_max_pages": 100,
        "incr_max_pages": 5,
        "incr_stop_consecutive": 5,
        "inter_category_rest": (90, 180),
        "incr_schedule": {"day_of_week": "wed", "hour": 2, "minute": 0},
        "incr_schedule_label": "每周三 02:00",
    },
}

# ================== 状态管理（v2 多网站结构）============================


def _initial_source_state() -> Dict[str, Any]:
    return {
        "added_at": datetime.now().isoformat(),  # 记录该源被加入的时间
        "full_crawl": {
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            # 启动时快照：目标分类、基线数据条数、扫描时间
            "target_categories": None,  # List[str]，全量开始时从 spider 获取
            "total_categories": None,  # int，目标分类总数
            "baseline_count": None,  # int，全量开始前 DB 已有条数
            "scan_at": None,  # ISO时间，基线扫描时间
            "categories_done": [],
            "category_stats": {},
            "total_stats": {"total": 0, "new": 0, "skipped": 0, "failed": 0},
            "error": None,
        },
        "incremental": {
            "last_run_at": None,
            "next_run_at": None,
            "history": [],
        },
    }


def _initial_state() -> Dict[str, Any]:
    return {
        "version": 2,
        "phase": "idle",
        "running_task": None,
        "sources": {src: _initial_source_state() for src in SOURCES},
        "last_updated": None,
    }


def _migrate_v1_to_v2(old: Dict[str, Any]) -> Dict[str, Any]:
    state = _initial_state()
    if "full_crawl" in old:
        state["sources"]["archdaily_cn"]["full_crawl"] = old["full_crawl"]
    if "incremental" in old:
        state["sources"]["archdaily_cn"]["incremental"] = old["incremental"]
    state["phase"] = old.get("phase", "idle")
    state["running_task"] = old.get("running_task")
    logger.info("状态文件已从 v1 迁移到 v2（多网站结构）")
    return state


def _load_state() -> Dict[str, Any]:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("version") != 2:
                data = _migrate_v1_to_v2(data)
                _save_state(data)
            for src in SOURCES:
                if src not in data.get("sources", {}):
                    data.setdefault("sources", {})[src] = _initial_source_state()
            return data
        except Exception as e:
            logger.warning(f"状态文件损坏，重置: {e}")
    return _initial_state()


def _save_state(state: Dict[str, Any]):
    state["last_updated"] = datetime.now().isoformat()
    try:
        tmp = STATE_FILE.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2, default=str)
        tmp.replace(STATE_FILE)
    except Exception as e:
        logger.error(f"保存状态失败: {e}")


def _get_source_state(state: Dict, source_name: str) -> Dict:
    if source_name not in state.get("sources", {}):
        state.setdefault("sources", {})[source_name] = _initial_source_state()
    return state["sources"][source_name]


# ================== 爬虫辅助 ==========================================


def _get_spider_instance(source_name: str):
    cfg = SOURCES[source_name]
    mod = importlib.import_module(cfg["module"])
    cls = getattr(mod, cfg["class"])
    return cls()


def _query_cat_stats(manager, source_name: str, cat_name: str) -> Dict:
    from sqlalchemy import func
    from intelligent_project_analyzer.external_data_system.models.external_projects import ExternalProject

    with manager.db.get_session() as session:
        cnt = (
            session.query(func.count(ExternalProject.id))
            .filter(
                ExternalProject.source == source_name,
                ExternalProject.primary_category == cat_name,
            )
            .scalar()
        )
    return {"db_count": cnt or 0}


# ================== 全量爬取 ==========================================


def _run_full_crawl(source_name: str = "archdaily_cn"):
    if source_name not in SOURCES:
        logger.error(f"未知网站: {source_name}，可用: {list(SOURCES.keys())}")
        return
    cfg = SOURCES[source_name]
    if not cfg.get("enabled", True):
        logger.warning(f"[{source_name}] 该数据源尚未启用，跳过全量爬取")
        return
    from intelligent_project_analyzer.external_data_system.spiders.spider_manager import SpiderManager

    state = _load_state()
    src_state = _get_source_state(state, source_name)
    fc = src_state["full_crawl"]

    if fc["status"] == "completed":
        logger.warning(f"[{source_name}] 全量已完成，如需重跑请先重置")
        return

    fc["status"] = "running"
    fc["started_at"] = fc.get("started_at") or datetime.now().isoformat()
    state["phase"] = "full_crawling"
    state["running_task"] = f"全量爬取 {cfg['display_name']}"
    _save_state(state)

    manager = SpiderManager()
    spider = _get_spider_instance(source_name)
    manager.register_spider(spider)
    all_categories = spider.get_categories()
    categories_done: List[str] = fc.get("categories_done", [])

    # ── 启动基线快照（仅首次，重试时保留已有快照）──────────────────────
    if not fc.get("scan_at"):
        fc["target_categories"] = list(all_categories.keys())
        fc["total_categories"] = len(all_categories)
        fc["scan_at"] = datetime.now().isoformat()
        try:
            from sqlalchemy import func as sqla_func
            from intelligent_project_analyzer.external_data_system.models.external_projects import ExternalProject

            with manager.db.get_session() as _sess:
                fc["baseline_count"] = (
                    _sess.query(sqla_func.count(ExternalProject.id))
                    .filter(ExternalProject.source == source_name)
                    .scalar()
                    or 0
                )
        except Exception as _e:
            logger.warning(f"[{source_name}] 基线条数查询失败: {_e}")
            fc["baseline_count"] = None
        _save_state(state)
        logger.info(
            f"[{source_name}] 基线快照: {fc['total_categories']} 个分类, "
            f"DB已有 {fc['baseline_count']} 条, 扫描时间 {fc['scan_at'][:19]}"
        )

    logger.info(f"[{source_name}] 全量开始  {len(all_categories)} 分类，已完成: {len(categories_done)}")

    for cat_name, cat_url in all_categories.items():
        if cat_name in categories_done:
            logger.info(f"   跳过: {cat_name}")
            continue
        logger.info(f" [{source_name}] {cat_name} ")
        state["running_task"] = f"全量 {cfg['display_name']} [{cat_name}]"
        _save_state(state)
        try:
            ok = manager.sync_source(
                source=source_name,
                category=cat_name,
                max_pages=cfg["full_max_pages"],
                max_items=None,
            )
            cat_status = "completed" if ok else "failed"
        except Exception as e:
            logger.error(f"分类 {cat_name} 异常: {e}")
            cat_status = "failed"

        if cat_name not in fc["categories_done"]:
            fc["categories_done"].append(cat_name)
        try:
            cat_stats = {"status": cat_status, **_query_cat_stats(manager, source_name, cat_name)}
            # 加入网站已知文章数（用于前端进度展示）
            if hasattr(spider, "CATEGORY_TOTALS") and cat_name in spider.CATEGORY_TOTALS:
                cat_stats["site_total"] = spider.CATEGORY_TOTALS[cat_name]
            fc["category_stats"][cat_name] = cat_stats
        except Exception:
            fc["category_stats"][cat_name] = {"status": cat_status}
        _save_state(state)

        cat_keys = list(all_categories.keys())
        if cat_name != cat_keys[-1]:
            rest = random.uniform(*cfg["inter_category_rest"])
            logger.info(f"  休息 {rest:.0f}s ...")
            time.sleep(rest)

    fc["status"] = "completed"
    fc["completed_at"] = datetime.now().isoformat()
    state["phase"] = "idle"
    state["running_task"] = None
    _save_state(state)
    logger.success(f"[{source_name}] 全量爬取完成！")


def _run_full_crawl_all():
    """依次对所有 **已启用** 的数据源执行全量爬取（跳过已完成或未启用的）"""
    source_list = [src for src, cfg in SOURCES.items() if cfg.get("enabled", True)]
    for i, src in enumerate(source_list):
        state = _load_state()
        if _get_source_state(state, src)["full_crawl"]["status"] == "completed":
            logger.info(f"[{src}] 全量已完成，跳过")
            continue
        logger.info(f"===== {i+1}/{len(source_list)}: {src} =====")
        _run_full_crawl(src)
        if i < len(source_list) - 1:
            rest = random.uniform(120, 300)
            logger.info(f"网站间休息 {rest:.0f}s ...")
            time.sleep(rest)
    logger.success("所有网站全量完成！")


# ================== 增量爬取 ==========================================


def _run_incremental_crawl(source_name: str = "archdaily_cn"):
    if source_name not in SOURCES:
        logger.error(f"未知网站: {source_name}")
        return
    cfg = SOURCES[source_name]
    if not cfg.get("enabled", True):
        logger.warning(f"[{source_name}] 该数据源尚未启用，跳过增量爬取")
        return
    from intelligent_project_analyzer.external_data_system.spiders.spider_manager import SpiderManager

    # 全量/增量两阶段模式已废弃，统一使用 checkpoint 机制：
    # - 有 checkpoint：从上次断点继续
    # - 无 checkpoint（首次或已清空）：从第 1 页重新爬取
    # 「清空并重新爬取」只需清空 checkpoint 再触发本函数即可
    run_start = datetime.now()
    state = _load_state()
    state["phase"] = "incremental_crawling"
    state["running_task"] = f"增量爬取 {cfg['display_name']}"
    _save_state(state)

    logger.info(f"[{source_name}] 增量开始: {run_start.strftime('%Y-%m-%d %H:%M')}")

    manager = SpiderManager()
    spider = _get_spider_instance(source_name)
    manager.register_spider(spider)
    # 记录同步前条数（用于统计新增量）
    total_before = 0
    try:
        from sqlalchemy import func
        from intelligent_project_analyzer.external_data_system.models.external_projects import ExternalProject

        with manager.db.get_session() as session:
            total_before = (
                session.query(func.count(ExternalProject.id)).filter(ExternalProject.source == source_name).scalar()
                or 0
            )
    except Exception:
        pass

    try:
        # 停止标志：API 可设置 stop_requested=True 通知此线程退出
        _state_now = _load_state()
        _state_now["stop_requested"] = False
        _save_state(_state_now)

        ok = manager.sync_source(
            source=source_name,
            category=None,
            max_pages=cfg["incr_max_pages"],
            max_items=None,
            stop_check=lambda: _load_state().get("stop_requested", False),
        )
        if _load_state().get("stop_requested", False):
            logger.warning(f"[{source_name}] 收到停止信号，提前结束")
            status = "stopped"
        else:
            status = "completed" if ok else "failed"
    except Exception as e:
        logger.error(f"[{source_name}] 增量异常: {e}")
        status = "failed"

    run_end = datetime.now()
    duration = (run_end - run_start).total_seconds()

    new_count = 0
    try:
        from sqlalchemy import func
        from intelligent_project_analyzer.external_data_system.models.external_projects import ExternalProject

        with manager.db.get_session() as session:
            total_after = (
                session.query(func.count(ExternalProject.id)).filter(ExternalProject.source == source_name).scalar()
                or 0
            )
        new_count = max(0, total_after - total_before)
    except Exception:
        pass

    run_record = {
        "run_at": run_start.isoformat(),
        "completed_at": run_end.isoformat(),
        "status": status,
        "duration_sec": round(duration, 1),
        "new_items": new_count,
    }

    state = _load_state()
    src_state = _get_source_state(state, source_name)
    incr = src_state["incremental"]
    incr["last_run_at"] = run_end.isoformat()
    incr["history"].insert(0, run_record)
    incr["history"] = incr["history"][:20]
    state["phase"] = "idle"
    state["running_task"] = None
    _save_state(state)
    logger.success(f"[{source_name}] 增量完成！新增约 {new_count} 条，耗时 {duration:.0f}s")


# ================== APScheduler 守护进程 ==============================


def _update_next_run_times():
    now = datetime.now()
    state = _load_state()
    day_map = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    for src_name, cfg in SOURCES.items():
        sched = cfg["incr_schedule"]
        target_wd = day_map.index(sched["day_of_week"])
        current_wd = now.weekday()
        days_ahead = (target_wd - current_wd) % 7
        if days_ahead == 0 and (
            now.hour > sched["hour"] or (now.hour == sched["hour"] and now.minute >= sched["minute"])
        ):
            days_ahead = 7
        next_run = (now + timedelta(days=days_ahead)).replace(
            hour=sched["hour"], minute=sched["minute"], second=0, microsecond=0
        )
        src_state = _get_source_state(state, src_name)
        src_state["incremental"]["next_run_at"] = next_run.isoformat()
        logger.info(f"[{src_name}] 下次增量: {next_run.strftime('%Y-%m-%d %H:%M')}")
    _save_state(state)


def run_scheduler():
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error("APScheduler 未安装，请运行: pip install APScheduler")
        sys.exit(1)

    scheduler = BlockingScheduler(timezone="Asia/Shanghai")

    # ── 为每个源注册每周增量任务 ─────────────────────────────────────────
    # 统一使用 checkpoint 机制，不再区分全量/增量两阶段
    for src_name, cfg in SOURCES.items():
        if not cfg.get("enabled", True):
            logger.info(f"[{src_name}] 未启用，跳过注册")
            continue
        sched = cfg["incr_schedule"]
        scheduler.add_job(
            func=lambda s=src_name: _run_incremental_crawl(s),
            trigger=CronTrigger(
                day_of_week=sched["day_of_week"],
                hour=sched["hour"],
                minute=sched["minute"],
                timezone="Asia/Shanghai",
            ),
            id=f"{src_name}_weekly_incr",
            name=f"{cfg['display_name']} 每周同步",
            max_instances=1,
            misfire_grace_time=3600,
        )
        logger.info(f"[{src_name}] 注册定时任务: {cfg['incr_schedule_label']}")

    _update_next_run_times()

    def _shutdown(sig, frame):
        logger.info("收到退出信号，调度器关闭中...")
        scheduler.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    logger.info("调度守护进程已启动，等待计划任务...")
    scheduler.start()


# ================== 入口 ==============================================

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "daemon"
    src_arg = sys.argv[2] if len(sys.argv) > 2 else None

    if cmd == "full":
        if src_arg:
            _run_full_crawl(src_arg)
        else:
            _run_full_crawl_all()
    elif cmd == "incr":
        _run_incremental_crawl(src_arg or "archdaily_cn")
    elif cmd == "status":
        state = _load_state()
        print(json.dumps(state, ensure_ascii=False, indent=2, default=str))
    elif cmd == "daemon":
        run_scheduler()
    else:
        print(f"用法: python scripts/crawl_scheduler.py [daemon|full [source]|incr [source]|status]")
        print(f"可用 source: {', '.join(SOURCES.keys())}")
        sys.exit(1)
