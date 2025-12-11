"""
角色选择与任务分派统一审核节点
Role Selection and Task Assignment Unified Review Node

合并角色选择审核和任务分派审核，减少人机交互次数
"""

from typing import Dict, Any, List, Optional, Literal
from datetime import datetime
from loguru import logger
from langgraph.types import interrupt, Command

from intelligent_project_analyzer.core.strategy_manager import StrategyManager
from intelligent_project_analyzer.core.state import AnalysisStage


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
        role_validation = self.strategy_manager.validate_role_selection(
            selected_roles, 
            strategy_name
        )
        
        # 获取互补性推荐
        complementary_recommendations = self.strategy_manager.get_complementary_recommendations(
            selected_roles,
            strategy_name
        )
        
        # 生成角色选择决策说明
        role_decision_explanation = self.strategy_manager.generate_decision_explanation(
            strategy_name=strategy_name,
            selected_roles=selected_roles,
            reasoning=selection_reasoning,
            alternatives=None,
            confidence=strategic_analysis.get("confidence", None)
        )

        # ===== 第二部分：任务分派审核 =====
        task_distribution = strategic_analysis.get("task_distribution", {})
        
        # 生成详细任务清单
        detailed_task_list, actual_tasks = self._generate_detailed_task_list(
            selected_roles,
            task_distribution
        )

        # 验证任务分配
        task_validation = self._validate_task_assignment(
            selected_roles,
            actual_tasks
        )

        # 获取任务分配原则
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
            }
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
                    tasks = [f"【{d.get('name', '')}】{d.get('description', '')}" for d in task_instruction.get("deliverables", [])]
                    focus_areas = [d.get("name", "") for d in task_instruction.get("deliverables", [])]
                    
                    # 🔥 P1修复: 格式化预期输出，包含验收标准
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
                    role_tasks = [f"【{d.get('name', '')}】{d.get('description', '')}" for d in task_instruction.get("deliverables", [])]
                    
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

        # 检查任务数量
        if len(actual_tasks) == 0:
            issues.append("没有分配任何任务")
        elif len(actual_tasks) < len(selected_roles):
            warnings.append(f"任务数量({len(actual_tasks)})少于角色数量({len(selected_roles)})")

        # 检查每个角色是否有任务
        for role in selected_roles:
            if not role.get("tasks"):
                issues.append(f"角色 {role.get('role_name', 'unknown')} 没有分配任务")

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "total_tasks": len(actual_tasks)
        }

    def _handle_user_decision(
        self,
        state: Dict[str, Any],
        user_decision: Dict[str, Any],
        interaction_data: Dict[str, Any]
    ) -> Command[Literal["batch_executor", "project_director"]]:
        """处理用户的审核决策"""
        action = user_decision.get("action", "")

        # 🔥 修复: 兼容 'approve' 和 'confirm' 两种确认值
        if action in ["approve", "confirm"]:
            logger.info("✅ User approved role selection and task assignment")
            
            # 检查是否有任务修改
            modifications = user_decision.get("modifications", {})
            if modifications:
                logger.info(f"📝 User provided task modifications for {len(modifications)} roles")
                # 应用任务修改到 selected_roles
                selected_roles = interaction_data["role_selection"]["selected_roles"]
                for role in selected_roles:
                    role_id = role.get("role_id", "")
                    if role_id in modifications:
                        modified_tasks = modifications[role_id]
                        logger.info(f"  - 更新 {role_id} 的 {len(modified_tasks)} 个任务")
                        role["tasks"] = modified_tasks
                
                # 更新 strategic_analysis 中的任务
                state_updates = {
                    "role_selection_approved": True,
                    "task_assignment_approved": True,
                    "analysis_stage": AnalysisStage.BATCH_EXECUTION.value,
                    "strategic_analysis": {
                        **state.get("strategic_analysis", {}),
                        "selected_roles": selected_roles,
                        "user_modifications_applied": True
                    },
                    "unified_review_result": {
                        "approved": True,
                        "timestamp": datetime.now().isoformat(),
                        "roles_count": len(selected_roles),
                        "tasks_count": interaction_data["task_assignment"]["summary"]["total_tasks"],
                        "has_user_modifications": True
                    }
                }
            else:
                # 无修改，直接通过
                state_updates = {
                    "role_selection_approved": True,
                    "task_assignment_approved": True,
                    "analysis_stage": AnalysisStage.BATCH_EXECUTION.value,
                    "unified_review_result": {
                        "approved": True,
                        "timestamp": datetime.now().isoformat(),
                        "roles_count": len(interaction_data["role_selection"]["selected_roles"]),
                        "tasks_count": interaction_data["task_assignment"]["summary"]["total_tasks"]
                    }
                }

            return Command(
                update=state_updates,
                goto="quality_preflight"  # 🔥 修复：进入预检，而不是直接跳到batch_executor
            )

        elif action == "modify_roles":
            logger.info("🔄 User requested role modification")
            modifications = user_decision.get("modifications", {})
            
            state_updates = {
                "role_selection_approved": False,
                "role_modification_request": modifications,
                "retry_reason": "用户请求修改角色选择"
            }
            
            return Command(
                update=state_updates,
                goto="project_director"
            )

        elif action == "modify_tasks":
            logger.info("🔄 User requested task modification")
            modifications = user_decision.get("modifications", {})
            
            state_updates = {
                "task_assignment_approved": False,
                "task_modification_request": modifications,
                "retry_reason": "用户请求修改任务分配"
            }
            
            return Command(
                update=state_updates,
                goto="project_director"
            )

        elif action == "change_strategy":
            logger.info("🔄 User requested strategy change")
            new_strategy = user_decision.get("new_strategy", "")
            
            state_updates = {
                "role_selection_approved": False,
                "requested_strategy": new_strategy,
                "retry_reason": f"用户请求更换策略为 {new_strategy}"
            }
            
            return Command(
                update=state_updates,
                goto="project_director"
            )

        elif action == "reject":
            logger.warning("❌ User rejected role selection and task assignment")
            rejection_reason = user_decision.get("reason", "未提供原因")
            
            state_updates = {
                "role_selection_approved": False,
                "task_assignment_approved": False,
                "rejection_reason": rejection_reason,
                "retry_reason": f"用户拒绝：{rejection_reason}"
            }
            
            return Command(
                update=state_updates,
                goto="project_director"
            )

        else:
            logger.error(f"❌ Unknown user action: {action}")
            # 默认返回项目总监重新规划
            return Command(
                update={"retry_reason": f"未知操作: {action}"},
                goto="project_director"
            )


# ===== 工厂函数 =====
def role_task_unified_review_node(state: Dict[str, Any]) -> Command[Literal["batch_executor", "project_director"]]:
    """
    角色任务统一审核节点工厂函数
    
    用于在工作流中调用
    """
    node = RoleTaskUnifiedReviewNode()
    return node.execute(state)

