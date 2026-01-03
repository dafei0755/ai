"""
项目总监智能体 - Enhanced Version

负责战略分析和任务分派，协调各专业智能体的工作
支持固定角色模式和动态角色配置模式
"""

import json
import time
from typing import Any, Dict, List, Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from langgraph.types import Command, Send
from loguru import logger

from ..core.state import AgentType, ProjectAnalysisState
from ..core.types import AnalysisResult, TaskAssignment, format_role_display_name
from ..services.capability_boundary_service import CapabilityBoundaryService
from .base import LLMAgent

# from ..workflow.batch_scheduler import BatchScheduler  # Moved to local import to avoid circular dependency


class ProjectDirectorAgent(LLMAgent):
    """
    项目总监智能体 - Dynamic Mode Only

    仅支持动态角色模式 (dynamic) - 从roles.yaml加载并动态选择角色

    配置参数:
    - enable_role_config: 是否启用角色配置系统 (默认: True)
    """

    def __init__(self, llm_model, config: Optional[Dict[str, Any]] = None):
        super().__init__(
            agent_type=AgentType.PROJECT_DIRECTOR,
            name="项目总监",
            description="制定分析策略，分派任务给专业智能体团队",
            llm_model=llm_model,
            config=config,
        )

        # 获取配置（仅支持 Dynamic Mode）
        self.mode = "dynamic"
        self.enable_role_config = config.get("enable_role_config", True) if config else True

        # 初始化动态角色系统
        self.role_manager = None
        self.dynamic_director = None
        self.agent_factory = None

        if self.enable_role_config:
            try:
                from ..core.role_manager import RoleManager
                from .dynamic_project_director import DynamicProjectDirector
                from .specialized_agent_factory import SpecializedAgentFactory

                self.role_manager = RoleManager()
                self.dynamic_director = DynamicProjectDirector(llm_model, self.role_manager)
                self.agent_factory = SpecializedAgentFactory

                logger.info(f"ProjectDirector initialized in {self.mode} mode with role configuration enabled")
            except Exception as e:
                logger.error(f"Failed to initialize role configuration system: {e}")
                raise RuntimeError(
                    f"ProjectDirector requires role configuration system, but initialization failed: {e}"
                )
        else:
            logger.warning("ProjectDirector initialized without role configuration system")

    def validate_input(self, state: ProjectAnalysisState) -> bool:
        """验证输入是否有效"""
        return state.get("structured_requirements") is not None and isinstance(
            state.get("structured_requirements"), dict
        )

    def get_dependencies(self) -> List[AgentType]:
        """获取依赖的智能体"""
        return [AgentType.REQUIREMENTS_ANALYST]

    def _construct_full_role_id(self, role_id: str) -> str:
        """
        根据 role_id 构造完整的角色ID

        注意: 使用配置文件的实际键名（主角色名称/静态），而非LLM生成的动态名称
        - V3: "叙事与体验专家" (配置文件) vs "人物及叙事专家" (LLM生成)
        - V5: "场景与行业专家" (配置文件) vs "场景与用户生态专家" (LLM生成)
        """
        # 如果已经是完整格式 (如 "V2_设计总监_2-1")，直接返回
        if role_id.count("_") >= 2:
            return role_id

        # 如果只是短ID (如 "2-1")，需要推断前缀
        # 根据第一个数字推断前缀
        if role_id.startswith("2-"):
            return f"V2_设计总监_{role_id}"
        elif role_id.startswith("3-"):
            return f"V3_叙事与体验专家_{role_id}"  # ✅ 配置文件键名
        elif role_id.startswith("4-"):
            return f"V4_设计研究员_{role_id}"
        elif role_id.startswith("5-"):
            return f"V5_场景与行业专家_{role_id}"  # ✅ 配置文件键名
        elif role_id.startswith("6-"):
            return f"V6_专业总工程师_{role_id}"
        else:
            # 未知格式，直接返回
            return role_id

    def get_system_prompt(self) -> str:
        """获取系统提示词 - 从外部配置加载（v6.0）"""
        from ..core.prompt_manager import PromptManager

        prompt_manager = PromptManager()
        prompt = prompt_manager.get_prompt("project_director")

        if not prompt:
            raise RuntimeError("[project_director] 提示词配置文件未找到！" "请确保 config/prompts/project_director.yaml 存在。")

        logger.info("[project_director] 成功从外部配置加载提示词（v6.0）")
        return prompt

    def get_task_description(self, state: ProjectAnalysisState) -> str:
        """
        获取具体任务描述

        🆕 V1.5集成: 将可行性分析结果注入到任务描述中，指导专家任务分派
        """
        requirements = state.get("structured_requirements", {})

        # 提取关键信息
        project_overview = requirements.get("project_overview", "")
        core_objectives = requirements.get("core_objectives", [])
        functional_requirements = requirements.get("functional_requirements", [])
        constraints = requirements.get("constraints", {})

        # 🆕 提取V1.5可行性分析结果
        feasibility = state.get("feasibility_assessment", {})
        feasibility_context = self._build_feasibility_context(feasibility)

        base_description = f"""基于以下需求分析结果，请制定项目分析策略并分派任务：

项目概述：
{project_overview}

核心目标：
{core_objectives}

功能需求：
{functional_requirements}

约束条件：
{constraints}"""

        # 🆕 如果有可行性分析结果，添加到任务描述中
        if feasibility_context:
            return (
                base_description
                + "\n\n"
                + feasibility_context
                + """

请分析项目特点，确定需要哪些专业智能体参与，并为每个智能体制定具体的分析任务。
考虑项目的复杂度、行业特点、技术要求等因素，确保分析的全面性和专业性。
🔥 特别注意：根据上述可行性分析的发现，优先分派专家处理高风险冲突和高优先级需求。"""
            )
        else:
            return (
                base_description
                + """

请分析项目特点，确定需要哪些专业智能体参与，并为每个智能体制定具体的分析任务。
考虑项目的复杂度、行业特点、技术要求等因素，确保分析的全面性和专业性。"""
            )

    def _build_feasibility_context(self, feasibility: Dict[str, Any]) -> str:
        """
        构建可行性分析上下文（🆕 V1.5集成）

        将V1.5的分析结果格式化为简洁的指导信息，用于影响ProjectDirector的决策

        Args:
            feasibility: V1.5可行性分析师的输出

        Returns:
            格式化的可行性上下文字符串
        """
        if not feasibility:
            return ""

        context_parts = []

        # 1. 总体可行性评估
        assessment = feasibility.get("feasibility_assessment", {})
        if assessment:
            overall = assessment.get("overall_feasibility", "")
            critical_issues = assessment.get("critical_issues", [])

            if overall or critical_issues:
                context_parts.append("## 📊 可行性评估（V1.5后台分析）")
                if overall:
                    status_emoji = {"high": "✅", "medium": "⚠️", "low": "🚨"}.get(overall, "ℹ️")
                    context_parts.append(f"{status_emoji} 总体可行性: {overall}")

                if critical_issues:
                    context_parts.append("🚨 关键问题:")
                    for issue in critical_issues[:3]:  # 最多显示3个
                        context_parts.append(f"   - {issue}")
                context_parts.append("")

        # 2. 冲突检测结果
        conflicts = feasibility.get("conflict_detection", {})
        if conflicts:
            has_conflict = False
            conflict_lines = ["## ⚠️ 资源约束冲突检测"]

            # 预算冲突
            budget_conflicts = conflicts.get("budget_conflicts", [])
            if budget_conflicts and budget_conflicts[0].get("detected"):
                has_conflict = True
                severity = budget_conflicts[0].get("severity", "unknown")
                description = budget_conflicts[0].get("description", "")
                conflict_lines.append(f"🔴 预算冲突 ({severity}): {description}")

            # 时间冲突
            timeline_conflicts = conflicts.get("timeline_conflicts", [])
            if timeline_conflicts and timeline_conflicts[0].get("detected"):
                has_conflict = True
                severity = timeline_conflicts[0].get("severity", "unknown")
                description = timeline_conflicts[0].get("description", "")
                conflict_lines.append(f"🕒 时间冲突 ({severity}): {description}")

            # 空间冲突
            space_conflicts = conflicts.get("space_conflicts", [])
            if space_conflicts and space_conflicts[0].get("detected"):
                has_conflict = True
                severity = space_conflicts[0].get("severity", "unknown")
                description = space_conflicts[0].get("description", "")
                conflict_lines.append(f"📐 空间冲突 ({severity}): {description}")

            if has_conflict:
                context_parts.extend(conflict_lines)
                context_parts.append("")

        # 3. 优先级矩阵（Top 3）
        priority_matrix = feasibility.get("priority_matrix", [])
        if priority_matrix:
            context_parts.append("## 🎯 需求优先级排序（Top 3）")
            for i, req in enumerate(priority_matrix[:3], start=1):
                requirement = req.get("requirement", "")
                score = req.get("priority_score", 0)
                cost = req.get("estimated_cost", "")
                context_parts.append(f"{i}. {requirement} (优先级分数: {score:.2f}, 成本: {cost})")
            context_parts.append("")

        # 4. 决策建议
        recommendations = feasibility.get("recommendations", [])
        if recommendations:
            # 找到推荐方案
            recommended = next((r for r in recommendations if r.get("recommended")), None)
            if recommended:
                context_parts.append("## 💡 推荐策略")
                context_parts.append(f"方案名称: {recommended.get('name', '')}")
                context_parts.append(f"策略: {recommended.get('strategy', '')}")

                # 关键调整
                adjustments = recommended.get("adjustments", [])
                if adjustments:
                    context_parts.append("关键调整:")
                    for adj in adjustments[:3]:  # 最多显示3个
                        context_parts.append(f"   - {adj}")
                context_parts.append("")

        return "\n".join(context_parts)

    def execute(
        self, state: ProjectAnalysisState, config: RunnableConfig, store: Optional[BaseStore] = None
    ) -> Command[Literal["v2_agent", "v3_agent", "v4_agent", "v5_agent", "v6_agent", "result_aggregator"]]:
        """
        执行战略分析和任务分派（仅 Dynamic Mode）
        """
        start_time = time.time()

        try:
            logger.info(f"Starting strategic analysis for session {state.get('session_id')} in Dynamic mode")

            # 验证输入
            if not self.validate_input(state):
                raise ValueError("Invalid input: structured requirements not found")

            # 执行 Dynamic Mode
            return self._execute_dynamic_mode(state, config, store, start_time)

        except Exception as e:
            error = self.handle_error(e, "strategic analysis and task dispatch")
            raise error

    def _execute_dynamic_mode(
        self, state: ProjectAnalysisState, config: RunnableConfig, store: Optional[BaseStore], start_time: float
    ) -> Command:
        """
        动态模式执行 - 使用角色配置系统动态选择角色

        🆕 v7.106: 融合用户确认的核心任务，确保专家分配与用户意图对齐
        """
        logger.info("Executing in dynamic mode with role configuration system")

        # 提取需求信息
        requirements = state.get("structured_requirements", {})
        requirements_text = self._format_requirements_for_selection(requirements)

        # 🆕 v7.106: 获取用户确认的核心任务
        confirmed_tasks = state.get("confirmed_core_tasks", [])
        if confirmed_tasks:
            logger.info(f"📋 [v7.106] 检测到 {len(confirmed_tasks)} 个用户确认的核心任务，将融合到角色选择中")

        # 使用动态项目总监选择角色（由LLM自主判断复杂度）
        try:
            # 🆕 v7.106: 如果有核心任务，传递给 select_roles_for_task
            if confirmed_tasks:
                # 构建包含核心任务的增强需求文本
                requirements_with_tasks = self._format_requirements_with_tasks(requirements_text, confirmed_tasks)
                selection = self.dynamic_director.select_roles_for_task(
                    requirements_with_tasks, confirmed_core_tasks=confirmed_tasks  # 🆕 传递用于验证
                )
            else:
                selection = self.dynamic_director.select_roles_for_task(requirements_text)

            logger.info(f"Dynamic director selected {len(selection.selected_roles)} roles")
            logger.debug(f"Selected roles: {selection.selected_roles}")

            # 🆕 能力边界检查：验证任务分派前的交付物能力
            primary_deliverables = requirements.get("primary_deliverables", [])
            if primary_deliverables:
                logger.info("🔍 [CapabilityBoundary] 验证任务分派前的交付物能力")
                boundary_check = CapabilityBoundaryService.check_deliverable_list(
                    deliverables=primary_deliverables,
                    context={
                        "node": "project_director",
                        "stage": "before_assignment",
                        "session_id": state.get("session_id", ""),
                    },
                )

                logger.info(f"📊 交付物能力边界检查结果:")
                logger.info(f"   在能力范围内: {boundary_check.within_capability}")
                logger.info(f"   能力匹配度: {boundary_check.capability_score:.2f}")

                # 如果有超出能力的交付物，标记限制说明
                if not boundary_check.within_capability:
                    logger.warning(f"⚠️ 部分交付物超出能力范围，已标记限制说明")

                    for i, deliv in enumerate(primary_deliverables):
                        deliv_type = deliv.get("type", "")

                        # 查找对应的检查结果
                        for check in boundary_check.deliverable_checks:
                            if not check.within_capability and check.original_type == deliv_type:
                                # 标记受限的交付物
                                deliv["capability_limited"] = True
                                deliv["limitation_note"] = check.transformation_reason or "超出系统能力范围"
                                logger.info(f"     - {deliv.get('deliverable_id', f'D{i+1}')}: {deliv_type} (受限)")
                                break
                else:
                    logger.info("✅ 所有交付物在能力范围内")

        except Exception as e:
            logger.error(f"Failed to select roles dynamically: {e}")
            raise ValueError(f"Dynamic role selection failed: {e}")

        # 创建动态智能体的Send命令
        parallel_commands = []
        dynamic_agents_info = {}

        for role in selection.selected_roles:
            try:
                # ✅ 从 RoleObject 中提取 role_id
                if isinstance(role, dict):
                    short_role_id = role.get("role_id", "")
                elif hasattr(role, "role_id"):
                    short_role_id = role.role_id
                else:
                    short_role_id = role  # 兼容旧格式（字符串）

                # ✅ 构造完整的角色ID（如 "V2_设计总监_2-1"）
                role_id = self._construct_full_role_id(short_role_id)

                logger.info(f"🔍 [DEBUG] Processing role: short_id={short_role_id}, full_id={role_id}")

                # 解析角色ID
                base_type, rid = self.role_manager.parse_full_role_id(role_id)
                role_config = self.role_manager.get_role_config(base_type, rid)

                if role_config:
                    # 获取任务描述 - 兼容 TaskDetail 对象和字符串格式
                    task_data = selection.task_distribution.get(role_id, "执行专业分析")

                    # 如果是 TaskDetail 对象，提取任务列表并合并为字符串
                    if hasattr(task_data, "tasks"):
                        task_description = "; ".join(task_data.tasks)
                    elif isinstance(task_data, dict) and "tasks" in task_data:
                        task_description = "; ".join(task_data["tasks"])
                    else:
                        task_description = str(task_data)

                    # 创建Send命令 (使用动态角色节点)
                    # 🆕 构建专家上下文，包含任务优先级信息
                    expert_context = {**state, "confirmed_core_tasks": confirmed_tasks}  # 🆕 传递确认任务（含优先级）

                    parallel_commands.append(
                        Send(
                            "dynamic_role_executor",  # 动态角色执行节点
                            {
                                "role_id": role_id,
                                "role_config": role_config,
                                "task": task_description,
                                "context": expert_context,  # 🆕 使用增强的上下文
                            },
                        )
                    )

                    # 记录角色信息
                    dynamic_agents_info[role_id] = {"name": role_config.get("name", "未知角色"), "task": task_description}

            except Exception as e:
                logger.error(f"Failed to create command for role {role_id}: {e}")

        # 如果没有成功创建任何命令，抛出错误
        if not parallel_commands:
            logger.error("No dynamic agents created")
            raise ValueError("Failed to create any dynamic agent commands")

        # 创建 subagents 字典，用于 V2-V6 agents 获取任务描述
        # 将动态角色映射到固定的 V2-V6 键
        subagents_mapping = {}
        role_to_v_mapping = {"V2": [], "V3": [], "V4": [], "V5": [], "V6": []}

        # 将选中的角色按类型分组
        for role in selection.selected_roles:
            # ✅ 从 RoleObject 中提取 role_id
            if isinstance(role, dict):
                short_role_id = role.get("role_id", "")
            elif hasattr(role, "role_id"):
                short_role_id = role.role_id
            else:
                short_role_id = role  # 兼容旧格式

            # ✅ 构造完整的角色ID
            role_id = self._construct_full_role_id(short_role_id)

            base_type, _ = self.role_manager.parse_full_role_id(role_id)
            if base_type in role_to_v_mapping:
                # 获取任务描述 - 兼容 TaskDetail 对象和字符串格式
                task_data = selection.task_distribution.get(role_id, "执行专业分析")

                # 如果是 TaskDetail 对象，提取任务列表并合并为字符串
                if hasattr(task_data, "tasks"):
                    task_desc = "; ".join(task_data.tasks)
                elif isinstance(task_data, dict) and "tasks" in task_data:
                    task_desc = "; ".join(task_data["tasks"])
                else:
                    task_desc = str(task_data)

                role_to_v_mapping[base_type].append(task_desc)

        # 为每个 V2-V6 创建任务描述（合并同类型的所有任务）
        for v_type, tasks in role_to_v_mapping.items():
            if tasks:
                subagents_mapping[v_type] = "; ".join(tasks)
            else:
                # 如果没有选中该类型的角色，使用默认描述
                default_tasks = {
                    "V2": "进行设计研究分析",
                    "V3": "进行技术架构分析",
                    "V4": "进行用户体验设计分析",
                    "V5": "进行商业模式分析",
                    "V6": "制定项目实施计划",
                }
                subagents_mapping[v_type] = default_tasks.get(v_type, "执行专业分析")

        # New: Calculate batch execution order using BatchScheduler
        from ..workflow.batch_scheduler import BatchScheduler

        batch_scheduler = BatchScheduler()
        try:
            # ✅ 构造完整角色ID列表传给 BatchScheduler
            full_role_ids = [
                self._construct_full_role_id(role.role_id)
                if hasattr(role, "role_id")
                else self._construct_full_role_id(role)
                for role in selection.selected_roles
            ]
            execution_batches = batch_scheduler.schedule_batches(full_role_ids)
            current_batch = 1  # Start from batch 1
            total_batches = len(execution_batches)
            logger.info(f"Batch calculation completed: {total_batches} batches total")
            for i, batch in enumerate(execution_batches, start=1):
                display_batch = [format_role_display_name(r) for r in batch]
                logger.info(f"  Batch {i}: {display_batch}")
        except Exception as e:
            logger.error(f"Batch calculation failed: {e}")
            # Fallback: treat all roles as single batch
            full_role_ids = [
                self._construct_full_role_id(role.role_id)
                if hasattr(role, "role_id")
                else self._construct_full_role_id(role)
                for role in selection.selected_roles
            ]
            execution_batches = [full_role_ids]
            current_batch = 1
            total_batches = 1

        # ✅ 序列化 selected_roles 为字典列表（保留完整信息）
        serialized_roles = [
            role.model_dump() if hasattr(role, "model_dump") else role for role in selection.selected_roles
        ]

        # 更新状态
        state_update = {
            "strategic_analysis": {
                "strategy_overview": selection.reasoning,
                "selected_roles": serialized_roles,  # ✅ 保存完整的 RoleObject 列表
                "task_distribution": selection.task_distribution,
                "execution_mode": "dynamic",
            },
            "subagents": subagents_mapping,  # 添加 subagents 字段
            "dynamic_agents": dynamic_agents_info,
            "active_agents": [
                self._construct_full_role_id(role.role_id)
                if hasattr(role, "role_id")
                else self._construct_full_role_id(role)
                for role in selection.selected_roles
            ],  # ✅ active_agents 存储完整角色ID（如 "V2_设计总监_2-1"）
            "execution_mode": "dynamic",
            # New: Batch execution fields
            "execution_batches": execution_batches,  # List[List[str]] - batch list
            "current_batch": current_batch,  # int - current batch number (1-based)
            "total_batches": total_batches,  # int - total number of batches
        }

        end_time = time.time()
        self._track_execution_time(start_time, end_time)

        logger.info(f"Dynamic mode analysis completed, dispatching {len(parallel_commands)} dynamic agents")

        # 返回Command对象
        return Command(update=state_update, goto=parallel_commands)

    def _format_requirements_with_tasks(self, requirements_text: str, confirmed_tasks: List[Dict[str, Any]]) -> str:
        """
        格式化需求信息并融合用户确认的核心任务（v7.106新增）

        Args:
            requirements_text: 原始需求文本
            confirmed_tasks: 用户确认的核心任务列表

        Returns:
            增强的需求文本，包含核心任务信息
        """
        enhanced_text = requirements_text

        enhanced_text += "\n\n# 用户确认的核心任务（优先级最高！）\n\n"
        enhanced_text += "用户在问卷环节已经确认了以下核心任务，你在分配专家任务时**必须围绕这些核心任务展开**：\n\n"

        for i, task in enumerate(confirmed_tasks, 1):
            enhanced_text += f"\n**核心任务 {i}: {task.get('title')}**\n"
            enhanced_text += f"- 描述: {task.get('description')}\n"
            enhanced_text += f"- 类型: {task.get('type')}\n"
            if task.get("motivation"):
                enhanced_text += f"- 动机: {task.get('motivation')}\n"
            # 如果任务有信息依赖，也要告知项目总监
            if task.get("missing_info"):
                enhanced_text += f"- ⚠️ 信息缺失: {', '.join(task['missing_info'])} (用户已在问卷中补充)\n"

        enhanced_text += "\n⚠️ **重要**：你分配给专家的任务必须与上述核心任务对齐，确保最终输出能回答用户确认的核心问题。\n"

        return enhanced_text

    def _format_requirements_for_selection(self, requirements: Dict[str, Any]) -> str:
        """
        格式化需求信息用于角色选择
        """
        lines = []

        if "project_overview" in requirements:
            lines.append(f"## 项目概述\n{requirements['project_overview']}\n")

        if "core_objectives" in requirements:
            lines.append("## 核心目标")
            for obj in requirements.get("core_objectives", []):
                lines.append(f"- {obj}")
            lines.append("")

        if "functional_requirements" in requirements:
            lines.append("## 功能需求")
            for req in requirements.get("functional_requirements", []):
                lines.append(f"- {req}")
            lines.append("")

        if "constraints" in requirements:
            lines.append("## 约束条件")
            constraints = requirements.get("constraints", {})

            # 处理constraints可能是字典或列表的情况
            if isinstance(constraints, dict):
                for key, value in constraints.items():
                    lines.append(f"- {key}: {value}")
            elif isinstance(constraints, list):
                for constraint in constraints:
                    if isinstance(constraint, dict):
                        for key, value in constraint.items():
                            lines.append(f"- {key}: {value}")
                    else:
                        lines.append(f"- {constraint}")
            else:
                # 如果是其他类型,直接转换为字符串
                lines.append(f"- {constraints}")

            lines.append("")

        return "\n".join(lines)

    def _parse_strategic_analysis(self, llm_response: str) -> Dict[str, Any]:
        """解析战略分析结果 - 支持新的v6.0格式"""
        try:
            # 尝试提取JSON部分
            start_idx = llm_response.find("{")
            end_idx = llm_response.rfind("}") + 1

            if start_idx != -1 and end_idx > start_idx:
                json_str = llm_response[start_idx:end_idx]
                strategic_data = json.loads(json_str)
            else:
                # 如果没有找到JSON，创建基础结构
                strategic_data = self._create_fallback_strategy(llm_response)

            # 验证新格式的必需字段
            required_fields = [
                "query_type",  # 新增：查询类型
                "query_type_reasoning",  # 新增：判定推理
                "assessment",  # 新增：评估结果
                "research_plan",  # 新增：研究计划
                "task_assignments",  # 保留：任务分派
                "execution_strategy",  # 新增：执行策略
                "agent_count",  # 新增：智能体数量
            ]

            # 兼容旧格式：如果没有新字段，尝试从旧字段转换
            if "query_type" not in strategic_data and "strategy_overview" in strategic_data:
                logger.info("Detected old format, converting to new format")
                strategic_data = self._convert_old_to_new_format(strategic_data)

            # 验证并填充缺失字段
            for field in required_fields:
                if field not in strategic_data:
                    strategic_data[field] = self._get_default_field_value(field)

            # 保留旧格式字段以兼容现有代码
            if "strategy_overview" not in strategic_data:
                strategic_data["strategy_overview"] = strategic_data.get("query_type_reasoning", "基于项目需求进行分析")

            if "selected_agents" not in strategic_data:
                strategic_data["selected_agents"] = list(strategic_data.get("task_assignments", {}).keys())

            return strategic_data

        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from strategic analysis, using fallback")
            return self._create_fallback_strategy(llm_response)

    def _convert_old_to_new_format(self, old_data: Dict[str, Any]) -> Dict[str, Any]:
        """将旧格式转换为新格式"""
        return {
            "query_type": "深度优先查询",  # 默认
            "query_type_reasoning": old_data.get("strategy_overview", "基于项目需求进行全面分析"),
            "assessment": {
                "core_concepts": [],
                "required_facts": [],
                "constraints": [],
                "user_concerns": "项目成功实施",
                "deliverable_format": "综合分析报告",
            },
            "research_plan": {"perspectives": ["设计视角", "技术视角", "用户体验视角", "商业视角", "实施视角"]},
            "task_assignments": old_data.get("task_assignments", self._create_default_assignments()),
            "execution_strategy": "并行",
            "agent_count": len(old_data.get("selected_agents", [])),
            "agent_count_reasoning": "基于项目复杂度",
            # 保留旧字段
            "strategy_overview": old_data.get("strategy_overview"),
            "selected_agents": old_data.get("selected_agents", []),
            "priority_order": old_data.get("priority_order", []),
            "estimated_duration": old_data.get("estimated_duration", 1800),
            "success_metrics": old_data.get("success_metrics", []),
        }

    def _get_default_field_value(self, field: str) -> Any:
        """获取字段的默认值"""
        defaults = {
            "query_type": "深度优先查询",
            "query_type_reasoning": "基于项目需求的复杂性，需要多维度深入分析",
            "assessment": {
                "core_concepts": [],
                "required_facts": [],
                "constraints": [],
                "user_concerns": "项目成功实施",
                "deliverable_format": "综合分析报告",
            },
            "research_plan": {"perspectives": ["设计视角", "技术视角", "用户体验视角", "商业视角", "实施视角"]},
            "task_assignments": self._create_default_assignments(),
            "execution_strategy": "并行",
            "agent_count": 5,
            "agent_count_reasoning": "标准复杂度项目，需要5个专业智能体",
        }
        return defaults.get(field, None)

    def _create_fallback_strategy(self, content: str) -> Dict[str, Any]:
        """创建备用的战略分析结构 - 新格式"""
        return {
            "query_type": "深度优先查询",
            "query_type_reasoning": "基于项目需求进行全面分析",
            "assessment": {
                "core_concepts": [],
                "required_facts": [],
                "constraints": [],
                "user_concerns": "项目成功实施",
                "deliverable_format": "综合分析报告",
            },
            "research_plan": {"perspectives": ["设计视角", "技术视角", "用户体验视角", "商业视角", "实施视角"]},
            "task_assignments": self._create_default_assignments(),
            "execution_strategy": "并行",
            "agent_count": 5,
            "agent_count_reasoning": "标准复杂度项目",
            # 兼容旧格式
            "strategy_overview": "基于项目需求进行全面分析",
            "selected_agents": ["V2", "V3", "V4", "V5", "V6"],
            "priority_order": ["V2", "V3", "V4", "V5", "V6"],
            "estimated_duration": 1800,
            "success_metrics": ["完整性", "专业性", "可操作性"],
            "raw_analysis": content,
        }

    def _create_default_assignments(self) -> Dict[str, str]:
        """创建默认的任务分派"""
        return {
            "V2": "进行设计研究分析，包括用户研究、设计趋势、界面设计建议等",
            "V3": "进行技术架构分析，包括技术可行性、架构设计、技术选型等",
            "V4": "进行用户体验设计分析，包括用户旅程、交互设计、体验优化等",
            "V5": "进行商业模式分析，包括市场定位、盈利模式、竞争分析等",
            "V6": "制定实施计划，包括项目规划、时间安排、资源配置等",
        }

    def create_task_assignment(self, agent_type: AgentType, task_description: str, priority: int = 1) -> TaskAssignment:
        """创建任务分派对象"""
        return TaskAssignment(
            agent_type=agent_type,
            task_description=task_description,
            priority=priority,
            dependencies=[],
            estimated_duration=300,  # 5分钟默认
        )

    def get_execution_strategy(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """获取执行策略"""
        requirements = state.get("structured_requirements", {})

        # 分析项目复杂度
        complexity_score = self._calculate_complexity(requirements)

        # 确定执行策略
        if complexity_score > 0.8:
            strategy = "comprehensive"  # 全面分析
        elif complexity_score > 0.5:
            strategy = "focused"  # 重点分析
        else:
            strategy = "basic"  # 基础分析

        return {
            "strategy_type": strategy,
            "complexity_score": complexity_score,
            "recommended_agents": self._get_recommended_agents(complexity_score),
            "estimated_duration": self._estimate_duration(complexity_score),
        }

    def _calculate_complexity(self, requirements: Dict[str, Any]) -> float:
        """计算项目复杂度"""
        complexity_factors = []

        # 功能需求数量
        functional_reqs = requirements.get("functional_requirements", [])
        if isinstance(functional_reqs, list):
            complexity_factors.append(min(len(functional_reqs) / 10, 0.3))

        # 约束条件复杂度
        constraints = requirements.get("constraints", {})
        if isinstance(constraints, dict):
            complexity_factors.append(min(len(constraints) / 5, 0.2))

        # 目标用户复杂度
        target_users = requirements.get("target_users", "")
        if isinstance(target_users, str) and len(target_users) > 100:
            complexity_factors.append(0.2)

        # 核心目标数量
        objectives = requirements.get("core_objectives", [])
        if isinstance(objectives, list):
            complexity_factors.append(min(len(objectives) / 5, 0.3))

        return min(sum(complexity_factors), 1.0)

    def _get_recommended_agents(self, complexity_score: float) -> List[str]:
        """根据复杂度推荐智能体"""
        if complexity_score > 0.8:
            return ["V2", "V3", "V4", "V5", "V6"]  # 全部
        elif complexity_score > 0.5:
            return ["V3", "V5", "V6"]  # 技术+商业+实施
        else:
            return ["V5", "V6"]  # 商业+实施

    def _estimate_duration(self, complexity_score: float) -> int:
        """估算执行时间（秒）"""
        base_duration = 600  # 10分钟基础时间
        return int(base_duration * (1 + complexity_score))

    def set_mode(self, mode: str) -> bool:
        """
        切换执行模式（仅支持 Dynamic Mode）

        Args:
            mode: 必须为 "dynamic"

        Returns:
            是否成功切换
        """
        if mode != "dynamic":
            logger.error(f"Invalid mode: {mode}. Only 'dynamic' mode is supported")
            return False

        if not self.enable_role_config:
            logger.error("Cannot use dynamic mode: role configuration system not available")
            return False

        old_mode = self.mode
        self.mode = mode
        logger.info(f"Mode set to {mode} (was {old_mode})")
        return True

    def get_mode_info(self) -> Dict[str, Any]:
        """
        获取当前模式信息

        Returns:
            模式信息字典
        """
        info = {
            "current_mode": self.mode,
            "role_config_enabled": self.enable_role_config,
            "available_modes": ["dynamic"],  # 仅支持 Dynamic Mode
        }

        if self.role_manager:
            info["total_roles"] = len(self.role_manager.get_all_role_ids())
            info["role_categories"] = list(self.role_manager.roles.keys())

        return info


# 注册智能体
from .base import AgentFactory

AgentFactory.register_agent(AgentType.PROJECT_DIRECTOR, ProjectDirectorAgent)
