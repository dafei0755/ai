"""
数据模型模块

包含PostgreSQL数据库模型定义。
"""

from .external_projects import (
    ExternalProject,
    ExternalProjectDatabase,
    ExternalProjectImage,
    ProjectDiscovery,
    QualityIssue,
    SyncHistory,
    get_external_db,
)

__all__ = [
    "ExternalProject",
    "ExternalProjectImage",
    "SyncHistory",
    "QualityIssue",
    "ProjectDiscovery",
    "ExternalProjectDatabase",
    "get_external_db",
]
