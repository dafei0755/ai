"""
搜索协调器 - 统一调度和结果共享
基于SearchMasterPlan执行协调搜索，避免重复，实现结果跨专家共享
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from .search_task_planner import SearchMasterPlan, SearchTask, SearchType
from .tool_factory import ToolFactory

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """搜索结果统一格式"""

    task_id: str
    deliverable_id: str
    search_type: SearchType
    query: str
    tool_used: str
    success: bool
    results: List[Dict[str, Any]]
    execution_time: float
    quality_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class SearchExecutionReport:
    """搜索执行报告"""

    plan_id: str
    successful_results: List[SearchResult] = field(default_factory=list)
    failed_results: List[SearchResult] = field(default_factory=list)
    total_api_calls: int = 0
    total_cost: float = 0.0
    execution_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CoordinatedSearchResult:
    """协调搜索总结果"""

    master_plan_id: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    execution_time: float
    results_by_deliverable: Dict[str, List[SearchResult]]
    results_by_type: Dict[SearchType, List[SearchResult]]
    shared_results: List[SearchResult]  # 跨交付物共享的结果
    resource_usage: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.now)


class SearchCoordinator:
    """搜索协调器 - 统一调度搜索任务，避免重复，实现结果共享"""

    def __init__(self):
        self.available_tools = {}
        self.result_cache = {}  # 查询缓存
        self.active_tasks = {}  # 活跃任务追踪
        self.shared_results_pool = []  # 共享结果池

        # 初始化搜索工具
        self._initialize_search_tools()

        # 去重配置
        self.similarity_threshold = 0.8  # 查询相似度阈值
        self.cache_ttl = 3600  # 缓存有效期（秒）

    def _initialize_search_tools(self):
        """初始化搜索工具"""
        try:
            tools = ToolFactory.create_all_tools()

            # 将工具按类型分类
            for tool_name, tool in tools.items():
                if tool_name == "tavily":
                    self.available_tools["tavily_search"] = tool
                elif tool_name == "bocha":
                    self.available_tools["bocha_search"] = tool
                elif tool_name == "arxiv":
                    self.available_tools["arxiv_search"] = tool
                elif tool_name == "milvus":
                    self.available_tools["milvus_kb"] = tool

            logger.info(f"🔧 [SearchCoordinator] 初始化完成，可用工具: {list(self.available_tools.keys())}")

        except Exception as e:
            logger.error(f"❌ [SearchCoordinator] 工具初始化失败: {e}")
            self.available_tools = {}

    async def execute_coordinated_search(self, master_plan: SearchMasterPlan) -> CoordinatedSearchResult:
        """
        执行协调搜索

        Args:
            master_plan: 搜索主计划

        Returns:
            协调搜索结果
        """
        logger.info(f"🎯 [SearchCoordinator] 开始执行搜索计划: {master_plan.plan_id}")
        logger.info(
            f"📊 [SearchCoordinator] 任务统计: {len(master_plan.search_tasks)}个任务, 预计耗时{master_plan.total_estimated_time}秒"
        )

        start_time = time.time()

        # Step 1: 去重和缓存检查
        deduplicated_tasks = self._deduplicate_tasks(master_plan.search_tasks)

        # Step 2: 按执行顺序分批执行
        completed_results = await self._execute_tasks_in_batches(deduplicated_tasks, master_plan.execution_order)

        # Step 3: 结果分发和共享
        distributed_results = self._distribute_and_share_results(completed_results, master_plan)

        # Step 4: 生成协调结果
        execution_time = time.time() - start_time
        coordinated_result = self._build_coordinated_result(
            master_plan, completed_results, distributed_results, execution_time
        )

        logger.info(f"✅ [SearchCoordinator] 搜索计划执行完成，耗时{execution_time:.2f}秒")
        logger.info(
            f"📈 [SearchCoordinator] 结果统计: {coordinated_result.completed_tasks}/{coordinated_result.total_tasks}任务完成"
        )

        return coordinated_result

    def _deduplicate_tasks(self, search_tasks: List[SearchTask]) -> List[SearchTask]:
        """去重搜索任务"""
        deduplicated = []
        seen_queries = set()

        for task in search_tasks:
            task_signature = self._generate_task_signature(task)

            # 检查缓存
            if task_signature in self.result_cache:
                cache_entry = self.result_cache[task_signature]
                if self._is_cache_valid(cache_entry):
                    logger.debug(f"💾 [SearchCoordinator] 任务{task.task_id}命中缓存")
                    continue

            # 检查查询相似度
            is_duplicate = False
            for query in task.queries:
                for seen_query in seen_queries:
                    if self._calculate_query_similarity(query, seen_query) > self.similarity_threshold:
                        logger.debug(f"🔄 [SearchCoordinator] 任务{task.task_id}查询重复: {query[:50]}...")
                        is_duplicate = True
                        break
                if is_duplicate:
                    break

            if not is_duplicate:
                deduplicated.append(task)
                seen_queries.update(task.queries)

        logger.info(f"🎯 [SearchCoordinator] 去重完成: {len(search_tasks)} → {len(deduplicated)}个任务")
        return deduplicated

    async def _execute_tasks_in_batches(
        self, tasks: List[SearchTask], execution_order: List[str]
    ) -> List[SearchResult]:
        """分批执行任务"""
        completed_results = []

        # 按依赖关系分批
        batches = self._group_tasks_into_batches(tasks, execution_order)

        for batch_idx, batch in enumerate(batches):
            logger.info(f"🔄 [SearchCoordinator] 执行第{batch_idx + 1}批任务: {len(batch)}个任务")

            # 并发执行当前批次
            batch_results = await self._execute_task_batch(batch)
            completed_results.extend(batch_results)

            # 更新共享结果池
            self._update_shared_results_pool(batch_results)

        return completed_results

    async def _execute_task_batch(self, tasks: List[SearchTask]) -> List[SearchResult]:
        """并发执行一批任务"""
        semaphore = asyncio.Semaphore(3)  # 最多3个并发搜索

        async def execute_single_task(task: SearchTask) -> SearchResult:
            async with semaphore:
                return await self._execute_single_search_task(task)

        # 创建任务并发执行
        batch_futures = [execute_single_task(task) for task in tasks]
        batch_results = await asyncio.gather(*batch_futures, return_exceptions=True)

        # 过滤异常结果
        valid_results = []
        for result in batch_results:
            if isinstance(result, SearchResult):
                valid_results.append(result)
            elif isinstance(result, Exception):
                logger.error(f"❌ [SearchCoordinator] 任务执行异常: {result}")

        return valid_results

    async def _execute_single_search_task(self, task: SearchTask) -> SearchResult:
        """执行单个搜索任务"""
        logger.debug(f"🔍 [SearchCoordinator] 执行任务: {task.task_id}")

        start_time = time.time()

        # 选择最优工具
        selected_tool_name, selected_tool = self._select_optimal_tool(task)

        if not selected_tool:
            logger.error(f"❌ [SearchCoordinator] 任务{task.task_id}无可用工具")
            return SearchResult(
                task_id=task.task_id,
                deliverable_id=task.deliverable_id,
                search_type=task.search_type,
                query="",
                tool_used="none",
                success=False,
                results=[],
                execution_time=time.time() - start_time,
                metadata={"error": "no_available_tool"},
            )

        # 执行搜索
        best_result = None
        best_quality = 0

        for query in task.queries:
            try:
                # 检查是否为LangChain工具
                if hasattr(selected_tool, "invoke"):
                    # LangChain工具调用
                    raw_result = selected_tool.invoke({"query": query})
                    search_result = self._parse_langchain_result(raw_result, query)
                else:
                    # 原始工具调用
                    search_result = self._execute_raw_tool_search(selected_tool, task, query)

                if search_result.get("success", False):
                    quality_score = self._calculate_result_quality(search_result)
                    if quality_score > best_quality:
                        best_result = search_result
                        best_quality = quality_score

            except Exception as e:
                logger.error(f"❌ [SearchCoordinator] 查询执行失败 '{query}': {e}")

        execution_time = time.time() - start_time

        if best_result:
            result = SearchResult(
                task_id=task.task_id,
                deliverable_id=task.deliverable_id,
                search_type=task.search_type,
                query=best_result.get("query", ""),
                tool_used=selected_tool_name,
                success=True,
                results=best_result.get("results", []),
                execution_time=execution_time,
                quality_score=best_quality,
                metadata={
                    "total_queries": len(task.queries),
                    "tool_response_time": execution_time,
                },
            )
        else:
            result = SearchResult(
                task_id=task.task_id,
                deliverable_id=task.deliverable_id,
                search_type=task.search_type,
                query=task.queries[0] if task.queries else "",
                tool_used=selected_tool_name,
                success=False,
                results=[],
                execution_time=execution_time,
                metadata={"error": "all_queries_failed"},
            )

        logger.debug(f"✅ [SearchCoordinator] 任务{task.task_id}完成，质量分数: {result.quality_score:.2f}")
        return result

    def _execute_raw_tool_search(self, tool: Any, task: SearchTask, query: str) -> Dict[str, Any]:
        """执行原始工具搜索"""
        if hasattr(tool, "search_for_deliverable"):
            # 使用交付物搜索方法
            deliverable_mock = {
                "name": f"搜索任务_{task.search_type.value}",
                "description": query,
                "id": task.deliverable_id,
            }
            return tool.search_for_deliverable(
                deliverable_mock, max_results=task.quality_requirements.get("max_results", 10)
            )

        elif hasattr(tool, "search"):
            # 使用标准搜索方法
            return tool.search(query, max_results=task.quality_requirements.get("max_results", 10))

        else:
            logger.warning(f"⚠️ [SearchCoordinator] 工具{type(tool).__name__}无搜索方法")
            return {"success": False, "error": "unsupported_tool_interface"}

    def _parse_langchain_result(self, raw_result: str, query: str) -> Dict[str, Any]:
        """解析LangChain工具返回结果"""
        try:
            # 尝试解析JSON格式结果
            import json

            if isinstance(raw_result, str) and raw_result.startswith("{"):
                parsed = json.loads(raw_result)
                return parsed

            # 简单文本结果转换
            return {
                "success": True,
                "query": query,
                "results": [
                    {
                        "title": "搜索结果",
                        "snippet": str(raw_result)[:500],
                        "url": "",
                        "quality_score": 60.0,
                    }
                ],
                "metadata": {"source": "langchain_tool"},
            }

        except Exception as e:
            logger.error(f"❌ [SearchCoordinator] LangChain结果解析失败: {e}")
            return {"success": False, "error": "parse_failed"}

    def _select_optimal_tool(self, task: SearchTask) -> Tuple[str, Any]:
        """为任务选择最优工具"""
        # 按任务推荐的工具顺序尝试
        for tool_name in task.required_tools:
            if tool_name in self.available_tools:
                tool = self.available_tools[tool_name]
                if self._is_tool_available(tool):
                    return tool_name, tool

        # 降级选择
        fallback_tools = ["tavily_search", "bocha_search", "milvus_kb"]
        for tool_name in fallback_tools:
            if tool_name in self.available_tools:
                tool = self.available_tools[tool_name]
                if self._is_tool_available(tool):
                    logger.warning(f"⚠️ [SearchCoordinator] 任务{task.task_id}降级使用工具: {tool_name}")
                    return tool_name, tool

        return "none", None

    def _is_tool_available(self, tool: Any) -> bool:
        """检查工具是否可用"""
        try:
            if hasattr(tool, "is_available"):
                return tool.is_available()
            else:
                # 简单可用性检查
                return tool is not None
        except:
            return False

    def _distribute_and_share_results(
        self, search_results: List[SearchResult], master_plan: SearchMasterPlan
    ) -> Dict[str, Any]:
        """分发和共享搜索结果"""
        distributed = {
            "by_deliverable": defaultdict(list),
            "by_type": defaultdict(list),
            "shared_results": [],
        }

        # 按交付物和类型分组
        for result in search_results:
            distributed["by_deliverable"][result.deliverable_id].append(result)
            distributed["by_type"][result.search_type].append(result)

            # 识别高质量结果进行共享
            if result.success and result.quality_score >= 80:
                distributed["shared_results"].append(result)

        return distributed

    def _deduplicate_queries(self, queries: List[str]) -> List[str]:
        """去重查询列表"""
        if len(queries) <= 1:
            return queries

        deduplicated = []
        for i, query in enumerate(queries):
            is_duplicate = False
            for j, existing_query in enumerate(deduplicated):
                similarity = self._calculate_query_similarity(query, existing_query)
                if similarity > self.similarity_threshold:
                    logger.debug(
                        f"🔄 [SearchCoordinator] 查询去重: '{query[:30]}...' 与 '{existing_query[:30]}...' 相似度{similarity:.2f}"
                    )
                    is_duplicate = True
                    break

            if not is_duplicate:
                deduplicated.append(query)

        logger.info(f"🎯 [SearchCoordinator] 查询去重: {len(queries)} → {len(deduplicated)}")
        return deduplicated

    def _calculate_query_similarity(self, query1: str, query2: str) -> float:
        """计算查询相似度（简单实现）"""
        if not query1 or not query2:
            return 0.0

        # 转换为小写并分词
        words1 = set(query1.lower().split())
        words2 = set(query2.lower().split())

        if not words1 or not words2:
            return 0.0

        # 计算Jaccard相似度
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    def _generate_task_signature(self, task: SearchTask) -> str:
        """生成任务签名用于缓存"""
        query_hash = hash(tuple(sorted(task.queries)))
        return f"{task.search_type.value}_{task.deliverable_id}_{query_hash}"

    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """检查缓存是否有效"""
        if "timestamp" not in cache_entry:
            return False

        cache_age = time.time() - cache_entry["timestamp"]
        return cache_age < self.cache_ttl

    def _group_tasks_into_batches(self, tasks: List[SearchTask], execution_order: List[str]) -> List[List[SearchTask]]:
        """按依赖关系分批任务"""
        # 简化实现：按优先级分批
        batches = []
        task_dict = {task.task_id: task for task in tasks}

        # 按优先级排序
        sorted_tasks = sorted(tasks, key=lambda t: t.priority)

        # 分批（每批最多5个任务）
        batch_size = 5
        for i in range(0, len(sorted_tasks), batch_size):
            batch = sorted_tasks[i : i + batch_size]
            batches.append(batch)

        return batches

    def _identify_sharing_opportunities(self, results: List[SearchResult]) -> List[Dict[str, Any]]:
        """识别结果共享机会"""
        sharing_opportunities = []

        # 简单实现：高质量结果可以共享
        for result in results:
            if result.success and result.quality_score >= 75:
                sharing_opportunities.append(
                    {
                        "result_id": result.task_id,
                        "sharing_scope": "cross_deliverable",
                        "quality_score": result.quality_score,
                        "search_type": result.search_type,
                    }
                )

        return sharing_opportunities

    def _build_coordinated_result(
        self,
        master_plan: SearchMasterPlan,
        completed_results: List[SearchResult],
        distributed_results: Dict[str, Any],
        execution_time: float,
    ) -> CoordinatedSearchResult:
        """构建协调搜索结果"""
        successful_results = [r for r in completed_results if r.success]
        failed_results = [r for r in completed_results if not r.success]

        resource_usage = self._calculate_resource_usage(completed_results)

        return CoordinatedSearchResult(
            master_plan_id=master_plan.plan_id,
            total_tasks=len(master_plan.search_tasks),
            completed_tasks=len(successful_results),
            failed_tasks=len(failed_results),
            execution_time=execution_time,
            results_by_deliverable=dict(distributed_results["by_deliverable"]),
            results_by_type=dict(distributed_results["by_type"]),
            shared_results=distributed_results["shared_results"],
            resource_usage=resource_usage,
        )

        # 识别可共享的结果（高质量且通用）
        for result in search_results:
            if result.success and result.quality_score >= 0.7 and self._is_result_shareable(result):
                distributed["shared_results"].append(result)

        logger.info(f"📤 [SearchCoordinator] 结果分发完成，共享结果: {len(distributed['shared_results'])}个")
        return distributed

    def _is_result_shareable(self, result: SearchResult) -> bool:
        """判断结果是否可共享"""
        # 概念探索和学术研究结果通常可共享
        shareable_types = {
            SearchType.CONCEPT_EXPLORATION,
            SearchType.ACADEMIC_RESEARCH,
            SearchType.TREND_ANALYSIS,
        }

        return result.search_type in shareable_types

    def _build_coordinated_result(
        self,
        master_plan: SearchMasterPlan,
        completed_results: List[SearchResult],
        distributed_results: Dict[str, Any],
        execution_time: float,
    ) -> CoordinatedSearchResult:
        """构建协调搜索结果"""

        total_tasks = len(master_plan.search_tasks)
        completed_tasks = len([r for r in completed_results if r.success])
        failed_tasks = len([r for r in completed_results if not r.success])

        # 统计资源使用
        resource_usage = self._calculate_resource_usage(completed_results)

        return CoordinatedSearchResult(
            master_plan_id=master_plan.plan_id,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            execution_time=execution_time,
            results_by_deliverable=dict(distributed_results["by_deliverable"]),
            results_by_type=dict(distributed_results["by_type"]),
            shared_results=distributed_results["shared_results"],
            resource_usage=resource_usage,
        )

    # 辅助方法
    def _generate_task_signature(self, task: SearchTask) -> str:
        """生成任务签名用于去重"""
        queries_str = "|".join(sorted(task.queries))
        return f"{task.search_type.value}:{queries_str}:{task.deliverable_id}"

    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """检查缓存是否有效"""
        created_at = cache_entry.get("created_at", datetime.min)
        age = (datetime.now() - created_at).total_seconds()
        return age < self.cache_ttl

    def _calculate_query_similarity(self, query1: str, query2: str) -> float:
        """计算查询相似度"""
        # 简单的词汇重叠相似度
        words1 = set(query1.lower().split())
        words2 = set(query2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        return len(intersection) / len(union)

    def _group_tasks_into_batches(self, tasks: List[SearchTask], execution_order: List[str]) -> List[List[SearchTask]]:
        """按依赖关系分批任务"""
        task_map = {task.task_id: task for task in tasks}
        batches = []
        processed = set()

        # 按执行顺序分批
        current_batch = []

        for task_id in execution_order:
            if task_id in task_map:
                task = task_map[task_id]

                # 检查依赖是否已完成
                dependencies_ready = all(dep_id in processed for dep_id in task.dependencies)

                if dependencies_ready:
                    current_batch.append(task)
                    processed.add(task_id)
                else:
                    # 开始新批次
                    if current_batch:
                        batches.append(current_batch)
                        current_batch = []
                    current_batch.append(task)
                    processed.add(task_id)

        if current_batch:
            batches.append(current_batch)

        return batches

    def _update_shared_results_pool(self, batch_results: List[SearchResult]):
        """更新共享结果池"""
        for result in batch_results:
            if result.success and result.quality_score >= 0.7:
                self.shared_results_pool.append(result)

        # 限制池大小
        if len(self.shared_results_pool) > 100:
            # 按质量排序，保留最佳结果
            self.shared_results_pool.sort(key=lambda r: r.quality_score, reverse=True)
            self.shared_results_pool = self.shared_results_pool[:100]

    def _calculate_result_quality(self, search_result: Dict[str, Any]) -> float:
        """计算搜索结果质量分数"""
        if not search_result.get("success", False):
            return 0.0

        results = search_result.get("results", [])
        if not results:
            return 0.0

        # 基于结果数量和质量分数
        result_count_score = min(len(results) / 10.0, 1.0) * 20  # 最多20分

        # 基于平均质量分数
        quality_scores = [r.get("quality_score", 50.0) for r in results if "quality_score" in r]
        if quality_scores:
            avg_quality = sum(quality_scores) / len(quality_scores)
        else:
            avg_quality = 60.0  # 默认质量分数

        total_score = result_count_score + (avg_quality * 0.8)
        return min(total_score, 100.0)

    def _calculate_resource_usage(self, results: List[SearchResult]) -> Dict[str, Any]:
        """计算资源使用统计"""
        usage = {
            "total_searches": len(results),
            "successful_searches": len([r for r in results if r.success]),
            "total_execution_time": sum(r.execution_time for r in results),
            "tool_usage": defaultdict(int),
            "average_quality": 0.0,
        }

        # 统计工具使用
        for result in results:
            usage["tool_usage"][result.tool_used] += 1

        # 计算平均质量
        successful_results = [r for r in results if r.success]
        if successful_results:
            usage["average_quality"] = sum(r.quality_score for r in successful_results) / len(successful_results)

        return dict(usage)

    async def execute_search_plan(self, search_plan: SearchMasterPlan, max_parallel: int = 3) -> SearchExecutionReport:
        """
        执行搜索计划（SearchWorkflowIntegrator调用接口）

        Args:
            search_plan: 搜索计划
            max_parallel: 最大并发数

        Returns:
            搜索执行报告
        """
        logger.info(f"🎯 [SearchCoordinator] 开始执行搜索计划: {search_plan.plan_id}")

        start_time = time.time()

        # 执行协调搜索
        coordinated_result = await self.execute_coordinated_search(search_plan)

        # 转换为执行报告格式
        successful_results = []
        failed_results = []

        for deliverable_results in coordinated_result.results_by_deliverable.values():
            for result in deliverable_results:
                if result.success:
                    successful_results.append(result)
                else:
                    failed_results.append(result)

        # 估算API调用次数和成本
        total_api_calls = len(successful_results) + len(failed_results)
        total_cost = total_api_calls * 0.01  # 假设每次调用0.01美元

        execution_time = time.time() - start_time

        report = SearchExecutionReport(
            plan_id=search_plan.plan_id,
            successful_results=successful_results,
            failed_results=failed_results,
            total_api_calls=total_api_calls,
            total_cost=total_cost,
            execution_time=execution_time,
        )

        logger.info(f"✅ [SearchCoordinator] 搜索计划执行完成: {len(successful_results)}成功, {len(failed_results)}失败")

        return report


# 便捷函数
async def execute_search_coordination(master_plan: SearchMasterPlan) -> CoordinatedSearchResult:
    """执行搜索协调的便捷异步函数"""
    coordinator = SearchCoordinator()
    return await coordinator.execute_coordinated_search(master_plan)
