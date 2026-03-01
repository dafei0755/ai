"""
Celery 应用配置

用于定时任务和异步任务调度
"""

import os
from celery import Celery
from celery.schedules import crontab

# 从环境变量读取配置
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# 创建 Celery 应用
app = Celery(
    "external_data_system",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "intelligent_project_analyzer.external_data_system.tasks.sync_tasks",
        "intelligent_project_analyzer.external_data_system.tasks.processing_tasks",
    ],
)

# Celery 配置
app.conf.update(
    # 时区
    timezone="Asia/Shanghai",
    enable_utc=True,
    # 任务结果
    result_expires=3600,  # 结果保留1小时
    # 任务序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # 任务路由
    task_routes={
        "external_data_system.tasks.sync_*": {"queue": "sync"},
        "external_data_system.tasks.process_*": {"queue": "process"},
    },
    # 任务限流
    task_annotations={
        "external_data_system.tasks.sync_*": {"rate_limit": "10/m"},  # 每分钟10个
    },
    # Worker 配置
    worker_prefetch_multiplier=1,  # 每次只取一个任务
    worker_max_tasks_per_child=50,  # 处理50个任务后重启worker
    # Windows 下 Celery prefork 不支持，必须使用 solo 模式
    worker_pool="solo",
)

# Celery Beat 定时任务配置
app.conf.beat_schedule = {
    # ========== 第一轮完整爬取（手动触发，注释掉） ==========
    # 'full-crawl-archdaily': {
    #     'task': 'external_data_system.tasks.full_crawl_archdaily',
    #     'schedule': crontab(hour=2, minute=0),  # 每天凌晨2点
    #     'options': {'queue': 'sync'},
    # },
    # ========== 每周增量更新（生产环境） ==========
    "weekly-sync-archdaily": {
        "task": "external_data_system.tasks.sync_archdaily_incremental",
        "schedule": crontab(hour=2, minute=0, day_of_week=1),  # 每周一凌晨2点
        "options": {"queue": "sync"},
    },
    "weekly-sync-gooood": {
        "task": "external_data_system.tasks.sync_gooood_incremental",
        "schedule": crontab(hour=2, minute=0, day_of_week=2),  # 每周二凌晨2点
        "options": {"queue": "sync"},
    },
    # ========== 数据处理任务 ==========
    "daily-batch-embeddings": {
        "task": "external_data_system.tasks.batch_generate_embeddings_task",
        "schedule": crontab(hour=3, minute=0),  # 每天凌晨3点
        "kwargs": {"batch_size": 100, "only_missing": True},
        "options": {"queue": "process"},
    },
    "daily-quality-check": {
        "task": "external_data_system.tasks.batch_quality_check_task",
        "schedule": crontab(hour=4, minute=0),  # 每天凌晨4点
        "kwargs": {"batch_size": 200},
        "options": {"queue": "process"},
    },
    # ========== 数据库维护 ==========
    "weekly-database-cleanup": {
        "task": "external_data_system.tasks.cleanup_old_sync_history",
        "schedule": crontab(hour=5, minute=0, day_of_week=0),  # 每周日凌晨5点
        "kwargs": {"days": 90},  # 清理90天前的记录
        "options": {"queue": "process"},
    },
    # ========== 监控报告 ==========
    "daily-quality-report": {
        "task": "external_data_system.tasks.generate_quality_report",
        "schedule": crontab(hour=23, minute=0),  # 每晚23点生成日报
        "options": {"queue": "process"},
    },
}


@app.task
def test_task():
    """测试任务"""
    from loguru import logger

    logger.info("✅ Celery测试任务执行成功！")
    return "success"


if __name__ == "__main__":
    app.start()
