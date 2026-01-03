"""
角色选择与任务分派统一审核节点
Role Selection and Task Assignment Unified Review Node

合并角色选择审核和任务分派审核，减少人机交互次数
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from langgraph.types import Command, interrupt
from loguru import logger

from intelligent_project_analyzer.core.state import AnalysisStage
from intelligent_project_analyzer.core.strategy_manager import StrategyManager
from intelligent_project_analyzer.services.capability_boundary_service import CapabilityBoundaryService


def _normalize_role_id(role_id: Any) -> str:
    """Normalize role identifiers into the short form used by deliverable IDs.

    Examples:
        "V2_设计总监_2-1" -> "2-1"
        "2-1" -> "2-1"
        "" -> ""
        None -> "None"  (kept for backward compatibility with existing tests)

    Notes:
        Some parts of the system use a verbose role id (with prefix and role name), while
        deliverables often key by the trailing numeric id like "2-1".
    """
    if role_id is None:
        return "None"

    s = str(role_id)
    if not s:
        return s

    # Prefer the trailing pattern like "2-1" if present.
    m = re.search(r"(\d+-\d+)$", s)
    if m:
        return m.group(1)

    # Fallback: if it contains underscores, try the last segment.
    if "_" in s:
        last = s.split("_")[-1]
        if re.fullmatch(r"\d+-\d+", last):
            return last

    return s


class RoleTaskUnifiedReviewNode:
    """角色选择与任务分派统一审核节点"""

    def __init__(self):
        """初始化审核节点"""
        self.strategy_manager = StrategyManager()
        logger.info("✅ Role-Task unified review node initialized")

    def execute(self, state: Dict[str, Any]) -> Command[Literal["batch_executor", "project_director"]]:
        """
        执行统一审核：同时审核角色选择和任务分派

        Args:
            state: 当前状态

        Returns:
            Command对象，指向下一节点
        """
        logger.info("🔍 Starting unified role & task review interaction")

        # 🔥 强制执行人工审核 - 不再跳过角色任务审核
        logger.info("📋 角色任务审核：需要人工确认")

        # 获取项目总监的分析结果
        strategic_analysis = state.get("strategic_analysis") or {}  # 🔥 修复：确保不为 None

        if not strategic_analysis:
            logger.error("❌ No strategic_analysis found in state")
            logger.debug(f"Available state keys: {list(state.keys())}")
            raise ValueError("Missing strategic_analysis in state")

        # ===== 第一部分：角色选择审核 =====
        selected_roles = strategic_analysis.get("selected_roles", [])
        selection_reasoning = strategic_analysis.get("strategy_overview", "")
        strategy_name = "goal_oriented_adaptive_collaboration_v7.2"

        logger.info(f"📋 Project director selected {len(selected_roles)} roles")

        # 验证角色选择
        role_validation = self.strategy_manager.validate_role_selection(selected_roles, strategy_name)

        # 获取互补性推荐
        complementary_recommendations = self.strategy_manager.get_complementary_recommendations(
            selected_roles, strategy_name
        )

        # 生成角色选择决策说明
        role_decision_explanation = self.strategy_manager.generate_decision_explanation(
            strategy_name=strategy_name,
            selected_roles=selected_roles,
            reasoning=selection_reasoning,
            alternatives=None,
            confidence=strategic_analysis.get("confidence", None),
        )

        # ===== 第二部分：任务分派审核 =====
        task_distribution = strategic_analysis.get("task_distribution", {})

        # 生成详细任务清单
        detailed_task_list, actual_tasks = self._generate_detailed_task_list(selected_roles, task_distribution)

        # 验证任务分配
        task_validation = self._validate_task_assignment(selected_roles, actual_tasks)

        # 获取任务分配原则
        assignment_principles = self.strategy_manager.get_assignment_principles()

        # 计算任务统计
        total_tasks = sum(len(role.get("tasks", [])) for role in detailed_task_list)
        roles_with_tasks = sum(1 for role in detailed_task_list if role.get("tasks"))

        task_summary = {
            "total_roles": len(detailed_task_list),
            "total_tasks": total_tasks,
            "roles_with_tasks": roles_with_tasks,
        }

        # ===== 第三部分：生成工具和概念图设置 =====
        tool_settings = self._generate_tool_settings(selected_roles)
        concept_image_settings = self._generate_concept_image_settings(selected_roles)

        # ===== 构建统一的交互数据 =====
        interaction_data = {
            "interaction_type": "role_and_task_unified_review",
            "message": "项目总监已完成角色选择和任务分派，请审核并确认：",
            # 角色选择部分
            "role_selection": {
                "decision_explanation": role_decision_explanation,
                "selected_roles": self._format_roles_for_review(selected_roles),
                "validation": role_validation,
                "recommendations": complementary_recommendations,
                "strategy_info": {
                    "current_strategy": strategy_name,
                    "available_strategies": [
                        {
                            "name": "goal_oriented_adaptive_collaboration_v7.2",
                            "description": "以最终输出结构为导向，自适应选择协同模式，并强制生成和应用动态角色名称。",
                        }
                    ],
                },
            },
            # 任务分派部分
            "task_assignment": {
                "task_list": detailed_task_list,
                "validation": task_validation,
                "assignment_principles": assignment_principles,
                "summary": task_summary,
            },
            # 🆕 工具设置
            "tool_settings": tool_settings,
            # 🆕 概念图设置
            "concept_image_settings": concept_image_settings,
            # 操作选项
            "options": {
                "approve": "确认角色和任务，开始执行",
                "modify_roles": "修改角色选择",
                "modify_tasks": "修改任务分配",
                "change_strategy": "更换选择策略",
                "reject": "拒绝并重新规划",
            },
        }

        logger.info(f"📤 Sending unified review request to user")
        logger.debug(f"Review data: {len(selected_roles)} roles, {total_tasks} tasks")

        # 触发人机交互，等待用户响应
        user_decision = interrupt(interaction_data)

        # 🔧 P1修复: 处理字符串或字典类型的user_decision
        if isinstance(user_decision, str):
            # 简单模式：字符串直接作为action
            decision_dict = {"action": user_decision}
            logger.info(f"📥 User decision received (string): {user_decision}")
        elif isinstance(user_decision, dict):
            # 复杂模式：字典包含action和其他字段
            decision_dict = user_decision
            logger.info(f"📥 User decision received (dict): {decision_dict.get('action', 'unknown')}")
        else:
            # 异常类型：默认approve
            logger.warning(f"⚠️ Unexpected user_decision type: {type(user_decision)}, defaulting to approve")
            decision_dict = {"action": "approve"}

        # ===== 处理用户决策 =====
        return self._handle_user_decision(state, decision_dict, interaction_data)

    def _format_roles_for_review(self, selected_roles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """格式化角色信息供审核"""
        formatted_roles = []
        for role in selected_roles:
            # 🔥 P1修复: 优先从 task_instruction 提取信息
            tasks = role.get("tasks", [])
            focus_areas = role.get("focus_areas", [])
            expected_output = role.get("expected_output", "")

            if not tasks and "task_instruction" in role:
                task_instruction = role["task_instruction"]
                if isinstance(task_instruction, dict) and "deliverables" in task_instruction:
                    # 🔥 P1修复: 格式化任务描述，包含交付物名称
                    tasks = [
                        f"【{d.get('name', '')}】{d.get('description', '')}"
                        for d in task_instruction.get("deliverables", [])
                    ]
                    focus_areas = [d.get("name", "") for d in task_instruction.get("deliverables", [])]

                    # 🔥 P1修复: 格式化预期输出，包含验收标准
                    objective = task_instruction.get("objective", "")
                    success_criteria = task_instruction.get("success_criteria", [])
                    if success_criteria:
                        criteria_str = "；".join(success_criteria)
                        expected_output = f"{objective}\n\n[验收标准] {criteria_str}"
                    else:
                        expected_output = objective

            formatted_roles.append(
                {
                    "role_id": role.get("role_id", ""),
                    "role_name": role.get("dynamic_role_name") or role.get("role_name", ""),
                    "tasks": tasks,
                    "focus_areas": focus_areas,
                    "expected_output": expected_output,
                    "dependencies": role.get("dependencies", []),
                }
            )
        return formatted_roles

    def _generate_detailed_task_list(
        self, selected_roles: List[Dict[str, Any]], task_distribution: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        生成详细任务清单

        Returns:
            (包含模板任务的列表, 仅实际任务的列表)
        """
        detailed_task_list = []
        actual_tasks = []

        for i, role in enumerate(selected_roles, 1):
            role_id = role.get("role_id", f"role_{i}")
            static_role_name = role.get("role_id", role_id)
            dynamic_role_name = role.get("dynamic_role_name") or role.get("role_name", "")

            # 提取角色的任务
            role_tasks = role.get("tasks", [])

            # 🔥 P1修复: 如果 tasks 为空但有 task_instruction (v2格式)，从中提取
            if not role_tasks and "task_instruction" in role:
                task_instruction = role["task_instruction"]
                if isinstance(task_instruction, dict) and "deliverables" in task_instruction:
                    # 格式化任务描述：【交付物名称】描述
                    role_tasks = [
                        f"【{d.get('name', '')}】{d.get('description', '')}"
                        for d in task_instruction.get("deliverables", [])
                    ]

                    # 同时补全其他字段
                    if not role.get("expected_output"):
                        objective = task_instruction.get("objective", "")
                        success_criteria = task_instruction.get("success_criteria", [])
                        if success_criteria:
                            criteria_str = "；".join(success_criteria)
                            role["expected_output"] = f"{objective}\n\n[验收标准] {criteria_str}"
                        else:
                            role["expected_output"] = objective

                    if not role.get("focus_areas"):
                        role["focus_areas"] = [d.get("name", "") for d in task_instruction.get("deliverables", [])]

                    # 回填到 role 对象中以便后续使用
                    role["tasks"] = role_tasks
                    logger.info(f"🔄 Extracted {len(role_tasks)} tasks from task_instruction for role {role_id}")

            # 为每个任务生成详细信息
            task_details = []
            for j, task in enumerate(role_tasks, 1):
                task_id = f"{role_id}_task_{j}"
                task_detail = {
                    "task_id": task_id,
                    "description": task,
                    "priority": "high" if j <= 2 else "medium",  # 前2个任务高优先级
                    "estimated_effort": "待评估",
                }
                task_details.append(task_detail)
                actual_tasks.append(task_detail)

            role_info = {
                "role_id": role_id,
                "static_role_name": static_role_name,
                "dynamic_role_name": dynamic_role_name,
                "role_name": dynamic_role_name,
                "tasks": task_details,
                "focus_areas": role.get("focus_areas", []),
                "expected_output": role.get("expected_output", ""),
                "dependencies": role.get("dependencies", []),
                "task_count": len(task_details),
            }
            detailed_task_list.append(role_info)

        return detailed_task_list, actual_tasks

    def _extract_role_base_type(self, role_id: str) -> str:
        """
        从角色ID提取基础类型

        Args:
            role_id: 角色ID (如 "2-1" 或 "V2_设计总监_2-1")

        Returns:
            基础角色类型 (如 "V2")
        """
        if isinstance(role_id, str):
            # 处理完整格式 "V2_设计总监_2-1"
            if role_id.startswith("V"):
                return role_id.split("_")[0]
            # 处理简化格式 "2-1"
            elif "-" in role_id:
                level = role_id.split("-")[0]
                return f"V{level}"
        return "V2"  # 默认返回V2

    def _generate_tool_settings(self, selected_roles: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        为每个角色生成工具配置建议

        Args:
            selected_roles: 选中的角色列表

        Returns:
            {
                "2-1": {
                    "enable_search": False,  # 设计师通常不需要搜索
                    "available_tools": ["tavily", "arxiv", "bocha"],
                    "recommended": []
                },
                "4-1": {
                    "enable_search": True,  # 研究员需要搜索
                    "available_tools": ["tavily", "arxiv", "bocha"],
                    "recommended": ["tavily", "arxiv"]
                }
            }
        """
        tool_settings = {}

        # 默认规则：V4（研究员）、V6（工程师）需要搜索，其他角色可选
        search_required_roles = ["V4", "V6"]

        for role in selected_roles:
            role_id = role.get("role_id", "")
            role_base_type = self._extract_role_base_type(role_id)

            enable_by_default = role_base_type in search_required_roles

            tool_settings[role_id] = {
                "enable_search": enable_by_default,
                "available_tools": ["tavily", "arxiv", "bocha"],
                "recommended": ["tavily", "arxiv"] if enable_by_default else [],
            }

        logger.info(f"🔧 Generated tool settings for {len(tool_settings)} roles")
        return tool_settings

    def _generate_concept_image_settings(self, selected_roles: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        为每个角色的交付物生成概念图配置建议

        Args:
            selected_roles: 选中的角色列表

        Returns:
            {
                "2-1": {
                    "deliverables": [
                        {
                            "name": "整体设计方案",
                            "enable_concept_image": True,
                            "recommended_aspect_ratio": "16:9"
                        }
                    ]
                }
            }
        """
        concept_settings = {}

        # 简化：基于角色类型判断是否需要概念图
        visual_roles = ["V2", "V3", "V5"]  # 设计师、叙事专家、场景专家需要视觉化

        for role in selected_roles:
            role_id = role.get("role_id", "")
            role_base_type = self._extract_role_base_type(role_id)

            # 从task_instruction提取交付物
            deliverables_info = []
            task_instruction = role.get("task_instruction", {})
            if isinstance(task_instruction, dict):
                deliverables = task_instruction.get("deliverables", [])
                for d in deliverables:
                    deliverable_name = d.get("name", "")
                    enable_by_default = role_base_type in visual_roles

                    deliverables_info.append(
                        {
                            "name": deliverable_name,
                            "enable_concept_image": enable_by_default,
                            "recommended_aspect_ratio": "16:9",
                        }
                    )

            if deliverables_info:
                concept_settings[role_id] = {"deliverables": deliverables_info}

        logger.info(f"🎨 Generated concept image settings for {len(concept_settings)} roles")
        return concept_settings

    def _validate_task_assignment(
        self, selected_roles: List[Dict[str, Any]], actual_tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """验证任务分配的合理性"""
        issues = []
        warnings = []

        # 检查任务数量
        if len(actual_tasks) == 0:
            issues.append("没有分配任何任务")
        elif len(actual_tasks) < len(selected_roles):
            warnings.append(f"任务数量({len(actual_tasks)})少于角色数量({len(selected_roles)})")

        # 检查每个角色是否有任务
        for role in selected_roles:
            if not role.get("tasks"):
                issues.append(f"角色 {role.get('role_name', 'unknown')} 没有分配任务")

        return {"is_valid": len(issues) == 0, "issues": issues, "warnings": warnings, "total_tasks": len(actual_tasks)}

    def _handle_user_decision(
        self, state: Dict[str, Any], user_decision: Dict[str, Any], interaction_data: Dict[str, Any]
    ) -> Command[Literal["batch_executor", "project_director"]]:
        """处理用户的审核决策"""
        action = user_decision.get("action", "")

        # 🔥 修复: 兼容 'approve' 和 'confirm' 两种确认值
        if action in ["approve", "confirm"]:
            logger.info("✅ User approved role selection and task assignment")

            # 🆕 提取工具设置和概念图设置
            tool_settings = user_decision.get("tool_settings", {})
            concept_image_settings = user_decision.get("concept_image_settings", {})

            # 检查是否有任务修改
            modifications = user_decision.get("modifications", {})
            if modifications:
                logger.info(f"📝 User provided task modifications for {len(modifications)} roles")

                # 🆕 能力边界检查：检查任务修改是否引入超范围需求
                logger.info("🔍 [CapabilityBoundary] 检查任务修改的能力边界")

                # 提取原始任务
                original_tasks = {}
                selected_roles = interaction_data["role_selection"]["selected_roles"]
                for role in selected_roles:
                    role_id = role.get("role_id", "")
                    original_tasks[role_id] = role.get("tasks", [])

                # 检查修改
                boundary_check = CapabilityBoundaryService.check_task_modifications(
                    original_tasks=original_tasks,
                    modified_tasks=modifications,
                    context={"node": "role_task_unified_review", "session_id": state.get("session_id", "")},
                )

                logger.info(f"📊 任务修改能力边界检查结果:")
                logger.info(f"   在能力范围内: {boundary_check.within_capability}")
                if boundary_check.has_new_deliverables:
                    logger.info(f"   新增交付物: {len(boundary_check.new_deliverables)} 项")
                    if not boundary_check.within_capability:
                        logger.warning(f"⚠️ 任务修改包含超范围需求")
                        for warning in boundary_check.capability_warnings:
                            logger.warning(f"     - {warning}")

                # 应用任务修改到 selected_roles
                for role in selected_roles:
                    role_id = role.get("role_id", "")
                    if role_id in modifications:
                        modified_tasks = modifications[role_id]
                        logger.info(f"  - 更新 {role_id} 的 {len(modified_tasks)} 个任务")
                        role["tasks"] = modified_tasks

                    # 🆕 应用工具设置
                    if role_id in tool_settings:
                        role["enable_search"] = tool_settings[role_id].get("enable_search", True)
                        logger.info(f"  - 应用 {role_id} 的搜索工具设置: {role.get('enable_search')}")

                    # 🆕 应用概念图设置
                    if role_id in concept_image_settings:
                        role["concept_image_config"] = concept_image_settings[role_id]
                        logger.info(f"  - 应用 {role_id} 的概念图设置")

                # 更新 strategic_analysis 中的任务
                state_updates = {
                    "role_selection_approved": True,
                    "task_assignment_approved": True,
                    "analysis_stage": AnalysisStage.BATCH_EXECUTION.value,
                    "strategic_analysis": {
                        **state.get("strategic_analysis", {}),
                        "selected_roles": selected_roles,
                        "user_modifications_applied": True,
                        "user_tool_settings_applied": True,  # 🆕 标记
                        "user_concept_settings_applied": True,  # 🆕 标记
                    },
                    "unified_review_result": {
                        "approved": True,
                        "timestamp": datetime.now().isoformat(),
                        "roles_count": len(selected_roles),
                        "tasks_count": interaction_data["task_assignment"]["summary"]["total_tasks"],
                        "has_user_modifications": True,
                    },
                    # 🆕 保存能力边界检查记录
                    "task_modification_boundary_check": boundary_check,
                }
            else:
                # 无修改，直接应用设置
                selected_roles = interaction_data["role_selection"]["selected_roles"]

                for role in selected_roles:
                    role_id = role.get("role_id", "")

                    # 🆕 应用工具设置
                    if role_id in tool_settings:
                        role["enable_search"] = tool_settings[role_id].get("enable_search", True)
                        logger.info(f"  - 应用 {role_id} 的搜索工具设置: {role.get('enable_search')}")

                    # 🆕 应用概念图设置
                    if role_id in concept_image_settings:
                        role["concept_image_config"] = concept_image_settings[role_id]
                        logger.info(f"  - 应用 {role_id} 的概念图设置")

                state_updates = {
                    "role_selection_approved": True,
                    "task_assignment_approved": True,
                    "analysis_stage": AnalysisStage.BATCH_EXECUTION.value,
                    "strategic_analysis": {
                        **state.get("strategic_analysis", {}),
                        "selected_roles": selected_roles,
                        "user_tool_settings_applied": True,  # 🆕 标记
                        "user_concept_settings_applied": True,  # 🆕 标记
                    },
                    "unified_review_result": {
                        "approved": True,
                        "timestamp": datetime.now().isoformat(),
                        "roles_count": len(selected_roles),
                        "tasks_count": interaction_data["task_assignment"]["summary"]["total_tasks"],
                    },
                }

            return Command(update=state_updates, goto="quality_preflight")  # 🔥 修复：进入预检，而不是直接跳到batch_executor

        elif action == "modify_roles":
            logger.info("🔄 User requested role modification")
            modifications = user_decision.get("modifications", {})

            state_updates = {
                "role_selection_approved": False,
                "role_modification_request": modifications,
                "retry_reason": "用户请求修改角色选择",
            }

            return Command(update=state_updates, goto="project_director")

        elif action == "modify_tasks":
            logger.info("🔄 User requested task modification")
            modifications = user_decision.get("modifications", {})

            state_updates = {
                "task_assignment_approved": False,
                "task_modification_request": modifications,
                "retry_reason": "用户请求修改任务分配",
            }

            return Command(update=state_updates, goto="project_director")

        elif action == "change_strategy":
            logger.info("🔄 User requested strategy change")
            new_strategy = user_decision.get("new_strategy", "")

            state_updates = {
                "role_selection_approved": False,
                "requested_strategy": new_strategy,
                "retry_reason": f"用户请求更换策略为 {new_strategy}",
            }

            return Command(update=state_updates, goto="project_director")

        elif action == "reject":
            logger.warning("❌ User rejected role selection and task assignment")
            rejection_reason = user_decision.get("reason", "未提供原因")

            state_updates = {
                "role_selection_approved": False,
                "task_assignment_approved": False,
                "rejection_reason": rejection_reason,
                "retry_reason": f"用户拒绝：{rejection_reason}",
            }

            return Command(update=state_updates, goto="project_director")

        else:
            logger.error(f"❌ Unknown user action: {action}")
            # 默认返回项目总监重新规划
            return Command(update={"retry_reason": f"未知操作: {action}"}, goto="project_director")


# ===== 工厂函数 =====
def role_task_unified_review_node(state: Dict[str, Any]) -> Command[Literal["batch_executor", "project_director"]]:
    """
    角色任务统一审核节点工厂函数

    用于在工作流中调用
    """
    node = RoleTaskUnifiedReviewNode()
    return node.execute(state)
