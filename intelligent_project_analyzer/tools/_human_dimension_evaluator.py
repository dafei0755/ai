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


class HumanDimensionEvaluator:
    """
    人性维度评估器 (v7.180)

    评估搜索结果是否触及用户的人性维度需求：
    - 情感共鸣度 (emotional)
    - 精神追求 (spiritual)
    - 心理安全 (safety)
    - 仪式感支持 (ritual)
    - 记忆锚点关联 (memory)

    使用示例：
        evaluator = HumanDimensionEvaluator()
        result = evaluator.evaluate(search_result, user_model)
        # result = {"human_score": 60, "matched_dimensions": ["emotional", "ritual"], ...}
    """

    def __init__(self):
        """初始化人性维度评估器"""
        # 延迟导入以避免循环依赖
        try:
            from ..utils.insight_methodology import InsightMethodology

            self.methodology = InsightMethodology
        except ImportError:
            logger.warning("️ InsightMethodology not available, using fallback")
            self.methodology = None

        # 备用关键词（如果方法论模块不可用）
        self.FALLBACK_DIMENSIONS = {
            "emotional": ["情感", "感受", "体验", "氛围", "温度", "情绪", "温馨", "舒适"],
            "spiritual": ["精神", "追求", "价值", "意义", "信仰", "理想", "自我", "成长"],
            "safety": ["安全", "庇护", "私密", "边界", "保护", "归属", "依恋", "稳定"],
            "ritual": ["仪式", "习惯", "日常", "节奏", "规律", "传统", "晨间", "睡前"],
            "memory": ["记忆", "回忆", "故事", "传承", "历史", "纪念", "怀旧", "童年"],
        }

        logger.info(" HumanDimensionEvaluator initialized")

    def evaluate(self, result: Dict[str, Any], user_model: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """
        评估单个搜索结果的人性维度相关性

        Args:
            result: 搜索结果
            user_model: 用户模型（来自L2分析）

        Returns:
            {
                "human_score": 0-100,
                "matched_dimensions": ["emotional", "ritual", ...],
                "relevance_details": {...},
                "dimension_scores": {...}
            }
        """
        content = result.get("content", "") or result.get("snippet", "") or ""
        title = result.get("title", "")
        text = f"{title} {content}"

        # 提取匹配的人性维度
        if self.methodology:
            matched = self.methodology.extract_human_dimensions(text)
        else:
            matched = self._extract_dimensions_fallback(text)

        # 计算各维度分数
        dimension_scores = {}
        matched_dims = []
        total_score = 0

        for dim_name, keywords in matched.items():
            if keywords:
                matched_dims.append(dim_name)
                # 每个维度基础20分，每个额外关键词+2分（最多30分/维度）
                dim_score = min(30, 20 + len(keywords) * 2)
                dimension_scores[dim_name] = dim_score
                total_score += dim_score

        # 基础分数（最多100分）
        base_score = min(100, total_score)

        # 如果有用户模型，计算与用户需求的匹配度
        user_match_bonus = 0
        if user_model and self.methodology:
            user_relevance = self.methodology.calculate_human_relevance(text, user_model)
            user_match_bonus = user_relevance * 0.2  # 用户匹配最多加20分

        final_score = min(100, base_score + user_match_bonus)

        return {
            "human_score": round(final_score, 2),
            "matched_dimensions": matched_dims,
            "relevance_details": matched,
            "dimension_scores": dimension_scores,
            "user_match_bonus": round(user_match_bonus, 2),
        }

    def _extract_dimensions_fallback(self, text: str) -> Dict[str, List[str]]:
        """
        备用维度提取方法（当方法论模块不可用时）

        Args:
            text: 输入文本

        Returns:
            维度 → 匹配关键词列表
        """
        result = {dim: [] for dim in self.FALLBACK_DIMENSIONS.keys()}

        if not text:
            return result

        text_lower = text.lower()

        for dimension, keywords in self.FALLBACK_DIMENSIONS.items():
            matched = []
            for keyword in keywords:
                if keyword in text or keyword.lower() in text_lower:
                    matched.append(keyword)
            result[dimension] = list(set(matched))

        return result

    def evaluate_batch(
        self, results: List[Dict[str, Any]], user_model: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        """
        批量评估搜索结果

        Args:
            results: 搜索结果列表
            user_model: 用户模型

        Returns:
            添加了人性维度评分的结果列表
        """
        for result in results:
            eval_result = self.evaluate(result, user_model)
            result["human_score"] = eval_result["human_score"]
            result["matched_dimensions"] = eval_result["matched_dimensions"]
            result["dimension_scores"] = eval_result.get("dimension_scores", {})

        return results

    def filter_by_human_score(
        self, results: List[Dict[str, Any]], min_score: float = 20.0, user_model: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        """
        按人性维度分数过滤结果

        Args:
            results: 搜索结果列表
            min_score: 最小人性维度分数
            user_model: 用户模型

        Returns:
            过滤后的结果列表
        """
        # 先评估
        evaluated = self.evaluate_batch(results, user_model)

        # 过滤
        filtered = [r for r in evaluated if r.get("human_score", 0) >= min_score]

        logger.debug(f" Human dimension filter: {len(results)} → {len(filtered)} results")
        return filtered

    def sort_by_human_score(
        self, results: List[Dict[str, Any]], descending: bool = True, user_model: Dict[str, Any] | None = None
    ) -> List[Dict[str, Any]]:
        """
        按人性维度分数排序

        Args:
            results: 搜索结果列表
            descending: 是否降序
            user_model: 用户模型

        Returns:
            排序后的结果列表
        """
        # 确保所有结果都有评分
        for result in results:
            if "human_score" not in result:
                eval_result = self.evaluate(result, user_model)
                result["human_score"] = eval_result["human_score"]
                result["matched_dimensions"] = eval_result["matched_dimensions"]

        return sorted(results, key=lambda x: x.get("human_score", 0), reverse=descending)


