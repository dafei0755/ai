"""
外部项目数据库模型 (已废弃 - 向后兼容重定向)

⚠️ 此文件已废弃。请使用:
   from intelligent_project_analyzer.external_data_system.models.external_projects import ...

此文件保留仅用于向后兼容，所有导入会自动重定向到新路径并发出警告。
"""

import warnings

warnings.warn(
    "intelligent_project_analyzer.models.external_projects 已废弃（旧模型缺少双语字段、content_hash 等 10+ 列）。"
    "请改用: from intelligent_project_analyzer.external_data_system.models.external_projects import ...",
    DeprecationWarning,
    stacklevel=2,
)

# 从新路径重导出所有公开接口，确保旧代码不中断
from intelligent_project_analyzer.external_data_system.models.external_projects import (  # noqa: F401, E402
    PGVECTOR_AVAILABLE,
    Base,
    ExternalProject,
    ExternalProjectDatabase,
    ExternalProjectImage,
    ProjectDiscovery,
    QualityIssue,
    SyncHistory,
    get_external_db,
)

__all__ = [
    "Base",
    "ExternalProject",
    "ExternalProjectImage",
    "SyncHistory",
    "QualityIssue",
    "ProjectDiscovery",
    "ExternalProjectDatabase",
    "get_external_db",
    "PGVECTOR_AVAILABLE",
]
