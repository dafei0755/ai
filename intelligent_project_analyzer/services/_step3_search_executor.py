"""
4步骤搜索流程编排服务 (v1.0)

实现智能、开放、不硬编码的4步骤搜索流程：
- Step 1: 深度分析 - 动态生成输出框架
- Step 2: 搜索任务分解 - 将框架转化为具体查询
- Step 3: 智能搜索执行 - 动态增补查询
- Step 4: 总结生成 - 灵活的内容驱动输出

核心原则：
1. 智能、开放、不硬编码
2. 职责分离
3. 自适应搜索
4. 用户控制

Author: AI Assistant
Created: 2026-02-01
Version: 1.0
"""

import json
import os
import re
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Tuple

import yaml
from loguru import logger

# 导入数据结构
from intelligent_project_analyzer.core.four_step_flow_types import (
    DeepAnalysisResult,
    Discovery,
    ExecutionAdvice,
    ExecutionStrategy,
    FourStepFlowState,
    FrameworkAddition,
    HumanDimensions,
    L1ProblemDeconstruction,
    L2MotivationDimension,
    L3CoreTension,
    L4JTBDDefinition,
    L5SharpnessTest,
    OutputBlock,
    OutputBlockSubItem,
    OutputFramework,
    Priority,
    QualityAssessment,
    SearchDirection,  # Step 1.5 新增
    SearchExecutionConfig,
    SearchQuery,
    SearchResultAnalysis,
    SearchTaskList,
    SupplementaryQuery,
    TriggerType,
    Understanding,
    ValidationCheck,
    ValidationReport,
)

# 导入LLM工厂
from intelligent_project_analyzer.services.llm_factory import LLMFactory

# 导入搜索方向生成器 (Step 1.5)
from intelligent_project_analyzer.services.search_direction_generator import (
    SearchDirectionGenerator,
)

# 导入搜索服务
try:
    from intelligent_project_analyzer.services.bocha_ai_search import (
        get_ai_search_service,
    )

    SEARCH_SERVICE_AVAILABLE = True
except ImportError:
    SEARCH_SERVICE_AVAILABLE = False
    logger.warning("️ 搜索服务未可用")

from intelligent_project_analyzer.services._four_step_helpers import PromptLoader


# ============================================================================
# Step 3: 智能搜索执行器
# ============================================================================


class Step3IntelligentSearchExecutor:
    """Step 3: 智能搜索执行器（含动态增补）"""

    def __init__(self, llm_factory: LLMFactory, search_service=None):
        self.llm_factory = llm_factory
        self.search_service = search_service or (get_ai_search_service() if SEARCH_SERVICE_AVAILABLE else None)
        self.prompt_config = PromptLoader.load_prompt_config("step3_search_result_analysis.yaml")

    async def execute(
        self,
        search_queries: List[SearchQuery],
        output_framework: OutputFramework,
        config: SearchExecutionConfig,
        stream: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行Step 3智能搜索

        Args:
            search_queries: 搜索查询列表
            output_framework: 输出框架
            config: 搜索执行配置
            stream: 是否流式输出

        Yields:
            SSE事件字典
        """
        logger.info(f" [Step 3] 开始智能搜索执行，共{len(search_queries)}个查询...")

        if not self.search_service:
            logger.error(" 搜索服务不可用")
            yield {"event": "step3_error", "data": {"error": "搜索服务不可用"}}
            return

        try:
            all_queries = search_queries.copy()
            executed_queries = []
            supplementary_queries = []
            framework_additions = []
            search_results = {}

            query_count = 0
            total_queries = len(all_queries)

            # 按优先级执行查询
            while all_queries and query_count < config.max_total_queries_multiplier * total_queries:
                current_query = all_queries.pop(0)
                query_count += 1

                # 发送搜索开始事件
                yield {
                    "event": "step3_query_start",
                    "data": {
                        "query_id": current_query.id,
                        "query": current_query.query,
                        "progress": f"{query_count}/{total_queries}",
                    },
                }

                # 执行搜索
                results = await self._execute_single_query(current_query)
                search_results[current_query.id] = results
                executed_queries.append(current_query.id)

                # 发送搜索结果事件
                yield {
                    "event": "step3_query_completed",
                    "data": {
                        "query_id": current_query.id,
                        "result_count": len(results),
                        "results": self._serialize_search_results(results[:5]),  # 只发送前5条
                    },
                }

                # 分析搜索结果，生成补充查询
                if config.enable_dynamic_supplementary:
                    analysis = await self._analyze_search_results(
                        current_query, results, output_framework, executed_queries
                    )

                    if analysis.supplementary_queries:
                        # 过滤和添加补充查询
                        for supp_query in analysis.supplementary_queries:
                            if self._should_execute_supplementary(supp_query, config):
                                # 转换为SearchQuery
                                search_query = SearchQuery(
                                    id=supp_query.id,
                                    query=supp_query.query,
                                    serves_blocks=supp_query.serves_blocks,
                                    expected_output=supp_query.expected_output,
                                    search_keywords=supp_query.search_keywords,
                                    success_criteria=supp_query.success_criteria,
                                    priority=(1 if supp_query.priority == Priority.HIGH else 2),
                                    dependencies=[],
                                    can_parallel_with=[],
                                    status="pending",
                                )
                                all_queries.append(search_query)
                                supplementary_queries.append(supp_query)

                                # 发送补充查询事件
                                yield {
                                    "event": "step3_supplementary_added",
                                    "data": {
                                        "parent_query_id": current_query.id,
                                        "supplementary_query": {
                                            "id": supp_query.id,
                                            "query": supp_query.query,
                                            "reason": supp_query.reason,
                                            "priority": supp_query.priority.value,
                                        },
                                    },
                                }

                    # 收集框架增补建议
                    if config.enable_framework_additions and analysis.framework_additions:
                        framework_additions.extend(analysis.framework_additions)

                # 检查是否超时
                if query_count >= config.max_total_queries_multiplier * total_queries:
                    logger.warning("️ 达到最大查询数限制")
                    break

            # 发送搜索完成事件
            yield {
                "event": "step3_completed",
                "data": {
                    "total_queries": query_count,
                    "original_queries": total_queries,
                    "supplementary_queries": len(supplementary_queries),
                    "framework_additions": [
                        {
                            "block_name": fa.block_name,
                            "reason": fa.reason,
                            "importance": fa.importance.value,
                            "sub_items": fa.sub_items,
                        }
                        for fa in framework_additions
                    ],
                    "search_results": {
                        query_id: self._serialize_search_results(results)
                        for query_id, results in search_results.items()
                    },
                },
            }

            logger.info(f" [Step 3] 智能搜索完成，共执行{query_count}个查询")

        except Exception as e:
            logger.error(f" [Step 3] 智能搜索失败: {e}")
            yield {"event": "step3_error", "data": {"error": str(e)}}

    async def _execute_single_query(self, query: SearchQuery) -> List[Dict[str, Any]]:
        """执行单个搜索查询"""
        try:
            # 使用搜索服务执行查询
            search_result = await self.search_service.search(query.query)

            # 转换为统一格式
            results = []
            if hasattr(search_result, "sources"):
                for source in search_result.sources[:20]:  # 最多返回20条
                    results.append(
                        {
                            "title": source.title,
                            "url": source.url,
                            "snippet": source.snippet,
                            "site_name": source.site_name,
                            "date_published": source.date_published,
                        }
                    )

            return results
        except Exception as e:
            logger.error(f" 搜索查询失败 {query.id}: {e}")
            return []

    async def _analyze_search_results(
        self,
        current_query: SearchQuery,
        results: List[Dict[str, Any]],
        output_framework: OutputFramework,
        executed_queries: List[str],
    ) -> SearchResultAnalysis:
        """分析搜索结果，生成补充查询"""
        try:
            # 构建分析prompt
            analysis_prompt = self._build_result_analysis_prompt(
                current_query, results, output_framework, executed_queries
            )

            # 调用LLM分析
            llm = self.llm_factory.create_llm(temperature=0.5, max_tokens=2000)
            response = await llm.ainvoke(analysis_prompt)
            analysis_content = response.content

            # 提取结构化数据
            structured_data = await self._extract_analysis_structured_data(analysis_content)

            # 解析为SearchResultAnalysis
            return self._parse_search_result_analysis(current_query.id, structured_data)

        except Exception as e:
            logger.error(f" 搜索结果分析失败: {e}")
            # 返回空分析
            return SearchResultAnalysis(
                current_query_id=current_query.id,
                quality_assessment=QualityAssessment(
                    score=50,
                    completeness="medium",
                    relevance="medium",
                    authority="medium",
                    timeliness="medium",
                    actionability="medium",
                ),
                should_execute=False,
            )

    def _build_result_analysis_prompt(
        self,
        current_query: SearchQuery,
        results: List[Dict[str, Any]],
        output_framework: OutputFramework,
        executed_queries: List[str],
    ) -> str:
        """构建搜索结果分析prompt"""
        template = self.prompt_config.get("result_analysis_prompt_template", "")

        # 格式化搜索结果
        results_str = "\n".join(
            [
                f"{i+1}. {r['title']}\n   URL: {r['url']}\n   摘要: {r['snippet'][:200]}..."
                for i, r in enumerate(results[:10])
            ]
        )

        # 格式化输出框架
        framework_str = self._format_output_framework(output_framework)

        # 格式化已执行查询
        executed_str = ", ".join(executed_queries)

        datetime_info = f"当前日期: {datetime.now().strftime('%Y年%m月%d日')}"

        prompt = template.format(
            datetime_info=datetime_info,
            current_query=current_query.query,
            result_count=len(results),
            search_results=results_str,
            output_framework=framework_str,
            executed_queries=executed_str,
        )
        return prompt

    def _format_output_framework(self, framework: OutputFramework) -> str:
        """格式化输出框架为文本"""
        lines = []
        for block in framework.blocks:
            lines.append(f"- {block.name}")
        return "\n".join(lines)

    async def _extract_analysis_structured_data(self, analysis_content: str) -> Dict[str, Any]:
        """提取分析的结构化数据"""
        json_prompt_template = self.prompt_config.get("json_extraction_prompt_template", "")

        datetime_info = f"当前日期: {datetime.now().strftime('%Y年%m月%d日')}"
        json_prompt = json_prompt_template.format(datetime_info=datetime_info, analysis_content=analysis_content)

        llm = self.llm_factory.create_llm(temperature=0.3, max_tokens=2000)
        response = await llm.ainvoke(json_prompt)

        # 解析JSON
        try:
            json_match = re.search(r"```json\s*(.*?)\s*```", response.content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_str = response.content

            structured_data = json.loads(json_str)
            return structured_data
        except json.JSONDecodeError as e:
            logger.error(f" JSON解析失败: {e}")
            return {}

    def _parse_search_result_analysis(self, query_id: str, structured_data: Dict[str, Any]) -> SearchResultAnalysis:
        """解析为SearchResultAnalysis对象"""
        # 解析quality_assessment
        qa_data = structured_data.get("quality_assessment", {})
        quality_assessment = QualityAssessment(
            score=qa_data.get("score", 50),
            completeness=qa_data.get("completeness", "medium"),
            relevance=qa_data.get("relevance", "medium"),
            authority=qa_data.get("authority", "medium"),
            timeliness=qa_data.get("timeliness", "medium"),
            actionability=qa_data.get("actionability", "medium"),
            issues=qa_data.get("issues", []),
        )

        # 解析discoveries
        discoveries = []
        for disc_data in structured_data.get("discoveries", []):
            discoveries.append(
                Discovery(
                    type=TriggerType(disc_data.get("type", "insufficient_info")),
                    description=disc_data.get("description", ""),
                    importance=Priority(disc_data.get("importance", "medium")),
                )
            )

        # 解析supplementary_queries
        supp_queries = []
        for sq_data in structured_data.get("supplementary_queries", []):
            supp_queries.append(
                SupplementaryQuery(
                    id=sq_data.get("id", ""),
                    query=sq_data.get("query", ""),
                    reason=sq_data.get("reason", ""),
                    trigger_type=TriggerType(sq_data.get("trigger_type", "insufficient_info")),
                    priority=Priority(sq_data.get("priority", "medium")),
                    serves_blocks=sq_data.get("serves_blocks", []),
                    expected_output=sq_data.get("expected_output", ""),
                    search_keywords=sq_data.get("search_keywords", []),
                    success_criteria=sq_data.get("success_criteria", ""),
                    parent_query_id=query_id,
                )
            )

        # 解析framework_additions
        additions = []
        for fa_data in structured_data.get("framework_additions", []):
            additions.append(
                FrameworkAddition(
                    block_name=fa_data.get("block_name", ""),
                    reason=fa_data.get("reason", ""),
                    importance=Priority(fa_data.get("importance", "medium")),
                    sub_items=fa_data.get("sub_items", []),
                    source=fa_data.get("source", ""),
                )
            )

        # 解析execution_advice
        advice_data = structured_data.get("execution_advice", {})

        return SearchResultAnalysis(
            current_query_id=query_id,
            quality_assessment=quality_assessment,
            discoveries=discoveries,
            supplementary_queries=supp_queries,
            framework_additions=additions,
            should_execute=advice_data.get("should_execute", True),
            execution_order=advice_data.get("execution_order", []),
            expected_value=advice_data.get("expected_value", ""),
        )

    def _should_execute_supplementary(self, supp_query: SupplementaryQuery, config: SearchExecutionConfig) -> bool:
        """判断是否应该执行补充查询"""
        # 检查优先级
        if supp_query.priority.value not in config.auto_execute_priority:
            return False

        # TODO: 检查相似度（避免重复）

        return True

    def _serialize_search_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """序列化搜索结果"""
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("snippet", "")[:200],
                "site_name": r.get("site_name", ""),
            }
            for r in results
        ]


__all__ = ["Step3IntelligentSearchExecutor"]
