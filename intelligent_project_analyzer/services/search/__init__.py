# -*- coding: utf-8 -*-
"""
services/search — 搜索与检索子包

收录搜索编排、缓存、策略、过滤、方向生成等组件。

快捷导入示例：
    from intelligent_project_analyzer.services.search import (
        SearchOrchestrator, get_search_orchestrator
    )
"""

# ── 搜索编排（核心入口）────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.search_orchestrator import (
        SearchOrchestrator,
        get_search_orchestrator,
        orchestrated_search,
    )
except Exception:  # pragma: no cover
    SearchOrchestrator = None  # type: ignore[assignment,misc]
    get_search_orchestrator = None  # type: ignore[assignment]
    orchestrated_search = None  # type: ignore[assignment]

# ── 搜索缓存 ──────────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.search_cache import SearchCache
except Exception:  # pragma: no cover
    SearchCache = None  # type: ignore[assignment,misc]

# ── 搜索方向生成 ─────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.search_direction_generator import (
        SearchDirectionGenerator,
    )
except Exception:  # pragma: no cover
    SearchDirectionGenerator = None  # type: ignore[assignment,misc]

# ── 搜索过滤 ──────────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.search_filter_manager import (
        SearchFilterManager,
    )
except Exception:  # pragma: no cover
    SearchFilterManager = None  # type: ignore[assignment,misc]

# ── 搜索模式配置 ─────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.search_mode_config_manager import (
        SearchModeConfigManager,
    )
except Exception:  # pragma: no cover
    SearchModeConfigManager = None  # type: ignore[assignment,misc]

# ── 智能搜索策略 ─────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.intelligent_search_strategy import (
        IntelligentSearchStrategy,
    )
except Exception:  # pragma: no cover
    IntelligentSearchStrategy = None  # type: ignore[assignment,misc]

# ── Bocha AI 搜索（外部服务）────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.bocha_ai_search import BochaAISearch
except Exception:  # pragma: no cover
    BochaAISearch = None  # type: ignore[assignment,misc]

# ── UCPPT 搜索引擎 ────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.ucppt_search_engine import (
        UcpptSearchEngine,
    )
except Exception:  # pragma: no cover
    UcpptSearchEngine = None  # type: ignore[assignment,misc]

# ── 上下文检索 ────────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.context_retriever import (
        ContextRetriever,
    )
except Exception:  # pragma: no cover
    ContextRetriever = None  # type: ignore[assignment,misc]

# ── Web 内容提取 ──────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.web_content_extractor import (
        WebContentExtractor,
    )
except Exception:  # pragma: no cover
    WebContentExtractor = None  # type: ignore[assignment,misc]

__all__ = [
    "SearchOrchestrator",
    "get_search_orchestrator",
    "orchestrated_search",
    "SearchCache",
    "SearchDirectionGenerator",
    "SearchFilterManager",
    "SearchModeConfigManager",
    "IntelligentSearchStrategy",
    "BochaAISearch",
    "UcpptSearchEngine",
    "ContextRetriever",
    "WebContentExtractor",
]
