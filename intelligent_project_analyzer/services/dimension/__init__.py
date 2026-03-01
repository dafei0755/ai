# -*- coding: utf-8 -*-
"""
services/dimension — 维度分析子包

收录维度生成、评估、选择、雷达图编排等组件。

快捷导入示例：
    from intelligent_project_analyzer.services.dimension import (
        RadarDimensionOrchestrator,
        ProjectSpecificDimensionGenerator,
        get_dimensions_config,
    )
"""

# ── 维度配置加载（核心 YAML 配置）────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.analysis_dimensions_loader import (
        AnalysisDimensionsConfig,
        DimensionValidation,
        get_dimensions_config,
        reload_dimensions_config,
    )
except Exception:  # pragma: no cover
    AnalysisDimensionsConfig = None  # type: ignore[assignment,misc]
    DimensionValidation = None  # type: ignore[assignment,misc]
    get_dimensions_config = None  # type: ignore[assignment]
    reload_dimensions_config = None  # type: ignore[assignment]

# ── 雷达图维度编排 (核心入口) ─────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.radar_dimension_orchestrator import (
        RadarDimensionOrchestrator,
    )
except Exception:  # pragma: no cover
    RadarDimensionOrchestrator = None  # type: ignore[assignment,misc]

# ── 项目特定维度生成器 ────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.project_specific_dimension_generator import (
        ProjectSpecificDimensionGenerator,
    )
except Exception:  # pragma: no cover
    ProjectSpecificDimensionGenerator = None  # type: ignore[assignment,misc]

# ── 自适应维度生成 ────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.adaptive_dimension_generator import (
        AdaptiveDimensionGenerator,
    )
except Exception:  # pragma: no cover
    AdaptiveDimensionGenerator = None  # type: ignore[assignment,misc]

# ── 动态维度生成 ──────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.dynamic_dimension_generator import (
        DynamicDimensionGenerator,
    )
except Exception:  # pragma: no cover
    DynamicDimensionGenerator = None  # type: ignore[assignment,misc]

# ── 维度评估 ──────────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.dimension_evaluator import (
        DimensionEvaluator,
    )
except Exception:  # pragma: no cover
    DimensionEvaluator = None  # type: ignore[assignment,misc]

# ── 维度选择 ──────────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.dimension_selector import (
        DimensionSelector,
    )
except Exception:  # pragma: no cover
    DimensionSelector = None  # type: ignore[assignment,misc]

# ── 维度使用追踪 ─────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.dimension_usage_tracker import (
        DimensionUsageTracker,
    )
except Exception:  # pragma: no cover
    DimensionUsageTracker = None  # type: ignore[assignment,misc]

# ── 维度相关性检测 ────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.dimension_correlation_detector import (
        DimensionCorrelationDetector,
    )
except Exception:  # pragma: no cover
    DimensionCorrelationDetector = None  # type: ignore[assignment,misc]

# ── LLM 维度推荐 ──────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.llm_dimension_recommender import (
        LLMDimensionRecommender,
    )
except Exception:  # pragma: no cover
    LLMDimensionRecommender = None  # type: ignore[assignment,misc]

# ── 人工维度指导 ──────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.human_dimension_guide import (
        HumanDimensionGuide,
    )
except Exception:  # pragma: no cover
    HumanDimensionGuide = None  # type: ignore[assignment,misc]

# ── 类型别名标准化 ────────────────────────────────────────────────────────────
try:
    from intelligent_project_analyzer.services.type_alias_normalizer import (
        TypeAliasNormalizer,
    )
except Exception:  # pragma: no cover
    TypeAliasNormalizer = None  # type: ignore[assignment,misc]

__all__ = [
    # 配置
    "AnalysisDimensionsConfig",
    "DimensionValidation",
    "get_dimensions_config",
    "reload_dimensions_config",
    # 核心编排
    "RadarDimensionOrchestrator",
    "ProjectSpecificDimensionGenerator",
    # 生成器
    "AdaptiveDimensionGenerator",
    "DynamicDimensionGenerator",
    # 评估 & 选择
    "DimensionEvaluator",
    "DimensionSelector",
    # 追踪 & 相关性
    "DimensionUsageTracker",
    "DimensionCorrelationDetector",
    # LLM 推荐
    "LLMDimensionRecommender",
    # 辅助
    "HumanDimensionGuide",
    "TypeAliasNormalizer",
]
