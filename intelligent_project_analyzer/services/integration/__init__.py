# -*- coding: utf-8 -*-
"""
services/integration — 外部集成与核心业务子包

收录本体、图像生成、身份认证、爬虫工具、项目类型检测、意图分析等组件。

快捷导入示例：
    from intelligent_project_analyzer.services.integration import (
        OntologyService, get_ontology_service, ToolFactory
    )
"""

# ── 工具工厂 ──────────────────────────────────────────────────────────────────
from intelligent_project_analyzer.services.tool_factory import ToolFactory

# ── 本体服务 ──────────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.ontology_service import (
        OntologyService,
        get_ontology_service,
    )
except Exception:  # pragma: no cover
    OntologyService = None  # type: ignore[assignment,misc]
    get_ontology_service = None  # type: ignore[assignment]

# ── 本体编辑器 ────────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.ontology_editor import OntologyEditor
except Exception:  # pragma: no cover
    OntologyEditor = None  # type: ignore[assignment,misc]

# ── 图像生成 ──────────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.image_generator import ImageGenerator
except Exception:  # pragma: no cover
    ImageGenerator = None  # type: ignore[assignment,misc]

try:
    from intelligent_project_analyzer.services.image_storage_manager import (
        ImageStorageManager,
    )
except Exception:  # pragma: no cover
    ImageStorageManager = None  # type: ignore[assignment,misc]

try:
    from intelligent_project_analyzer.services.inpainting_service import (
        InpaintingService,
    )
except Exception:  # pragma: no cover
    InpaintingService = None  # type: ignore[assignment,misc]

# ── 项目类型检测 ─────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.project_type_detector import (
        ProjectTypeDetector,
    )
except Exception:  # pragma: no cover
    ProjectTypeDetector = None  # type: ignore[assignment,misc]

# ── 意图分类 ──────────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.intent_classifier import (
        IntentClassifier,
    )
except Exception:  # pragma: no cover
    IntentClassifier = None  # type: ignore[assignment,misc]

try:
    from intelligent_project_analyzer.services.change_intent_detector import (
        ChangeIntentDetector,
    )
except Exception:  # pragma: no cover
    ChangeIntentDetector = None  # type: ignore[assignment,misc]

# ── 地理位置服务 ─────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.geoip_service import GeoIPService
except Exception:  # pragma: no cover
    GeoIPService = None  # type: ignore[assignment,misc]

# ── WordPress / 外部 CMS ─────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.wordpress_jwt_service import (
        WordPressJWTService,
    )
except Exception:  # pragma: no cover
    WordPressJWTService = None  # type: ignore[assignment,misc]

# ── SF 知识库加载 ─────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.sf_knowledge_loader import (
        SFKnowledgeLoader,
    )
except Exception:  # pragma: no cover
    SFKnowledgeLoader = None  # type: ignore[assignment,misc]

# ── 文件处理 ──────────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.file_processor import FileProcessor
except Exception:  # pragma: no cover
    FileProcessor = None  # type: ignore[assignment,misc]

__all__ = [
    # 核心工厂
    "ToolFactory",
    # 本体
    "OntologyService",
    "get_ontology_service",
    "OntologyEditor",
    # 图像
    "ImageGenerator",
    "ImageStorageManager",
    "InpaintingService",
    # 项目类型 & 意图
    "ProjectTypeDetector",
    "IntentClassifier",
    "ChangeIntentDetector",
    # 外部服务
    "GeoIPService",
    "WordPressJWTService",
    "SFKnowledgeLoader",
    # 工具
    "FileProcessor",
]
