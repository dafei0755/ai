"""
搜索结果分发器 - 智能分发搜索结果给相关交付物
实现搜索完成后的实时结果分发和跨专家共享机制
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from .search_coordinator import SearchResult
from .search_task_planner import DeliverableSearchBinding, SearchType

logger = logging.getLogger(__name__)


@dataclass
class DistributedResult:
    """分发结果包装"""

    original_result: SearchResult
    target_deliverable_ids: List[str]
    relevance_scores: Dict[str, float]  # deliverable_id -> relevance_score
    distribution_metadata: Dict[str, Any] = field(default_factory=dict)
    distributed_at: datetime = field(default_factory=datetime.now)


@dataclass
class DistributionReport:
    """分发报告"""

    total_results: int
    distributed_results: int
    shared_results: int
    deliverable_coverage: Dict[str, int]  # deliverable_id -> result_count
    distribution_quality: float
    execution_time: float
    created_at: datetime = field(default_factory=datetime.now)


class SearchResultDistributor:
    """搜索结果分发器 - 智能分发和共享搜索结果"""

    def __init__(self):
        self.result_cache = {}  # 结果缓存
        self.deliverable_profiles = {}  # 交付物特征档案
        self.distribution_history = []  # 分发历史

        # 相似度配置
        self.relevance_threshold = 0.6  # 相关性阈值
        self.sharing_threshold = 0.7  # 共享质量阈值

        # 分发权重配置
        self.distribution_weights = {
            "keyword_similarity": 0.4,  # 关键词相似度
            "type_compatibility": 0.3,  # 类型兼容性
            "quality_score": 0.2,  # 质量分数
            "deliverable_priority": 0.1,  # 交付物优先级
        }

    def distribute_search_results(
        self,
        search_results: List[SearchResult],
        deliverable_bindings: List[DeliverableSearchBinding],
        session_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[DistributedResult]]:
        """
        智能分发搜索结果给相关交付物

        Args:
            search_results: 搜索结果列表
            deliverable_bindings: 交付物绑定信息
            session_context: 会话上下文

        Returns:
            按交付物ID分组的分发结果
        """
        logger.info(f"📤 [SearchResultDistributor] 开始分发{len(search_results)}个搜索结果")

        start_time = time.time()

        # Step 1: 构建交付物特征档案
        self._build_deliverable_profiles(deliverable_bindings)

        # Step 2: 计算结果相关性
        relevance_matrix = self._calculate_relevance_matrix(search_results, deliverable_bindings)

        # Step 3: 执行智能分发
        distributed_results = self._execute_distribution(search_results, relevance_matrix)

        # Step 4: 识别共享结果
        shared_results = self._identify_shared_results(distributed_results)

        # Step 5: 优化分发策略
        optimized_distribution = self._optimize_distribution(distributed_results, shared_results)

        execution_time = time.time() - start_time

        # 记录分发统计
        self._record_distribution_statistics(optimized_distribution, shared_results, execution_time)

        logger.info(f"✅ [SearchResultDistributor] 结果分发完成，耗时{execution_time:.2f}秒")

        return optimized_distribution

    def _build_deliverable_profiles(self, deliverable_bindings: List[DeliverableSearchBinding]):
        """构建交付物特征档案"""
        logger.debug("📋 [SearchResultDistributor] 构建交付物特征档案")

        for binding in deliverable_bindings:
            profile = {
                "deliverable_id": binding.deliverable_id,
                "name": binding.deliverable_name,
                "type": binding.deliverable_type,
                "keywords": self._extract_deliverable_keywords(binding),
                "search_types": [st.value for st in binding.required_search_types],
                "complexity": binding.search_complexity,
                "priority": self._calculate_deliverable_priority(binding),
                "compatibility_matrix": self._build_compatibility_matrix(binding),
            }

            self.deliverable_profiles[binding.deliverable_id] = profile

        logger.debug(f"📊 [SearchResultDistributor] 构建了{len(self.deliverable_profiles)}个交付物档案")

    def _calculate_relevance_matrix(
        self, search_results: List[SearchResult], deliverable_bindings: List[DeliverableSearchBinding]
    ) -> Dict[str, Dict[str, float]]:
        """计算搜索结果与交付物的相关性矩阵"""
        logger.debug("🧮 [SearchResultDistributor] 计算相关性矩阵")

        relevance_matrix = {}

        for result in search_results:
            result_id = f"{result.task_id}_{result.search_type.value}"
            relevance_matrix[result_id] = {}

            for binding in deliverable_bindings:
                relevance_score = self._calculate_result_relevance(result, binding)
                relevance_matrix[result_id][binding.deliverable_id] = relevance_score

        return relevance_matrix

    def _calculate_result_relevance(self, result: SearchResult, binding: DeliverableSearchBinding) -> float:
        """计算单个搜索结果与交付物的相关性分数"""

        # 1. 关键词相似度
        keyword_similarity = self._calculate_keyword_similarity(result, binding)

        # 2. 类型兼容性
        type_compatibility = self._calculate_type_compatibility(result, binding)

        # 3. 质量分数权重
        quality_weight = min(result.quality_score / 100.0, 1.0)

        # 4. 交付物优先级权重
        deliverable_priority = self.deliverable_profiles[binding.deliverable_id]["priority"]
        priority_weight = deliverable_priority / 5.0  # 归一化到0-1

        # 加权计算相关性
        relevance_score = (
            keyword_similarity * self.distribution_weights["keyword_similarity"]
            + type_compatibility * self.distribution_weights["type_compatibility"]
            + quality_weight * self.distribution_weights["quality_score"]
            + priority_weight * self.distribution_weights["deliverable_priority"]
        )

        return min(relevance_score, 1.0)

    def _calculate_keyword_similarity(self, result: SearchResult, binding: DeliverableSearchBinding) -> float:
        """计算关键词相似度"""
        # 提取搜索结果关键词
        result_keywords = set()

        # 从查询中提取
        if result.query:
            result_keywords.update(result.query.lower().split())

        # 从搜索结果中提取
        for search_item in result.results:
            title = search_item.get("title", "")
            snippet = search_item.get("snippet", "")
            result_keywords.update(title.lower().split())
            result_keywords.update(snippet.lower().split()[:10])  # 限制snippet词数

        # 获取交付物关键词
        deliverable_keywords = set(self.deliverable_profiles[binding.deliverable_id]["keywords"])

        if not result_keywords or not deliverable_keywords:
            return 0.0

        # 计算Jaccard相似度
        intersection = result_keywords.intersection(deliverable_keywords)
        union = result_keywords.union(deliverable_keywords)

        return len(intersection) / len(union) if union else 0.0

    def _calculate_type_compatibility(self, result: SearchResult, binding: DeliverableSearchBinding) -> float:
        """计算搜索类型兼容性"""
        result_type = result.search_type.value
        compatible_types = self.deliverable_profiles[binding.deliverable_id]["search_types"]

        if result_type in compatible_types:
            return 1.0

        # 检查类型间的兼容性
        compatibility_rules = {
            "concept": ["trends", "expert", "cases"],
            "academic": ["technical", "concept"],
            "trends": ["concept", "expert", "data"],
            "cases": ["concept", "trends", "expert"],
            "data": ["trends", "cases"],
            "expert": ["trends", "cases", "concept"],
            "technical": ["academic", "cases"],
            "dimension": ["concept", "academic"],
        }

        compatible_with_result = compatibility_rules.get(result_type, [])

        for compatible_type in compatible_with_result:
            if compatible_type in compatible_types:
                return 0.7  # 部分兼容

        return 0.2  # 低兼容性，但不完全排除

    def _execute_distribution(
        self, search_results: List[SearchResult], relevance_matrix: Dict[str, Dict[str, float]]
    ) -> Dict[str, List[DistributedResult]]:
        """执行智能分发"""
        distribution = defaultdict(list)

        for result in search_results:
            result_id = f"{result.task_id}_{result.search_type.value}"

            if result_id not in relevance_matrix:
                continue

            # 获取相关性分数
            relevance_scores = relevance_matrix[result_id]

            # 筛选相关的交付物
            relevant_deliverables = [
                deliverable_id
                for deliverable_id, score in relevance_scores.items()
                if score >= self.relevance_threshold
            ]

            if relevant_deliverables:
                # 创建分发结果
                distributed_result = DistributedResult(
                    original_result=result,
                    target_deliverable_ids=relevant_deliverables,
                    relevance_scores=relevance_scores,
                    distribution_metadata={
                        "distribution_reason": "relevance_based",
                        "max_relevance": max(relevance_scores.values()),
                        "avg_relevance": sum(relevance_scores.values()) / len(relevance_scores),
                    },
                )

                # 分发给所有相关交付物
                for deliverable_id in relevant_deliverables:
                    distribution[deliverable_id].append(distributed_result)
            else:
                # 降级策略：分发给原始交付物
                original_deliverable = result.deliverable_id
                if original_deliverable:
                    distributed_result = DistributedResult(
                        original_result=result,
                        target_deliverable_ids=[original_deliverable],
                        relevance_scores={original_deliverable: 1.0},
                        distribution_metadata={
                            "distribution_reason": "fallback_to_original",
                            "max_relevance": 1.0,
                        },
                    )
                    distribution[original_deliverable].append(distributed_result)

        return dict(distribution)

    def _identify_shared_results(
        self, distributed_results: Dict[str, List[DistributedResult]]
    ) -> List[DistributedResult]:
        """识别可跨交付物共享的结果"""
        shared_results = []

        # 统计结果出现频率
        result_frequency = defaultdict(int)
        result_map = {}

        for deliverable_id, results in distributed_results.items():
            for dist_result in results:
                result_key = f"{dist_result.original_result.task_id}_{dist_result.original_result.search_type.value}"
                result_frequency[result_key] += 1
                result_map[result_key] = dist_result

        # 筛选高频且高质量的结果
        for result_key, frequency in result_frequency.items():
            if frequency >= 2:  # 至少被2个交付物使用
                dist_result = result_map[result_key]
                if dist_result.original_result.quality_score >= self.sharing_threshold * 100:
                    shared_results.append(dist_result)

        logger.info(f"🔗 [SearchResultDistributor] 识别出{len(shared_results)}个共享结果")
        return shared_results

    def _optimize_distribution(
        self, distributed_results: Dict[str, List[DistributedResult]], shared_results: List[DistributedResult]
    ) -> Dict[str, List[DistributedResult]]:
        """优化分发策略"""
        optimized = distributed_results.copy()

        # 为每个交付物添加相关的共享结果
        for deliverable_id, current_results in optimized.items():
            current_result_ids = {
                f"{r.original_result.task_id}_{r.original_result.search_type.value}" for r in current_results
            }

            # 添加未包含的相关共享结果
            for shared_result in shared_results:
                shared_result_id = (
                    f"{shared_result.original_result.task_id}_{shared_result.original_result.search_type.value}"
                )

                if shared_result_id not in current_result_ids:
                    # 检查与当前交付物的相关性
                    if deliverable_id in shared_result.relevance_scores:
                        relevance = shared_result.relevance_scores[deliverable_id]
                        if relevance >= self.relevance_threshold * 0.8:  # 稍微放宽标准
                            # 创建共享结果副本
                            shared_copy = DistributedResult(
                                original_result=shared_result.original_result,
                                target_deliverable_ids=[deliverable_id],
                                relevance_scores={deliverable_id: relevance},
                                distribution_metadata={
                                    "distribution_reason": "shared_result",
                                    "shared_from": shared_result.target_deliverable_ids,
                                },
                            )
                            optimized[deliverable_id].append(shared_copy)

        return optimized

    def _record_distribution_statistics(
        self,
        distribution: Dict[str, List[DistributedResult]],
        shared_results: List[DistributedResult],
        execution_time: float,
    ):
        """记录分发统计信息"""
        total_results = sum(len(results) for results in distribution.values())
        distributed_results = len(
            set(
                f"{r.original_result.task_id}_{r.original_result.search_type.value}"
                for results in distribution.values()
                for r in results
            )
        )

        deliverable_coverage = {deliverable_id: len(results) for deliverable_id, results in distribution.items()}

        # 计算分发质量
        quality_scores = []
        for results in distribution.values():
            for result in results:
                max_relevance = result.distribution_metadata.get("max_relevance", 0.0)
                quality_scores.append(max_relevance)

        distribution_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

        report = DistributionReport(
            total_results=total_results,
            distributed_results=distributed_results,
            shared_results=len(shared_results),
            deliverable_coverage=deliverable_coverage,
            distribution_quality=distribution_quality,
            execution_time=execution_time,
        )

        self.distribution_history.append(report)

        logger.info(f"📊 [SearchResultDistributor] 分发统计:")
        logger.info(f"  总结果数: {total_results}")
        logger.info(f"  唯一结果数: {distributed_results}")
        logger.info(f"  共享结果数: {len(shared_results)}")
        logger.info(f"  分发质量: {distribution_quality:.2f}")
        logger.info(f"  交付物覆盖: {deliverable_coverage}")

    # 辅助方法
    def _extract_deliverable_keywords(self, binding: DeliverableSearchBinding) -> List[str]:
        """从交付物绑定中提取关键词"""
        keywords = []

        # 从名称提取
        name_words = binding.deliverable_name.lower().split()
        keywords.extend([w for w in name_words if len(w) > 2])

        # 从类型提取
        type_words = binding.deliverable_type.replace("_", " ").split()
        keywords.extend([w for w in type_words if len(w) > 2])

        # 从元数据提取
        description = binding.binding_metadata.get("deliverable_description", "")
        if description:
            desc_words = description.lower().split()
            keywords.extend([w for w in desc_words[:10] if len(w) > 2])  # 限制数量

        # 去重并返回
        return list(set(keywords))

    def _calculate_deliverable_priority(self, binding: DeliverableSearchBinding) -> int:
        """计算交付物优先级"""
        priority = 3  # 默认优先级

        # 基于复杂度调整
        if binding.search_complexity >= 4:
            priority = 2
        elif binding.search_complexity <= 2:
            priority = 4

        # 基于搜索类型调整
        high_priority_types = {SearchType.CONCEPT_EXPLORATION, SearchType.ACADEMIC_RESEARCH}
        if any(st in high_priority_types for st in binding.required_search_types):
            priority = max(1, priority - 1)

        return min(5, max(1, priority))

    def _build_compatibility_matrix(self, binding: DeliverableSearchBinding) -> Dict[str, float]:
        """构建交付物与搜索类型的兼容性矩阵"""
        compatibility = {}

        for search_type in binding.required_search_types:
            compatibility[search_type.value] = 1.0

        # 添加兼容性规则
        type_compatibility = {
            "concept": ["trends", "expert"],
            "academic": ["technical", "concept"],
            "trends": ["concept", "data"],
            "cases": ["concept", "expert"],
        }

        for primary_type in binding.required_search_types:
            compatible_types = type_compatibility.get(primary_type.value, [])
            for comp_type in compatible_types:
                if comp_type not in compatibility:
                    compatibility[comp_type] = 0.7

        return compatibility


# 便捷函数
def distribute_search_results_to_deliverables(
    search_results: List[SearchResult],
    deliverable_bindings: List[DeliverableSearchBinding],
    session_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, List[DistributedResult]]:
    """分发搜索结果给交付物的便捷函数"""
    distributor = SearchResultDistributor()
    return distributor.distribute_search_results(search_results, deliverable_bindings, session_context)
