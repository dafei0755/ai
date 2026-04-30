# DEPRECATED: 已被 v2.0 双态架构 gate_node（门禁）+ requirements_s1-s5 节点链取代。
# 当 ENABLE_DUAL_MODE_V2=true 时本模块不再被主工作流调用，仅保留以供回退兼容。
"""
项目总监智能体 - Enhanced Version

负责战略分析和任务分派，协调各专业智能体的工作
支持固定角色模式和动态角色配置模式
"""

import json
import time
from typing import Any, Dict, List, Literal, Optional

from langchain_core.runnables import RunnableConfig
from langgraph.store.base import BaseStore
from langgraph.types import Command, Send
from loguru import logger

from ..core.state import AgentType, ProjectAnalysisState
from ..core.types import TaskAssignment, format_role_display_name
from ..services.capability_boundary_service import CapabilityBoundaryService

# v7.700 P0: Mode Task Library 集成
from ..services.mode_task_library import ModeTaskLibrary
from .base import LLMAgent

# from ..workflow.batch_scheduler import BatchScheduler  # Moved to local import to avoid circular dependency


# ============ 任务分配验证函数 (v7.140 新增) ============


def _validate_task_distribution_embedded(
    state: ProjectAnalysisState, strategic_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    在 project_director 内部调用的验证函数
    检查当前任务分配的合理性

    返回格式:
    {
        "status": "passed" | "warning" | "failed",
        "issues": List[Dict],
        "summary": str,
        "total_issues": int
    }
    """
    issues = []

    # 获取任务分配信息
    selected_roles = strategic_analysis.get("selected_roles", [])
    task_distribution = strategic_analysis.get("task_distribution", {})
    execution_batches = strategic_analysis.get("execution_batches", [])

    # 1. 任务完整性检查
    required_capabilities = _extract_required_capabilities_from_requirements(state)
    assigned_capabilities = _extract_assigned_capabilities_from_distribution(task_distribution, selected_roles)

    missing_caps = set(required_capabilities) - set(assigned_capabilities)
    if missing_caps:
        issues.append(
            {
                "severity": "critical",
                "type": "missing_task",
                "description": f"以下需求未分配任务: {', '.join(missing_caps)}",
                "missing_capabilities": list(missing_caps),
                "suggestion": "建议增加相应专家或调整现有专家的任务范围",
            }
        )

    # 2. 角色能力匹配检查
    for role_id, task_data in task_distribution.items():
        # 提取任务描述
        if hasattr(task_data, "tasks"):
            tasks_list = task_data.tasks
        elif isinstance(task_data, dict) and "tasks" in task_data:
            tasks_list = task_data["tasks"]
        else:
            tasks_list = [str(task_data)]

        # 查找对应的角色对象
        role_obj = None
        for role in selected_roles:
            if isinstance(role, dict):
                if role.get("role_id") == role_id:
                    role_obj = role
                    break
            elif hasattr(role, "role_id"):
                if role.role_id == role_id:
                    role_obj = role
                    break

        if role_obj:
            role_name = (
                role_obj.get("name", "未知角色") if isinstance(role_obj, dict) else getattr(role_obj, "name", "未知角色")
            )
            expertise = role_obj.get("expertise", "") if isinstance(role_obj, dict) else getattr(role_obj, "expertise", "")
            role_name = str(role_name)
            expertise = str(expertise) if expertise is not None else ""

            # 检查能力匹配度
            if not _check_capability_match(expertise, tasks_list):
                issues.append(
                    {
                        "severity": "high",
                        "type": "capability_mismatch",
                        "role_id": role_id,
                        "role_name": role_name,
                        "description": f"{role_name} 的专业能力可能无法完全胜任分配的任务",
                        "tasks": tasks_list[:2],  # 只显示前两个任务
                        "suggestion": f"建议重新评估 {role_name} 的任务分配，或选择更匹配的专家",
                    }
                )

    # 3. 批次依赖检查
    if execution_batches and len(execution_batches) > 1:
        dependency_issues = _check_batch_dependency_conflicts(execution_batches, task_distribution)
        issues.extend(dependency_issues)

    # 判定验证状态
    critical_count = sum(1 for i in issues if i["severity"] == "critical")
    high_count = sum(1 for i in issues if i["severity"] == "high")

    if critical_count > 0:
        status = "failed"
    elif high_count > 2:
        status = "warning"
    else:
        status = "passed"

    return {
        "status": status,
        "issues": issues,
        "summary": f"验证结果: {critical_count} 个严重问题, {high_count} 个高风险问题",
        "total_issues": len(issues),
    }


def _extract_required_capabilities_from_requirements(state: ProjectAnalysisState) -> List[str]:
    """
    从需求中提取所需的关键能力
    """
    capabilities = []

    requirements = state.get("structured_requirements", {})
    confirmed_tasks = state.get("confirmed_core_tasks", [])

    # 从结构化需求中提取
    if "functional_requirements" in requirements:
        for req in requirements["functional_requirements"]:
            if isinstance(req, str):
                capabilities.append(req[:30])  # 取前30个字符作为能力标识

    # 从用户确认任务中提取
    if confirmed_tasks:
        for task in confirmed_tasks:
            if isinstance(task, dict):
                title = task.get("title", "")
                if title:
                    capabilities.append(title[:30])
            elif isinstance(task, str):
                capabilities.append(task[:30])

    return capabilities


def _extract_assigned_capabilities_from_distribution(task_distribution: Dict, selected_roles: List) -> List[str]:
    """
    从任务分配中提取已分配的能力
    """
    capabilities = []

    for role_id, task_data in task_distribution.items():
        # 提取任务描述
        if hasattr(task_data, "tasks"):
            tasks_list = task_data.tasks
        elif isinstance(task_data, dict) and "tasks" in task_data:
            tasks_list = task_data["tasks"]
        else:
            tasks_list = [str(task_data)]

        # 将任务描述作为能力
        for task in tasks_list:
            task_str = str(task)
            capabilities.append(task_str[:30])

    return capabilities


def _check_capability_match(expertise: str, tasks: List[str]) -> bool:
    """
    检查专家能力是否匹配任务需求

    简化版：检查 expertise 中是否包含任务关键词
    """
    if not expertise or not tasks:
        return True  # 无法判断时默认通过

    expertise_lower = expertise.lower()

    # 关键词匹配
    for task in tasks:
        task_lower = str(task).lower()
        # 提取任务中的关键词
        task_keywords = [w for w in task_lower.split() if len(w) > 2]

        # 如果至少有一个关键词匹配，认为有能力
        matched = any(keyword in expertise_lower for keyword in task_keywords[:5])
        if not matched:
            return False

    return True


def _check_batch_dependency_conflicts(batches: List[List[str]], task_distribution: Dict) -> List[Dict]:
    """
    检查批次间的依赖冲突
    """
    issues = []

    # 简化版：检查是否有明显的依赖关系被违反
    # 例如：需求分析应该在设计之前
    dependency_rules = [
        ("需求", "设计"),
        ("设计", "实现"),
        ("分析", "方案"),
    ]

    for batch_idx, batch_roles in enumerate(batches):
        for dependent, prerequisite in dependency_rules:
            # 检查当前批次是否有依赖项，而前置项在后续批次
            has_dependent = any(dependent in str(task_distribution.get(role, "")).lower() for role in batch_roles)

            if has_dependent:
                # 检查前置项是否在后续批次
                for later_batch_idx in range(batch_idx + 1, len(batches)):
                    later_batch = batches[later_batch_idx]
                    has_prerequisite = any(
                        prerequisite in str(task_distribution.get(role, "")).lower() for role in later_batch
                    )

                    if has_prerequisite:
                        issues.append(
                            {
                                "severity": "medium",
                                "type": "dependency_conflict",
                                "description": (
                                    f"批次{batch_idx + 1}的'{dependent}'任务可能依赖"
                                    f"批次{later_batch_idx + 1}的'{prerequisite}'任务"
                                ),
                                "suggestion": "建议调整批次顺序，确保依赖关系正确",
                            }
                        )

    return issues


def _generate_correction_feedback(validation_result: Dict[str, Any]) -> str:
    """
    基于验证结果生成反馈，供 LLM 自我修正
    """
    feedback_parts = ["任务分配验证失败，需要调整：\n\n"]

    for issue in validation_result["issues"]:
        if issue["severity"] in ["critical", "high"]:
            if issue["type"] == "missing_task":
                feedback_parts.append(
                    f" 缺失任务：{issue['description']}\n"
                    f"   建议：{issue.get('suggestion', '请为这些能力需求分配合适的专家')}\n\n"
                )
            elif issue["type"] == "capability_mismatch":
                feedback_parts.append(
                    f"️  能力不匹配：{issue['role_name']} 无法胜任任务\n"
                    f"   建议：{issue.get('suggestion', '重新选择具有相关专业能力的专家')}\n\n"
                )
            elif issue["type"] == "dependency_conflict":
                feedback_parts.append(
                    f"️  依赖冲突：{issue['description']}\n"
                    f"   建议：{issue.get('suggestion', '调整批次划分或任务顺序')}\n\n"
                )

    return "".join(feedback_parts)


def _is_auth_401_error(error_msg: str) -> bool:
    """识别认证类 401 错误，命中后应立即失败。"""
    lowered = (error_msg or "").lower()
    return (
        "401" in lowered
        and (
            "authentication" in lowered
            or "invalid_api_key" in lowered
            or "invalid api key" in lowered
            or "incorrect api key" in lowered
            or "user not found" in lowered
            or "unauthorized" in lowered
        )
    )


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
        """获取依赖的智能体（V1 RequirementsAnalystAgent 已废弃，无运行时依赖）"""
        return []

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
            return f"V3_叙事与体验专家_{role_id}"  # 配置文件键名
        elif role_id.startswith("4-"):
            return f"V4_设计研究员_{role_id}"
        elif role_id.startswith("5-"):
            return f"V5_场景与行业专家_{role_id}"  # 配置文件键名
        elif role_id.startswith("6-"):
            return f"V6_专业总工程师_{role_id}"
        elif role_id.startswith("7-"):
            return f"V7_社会关系与心理洞察专家_{role_id}"
        elif role_id.startswith("8-"):
            return f"V8_政策与治理顾问_{role_id}"
        elif role_id.startswith("9-"):
            return f"V9_产业链分析师_{role_id}"
        else:
            # 未知格式，直接返回
            return role_id

    def get_system_prompt(self) -> str:
        """获取系统提示词 - 从外部配置加载（v6.0）"""
        from ..core.prompt_manager import PromptManager

        prompt_manager = PromptManager()
        prompt = prompt_manager.get_prompt("project_director")

        if not prompt:
            raise RuntimeError(
                "[project_director] 提示词配置文件未找到！请确保 config/prompts/project_director.yaml 存在。"
            )

        logger.info("[project_director] 成功从外部配置加载提示词（v6.0）")
        return prompt

    def get_task_description(self, state: ProjectAnalysisState) -> str:
        """
        获取具体任务描述

         V1.5集成: 将可行性分析结果注入到任务描述中，指导专家任务分派
        """
        requirements = state.get("structured_requirements", {})

        # 提取关键信息
        project_overview = requirements.get("project_overview", "")
        core_objectives = requirements.get("core_objectives", [])
        functional_requirements = requirements.get("functional_requirements", [])
        constraints = requirements.get("constraints", {})

        # v8.1: 提取雷达图优先级结构（含维度ID、权重、key_requirements）
        design_priorities_structured = requirements.get("design_priorities_structured", [])
        priorities_section = ""
        if design_priorities_structured:
            priority_lines = []
            for p in design_priorities_structured[:5]:
                reqs_text = "、".join(p.get("key_requirements", [])[:3]) or "待明确"
                weight_pct = int(p.get("weight", 0) * 100)
                priority_lines.append(f"- {p.get('label', p.get('dimension', ''))}（权重{weight_pct}%）: {reqs_text}")
            priorities_section = "\n\n客户偏好雷达图优先级（权重越高越重要，需在任务分派中优先体现）：\n" + "\n".join(
                priority_lines
            )

        #  提取V1.5可行性分析结果
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
{constraints}{priorities_section}"""

        # 🆕 v12.0: 注入视觉约束信封
        _visual_constraints = state.get("visual_constraints") or {}
        _constraint_envelope = _visual_constraints.get("constraint_envelope", "")
        if _constraint_envelope:
            base_description += f"\n\n{_constraint_envelope}"
            logger.info(f"  🎯 [v12.0] 已注入约束信封 ({len(_constraint_envelope)} 字符)")

        #  如果有可行性分析结果，添加到任务描述中
        if feasibility_context:
            return (
                base_description
                + "\n\n"
                + feasibility_context
                + """

请分析项目特点，确定需要哪些专业智能体参与，并为每个智能体制定具体的分析任务。
考虑项目的复杂度、行业特点、技术要求等因素，确保分析的全面性和专业性。
 特别注意：根据上述可行性分析的发现，优先分派专家处理高风险冲突和高优先级需求。"""
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
        构建可行性分析上下文（ V1.5集成）

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
                context_parts.append("##  可行性评估（V1.5后台分析）")
                if overall:
                    status_emoji = {"high": "", "medium": "️", "low": ""}.get(overall, "ℹ️")
                    context_parts.append(f"{status_emoji} 总体可行性: {overall}")

                if critical_issues:
                    context_parts.append(" 关键问题:")
                    for issue in critical_issues[:3]:  # 最多显示3个
                        context_parts.append(f"   - {issue}")
                context_parts.append("")

        # 2. 冲突检测结果
        conflicts = feasibility.get("conflict_detection", {})
        if conflicts:
            has_conflict = False
            conflict_lines = ["## ️ 资源约束冲突检测"]

            # 预算冲突
            budget_conflicts = conflicts.get("budget_conflicts", [])
            if budget_conflicts and budget_conflicts[0].get("detected"):
                has_conflict = True
                severity = budget_conflicts[0].get("severity", "unknown")
                description = budget_conflicts[0].get("description", "")
                conflict_lines.append(f" 预算冲突 ({severity}): {description}")

            # 时间冲突
            timeline_conflicts = conflicts.get("timeline_conflicts", [])
            if timeline_conflicts and timeline_conflicts[0].get("detected"):
                has_conflict = True
                severity = timeline_conflicts[0].get("severity", "unknown")
                description = timeline_conflicts[0].get("description", "")
                conflict_lines.append(f" 时间冲突 ({severity}): {description}")

            # 空间冲突
            space_conflicts = conflicts.get("space_conflicts", [])
            if space_conflicts and space_conflicts[0].get("detected"):
                has_conflict = True
                severity = space_conflicts[0].get("severity", "unknown")
                description = space_conflicts[0].get("description", "")
                conflict_lines.append(f" 空间冲突 ({severity}): {description}")

            if has_conflict:
                context_parts.extend(conflict_lines)
                context_parts.append("")

        # 3. 优先级矩阵（Top 3）
        priority_matrix = feasibility.get("priority_matrix", [])
        if priority_matrix:
            context_parts.append("##  需求优先级排序（Top 3）")
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
                context_parts.append("##  推荐策略")
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

         v7.106: 融合用户确认的核心任务，确保专家分配与用户意图对齐
         v7.140: 集成内置验证循环，自动修正任务分配问题
        """
        logger.info("Executing in dynamic mode with role configuration system (validation-enabled)")

        # v9.2 fix: 消费 unified_review 发回的修改指令
        # 当用户在 unified_review 中选择 modify_roles/modify_tasks/reject 后，
        # 这些字段会被写入 state，DPD 应该将其纳入 LLM prompt 指导重新生成
        user_retry_reason = state.get("retry_reason", "")
        user_role_mod = state.get("role_modification_request", {})
        user_task_mod = state.get("task_modification_request", {})
        user_rejection = state.get("rejection_reason", "")
        user_requested_strategy = state.get("requested_strategy", "")

        user_modification_context = ""
        if user_retry_reason:
            logger.info(f"🔄 [v9.2] 检测到用户审核反馈: {user_retry_reason}")
            mod_parts = [f"## 用户审核反馈\n原因: {user_retry_reason}"]

            if user_role_mod:
                import json as _json
                mod_parts.append(f"角色修改请求: {_json.dumps(user_role_mod, ensure_ascii=False)}")
            if user_task_mod:
                import json as _json
                mod_parts.append(f"任务修改请求: {_json.dumps(user_task_mod, ensure_ascii=False)}")
            if user_rejection:
                mod_parts.append(f"拒绝原因: {user_rejection}")
            if user_requested_strategy:
                mod_parts.append(f"请求的新策略: {user_requested_strategy}")

            user_modification_context = "\n".join(mod_parts)

        #  v7.144: 优先使用需求洞察生成的 restructured_requirements（更完整），回退到标准流程的 structured_requirements
        restructured_requirements = state.get("restructured_requirements", {})
        structured_requirements = state.get("structured_requirements", {})

        if restructured_requirements:
            logger.info(" [v7.144] 使用需求洞察生成的 restructured_requirements 进行角色选择")
            requirements = restructured_requirements
        else:
            logger.info(" [v7.144] 使用标准流程的 structured_requirements 进行角色选择")
            requirements = structured_requirements

        requirements_text = self._format_requirements_for_selection(requirements)

        # v8.0 P0-T4: 注入设计模式标签到需求文本，让LLM感知模式上下文
        try:
            from intelligent_project_analyzer.services.mode_question_loader import extract_detected_modes_from_state

            detected_modes_for_text = extract_detected_modes_from_state(state)
            if detected_modes_for_text:
                MODE_LABELS = {
                    "M1_concept_driven": "概念驱动型",
                    "M2_functional_efficiency": "功能效率型",
                    "M3_emotional_experience": "情感体验型",
                    "M4_capital_asset": "资本资产型",
                    "M5_rural_context": "乡建在地型",
                    "M6_urban_regeneration": "城市更新型",
                    "M7_technology_integration": "技术整合型",
                    "M8_extreme_condition": "极端条件型",
                    "M9_social_structure": "社会结构型",
                    "M10_future_speculation": "未来推演型",
                    "M11_healthcare_healing": "健康疗愈型",
                }
                mode_lines = ["\n## 设计模式上下文"]
                for m in detected_modes_for_text:
                    mode_id = m.get("mode", "")
                    confidence = m.get("confidence", 0)
                    label = MODE_LABELS.get(mode_id, mode_id)
                    mode_lines.append(f"- {mode_id} ({label}), 置信度: {confidence:.2f}")
                mode_lines.append("")
                requirements_text += "\n".join(mode_lines)
                logger.info(f"[v8.0 P0-T4] 已注入 {len(detected_modes_for_text)} 个模式标签到需求文本")
        except Exception as e:
            logger.warning(f"[v8.0 P0-T4] 模式标签注入失败: {e}")

        #  v7.106: 获取用户确认的核心任务
        confirmed_tasks = state.get("confirmed_core_tasks", [])
        if confirmed_tasks:
            logger.info(f" [v7.106] 检测到 {len(confirmed_tasks)} 个用户确认的核心任务，将融合到角色选择中")

        # v7.700 P0: 注入模式必需任务到任务列表
        try:
            detected_modes = extract_detected_modes_from_state(state)
            if detected_modes:
                logger.info(f"🎯 [v7.700 P0] 检测到 {len(detected_modes)} 个设计模式，注入必需任务")

                # 获取模式必需任务
                # v9.2 fix: get_mandatory_tasks_for_modes 返回 Tuple[List, Optional[ResolutionResult]]，必须解包
                mandatory_tasks, mode_resolution_result = ModeTaskLibrary.get_mandatory_tasks_for_modes(
                    detected_modes,
                    include_p1=True,  # 包含P1推荐任务
                    include_p2=False,  # 不包含P2可选任务
                )

                if mode_resolution_result:
                    logger.info(f"   混合模式解决策略: {mode_resolution_result}")

                if mandatory_tasks:
                    logger.info(f"   注入 {len(mandatory_tasks)} 个模式必需任务")

                    # 将模式任务转换为可用格式并合并到 confirmed_tasks
                    mode_task_objects = []
                    for task in mandatory_tasks:
                        task_obj = {
                            "title": f"[{task['priority']}] {task['task_name']}",
                            "description": f"{task['description']} (目标专家: {task['target_expert']})",
                            "task_id": task["task_id"],
                            "priority": task["priority"],
                            "target_expert": task["target_expert"],
                            "source": "mode_library",
                            "source_mode": task["source_mode"],
                        }
                        mode_task_objects.append(task_obj)

                    # 合并用户确认任务和模式必需任务
                    if confirmed_tasks:
                        confirmed_tasks = confirmed_tasks + mode_task_objects
                    else:
                        confirmed_tasks = mode_task_objects

                    logger.info(f"   合并后总任务数: {len(confirmed_tasks)}")

                    # 更新 state 中的 confirmed_tasks
                    state = dict(state)
                    state["confirmed_core_tasks"] = confirmed_tasks

        except Exception as e:
            logger.warning(f"⚠️ [v7.700 P0] 模式任务注入失败: {e}，继续使用原始任务列表")

        # =====================================================================
        # ⚠️ v9.1 G3: 能力缺口检测 + 遗漏任务补充
        # 对比 confirmed_tasks 覆盖的能力 vs 检测模式所需能力，补充遗漏
        # =====================================================================
        try:
            if confirmed_tasks and detected_modes_for_text:
                # 收集所有任务已覆盖的关键词
                covered_keywords: set[str] = set()
                for task in confirmed_tasks:
                    text = (task.get("title", "") + " " + task.get("description", "")).lower()
                    covered_keywords.update(w for w in text.split() if len(w) >= 2)

                # 定义各模式的关键能力维度
                mode_required_keywords = {
                    "M1_concept_driven": ["概念", "哲学", "理论", "叙事"],
                    "M2_function_efficiency": ["功能", "效率", "流线", "动线", "规范"],
                    "M3_emotional_experience": ["情感", "体验", "氛围", "感知", "情绪"],
                    "M4_capital_asset": ["投资", "回报", "商业", "运营", "成本"],
                    "M5_rural_context": ["乡村", "在地", "风土", "村落", "传统"],
                    "M6_urban_regeneration": ["更新", "活化", "城市", "社区", "公共"],
                    "M7_tech_integration": ["技术", "数字", "智能", "BIM", "参数化"],
                    "M8_extreme_condition": ["极端", "韧性", "灾害", "气候", "防护"],
                    "M9_social_structure": ["社会", "治理", "参与", "公平", "包容"],
                    "M10_future_speculation": ["未来", "推演", "预测", "情景", "趋势"],
                    "M11_healthcare_healing": ["疗愈", "健康", "康复", "安全感", "舒适"],
                    "M12_ecological_regenerative": ["生态", "再生", "碳", "生物", "自然"],
                }

                supplement_tasks = []
                for mode_info in detected_modes_for_text[:2]:  # 只检查前2个模式
                    mode_id = mode_info.get("mode", "")
                    required = mode_required_keywords.get(mode_id, [])
                    # 检查哪些关键能力未被覆盖
                    uncovered = [kw for kw in required if not any(kw in ck for ck in covered_keywords)]
                    if len(uncovered) >= 2:  # 至少2个关键能力未覆盖才补充
                        supplement_task = {
                            "title": f"[补充] {mode_id}模式关键维度调研",
                            "description": f"补充调研: {'、'.join(uncovered)}（自动检测到{mode_id}模式下这些维度未被现有任务覆盖）",
                            "task_id": f"supplement_{mode_id}",
                            "priority": "P1",
                            "source": "capability_gap_v9.1",
                            "source_mode": mode_id,
                            "task_type": "research",
                        }
                        supplement_tasks.append(supplement_task)
                        logger.info(f"🔍 [v9.1 G3] {mode_id} 能力缺口: {uncovered} → 补充1个任务")

                if supplement_tasks:
                    confirmed_tasks = confirmed_tasks + supplement_tasks
                    state = dict(state)
                    state["confirmed_core_tasks"] = confirmed_tasks
                    logger.info(f"✅ [v9.1 G3] 补充 {len(supplement_tasks)} 个遗漏任务，总数: {len(confirmed_tasks)}")
                else:
                    logger.info("✅ [v9.1 G3] 能力缺口检测通过，无需补充")
        except Exception as e:
            logger.warning(f"⚠️ [v9.1 G3] 能力缺口检测失败: {e}，继续使用现有任务列表")

        #  v7.140: 验证循环（最多3次）
        max_validation_retries = 3
        validation_passed = False
        final_validation_report = None
        selection = None

        for attempt in range(max_validation_retries):
            logger.info(f" [v7.140] 任务分配尝试 {attempt + 1}/{max_validation_retries}")

            # 使用动态项目总监选择角色（由LLM自主判断复杂度）
            try:
                # 检查是否有修正反馈（第2次及以后的尝试）
                correction_feedback = state.get("correction_feedback", "")
                if correction_feedback:
                    logger.warning(f" [v7.140] 收到修正反馈，将调整任务分配：\n{correction_feedback}")

                # v9.2 fix: 将用户审核反馈融入 correction_feedback
                if user_modification_context and not correction_feedback:
                    correction_feedback = user_modification_context
                    logger.info(f"🔄 [v9.2] 将用户审核请求作为修正反馈注入 LLM prompt")
                elif user_modification_context and correction_feedback:
                    correction_feedback = f"{correction_feedback}\n\n{user_modification_context}"
                    logger.info(f"🔄 [v9.2] 将用户审核请求追加到已有修正反馈")

                #  v7.106: 如果有核心任务，传递给 select_roles_for_task
                # v8.2: 同时传递 primary_deliverables 用于交付物约束验证
                _primary_deliverables = requirements.get("primary_deliverables", [])

                if self.dynamic_director is None:
                    raise RuntimeError("dynamic_director 未初始化")

                if confirmed_tasks:
                    # 构建包含核心任务的增强需求文本
                    requirements_with_tasks = self._format_requirements_with_tasks(requirements_text, confirmed_tasks)

                    #  v7.140: 如果有修正反馈，添加到需求文本中
                    if correction_feedback:
                        requirements_with_tasks += f"\n\n## 修正要求\n{correction_feedback}"

                    selection = self.dynamic_director.select_roles_for_task(
                        requirements_with_tasks,
                        confirmed_core_tasks=confirmed_tasks,  # 传递用于验证
                        primary_deliverables=_primary_deliverables,  # v8.2: 约束验证
                    )
                else:
                    if correction_feedback:
                        requirements_text_with_feedback = f"{requirements_text}\n\n## 修正要求\n{correction_feedback}"
                    else:
                        requirements_text_with_feedback = requirements_text

                    selection = self.dynamic_director.select_roles_for_task(
                        requirements_text_with_feedback,
                        primary_deliverables=_primary_deliverables,  # v8.2: 约束验证
                    )

                logger.info(f"Dynamic director selected {len(selection.selected_roles)} roles")
                logger.debug(f"Selected roles: {selection.selected_roles}")

                #  v7.140: 立即验证任务分配
                strategic_analysis_for_validation = {
                    "selected_roles": selection.selected_roles,
                    "task_distribution": selection.task_distribution,
                    "execution_batches": selection.execution_batches if hasattr(selection, "execution_batches") else [],
                }

                validation_report = _validate_task_distribution_embedded(state, strategic_analysis_for_validation)
                final_validation_report = validation_report

                logger.info(f" [v7.140] 验证结果（第{attempt + 1}次）: {validation_report['status']}")
                logger.info(f"   {validation_report['summary']}")

                if validation_report["status"] == "passed":
                    # 验证通过，直接退出循环
                    validation_passed = True
                    logger.info(" [v7.140] 任务分配验证通过！")
                    break

                elif validation_report["status"] == "failed" and attempt < max_validation_retries - 1:
                    # 验证失败，生成修正反馈
                    correction_feedback = _generate_correction_feedback(validation_report)
                    logger.warning(f" [v7.140] 任务分配验证失败，准备重试 ({attempt + 2}/{max_validation_retries})")

                    # 注入反馈到 state，供下一轮迭代使用
                    state = dict(state)
                    state["correction_feedback"] = correction_feedback
                    state["previous_validation_issues"] = validation_report["issues"]

                    # 继续下一轮
                    continue

                else:
                    # 达到最大重试或状态为 warning
                    if validation_report["status"] == "warning":
                        validation_passed = True  # warning 状态也算通过，但有警告
                        logger.warning("️  [v7.140] 任务分配存在警告，但可继续执行")
                    else:
                        logger.warning("️  [v7.140] 任务分配验证未完全通过，已达最大重试次数")
                    break

            except Exception as e:
                logger.error(f"Failed to select roles dynamically (attempt {attempt + 1}): {e}")
                if _is_auth_401_error(str(e)):
                    logger.error(" 检测到认证错误(401)，停止角色选择重试")
                    raise RuntimeError(f"LLM_AUTH_401: {e}") from e
                if attempt == max_validation_retries - 1:
                    raise ValueError(f"Dynamic role selection failed after {max_validation_retries} attempts: {e}")
                continue

        # 如果循环结束后仍无有效 selection，抛出错误
        if selection is None:
            raise ValueError("Failed to generate valid task distribution")

        #  能力边界检查：验证任务分派前的交付物能力
        primary_deliverables = requirements.get("primary_deliverables", [])
        if primary_deliverables:
            logger.info(" [CapabilityBoundary] 验证任务分派前的交付物能力")
            boundary_check = CapabilityBoundaryService.check_deliverable_list(
                deliverables=primary_deliverables,
                context={
                    "node": "project_director",
                    "stage": "before_assignment",
                    "session_id": state.get("session_id", ""),
                },
            )

            logger.info(" 交付物能力边界检查结果:")
            logger.info(f"   在能力范围内: {boundary_check.within_capability}")
            logger.info(f"   能力匹配度: {boundary_check.capability_score:.2f}")

            # 如果有超出能力的交付物，标记限制说明
            if not boundary_check.within_capability:
                logger.warning("️ 部分交付物超出能力范围，已标记限制说明")

                for i, deliv in enumerate(primary_deliverables):
                    deliv_type = deliv.get("type", "")

                    # 查找对应的检查结果
                    for check in boundary_check.deliverable_checks:
                        if not check.within_capability and check.original_type == deliv_type:
                            # 标记受限的交付物
                            deliv["capability_limited"] = True
                            deliv["limitation_note"] = check.transformation_reason or "超出系统能力范围"
                            logger.info(f"     - {deliv.get('deliverable_id', f'D{i + 1}')}: {deliv_type} (受限)")
                            break
            else:
                logger.info(" 所有交付物在能力范围内")

        # 创建动态智能体的Send命令
        parallel_commands = []
        dynamic_agents_info = {}

        for role in selection.selected_roles:
            try:
                #  从 RoleObject 中提取 role_id
                if isinstance(role, dict):
                    short_role_id = role.get("role_id", "")
                elif hasattr(role, "role_id"):
                    short_role_id = role.role_id
                else:
                    short_role_id = role  # 兼容旧格式（字符串）

                #  构造完整的角色ID（如 "V2_设计总监_2-1"）
                role_id = self._construct_full_role_id(short_role_id)

                logger.info(f" [DEBUG] Processing role: short_id={short_role_id}, full_id={role_id}")

                # 解析角色ID
                if self.role_manager is None:
                    continue
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
                    #  构建专家上下文，包含任务优先级信息
                    expert_context = {**state, "confirmed_core_tasks": confirmed_tasks}  # 传递确认任务（含优先级）

                    parallel_commands.append(
                        Send(
                            "dynamic_role_executor",  # 动态角色执行节点
                            {
                                "role_id": role_id,
                                "role_config": role_config,
                                "task": task_description,
                                "context": expert_context,  # 使用增强的上下文
                            },
                        )
                    )

                    # 记录角色信息
                    dynamic_agents_info[role_id] = {
                        "name": role_config.get("name", "未知角色"),
                        "task": task_description,
                    }

            except Exception as e:
                logger.error(f"Failed to create command for role {role_id}: {e}")

        # 如果没有成功创建任何命令，抛出错误
        if not parallel_commands:
            logger.error("No dynamic agents created")
            raise ValueError("Failed to create any dynamic agent commands")

        # 创建 subagents 字典，用于 V2-V6 agents 获取任务描述
        # 将动态角色映射到固定的 V2-V6 键
        subagents_mapping = {}
        role_to_v_mapping: Dict[str, List[str]] = {"V2": [], "V3": [], "V4": [], "V5": [], "V6": []}

        # 将选中的角色按类型分组
        for role in selection.selected_roles:
            #  从 RoleObject 中提取 role_id
            if isinstance(role, dict):
                short_role_id = role.get("role_id", "")
            elif hasattr(role, "role_id"):
                short_role_id = role.role_id
            else:
                short_role_id = role  # 兼容旧格式

            #  构造完整的角色ID
            role_id = self._construct_full_role_id(short_role_id)

            if self.role_manager is None:
                continue
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
            #  构造完整角色ID列表传给 BatchScheduler
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

        #  序列化 selected_roles 为字典列表（保留完整信息）
        #  Phase 0优化: 排除None和默认值
        serialized_roles = [
            role.model_dump(exclude_none=True, exclude_defaults=True) if hasattr(role, "model_dump") else role
            for role in selection.selected_roles
        ]

        # ============================================================================
        # v15.0: 从 RoleSelection 后处理构建 DWP 列表 + 覆盖率验证
        # ============================================================================
        from intelligent_project_analyzer.agents.dynamic_project_director import build_dwps_from_role_selection
        from intelligent_project_analyzer.core.task_oriented_models import validate_dwp_coverage

        dwp_list = []
        dwp_coverage_report = None
        try:
            dwp_list = build_dwps_from_role_selection(
                selection, confirmed_tasks,
                questionnaire_summary=state.get("questionnaire_summary"),
            )
            if confirmed_tasks:
                if dwp_list:
                    dwp_coverage_report = validate_dwp_coverage(confirmed_tasks, dwp_list)
                    logger.info(f"📊 [v15.0] DWP 覆盖率: {dwp_coverage_report['coverage_rate']:.1%}")
                    logger.info(f"   {dwp_coverage_report['details']}")
                else:
                    # Gap 6 fix: dwp_list 为空时，所有 confirmed_tasks 都未覆盖
                    logger.warning("⚠️ [v10.0] DWP 列表为空，所有已确认任务均未覆盖")
                    all_task_ids = {t.get("task_id") or t.get("id", "") for t in confirmed_tasks}
                    dwp_coverage_report = {
                        "covered": False,
                        "coverage_rate": 0.0,
                        "covered_task_ids": set(),
                        "uncovered_task_ids": all_task_ids,
                        "details": f"DWP 列表为空，{len(all_task_ids)} 个任务未覆盖",
                    }
                if not dwp_coverage_report.get("covered", True):
                    uncovered_ids = dwp_coverage_report["uncovered_task_ids"]
                    logger.warning(f"⚠️ [v15.0] 未覆盖的任务: {uncovered_ids}")

                    # ================================================================
                    # v9.2 fix: 为未覆盖任务自动补建 fallback DWP
                    # 确保 100% 的 confirmed_core_tasks 都有对应的 DWP
                    # ================================================================
                    uncovered_tasks = [
                        t for t in confirmed_tasks
                        if (t.get("task_id") or t.get("id", "")) in uncovered_ids
                    ]
                    if uncovered_tasks:
                        # 按 priority 分组，high → medium → low
                        from intelligent_project_analyzer.core.task_oriented_models import (
                            DeliverableWorkPackage, Priority, DeliverableFormat,
                        )
                        # 找到任务数最少的角色作为 fallback owner
                        role_task_counts = {}
                        for dwp in dwp_list:
                            owner = getattr(dwp, "owner_role_id", "unassigned")
                            role_task_counts[owner] = role_task_counts.get(owner, 0) + 1
                        # 所有已选角色
                        all_role_ids = [
                            r.role_id if hasattr(r, "role_id") else r.get("role_id", "")
                            for r in selection.selected_roles
                        ]
                        fallback_dwp_count = len(dwp_list)
                        supplemented = 0
                        for task in uncovered_tasks:
                            task_id = task.get("task_id") or task.get("id", "unknown")
                            task_title = task.get("title", "未命名任务")
                            task_desc = task.get("description", "")
                            task_priority = task.get("priority", "medium")
                            target_expert = task.get("target_expert", "")

                            # 优先分配给 target_expert 指定的角色，否则分配给任务最少的角色
                            owner_role = ""
                            if target_expert:
                                for rid in all_role_ids:
                                    if target_expert in rid or rid in target_expert:
                                        owner_role = rid
                                        break
                            if not owner_role and all_role_ids:
                                owner_role = min(all_role_ids, key=lambda r: role_task_counts.get(r, 0))

                            fallback_dwp_count += 1
                            try:
                                fallback_dwp = DeliverableWorkPackage(
                                    dwp_id=f"DWP-{fallback_dwp_count:03d}",
                                    name=task_title,
                                    description=task_desc or task_title,
                                    deliverable_type="analysis_report",
                                    format=DeliverableFormat.ANALYSIS,
                                    source_task_ids=[task_id],
                                    owner_role_id=owner_role or "unassigned",
                                    contributor_role_ids=[],
                                    depends_on=[],
                                    priority=Priority.HIGH if task_priority == "high" else (
                                        Priority.LOW if task_priority == "low" else Priority.MEDIUM
                                    ),
                                    success_criteria=[f"完成 {task_title} 的分析与交付"],
                                    constraints=[],
                                    require_search=False,
                                    is_auto_supplemented=True,
                                )
                                dwp_list.append(fallback_dwp)
                                role_task_counts[owner_role] = role_task_counts.get(owner_role, 0) + 1
                                supplemented += 1
                            except Exception as dwp_err:
                                logger.warning(f"⚠️ [v9.2] 为任务 {task_id} 补建 DWP 失败: {dwp_err}")

                        logger.info(
                            f"🔄 [v9.2] 为 {supplemented} 个未覆盖任务自动补建了 fallback DWP，"
                            f"总数: {len(dwp_list)}"
                        )
                        # 重新验证覆盖率
                        dwp_coverage_report = validate_dwp_coverage(confirmed_tasks, dwp_list)
                        logger.info(f"📊 [v9.2] 补建后 DWP 覆盖率: {dwp_coverage_report['coverage_rate']:.1%}")
            else:
                logger.info(f"📊 [v15.0] 构建了 {len(dwp_list)} 个 DWP（无核心任务用于覆盖率验证）")
        except Exception as e:
            logger.warning(f"⚠️ [v15.0] DWP 构建失败（不影响主流程）: {e}")

        # 序列化 DWP 以写入 state
        serialized_dwps = []
        for dwp in dwp_list:
            try:
                serialized_dwps.append(dwp.model_dump(exclude_none=True) if hasattr(dwp, "model_dump") else dwp.dict())
            except Exception:
                serialized_dwps.append({"dwp_id": getattr(dwp, "dwp_id", "?"), "error": "serialization_failed"})

        # v7.700 P0: 模式任务覆盖率验证
        mode_task_coverage = None
        try:
            detected_modes = extract_detected_modes_from_state(state)
            if detected_modes:
                logger.info("🔍 [v7.700 P0] 验证模式任务覆盖率")

                # 将 task_distribution 转换为任务列表
                allocated_tasks = []
                for role_id, task_data in selection.task_distribution.items():
                    if hasattr(task_data, "tasks"):
                        task_list = task_data.tasks
                    elif isinstance(task_data, dict) and "tasks" in task_data:
                        task_list = task_data["tasks"]
                    else:
                        task_list = [str(task_data)]

                    for task_desc in task_list:
                        allocated_tasks.append({"role_id": role_id, "description": task_desc})

                # 验证覆盖率
                coverage_result = ModeTaskLibrary.validate_task_coverage(detected_modes, allocated_tasks)

                mode_task_coverage = coverage_result

                if coverage_result["status"] == "failed":
                    logger.warning(f"⚠️ [v7.700 P0] 模式任务覆盖率验证失败: {coverage_result['summary']}")
                    if coverage_result["missing_p0_tasks"]:
                        logger.warning("   缺失P0任务:")
                        for missing_task in coverage_result["missing_p0_tasks"]:
                            logger.warning(
                                f"      - {missing_task['task_id']}: {missing_task['task_name']} "
                                f"(目标: {missing_task['target_expert']})"
                            )
                elif coverage_result["status"] == "warning":
                    logger.warning(f"⚠️ [v7.700 P0] {coverage_result['summary']}")
                else:
                    logger.info(f"✅ [v7.700 P0] {coverage_result['summary']}")

        except Exception as e:
            logger.warning(f"⚠️ [v7.700 P0] 模式任务覆盖率验证失败: {e}")

        # 更新状态
        state_update = {
            "strategic_analysis": {
                "strategy_overview": selection.reasoning,
                "selected_roles": serialized_roles,  # 保存完整的 RoleObject 列表
                "task_distribution": selection.task_distribution,
                "execution_mode": "dynamic",
                # v7.700 P0: 模式任务覆盖率验证结果
                "mode_task_coverage": mode_task_coverage,
                # v9.0: 框架选择 — LLM 自主决定的分析框架
                "analysis_framework": getattr(selection, "analysis_framework", None) or "ability_core",
            },
            "subagents": subagents_mapping,  # 添加 subagents 字段
            "dynamic_agents": dynamic_agents_info,
            "active_agents": [
                self._construct_full_role_id(role.role_id)
                if hasattr(role, "role_id")
                else self._construct_full_role_id(role)
                for role in selection.selected_roles
            ],  # active_agents 存储完整角色ID（如 "V2_设计总监_2-1"）
            "execution_mode": "dynamic",
            # New: Batch execution fields
            "execution_batches": execution_batches,  # List[List[str]] - batch list
            "current_batch": current_batch,  # int - current batch number (1-based)
            "total_batches": total_batches,  # int - total number of batches
            #  v7.140: 验证报告字段
            "validation_report": final_validation_report,  # Dict - 验证结果
            "validation_passed": validation_passed,  # bool - 是否通过验证
            "validation_retry_count": attempt + 1,  # int - 验证重试次数
            # v15.0: DWP 数据
            "deliverable_work_packages": serialized_dwps,  # List[Dict] - DWP
            "dwp_coverage_report": dwp_coverage_report,  # Dict - 覆盖率报告
        }

        end_time = time.time()
        self._track_execution_time(start_time, end_time)

        logger.info(f"Dynamic mode analysis completed, dispatching {len(parallel_commands)} dynamic agents")
        if final_validation_report:
            logger.info(f" [v7.140] 验证报告: {final_validation_report['summary']}")
            if validation_passed:
                logger.info(" [v7.140] 任务分配已通过验证")
            else:
                logger.warning("️  [v7.140] 任务分配存在警告，详情见 state.validation_report")

        # 返回Command对象
        return Command(update=state_update, goto=parallel_commands)

    def _format_requirements_with_tasks(self, requirements_text: str, confirmed_tasks: List[Dict[str, Any]]) -> str:
        """
        格式化需求信息并融合用户确认的核心任务（v7.106新增, v15.0 DWP 增强）

        v15.0 变更: 除自然语言描述外，同时传递结构化 JSON（含 task_id, title, priority,
        dependencies, source_keywords），使 LLM 可在输出中引用 task_id 建立追溯。

        Args:
            requirements_text: 原始需求文本
            confirmed_tasks: 用户确认的核心任务列表

        Returns:
            增强的需求文本，包含核心任务信息（自然语言 + 结构化 JSON）
        """
        enhanced_text = requirements_text

        enhanced_text += "\n\n# 用户确认的核心任务（优先级最高！）\n\n"
        enhanced_text += "用户在问卷环节已经确认了以下核心任务，你在分配专家任务时**必须围绕这些核心任务展开**：\n\n"

        for i, task in enumerate(confirmed_tasks, 1):
            task_id = task.get("task_id") or task.get("id", f"task_{i}")
            enhanced_text += f"\n**核心任务 {i} [{task_id}]: {task.get('title')}**\n"
            enhanced_text += f"- 描述: {task.get('description')}\n"
            enhanced_text += f"- 类型: {task.get('type')}\n"
            if task.get("motivation"):
                enhanced_text += f"- 动机: {task.get('motivation')}\n"
            if task.get("priority"):
                enhanced_text += f"- 优先级: {task.get('priority')}\n"
            if task.get("dependencies"):
                enhanced_text += f"- 依赖: {', '.join(task['dependencies'])}\n"
            # 如果任务有信息依赖，也要告知项目总监
            if task.get("missing_info"):
                enhanced_text += f"- ️ 信息缺失: {', '.join(task['missing_info'])} (用户已在问卷中补充)\n"

        # v15.0: 附加结构化 JSON 供 LLM 在 DWP 的 source_task_ids 中引用
        import json

        task_json_list = []
        for task in confirmed_tasks:
            task_json_list.append(
                {
                    "task_id": task.get("task_id") or task.get("id", ""),
                    "title": task.get("title", ""),
                    "priority": task.get("priority", "P1"),
                    "type": task.get("type", ""),
                    "dependencies": task.get("dependencies", []),
                    "source_keywords": task.get("source_keywords", []),
                    "category": task.get("category", ""),
                }
            )

        enhanced_text += "\n\n## 核心任务结构化索引（JSON）\n"
        enhanced_text += "以下为核心任务的结构化数据。在生成 DWP 时，**必须在 source_task_ids 中引用这些 task_id**：\n"
        enhanced_text += f"```json\n{json.dumps(task_json_list, ensure_ascii=False, indent=2)}\n```\n"

        enhanced_text += (
            "\n⚠️ **重要**：你分配给专家的任务必须与上述核心任务对齐，确保最终输出能回答用户确认的核心问题。\n"
        )
        enhanced_text += "每个交付物工作包(DWP)的 source_task_ids 必须引用上述 task_id，实现 100% 覆盖。\n"

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
from .base import AgentFactory  # noqa: E402

AgentFactory.register_agent(AgentType.PROJECT_DIRECTOR, ProjectDirectorAgent)
