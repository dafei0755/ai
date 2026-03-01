"""
本体论智能学习模块 (Ontology Learning Module)

该模块实现本体论框架的自动学习、扩展和优化能力，将静态知识库
进化为自主学习的动态系统。

核心组件:
- DimensionExtractor: 从专家输出中提取新维度
- QualityAssessor: 评估维度质量和有效性
- RelationMiner: 挖掘维度之间的关系
- AutoExpander: 自动扩展本体论框架
- WeeklyOptimizer: 定期优化任务调度器

版本: v3.0
创建日期: 2026-02-10
"""

from .dimension_extractor import DimensionExtractor, ExtractedDimension
from .quality_assessor import QualityAssessor, QualityMetrics

__all__ = [
    "DimensionExtractor",
    "ExtractedDimension",
    "QualityAssessor",
    "QualityMetrics",
]
