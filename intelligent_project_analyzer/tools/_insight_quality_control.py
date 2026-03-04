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


from ._enhanced_quality_control import EnhancedSearchQualityControl
from ._human_dimension_evaluator import HumanDimensionEvaluator

class InsightAwareQualityControl(EnhancedSearchQualityControl):
    """
    洞察感知质量控制器 (v7.180)

    在原有质量控制基础上，增加人性维度评估

    评分权重：
    - 原有质量分数: 85%
    - 人性维度分数: 15%

    使用示例：
        qc = InsightAwareQualityControl(
            enable_human_evaluation=True,
            user_model={"psychological": "...", "emotional": "..."}
        )
        results = qc.process_results(search_results)
    """

    def __init__(
        self,
        min_relevance: float = 0.6,
        min_content_length: int = 50,
        enable_deduplication: bool = True,
        enable_filters: bool = True,
        enable_depth_evaluation: bool = True,
        enable_human_evaluation: bool = True,
        min_depth_score: int = 20,
        user_model: Dict[str, Any] | None = None,
        human_weight: float = 0.15,
    ):
        """
        初始化洞察感知质量控制器

        Args:
            min_relevance: 最小相关性阈值
            min_content_length: 最小内容长度
            enable_deduplication: 是否启用去重
            enable_filters: 是否启用黑白名单过滤
            enable_depth_evaluation: 是否启用深度评估
            enable_human_evaluation: 是否启用人性维度评估
            min_depth_score: 最小深度分数
            user_model: 用户模型（来自L2分析）
            human_weight: 人性维度分数权重（默认15%）
        """
        super().__init__(
            min_relevance=min_relevance,
            min_content_length=min_content_length,
            enable_deduplication=enable_deduplication,
            enable_filters=enable_filters,
            enable_depth_evaluation=enable_depth_evaluation,
            min_depth_score=min_depth_score,
        )

        self.enable_human_evaluation = enable_human_evaluation
        self.user_model = user_model
        self.human_weight = human_weight
        self.human_evaluator = HumanDimensionEvaluator() if enable_human_evaluation else None

        logger.info(
            f" InsightAwareQualityControl initialized: "
            f"human_eval={enable_human_evaluation}, human_weight={human_weight}"
        )

    def process_results(
        self, results: List[Dict[str, Any]], deliverable_context: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        """
        处理搜索结果（洞察感知版管道）

        Pipeline: 父类处理 → 人性维度评估 → 综合评分 → 重新排序

        Args:
            results: 原始搜索结果列表
            deliverable_context: 交付物上下文

        Returns:
            处理后的结果列表
        """
        # 调用父类处理
        processed = super().process_results(results, deliverable_context)

        # 人性维度评估
        if self.enable_human_evaluation and self.human_evaluator:
            logger.debug(f" Evaluating human dimensions for {len(processed)} results")
            processed = self.human_evaluator.evaluate_batch(processed, self.user_model)

            # 更新综合分数（加入人性维度分数）
            base_weight = 1.0 - self.human_weight
            for result in processed:
                human_score = result.get("human_score", 0)
                original_score = result.get("quality_score", 50)
                # 加权计算
                result["quality_score"] = round(original_score * base_weight + human_score * self.human_weight, 2)
                result["human_evaluation_applied"] = True

            # 重新排序
            processed = sorted(processed, key=lambda x: x.get("quality_score", 0), reverse=True)

            logger.info(f" Human dimension evaluation completed for {len(processed)} results")

        return processed

    def set_user_model(self, user_model: Dict[str, Any]) -> None:
        """
        设置用户模型（用于动态更新）

        Args:
            user_model: 用户模型
        """
        self.user_model = user_model
        logger.debug(" User model updated for InsightAwareQualityControl")


# 便捷函数
def evaluate_human_dimensions(
    results: List[Dict[str, Any]], user_model: Dict[str, Any] | None = None
) -> List[Dict[str, Any]]:
    """
    快速评估人性维度

    Args:
        results: 搜索结果列表
        user_model: 用户模型

    Returns:
        添加了人性维度评分的结果列表
    """
    evaluator = HumanDimensionEvaluator()
    return evaluator.evaluate_batch(results, user_model)


def insight_aware_quality_control(
    results: List[Dict[str, Any]],
    min_relevance: float = 0.6,
    enable_depth: bool = True,
    enable_human: bool = True,
    user_model: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """
    洞察感知质量控制（便捷函数）

    Args:
        results: 搜索结果列表
        min_relevance: 最小相关性阈值
        enable_depth: 是否启用深度评估
        enable_human: 是否启用人性维度评估
        user_model: 用户模型

    Returns:
        处理后的结果列表
    """
    qc = InsightAwareQualityControl(
        min_relevance=min_relevance,
        enable_depth_evaluation=enable_depth,
        enable_human_evaluation=enable_human,
        user_model=user_model,
    )
    return qc.process_results(results)
