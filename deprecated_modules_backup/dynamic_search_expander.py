"""
动态搜索扩展器 - 基于搜索结果发现触发补充搜索
实现搜索质量反馈循环和策略优化，支持发散性搜索任务生成
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from .search_coordinator import SearchCoordinator, SearchResult
from .search_task_planner import SearchMasterPlan, SearchTask, SearchType

logger = logging.getLogger(__name__)


class ExpansionTrigger(Enum):
    """搜索扩展触发器"""

    QUALITY_GAP = "quality_gap"  # 质量缺口
    COVERAGE_GAP = "coverage_gap"  # 覆盖缺口
    DISCOVERY_SIGNAL = "discovery"  # 发现信号
    USER_FEEDBACK = "user_feedback"  # 用户反馈
    AUTOMATIC_DEPTH = "auto_depth"  # 自动深化


@dataclass
class SearchGap:
    """搜索缺口定义"""

    gap_type: ExpansionTrigger
    deliverable_id: str
    missing_search_types: List[SearchType]
    quality_threshold: float
    current_quality: float
    gap_severity: float  # 0-1, 1为最严重
    suggested_queries: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExpansionTask:
    """扩展搜索任务"""

    task_id: str
    trigger: ExpansionTrigger
    original_plan_id: str
    gap_analysis: SearchGap
    new_search_tasks: List[SearchTask]
    priority: int = 1
    estimated_impact: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class QualityFeedback:
    """质量反馈"""

    deliverable_id: str
    search_type: SearchType
    expected_quality: float
    actual_quality: float
    quality_gap: float
    feedback_source: str  # "automatic", "user", "expert"
    improvement_suggestions: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


class DynamicSearchExpander:
    """动态搜索扩展器 - 智能补充和优化搜索任务"""

    def __init__(self):
        self.gap_history = []  # 缺口历史
        self.expansion_history = []  # 扩展历史
        self.quality_feedback_history = []  # 质量反馈历史

        # 扩展配置
        self.quality_gap_threshold = 0.2  # 质量缺口阈值
        self.coverage_gap_threshold = 0.3  # 覆盖缺口阈值
        self.max_expansion_rounds = 3  # 最大扩展轮数

        # 搜索类型扩展映射
        self.expansion_mappings = {
            SearchType.CONCEPT_EXPLORATION: [SearchType.TREND_ANALYSIS, SearchType.CASE_STUDIES],
            SearchType.ACADEMIC_RESEARCH: [SearchType.TECHNICAL_SPECS, SearchType.EXPERT_INSIGHTS],
            SearchType.TREND_ANALYSIS: [SearchType.DATA_STATISTICS, SearchType.EXPERT_INSIGHTS],
            SearchType.CASE_STUDIES: [SearchType.EXPERT_INSIGHTS, SearchType.DIMENSION_ANALYSIS],
            SearchType.DATA_STATISTICS: [SearchType.TREND_ANALYSIS, SearchType.EXPERT_INSIGHTS],
        }

    async def analyze_and_expand_search(
        self,
        original_plan: SearchMasterPlan,
        search_results: List[SearchResult],
        quality_feedback: Optional[List[QualityFeedback]] = None,
    ) -> Optional[SearchMasterPlan]:
        """
        分析搜索结果并生成扩展搜索计划

        Args:
            original_plan: 原始搜索计划
            search_results: 搜索结果
            quality_feedback: 质量反馈

        Returns:
            扩展搜索计划（如果需要）
        """
        logger.info(f"🔍 [DynamicSearchExpander] 开始分析搜索结果，结果数量: {len(search_results)}")

        start_time = time.time()

        # Step 1: 分析搜索缺口
        search_gaps = self._analyze_search_gaps(original_plan, search_results, quality_feedback)

        if not search_gaps:
            logger.info("✅ [DynamicSearchExpander] 未发现需要扩展的搜索缺口")
            return None

        # Step 2: 生成扩展任务
        expansion_tasks = self._generate_expansion_tasks(search_gaps, original_plan)

        # Step 3: 构建扩展搜索计划
        expansion_plan = await self._build_expansion_plan(expansion_tasks, original_plan)

        # Step 4: 记录扩展历史
        self._record_expansion_attempt(expansion_tasks, expansion_plan)

        analysis_time = time.time() - start_time

        logger.info(f"✅ [DynamicSearchExpander] 扩展分析完成，耗时{analysis_time:.2f}秒")
        logger.info(f"📊 [DynamicSearchExpander] 生成{len(expansion_tasks)}个扩展任务")

        return expansion_plan

    def _analyze_search_gaps(
        self,
        original_plan: SearchMasterPlan,
        search_results: List[SearchResult],
        quality_feedback: Optional[List[QualityFeedback]],
    ) -> List[SearchGap]:
        """分析搜索缺口"""
        gaps = []

        # 按交付物分组分析
        results_by_deliverable = self._group_results_by_deliverable(search_results)

        for binding in original_plan.deliverable_bindings:
            deliverable_id = binding.deliverable_id
            deliverable_results = results_by_deliverable.get(deliverable_id, [])

            # 1. 质量缺口分析
            quality_gaps = self._analyze_quality_gaps(binding, deliverable_results, quality_feedback)
            gaps.extend(quality_gaps)

            # 2. 覆盖缺口分析
            coverage_gaps = self._analyze_coverage_gaps(binding, deliverable_results)
            gaps.extend(coverage_gaps)

            # 3. 发现信号分析
            discovery_gaps = self._analyze_discovery_signals(binding, deliverable_results)
            gaps.extend(discovery_gaps)

        # 按严重程度排序
        gaps.sort(key=lambda g: g.gap_severity, reverse=True)

        logger.debug(f"🔍 [DynamicSearchExpander] 发现{len(gaps)}个搜索缺口")
        return gaps

    def _analyze_quality_gaps(
        self, binding, deliverable_results: List[SearchResult], quality_feedback: Optional[List[QualityFeedback]]
    ) -> List[SearchGap]:
        """分析质量缺口"""
        gaps = []

        # 计算各搜索类型的质量
        type_quality = {}
        for result in deliverable_results:
            search_type = result.search_type
            if search_type not in type_quality:
                type_quality[search_type] = []
            type_quality[search_type].append(result.quality_score)

        # 计算平均质量
        avg_quality_by_type = {st: sum(scores) / len(scores) for st, scores in type_quality.items()}

        # 检查质量缺口
        for search_type in binding.required_search_types:
            expected_quality = binding.quality_threshold * 100  # 转换为0-100范围
            actual_quality = avg_quality_by_type.get(search_type, 0.0)

            quality_gap = (expected_quality - actual_quality) / 100.0

            if quality_gap >= self.quality_gap_threshold:
                gap = SearchGap(
                    gap_type=ExpansionTrigger.QUALITY_GAP,
                    deliverable_id=binding.deliverable_id,
                    missing_search_types=[search_type],
                    quality_threshold=expected_quality,
                    current_quality=actual_quality,
                    gap_severity=min(quality_gap / 0.5, 1.0),  # 归一化
                    suggested_queries=self._generate_quality_improvement_queries(binding, search_type),
                    metadata={
                        "search_type": search_type.value,
                        "expected_quality": expected_quality,
                        "actual_quality": actual_quality,
                    },
                )
                gaps.append(gap)

        return gaps

    def _analyze_coverage_gaps(self, binding, deliverable_results: List[SearchResult]) -> List[SearchGap]:
        """分析覆盖缺口"""
        gaps = []

        # 统计已覆盖的搜索类型
        covered_types = {result.search_type for result in deliverable_results if result.success}
        required_types = set(binding.required_search_types)

        missing_types = required_types - covered_types

        if missing_types:
            coverage_ratio = len(covered_types) / len(required_types)
            gap_severity = 1.0 - coverage_ratio

            if gap_severity >= self.coverage_gap_threshold:
                gap = SearchGap(
                    gap_type=ExpansionTrigger.COVERAGE_GAP,
                    deliverable_id=binding.deliverable_id,
                    missing_search_types=list(missing_types),
                    quality_threshold=binding.quality_threshold,
                    current_quality=coverage_ratio,
                    gap_severity=gap_severity,
                    suggested_queries=self._generate_coverage_queries(binding, missing_types),
                    metadata={
                        "missing_types": [t.value for t in missing_types],
                        "coverage_ratio": coverage_ratio,
                    },
                )
                gaps.append(gap)

        return gaps

    def _analyze_discovery_signals(self, binding, deliverable_results: List[SearchResult]) -> List[SearchGap]:
        """分析发现信号 - 从搜索结果中发现新的搜索机会"""
        gaps = []

        # 提取发现关键词
        discovery_keywords = set()
        for result in deliverable_results:
            if result.success and result.quality_score >= 70:
                for item in result.results:
                    title = item.get("title", "")
                    snippet = item.get("snippet", "")

                    # 简单关键词提取
                    discovery_keywords.update(self._extract_discovery_keywords(title + " " + snippet))

        # 识别新的搜索方向
        if len(discovery_keywords) >= 5:  # 足够的发现信号
            # 判断是否值得深化搜索
            if self._should_expand_discovery(discovery_keywords, binding):
                expansion_types = self._suggest_discovery_expansion_types(binding)

                if expansion_types:
                    gap = SearchGap(
                        gap_type=ExpansionTrigger.DISCOVERY_SIGNAL,
                        deliverable_id=binding.deliverable_id,
                        missing_search_types=expansion_types,
                        quality_threshold=binding.quality_threshold,
                        current_quality=0.5,  # 发现信号的质量评估
                        gap_severity=0.6,  # 中等严重程度
                        suggested_queries=self._generate_discovery_queries(discovery_keywords, binding),
                        metadata={
                            "discovery_keywords": list(discovery_keywords)[:10],
                            "expansion_reason": "rich_discovery_signals",
                        },
                    )
                    gaps.append(gap)

        return gaps

    def _generate_expansion_tasks(
        self, search_gaps: List[SearchGap], original_plan: SearchMasterPlan
    ) -> List[ExpansionTask]:
        """生成扩展任务"""
        expansion_tasks = []

        for gap in search_gaps[:5]:  # 最多处理前5个最严重的缺口
            # 生成新的搜索任务
            new_search_tasks = self._create_gap_filling_tasks(gap, original_plan)

            if new_search_tasks:
                expansion_task = ExpansionTask(
                    task_id=f"expansion_{gap.gap_type.value}_{gap.deliverable_id}_{int(time.time())}",
                    trigger=gap.gap_type,
                    original_plan_id=original_plan.plan_id,
                    gap_analysis=gap,
                    new_search_tasks=new_search_tasks,
                    priority=self._calculate_expansion_priority(gap),
                    estimated_impact=gap.gap_severity,
                )
                expansion_tasks.append(expansion_task)

        return expansion_tasks

    def _create_gap_filling_tasks(self, gap: SearchGap, original_plan: SearchMasterPlan) -> List[SearchTask]:
        """创建填补缺口的搜索任务"""
        tasks = []

        for search_type in gap.missing_search_types:
            task_id = f"gap_fill_{search_type.value}_{gap.deliverable_id}_{int(time.time())}"

            # 生成查询
            queries = (
                gap.suggested_queries[:3]
                if gap.suggested_queries
                else [f"{gap.deliverable_id} {search_type.value} expansion"]
            )

            # 选择工具
            tool_preferences = {
                SearchType.ACADEMIC_RESEARCH: ["arxiv_search", "milvus_kb"],
                SearchType.TREND_ANALYSIS: ["bocha_search", "tavily_search"],
                SearchType.CASE_STUDIES: ["tavily_search", "bocha_search"],
                SearchType.DATA_STATISTICS: ["tavily_search", "bocha_search"],
                SearchType.EXPERT_INSIGHTS: ["bocha_search", "tavily_search"],
                SearchType.TECHNICAL_SPECS: ["arxiv_search", "tavily_search"],
            }

            required_tools = tool_preferences.get(search_type, ["tavily_search"])

            task = SearchTask(
                task_id=task_id,
                deliverable_id=gap.deliverable_id,
                search_type=search_type,
                queries=queries,
                priority=self._calculate_task_priority_for_gap(gap, search_type),
                dependencies=[],
                estimated_duration=45,  # 扩展任务通常需要更多时间
                required_tools=required_tools,
                quality_requirements={
                    "min_results": 3,
                    "quality_threshold": gap.quality_threshold,
                    "max_results": 12,
                },
                metadata={
                    "expansion_trigger": gap.gap_type.value,
                    "gap_severity": gap.gap_severity,
                    "original_plan": original_plan.plan_id,
                },
            )

            tasks.append(task)

        return tasks

    async def _build_expansion_plan(
        self, expansion_tasks: List[ExpansionTask], original_plan: SearchMasterPlan
    ) -> SearchMasterPlan:
        """构建扩展搜索计划"""
        if not expansion_tasks:
            return None

        # 收集所有新搜索任务
        all_new_tasks = []
        for expansion_task in expansion_tasks:
            all_new_tasks.extend(expansion_task.new_search_tasks)

        # 计算执行顺序
        execution_order = [task.task_id for task in all_new_tasks]

        # 估算资源需求
        resource_requirements = self._estimate_expansion_resource_requirements(all_new_tasks)

        expansion_plan = SearchMasterPlan(
            plan_id=f"expansion_{original_plan.plan_id}_{int(time.time())}",
            requirements_summary=original_plan.requirements_summary,
            deliverable_bindings=original_plan.deliverable_bindings,
            search_tasks=all_new_tasks,
            dependency_graph={task.task_id: task.dependencies for task in all_new_tasks},
            execution_order=execution_order,
            total_estimated_time=sum(task.estimated_duration for task in all_new_tasks),
            resource_requirements=resource_requirements,
        )

        return expansion_plan

    # 辅助方法
    def _group_results_by_deliverable(self, search_results: List[SearchResult]) -> Dict[str, List[SearchResult]]:
        """按交付物分组搜索结果"""
        grouped = {}
        for result in search_results:
            deliverable_id = result.deliverable_id
            if deliverable_id not in grouped:
                grouped[deliverable_id] = []
            grouped[deliverable_id].append(result)
        return grouped

    def _generate_quality_improvement_queries(self, binding, search_type: SearchType) -> List[str]:
        """生成质量改进查询"""
        base_name = binding.deliverable_name

        quality_queries = {
            SearchType.CONCEPT_EXPLORATION: [
                f"{base_name} best practices methodology",
                f"advanced {base_name} framework analysis",
                f"{base_name} expert design principles",
            ],
            SearchType.ACADEMIC_RESEARCH: [
                f"{base_name} peer reviewed research",
                f"{base_name} academic methodology study",
                f"scholarly {base_name} analysis framework",
            ],
            SearchType.TREND_ANALYSIS: [
                f"{base_name} emerging trends 2024 2025",
                f"future {base_name} innovations",
                f"{base_name} industry evolution patterns",
            ],
            SearchType.CASE_STUDIES: [
                f"successful {base_name} implementation examples",
                f"{base_name} proven case studies",
                f"award winning {base_name} projects",
            ],
        }

        return quality_queries.get(search_type, [f"high quality {base_name} {search_type.value}"])

    def _generate_coverage_queries(self, binding, missing_types: Set[SearchType]) -> List[str]:
        """生成覆盖缺口查询"""
        base_name = binding.deliverable_name
        queries = []

        for search_type in missing_types:
            queries.extend(
                [f"{base_name} {search_type.value} comprehensive", f"complete {base_name} {search_type.value} guide"]
            )

        return queries[:6]  # 限制查询数量

    def _extract_discovery_keywords(self, text: str) -> Set[str]:
        """提取发现关键词"""
        import re

        # 发现信号关键词
        discovery_indicators = [
            "new",
            "emerging",
            "innovative",
            "breakthrough",
            "advanced",
            "cutting-edge",
            "novel",
            "revolutionary",
            "next-generation",
            "future",
            "trend",
            "evolution",
            "development",
        ]

        words = re.findall(r"\w+", text.lower())
        discovery_keywords = set()

        # 查找发现信号词汇附近的关键词
        for i, word in enumerate(words):
            if word in discovery_indicators:
                # 提取附近的词汇
                context_start = max(0, i - 2)
                context_end = min(len(words), i + 3)
                context_words = words[context_start:context_end]

                # 过滤和添加
                for ctx_word in context_words:
                    if len(ctx_word) > 3 and ctx_word not in discovery_indicators:
                        discovery_keywords.add(ctx_word)

        return discovery_keywords

    def _should_expand_discovery(self, keywords: Set[str], binding) -> bool:
        """判断是否应该基于发现进行扩展"""
        # 检查关键词与交付物的相关性
        deliverable_name_words = set(binding.deliverable_name.lower().split())
        relevance = len(keywords.intersection(deliverable_name_words)) / len(deliverable_name_words)

        return relevance >= 0.2 and len(keywords) >= 3

    def _suggest_discovery_expansion_types(self, binding) -> List[SearchType]:
        """基于发现建议扩展搜索类型"""
        current_types = set(binding.required_search_types)

        # 基于现有类型建议扩展类型
        expansion_suggestions = []
        for current_type in current_types:
            suggested = self.expansion_mappings.get(current_type, [])
            expansion_suggestions.extend(suggested)

        # 去重并排除已有类型
        new_types = list(set(expansion_suggestions) - current_types)
        return new_types[:2]  # 最多2个新类型

    def _generate_discovery_queries(self, keywords: Set[str], binding) -> List[str]:
        """生成发现查询"""
        base_name = binding.deliverable_name
        keyword_list = list(keywords)[:5]

        queries = [
            f"{base_name} {' '.join(keyword_list[:3])}",
            f"advanced {base_name} {' '.join(keyword_list[2:5])}",
            f"innovative {base_name} {keyword_list[0]} solutions",
        ]

        return queries

    def _calculate_expansion_priority(self, gap: SearchGap) -> int:
        """计算扩展优先级"""
        if gap.gap_type == ExpansionTrigger.QUALITY_GAP:
            return max(1, 3 - int(gap.gap_severity * 2))
        elif gap.gap_type == ExpansionTrigger.COVERAGE_GAP:
            return max(1, 4 - int(gap.gap_severity * 2))
        else:
            return 3

    def _calculate_task_priority_for_gap(self, gap: SearchGap, search_type: SearchType) -> int:
        """为缺口任务计算优先级"""
        base_priority = 2  # 扩展任务通常优先级较低

        if gap.gap_severity >= 0.8:
            base_priority = 1
        elif gap.gap_severity <= 0.3:
            base_priority = 4

        return base_priority

    def _estimate_expansion_resource_requirements(self, tasks: List[SearchTask]) -> Dict[str, int]:
        """估算扩展资源需求"""
        requirements = {
            "total_api_calls": len(tasks) * 3,  # 平均每任务3个查询
            "concurrent_searches": min(len(tasks), 2),  # 扩展搜索并发较低
            "estimated_cost": len(tasks) * 0.015,  # 扩展搜索成本稍高
            "tool_usage": {},
        }

        for task in tasks:
            for tool in task.required_tools:
                requirements["tool_usage"][tool] = requirements["tool_usage"].get(tool, 0) + 1

        return requirements

    def _record_expansion_attempt(
        self, expansion_tasks: List[ExpansionTask], expansion_plan: Optional[SearchMasterPlan]
    ):
        """记录扩展尝试"""
        self.expansion_history.append(
            {
                "timestamp": datetime.now(),
                "expansion_tasks": len(expansion_tasks),
                "plan_generated": expansion_plan is not None,
                "triggers": [task.trigger.value for task in expansion_tasks],
            }
        )


# 便捷函数
async def expand_search_based_on_results(
    original_plan: SearchMasterPlan,
    search_results: List[SearchResult],
    quality_feedback: Optional[List[QualityFeedback]] = None,
) -> Optional[SearchMasterPlan]:
    """基于搜索结果扩展搜索的便捷函数"""
    expander = DynamicSearchExpander()
    return await expander.analyze_and_expand_search(original_plan, search_results, quality_feedback)
