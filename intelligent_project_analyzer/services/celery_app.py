# -*- coding: utf-8 -*-
"""
Celery 应用配置

用于异步任务队列，支持多用户并发分析
"""

from celery import Celery
from kombu import serialization
import json

# 注册自定义序列化器以支持中文
serialization.register(
    'utf8json',
    lambda x: json.dumps(x, ensure_ascii=False),
    lambda x: json.loads(x),
    content_type='application/json',
    content_encoding='utf-8',
)

# 创建 Celery 应用
celery_app = Celery(
    'intelligent_project_analyzer',
    broker='redis://localhost:6379/0',  # 消息队列
    backend='redis://localhost:6379/1',  # 结果存储
    include=['intelligent_project_analyzer.services.celery_tasks']  # 任务模块
)

# Celery 配置
celery_app.conf.update(
    # 序列化配置
    task_serializer='utf8json',
    accept_content=['utf8json', 'json'],
    result_serializer='utf8json',
    
    # 时区
    timezone='Asia/Shanghai',
    enable_utc=True,
    
    # 任务配置
    task_track_started=True,  # 跟踪任务开始状态
    task_time_limit=1800,     # 单个任务最长 30 分钟
    task_soft_time_limit=1500,  # 软限制 25 分钟（给清理时间）
    
    # 结果配置
    result_expires=86400,     # 结果保留 24 小时
    result_extended=True,     # 扩展结果信息
    
    # Worker 配置
    worker_prefetch_multiplier=1,  # 每次只取一个任务（长任务适用）
    worker_concurrency=4,          # 并发 Worker 数
    
    # 任务路由（可选：不同任务用不同队列）
    task_routes={
        'intelligent_project_analyzer.services.celery_tasks.analyze_project': {
            'queue': 'analysis'
        },
        'intelligent_project_analyzer.services.celery_tasks.generate_report': {
            'queue': 'report'
        }
    },
    
    # 任务默认配置
    task_default_queue='default',
    task_default_exchange='default',
    task_default_routing_key='default',
    
    # 重试配置
    task_acks_late=True,           # 任务完成后才确认
    task_reject_on_worker_lost=True,  # Worker 丢失时重新排队
    
    # 心跳检测
    broker_heartbeat=10,
    broker_connection_timeout=30,
)


# 定期任务（可选）
celery_app.conf.beat_schedule = {
    # 示例：每小时清理过期会话
    # 'cleanup-expired-sessions': {
    #     'task': 'intelligent_project_analyzer.services.celery_tasks.cleanup_expired_sessions',
    #     'schedule': 3600.0,  # 每小时
    # },
}


if __name__ == '__main__':
    celery_app.start()
