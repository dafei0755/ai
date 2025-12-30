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
from ..utils.capability_detector import CapabilityDetector, check_capability


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
        store: Optional[BaseStore] = None,
        use_two_phase: bool = False  # 🆕 v7.17: 支持两阶段模式
    ) -> AnalysisResult:
        """执行需求分析
        
        Args:
            state: 项目分析状态
            config: 运行配置
            store: 可选的存储后端
            use_two_phase: 是否使用两阶段模式（v7.17新增）
                - False: 单次LLM调用（默认，向后兼容）
                - True: Phase1（快速定性）→ Phase2（深度分析）
        """
        # 🆕 v7.17: 如果启用两阶段模式，使用新的执行流程
        if use_two_phase:
            return self._execute_two_phase(state, config, store)
        
        # 原有的单次调用逻辑
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

    # ═══════════════════════════════════════════════════════════════════════════
    # 🆕 v7.17 P1: 两阶段执行架构
    # Phase1: 快速定性 + 交付物识别 (~1.5s)
    # Phase2: 深度分析 + 专家接口构建 (~3s)
    # ═══════════════════════════════════════════════════════════════════════════

    def _execute_two_phase(
        self,
        state: ProjectAnalysisState,
        config: RunnableConfig,
        store: Optional[BaseStore] = None
    ) -> AnalysisResult:
        """🆕 v7.17: 两阶段执行模式
        
        Phase1: 快速定性 + 交付物识别（~1.5s）
        - L0 项目定性（信息充足/不足判断）
        - 交付物识别 + 能力边界判断
        - 输出: info_status, primary_deliverables, recommended_next_step
        
        Phase2: 深度分析 + 专家接口（~3s，仅当 Phase1 判断信息充足时）
        - L1-L5 深度分析
        - 专家接口构建
        - 输出: 完整的 structured_data + expert_handoff
        """
        start_time = time.time()
        session_id = state.get("session_id", "unknown")
        
        logger.info(f"🚀 [v7.17] 启动两阶段需求分析 (session: {session_id})")
        
        try:
            # 验证输入
            if not self.validate_input(state):
                raise ValueError("Invalid input: user input is too short or empty")
            
            user_input = state.get("user_input", "")
            
            # ═══════════════════════════════════════════════════════════════
            # 🆕 v7.17 P2: 程序化能力边界预检测
            # 在 LLM 调用前完成，减少 LLM 判断负担
            # ═══════════════════════════════════════════════════════════════
            precheck_start = time.time()
            logger.info("🔍 [预检测] 程序化能力边界检测...")
            
            capability_precheck = check_capability(user_input)
            precheck_elapsed = time.time() - precheck_start
            
            logger.info(f"✅ [预检测] 完成，耗时 {precheck_elapsed:.3f}s")
            logger.info(f"   - 信息充足: {capability_precheck['info_sufficiency']['is_sufficient']}")
            logger.info(f"   - 能力匹配: {capability_precheck['deliverable_capability']['capability_score']:.0%}")
            logger.info(f"   - 需要转化: {capability_precheck['deliverable_capability']['transformations_needed']}个")
            
            # ═══════════════════════════════════════════════════════════════
            # Phase 1: 快速定性 + 交付物识别（带预检测结果）
            # ═══════════════════════════════════════════════════════════════
            phase1_start = time.time()
            logger.info("📋 [Phase1] 开始快速定性 + 交付物识别...")
            
            phase1_result = self._execute_phase1(user_input, capability_precheck)
            
            phase1_elapsed = time.time() - phase1_start
            logger.info(f"✅ [Phase1] 完成，耗时 {phase1_elapsed:.2f}s")
            logger.info(f"   - info_status: {phase1_result.get('info_status')}")
            logger.info(f"   - deliverables: {len(phase1_result.get('primary_deliverables', []))}个")
            logger.info(f"   - next_step: {phase1_result.get('recommended_next_step')}")
            
            # 判断是否需要执行 Phase2
            info_status = phase1_result.get("info_status", "insufficient")
            recommended_next = phase1_result.get("recommended_next_step", "questionnaire_first")
            
            if info_status == "insufficient" or recommended_next == "questionnaire_first":
                # 信息不足，跳过 Phase2，直接返回 Phase1 结果
                logger.info("⚠️ [Phase1] 信息不足，跳过 Phase2，建议先收集问卷")
                
                structured_data = self._build_phase1_only_result(phase1_result, user_input)
                structured_data["analysis_mode"] = "phase1_only"
                structured_data["skip_phase2_reason"] = phase1_result.get("info_status_reason", "信息不足")
                
                result = self.create_analysis_result(
                    content=json.dumps(phase1_result, ensure_ascii=False, indent=2),
                    structured_data=structured_data,
                    confidence=0.5,  # Phase1 only 的置信度较低
                    sources=["user_input", "phase1_analysis"]
                )
                
                end_time = time.time()
                self._track_execution_time(start_time, end_time)
                logger.info(f"🏁 [v7.17] 两阶段分析完成（仅Phase1），总耗时 {end_time - start_time:.2f}s")
                
                return result
            
            # ═══════════════════════════════════════════════════════════════
            # Phase 2: 深度分析 + 专家接口
            # ═══════════════════════════════════════════════════════════════
            phase2_start = time.time()
            logger.info("🔬 [Phase2] 开始深度分析 + 专家接口构建...")
            
            phase2_result = self._execute_phase2(user_input, phase1_result)
            
            phase2_elapsed = time.time() - phase2_start
            logger.info(f"✅ [Phase2] 完成，耗时 {phase2_elapsed:.2f}s")
            
            # 合并 Phase1 和 Phase2 结果
            structured_data = self._merge_phase_results(phase1_result, phase2_result)
            structured_data["analysis_mode"] = "two_phase"
            structured_data["phase1_elapsed_s"] = round(phase1_elapsed, 2)
            structured_data["phase2_elapsed_s"] = round(phase2_elapsed, 2)
            
            # 后处理：字段规范化、项目类型推断
            self._normalize_jtbd_fields(structured_data)
            structured_data["project_type"] = self._infer_project_type(structured_data)
            
            # 创建分析结果
            confidence = self._calculate_two_phase_confidence(phase1_result, phase2_result)
            
            result = self.create_analysis_result(
                content=json.dumps(phase2_result, ensure_ascii=False, indent=2),
                structured_data=structured_data,
                confidence=confidence,
                sources=["user_input", "phase1_analysis", "phase2_analysis"]
            )
            
            end_time = time.time()
            self._track_execution_time(start_time, end_time)
            logger.info(f"🏁 [v7.17] 两阶段分析完成，总耗时 {end_time - start_time:.2f}s")
            
            return result
            
        except Exception as e:
            error = self.handle_error(e, "two-phase requirements analysis")
            raise error

    def _execute_phase1(self, user_input: str, capability_precheck: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行 Phase1: 快速定性 + 交付物识别
        
        Args:
            user_input: 用户输入文本
            capability_precheck: 程序化预检测结果（v7.17 P2）
        """
        # 加载 Phase1 专用提示词
        phase1_config = self.prompt_manager.get_prompt("requirements_analyst_phase1", return_full_config=True)
        
        if not phase1_config:
            logger.warning("[Phase1] 未找到专用配置，使用默认定性逻辑")
            return self._fallback_phase1(user_input, capability_precheck)
        
        system_prompt = phase1_config.get("system_prompt", "")
        task_template = phase1_config.get("task_description_template", "")
        
        # 构建任务描述
        from datetime import datetime
        datetime_info = f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}。"
        task_description = task_template.replace("{datetime_info}", datetime_info).replace("{user_input}", user_input)
        
        # 🆕 v7.17 P2: 将预检测结果注入到任务描述中
        if capability_precheck:
            precheck_hints = self._format_precheck_hints(capability_precheck)
            task_description = f"{precheck_hints}\n\n{task_description}"
        
        # 调用 LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task_description}
        ]
        
        response = self.invoke_llm(messages)
        
        # 解析 JSON
        try:
            result = self._parse_phase_response(response.content)
            result["phase"] = 1
            return result
        except Exception as e:
            logger.error(f"[Phase1] JSON解析失败: {e}")
            return self._fallback_phase1(user_input, capability_precheck)

    def _execute_phase2(self, user_input: str, phase1_result: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Phase2: 深度分析 + 专家接口构建"""
        # 加载 Phase2 专用提示词
        phase2_config = self.prompt_manager.get_prompt("requirements_analyst_phase2", return_full_config=True)
        
        if not phase2_config:
            logger.warning("[Phase2] 未找到专用配置，使用默认分析逻辑")
            return self._fallback_phase2(user_input, phase1_result)
        
        system_prompt = phase2_config.get("system_prompt", "")
        task_template = phase2_config.get("task_description_template", "")
        
        # 构建任务描述（包含 Phase1 输出）
        from datetime import datetime
        datetime_info = f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}。"
        phase1_output_str = json.dumps(phase1_result, ensure_ascii=False, indent=2)
        
        task_description = (
            task_template
            .replace("{datetime_info}", datetime_info)
            .replace("{user_input}", user_input)
            .replace("{phase1_output}", phase1_output_str)
        )
        
        # 调用 LLM
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task_description}
        ]
        
        response = self.invoke_llm(messages)
        
        # 解析 JSON
        try:
            result = self._parse_phase_response(response.content)
            result["phase"] = 2
            return result
        except Exception as e:
            logger.error(f"[Phase2] JSON解析失败: {e}")
            return self._fallback_phase2(user_input, phase1_result)

    def _parse_phase_response(self, response: str) -> Dict[str, Any]:
        """解析阶段响应的 JSON"""
        # 复用已有的 JSON 提取逻辑
        json_str = self._extract_balanced_json(response)
        if json_str:
            return json.loads(json_str)
        
        # 尝试首尾括号提取
        first_brace = response.find('{')
        last_brace = response.rfind('}')
        if first_brace != -1 and last_brace != -1:
            return json.loads(response[first_brace:last_brace+1])
        
        raise ValueError("无法从响应中提取 JSON")

    def _fallback_phase1(self, user_input: str, capability_precheck: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Phase1 降级逻辑 - 使用程序化预检测结果（v7.17 P2 增强）"""
        
        # 如果有预检测结果，优先使用
        if capability_precheck:
            info_suff = capability_precheck.get("info_sufficiency", {})
            deliv_cap = capability_precheck.get("deliverable_capability", {})
            capable_deliverables = capability_precheck.get("capable_deliverables", [])
            transformations = capability_precheck.get("transformations", [])
            
            info_sufficient = info_suff.get("is_sufficient", False)
            
            # 构建交付物列表
            primary_deliverables = []
            
            # 添加能力范围内的交付物
            for i, d in enumerate(capable_deliverables[:3]):
                primary_deliverables.append({
                    "deliverable_id": f"D{i+1}",
                    "type": d.get("type", "design_strategy"),
                    "description": f"基于关键词 {d.get('keywords', [])} 识别",
                    "priority": "MUST_HAVE",
                    "capability_check": {"within_capability": True}
                })
            
            # 添加需要转化的交付物
            for i, t in enumerate(transformations[:2]):
                primary_deliverables.append({
                    "deliverable_id": f"D{len(capable_deliverables)+i+1}",
                    "type": t.get("transformed_to", "design_strategy"),
                    "description": t.get("reason", ""),
                    "priority": "NICE_TO_HAVE",
                    "capability_check": {
                        "within_capability": False,
                        "original_request": t.get("original", ""),
                        "transformed_to": t.get("transformed_to", "")
                    }
                })
            
            # 确保至少有一个交付物
            if not primary_deliverables:
                primary_deliverables.append({
                    "deliverable_id": "D1",
                    "type": "design_strategy",
                    "description": "设计策略文档",
                    "priority": "MUST_HAVE",
                    "capability_check": {"within_capability": True}
                })
            
            return {
                "phase": 1,
                "info_status": "sufficient" if info_sufficient else "insufficient",
                "info_status_reason": info_suff.get("reason", "基于程序化检测"),
                "info_gaps": info_suff.get("missing_elements", []),
                "project_type_preliminary": "personal_residential",
                "project_summary": user_input[:50] + "...",
                "primary_deliverables": primary_deliverables,
                "recommended_next_step": capability_precheck.get("recommended_action", "questionnaire_first"),
                "precheck_based": True,
                "fallback": True
            }
        
        # 兜底：简单规则判断（无预检测结果时）
        word_count = len(user_input)
        has_numbers = any(c.isdigit() for c in user_input)
        has_location = any(kw in user_input for kw in ["平米", "㎡", "房间", "卧室", "客厅"])
        
        info_sufficient = word_count > 100 and (has_numbers or has_location)
        
        return {
            "phase": 1,
            "info_status": "sufficient" if info_sufficient else "insufficient",
            "info_status_reason": "基于规则判断" if info_sufficient else "信息量不足，建议补充",
            "info_gaps": [] if info_sufficient else ["项目类型", "空间约束", "预算范围"],
            "project_type_preliminary": "personal_residential",
            "project_summary": user_input[:50] + "...",
            "primary_deliverables": [{
                "deliverable_id": "D1",
                "type": "design_strategy",
                "description": "设计策略文档",
                "priority": "MUST_HAVE",
                "capability_check": {"within_capability": True}
            }],
            "recommended_next_step": "phase2_analysis" if info_sufficient else "questionnaire_first",
            "fallback": True
        }

    def _format_precheck_hints(self, capability_precheck: Dict[str, Any]) -> str:
        """
        格式化程序化预检测结果为 LLM 提示
        
        v7.17 P2: 将预检测结果注入到 Phase1 任务描述中，
        减少 LLM 的判断负担，提高一致性
        """
        hints = ["### 🔍 程序化预检测结果（已完成，请参考）"]
        
        # 信息充足性提示
        info_suff = capability_precheck.get("info_sufficiency", {})
        if info_suff.get("is_sufficient"):
            hints.append(f"✅ **信息充足性**: 充足（得分 {info_suff.get('score', 0):.2f}）")
            hints.append(f"   - 已识别: {', '.join(info_suff.get('present_elements', []))}")
        else:
            hints.append(f"⚠️ **信息充足性**: 不足（得分 {info_suff.get('score', 0):.2f}）")
            hints.append(f"   - 缺少: {', '.join(info_suff.get('missing_elements', [])[:5])}")
        
        # 能力匹配提示
        deliv_cap = capability_precheck.get("deliverable_capability", {})
        cap_score = deliv_cap.get("capability_score", 1.0)
        hints.append(f"✅ **能力匹配度**: {cap_score:.0%}")
        
        # 在能力范围内的交付物
        capable = capability_precheck.get("capable_deliverables", [])
        if capable:
            deliverable_types = [d.get("type", "") for d in capable[:3]]
            hints.append(f"   - 可交付: {', '.join(deliverable_types)}")
        
        # 需要转化的需求
        transformations = capability_precheck.get("transformations", [])
        if transformations:
            hints.append("⚠️ **需要转化的需求**:")
            for t in transformations[:3]:
                hints.append(f"   - '{t.get('original')}' → '{t.get('transformed_to')}' ({t.get('reason', '')[:50]})")
        
        # 推荐行动
        recommended = capability_precheck.get("recommended_action", "proceed_analysis")
        action_map = {
            "proceed_analysis": "建议继续深度分析",
            "questionnaire_first": "建议先收集问卷补充信息",
            "clarify_expectations": "建议与用户澄清期望（部分需求超出能力）"
        }
        hints.append(f"📋 **建议行动**: {action_map.get(recommended, recommended)}")
        
        hints.append("")
        hints.append("请基于以上预检测结果完成 Phase1 分析，重点验证和补充预检测的判断。")
        
        return "\n".join(hints)

    def _fallback_phase2(self, user_input: str, phase1_result: Dict[str, Any]) -> Dict[str, Any]:
        """Phase2 降级逻辑"""
        return {
            "phase": 2,
            "analysis_layers": {
                "L1_facts": [f"用户输入: {user_input[:100]}..."],
                "L2_user_model": {"psychological": "待分析", "sociological": "待分析", "aesthetic": "待分析"},
                "L3_core_tension": "待识别核心矛盾",
                "L4_project_task": user_input[:200],
                "L5_sharpness": {"score": 50, "note": "降级模式"}
            },
            "structured_output": {
                "project_task": user_input[:200],
                "character_narrative": "待进一步分析",
                "physical_context": "待明确",
                "resource_constraints": "待明确",
                "regulatory_requirements": "待明确",
                "inspiration_references": "待补齐",
                "experience_behavior": "待补齐",
                "design_challenge": "待识别"
            },
            "expert_handoff": {
                "critical_questions_for_experts": {},
                "design_challenge_spectrum": {},
                "permission_to_diverge": {}
            },
            "fallback": True
        }

    def _build_phase1_only_result(self, phase1_result: Dict[str, Any], user_input: str) -> Dict[str, Any]:
        """构建仅 Phase1 的结果结构"""
        return {
            "project_task": phase1_result.get("project_summary", user_input[:200]),
            "character_narrative": "待问卷补充后分析",
            "physical_context": "待明确",
            "resource_constraints": "待明确",
            "regulatory_requirements": "待明确",
            "inspiration_references": "待补齐",
            "experience_behavior": "待补齐",
            "design_challenge": "待识别",
            "primary_deliverables": phase1_result.get("primary_deliverables", []),
            "info_status": phase1_result.get("info_status"),
            "info_gaps": phase1_result.get("info_gaps", []),
            "project_type_preliminary": phase1_result.get("project_type_preliminary"),
            "project_overview": phase1_result.get("project_summary", user_input[:200]),
            "core_objectives": [],
            "project_tasks": []
        }

    def _merge_phase_results(self, phase1: Dict[str, Any], phase2: Dict[str, Any]) -> Dict[str, Any]:
        """合并 Phase1 和 Phase2 结果"""
        structured_output = phase2.get("structured_output", {})
        
        result = {
            # 来自 Phase2 的核心字段
            "project_task": structured_output.get("project_task", ""),
            "character_narrative": structured_output.get("character_narrative", ""),
            "physical_context": structured_output.get("physical_context", ""),
            "resource_constraints": structured_output.get("resource_constraints", ""),
            "regulatory_requirements": structured_output.get("regulatory_requirements", ""),
            "inspiration_references": structured_output.get("inspiration_references", ""),
            "experience_behavior": structured_output.get("experience_behavior", ""),
            "design_challenge": structured_output.get("design_challenge", ""),
            
            # 来自 Phase1 的交付物识别
            "primary_deliverables": phase1.get("primary_deliverables", []),
            "info_status": phase1.get("info_status"),
            "project_type_preliminary": phase1.get("project_type_preliminary"),
            
            # 来自 Phase2 的分析层
            "analysis_layers": phase2.get("analysis_layers", {}),
            
            # 来自 Phase2 的专家接口
            "expert_handoff": phase2.get("expert_handoff", {}),
            
            # 兼容旧格式
            "project_overview": structured_output.get("project_task", ""),
            "core_objectives": [],
            "project_tasks": []
        }
        
        # 从 project_task 提取目标和任务
        project_task = result["project_task"]
        if project_task:
            result["core_objectives"] = [project_task[:100]]
            result["project_tasks"] = [project_task]
        
        return result

    def _calculate_two_phase_confidence(self, phase1: Dict[str, Any], phase2: Dict[str, Any]) -> float:
        """计算两阶段分析的置信度"""
        confidence = 0.5  # 基础置信度
        
        # Phase1 贡献
        if phase1.get("info_status") == "sufficient":
            confidence += 0.1
        if len(phase1.get("primary_deliverables", [])) > 0:
            confidence += 0.1
        
        # Phase2 贡献
        sharpness = phase2.get("analysis_layers", {}).get("L5_sharpness", {})
        if isinstance(sharpness, dict):
            score = sharpness.get("score", 0)
            confidence += min(score / 200, 0.2)  # 最多 +0.2
        
        if phase2.get("expert_handoff", {}).get("critical_questions_for_experts"):
            confidence += 0.1
        
        return min(confidence, 1.0)


# 注册智能体
from .base import AgentFactory
AgentFactory.register_agent(AgentType.REQUIREMENTS_ANALYST, RequirementsAnalystAgent)
