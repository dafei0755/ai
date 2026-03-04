"""
ExpertCompletionMixin

专家交付物补全、降级搜索相关方法，从 task_oriented_expert_factory.py 中拆分。
由 TaskOrientedExpertFactory 通过多重继承引入。
"""

import datetime
import json
import re
from typing import Any, Dict, List

from loguru import logger

from ..core.state import ProjectAnalysisState


class ExpertCompletionMixin:
    """Mixin: 交付物补全 + 工具降级搜索"""

    # forward ref: 子类需提供 _get_llm / _get_timestamp 实现
    # (由 TaskOrientedExpertFactory 提供)

    def _validate_task_completion(self, structured_output: Dict[str, Any], task_instruction: Dict[str, Any]) -> bool:
        """
        验证任务完成情况，确保所有deliverables都已处理

         v7.9.3: 增强验证 - 检测到缺失交付物时标记需要补全，而非直接通过

        Returns:
            bool: True表示验证通过，False表示需要补全
        """
        if not structured_output:
            logger.warning("️ 无结构化输出，无法验证任务完成情况")
            return False

        try:
            # 获取任务指令中的预期交付物
            expected_deliverables = task_instruction.get("deliverables", [])

            # 获取实际的交付物输出（修复字段路径）
            task_exec_report = structured_output.get("task_execution_report", {})
            actual_results = task_exec_report.get("deliverable_outputs", [])

            # 如果没有预期交付物，则直接通过（降级场景）
            if not expected_deliverables:
                logger.info(" 无预期交付物要求，验证通过")
                return True

            expected_names = {d.get("name", f"交付物{i}") for i, d in enumerate(expected_deliverables, 1)}
            actual_names = {r.get("deliverable_name", "") for r in actual_results}

            missing_deliverables = expected_names - actual_names
            if missing_deliverables:
                logger.warning(f"️ 缺失交付物: {missing_deliverables}")
                #  v7.9.3: 不再直接返回True，而是标记需要补全
                if "validation_result" not in structured_output:
                    structured_output["validation_result"] = {}
                structured_output["validation_result"]["missing_deliverables"] = list(missing_deliverables)
                structured_output["validation_result"]["needs_completion"] = True
                structured_output["validation_result"]["expected_deliverables"] = expected_deliverables
                logger.info(f" 标记需要补全的交付物: {missing_deliverables}")
                return False  #  返回False表示验证未通过，需要补全

            # 验证协议执行状态（修复字段名）
            protocol_execution = structured_output.get("protocol_execution", {})
            if not protocol_execution.get("protocol_status"):
                logger.warning("️ 协议执行状态缺失")
                # 降级场景下不强制失败
                return True

            logger.info(" 任务完成验证通过")
            return True

        except Exception as e:
            logger.error(f" 验证任务完成时出错: {str(e)}")
            # 发生错误时也返回True，避免阻塞流程
            return True


    async def _complete_missing_deliverables(
        self, structured_output: Dict[str, Any], role_object: Dict[str, Any], context: str, state: ProjectAnalysisState
    ) -> Dict[str, Any]:
        """
         v7.11: 自动补全缺失的交付物（性能优化版）

        当检测到专家输出缺少部分交付物时，自动调用LLM补充缺失部分

        性能优化:
        - 限制每次补全最多3个交付物
        - 添加超时控制（30秒）
        - 如果缺失过多，优先补全核心交付物

        Args:
            structured_output: 当前的结构化输出（包含validation_result）
            role_object: 角色对象
            context: 项目上下文
            state: 当前状态

        Returns:
            Dict: 补全后的结构化输出
        """
        import asyncio

        try:
            validation_result = structured_output.get("validation_result", {})
            missing_deliverables = validation_result.get("missing_deliverables", [])
            expected_deliverables = validation_result.get("expected_deliverables", [])

            if not missing_deliverables:
                logger.warning("️ 没有缺失的交付物，无需补全")
                return structured_output

            #  v7.11: 性能优化 - 限制每次补全的数量
            MAX_COMPLETION_COUNT = 3
            if len(missing_deliverables) > MAX_COMPLETION_COUNT:
                logger.warning(f"️ 缺失交付物过多({len(missing_deliverables)}个)，只补全前{MAX_COMPLETION_COUNT}个")
                missing_deliverables = missing_deliverables[:MAX_COMPLETION_COUNT]

            logger.info(f" 开始补全缺失的交付物: {missing_deliverables}")

            # 构建补全提示词
            completion_prompt = self._build_completion_prompt(
                role_object=role_object,
                context=context,
                state=state,
                missing_deliverables=missing_deliverables,
                expected_deliverables=expected_deliverables,
                existing_output=structured_output,
            )

            #  v7.11: 添加超时控制（30秒）
            #  v7.52: 使用 JSON 模式强制 JSON 输出
            llm = self._get_llm()

            # 尝试使用 with_structured_output (JSON模式)
            try:
                llm_json_mode = llm.with_structured_output(method="json_mode")
                logger.info(" [v7.52] 使用 JSON 模式强制输出")
            except Exception as e:
                logger.debug(f"️ JSON模式不可用，使用普通模式: {e}")
                llm_json_mode = llm

            messages = [
                {"role": "system", "content": completion_prompt["system_prompt"]},
                {"role": "user", "content": completion_prompt["user_prompt"]},
            ]

            try:
                response = await asyncio.wait_for(llm_json_mode.ainvoke(messages), timeout=30.0)  # 30秒超时
                completion_output = response.content if hasattr(response, "content") else str(response)
            except asyncio.TimeoutError:
                logger.warning("️ 交付物补全超时（30秒），使用原始输出")
                return structured_output

            # 解析补充的交付物
            completed_deliverables = self._parse_completion_output(completion_output, missing_deliverables)

            #  v7.52: 批量失败时尝试逐个生成
            if not completed_deliverables and len(missing_deliverables) > 1:
                logger.warning(f"️ 批量补全失败，尝试逐个生成 {len(missing_deliverables)} 个交付物")
                completed_deliverables = await self._complete_deliverables_one_by_one(
                    role_object, context, state, missing_deliverables
                )

            #  v7.23: 更准确的日志信息
            if not completed_deliverables:
                logger.warning(f"️ 交付物补全完全失败：尝试补全 {len(missing_deliverables)} 个，实际解析出 0 个")
                #  v7.52: 生成占位符，避免完全失败
                completed_deliverables = self._generate_placeholder_deliverables(missing_deliverables)
                logger.info(f" [v7.52] 已生成 {len(completed_deliverables)} 个占位交付物")

            # 合并到原始输出
            task_exec_report = structured_output.get("task_execution_report", {})
            deliverable_outputs = task_exec_report.get("deliverable_outputs", [])

            # 添加补充的交付物
            for deliverable in completed_deliverables:
                deliverable_outputs.append(deliverable)
                logger.info(f" 已补全交付物: {deliverable.get('deliverable_name')}")

            # 更新结构化输出
            task_exec_report["deliverable_outputs"] = deliverable_outputs
            structured_output["task_execution_report"] = task_exec_report

            # 清除validation_result标记
            if "validation_result" in structured_output:
                del structured_output["validation_result"]

            logger.info(f" 成功补全 {len(completed_deliverables)}/{len(missing_deliverables)} 个交付物")
            return structured_output

        except Exception as e:
            logger.error(f" 补全缺失交付物时出错: {str(e)}")
            # 发生错误时返回原始输出，不阻塞流程
            logger.warning("️ 补全失败，使用原始输出")
            return structured_output


    def _build_completion_prompt(
        self,
        role_object: Dict[str, Any],
        context: str,
        state: ProjectAnalysisState,
        missing_deliverables: List[str],
        expected_deliverables: List[Dict[str, Any]],
        existing_output: Dict[str, Any],
    ) -> Dict[str, str]:
        """
         v7.9.3: 构建补全提示词，只要求LLM输出缺失的交付物

        Args:
            role_object: 角色对象
            context: 项目上下文
            state: 当前状态
            missing_deliverables: 缺失的交付物名称列表
            expected_deliverables: 预期的所有交付物定义
            existing_output: 已有的输出（用于上下文）

        Returns:
            Dict: 包含system_prompt和user_prompt的字典
        """
        # 筛选出缺失的交付物定义
        missing_defs = [d for d in expected_deliverables if d.get("name") in missing_deliverables]

        # 获取已完成的交付物（作为参考）
        existing_deliverables = existing_output.get("task_execution_report", {}).get("deliverable_outputs", [])
        existing_names = [d.get("deliverable_name") for d in existing_deliverables]

        system_prompt = f"""
你是 {role_object.get('dynamic_role_name', role_object.get('role_name'))}。

#  补全任务

你之前已经完成了部分交付物：{', '.join(existing_names)}

但还有以下交付物**尚未完成**，需要你现在补充：

"""
        for i, deliverable in enumerate(missing_defs, 1):
            system_prompt += f"""
**缺失交付物 {i}: {deliverable.get('name')}**
- 描述: {deliverable.get('description', '')}
- 格式: {deliverable.get('format', 'analysis')}
- 成功标准: {', '.join(deliverable.get('success_criteria', []))}
"""

        system_prompt += """

#  输出要求

**请只输出缺失的交付物**，格式如下：

```json
{
  "deliverable_outputs": [
    {
      "deliverable_name": "缺失交付物的名称（必须与上面列出的名称完全一致）",
      "content": "详细的分析内容（完整、专业、符合成功标准）",
      "completion_status": "completed",
      "completion_rate": 0.95,
      "notes": "补充说明",
      "quality_self_assessment": 0.9
    }
  ]
}
```

# ️ 关键要求

1. **只输出缺失的交付物**，不要重复已完成的交付物
2. **deliverable_name必须与任务指令中的名称完全一致**
3. **content要详细完整**，不要简化或省略
4. **返回有效的JSON格式**，不要有额外文字
5. **不要使用markdown代码块包裹JSON**

开始补充缺失的交付物：
"""

        user_prompt = f"""
#  项目上下文
{context}

#  当前项目状态
- 项目阶段: {state.get('current_phase', '分析阶段')}
- 已完成分析: {len(state.get('expert_analyses', {}))}个专家

#  你的任务

请基于上述项目上下文，补充以下缺失的交付物：
{', '.join(missing_deliverables)}

**记住**：只输出缺失的交付物，格式为JSON，不要有任何额外文字。
"""

        return {"system_prompt": system_prompt, "user_prompt": user_prompt}


    def _parse_completion_output(self, completion_output: str, missing_deliverables: List[str]) -> List[Dict[str, Any]]:
        """
         v7.9.3: 解析补全输出，提取交付物列表
         v7.23: 增强 JSON 解析容错性，支持多种格式

        Args:
            completion_output: LLM返回的补全内容
            missing_deliverables: 预期的缺失交付物名称列表

        Returns:
            List[Dict]: 解析后的交付物列表
        """
        import re

        try:
            json_str = None

            # 策略1: 提取 ```json ... ``` 代码块
            if "```json" in completion_output:
                json_start = completion_output.find("```json") + 7
                json_end = completion_output.find("```", json_start)
                if json_end > json_start:
                    json_str = completion_output[json_start:json_end].strip()

            # 策略2: 提取 ``` ... ``` 代码块（无语言标识）
            if not json_str and "```" in completion_output:
                matches = re.findall(r"```\s*([\s\S]*?)\s*```", completion_output)
                for match in matches:
                    if "{" in match and "}" in match:
                        json_str = match.strip()
                        break

            # 策略3: 提取最外层 {...} 或 [...]
            if not json_str:
                # 优先尝试提取对象
                obj_match = re.search(r"\{[\s\S]*\}", completion_output)
                if obj_match:
                    json_str = obj_match.group()
                else:
                    # 尝试提取数组
                    arr_match = re.search(r"\[[\s\S]*\]", completion_output)
                    if arr_match:
                        json_str = arr_match.group()

            if not json_str:
                logger.warning("️ 补全输出不包含有效JSON结构")
                return []

            #  v7.23: 清理常见的 JSON 格式问题
            # 移除 JavaScript 风格的注释
            json_str = re.sub(r"//.*?(?=\n|$)", "", json_str)
            json_str = re.sub(r"/\*.*?\*/", "", json_str, flags=re.DOTALL)
            # 移除尾随逗号
            json_str = re.sub(r",(\s*[}\]])", r"\1", json_str)

            # 解析JSON
            parsed = json.loads(json_str)

            # 提取deliverable_outputs（支持多种字段名）
            if isinstance(parsed, dict):
                deliverables = (
                    parsed.get("deliverable_outputs") or parsed.get("deliverables") or parsed.get("outputs") or []
                )
                if deliverables:
                    logger.info(f" 成功解析 {len(deliverables)} 个补全交付物")
                    return deliverables
                else:
                    logger.warning("️ 解析的JSON中没有deliverable_outputs字段")
                    return []
            elif isinstance(parsed, list):
                # 如果直接返回数组
                if parsed:
                    logger.info(f" 成功解析 {len(parsed)} 个补全交付物（数组格式）")
                    return parsed
                return []
            else:
                logger.warning(f"️ 解析结果类型不符合预期: {type(parsed)}")
                return []

        except json.JSONDecodeError as e:
            logger.error(f" 解析补全输出JSON失败: {str(e)}")
            logger.debug(f"原始输出片段: {completion_output[:300]}...")

            #  v7.23: 尝试从原始输出构造默认交付物
            fallback_deliverables = []
            for name in missing_deliverables[:2]:  # 最多构造2个
                fallback_deliverables.append(
                    {
                        "deliverable_name": name,
                        "content": f"[解析失败，需要人工补充] 原始输出: {completion_output[:200]}...",
                        "completion_status": "partial",
                        "completion_rate": 0.3,
                        "notes": "LLM输出格式异常，已使用降级策略",
                    }
                )
            if fallback_deliverables:
                logger.warning(f"️ 使用降级策略，构造 {len(fallback_deliverables)} 个占位交付物")
            return fallback_deliverables

        except Exception as e:
            logger.error(f" 处理补全输出时出错: {str(e)}")
            return []


    async def _complete_deliverables_one_by_one(
        self, role_object: Dict[str, Any], context: str, state: ProjectAnalysisState, missing_deliverables: List[str]
    ) -> List[Dict[str, Any]]:
        """
         v7.52: 逐个生成缺失交付物（降级策略）

        当批量生成失败时，尝试逐个生成每个交付物，
        提高成功率。

        Args:
            role_object: 角色对象
            context: 项目上下文
            state: 当前状态
            missing_deliverables: 缺失的交付物名称列表

        Returns:
            List[Dict]: 生成的交付物列表
        """
        import asyncio

        completed = []
        llm = self._get_llm()

        for deliverable_name in missing_deliverables:
            try:
                logger.info(f" 逐个生成: {deliverable_name}")

                # 构建单个交付物的提示词
                single_prompt = f"""你是 {role_object.get('name', '专家')}。

请生成以下交付物：
**{deliverable_name}**

#  项目上下文
{context[:1000]}...

#  要求
1. 输出JSON格式，包含以下字段：
   - deliverable_name: "{deliverable_name}"
   - content: 详细内容
   - key_insights: 关键洞察（列表）
   - completion_rate: 完成度（0-1）

2. 直接返回JSON，不要有额外文字

输出示例：
{{
  "deliverable_name": "{deliverable_name}",
  "content": "...",
  "key_insights": ["洞察1", "洞察2"],
  "completion_rate": 1.0
}}
"""

                # 调用LLM（10秒超时）
                response = await asyncio.wait_for(
                    llm.ainvoke([{"role": "user", "content": single_prompt}]), timeout=10.0
                )
                output = response.content if hasattr(response, "content") else str(response)

                # 解析单个交付物
                single_result = self._parse_single_deliverable_output(output, deliverable_name)
                if single_result:
                    completed.append(single_result)
                    logger.info(f" 成功生成: {deliverable_name}")
                else:
                    logger.warning(f"️ 解析失败: {deliverable_name}")

            except asyncio.TimeoutError:
                logger.warning(f"️ 生成超时: {deliverable_name}")
            except Exception as e:
                logger.error(f" 生成失败 {deliverable_name}: {e}")

            # 限制最多尝试3个
            if len(completed) >= 3:
                logger.info(" 已成功生成3个交付物，停止逐个生成")
                break

        return completed


    def _parse_single_deliverable_output(self, output: str, expected_name: str) -> Dict[str, Any] | None:
        """
         v7.52: 解析单个交付物的LLM输出

        Args:
            output: LLM原始输出
            expected_name: 期望的交付物名称

        Returns:
            Dict | None: 解析成功返回交付物字典，失败返回None
        """
        import json
        import re

        try:
            # 提取JSON
            json_str = None
            if "```json" in output:
                json_start = output.find("```json") + 7
                json_end = output.find("```", json_start)
                if json_end > json_start:
                    json_str = output[json_start:json_end].strip()
            elif "```" in output:
                matches = re.findall(r"```\s*([\s\S]*?)\s*```", output)
                for match in matches:
                    if "{" in match:
                        json_str = match.strip()
                        break

            if not json_str:
                obj_match = re.search(r"\{[\s\S]*\}", output)
                if obj_match:
                    json_str = obj_match.group()

            if not json_str:
                return None

            # 解析JSON
            parsed = json.loads(json_str)

            # 验证必需字段
            if not parsed.get("deliverable_name"):
                parsed["deliverable_name"] = expected_name

            if not parsed.get("content"):
                return None

            # 补充可选字段
            if "completion_rate" not in parsed:
                parsed["completion_rate"] = 0.8
            if "key_insights" not in parsed:
                parsed["key_insights"] = []

            return parsed

        except Exception as e:
            logger.debug(f"️ 单个交付物解析失败: {e}")
            return None


    def _generate_placeholder_deliverables(self, missing_names: List[str]) -> List[Dict[str, Any]]:
        """
         v7.52: 生成占位交付物（最终降级策略）

        当所有生成策略都失败时，生成占位内容，
        避免流程完全失败。

        Args:
            missing_names: 缺失的交付物名称列表

        Returns:
            List[Dict]: 占位交付物列表
        """
        placeholders = []
        for name in missing_names[:3]:  # 最多3个
            placeholders.append(
                {
                    "deliverable_name": name,
                    "content": f"[待补充] {name}\n\n由于LLM生成失败，此交付物需要人工补充。建议审查项目需求后手动完成。",
                    "completion_status": "pending",
                    "completion_rate": 0.0,
                    "key_insights": [],
                    "notes": " v7.52: 自动生成的占位内容，需要人工补充",
                }
            )
        return placeholders


    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


    def _extract_full_deliverable_content(self, structured_output: Dict[str, Any]) -> str:
        """
         v7.128: 提取所有交付物的完整内容（用于概念图生成）

        Args:
            structured_output: 专家结构化输出

        Returns:
            拼接后的完整内容（包含设计理念、空间布局、材料选型等所有细节）
            格式：## 交付物名称1\n\n详细内容...\n\n## 交付物名称2\n\n详细内容...
        """
        task_exec_report = structured_output.get("task_execution_report", {})
        deliverable_outputs = task_exec_report.get("deliverable_outputs", [])

        full_content = []
        for deliverable in deliverable_outputs:
            name = deliverable.get("deliverable_name", "")
            content = deliverable.get("content", "")
            if content:
                full_content.append(f"## {name}\n\n{content}")

        result = "\n\n".join(full_content) if full_content else ""
        logger.debug(f"[v7.128] 提取完整内容长度: {len(result)} 字符")
        return result


    def _extract_deliverable_specific_content(
        self, structured_output: Dict[str, Any], deliverable_metadata: dict
    ) -> str:
        """
         v7.128: 提取特定交付物的完整分析内容

        Args:
            structured_output: 专家结构化输出
            deliverable_metadata: 交付物元数据（包含name）

        Returns:
            该交付物的完整分析内容（最多3000字）
        """
        deliverable_name = deliverable_metadata.get("name", "")

        task_exec_report = structured_output.get("task_execution_report", {})
        deliverable_outputs = task_exec_report.get("deliverable_outputs", [])

        # 精准匹配交付物名称
        for deliverable in deliverable_outputs:
            if deliverable.get("deliverable_name") == deliverable_name:
                content = deliverable.get("content", "")
                limited_content = content[:3000]  # 限制3000字
                logger.info(f"[v7.128] 为交付物 '{deliverable_name}' 提取专家分析: {len(limited_content)} 字符")
                return limited_content

        # 降级：返回所有内容的拼接
        all_content = "\n\n".join(d.get("content", "") for d in deliverable_outputs)
        limited_content = all_content[:3000]
        logger.warning(f"[v7.128] 未找到交付物 '{deliverable_name}' 的精准匹配，返回所有内容: {len(limited_content)} 字符")
        return limited_content


    async def _execute_fallback_search(
        self,
        role_object: Dict[str, Any],
        context: str,
        state: ProjectAnalysisState,
        tools: List[Any] | None = None,
    ) -> List[Dict[str, Any]]:
        """
         v7.129 Week2 P2: 执行降级搜索

        当LLM未主动调用工具时，系统自动执行搜索作为后备方案，
        确保至少有基本的搜索引用。优先级: Serper > Tavily > Bocha (v7.130+)

        Args:
            role_object: 角色对象
            context: 项目上下文
            state: 当前状态
            tools: 可用的工具列表

        Returns:
            搜索引用列表
        """
        role_id = role_object.get("role_id", "unknown")
        logger.info(f" [v7.129 Fallback] {role_id} 开始执行降级搜索")

        search_references = []

        try:
            # 1. 从tools中找到搜索工具（优先博查 → Tavily → Milvus）
            bocha_tool = None
            tavily_tool = None
            serper_tool = None

            if tools:
                for tool in tools:
                    tool_name = getattr(tool, "name", "")
                    if "bocha" in tool_name.lower():
                        bocha_tool = tool
                    elif "tavily" in tool_name.lower():
                        tavily_tool = tool
                    elif "serper" in tool_name.lower():
                        serper_tool = tool

            # 2. 如果tools中没有，从ToolFactory创建（博查优先）
            if not bocha_tool and not tavily_tool and not serper_tool:
                logger.info(f" [v7.129 Fallback] {role_id} 从ToolFactory创建搜索工具")
                from ..services.tool_factory import ToolFactory

                try:
                    bocha_tool = ToolFactory.create_bocha_tool()
                    logger.info(" [v7.129 Fallback] 博查工具创建成功（优先）")
                except Exception as e:
                    logger.warning(f"️ [v7.129 Fallback] 博查工具创建失败: {e}")
                    try:
                        tavily_tool = ToolFactory.create_tavily_tool()
                        logger.info(" [v7.129 Fallback] Tavily工具创建成功（降级）")
                    except Exception as e2:
                        logger.warning(f"️ [v7.129 Fallback] Tavily工具也创建失败: {e2}")
                        try:
                            serper_tool = ToolFactory.create_serper_tool()
                            logger.info(" [v7.129 Fallback] Serper工具创建成功（二次降级）")
                        except Exception as e3:
                            logger.error(f" [v7.129 Fallback] 所有搜索工具创建失败: {e3}")

            # 3. 提取搜索查询关键词
            task_instruction = role_object.get("task_instruction", {})
            deliverables = task_instruction.get("deliverables", [])

            # 构建基本搜索查询
            user_input = state.get("user_input", "")
            base_query = user_input[:100] if user_input else context[:100]

            # 生成搜索查询列表（最多3个）
            search_queries = []

            # Query 1: 基于用户输入
            if user_input:
                search_queries.append(base_query + " 设计案例 2025")

            # Query 2: 基于第一个deliverable
            if deliverables and len(deliverables) > 0:
                first_deliverable = deliverables[0].get("name", "")
                if first_deliverable:
                    search_queries.append(f"{first_deliverable} 最佳实践")

            # Query 3: 基于角色名称
            role_name = role_object.get("dynamic_role_name", role_object.get("role_name", ""))
            if role_name:
                search_queries.append(f"{role_name} 专业分析方法")

            # 确保至少有1个查询
            if not search_queries:
                search_queries.append(base_query)

            # 限制最多3个查询
            search_queries = search_queries[:3]

            logger.info(f" [v7.129 Fallback] {role_id} 执行 {len(search_queries)} 个搜索查询")

            # 4. 执行搜索
            for idx, query in enumerate(search_queries, 1):
                try:
                    logger.info(f"   [{idx}/{len(search_queries)}] 查询: {query[:50]}...")

                    #  智能语言感知路由：根据查询语言选择最佳工具
                    # 策略：中文查询 → 博查（中文专用）→ Tavily（全球覆盖）→ Serper
                    #      英文查询 → Tavily（全球覆盖）→ 博查 → Serper

                    def is_chinese_query(text: str) -> bool:
                        """判断是否为中文查询（包含中文字符）"""
                        return any("\u4e00" <= char <= "\u9fff" for char in text)

                    is_chinese = is_chinese_query(query)

                    #  v7.131: 语言感知路由 - 中文查询优先使用博查
                    if is_chinese:
                        # 中文查询: Bocha → Tavily → Serper
                        tool_to_use = bocha_tool if bocha_tool else (tavily_tool if tavily_tool else serper_tool)
                        if bocha_tool:
                            logger.info(f" [Fallback] 中文查询 '{query[:30]}...'，使用博查（中文专用）")
                        elif tavily_tool:
                            logger.warning("️ [Fallback] 博查不可用，降级至Tavily")
                        elif serper_tool:
                            logger.warning("️ [Fallback] 博查和Tavily不可用，降级至Serper")
                    else:
                        # 英文查询: Tavily → Bocha → Serper
                        tool_to_use = tavily_tool if tavily_tool else (bocha_tool if bocha_tool else serper_tool)
                        if tavily_tool:
                            logger.info(" [Fallback] 英文查询，使用Tavily（全球覆盖）")
                        elif bocha_tool:
                            logger.warning("️ [Fallback] Tavily不可用，降级至博查")
                        elif serper_tool:
                            logger.warning("️ [Fallback] Tavily和博查不可用，降级至Serper")

                    if not tool_to_use:
                        logger.error(" [v7.129 Fallback] 无可用搜索工具")
                        break

                    # 调用工具
                    search_result = await tool_to_use.ainvoke({"query": query})

                    # 解析结果
                    if isinstance(search_result, dict):
                        results_list = search_result.get("results", [])
                    elif isinstance(search_result, list):
                        results_list = search_result
                    else:
                        # 尝试解析字符串结果
                        import json

                        try:
                            parsed = json.loads(str(search_result))
                            results_list = parsed.get("results", []) if isinstance(parsed, dict) else []
                        except Exception:
                            logger.warning(f"️ [v7.129 Fallback] 无法解析搜索结果: {type(search_result)}")
                            results_list = []

                    # 转换为search_references格式
                    for result in results_list[:5]:  # 每个查询最多5条结果
                        ref = {
                            "title": result.get("title", ""),
                            "url": result.get("url", ""),
                            "snippet": result.get("snippet", result.get("content", ""))[:500],
                            "source": f"fallback_{tool_to_use.name}"
                            if hasattr(tool_to_use, "name")
                            else "fallback_search",
                            "query": query,
                            "role_id": role_id,
                            "deliverable_id": f"{role_id}_fallback",
                            "timestamp": self._get_timestamp(),
                        }
                        search_references.append(ref)

                    logger.info(f"    查询{idx}获得 {len(results_list)} 条结果")

                except Exception as search_error:
                    logger.error(f"    查询{idx}失败: {search_error}")
                    continue

            logger.info(f" [v7.129 Fallback] {role_id} 降级搜索完成，共获得 {len(search_references)} 条引用")

        except Exception as e:
            logger.error(f" [v7.129 Fallback] {role_id} 降级搜索异常: {e}")
            import traceback

            traceback.print_exc()

        return search_references


# 兼容性接口：为现有代码提供平滑过渡

