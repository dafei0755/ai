"""
需求分析师智能体

负责理解和结构化用户需求，为后续分析提供基础
"""

import json
from typing import Dict, List, Optional, Any
import time

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from loguru import logger

from .base import LLMAgent
from ..core.state import ProjectAnalysisState, AgentType
from ..core.types import AnalysisResult
from ..core.prompt_manager import PromptManager
from ..utils.jtbd_parser import transform_jtbd_to_natural_language


class RequirementsAnalystAgent(LLMAgent):
    """需求分析师智能体"""
    
    def __init__(self, llm_model, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            agent_type=AgentType.REQUIREMENTS_ANALYST,
            name="需求分析师",
            description="理解和结构化用户项目需求，识别关键要素和约束条件",
            llm_model=llm_model,
            config=config
        )

        # 初始化提示词管理器
        self.prompt_manager = PromptManager()
    
    def validate_input(self, state: ProjectAnalysisState) -> bool:
        """验证输入是否有效"""
        user_input = state.get("user_input", "").strip()
        return len(user_input) > 10  # 至少10个字符
    
    def get_system_prompt(self) -> str:
        """获取系统提示词 - 从外部配置加载 v3.4 (优化版本)"""
        # ✅ v3.4优化: 优先加载精简版配置，提升3-5倍响应速度
        # 尝试加载精简版 (requirements_analyst_lite.yaml)
        prompt_config = self.prompt_manager.get_prompt("requirements_analyst_lite", return_full_config=True)
        
        # 如果精简版不存在，回退到完整版
        if not prompt_config:
            logger.info("[INFO] 精简版配置未找到，加载完整版 requirements_analyst.yaml")
            prompt_config = self.prompt_manager.get_prompt("requirements_analyst", return_full_config=True)

        # 如果配置不存在，抛出错误（不再使用硬编码 fallback）
        if not prompt_config:
            raise ValueError(
                "❌ 未找到提示词配置: requirements_analyst 或 requirements_analyst_lite\n"
                "请确保配置文件存在: config/prompts/requirements_analyst_lite.yaml\n"
                "系统无法使用硬编码提示词，请检查配置文件。"
            )

        # 获取系统提示词
        system_prompt = prompt_config.get("system_prompt", "")

        if not system_prompt:
            raise ValueError(
                "❌ 配置文件中缺少 system_prompt 字段\n"
                "请确保配置文件包含完整的 system_prompt 字段。"
            )
        
        # ✅ v3.4优化日志
        prompt_length = len(system_prompt)
        estimated_tokens = prompt_length // 4
        logger.info(f"[v3.4 优化] 已加载提示词: {prompt_length} 字符, 约 {estimated_tokens} tokens")

        return system_prompt

    def get_task_description(self, state: ProjectAnalysisState) -> str:
        """获取具体任务描述 - v3.4版本（优先使用精简版配置）"""
        user_input = state.get("user_input", "")

        # ✅ v3.4优化: 优先使用精简版配置
        # 使用 PromptManager 的新方法获取任务描述
        task_description = self.prompt_manager.get_task_description(
            agent_name="requirements_analyst_lite",
            user_input=user_input,
            include_datetime=True
        )
        
        # 如果精简版不存在，回退到完整版
        if not task_description:
            logger.info("[INFO] 精简版任务描述未找到，使用完整版")
            task_description = self.prompt_manager.get_task_description(
                agent_name="requirements_analyst",
                user_input=user_input,
                include_datetime=True
            )

        # 如果配置不存在，抛出错误
        if not task_description:
            raise ValueError(
                "❌ 配置文件中缺少 task_description_template 字段\n"
                "请确保配置文件包含完整的 task_description_template 字段。"
            )

        return task_description
    
    def execute(
        self,
        state: ProjectAnalysisState,
        config: RunnableConfig,
        store: Optional[BaseStore] = None
    ) -> AnalysisResult:
        """执行需求分析"""
        start_time = time.time()
        
        try:
            logger.info(f"Starting requirements analysis for session {state.get('session_id')}")
            
            # 验证输入
            if not self.validate_input(state):
                raise ValueError("Invalid input: user input is too short or empty")
            
            # 检索用户历史偏好（如果有store）
            user_context = ""
            if store and config.get("configurable", {}).get("user_id"):
                user_context = self._retrieve_user_preferences(store, config)
            
            # 准备消息
            messages = self.prepare_messages(state)
            
            # 添加用户偏好上下文
            if user_context:
                messages.append(HumanMessage(content=f"用户历史偏好：\n{user_context}"))
            
            # 调用LLM
            response = self.invoke_llm(messages)
            
            # 解析结构化结果
            structured_requirements = self._parse_requirements(response.content)

            # 🆕 v7.3: 问卷生成已分离到专门节点，此处不再处理问卷
            # 原因：只有充分分析才能指导问卷的生成
            # 新架构：需求分析（专注分析）→ calibration_questionnaire节点（动态生成问卷）

            # 向后兼容：如果LLM仍然返回了calibration_questionnaire字段（旧模型或缓存），保留但标记为待替换
            if "calibration_questionnaire" in structured_requirements:
                logger.info("ℹ️ 检测到LLM返回了calibration_questionnaire（旧行为），将保留但由专门节点重新生成")
                structured_requirements["calibration_questionnaire"]["source"] = "llm_legacy"
                structured_requirements["calibration_questionnaire"]["note"] = "此问卷将被专门节点重新生成"
            
            # 保存用户偏好（如果有新的偏好信息）
            if store and config.get("configurable", {}).get("user_id"):
                self._save_user_preferences(store, config, structured_requirements)
            
            # 创建分析结果
            result = self.create_analysis_result(
                content=response.content,
                structured_data=structured_requirements,
                confidence=self._calculate_confidence(structured_requirements),
                sources=["user_input", "llm_analysis"]
            )
            
            end_time = time.time()
            self._track_execution_time(start_time, end_time)
            
            logger.info("Requirements analysis completed successfully")
            return result
            
        except Exception as e:
            error = self.handle_error(e, "requirements analysis")
            raise error
    
    def _parse_requirements(self, llm_response: str) -> Dict[str, Any]:
        """解析LLM响应中的结构化需求 - 支持v1.0格式 - v3.6修复JSON解析"""
        try:
            # 🔥 v3.6优化：使用多种方法提取JSON，防止内容截断
            json_str = None

            # 方法1: 尝试提取JSON代码块（支持markdown code fence）
            import re
            json_pattern = r'```json\s*\n(.*?)\n```'
            match = re.search(json_pattern, llm_response, re.DOTALL)
            if match:
                json_str = match.group(1)
                logger.info("[JSON解析] ✅ 使用code fence提取")

            # 方法2: 尝试提取 ```{ ... }``` 格式（无json标记）
            if not json_str:
                code_block_pattern = r'```\s*\n(\{.*?\})\n```'
                match = re.search(code_block_pattern, llm_response, re.DOTALL)
                if match:
                    json_str = match.group(1)
                    logger.info("[JSON解析] ✅ 使用无标记代码块提取")

            # 方法3: 使用栈匹配法找到完整JSON（平衡大括号）
            if not json_str:
                json_str = self._extract_balanced_json(llm_response)
                if json_str:
                    logger.info("[JSON解析] ✅ 使用平衡括号提取")

            # 方法4: 🆕 尝试查找最大的JSON对象（从第一个{到最后一个}）
            if not json_str:
                first_brace = llm_response.find('{')
                last_brace = llm_response.rfind('}')
                if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                    json_candidate = llm_response[first_brace:last_brace+1]
                    # 尝试解析验证
                    try:
                        json.loads(json_candidate)
                        json_str = json_candidate
                        logger.info("[JSON解析] ✅ 使用首尾括号提取并验证成功")
                    except:
                        logger.warning("[JSON解析] ⚠️ 首尾括号提取验证失败")

            # 如果所有方法都失败
            if not json_str:
                logger.warning("[JSON解析] ⚠️ 所有提取方法失败，使用fallback")
                logger.debug(f"[JSON解析] LLM响应前200字符: {llm_response[:200]}")
                logger.debug(f"[JSON解析] LLM响应后200字符: {llm_response[-200:]}")
                # 🔥 v3.6调试：保存完整响应以便分析
                try:
                    import os
                    from datetime import datetime
                    debug_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "debug")
                    os.makedirs(debug_dir, exist_ok=True)
                    debug_file = os.path.join(debug_dir, f"llm_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(llm_response)
                    logger.info(f"[JSON解析] 完整LLM响应已保存到: {debug_file}")
                except Exception as save_error:
                    logger.warning(f"[JSON解析] 无法保存调试文件: {save_error}")

            if json_str:
                structured_data = json.loads(json_str)
                logger.info(f"[JSON解析] ✅ 成功解析，包含 {len(structured_data)} 个字段")
            else:
                # 如果没有找到JSON，创建基础结构
                structured_data = self._create_fallback_structure(llm_response)

            # 验证新格式的必需字段
            new_format_fields = [
                "project_task", "character_narrative", "space_constraints",
                "inspiration_references", "experience_behavior", "core_tension"
            ]

            # 检查是否是新格式
            is_new_format = any(field in structured_data for field in new_format_fields)

            if is_new_format:
                # 新格式（v2.0）：验证并填充缺失字段
                for field in new_format_fields:
                    if field not in structured_data:
                        structured_data[field] = "待进一步分析"

                # 🆕 v7.3: 问卷生成已分离，此处不再验证和修正问卷
                # 原因：问卷应在深度分析完成后，由专门节点基于分析结果动态生成
                # 旧逻辑（_validate_and_fix_questionnaire）已弃用，问卷生成移至 calibration_questionnaire.py

                # 向后兼容：如果存在旧问卷字段，保留但标记
                if "calibration_questionnaire" in structured_data:
                    logger.info("ℹ️ 检测到旧问卷字段，将由专门节点重新生成")
                    structured_data["calibration_questionnaire"]["source"] = "to_be_regenerated"

                # 🆕 v7.2: 构建完整的6字段数据结构（用于前端展示）
                # 从旧字段映射到新字段，确保前端能正确显示所有内容
                project_task = structured_data.get("project_task", "")
                character_narrative = structured_data.get("character_narrative", "")
                physical_context = structured_data.get("physical_context", "")
                resource_constraints = structured_data.get("resource_constraints", "")
                regulatory_requirements = structured_data.get("regulatory_requirements", "")
                
                # 1. project_overview: 项目概览（直接使用 project_task）
                structured_data["project_overview"] = project_task
                
                # 2. core_objectives: 核心目标（从 project_task 提取，或使用 design_goals）
                design_goals = structured_data.get("design_goals", "")
                if design_goals and len(design_goals) > 20:
                    # 如果有 design_goals，按句号分割为列表
                    goals_list = [g.strip() for g in design_goals.split('。') if g.strip() and len(g.strip()) > 5]
                    structured_data["core_objectives"] = goals_list[:5]  # 最多5个目标
                elif project_task and len(project_task) > 50:
                    # 从 project_task 提取核心目标
                    core_obj = project_task[:80].strip()
                    if '，' in core_obj or '。' in core_obj:
                        core_obj = core_obj.split('，')[0].split('。')[0]
                    structured_data["core_objectives"] = [core_obj]
                else:
                    structured_data["core_objectives"] = [project_task] if project_task else []
                
                # 3. project_tasks: 项目任务（从 project_task 提取关键词，或使用 functional_requirements）
                functional_req = structured_data.get("functional_requirements", "")
                if functional_req and len(functional_req) > 20:
                    # 按句号/分号分割功能需求为任务列表
                    tasks_list = [t.strip() for t in functional_req.replace('；', '。').split('。') if t.strip() and len(t.strip()) > 5]
                    structured_data["project_tasks"] = tasks_list[:8]  # 最多8个任务
                else:
                    # 默认从 project_task 提取一个任务
                    structured_data["project_tasks"] = [project_task] if project_task else []
                
                # 4. narrative_characters: 叙事角色（从 character_narrative 分段提取）
                if character_narrative and len(character_narrative) > 20:
                    # 按 "→" 或 "、" 分割人物叙事
                    if '→' in character_narrative:
                        char_list = [c.strip() for c in character_narrative.split('→') if c.strip()]
                        structured_data["narrative_characters"] = char_list[:6]  # 最多6个阶段
                    elif '、' in character_narrative:
                        char_list = [c.strip() for c in character_narrative.split('、') if c.strip()]
                        structured_data["narrative_characters"] = char_list[:6]
                    else:
                        # 整段作为一个角色描述
                        structured_data["narrative_characters"] = [character_narrative]
                else:
                    structured_data["narrative_characters"] = [character_narrative] if character_narrative else []
                
                # 5. physical_contexts: 物理环境（从 physical_context 分句提取）
                if physical_context and len(physical_context) > 20:
                    # 按逗号/句号分割物理环境
                    context_list = [c.strip() for c in physical_context.replace('，', '。').split('。') if c.strip() and len(c.strip()) > 5]
                    structured_data["physical_contexts"] = context_list[:6]  # 最多6个环境
                else:
                    structured_data["physical_contexts"] = [physical_context] if physical_context else []
                
                # 6. constraints_opportunities: 约束与机遇（结构化对象）
                space_constraints = structured_data.get("space_constraints", "")
                core_tension = structured_data.get("core_tension", "")
                design_challenge = structured_data.get("design_challenge", "")
                inspiration_refs = structured_data.get("inspiration_references", "")
                
                # 约束类字段（按重要性分句）
                constraints_parts = []
                if resource_constraints:
                    constraints_parts.append(f"资源约束：{resource_constraints}")
                if regulatory_requirements:
                    constraints_parts.append(f"规范要求：{regulatory_requirements}")
                if space_constraints:
                    constraints_parts.append(f"空间约束：{space_constraints}")
                if core_tension:
                    constraints_parts.append(f"核心矛盾：{core_tension}")
                
                # 机遇类字段
                opportunities_parts = []
                if design_challenge:
                    opportunities_parts.append(f"设计挑战：{design_challenge}")
                if inspiration_refs:
                    opportunities_parts.append(f"灵感参考：{inspiration_refs}")
                
                structured_data["constraints_opportunities"] = {
                    "constraints": constraints_parts if constraints_parts else ["暂无明确约束"],
                    "opportunities": opportunities_parts if opportunities_parts else ["待发掘机遇"]
                }
                
                # 兼容旧格式：保留旧字段（用于其他可能依赖旧字段的模块）
                structured_data["target_users"] = character_narrative[:100].strip() if character_narrative else ""
                physical = physical_context
                resource = resource_constraints
                regulatory = regulatory_requirements
                combined_constraints = f"{physical} {resource} {regulatory}".strip()
                structured_data["constraints"] = {"description": combined_constraints}
            else:
                # 旧格式：验证旧字段
                old_format_fields = [
                    "project_overview", "core_objectives", "functional_requirements",
                    "target_users", "constraints"
                ]

                for field in old_format_fields:
                    if field not in structured_data:
                        structured_data[field] = "待进一步分析"

            self._normalize_jtbd_fields(structured_data)
            
            # 🆕 推断项目类型（用于本体论注入）
            project_type = self._infer_project_type(structured_data)
            structured_data["project_type"] = project_type
            
            return structured_data

        except json.JSONDecodeError as e:
            logger.error(f"[JSON解析] ❌ JSONDecodeError: {str(e)}")
            logger.error(f"[JSON解析] 问题位置: line {e.lineno}, col {e.colno}")
            if json_str:
                # 显示错误前后的文本片段
                error_pos = getattr(e, 'pos', 0)
                start_pos = max(0, error_pos - 50)
                end_pos = min(len(json_str), error_pos + 50)
                logger.error(f"[JSON解析] 前后文本: ...{json_str[start_pos:end_pos]}...")
            logger.warning("[JSON解析] 使用fallback结构")
            return self._create_fallback_structure(llm_response)
        except Exception as e:
            logger.error(f"[JSON解析] ❌ 未知错误: {str(e)}")
            logger.warning("[JSON解析] 使用fallback结构")
            return self._create_fallback_structure(llm_response)

    def _extract_balanced_json(self, text: str) -> str | None:
        """
        使用栈匹配法提取完整的JSON对象

        🔥 v3.6新增：防止简单的find('{')和rfind('}')在遇到嵌套JSON或字符串中的大括号时失败

        Args:
            text: 包含JSON的文本

        Returns:
            完整的JSON字符串，如果未找到则返回None
        """
        start_idx = text.find('{')
        if start_idx == -1:
            return None

        stack = []
        in_string = False
        escape = False

        for i in range(start_idx, len(text)):
            ch = text[i]

            # 处理转义字符
            if escape:
                escape = False
                continue
            if ch == '\\':
                escape = True
                continue

            # 处理字符串状态（只在双引号时切换）
            if ch == '"':
                in_string = not in_string
                continue

            # 只在非字符串状态下处理括号
            if not in_string:
                if ch == '{':
                    stack.append(ch)
                elif ch == '}':
                    if stack:
                        stack.pop()
                    if not stack:  # 栈空，找到完整JSON
                        json_candidate = text[start_idx:i+1]
                        logger.info(f"[JSON解析] 平衡括号提取成功，长度: {len(json_candidate)} 字符")
                        return json_candidate

        logger.warning("[JSON解析] 未找到平衡的JSON结构")
        return None

    def _create_fallback_structure(self, content: str) -> Dict[str, Any]:
        """创建备用的结构化数据 - 支持新格式"""
        return {
            # 新格式字段
            "project_task": content[:500] + "..." if len(content) > 500 else content,
            "character_narrative": "待进一步分析核心人物特征",
            "physical_context": "待明确物理环境条件",
            "resource_constraints": "待明确资源限制",
            "regulatory_requirements": "待明确规范要求",
            "inspiration_references": "【待后续专家补齐】V4设计研究员将提供国际案例参考，V5场景专家将结合行业趋势补充灵感来源",
            "experience_behavior": "【待后续专家补齐】V3叙事专家将构建完整用户旅程，V5场景专家将细化典型使用场景",
            "design_challenge": "待识别设计挑战",
            "calibration_questionnaire": {
                "introduction": "以下问题旨在精准捕捉您在战术执行和美学表达层面的个人偏好",
                "questions": []
            },
            # 兼容旧格式字段
            "project_overview": content[:500] + "..." if len(content) > 500 else content,
            "core_objectives": ["基于用户描述的项目目标"],
            "functional_requirements": ["待详细分析"],
            "non_functional_requirements": {"performance": "待定义", "security": "待定义"},
            "target_users": "待识别",
            "use_cases": ["主要使用场景待分析"],
            "constraints": {"budget": "未明确", "timeline": "未明确", "technology": "未明确"},
            "assumptions": ["基于当前信息的假设"],
            "risks": ["待识别潜在风险"],
            "success_criteria": ["待定义成功标准"],
            "raw_analysis": content
        }

    def _normalize_jtbd_fields(self, structured_data: Dict[str, Any]) -> None:
        """将 JTBD 相关字段转换为自然语言，避免在 UI 中出现公式术语"""
        if not structured_data:
            return

        for field in ["project_task", "project_overview"]:
            value = structured_data.get(field)
            if isinstance(value, str):
                structured_data[field] = transform_jtbd_to_natural_language(value)

        core_objectives = structured_data.get("core_objectives")
        if isinstance(core_objectives, list):
            structured_data["core_objectives"] = [
                transform_jtbd_to_natural_language(obj) if isinstance(obj, str) else obj
                for obj in core_objectives
            ]

    def _validate_and_fix_questionnaire(self, structured_data: Dict[str, Any]) -> None:
        """
        🚫 v7.3 已废弃：此方法不再使用

        原因：问卷生成已分离到专门节点
        - 旧架构：需求分析师在单次LLM调用中同时生成分析结果和问卷，然后验证修正问卷
        - 新架构：需求分析师专注于深度分析，问卷由 calibration_questionnaire.py 节点基于分析结果动态生成

        迁移说明：
        - 问卷生成逻辑已迁移至 intelligent_project_analyzer/interaction/questionnaire/
        - 包含多个专门生成器：FallbackQuestionGenerator, PhilosophyQuestionGenerator 等

        向后兼容：保留此方法存根，避免旧代码调用时报错
        """
        logger.warning("[DEPRECATED] _validate_and_fix_questionnaire 已废弃，问卷生成已移至专门节点")
        return  # 空实现，直接返回

    def _validate_and_fix_questionnaire_legacy(self, structured_data: Dict[str, Any]) -> None:
        """
        [已废弃] 旧版问卷验证逻辑 - 仅保留作为参考
        1. 必须生成 7-10个问题（禁止只生成2-3个）
        2. 题型顺序：单选题(2-3个) → 多选题(2-3个) → 开放题(2个)
        3. 从用户输入中智能生成问题，而不是使用通用模板
        """
        questionnaire = structured_data.get("calibration_questionnaire", {})
        questions = questionnaire.get("questions", [])

        # 统计各类题型数量
        single_choice_count = sum(1 for q in questions if q.get("type") == "single_choice")
        multiple_choice_count = sum(1 for q in questions if q.get("type") == "multiple_choice")
        open_ended_count = sum(1 for q in questions if q.get("type") == "open_ended")
        total_count = len(questions)

        logger.info(f"[问卷验证] 当前问卷: 总数={total_count}, 单选={single_choice_count}, 多选={multiple_choice_count}, 开放={open_ended_count}")

        # 检查是否需要修正
        needs_fix = (
            total_count < 7 or  # 少于7个问题
            single_choice_count < 2 or  # 单选题少于2个
            multiple_choice_count < 2 or  # 多选题少于2个
            open_ended_count < 2  # 开放题少于2个
        )

        if not needs_fix:
            logger.info("[问卷验证] ✅ 问卷结构符合要求")
            return

        logger.warning(f"[问卷验证] ❌ 问卷不符合要求，开始智能补齐...")

        # 🔥 智能补齐：从用户输入和已分析的结构化数据中提取关键信息
        project_task = structured_data.get("project_task", "")
        character_narrative = structured_data.get("character_narrative", "")
        design_challenge = structured_data.get("design_challenge", "")
        physical_context = structured_data.get("physical_context", "")
        resource_constraints = structured_data.get("resource_constraints", "")

        # 提取核心矛盾（从design_challenge中）
        tension_a = "功能性需求"
        tension_b = "情感化需求"

        # 🔍 尝试多种正则模式匹配核心矛盾
        import re

        # 模式1: "A"...与..."B" 格式（中文引号）
        match = re.search(r'"([^"]{2,30?})"[^"]{0,50?}与[^"]{0,50?}"([^"]{2,30?})"', design_challenge)
        if match:
            tension_a = match.group(1).strip()
            tension_b = match.group(2).strip()
            logger.info(f"[矛盾提取] 使用模式1: \"{tension_a}\" vs \"{tension_b}\"")
        else:
            # 模式2: A vs B 或 A与其对B 格式
            match = re.search(r'(.{5,30}?)[的需求]*(?:vs|与其对)(.{5,30}?)[的需求]*', design_challenge)
            if match:
                tension_a = match.group(1).strip()
                tension_b = match.group(2).strip()
                logger.info(f"[矛盾提取] 使用模式2: {tension_a} vs {tension_b}")

        # 提取项目类型关键词
        project_type = structured_data.get("project_type", "personal_residential")
        is_residential = "residential" in project_type
        is_commercial = "commercial" in project_type

        # 分离现有问题
        existing_single = [q for q in questions if q.get("type") == "single_choice"]
        existing_multiple = [q for q in questions if q.get("type") == "multiple_choice"]
        existing_open = [q for q in questions if q.get("type") == "open_ended"]

        # 🎯 补充单选题（确保至少2个）- 从核心矛盾生成（概念阶段友好版）
        while len(existing_single) < 2:
            template_idx = len(existing_single)
            if template_idx == 0 and tension_a and tension_b and tension_a != "功能性需求" and tension_b != "情感化需求":
                # 如果成功提取了具体的核心矛盾（非默认值），使用具体问题
                existing_single.append({
                    "question": f"当{tension_a}与{tension_b}产生冲突时，您更倾向于？(单选)",
                    "context": f"这是本项目最核心的战略选择，将决定设计的根本方向。",
                    "type": "single_choice",
                    "options": [
                        f"优先保证{tension_a}，可以在{tension_b}上做出妥协",
                        f"优先保证{tension_b}，{tension_a}可以通过其他方式补偿",
                        f"寻求平衡点，通过创新设计同时满足两者"
                    ]
                })
            elif template_idx == 0:
                # 第一个兜底：适合概念阶段的开放性问题
                existing_single.append({
                    "question": "您希望这个空间首先给人什么样的感觉？(单选)",
                    "context": "帮助我们确定设计的核心情感基调，这将指导所有后续决策。",
                    "type": "single_choice",
                    "options": [
                        "温暖舒适：像家一样放松自在",
                        "简洁高效：专注于功能和效率",
                        "独特个性：表达自我和品味",
                        "平衡包容：兼顾多种需求和场景"
                    ]
                })
            elif template_idx == 1 and resource_constraints and len(resource_constraints) > 10:
                # 如果有明确的资源约束，使用具体问题
                existing_single.append({
                    "question": f"面对{resource_constraints}的限制，您的取舍策略是？(单选)",
                    "context": "帮助我们在资源有限时做出明智的优先级决策。",
                    "type": "single_choice",
                    "options": [
                        "集中资源打造核心体验区，其他区域从简",
                        "平均分配，确保整体协调统一",
                        "先满足基本功能，预留后期升级空间"
                    ]
                })
            else:
                # 第二个兜底：关于设计优先级的探索性问题
                existing_single.append({
                    "question": "在设计决策中，您认为什么最不能妥协？(单选)",
                    "context": "识别您的核心价值观，确保设计不会偏离最重要的诉求。",
                    "type": "single_choice",
                    "options": [
                        "使用便利性：日常生活流畅无阻",
                        "美学品质：视觉和感官的愉悦",
                        "长期价值：经得起时间考验",
                        "创新突破：与众不同的独特体验"
                    ]
                })

        # 🎯 补充多选题（确保至少2个）- 真正需要思考的选择（非常识性问题）
        while len(existing_multiple) < 2:
            template_idx = len(existing_multiple)
            if template_idx == 0:
                # 第一个多选：关于空间使用节奏和时间感
                if is_residential:
                    existing_multiple.append({
                        "question": "以下哪些时刻/场景，您希望空间能特别支持？(多选)",
                        "context": "帮助我们理解您的生活节奏和关键场景，设计会围绕这些时刻展开。",
                        "type": "multiple_choice",
                        "options": [
                            "清晨独处：沉思、阅读或运动的私密时光",
                            "工作专注：需要高度集中的深度工作时段",
                            "家庭互动：与家人共度的温馨时刻",
                            "社交娱乐：接待朋友或举办聚会",
                            "夜间放松：卸下一天疲惫的独处时光",
                            "灵活切换：在多种状态间快速转换"
                        ]
                    })
                elif is_commercial:
                    existing_multiple.append({
                        "question": "以下哪些体验场景，您希望空间能特别强化？(多选)",
                        "context": "商业空间的成功在于关键场景的极致体验，请选择您认为最重要的。",
                        "type": "multiple_choice",
                        "options": [
                            "初次相遇：第一印象和品牌感知的黄金时刻",
                            "核心体验：用户使用核心功能/服务的关键时刻",
                            "情感共鸣：建立品牌认同和情感连接的时刻",
                            "高效流转：用户完成目标的流畅度和效率",
                            "停留驻足：让用户愿意多待一会儿的吸引力",
                            "记忆锚点：离开后仍能回想起的独特体验"
                        ]
                    })
                else:
                    existing_multiple.append({
                        "question": "您希望这个空间在哪些方面超出常规？(多选)",
                        "context": "帮助我们识别您的独特诉求，避免设计成千篇一律的标准方案。",
                        "type": "multiple_choice",
                        "options": [
                            "感官体验：光影/材质/声音等超越常规的感官设计",
                            "空间叙事：有故事性和情感深度的空间序列",
                            "功能创新：打破常规的使用方式或空间组织",
                            "可持续性：环保、节能或与自然的深度连接",
                            "技术融合：智能化或新技术的巧妙应用",
                            "文化表达：特定文化/艺术的深度体现"
                        ]
                    })
            else:
                # 第二个多选：关于设计过程中的价值排序
                if is_residential:
                    existing_multiple.append({
                        "question": "当预算/时间有限需要取舍时，以下哪些您愿意优先保障？(多选)",
                        "context": "这不是理想状态的全部需求，而是帮助我们理解您真正的优先级。",
                        "type": "multiple_choice",
                        "options": [
                            "结构优化：动线/采光/通风等基础体验的优化",
                            "材质品质：关键区域使用更好的材料",
                            "定制设计：为特殊需求专门设计的功能",
                            "储物系统：充足且合理的收纳解决方案",
                            "氛围营造：灯光/色彩/艺术品等氛围要素",
                            "智能集成：智能家居或自动化系统"
                        ]
                    })
                elif is_commercial:
                    existing_multiple.append({
                        "question": "在商业空间的投入分配上，您更倾向于加强哪些方面？(多选)",
                        "context": "帮助我们理解您的商业策略和价值取向，优化资源配置。",
                        "type": "multiple_choice",
                        "options": [
                            "门面形象：外立面/入口等第一印象的投入",
                            "核心区域：最关键功能区的品质提升",
                            "品牌氛围：整体调性和品牌表达的完整性",
                            "运营灵活：后期调整和多场景适配的能力",
                            "体验细节：小而美的触点设计和惊喜时刻",
                            "长期耐用：材料/设备的品质和维护成本控制"
                        ]
                    })
                else:
                    existing_multiple.append({
                        "question": "以下哪些因素会显著影响您对最终方案的满意度？(多选)",
                        "context": "帮助我们理解您的评判标准，确保设计方向符合您的预期。",
                        "type": "multiple_choice",
                        "options": [
                            "视觉完成度：呈现效果与预期的一致性",
                            "功能完整性：所需功能的实现程度",
                            "使用便利性：日常使用的舒适和流畅",
                            "独特性：与其他项目的差异化",
                            "可持续性：长期使用和维护的合理性",
                            "成本控制：在预算范围内的实现程度"
                        ]
                    })

        # 🎯 补充开放题（确保至少2个）- 捕捉深层需求（概念阶段友好版）
        while len(existing_open) < 2:
            template_idx = len(existing_open)
            if template_idx == 0:
                # 第一个开放题：关于理想状态的想象
                existing_open.append({
                    "question": "请描述一个让您印象深刻的空间体验（可以是任何地方），以及它打动您的特质。(开放题)",
                    "context": "这将成为设计的'精神参考'，帮助我们理解您追求的空间品质。",
                    "type": "open_ended"
                })
            else:
                # 第二个开放题：关于使用者的真实状态
                if is_residential:
                    existing_open.append({
                        "question": "在您设想的日常生活中，有哪些时刻或场景是特别重要的？(开放题)",
                        "context": "不必是「早晨」或「夜晚」这样的具体时间，可以是任何对您有意义的状态或场景。",
                        "type": "open_ended"
                    })
                elif is_commercial:
                    existing_open.append({
                        "question": "您希望用户/客户在这个空间中经历怎样的体验旅程？(开放题)",
                        "context": "从进入到离开，描述您理想中的体验过程和关键感受。",
                        "type": "open_ended"
                    })
                else:
                    existing_open.append({
                        "question": "如果用三个关键词描述您理想中的空间，会是什么？请简单解释原因。(开放题)",
                        "context": "帮助我们快速把握您的核心诉求和价值取向。",
                        "type": "open_ended"
                    })

        # 按照要求的顺序重新组织问题：单选 → 多选 → 开放
        fixed_questions = existing_single + existing_multiple + existing_open

        logger.info(f"[问卷验证] ✅ 智能补齐完成: 总数={len(fixed_questions)}, 单选={len(existing_single)}, 多选={len(existing_multiple)}, 开放={len(existing_open)}")
        logger.info(f"[问卷验证] 📊 补齐策略: 基于用户输入的核心矛盾({tension_a} vs {tension_b})和项目类型({project_type})生成")

        # 更新问卷
        structured_data["calibration_questionnaire"]["questions"] = fixed_questions
    
    def _infer_project_type(self, structured_data: Dict[str, Any]) -> str:
        """
        推断项目类型（用于本体论注入）
        
        根据需求内容中的关键词匹配，识别项目类型：
        - personal_residential: 个人/家庭住宅类项目
        - hybrid_residential_commercial: 混合型（住宅+商业）
        - commercial_enterprise: 纯商业/企业级项目
        
        Returns:
            项目类型标识字符串
        """
        # 提取所有文本内容进行关键词匹配
        all_text = " ".join([
            str(structured_data.get("project_task", "")),
            str(structured_data.get("character_narrative", "")),
            str(structured_data.get("project_overview", "")),
            str(structured_data.get("target_users", "")),
        ]).lower()
        
        # 定义关键词集合（按优先级）
        personal_keywords = [
            "住宅", "家", "公寓", "别墅", "房子", "居住", "卧室", "客厅", 
            "家庭", "个人", "私宅", "家居", "户型", "住房", "民宿"
        ]
        
        commercial_keywords = [
            # 办公类
            "办公", "商业", "企业", "公司", "写字楼", "工作室", "创意园", "产业园", "厂房", "仓储", "品牌", "连锁",
            # 零售/展示类
            "店铺", "商店", "展厅", "零售", "购物", "商场", "专卖店", "旗舰店", "体验店",
            # 餐饮类
            "餐厅", "餐饮", "中餐", "西餐", "日料", "包房", "包间", "宴会厅", "食堂", "茶餐厅",
            "咖啡", "咖啡厅", "咖啡馆", "茶室", "茶馆", "酒吧", "清吧",
            # 住宿/会所类
            "酒店", "宾馆", "民宿", "会所", "俱乐部", "会议室",
            # 🔥 公共/市政类（城市更新、菜市场等）
            "菜市场", "市场", "农贸市场", "集市", "城市更新", "旧改", "改造", "公共空间",
            "社区中心", "文化中心", "活动中心", "体育馆", "图书馆", "博物馆", "美术馆",
            "标杆", "示范", "地标", "城市名片",
            # 🔥 文化/体验类
            "文化", "传统", "渔村", "历史", "遗产", "非遗", "民俗", "在地文化",
            # 🔥 教育/医疗/健康类
            "学校", "教育", "培训", "幼儿园", "早教", "托育",
            "医院", "诊所", "医疗", "养老院", "康养", "健康中心", "体检中心", "康复中心",
            "健康管理", "健康", "医美", "理疗", "养生", "保健",
            # 🔥 商业运营类（强烈表明是商业项目）
            "经营", "运营", "市场营销", "营销", "用户体验", "商业模式", "盈利"
        ]
        
        # 统计关键词命中数
        personal_score = sum(1 for kw in personal_keywords if kw in all_text)
        commercial_score = sum(1 for kw in commercial_keywords if kw in all_text)
        
        logger.info(f"[项目类型推断] 个人/住宅得分: {personal_score}, 商业/企业得分: {commercial_score}")
        
        # 判定逻辑
        if personal_score > 0 and commercial_score > 0:
            # 同时包含住宅和商业关键词
            logger.info("[项目类型推断] 识别为混合型项目 (hybrid_residential_commercial)")
            return "hybrid_residential_commercial"
        elif personal_score > commercial_score:
            # 主要是住宅类关键词
            logger.info("[项目类型推断] 识别为个人/住宅项目 (personal_residential)")
            return "personal_residential"
        elif commercial_score > personal_score:
            # 主要是商业类关键词
            logger.info("[项目类型推断] 识别为商业/企业项目 (commercial_enterprise)")
            return "commercial_enterprise"
        else:
            # 未命中任何关键词，返回 None（将触发 meta_framework）
            logger.warning("[项目类型推断] 无法识别项目类型，将使用通用框架 (meta_framework)")
            return None
    
    def _calculate_confidence(self, structured_data: Dict[str, Any]) -> float:
        """计算分析结果的置信度"""
        confidence_factors = []
        
        # 检查关键字段的完整性
        key_fields = ["project_overview", "core_objectives", "functional_requirements"]
        for field in key_fields:
            value = structured_data.get(field, "")
            if isinstance(value, str) and len(value) > 20:
                confidence_factors.append(0.3)
            elif isinstance(value, list) and len(value) > 0:
                confidence_factors.append(0.3)
            else:
                confidence_factors.append(0.1)
        
        # 检查详细程度
        total_content_length = sum(
            len(str(v)) for v in structured_data.values()
        )
        if total_content_length > 1000:
            confidence_factors.append(0.1)
        
        return min(sum(confidence_factors), 1.0)
    
    def _retrieve_user_preferences(self, store: BaseStore, config: RunnableConfig) -> str:
        """检索用户历史偏好"""
        try:
            user_id = config["configurable"]["user_id"]
            namespace = ("user_preferences", user_id)
            
            # 搜索相关的用户偏好
            memories = store.search(namespace, limit=5)
            
            if memories:
                preferences = []
                for memory in memories:
                    if "preference" in memory.value:
                        preferences.append(memory.value["preference"])
                
                return "\n".join(preferences) if preferences else ""
            
            return ""
            
        except Exception as e:
            logger.warning(f"Failed to retrieve user preferences: {str(e)}")
            return ""
    
    def _save_user_preferences(
        self,
        store: BaseStore,
        config: RunnableConfig,
        structured_requirements: Dict[str, Any]
    ):
        """保存用户偏好"""
        try:
            user_id = config["configurable"]["user_id"]
            namespace = ("user_preferences", user_id)
            
            # 提取可能的偏好信息
            preferences = []
            
            # 从目标用户中提取偏好
            target_users = structured_requirements.get("target_users", "")
            if target_users and len(target_users) > 10:
                preferences.append(f"目标用户偏好: {target_users}")
            
            # 从约束条件中提取偏好
            constraints = structured_requirements.get("constraints", {})
            if isinstance(constraints, dict):
                for key, value in constraints.items():
                    if value and value != "未明确" and value != "待定义":
                        preferences.append(f"{key}偏好: {value}")
            
            # 保存偏好
            for i, preference in enumerate(preferences):
                memory_id = f"req_analysis_{int(time.time())}_{i}"
                store.put(namespace, memory_id, {
                    "preference": preference,
                    "source": "requirements_analysis",
                    "timestamp": time.time()
                })
            
        except Exception as e:
            logger.warning(f"Failed to save user preferences: {str(e)}")


# 注册智能体
from .base import AgentFactory
AgentFactory.register_agent(AgentType.REQUIREMENTS_ANALYST, RequirementsAnalystAgent)
