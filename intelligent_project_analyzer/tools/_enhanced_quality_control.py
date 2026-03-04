"""
Search Quality Control (v7.197 + 语义去重 + 动态权重)

搜索结果质量控制管道：黑名单过滤 → 相关性过滤 → 语义去重 → 可信度评估 → 白名单提升 → 排序 → 域名统计

v7.197 新增：
- 语义去重：使用 Embedding 相似度替代前100字符对比
- 动态权重：根据查询类型动态调整时效性/可信度权重
- 查询分类器集成：自动识别 news/academic/case/concept 等类型
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Set
from urllib.parse import urlparse

from loguru import logger

# v7.197: 导入语义去重和查询分类器
_semantic_dedup_module = None
_query_classifier_module = None


def _get_semantic_dedup():
    """延迟加载语义去重模块"""
    global _semantic_dedup_module
    if _semantic_dedup_module is None:
        try:
            from . import semantic_dedup

            _semantic_dedup_module = semantic_dedup
        except Exception as e:
            logger.warning(f"️ 语义去重模块加载失败，使用前缀去重: {e}")
            _semantic_dedup_module = False
    return _semantic_dedup_module if _semantic_dedup_module else None


def _get_query_classifier():
    """延迟加载查询分类器模块"""
    global _query_classifier_module
    if _query_classifier_module is None:
        try:
            from . import query_classifier

            _query_classifier_module = query_classifier
        except Exception as e:
            logger.warning(f"️ 查询分类器模块加载失败，使用默认权重: {e}")
            _query_classifier_module = False
    return _query_classifier_module if _query_classifier_module else None


# 域名质量统计服务（延迟导入以避免循环依赖）
_domain_stats_service = None


def _get_domain_stats_service():
    """获取域名统计服务（延迟加载）"""
    global _domain_stats_service
    if _domain_stats_service is None:
        try:
            from ..services.domain_quality_stats import get_domain_stats_service

            _domain_stats_service = get_domain_stats_service()
        except Exception as e:
            logger.warning(f"️ 域名质量统计服务加载失败: {e}")
            _domain_stats_service = False  # 标记为加载失败，避免重复尝试
    return _domain_stats_service if _domain_stats_service else None


from ._search_quality_control import SearchQualityControl
from ._content_depth_evaluator import ContentDepthEvaluator

class EnhancedSearchQualityControl(SearchQualityControl):
    """
    增强版搜索质量控制器 (v7.170)

    在原有质量控制基础上，增加内容深度评估
    """

    def __init__(
        self,
        min_relevance: float = 0.6,
        min_content_length: int = 50,
        enable_deduplication: bool = True,
        enable_filters: bool = True,
        enable_depth_evaluation: bool = True,
        min_depth_score: int = 20,
    ):
        """
        初始化增强版质量控制器

        Args:
            min_relevance: 最小相关性阈值
            min_content_length: 最小内容长度
            enable_deduplication: 是否启用去重
            enable_filters: 是否启用黑白名单过滤
            enable_depth_evaluation: 是否启用深度评估
            min_depth_score: 最小深度分数
        """
        super().__init__(
            min_relevance=min_relevance,
            min_content_length=min_content_length,
            enable_deduplication=enable_deduplication,
            enable_filters=enable_filters,
        )

        self.enable_depth_evaluation = enable_depth_evaluation
        self.min_depth_score = min_depth_score
        self.depth_evaluator = ContentDepthEvaluator() if enable_depth_evaluation else None

        logger.info(f" EnhancedSearchQualityControl initialized: depth_eval={enable_depth_evaluation}")

    def process_results(
        self, results: List[Dict[str, Any]], deliverable_context: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        """
        处理搜索结果（增强版管道）

        Pipeline: Filter → Deduplicate → Assess → Depth Evaluate → Score → Sort

        Args:
            results: 原始搜索结果列表
            deliverable_context: 交付物上下文

        Returns:
            处理后的结果列表
        """
        # 调用父类的处理方法
        processed = super().process_results(results, deliverable_context)

        # 添加深度评估
        if self.enable_depth_evaluation and self.depth_evaluator:
            logger.debug(f" Evaluating content depth for {len(processed)} results")
            processed = self.depth_evaluator.evaluate_batch(processed)

            # 更新综合分数（加入深度分数）
            for result in processed:
                depth_score = result.get("depth_score", 0)
                original_score = result.get("quality_score", 50)
                # 深度分数占20%权重
                result["quality_score"] = round(original_score * 0.8 + depth_score * 0.2, 2)

            # 重新排序
            processed = sorted(processed, key=lambda x: x.get("quality_score", 0), reverse=True)

            logger.info(f" Depth evaluation completed for {len(processed)} results")

        return processed


# 便捷函数
def evaluate_content_depth(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    快速评估内容深度

    Args:
        results: 搜索结果列表

    Returns:
        添加了深度评分的结果列表
    """
    evaluator = ContentDepthEvaluator()
    return evaluator.evaluate_batch(results)


def enhanced_quality_control(
    results: List[Dict[str, Any]], min_relevance: float = 0.6, enable_depth: bool = True
) -> List[Dict[str, Any]]:
    """
    增强版质量控制

    Args:
        results: 搜索结果列表
        min_relevance: 最小相关性阈值
        enable_depth: 是否启用深度评估

    Returns:
        处理后的结果列表
    """
    qc = EnhancedSearchQualityControl(min_relevance=min_relevance, enable_depth_evaluation=enable_depth)
    return qc.process_results(results)


# ============================================================================
# v7.180 新增：人性维度评估器
# ============================================================================


