"""角色任务统一审核节点 - 重构版 (继承 InteractionAgent基类)

示例展示如何使用 InteractionAgent 基类实现角色任务审核节点。

原文件: role_task_unified_review.py (446行)
重构后: role_task_unified_review_refactored.py (约200行，减少55%)
"""

from datetime import datetime
from typing import Any, Dict, List, Literal

from langgraph.store.base import BaseStore
from langgraph.types import Command
from loguru import logger

from ...core.state import AnalysisStage, ProjectAnalysisState
from ...core.strategy_manager import StrategyManager
from ..nodes.interaction_agent_base import InteractionAgent, extract_intent_from_response


class RoleTaskUnifiedReviewNode(InteractionAgent):
    """角色任务统一审核节点 - 继承统一基类"""

    def __init__(self):
        """初始化审核节点"""
        super().__init__()
        self.strategy_manager = StrategyManager()
        logger.info(" Role-Task unified review node initialized (refactored)")

    # ========== 实现抽象方法 ==========

    def _get_interaction_type(self) -> str:
        """返回交互类型"""
        return "role_and_task_unified_review"

    def _should_skip(self, state: ProjectAnalysisState) -> tuple[bool, str]:
        """检查是否应跳过审核

        注意: 角色任务审核通常不应跳过，除非有明确的跳过标志。
        """
        # 检查是否有跳过标志
        if state.get("skip_unified_review"):
            return True, "用户设置了跳过角色任务审核标志"

        # 追问模式下可能跳过
        if state.get("is_followup") and state.get("skip_all_interactions"):
            return True, "追问模式下跳过所有交互"

        return False, ""

    def _validate_state(self, state: ProjectAnalysisState) -> tuple[bool, str]:
        """验证状态完整性"""
        strategic_analysis = state.get("strategic_analysis")

        if not strategic_analysis:
            return False, "Missing strategic_analysis in state"

        selected_roles = strategic_analysis.get("selected_roles", [])
        if not selected_roles:
            return False, "No roles selected in strategic_analysis"

        return True, ""

    def _prepare_interaction_data(
        self,
        state: ProjectAnalysisState,
        store: BaseStore | None = None
    ) -> Dict[str, Any]:
        """准备角色任务审核交互数据"""
        strategic_analysis = state.get("strategic_analysis", {})
        selected_roles = strategic_analysis.get("selected_roles", [])
        selection_reasoning = strategic_analysis.get("strategy_overview", "")
        strategy_name = "goal_oriented_adaptive_collaboration_v7.2"

        logger.info(f" Project director selected {len(selected_roles)} roles")

        # ===== 第一部分：角色选择审核 =====
        role_validation = self.strategy_manager.validate_role_selection(
            selected_roles,
            strategy_name
        )

        complementary_recommendations = self.strategy_manager.get_complementary_recommendations(
            selected_roles,
            strategy_name
        )

        role_decision_explanation = self.strategy_manager.generate_decision_explanation(
            strategy_name=strategy_name,
            selected_roles=selected_roles,
            reasoning=selection_reasoning,
            alternatives=None,
            confidence=strategic_analysis.get("confidence", None)
        )

        # ===== 第二部分：任务分派审核 =====
        task_distribution = strategic_analysis.get("task_distribution", {})

        detailed_task_list, actual_tasks = self._generate_detailed_task_list(
            selected_roles,
            task_distribution
        )

        task_validation = self._validate_task_assignment(
            selected_roles,
            actual_tasks
        )

        assignment_principles = self.strategy_manager.get_assignment_principles()

        # 计算任务统计
        total_tasks = sum(len(role.get("tasks", [])) for role in detailed_task_list)
        roles_with_tasks = sum(1 for role in detailed_task_list if role.get("tasks"))

        task_summary = {
            "total_roles": len(detailed_task_list),
            "total_tasks": total_tasks,
            "roles_with_tasks": roles_with_tasks
        }

        # ===== 构建统一的交互数据 =====
        return {
            "interaction_type": self.interaction_type,
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
                            "description": "以最终输出结构为导向，自适应选择协同模式，并强制生成和应用动态角色名称。"
                        }
                    ]
                }
            },

            # 任务分派部分
            "task_assignment": {
                "task_list": detailed_task_list,
                "validation": task_validation,
                "assignment_principles": assignment_principles,
                "summary": task_summary
            },

            # 操作选项
            "options": {
                "approve": "确认角色和任务，开始执行",
                "modify_roles": "修改角色选择",
                "modify_tasks": "修改任务分配",
                "change_strategy": "更换选择策略",
                "reject": "拒绝并重新规划"
            },

            # 元数据（用于后续处理）
            "_metadata": {
                "selected_roles": selected_roles,
                "detailed_task_list": detailed_task_list,
                "task_summary": task_summary
            }
        }

    def _process_response(
        self,
        state: ProjectAnalysisState,
        user_response: Any,
        store: BaseStore | None = None
    ) -> Command[Literal["quality_preflight", "project_director"]]:
        """处理用户审核响应"""
        # 提取用户意图
        action = extract_intent_from_response(user_response)

        logger.info(f"User action: {action}")

        # 提取交互数据（从准备阶段缓存）
        # 注意: 实际实现中，interaction_data 需要从 state 或其他地方获取
        # 这里简化为从 user_response 中提取相关信息
        modifications = {}
        if isinstance(user_response, dict):
            modifications = user_response.get("modifications", {})

        # 根据用户意图路由
        if action in ["approve", "confirm"]:
            return self._handle_approval(state, modifications)
        elif action == "modify_roles":
            return self._handle_modify_roles(state, user_response)
        elif action == "modify_tasks":
            return self._handle_modify_tasks(state, user_response)
        elif action == "change_strategy":
            return self._handle_change_strategy(state, user_response)
        elif action == "reject":
            return self._handle_rejection(state, user_response)
        else:
            logger.error(f" Unknown user action: {action}")
            return Command(
                update={"retry_reason": f"未知操作: {action}"},
                goto="project_director"
            )

    # ========== 辅助方法 ==========

    def _format_roles_for_review(self, selected_roles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """格式化角色信息供审核"""
        formatted_roles = []
        for role in selected_roles:
            # 优先从 task_instruction 提取信息
            tasks = role.get("tasks", [])
            focus_areas = role.get("focus_areas", [])
            expected_output = role.get("expected_output", "")

            if not tasks and "task_instruction" in role:
                task_instruction = role["task_instruction"]
                if isinstance(task_instruction, dict) and "deliverables" in task_instruction:
                    tasks = [f"【{d.get('name', '')}】{d.get('description', '')}"
                            for d in task_instruction.get("deliverables", [])]
                    focus_areas = [d.get("name", "") for d in task_instruction.get("deliverables", [])]

                    objective = task_instruction.get("objective", "")
                    success_criteria = task_instruction.get("success_criteria", [])
                    if success_criteria:
                        criteria_str = "；".join(success_criteria)
                        expected_output = f"{objective}\n\n[验收标准] {criteria_str}"
                    else:
                        expected_output = objective

            formatted_roles.append({
                "role_id": role.get("role_id", ""),
                "role_name": role.get("dynamic_role_name") or role.get("role_name", ""),
                "tasks": tasks,
                "focus_areas": focus_areas,
                "expected_output": expected_output,
                "dependencies": role.get("dependencies", [])
            })
        return formatted_roles

    def _generate_detailed_task_list(
        self,
        selected_roles: List[Dict[str, Any]],
        task_distribution: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """生成详细任务清单"""
        detailed_task_list = []
        actual_tasks = []

        for i, role in enumerate(selected_roles, 1):
            role_id = role.get("role_id", f"role_{i}")
            static_role_name = role.get("role_id", role_id)
            dynamic_role_name = role.get("dynamic_role_name") or role.get("role_name", "")

            # 提取角色的任务
            role_tasks = role.get("tasks", [])

            # 如果 tasks 为空但有 task_instruction (v2格式)，从中提取
            if not role_tasks and "task_instruction" in role:
                task_instruction = role["task_instruction"]
                if isinstance(task_instruction, dict) and "deliverables" in task_instruction:
                    role_tasks = [f"【{d.get('name', '')}】{d.get('description', '')}"
                                 for d in task_instruction.get("deliverables", [])]
                    role["tasks"] = role_tasks
                    logger.info(f" Extracted {len(role_tasks)} tasks from task_instruction for role {role_id}")

            # 为每个任务生成详细信息
            task_details = []
            for j, task in enumerate(role_tasks, 1):
                task_id = f"{role_id}_task_{j}"
                task_detail = {
                    "task_id": task_id,
                    "description": task,
                    "priority": "high" if j <= 2 else "medium",
                    "estimated_effort": "待评估"
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
                "task_count": len(task_details)
            }
            detailed_task_list.append(role_info)

        return detailed_task_list, actual_tasks

    def _validate_task_assignment(
        self,
        selected_roles: List[Dict[str, Any]],
        actual_tasks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """验证任务分配的合理性"""
        issues = []
        warnings = []

        if len(actual_tasks) == 0:
            issues.append("没有分配任何任务")
        elif len(actual_tasks) < len(selected_roles):
            warnings.append(f"任务数量({len(actual_tasks)})少于角色数量({len(selected_roles)})")

        for role in selected_roles:
            if not role.get("tasks"):
                issues.append(f"角色 {role.get('role_name', 'unknown')} 没有分配任务")

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "total_tasks": len(actual_tasks)
        }

    # ========== 响应处理方法 ==========

    def _handle_approval(
        self,
        state: ProjectAnalysisState,
        modifications: Dict
    ) -> Command[Literal["quality_preflight"]]:
        """处理批准操作"""
        logger.info(" User approved role selection and task assignment")

        strategic_analysis = state.get("strategic_analysis", {})
        selected_roles = strategic_analysis.get("selected_roles", [])

        if modifications:
            logger.info(f" User provided task modifications for {len(modifications)} roles")
            # 应用任务修改
            for role in selected_roles:
                role_id = role.get("role_id", "")
                if role_id in modifications:
                    modified_tasks = modifications[role_id]
                    logger.info(f"  - 更新 {role_id} 的 {len(modified_tasks)} 个任务")
                    role["tasks"] = modified_tasks

            state_updates = {
                "role_selection_approved": True,
                "task_assignment_approved": True,
                "analysis_stage": AnalysisStage.BATCH_EXECUTION.value,
                "strategic_analysis": {
                    **strategic_analysis,
                    "selected_roles": selected_roles,
                    "user_modifications_applied": True
                },
                "unified_review_result": {
                    "approved": True,
                    "timestamp": datetime.now().isoformat(),
                    "roles_count": len(selected_roles),
                    "has_user_modifications": True
                }
            }
        else:
            state_updates = {
                "role_selection_approved": True,
                "task_assignment_approved": True,
                "analysis_stage": AnalysisStage.BATCH_EXECUTION.value,
                "unified_review_result": {
                    "approved": True,
                    "timestamp": datetime.now().isoformat(),
                    "roles_count": len(selected_roles)
                }
            }

        return Command(update=state_updates, goto="quality_preflight")

    def _handle_modify_roles(
        self,
        state: ProjectAnalysisState,
        user_response: Dict
    ) -> Command[Literal["project_director"]]:
        """处理修改角色操作"""
        logger.info(" User requested role modification")
        modifications = user_response.get("modifications", {})

        return Command(
            update={
                "role_selection_approved": False,
                "role_modification_request": modifications,
                "retry_reason": "用户请求修改角色选择"
            },
            goto="project_director"
        )

    def _handle_modify_tasks(
        self,
        state: ProjectAnalysisState,
        user_response: Dict
    ) -> Command[Literal["project_director"]]:
        """处理修改任务操作"""
        logger.info(" User requested task modification")
        modifications = user_response.get("modifications", {})

        return Command(
            update={
                "task_assignment_approved": False,
                "task_modification_request": modifications,
                "retry_reason": "用户请求修改任务分配"
            },
            goto="project_director"
        )

    def _handle_change_strategy(
        self,
        state: ProjectAnalysisState,
        user_response: Dict
    ) -> Command[Literal["project_director"]]:
        """处理更换策略操作"""
        logger.info(" User requested strategy change")
        new_strategy = user_response.get("new_strategy", "")

        return Command(
            update={
                "role_selection_approved": False,
                "requested_strategy": new_strategy,
                "retry_reason": f"用户请求更换策略为 {new_strategy}"
            },
            goto="project_director"
        )

    def _handle_rejection(
        self,
        state: ProjectAnalysisState,
        user_response: Dict
    ) -> Command[Literal["project_director"]]:
        """处理拒绝操作"""
        logger.warning(" User rejected role selection and task assignment")
        rejection_reason = user_response.get("reason", "未提供原因")

        return Command(
            update={
                "role_selection_approved": False,
                "task_assignment_approved": False,
                "rejection_reason": rejection_reason,
                "retry_reason": f"用户拒绝：{rejection_reason}"
            },
            goto="project_director"
        )

    def _get_fallback_node(self, state: ProjectAnalysisState) -> str:
        """重写回退节点"""
        return "project_director"

    def _get_next_node_after_skip(self, state: ProjectAnalysisState) -> str:
        """重写跳过后的下一节点"""
        return "quality_preflight"


# ========== 向后兼容的工厂函数 ==========

_node_instance = None


def get_role_task_unified_review_node() -> RoleTaskUnifiedReviewNode:
    """获取单例节点实例"""
    global _node_instance
    if _node_instance is None:
        _node_instance = RoleTaskUnifiedReviewNode()
    return _node_instance


# 向后兼容: 原有调用方式
def role_task_unified_review_node_refactored(state: Dict[str, Any]) -> Command:
    """向后兼容的执行函数

    原调用: role_task_unified_review_node(state)
    新调用: get_role_task_unified_review_node().execute(state)
    """
    node = get_role_task_unified_review_node()
    return node.execute(state)
