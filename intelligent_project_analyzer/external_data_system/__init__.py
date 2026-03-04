"""
外部建筑数据采集系统 (External Architecture Data System)

这是一个独立的爬虫子系统，负责从多个建筑网站采集项目数据。

核心组件：
- spiders: 爬虫实现（Archdaily, Gooood, Dezeen等）
- models: 数据模型（PostgreSQL + pgvector）
- tasks: 异步任务（Celery）
- api: RESTful接口
- utils: 工具函数（限流、代理、重试等）

设计原则：
1. 高内聚：所有爬虫相关代码集中管理
2. 低耦合：通过明确接口与主项目交互
3. 易扩展：新增数据源只需实现 BaseSpider
4. 易测试：可独立运行测试套件

Author: AI Architecture Team
Version: v1.0.0
Date: 2026-02-17
"""

# 导出核心接口
from .spiders import get_spider_manager

from .models import (
    ExternalProject,
    ExternalProjectImage,
    SyncHistory,
    QualityIssue,
    ProjectDiscovery,
    get_external_db,
)

from .api import router as external_data_router

from intelligent_project_analyzer.versioning import PRODUCT_VERSION as __version__

__all__ = [
    # Spider接口
    "get_spider_manager",
    # 数据模型
    "ExternalProject",
    "ExternalProjectImage",
    "SyncHistory",
    "QualityIssue",
    "ProjectDiscovery",
    "get_external_db",
    # API路由
    "external_data_router",
]
