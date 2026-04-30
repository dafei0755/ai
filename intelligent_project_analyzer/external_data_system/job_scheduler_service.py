"""
APScheduler BackgroundScheduler 单例服务

运行在 FastAPI 进程内，可通过 API 查看/修改/监控定时任务。
默认注册任务（每个数据源独立调度，时间错开）：
  - archdaily_cn_weekly_incr: 每周一 02:00 增量爬取 archdaily.cn
  - gooood_weekly_incr:       每周二 02:00 增量爬取谷德设计网
  - dezeen_weekly_incr:       每周三 02:00 增量爬取 Dezeen
"""

from __future__ import annotations

import importlib.util
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.job import Job
from loguru import logger

_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
_CRAWL_SCHEDULER_FILE = _SCRIPTS_DIR / "crawl_scheduler.py"


def _load_crawl_scheduler_module():
    """动态加载 scripts/crawl_scheduler.py（避免循环导入）"""
    spec = importlib.util.spec_from_file_location("crawl_scheduler", _CRAWL_SCHEDULER_FILE)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _run_incremental_job(source_name: str = "archdaily_cn"):
    """APScheduler job 函数：执行增量爬取（指定数据源）"""
    logger.info(f"[JobScheduler] 启动定时增量爬取: {source_name}")
    try:
        mod = _load_crawl_scheduler_module()
        mod._run_incremental_crawl(source_name)
        logger.info(f"[JobScheduler] 增量爬取完成: {source_name}")
    except Exception as exc:
        logger.error(f"[JobScheduler] 增量爬取失败 ({source_name}): {exc}")


def _run_full_job(source_name: str = "archdaily_cn"):
    """APScheduler job 函数：执行全量爬取（指定数据源）"""
    logger.info(f"[JobScheduler] 启动全量爬取: {source_name}")
    try:
        mod = _load_crawl_scheduler_module()
        mod._run_full_crawl(source_name)
        logger.info(f"[JobScheduler] 全量爬取完成: {source_name}")
    except Exception as exc:
        logger.error(f"[JobScheduler] 全量爬取失败 ({source_name}): {exc}")


def _job_to_dict(job: Job) -> Dict[str, Any]:
    """将 APScheduler Job 序列化为 dict"""
    trigger = job.trigger
    trigger_str = str(trigger)

    next_run: Optional[str] = None
    if job.next_run_time:
        next_run = job.next_run_time.isoformat()

    # 解析 CronTrigger 字段供前端展示/编辑
    cron_fields: Dict[str, str] = {}
    if isinstance(trigger, CronTrigger):
        for field in trigger.fields:
            cron_fields[field.name] = str(field)

    status = "paused" if job.next_run_time is None else "active"

    return {
        "id": job.id,
        "name": job.name,
        "trigger_type": type(trigger).__name__,
        "trigger_str": trigger_str,
        "cron_fields": cron_fields,
        "next_run_time": next_run,
        "status": status,
        "max_instances": job.max_instances,
        "misfire_grace_time": job.misfire_grace_time,
    }


class JobSchedulerService:
    """APScheduler BackgroundScheduler 单例，运行在 FastAPI 进程内"""

    _instance: Optional["JobSchedulerService"] = None
    _lock = threading.Lock()

    # ----------------------------- 单例 -----------------------------

    @classmethod
    def get_instance(cls) -> "JobSchedulerService":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ----------------------------- 初始化 ---------------------------

    def __init__(self):
        self._scheduler = BackgroundScheduler(
            timezone="Asia/Shanghai",
            job_defaults={
                "coalesce": True,       # 积压时只执行一次
                "max_instances": 1,
                "misfire_grace_time": 3600,  # 错过1小时内可补执行
            },
        )
        self._register_default_jobs()

    # 各数据源增量调度配置
    _SOURCE_SCHEDULES = [
        {
            "source": "archdaily_cn",
            "display_name": "archdaily.cn",
            "enabled": True,
            "day_of_week": "mon",
            "hour": 2,
            "minute": 0,
            "label": "每周一 02:00",
        },
        {
            "source": "gooood",
            "display_name": "谷德设计网",
            "enabled": False,   # 待开放
            "day_of_week": "tue",
            "hour": 2,
            "minute": 0,
            "label": "每周二 02:00",
        },
        {
            "source": "dezeen",
            "display_name": "Dezeen",
            "enabled": False,   # 待开放
            "day_of_week": "wed",
            "hour": 2,
            "minute": 0,
            "label": "每周三 02:00",
        },
    ]

    def _register_default_jobs(self):
        """注册所有 **已启用** 数据源的默认增量调度任务"""
        registered = 0
        for cfg in self._SOURCE_SCHEDULES:
            if not cfg.get("enabled", True):
                logger.info(f"[JobScheduler] 跳过未启用源: {cfg['source']}")
                continue
            source = cfg["source"]
            job_id = f"{source}_weekly_incr"
            self._scheduler.add_job(
                func=_run_incremental_job,
                args=[source],
                trigger=CronTrigger(
                    day_of_week=cfg["day_of_week"],
                    hour=cfg["hour"],
                    minute=cfg["minute"],
                    timezone="Asia/Shanghai",
                ),
                id=job_id,
                name=f"{cfg['display_name']} 每周增量爬取",
                max_instances=1,
                coalesce=True,
                replace_existing=True,
            )
            logger.info(f"[JobScheduler] 默认任务已注册: {job_id} ({cfg['label']})")
            registered += 1
        logger.info(f"[JobScheduler] 共注册 {registered} 个增量调度任务")

    # ----------------------------- 生命周期 -------------------------

    def start(self):
        """启动 BackgroundScheduler（FastAPI lifespan 调用）"""
        if not self._scheduler.running:
            self._scheduler.start()
            logger.info("[JobScheduler] BackgroundScheduler 已启动")

    def shutdown(self, wait: bool = False):
        """关闭 BackgroundScheduler（FastAPI lifespan 调用）"""
        if self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            logger.info("[JobScheduler] BackgroundScheduler 已关闭")

    # ----------------------------- 查询 ----------------------------

    def get_jobs(self) -> List[Dict[str, Any]]:
        """列出所有任务"""
        return [_job_to_dict(j) for j in self._scheduler.get_jobs()]

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """查询单个任务"""
        job = self._scheduler.get_job(job_id)
        if job is None:
            return None
        return _job_to_dict(job)

    def is_running(self) -> bool:
        return self._scheduler.running

    # ----------------------------- 控制 ----------------------------

    def pause_job(self, job_id: str) -> Dict[str, Any]:
        """暂停任务"""
        job = self._scheduler.get_job(job_id)
        if job is None:
            raise ValueError(f"任务不存在: {job_id}")
        self._scheduler.pause_job(job_id)
        logger.info(f"[JobScheduler] 任务已暂停: {job_id}")
        return _job_to_dict(self._scheduler.get_job(job_id))

    def resume_job(self, job_id: str) -> Dict[str, Any]:
        """恢复任务"""
        job = self._scheduler.get_job(job_id)
        if job is None:
            raise ValueError(f"任务不存在: {job_id}")
        self._scheduler.resume_job(job_id)
        logger.info(f"[JobScheduler] 任务已恢复: {job_id}")
        return _job_to_dict(self._scheduler.get_job(job_id))

    def run_job_now(self, job_id: str) -> Dict[str, Any]:
        """立即执行一次（不影响常规调度）"""
        job = self._scheduler.get_job(job_id)
        if job is None:
            raise ValueError(f"任务不存在: {job_id}")
        self._scheduler.add_job(
            func=job.func,
            trigger=DateTrigger(run_date=datetime.now(tz=self._scheduler.timezone)),
            id=f"{job_id}__manual_{int(datetime.now().timestamp())}",
            name=f"{job.name} [手动]",
            max_instances=1,
            coalesce=True,
            replace_existing=False,
        )
        logger.info(f"[JobScheduler] 任务已触发立即执行: {job_id}")
        return {"status": "triggered", "job_id": job_id}

    def modify_job_cron(
        self,
        job_id: str,
        *,
        day_of_week: Optional[str] = None,
        hour: Optional[int] = None,
        minute: Optional[int] = None,
        second: Optional[int] = None,
    ) -> Dict[str, Any]:
        """修改任务的 Cron 触发器（只传要改的字段）"""
        job = self._scheduler.get_job(job_id)
        if job is None:
            raise ValueError(f"任务不存在: {job_id}")

        # 读取现有字段
        old_trigger = job.trigger
        if not isinstance(old_trigger, CronTrigger):
            raise ValueError(f"任务 {job_id} 不是 CronTrigger，无法修改 cron 字段")

        # 构建新 trigger（合并现有值）
        old_fields: Dict[str, Any] = {f.name: str(f) for f in old_trigger.fields}
        new_trigger = CronTrigger(
            day_of_week=day_of_week if day_of_week is not None else old_fields.get("day_of_week", "*"),
            hour=hour if hour is not None else old_fields.get("hour", "*"),
            minute=minute if minute is not None else old_fields.get("minute", "0"),
            second=second if second is not None else old_fields.get("second", "0"),
            timezone="Asia/Shanghai",
        )
        self._scheduler.reschedule_job(job_id, trigger=new_trigger)
        logger.info(f"[JobScheduler] 任务 cron 已修改: {job_id} → {new_trigger}")
        return _job_to_dict(self._scheduler.get_job(job_id))
