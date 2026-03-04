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

class ContentDepthEvaluator:
    """
    内容深度评估器 (v7.170)

    评估搜索结果的内容深度，区分"有分析框架的深度内容"和"简单罗列的浅层内容"

    评估维度：
    1. 是否有分析框架 (20分)
    2. 是否有对比分析 (15分)
    3. 是否有数据支撑 (15分)
    4. 是否有案例研究 (15分)
    5. 是否有方法论 (15分)
    6. 是否有结论/建议 (10分)
    7. 内容长度 (10分)
    """

    # 深度评估权重
    DEPTH_WEIGHTS = {
        "has_framework": 20,  # 是否有分析框架
        "has_comparison": 15,  # 是否有对比分析
        "has_data": 15,  # 是否有数据支撑
        "has_case_study": 15,  # 是否有案例研究
        "has_methodology": 15,  # 是否有方法论
        "has_conclusion": 10,  # 是否有结论/建议
        "content_length": 10,  # 内容长度
    }

    # 框架关键词
    FRAMEWORK_KEYWORDS = [
        "框架",
        "模型",
        "体系",
        "结构",
        "维度",
        "层面",
        "系统",
        "framework",
        "model",
        "structure",
        "dimension",
        "system",
    ]

    # 对比关键词
    COMPARISON_KEYWORDS = [
        "对比",
        "比较",
        "区别",
        "差异",
        "vs",
        "相比",
        "不同",
        "compare",
        "comparison",
        "difference",
        "versus",
        "contrast",
    ]

    # 数据关键词
    DATA_KEYWORDS = [
        "%",
        "数据",
        "统计",
        "调查",
        "报告",
        "增长",
        "下降",
        "比例",
        "data",
        "statistics",
        "survey",
        "report",
        "growth",
        "percentage",
    ]

    # 案例关键词
    CASE_KEYWORDS = ["案例", "项目", "实例", "实践", "作品", "设计案例", "case", "project", "example", "practice", "case study"]

    # 方法论关键词
    METHODOLOGY_KEYWORDS = [
        "方法",
        "步骤",
        "流程",
        "策略",
        "原则",
        "指南",
        "方法论",
        "method",
        "step",
        "process",
        "strategy",
        "principle",
        "guideline",
        "methodology",
    ]

    # 结论关键词
    CONCLUSION_KEYWORDS = [
        "结论",
        "建议",
        "总结",
        "启示",
        "展望",
        "未来",
        "conclusion",
        "recommendation",
        "summary",
        "insight",
        "future",
    ]

    def __init__(self, min_content_length: int = 500):
        """
        初始化内容深度评估器

        Args:
            min_content_length: 被认为是"长内容"的最小字符数
        """
        self.min_content_length = min_content_length

    def evaluate_depth(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估单个搜索结果的内容深度

        Args:
            result: 搜索结果字典

        Returns:
            包含深度评分和各维度得分的字典
        """
        content = result.get("content", "") or result.get("snippet", "") or result.get("summary", "")
        title = result.get("title", "")
        text = f"{title} {content}".lower()

        # 评估各维度
        scores = {
            "has_framework": self._check_keywords(text, self.FRAMEWORK_KEYWORDS),
            "has_comparison": self._check_keywords(text, self.COMPARISON_KEYWORDS),
            "has_data": self._check_keywords(text, self.DATA_KEYWORDS),
            "has_case_study": self._check_keywords(text, self.CASE_KEYWORDS),
            "has_methodology": self._check_keywords(text, self.METHODOLOGY_KEYWORDS),
            "has_conclusion": self._check_keywords(text, self.CONCLUSION_KEYWORDS),
            "content_length": len(content) >= self.min_content_length,
        }

        # 计算总分
        total_score = sum(self.DEPTH_WEIGHTS[key] if value else 0 for key, value in scores.items())

        return {
            "depth_score": total_score,
            "depth_indicators": scores,
            "depth_level": self._get_depth_level(total_score),
        }

    def _check_keywords(self, text: str, keywords: List[str]) -> bool:
        """检查文本是否包含关键词"""
        return any(keyword.lower() in text for keyword in keywords)

    def _get_depth_level(self, score: int) -> str:
        """
        根据分数获取深度等级

        Args:
            score: 深度分数 (0-100)

        Returns:
            深度等级: "deep", "medium", "shallow"
        """
        if score >= 60:
            return "deep"
        elif score >= 30:
            return "medium"
        else:
            return "shallow"

    def evaluate_batch(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量评估搜索结果的内容深度

        Args:
            results: 搜索结果列表

        Returns:
            添加了深度评分的结果列表
        """
        for result in results:
            depth_info = self.evaluate_depth(result)
            result["depth_score"] = depth_info["depth_score"]
            result["depth_indicators"] = depth_info["depth_indicators"]
            result["depth_level"] = depth_info["depth_level"]

        return results

    def filter_by_depth(
        self, results: List[Dict[str, Any]], min_depth_score: int = 30, min_depth_level: str = "medium"
    ) -> List[Dict[str, Any]]:
        """
        按深度过滤搜索结果

        Args:
            results: 搜索结果列表
            min_depth_score: 最小深度分数
            min_depth_level: 最小深度等级

        Returns:
            过滤后的结果列表
        """
        depth_levels = {"shallow": 0, "medium": 1, "deep": 2}
        min_level_value = depth_levels.get(min_depth_level, 1)

        filtered = []
        for result in results:
            # 如果还没有评估深度，先评估
            if "depth_score" not in result:
                depth_info = self.evaluate_depth(result)
                result.update(depth_info)

            # 检查是否满足条件
            result_level_value = depth_levels.get(result.get("depth_level", "shallow"), 0)
            if result.get("depth_score", 0) >= min_depth_score or result_level_value >= min_level_value:
                filtered.append(result)

        return filtered

    def sort_by_depth(self, results: List[Dict[str, Any]], descending: bool = True) -> List[Dict[str, Any]]:
        """
        按深度分数排序

        Args:
            results: 搜索结果列表
            descending: 是否降序

        Returns:
            排序后的结果列表
        """
        # 确保所有结果都有深度评分
        for result in results:
            if "depth_score" not in result:
                depth_info = self.evaluate_depth(result)
                result.update(depth_info)

        return sorted(results, key=lambda x: x.get("depth_score", 0), reverse=descending)


