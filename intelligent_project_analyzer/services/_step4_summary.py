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
# Step 4: 总结生成执行器
# ============================================================================


class Step4SummaryGenerationExecutor:
    """Step 4: 总结生成执行器"""

    def __init__(self, llm_factory: LLMFactory):
        self.llm_factory = llm_factory
        self.prompt_config = PromptLoader.load_prompt_config("step4_summary_generation.yaml")

    async def execute(
        self,
        user_input: str,
        output_framework: OutputFramework,
        search_results: Dict[str, List[Dict[str, Any]]],
        framework_additions: List[FrameworkAddition],
        stream: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行Step 4总结生成

        Args:
            user_input: 用户输入
            output_framework: 输出框架
            search_results: 搜索结果字典
            framework_additions: 框架增补建议
            stream: 是否流式输出

        Yields:
            SSE事件字典
        """
        logger.info(" [Step 4] 开始总结生成...")

        try:
            # 1. 构建prompt
            summary_prompt = self._build_summary_prompt(
                user_input, output_framework, search_results, framework_additions
            )

            # 2. 调用LLM生成总结
            llm = self.llm_factory.create_llm(temperature=0.7, max_tokens=6000)

            if stream:
                # 流式输出
                summary_content = ""
                async for chunk in self._stream_llm_response(llm, summary_prompt):
                    summary_content += chunk
                    yield {
                        "event": "step4_summary_chunk",
                        "data": {"chunk": chunk, "accumulated": summary_content},
                    }

                # 3. 提取结构化元数据
                yield {"event": "step4_extracting_metadata", "data": {}}
                metadata = await self._extract_summary_metadata(summary_content)

                yield {
                    "event": "step4_completed",
                    "data": {"summary_content": summary_content, "metadata": metadata},
                }

                logger.info(" [Step 4] 总结生成完成")

            else:
                # 非流式输出
                summary_content = await self._generate_llm_response(llm, summary_prompt)
                metadata = await self._extract_summary_metadata(summary_content)

                yield {
                    "event": "step4_completed",
                    "data": {"summary_content": summary_content, "metadata": metadata},
                }

        except Exception as e:
            logger.error(f" [Step 4] 总结生成失败: {e}")
            yield {"event": "step4_error", "data": {"error": str(e)}}

    def _build_summary_prompt(
        self,
        user_input: str,
        output_framework: OutputFramework,
        search_results: Dict[str, List[Dict[str, Any]]],
        framework_additions: List[FrameworkAddition],
    ) -> str:
        """构建总结生成prompt"""
        template = self.prompt_config.get("summary_generation_prompt_template", "")

        # 格式化输出框架
        framework_str = self._format_output_framework(output_framework)

        # 格式化搜索结果
        results_str = self._format_search_results(search_results)

        # 格式化框架增补
        additions_str = self._format_framework_additions(framework_additions)

        datetime_info = f"当前日期: {datetime.now().strftime('%Y年%m月%d日')}"

        prompt = template.format(
            datetime_info=datetime_info,
            user_input=user_input,
            output_framework=framework_str,
            result_count=sum(len(results) for results in search_results.values()),
            search_results=results_str,
            framework_additions=additions_str,
        )
        return prompt

    def _format_output_framework(self, framework: OutputFramework) -> str:
        """格式化输出框架"""
        lines = []
        lines.append(f"**核心目标**: {framework.core_objective}")
        lines.append(f"**交付物类型**: {framework.deliverable_type}")
        lines.append("\n**板块结构**:")
        for block in framework.blocks:
            lines.append(f"\n{block.name} ({block.estimated_length})")
            for item in block.sub_items:
                lines.append(f"  - {item.name}: {item.description}")
        return "\n".join(lines)

    def _format_search_results(self, search_results: Dict[str, List[Dict[str, Any]]]) -> str:
        """格式化搜索结果"""
        lines = []
        source_num = 1
        for _query_id, results in search_results.items():
            for result in results[:5]:  # 每个查询最多5条
                lines.append(
                    f"[{source_num}] {result.get('title', '')}\n"
                    f"    URL: {result.get('url', '')}\n"
                    f"    摘要: {result.get('snippet', '')[:300]}..."
                )
                source_num += 1
        return "\n\n".join(lines)

    def _format_framework_additions(self, additions: List[FrameworkAddition]) -> str:
        """格式化框架增补"""
        if not additions:
            return "无"

        lines = []
        for addition in additions:
            lines.append(f"**{addition.block_name}** ({addition.importance.value})")
            lines.append(f"原因: {addition.reason}")
            lines.append("建议子项:")
            for item in addition.sub_items:
                lines.append(f"  - {item}")
        return "\n\n".join(lines)

    async def _stream_llm_response(self, llm, prompt: str) -> AsyncGenerator[str, None]:
        """流式调用LLM"""
        try:
            async for chunk in llm.astream(prompt):
                if hasattr(chunk, "content"):
                    yield chunk.content
        except Exception as e:
            logger.error(f" LLM流式调用失败: {e}")
            raise

    async def _generate_llm_response(self, llm, prompt: str) -> str:
        """非流式调用LLM"""
        try:
            response = await llm.ainvoke(prompt)
            return response.content
        except Exception as e:
            logger.error(f" LLM调用失败: {e}")
            raise

    async def _extract_summary_metadata(self, summary_content: str) -> Dict[str, Any]:
        """提取总结的元数据"""
        # TODO: 实现元数据提取
        return {
            "total_words": len(summary_content),
            "generation_time": datetime.now().isoformat(),
        }


__all__ = ["Step4SummaryGenerationExecutor"]
