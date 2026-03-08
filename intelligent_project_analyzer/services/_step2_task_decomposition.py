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
# Step 2: 搜索任务分解执行器
# ============================================================================


class Step2SearchTaskDecompositionExecutor:
    """Step 2: 搜索任务分解执行器 (v2.0 - 支持搜索方向)"""

    def __init__(self, llm_factory: LLMFactory):
        self.llm_factory = llm_factory
        self.prompt_config = PromptLoader.load_prompt_config("step2_search_task_decomposition.yaml")

    async def execute(
        self,
        user_input: str,
        output_framework: OutputFramework,
        search_directions: Dict[str, List[SearchDirection]] | None = None,  # v2.0 新增
        stream: bool = True,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        执行Step 2搜索任务分解

        Args:
            user_input: 用户输入
            output_framework: Step 1的输出框架
            search_directions: Step 1.5的搜索方向 (block_id -> directions)
            stream: 是否流式输出

        Yields:
            SSE事件字典
        """
        logger.info(" [Step 2] 开始搜索任务分解...")

        try:
            # 1. 构建prompt
            task_prompt = self._build_task_decomposition_prompt(user_input, output_framework, search_directions)

            # 2. 调用LLM生成任务清单
            # v7.421: 提升参数以强化初始生成质量
            # - temperature 0.5 → 0.7: 提升创造性，生成更丰富的任务
            # - max_tokens 3000 → 5000: 确保充分输出（5个板块×8个任务需要更多token）
            llm = self.llm_factory.create_llm(temperature=0.7, max_tokens=5000)

            if stream:
                # 流式输出
                task_list_content = ""
                async for chunk in self._stream_llm_response(llm, task_prompt):
                    task_list_content += chunk
                    yield {
                        "event": "step2_task_list_chunk",
                        "data": {"chunk": chunk, "accumulated": task_list_content},
                    }

                # 3. 提取结构化数据
                yield {"event": "step2_extracting_structure", "data": {}}
                structured_data = await self._extract_structured_data(user_input, task_list_content)

                # 4. 解析为SearchTaskList
                result = self._parse_search_task_list(task_list_content, structured_data)

                #  v7.420: 验证并补充搜索任务
                yield {"event": "step2_validating_queries", "data": {"message": "正在验证搜索任务数量..."}}
                validated_queries = await self._validate_and_supplement_queries(
                    queries=result.search_queries,
                    output_framework=output_framework,
                    user_input=user_input,
                )

                # 更新结果
                result.search_queries = validated_queries

                yield {
                    "event": "step2_completed",
                    "data": {
                        "task_list_content": task_list_content,
                        "search_queries": self._serialize_search_queries(result.search_queries),
                        "execution_strategy": self._serialize_execution_strategy(result.execution_strategy),
                        "execution_advice": self._serialize_execution_advice(result.execution_advice),
                    },
                }

                logger.info(f" [Step 2] 搜索任务分解完成，共{len(result.search_queries)}个查询")

            else:
                # 非流式输出
                task_list_content = await self._generate_llm_response(llm, task_prompt)
                structured_data = await self._extract_structured_data(user_input, task_list_content)
                result = self._parse_search_task_list(task_list_content, structured_data)

                #  v7.420: 验证并补充搜索任务
                validated_queries = await self._validate_and_supplement_queries(
                    queries=result.search_queries,
                    output_framework=output_framework,
                    user_input=user_input,
                )

                # 更新结果
                result.search_queries = validated_queries

                yield {
                    "event": "step2_completed",
                    "data": {
                        "task_list_content": task_list_content,
                        "search_queries": self._serialize_search_queries(result.search_queries),
                        "execution_strategy": self._serialize_execution_strategy(result.execution_strategy),
                        "execution_advice": self._serialize_execution_advice(result.execution_advice),
                    },
                }

        except Exception as e:
            import traceback

            logger.error(f" [Step 2] 搜索任务分解失败: {e}")
            logger.error(f"完整异常信息:\n{traceback.format_exc()}")
            yield {"event": "step2_error", "data": {"error": str(e)}}

    def _build_task_decomposition_prompt(
        self,
        user_input: str,
        output_framework: OutputFramework,
        search_directions: Dict[str, List[SearchDirection]] | None = None,
        understanding: Understanding | None = None,  # v2.0 新增
    ) -> str:
        """构建任务分解prompt (v2.0 - 支持搜索方向和 L2/L3 分析结果)"""
        template = self.prompt_config.get("task_decomposition_prompt_template", "")

        # 序列化output_framework
        framework_str = self._format_output_framework(output_framework)

        # v2.0: 序列化search_directions
        directions_str = ""
        if search_directions:
            directions_str = self._format_search_directions(search_directions)

        # v2.0 新增：格式化 L2/L3/人性维度分析结果
        l2_motivations_summary = ""
        l3_tension_summary = ""
        human_dimensions_summary = ""

        if understanding:
            l2_motivations_summary = self._format_l2_motivations_for_step2(understanding)
            l3_tension_summary = self._format_l3_tension_for_step2(understanding)
            human_dimensions_summary = self._format_human_dimensions_for_step2(understanding)

        datetime_info = f"当前日期: {datetime.now().strftime('%Y年%m月%d日')}"

        prompt = template.format(
            datetime_info=datetime_info,
            user_input=user_input,
            output_framework=framework_str,
            search_directions=directions_str,
            l2_motivations_summary=l2_motivations_summary,  # v2.0 新增
            l3_tension_summary=l3_tension_summary,  # v2.0 新增
            human_dimensions_summary=human_dimensions_summary,  # v2.0 新增
        )
        return prompt

    def _format_l2_motivations_for_step2(self, understanding: Understanding) -> str:
        """格式化 L2 动机分析结果供 Step 2 使用（v2.0 新增）"""
        if not understanding or not understanding.l2_motivations:
            return "**L2 动机分析**: 未提供"

        lines = []
        lines.append("**L2 动机分析（用于智能维度选择）**:")
        lines.append("")

        # 按类型分组
        motivation_by_type = {}
        for m in understanding.l2_motivations:
            if m.type not in motivation_by_type:
                motivation_by_type[m.type] = []
            motivation_by_type[m.type].append(m)

        for mot_type, motivations in motivation_by_type.items():
            lines.append(f"**{mot_type}动机**:")
            for m in motivations:
                lines.append(f"  - {m.name}（得分{m.score}）: {m.scenario_expression}")
        lines.append("")

        # 维度选择建议
        lines.append("**基于动机的维度选择建议**:")
        if any(m.type == "精神型" for m in understanding.l2_motivations):
            lines.append("  - 精神型动机 → 【美学溯源】【时代对话】")
        if any(m.type == "情感型" for m in understanding.l2_motivations):
            lines.append("  - 情感型动机 → 【情感锚点】【生活仪式】")
        if any(m.type == "社会型" for m in understanding.l2_motivations):
            lines.append("  - 社会型动机 → 【空间叙事】")
        if any(m.type == "功能型" for m in understanding.l2_motivations):
            lines.append("  - 功能型动机 → 【材质肌理】")

        return "\n".join(lines)

    def _format_l3_tension_for_step2(self, understanding: Understanding) -> str:
        """格式化 L3 核心张力供 Step 2 使用（v2.0 新增）"""
        if not understanding or not understanding.l3_tension:
            return "**L3 核心张力**: 未提供"

        tension = understanding.l3_tension
        lines = []
        lines.append("**L3 核心张力（用于智能维度选择）**:")
        lines.append(f"  - 主导动机: {tension.primary_motivation}")
        lines.append(f"  - 次要动机: {tension.secondary_motivation}")
        lines.append(f"  - 张力公式: {tension.tension_formula}")
        lines.append(f"  - 解决策略: {tension.resolution_strategy}")
        lines.append("")

        # 维度选择建议
        lines.append("**基于张力的维度选择建议**:")
        if "vs" in tension.tension_formula:
            lines.append("  - 对立型张力（vs）→ 【时代对话】研究如何融合对立")
        if "+" in tension.tension_formula:
            lines.append("  - 融合型张力（+）→ 【在地融合】研究如何协同")

        # 隐性洞察
        if tension.hidden_insights:
            lines.append("")
            lines.append("**隐性需求洞察**:")
            for insight in tension.hidden_insights:
                lines.append(f"  - {insight}")

        return "\n".join(lines)

    def _format_human_dimensions_for_step2(self, understanding: Understanding) -> str:
        """格式化人性维度供 Step 2 使用（v2.0 新增）"""
        if not understanding or not understanding.human_dimensions:
            return "**人性维度**: 未启用"

        hd = understanding.human_dimensions
        if not hd.enabled:
            return "**人性维度**: 未启用"

        lines = []
        lines.append("**人性维度分析（用于智能维度选择）**:")
        lines.append("")

        if hd.emotional_landscape:
            lines.append(f"  - 情绪地图: {hd.emotional_landscape}")
        if hd.spiritual_aspirations:
            lines.append(f"  - 精神追求: {hd.spiritual_aspirations}")
        if hd.psychological_safety_needs:
            lines.append(f"  - 心理安全需求: {hd.psychological_safety_needs}")
        if hd.ritual_behaviors:
            lines.append(f"  - 仪式行为: {hd.ritual_behaviors}")
        if hd.memory_anchors:
            lines.append(f"  - 记忆锚点: {hd.memory_anchors}")

        lines.append("")
        lines.append("**基于人性维度的维度选择建议**:")
        if hd.memory_anchors:
            lines.append("  - memory_anchors 非空 → 【情感锚点】")
        if hd.ritual_behaviors:
            lines.append("  - ritual_behaviors 非空 → 【生活仪式】")
        if hd.emotional_landscape:
            lines.append("  - emotional_landscape 非空 → 【光影氛围】")

        return "\n".join(lines)

    def _format_search_directions(self, search_directions: Dict[str, List[SearchDirection]]) -> str:
        """格式化搜索方向为文本 (v2.0 新增)"""
        if not search_directions:
            return ""

        lines = []
        lines.append("## Step 1.5 搜索方向")
        lines.append("")

        for block_id, directions in search_directions.items():
            if not directions:
                continue

            lines.append(f"### 板块 {block_id}")
            for i, direction in enumerate(directions, 1):
                lines.append(f"\n**方向 {i}: {direction.core_theme}**")
                lines.append(f"- **搜索范围**: {direction.search_scope}")
                lines.append(f"- **预期信息类型**: {', '.join(direction.expected_info_types)}")
                lines.append(f"- **关键维度**: {', '.join(direction.key_dimensions)}")
                lines.append(f"- **预期查询数**: {direction.expected_query_count}个")
                lines.append(f"- **用户特征**: {', '.join(direction.user_characteristics)}")
            lines.append("")

        return "\n".join(lines)

    def _format_output_framework(self, framework: OutputFramework) -> str:
        """格式化输出框架为文本 (v2.0: 移除硬编码数量约束，改为智能提示)"""
        lines = []
        lines.append(f"**核心目标**: {framework.core_objective}")
        lines.append(f"**最终交付物类型**: {framework.deliverable_type}")
        lines.append("")
        lines.append("**输出结构**:")
        lines.append("")
        # v7.360: 先列出所有板块ID，方便LLM正确填写serves_blocks
        lines.append("**板块ID列表** (用于serves_blocks字段):")
        for block in framework.blocks:
            lines.append(f"  - {block.id}: {block.name} ({len(block.sub_items)}个子项)")
        lines.append("")

        # v2.0: 移除硬编码数量约束，改为智能提示
        block_count = len(framework.blocks)
        lines.append("=" * 60)
        lines.append("** 设计思维驱动的搜索任务生成**")
        lines.append(f"  - 板块数量: {block_count} 个")
        lines.append("  - 任务数量: 基于 L2 动机和 L3 张力智能确定")
        lines.append("  - 维度选择: 参考上方的 L2/L3/人性维度分析结果")
        lines.append("  - **核心原则**: 每个选定维度生成 1-2 个搜索任务")
        lines.append("=" * 60)
        lines.append("")

        # 详细板块信息
        for block in framework.blocks:
            lines.append(f"\n**板块 {block.id}: {block.name}** ({block.estimated_length})")
            lines.append("  根据 L2 动机和板块主题智能选择搜索维度")
            lines.append("  子项列表（参考，但搜索任务要更详细）：")
            for item in block.sub_items:
                lines.append(f"  - {item.id} {item.name}: {item.description}")

        return "\n".join(lines)

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

    async def _extract_structured_data(self, user_input: str, task_list_content: str) -> Dict[str, Any]:
        """提取结构化数据（JSON）"""
        json_prompt_template = self.prompt_config.get("json_extraction_prompt_template", "")

        datetime_info = f"当前日期: {datetime.now().strftime('%Y年%m月%d日')}"
        json_prompt = json_prompt_template.format(
            datetime_info=datetime_info,
            user_input=user_input,
            task_list_content=task_list_content,
        )

        llm = self.llm_factory.create_llm(temperature=0.3, max_tokens=4000)
        response = await self._generate_llm_response(llm, json_prompt)

        # 解析JSON（v7.333.3 增强健壮性）
        try:
            # 尝试提取 ```json ... ``` 代码块
            json_match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试提取 ``` ... ``` 代码块
                json_match = re.search(r"```\s*(.*?)\s*```", response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # 尝试直接匹配 { ... } JSON 对象
                    json_match = re.search(r"\{[\s\S]*\}", response)
                    if json_match:
                        json_str = json_match.group(0)
                    else:
                        json_str = response

            # 清理常见问题
            json_str = json_str.strip()
            # 移除可能的 BOM 或其他不可见字符
            json_str = json_str.lstrip("\ufeff")

            structured_data = json.loads(json_str)
            logger.info(f" [Step 2] JSON 解析成功，提取到 {len(structured_data.get('search_queries', []))} 个查询")
            return structured_data
        except json.JSONDecodeError as e:
            logger.error(f" [Step 2] JSON解析失败: {e}")
            logger.debug(f"原始响应前200字符: {response[:200]}")

            # v7.333.4: 返回空结构而非抛出异常，让流程继续
            logger.warning("️ [Step 2] 使用空结构继续，后续将从 task_list_content 解析")
            return {
                "search_queries": [],
                "execution_strategy": {},
                "execution_advice": {},
            }
        except Exception as e:
            import traceback

            logger.error(f" [Step 2] JSON提取/解析时发生意外错误: {e}")
            logger.error(f"完整异常信息:\n{traceback.format_exc()}")
            # 返回空结构继续流程
            return {
                "search_queries": [],
                "execution_strategy": {},
                "execution_advice": {},
            }

    def _parse_search_task_list(self, task_list_content: str, structured_data: Dict[str, Any]) -> SearchTaskList:
        """解析为SearchTaskList对象"""
        # 解析search_queries
        queries = []
        for query_data in structured_data.get("search_queries", []):
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
                    status="pending",
                )
            )

        # 解析execution_strategy
        strategy_data = structured_data.get("execution_strategy", {})
        execution_strategy = ExecutionStrategy(
            priority_1_queries=strategy_data.get("priority_1_queries", []),
            priority_2_queries=strategy_data.get("priority_2_queries", []),
            priority_3_queries=strategy_data.get("priority_3_queries", []),
            parallel_groups=strategy_data.get("parallel_groups", []),
        )

        # 解析execution_advice
        advice_data = structured_data.get("execution_advice", {})
        execution_advice = ExecutionAdvice(
            overall_strategy=advice_data.get("overall_strategy", ""),
            key_success_factors=advice_data.get("key_success_factors", ""),
            risk_alerts=advice_data.get("risk_alerts", ""),
        )

        return SearchTaskList(
            search_queries=queries,
            execution_strategy=execution_strategy,
            execution_advice=execution_advice,
            metadata=structured_data.get("metadata", {}),
        )

    async def _validate_and_supplement_queries(
        self,
        queries: List[SearchQuery],
        output_framework: OutputFramework,
        user_input: str,
    ) -> List[SearchQuery]:
        """
        验证搜索任务数量并自动补充不足的任务（v7.420新增）

        核心逻辑：
        1. 统计每个板块的搜索任务数量
        2. 如果某个板块任务数少于3个，自动生成补充任务
        3. 确保所有板块都有充分的搜索覆盖

        Args:
            queries: 原始搜索查询列表
            output_framework: 输出框架
            user_input: 用户输入

        Returns:
            补充后的搜索查询列表
        """
        logger.info(" [Step 2 验证] 开始验证搜索任务数量...")

        # 1. 统计每个板块的搜索任务数量
        block_query_count = {}
        block_queries = {}

        for block in output_framework.blocks:
            block_query_count[block.id] = 0
            block_queries[block.id] = []

        for query in queries:
            for block_id in query.serves_blocks:
                if block_id in block_query_count:
                    block_query_count[block_id] += 1
                    block_queries[block_id].append(query)

        # 2. 检查并报告
        insufficient_blocks = []
        for block in output_framework.blocks:
            count = block_query_count.get(block.id, 0)
            logger.info(f"   板块 {block.id} ({block.name}): {count} 个搜索任务")

            if count < 3:
                insufficient_blocks.append(block)
                logger.warning(f"   ️ 板块 {block.id} 任务不足（{count}<3），需要补充")

        # 3. 如果有不足的板块，生成补充任务
        supplementary_queries = []
        if insufficient_blocks:
            logger.info(f" [Step 2 验证] 开始为 {len(insufficient_blocks)} 个板块生成补充任务...")

            for block in insufficient_blocks:
                current_count = block_query_count.get(block.id, 0)
                needed_count = 3 - current_count

                logger.info(f"   为板块 {block.id} 生成 {needed_count} 个补充任务...")

                # 生成补充任务
                block_supp_queries = await self._generate_supplementary_queries_for_block(
                    block=block,
                    existing_queries=block_queries.get(block.id, []),
                    needed_count=needed_count,
                    user_input=user_input,
                )

                supplementary_queries.extend(block_supp_queries)
                logger.info(f"    已生成 {len(block_supp_queries)} 个补充任务")

        # 4. 合并原始任务和补充任务
        all_queries = queries + supplementary_queries

        logger.info(" [Step 2 验证] 验证完成")
        logger.info(f"   原始任务: {len(queries)} 个")
        logger.info(f"   补充任务: {len(supplementary_queries)} 个")
        logger.info(f"   总计任务: {len(all_queries)} 个")

        return all_queries

    async def _generate_supplementary_queries_for_block(
        self,
        block: OutputBlock,
        existing_queries: List[SearchQuery],
        needed_count: int,
        user_input: str,
    ) -> List[SearchQuery]:
        """
        为单个板块生成补充搜索任务

        Args:
            block: 板块对象
            existing_queries: 该板块现有的搜索任务
            needed_count: 需要补充的任务数量
            user_input: 用户输入

        Returns:
            补充搜索任务列表
        """
        # 构建prompt
        existing_queries_text = (
            "\n".join([f"- {q.query}" for q in existing_queries]) if existing_queries else "（当前没有搜索任务）"
        )

        sub_items_text = "\n".join([f"- {item.id} {item.name}: {item.description}" for item in block.sub_items])

        prompt = f"""你是一位资深的信息检索专家。以下板块的搜索任务不足，需要补充。

## 板块信息

**板块ID**: {block.id}
**板块名称**: {block.name}
**板块长度**: {block.estimated_length}
**用户特征**: {', '.join(block.user_characteristics)}

**子项列表**:
{sub_items_text}

## 用户问题
"{user_input}"

## 现有搜索任务
{existing_queries_text}

## 任务

请为此板块生成 {needed_count} 个**深度挖掘**的补充搜索任务。

**要求**:
1. 不要重复现有任务的内容
2. 从不同维度扩展：理论基础、案例参考、技术细节、用户洞察、趋势动态、对比分析
3. 查询必须高度具体化，包含用户关键特征
4. 查询可以直接用于搜索引擎

**输出格式（JSON）**:

```json
{{
  "supplementary_queries": [
    {{
      "query": "具体查询内容（必须包含用户关键特征）",
      "expected_output": "预期输出说明",
      "search_keywords": ["关键词1", "关键词2", "关键词3"],
      "success_criteria": "成功标准",
      "dimension": "理论基础/案例参考/技术细节/用户洞察/趋势动态/对比分析"
    }}
  ]
}}
```

请只输出JSON，不要有其他内容。"""

        # 调用LLM（v7.421: 提升temperature到0.6以提升补充任务的多样性）
        llm = self.llm_factory.create_llm(temperature=0.6, max_tokens=2000)

        try:
            response = await llm.ainvoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)

            # 解析JSON
            json_match = re.search(r"```json\s*(.*?)\s*```", content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r"\{[\s\S]*\}", content)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    json_str = content

            data = json.loads(json_str.strip())

            # 构建SearchQuery对象
            supplementary_queries = []
            existing_query_count = len(existing_queries)

            for i, query_data in enumerate(data.get("supplementary_queries", []), 1):
                query_id = f"query_{block.id.split('_')[-1]}_{existing_query_count + i}_supp"

                supplementary_queries.append(
                    SearchQuery(
                        id=query_id,
                        query=query_data.get("query", ""),
                        serves_blocks=[block.id],
                        expected_output=query_data.get("expected_output", ""),
                        search_keywords=query_data.get("search_keywords", []),
                        success_criteria=query_data.get("success_criteria", ""),
                        priority=2,  # 补充任务优先级为2
                        dependencies=[],
                        can_parallel_with=[],
                        status="pending",
                    )
                )

            return supplementary_queries

        except Exception as e:
            logger.error(f" 生成补充任务失败: {e}")
            # 降级策略：生成简单的补充任务
            return self._fallback_supplementary_queries(block, existing_queries, needed_count)

    def _fallback_supplementary_queries(
        self,
        block: OutputBlock,
        existing_queries: List[SearchQuery],
        needed_count: int,
    ) -> List[SearchQuery]:
        """
        降级策略：生成简单的补充任务

        当LLM生成失败时使用
        """
        logger.warning("️ 使用降级策略生成补充任务")

        supplementary_queries = []
        existing_query_count = len(existing_queries)

        # 预定义的补充任务模板（基于多维度）
        dimensions = [
            ("理论基础", f"{block.name}的设计原则和理论基础", ["设计原则", "理论", "方法论"]),
            ("案例参考", f"{block.name}的实际案例和成功经验", ["案例", "成功经验", "实践"]),
            ("技术细节", f"{block.name}的具体实现方法和技术细节", ["实现方法", "技术", "工艺"]),
            ("用户洞察", f"{block.name}的用户需求和痛点分析", ["用户需求", "痛点", "行为模式"]),
            ("趋势动态", f"{block.name}的行业趋势和创新方向", ["趋势", "创新", "展望"]),
        ]

        for i in range(min(needed_count, len(dimensions))):
            dim_name, query_template, keywords = dimensions[i]
            query_id = f"query_{block.id.split('_')[-1]}_{existing_query_count + i + 1}_supp"

            # 添加用户特征
            user_chars_str = " ".join(block.user_characteristics[:2]) if block.user_characteristics else ""
            if user_chars_str:
                query_text = f"{user_chars_str} {query_template}"
            else:
                query_text = query_template

            supplementary_queries.append(
                SearchQuery(
                    id=query_id,
                    query=query_text,
                    serves_blocks=[block.id],
                    expected_output=f"从{dim_name}角度补充{block.name}的相关信息",
                    search_keywords=keywords + block.user_characteristics[:1],
                    success_criteria=f"找到与{dim_name}相关的有价值信息",
                    priority=2,
                    dependencies=[],
                    can_parallel_with=[],
                    status="pending",
                )
            )

        return supplementary_queries

    def _serialize_search_queries(self, queries: List[SearchQuery]) -> List[Dict[str, Any]]:
        """序列化搜索查询列表"""
        return [
            {
                "id": q.id,
                "query": q.query,
                "serves_blocks": q.serves_blocks,
                "expected_output": q.expected_output,
                "search_keywords": q.search_keywords,
                "success_criteria": q.success_criteria,
                "priority": q.priority,
                "dependencies": q.dependencies,
                "can_parallel_with": q.can_parallel_with,
                "status": q.status,
            }
            for q in queries
        ]

    def _serialize_execution_strategy(self, strategy: ExecutionStrategy | None) -> Dict[str, Any] | None:
        """序列化执行策略"""
        if not strategy:
            return None
        return {
            "priority_1_queries": strategy.priority_1_queries,
            "priority_2_queries": strategy.priority_2_queries,
            "priority_3_queries": strategy.priority_3_queries,
            "parallel_groups": strategy.parallel_groups,
        }

    def _serialize_execution_advice(self, advice: ExecutionAdvice | None) -> Dict[str, Any] | None:
        """序列化执行建议"""
        if not advice:
            return None
        return {
            "overall_strategy": advice.overall_strategy,
            "key_success_factors": advice.key_success_factors,
            "risk_alerts": advice.risk_alerts,
        }


__all__ = ["Step2SearchTaskDecompositionExecutor"]
