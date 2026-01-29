"""
搜索任务预规划器 - 结果导向架构核心组件
基于需求分析和交付物框架生成完整的搜索任务主线
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class SearchType(Enum):
    """搜索类型枚举"""

    CONCEPT_EXPLORATION = "concept"  # 概念探索
    DIMENSION_ANALYSIS = "dimension"  # 维度分析
    ACADEMIC_RESEARCH = "academic"  # 学术研究
    CASE_STUDIES = "cases"  # 案例研究
    DATA_STATISTICS = "data"  # 数据统计
    TREND_ANALYSIS = "trends"  # 趋势分析
    EXPERT_INSIGHTS = "expert"  # 专家观点
    TECHNICAL_SPECS = "technical"  # 技术规格


@dataclass
class SearchTask:
    """搜索任务定义"""

    task_id: str
    deliverable_id: str
    search_type: SearchType
    queries: List[str]
    priority: int = 1  # 1=最高, 5=最低
    dependencies: List[str] = field(default_factory=list)
    estimated_duration: int = 30  # 估计执行时间（秒）
    required_tools: List[str] = field(default_factory=list)
    quality_requirements: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "planned"  # planned, queued, executing, completed, failed
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class DeliverableSearchBinding:
    """交付物搜索绑定"""

    deliverable_id: str
    deliverable_name: str
    deliverable_type: str
    required_search_types: List[SearchType]
    search_complexity: int = 1  # 1-5, 影响搜索深度和资源分配
    quality_threshold: float = 0.7
    max_search_tasks: int = 3
    binding_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchMasterPlan:
    """搜索主计划"""

    plan_id: str
    requirements_summary: Dict[str, Any]
    deliverable_bindings: List[DeliverableSearchBinding]
    search_tasks: List[SearchTask]
    dependency_graph: Dict[str, List[str]]
    execution_order: List[str]
    total_estimated_time: int
    resource_requirements: Dict[str, int]
    created_at: datetime = field(default_factory=datetime.now)


class SearchTaskPlanner:
    """搜索任务预规划器 - 结果导向架构核心"""

    def __init__(self):
        self.task_counter = 0

        # 交付物类型与搜索类型映射
        self.deliverable_search_mapping = {
            "user_persona": [SearchType.CASE_STUDIES, SearchType.DATA_STATISTICS],
            "space_analysis": [SearchType.CONCEPT_EXPLORATION, SearchType.TREND_ANALYSIS],
            "market_research": [SearchType.DATA_STATISTICS, SearchType.EXPERT_INSIGHTS],
            "design_strategy": [SearchType.CONCEPT_EXPLORATION, SearchType.CASE_STUDIES],
            "technical_specs": [SearchType.TECHNICAL_SPECS, SearchType.ACADEMIC_RESEARCH],
            "trend_analysis": [SearchType.TREND_ANALYSIS, SearchType.EXPERT_INSIGHTS],
            "risk_assessment": [SearchType.CASE_STUDIES, SearchType.EXPERT_INSIGHTS],
            "implementation_plan": [SearchType.TECHNICAL_SPECS, SearchType.CASE_STUDIES],
        }

        # 搜索工具优先级配置
        self.tool_preferences = {
            SearchType.ACADEMIC_RESEARCH: ["arxiv_search", "milvus_kb"],
            SearchType.TREND_ANALYSIS: ["bocha_search", "tavily_search"],
            SearchType.CASE_STUDIES: ["tavily_search", "bocha_search", "milvus_kb"],
            SearchType.DATA_STATISTICS: ["tavily_search", "bocha_search"],
            SearchType.CONCEPT_EXPLORATION: ["bocha_search", "tavily_search", "milvus_kb"],
            SearchType.EXPERT_INSIGHTS: ["bocha_search", "tavily_search"],
            SearchType.TECHNICAL_SPECS: ["arxiv_search", "tavily_search"],
            SearchType.DIMENSION_ANALYSIS: ["milvus_kb", "bocha_search"],
        }

    def generate_search_master_plan(
        self,
        requirements: Dict[str, Any],
        deliverables: List[Dict[str, Any]],
        questionnaire: Optional[Dict[str, Any]] = None,
    ) -> SearchMasterPlan:
        """
        基于需求分析和交付物框架生成搜索任务主线

        Args:
            requirements: 需求分析结果
            deliverables: 交付物列表
            questionnaire: 可选的问卷答案

        Returns:
            完整的搜索主计划
        """
        logger.info(f"🎯 [SearchTaskPlanner] 开始生成搜索主计划，交付物数量: {len(deliverables)}")

        plan_start = time.time()

        # Step 1: 生成交付物搜索绑定
        deliverable_bindings = self._generate_deliverable_bindings(deliverables, requirements)

        # Step 2: 生成搜索任务
        search_tasks = self._generate_search_tasks(deliverable_bindings, requirements)

        # Step 3: 建立依赖关系
        dependency_graph = self._build_dependency_graph(search_tasks)

        # Step 4: 计算执行顺序
        execution_order = self._calculate_execution_order(search_tasks, dependency_graph)

        # Step 5: 估算资源需求
        resource_requirements = self._estimate_resource_requirements(search_tasks)

        plan_time = time.time() - plan_start

        plan_id = f"search_plan_{int(time.time())}_{len(search_tasks)}"

        master_plan = SearchMasterPlan(
            plan_id=plan_id,
            requirements_summary=self._extract_requirements_summary(requirements),
            deliverable_bindings=deliverable_bindings,
            search_tasks=search_tasks,
            dependency_graph=dependency_graph,
            execution_order=execution_order,
            total_estimated_time=sum(task.estimated_duration for task in search_tasks),
            resource_requirements=resource_requirements,
        )

        logger.info(f"✅ [SearchTaskPlanner] 搜索主计划生成完成，用时{plan_time:.2f}s")
        logger.info(f"📊 [SearchTaskPlanner] 计划统计: {len(search_tasks)}个搜索任务, {len(deliverable_bindings)}个交付物绑定")

        return master_plan

    def _generate_deliverable_bindings(
        self, deliverables: List[Dict[str, Any]], requirements: Dict[str, Any]
    ) -> List[DeliverableSearchBinding]:
        """生成交付物搜索绑定"""
        bindings = []

        for deliverable in deliverables:
            deliverable_id = deliverable.get("id", "")
            deliverable_name = deliverable.get("name", "")
            deliverable_type = self._infer_deliverable_type(deliverable)

            # 根据交付物类型确定搜索类型
            required_search_types = self.deliverable_search_mapping.get(
                deliverable_type, [SearchType.CONCEPT_EXPLORATION, SearchType.CASE_STUDIES]
            )

            # 根据需求复杂度调整搜索复杂度
            search_complexity = self._calculate_search_complexity(deliverable, requirements)

            binding = DeliverableSearchBinding(
                deliverable_id=deliverable_id,
                deliverable_name=deliverable_name,
                deliverable_type=deliverable_type,
                required_search_types=required_search_types,
                search_complexity=search_complexity,
                quality_threshold=0.7,
                max_search_tasks=min(3, len(required_search_types)),
                binding_metadata={
                    "deliverable_description": deliverable.get("description", ""),
                    "deliverable_format": deliverable.get("format", ""),
                    "estimated_complexity": search_complexity,
                },
            )

            bindings.append(binding)

        logger.debug(f"📋 [SearchTaskPlanner] 生成{len(bindings)}个交付物搜索绑定")
        return bindings

    def _generate_search_tasks(
        self, deliverable_bindings: List[DeliverableSearchBinding], requirements: Dict[str, Any]
    ) -> List[SearchTask]:
        """生成搜索任务"""
        tasks = []

        for binding in deliverable_bindings:
            for search_type in binding.required_search_types:
                self.task_counter += 1

                task_id = f"search_task_{self.task_counter:03d}_{search_type.value}_{binding.deliverable_id}"

                # 生成查询关键词
                queries = self._generate_queries_for_search_type(search_type, binding, requirements)

                # 确定优先级
                priority = self._calculate_task_priority(search_type, binding)

                # 选择推荐工具
                required_tools = self.tool_preferences.get(search_type, ["tavily_search"])

                # 估算执行时间
                estimated_duration = self._estimate_task_duration(search_type, binding)

                task = SearchTask(
                    task_id=task_id,
                    deliverable_id=binding.deliverable_id,
                    search_type=search_type,
                    queries=queries,
                    priority=priority,
                    dependencies=[],  # 稍后计算
                    estimated_duration=estimated_duration,
                    required_tools=required_tools,
                    quality_requirements={
                        "min_results": 5,
                        "quality_threshold": binding.quality_threshold,
                        "max_results": 15,
                    },
                    metadata={
                        "deliverable_name": binding.deliverable_name,
                        "search_type": search_type.value,
                        "complexity": binding.search_complexity,
                    },
                )

                tasks.append(task)

        logger.debug(f"🔍 [SearchTaskPlanner] 生成{len(tasks)}个搜索任务")
        return tasks

    def _generate_queries_for_search_type(
        self, search_type: SearchType, binding: DeliverableSearchBinding, requirements: Dict[str, Any]
    ) -> List[str]:
        """为特定搜索类型生成查询关键词"""
        base_keywords = self._extract_keywords_from_requirements(requirements)
        deliverable_keywords = self._extract_keywords_from_deliverable(binding)

        queries = []

        if search_type == SearchType.CONCEPT_EXPLORATION:
            queries.extend(
                [
                    f"{' '.join(base_keywords[:3])} concept design",
                    f"{binding.deliverable_name} design principles",
                    f"{' '.join(deliverable_keywords)} methodology",
                ]
            )

        elif search_type == SearchType.TREND_ANALYSIS:
            queries.extend(
                [
                    f"{' '.join(base_keywords[:2])} trends 2024 2025",
                    f"latest {binding.deliverable_name} innovations",
                    f"emerging {' '.join(deliverable_keywords)} patterns",
                ]
            )

        elif search_type == SearchType.CASE_STUDIES:
            queries.extend(
                [
                    f"{' '.join(base_keywords[:3])} case study successful",
                    f"{binding.deliverable_name} best practices examples",
                    f"successful {' '.join(deliverable_keywords)} implementation",
                ]
            )

        elif search_type == SearchType.ACADEMIC_RESEARCH:
            queries.extend(
                [
                    f"{' '.join(base_keywords[:2])} research methodology",
                    f"{binding.deliverable_name} academic study",
                    f"scientific {' '.join(deliverable_keywords)} analysis",
                ]
            )

        elif search_type == SearchType.DATA_STATISTICS:
            queries.extend(
                [
                    f"{' '.join(base_keywords[:3])} market data statistics",
                    f"{binding.deliverable_name} performance metrics",
                    f"{' '.join(deliverable_keywords)} industry benchmarks",
                ]
            )

        else:
            # 默认查询
            queries.extend(
                [f"{' '.join(base_keywords[:3])}", f"{binding.deliverable_name}", f"{' '.join(deliverable_keywords)}"]
            )

        # 过滤和去重
        queries = [q for q in queries if len(q.strip()) > 5]
        queries = list(dict.fromkeys(queries))  # 去重

        return queries[:3]  # 最多3个查询

    def _build_dependency_graph(self, search_tasks: List[SearchTask]) -> Dict[str, List[str]]:
        """建立搜索任务依赖图"""
        dependency_graph = {}

        # 按交付物分组
        deliverable_groups = {}
        for task in search_tasks:
            deliverable_id = task.deliverable_id
            if deliverable_id not in deliverable_groups:
                deliverable_groups[deliverable_id] = []
            deliverable_groups[deliverable_id].append(task)

        # 建立依赖关系规则
        dependency_rules = {
            SearchType.CONCEPT_EXPLORATION: [],  # 优先执行
            SearchType.ACADEMIC_RESEARCH: [],  # 优先执行
            SearchType.DIMENSION_ANALYSIS: [SearchType.CONCEPT_EXPLORATION],
            SearchType.TREND_ANALYSIS: [SearchType.CONCEPT_EXPLORATION],
            SearchType.CASE_STUDIES: [SearchType.CONCEPT_EXPLORATION, SearchType.ACADEMIC_RESEARCH],
            SearchType.DATA_STATISTICS: [SearchType.CONCEPT_EXPLORATION],
            SearchType.EXPERT_INSIGHTS: [SearchType.TREND_ANALYSIS, SearchType.CASE_STUDIES],
            SearchType.TECHNICAL_SPECS: [SearchType.ACADEMIC_RESEARCH, SearchType.CASE_STUDIES],
        }

        # 应用依赖规则
        for task in search_tasks:
            dependencies = []
            required_predecessors = dependency_rules.get(task.search_type, [])

            # 在同一交付物内查找依赖
            for predecessor_type in required_predecessors:
                for other_task in deliverable_groups[task.deliverable_id]:
                    if other_task.search_type == predecessor_type and other_task.task_id != task.task_id:
                        dependencies.append(other_task.task_id)

            task.dependencies = dependencies
            dependency_graph[task.task_id] = dependencies

        return dependency_graph

    def _calculate_execution_order(
        self, search_tasks: List[SearchTask], dependency_graph: Dict[str, List[str]]
    ) -> List[str]:
        """计算搜索任务执行顺序（拓扑排序）"""
        # 拓扑排序实现
        in_degree = {task.task_id: len(task.dependencies) for task in search_tasks}
        queue = [task.task_id for task in search_tasks if len(task.dependencies) == 0]
        execution_order = []

        while queue:
            # 按优先级排序
            queue.sort(key=lambda task_id: next(task.priority for task in search_tasks if task.task_id == task_id))

            current_task_id = queue.pop(0)
            execution_order.append(current_task_id)

            # 更新依赖计数
            for task in search_tasks:
                if current_task_id in task.dependencies:
                    in_degree[task.task_id] -= 1
                    if in_degree[task.task_id] == 0:
                        queue.append(task.task_id)

        return execution_order

    def _estimate_resource_requirements(self, search_tasks: List[SearchTask]) -> Dict[str, int]:
        """估算资源需求"""
        requirements = {"total_api_calls": 0, "concurrent_searches": 0, "estimated_cost": 0, "tool_usage": {}}

        for task in search_tasks:
            # 估算API调用次数
            api_calls = len(task.queries) * len(task.required_tools)
            requirements["total_api_calls"] += api_calls

            # 统计工具使用
            for tool in task.required_tools:
                requirements["tool_usage"][tool] = requirements["tool_usage"].get(tool, 0) + 1

        # 估算并发搜索数量
        requirements["concurrent_searches"] = min(len(search_tasks), 5)

        # 估算成本（基于API调用）
        cost_per_call = {
            "tavily_search": 0.005,
            "bocha_search": 0.003,
            "arxiv_search": 0.0,
            "milvus_kb": 0.0,
        }

        total_cost = 0
        for tool, usage in requirements["tool_usage"].items():
            tool_cost = cost_per_call.get(tool, 0.001)
            total_cost += usage * tool_cost

        requirements["estimated_cost"] = round(total_cost, 4)

        return requirements

    # 辅助方法
    def _infer_deliverable_type(self, deliverable: Dict[str, Any]) -> str:
        """推断交付物类型"""
        name = deliverable.get("name", "").lower()
        description = deliverable.get("description", "").lower()

        if any(keyword in name for keyword in ["用户", "persona", "画像"]):
            return "user_persona"
        elif any(keyword in name for keyword in ["空间", "space", "layout"]):
            return "space_analysis"
        elif any(keyword in name for keyword in ["市场", "market", "research"]):
            return "market_research"
        elif any(keyword in name for keyword in ["策略", "strategy", "plan"]):
            return "design_strategy"
        elif any(keyword in name for keyword in ["技术", "technical", "spec"]):
            return "technical_specs"
        elif any(keyword in name for keyword in ["趋势", "trend", "analysis"]):
            return "trend_analysis"
        elif any(keyword in name for keyword in ["风险", "risk", "assessment"]):
            return "risk_assessment"
        elif any(keyword in name for keyword in ["实施", "implementation", "plan"]):
            return "implementation_plan"
        else:
            return "general_analysis"

    def _calculate_search_complexity(self, deliverable: Dict[str, Any], requirements: Dict[str, Any]) -> int:
        """计算搜索复杂度 (1-5)"""
        complexity = 1

        # 基于交付物描述长度
        description = deliverable.get("description", "")
        if len(description) > 100:
            complexity += 1

        # 基于需求复杂度
        if len(requirements.get("constraints", [])) > 3:
            complexity += 1

        if requirements.get("project_scope", "") in ["large", "enterprise"]:
            complexity += 1

        # 基于特殊需求
        if requirements.get("special_requirements", []):
            complexity += 1

        return min(complexity, 5)

    def _calculate_task_priority(self, search_type: SearchType, binding: DeliverableSearchBinding) -> int:
        """计算任务优先级 (1=最高, 5=最低)"""
        # 基础优先级
        base_priority = {
            SearchType.CONCEPT_EXPLORATION: 1,
            SearchType.ACADEMIC_RESEARCH: 1,
            SearchType.DIMENSION_ANALYSIS: 2,
            SearchType.CASE_STUDIES: 2,
            SearchType.TREND_ANALYSIS: 3,
            SearchType.DATA_STATISTICS: 3,
            SearchType.EXPERT_INSIGHTS: 4,
            SearchType.TECHNICAL_SPECS: 4,
        }

        priority = base_priority.get(search_type, 3)

        # 根据搜索复杂度调整
        if binding.search_complexity >= 4:
            priority = max(1, priority - 1)  # 提高优先级
        elif binding.search_complexity <= 2:
            priority = min(5, priority + 1)  # 降低优先级

        return priority

    def _estimate_task_duration(self, search_type: SearchType, binding: DeliverableSearchBinding) -> int:
        """估算任务执行时间（秒）"""
        base_duration = {
            SearchType.CONCEPT_EXPLORATION: 30,
            SearchType.ACADEMIC_RESEARCH: 45,
            SearchType.TREND_ANALYSIS: 25,
            SearchType.CASE_STUDIES: 35,
            SearchType.DATA_STATISTICS: 20,
            SearchType.EXPERT_INSIGHTS: 30,
            SearchType.TECHNICAL_SPECS: 40,
            SearchType.DIMENSION_ANALYSIS: 25,
        }

        duration = base_duration.get(search_type, 30)

        # 根据复杂度调整
        duration += (binding.search_complexity - 1) * 10

        return duration

    def _extract_keywords_from_requirements(self, requirements: Dict[str, Any]) -> List[str]:
        """从需求中提取关键词"""
        keywords = []

        # 从项目描述提取
        project_description = requirements.get("project_description", "")
        keywords.extend(self._simple_keyword_extraction(project_description))

        # 从项目类型提取
        project_type = requirements.get("project_type", "")
        if project_type:
            keywords.append(project_type)

        # 从约束条件提取
        constraints = requirements.get("constraints", [])
        for constraint in constraints:
            if isinstance(constraint, str):
                keywords.extend(self._simple_keyword_extraction(constraint))

        return keywords[:10]  # 最多10个关键词

    def _extract_keywords_from_deliverable(self, binding: DeliverableSearchBinding) -> List[str]:
        """从交付物提取关键词"""
        keywords = []

        # 从名称提取
        name_keywords = self._simple_keyword_extraction(binding.deliverable_name)
        keywords.extend(name_keywords)

        # 从描述提取
        description = binding.binding_metadata.get("deliverable_description", "")
        if description:
            desc_keywords = self._simple_keyword_extraction(description)
            keywords.extend(desc_keywords)

        return keywords[:5]  # 最多5个关键词

    def _simple_keyword_extraction(self, text: str) -> List[str]:
        """简单的关键词提取"""
        if not text:
            return []

        # 停用词
        stopwords = {
            "的",
            "和",
            "与",
            "或",
            "但",
            "然而",
            "因为",
            "所以",
            "这",
            "那",
            "这个",
            "那个",
            "a",
            "an",
            "the",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
        }

        # 简单分词（按空格和标点分割）
        import re

        words = re.findall(r"\w+", text.lower())

        # 过滤停用词和短词
        keywords = [word for word in words if len(word) > 2 and word not in stopwords]

        return keywords[:5]

    def _extract_requirements_summary(self, requirements: Dict[str, Any]) -> Dict[str, Any]:
        """提取需求摘要"""
        return {
            "project_type": requirements.get("project_type", ""),
            "main_objectives": requirements.get("main_objectives", [])[:3],
            "key_constraints": requirements.get("constraints", [])[:3],
            "complexity_score": self._calculate_requirements_complexity(requirements),
        }

    def _calculate_requirements_complexity(self, requirements: Dict[str, Any]) -> int:
        """计算需求复杂度"""
        complexity = 1

        if len(requirements.get("constraints", [])) > 5:
            complexity += 1

        if len(requirements.get("special_requirements", [])) > 2:
            complexity += 1

        if requirements.get("project_scope") in ["large", "enterprise"]:
            complexity += 1

        return min(complexity, 5)


# 便捷函数
def create_search_master_plan(
    requirements: Dict[str, Any], deliverables: List[Dict[str, Any]], questionnaire: Optional[Dict[str, Any]] = None
) -> SearchMasterPlan:
    """创建搜索主计划的便捷函数"""
    planner = SearchTaskPlanner()
    return planner.generate_search_master_plan(requirements, deliverables, questionnaire)
