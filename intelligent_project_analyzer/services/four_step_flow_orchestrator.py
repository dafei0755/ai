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

# 导入子模块
from intelligent_project_analyzer.services._four_step_helpers import PromptLoader, clean_repetitive_content
from intelligent_project_analyzer.services._step1_deep_analysis import Step1DeepAnalysisExecutor
from intelligent_project_analyzer.services._step2_task_decomposition import Step2SearchTaskDecompositionExecutor
from intelligent_project_analyzer.services._step3_search_executor import Step3IntelligentSearchExecutor
from intelligent_project_analyzer.services._step4_summary import Step4SummaryGenerationExecutor


# ============================================================================
# 主编排器
# ============================================================================


class FourStepFlowOrchestrator:
    """4步骤流程编排器 (v2.0 - 支持 Step 1.5 搜索方向生成)"""

    def __init__(self):
        self.llm_factory = LLMFactory()
        self.step1_executor = Step1DeepAnalysisExecutor(self.llm_factory)
        self.step2_executor = Step2SearchTaskDecompositionExecutor(self.llm_factory)
        self.step3_executor = Step3IntelligentSearchExecutor(self.llm_factory)
        self.step4_executor = Step4SummaryGenerationExecutor(self.llm_factory)

        # v2.0: 新增 Step 1.5 搜索方向生成器
        try:
            step1_5_config = PromptLoader.load_prompt_config("step1_5_direction_generation.yaml")
            self.search_direction_generator = SearchDirectionGenerator(self.llm_factory, step1_5_config)
            logger.info(" Step 1.5 搜索方向生成器初始化成功")
        except Exception as e:
            logger.warning(f"️ Step 1.5 搜索方向生成器初始化失败: {e}，将跳过 Step 1.5")
            self.search_direction_generator = None

    async def execute_flow(
        self, user_input: str, config: SearchExecutionConfig | None = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行完整的4步骤流程

        Args:
            user_input: 用户输入
            config: 搜索执行配置

        Yields:
            SSE事件字典
        """
        logger.info(" 开始执行4步骤搜索流程...")

        # 初始化状态
        state = FourStepFlowState(config=config or SearchExecutionConfig())

        try:
            # ================================================================
            # Step 1: 深度分析
            # ================================================================
            yield {"event": "flow_step_start", "data": {"step": 1, "name": "深度分析"}}

            step1_result = None
            async for event in self.step1_executor.execute(user_input, stream=True):
                yield event
                if event["event"] == "step1_completed":
                    step1_result = event["data"]
                    state.step1_completed = True

            if not step1_result:
                raise Exception("Step 1未能完成")

            # 等待用户确认/编辑输出框架
            yield {
                "event": "flow_waiting_user_confirmation",
                "data": {
                    "step": 1,
                    "message": "请查看深度分析结果，确认或编辑输出框架",
                    "editable_data": step1_result["output_framework"],
                },
            }

            # TODO: 实际实现中需要等待用户输入
            # 这里假设用户直接确认

            # ================================================================
            # Step 1.5: 搜索方向生成 (v2.0 新增)
            # ================================================================
            search_directions = {}
            if self.search_direction_generator:
                logger.info(" [Step 1.5] 开始搜索方向生成...")
                yield {
                    "event": "flow_step_start",
                    "data": {"step": 1.5, "name": "搜索方向生成"},
                }

                # 重建OutputFramework对象
                output_framework = self._rebuild_output_framework(step1_result["output_framework"])
                logger.info(f" [Step 1.5] 输出框架包含 {len(output_framework.blocks)} 个板块")

                # 重建Understanding对象
                understanding = self._rebuild_understanding(step1_result.get("understanding", {}))
                logger.debug(" [Step 1.5] Understanding 重建完成")

                # 为每个板块生成搜索方向
                for i, block in enumerate(output_framework.blocks):
                    logger.info(f" [Step 1.5] 处理板块 {i+1}/{len(output_framework.blocks)}: {block.name[:30]}...")
                    try:
                        directions = await self.search_direction_generator.generate_directions(
                            block=block, understanding=understanding, block_index=i
                        )
                        search_directions[block.id] = directions

                        # 发送进度事件
                        yield {
                            "event": "step1_5_direction_generated",
                            "data": {
                                "block_id": block.id,
                                "block_name": block.name,
                                "directions": [self._direction_to_dict(d) for d in directions],
                                "progress": f"{i+1}/{len(output_framework.blocks)}",
                            },
                        }
                        logger.info(f" [Step 1.5] 板块 {block.id} 生成 {len(directions)} 个搜索方向")
                        for j, d in enumerate(directions):
                            logger.debug(f"   方向 {j+1}: {d.core_theme[:40]}...")
                    except Exception as e:
                        logger.error(f" [Step 1.5] 板块 {block.id} 搜索方向生成失败: {e}", exc_info=True)
                        # 继续处理其他板块

                total_directions = sum(len(dirs) for dirs in search_directions.values())
                yield {
                    "event": "step1_5_completed",
                    "data": {
                        "search_directions": {
                            block_id: [self._direction_to_dict(d) for d in dirs]
                            for block_id, dirs in search_directions.items()
                        },
                        "total_directions": total_directions,
                    },
                }
                state.step1_5_completed = True
                logger.info(f" [Step 1.5] 搜索方向生成完成 | 板块数: {len(search_directions)} | 方向总数: {total_directions}")
            else:
                # 如果没有搜索方向生成器，重建OutputFramework对象
                output_framework = self._rebuild_output_framework(step1_result["output_framework"])
                logger.warning("️ [Step 1.5] 跳过搜索方向生成（生成器未初始化）")

            # ================================================================
            # Step 2: 搜索任务分解
            # ================================================================
            logger.info(" [Step 2] 开始搜索任务分解...")
            logger.info(f" [Step 2] 搜索方向数量: {len(search_directions) if search_directions else 0}")
            yield {
                "event": "flow_step_start",
                "data": {"step": 2, "name": "搜索任务分解"},
            }

            # v2.0: 传递搜索方向给 Step 2
            step2_result = None
            async for event in self.step2_executor.execute(
                user_input,
                output_framework,
                search_directions=search_directions if search_directions else None,
                stream=True,
            ):
                yield event
                if event["event"] == "step2_completed":
                    step2_result = event["data"]
                    state.step2_completed = True
                    query_count = len(step2_result.get("search_queries", []))
                    logger.info(f" [Step 2] 搜索任务分解完成 | 查询数量: {query_count}")

            if not step2_result:
                raise Exception("Step 2未能完成")

            # 等待用户确认/编辑搜索查询
            yield {
                "event": "flow_waiting_user_confirmation",
                "data": {
                    "step": 2,
                    "message": "请查看搜索任务清单，确认或编辑查询",
                    "editable_data": step2_result["search_queries"],
                },
            }

            # TODO: 实际实现中需要等待用户输入
            # 这里假设用户直接确认

            # ================================================================
            # Step 3: 智能搜索执行
            # ================================================================
            yield {
                "event": "flow_step_start",
                "data": {"step": 3, "name": "智能搜索执行"},
            }

            # 重建SearchQuery对象列表
            search_queries = self._rebuild_search_queries(step2_result["search_queries"])

            step3_result = None
            async for event in self.step3_executor.execute(search_queries, output_framework, state.config, stream=True):
                yield event
                if event["event"] == "step3_completed":
                    step3_result = event["data"]
                    state.step3_completed = True

            if not step3_result:
                raise Exception("Step 3未能完成")

            # 如果有框架增补建议，等待用户确认
            if step3_result.get("framework_additions"):
                yield {
                    "event": "flow_waiting_user_confirmation",
                    "data": {
                        "step": 3,
                        "message": "发现新的重要方向，是否增补输出框架？",
                        "editable_data": step3_result["framework_additions"],
                    },
                }

                # TODO: 实际实现中需要等待用户输入
                # 这里假设用户接受增补

            # ================================================================
            # Step 4: 总结生成
            # ================================================================
            yield {"event": "flow_step_start", "data": {"step": 4, "name": "总结生成"}}

            # 重建FrameworkAddition对象列表
            framework_additions = self._rebuild_framework_additions(step3_result.get("framework_additions", []))

            step4_result = None
            async for event in self.step4_executor.execute(
                user_input,
                output_framework,
                step3_result["search_results"],
                framework_additions,
                stream=True,
            ):
                yield event
                if event["event"] == "step4_completed":
                    step4_result = event["data"]
                    state.step4_completed = True

            if not step4_result:
                raise Exception("Step 4未能完成")

            # ================================================================
            # 流程完成
            # ================================================================
            yield {
                "event": "flow_completed",
                "data": {
                    "message": "4步骤流程完成",
                    "summary": step4_result["summary_content"],
                    "metadata": step4_result.get("metadata", {}),
                },
            }

            logger.info(" 4步骤流程完成")

        except Exception as e:
            logger.error(f" 4步骤流程执行失败: {e}")
            yield {"event": "flow_error", "data": {"error": str(e)}}

    def _rebuild_output_framework(self, framework_data: Dict[str, Any]) -> OutputFramework:
        """从序列化数据重建OutputFramework对象"""
        blocks = []
        for block_data in framework_data.get("blocks", []):
            sub_items = [OutputBlockSubItem(**item) for item in block_data.get("sub_items", [])]
            blocks.append(
                OutputBlock(
                    id=block_data.get("id", ""),
                    name=block_data.get("name", ""),
                    estimated_length=block_data.get("estimated_length", ""),
                    sub_items=sub_items,
                )
            )

        return OutputFramework(
            core_objective=framework_data.get("core_objective", ""),
            deliverable_type=framework_data.get("deliverable_type", ""),
            blocks=blocks,
            quality_standards=framework_data.get("quality_standards", []),
        )

    def _rebuild_search_queries(self, queries_data: List[Dict[str, Any]]) -> List[SearchQuery]:
        """从序列化数据重建SearchQuery对象列表"""
        queries = []
        for query_data in queries_data:
            queries.append(
                SearchQuery(
                    id=query_data.get("id", ""),
                    query=query_data.get("query", ""),
                    serves_blocks=query_data.get("serves_blocks", []),
                    expected_output=query_data.get("expected_output", ""),
                    search_keywords=query_data.get("search_keywords", []),
                    success_criteria=query_data.get("success_criteria", ""),
                    priority=query_data.get("priority", 1),
                    dependencies=query_data.get("dependencies", []),
                    can_parallel_with=query_data.get("can_parallel_with", []),
                    status=query_data.get("status", "pending"),
                )
            )
        return queries

    def _rebuild_framework_additions(self, additions_data: List[Dict[str, Any]]) -> List[FrameworkAddition]:
        """从序列化数据重建FrameworkAddition对象列表"""
        additions = []
        for addition_data in additions_data:
            additions.append(
                FrameworkAddition(
                    block_name=addition_data.get("block_name", ""),
                    reason=addition_data.get("reason", ""),
                    importance=Priority(addition_data.get("importance", "medium")),
                    sub_items=addition_data.get("sub_items", []),
                    source=addition_data.get("source", ""),
                )
            )
        return additions

    def _rebuild_understanding(self, understanding_data: Dict[str, Any]) -> Understanding:
        """从序列化数据重建Understanding对象 (v2.0 新增)"""
        # 重建 L1 问题解构
        l1_data = understanding_data.get("l1_deconstruction", {})
        l1 = L1ProblemDeconstruction(
            user_identity=l1_data.get("user_identity", ""),
            explicit_needs=l1_data.get("explicit_needs", ""),
            implicit_motivations=l1_data.get("implicit_motivations", ""),
            key_constraints=l1_data.get("key_constraints", ""),
            analysis_perspective=l1_data.get("analysis_perspective", ""),
        )

        # 重建 L2 动机列表
        l2_motivations = []
        for m_data in understanding_data.get("l2_motivations", []):
            l2_motivations.append(
                L2MotivationDimension(
                    name=m_data.get("name", ""),
                    type=m_data.get("type", "功能型"),
                    score=m_data.get("score", 3),
                    reason=m_data.get("reason", ""),
                    evidence=m_data.get("evidence", []),
                    scenario_expression=m_data.get("scenario_expression", ""),
                )
            )

        # 重建 L3 核心张力
        l3_data = understanding_data.get("l3_tension", {})
        l3 = L3CoreTension(
            primary_motivation=l3_data.get("primary_motivation", ""),
            secondary_motivation=l3_data.get("secondary_motivation", ""),
            tension_formula=l3_data.get("tension_formula", ""),
            resolution_strategy=l3_data.get("resolution_strategy", ""),
            hidden_insights=l3_data.get("hidden_insights", []),
        )

        # 重建 L4 JTBD
        l4_data = understanding_data.get("l4_jtbd", {})
        l4 = L4JTBDDefinition(
            user_role=l4_data.get("user_role", ""),
            information_type=l4_data.get("information_type", ""),
            task_1=l4_data.get("task_1", ""),
            task_2=l4_data.get("task_2", ""),
            full_statement=l4_data.get("full_statement", ""),
        )

        # 重建 L5 锐度测试
        l5_data = understanding_data.get("l5_sharpness", {})
        l5 = L5SharpnessTest(
            specificity_score=l5_data.get("specificity_score", 5),
            specificity_reason=l5_data.get("specificity_reason", ""),
            specificity_evidence=l5_data.get("specificity_evidence", ""),
            actionability_score=l5_data.get("actionability_score", 5),
            actionability_reason=l5_data.get("actionability_reason", ""),
            actionability_evidence=l5_data.get("actionability_evidence", ""),
            depth_score=l5_data.get("depth_score", 5),
            depth_reason=l5_data.get("depth_reason", ""),
            depth_evidence=l5_data.get("depth_evidence", ""),
            searchability_score=l5_data.get("searchability_score", 5),
            searchability_reason=l5_data.get("searchability_reason", ""),
            searchability_evidence=l5_data.get("searchability_evidence", ""),
        )

        return Understanding(
            l1_deconstruction=l1,
            l2_motivations=l2_motivations,
            l3_tension=l3,
            l4_jtbd=l4,
            l5_sharpness=l5,
            comprehensive_summary=understanding_data.get("comprehensive_summary", ""),
        )

    def _direction_to_dict(self, direction: SearchDirection) -> Dict[str, Any]:
        """将SearchDirection对象转换为字典 (v2.0 新增)"""
        return {
            "id": direction.id,
            "block_id": direction.block_id,
            "core_theme": direction.core_theme,
            "search_scope": direction.search_scope,
            "expected_info_types": direction.expected_info_types,
            "key_dimensions": direction.key_dimensions,
            "user_characteristics": direction.user_characteristics,
            "expected_query_count": direction.expected_query_count,
            "priority": direction.priority,
            "metadata": direction.metadata,
        }


# ============================================================================
# 导出接口
# ============================================================================


def get_four_step_flow_orchestrator() -> FourStepFlowOrchestrator:
    """获取4步骤流程编排器实例"""
    return FourStepFlowOrchestrator()

__all__ = [
    "FourStepFlowOrchestrator",
    "get_four_step_flow_orchestrator",
    "PromptLoader",
    "Step1DeepAnalysisExecutor",
    "Step2SearchTaskDecompositionExecutor",
    "Step3IntelligentSearchExecutor",
    "Step4SummaryGenerationExecutor",
]
