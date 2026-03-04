"""
任务分派审核交互节点
Task Assignment Review Interaction Node

在任务分派后,允许用户审核和调整任务分配
"""

from typing import Any, Dict, List, Literal, Union

from langgraph.types import Command, interrupt
from loguru import logger

from intelligent_project_analyzer.core.strategy_manager import StrategyManager

from .utils import SendFactory


class TaskAssignmentReviewNode:
    """任务分派审核节点"""
    
    def __init__(self):
        """初始化审核节点"""
        self.strategy_manager = StrategyManager()
        logger.info("Task assignment review node initialized")
    
    def execute(self, state: Dict[str, Any]) -> Command[Literal["first_batch_agent", "project_director"]]:
        """
        执行任务分派审核

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        logger.info("Starting task assignment review interaction")

        #  检查是否是重新执行模式，如果是则跳过审核
        if state.get("skip_task_review"):
            logger.info(" 重新执行模式，跳过任务分配审核，直接进入批次执行")
            return Command(
                update={"task_assignment_approved": True},
                goto="batch_executor"  #  更新：使用新的批次执行器
            )

        # 获取项目总监的结果
        # 项目总监返回的数据在 strategic_analysis 键中
        strategic_analysis = state.get("strategic_analysis") or {}  #  修复：确保不为 None

        #  详细调试日志
        logger.info(f" [DEBUG] strategic_analysis 类型: {type(strategic_analysis)}")
        logger.info(f" [DEBUG] strategic_analysis 内容: {strategic_analysis}")
        logger.info(f" [DEBUG] strategic_analysis 长度: {len(strategic_analysis) if strategic_analysis else 0}")

        if not strategic_analysis:
            logger.error(" No strategic_analysis found in state")
            logger.debug(f"Available state keys: {list(state.keys())}")
            return state

        # 提取任务分配信息
        selected_roles = strategic_analysis.get("selected_roles", [])
        task_distribution = strategic_analysis.get("task_distribution", {})
        
        logger.info(f"Reviewing task assignment for {len(selected_roles)} roles")
        
        # 生成详细的任务清单（包括模板任务）
        detailed_task_list, actual_tasks = self._generate_detailed_task_list(
            selected_roles,
            task_distribution
        )

        # 验证任务分配（使用实际任务）
        validation_result = self._validate_task_assignment(
            selected_roles,
            actual_tasks
        )

        # 获取任务分配原则
        assignment_principles = self.strategy_manager.get_assignment_principles()

        # 计算实际的任务统计
        total_tasks = sum(len(tasks) for tasks in actual_tasks.values())
        
        #  修复：从 selected_roles 中提取角色ID并构造完整ID
        role_ids_with_tasks = []
        for role in selected_roles:
            if isinstance(role, dict):
                role_id = role.get('role_id', '')
            elif hasattr(role, 'role_id'):
                role_id = role.role_id
            else:
                role_id = role
            
            full_role_id = self._construct_full_role_id(role_id)
            if actual_tasks.get(full_role_id):
                role_ids_with_tasks.append(full_role_id)
        
        roles_with_tasks = len(role_ids_with_tasks)

        # 准备交互数据
        interaction_data = {
            "interaction_type": "task_assignment_review",
            "message": "项目总监已完成任务分派,请审核各角色的任务清单:",
            "task_list": detailed_task_list,
            "validation": validation_result,
            "assignment_principles": assignment_principles,
            "summary": {
                "total_roles": len(selected_roles),
                "total_tasks": total_tasks,
                "roles_with_tasks": roles_with_tasks
            },
            "options": {
                "approve": "确认任务分派,开始执行",
                "modify": "修改任务分配",
                "add_tasks": "为某个角色添加任务",
                "remove_tasks": "移除某些任务",
                "reject": "拒绝并重新分派"
            }
        }

        logger.debug(f"Prepared task assignment review with {len(detailed_task_list)} role assignments")
        logger.debug(f"Validation result: {validation_result}")
        logger.info(f"Task summary: {total_tasks} tasks across {roles_with_tasks} roles")
        
        # 调用 interrupt 暂停工作流,等待用户输入
        logger.info("Calling interrupt() to wait for user review of task assignment")
        user_response = interrupt(interaction_data)
        
        # 处理用户响应
        logger.info(f"Received user response: {type(user_response)}")
        logger.debug(f"User response content: {user_response}")
        
        #  使用意图解析器（支持自然语言）
        from ..utils.intent_parser import parse_user_intent
        
        intent_result = parse_user_intent(
            user_response,
            context="任务分派审核",
            stage="task_assignment_review"
        )
        
        logger.info(f" 用户意图解析: {intent_result['intent']} (方法: {intent_result['method']})")
        
        #  根据意图直接返回Command进行路由
        intent = intent_result["intent"]

        if intent == "approve":
            logger.info(" User approved task assignment, proceeding to execution")

            #  2025-11-18: 集成 BatchScheduler 计算批次
            from intelligent_project_analyzer.workflow.batch_scheduler import BatchScheduler

            # 1. 计算批次（基于依赖关系的拓扑排序）
            scheduler = BatchScheduler()
            active_agents = state.get("active_agents", [])
            batches = scheduler.schedule_batches(active_agents)

            logger.info(f" BatchScheduler 计算得到 {len(batches)} 个批次:")
            for i, batch in enumerate(batches, start=1):
                logger.info(f"  批次 {i}: {batch}")

            # 2. 创建第一批的 Send 对象
            # 使用新方法：SendFactory.create_batch_sends()
            #  修复 (2025-11-18): 直接传递 batches 参数，避免时序问题
            #  修复 (2025-11-19): 使用正确的节点名 agent_executor
            send_list = SendFactory.create_batch_sends(
                state=state,
                batch_number=1,
                node_name="agent_executor",  # 修复：使用 agent_executor 替代 first_batch_agent
                batches=batches  # 直接传递已计算的批次
            )

            return Command(
                update={
                    "task_assignment_approved": True,
                    "task_assignment_modified": False,
                    "proceed_to_execution": True,
                    #  保存批次信息到状态
                    "execution_batches": batches,
                    "current_batch": 1,
                    "total_batches": len(batches)
                },
                goto=send_list  # 使用 Send 列表进行并行执行
            )
        elif intent in ["reject", "revise"]:
            logger.warning(f"️ User {intent} task assignment, returning to project director")
            return Command(
                update={
                    "task_assignment_approved": False,
                    "reassign_required": True,
                    "rejection_reason": intent_result.get("content", f"User {intent}")
                },
                goto="project_director"
            )
        elif intent == "modify":
            logger.info(" User requested modifications, returning to project director")
            return Command(
                update={
                    "task_assignment_approved": False,
                    "task_assignment_modified": True,
                    "modification_request": intent_result.get("content", "")
                },
                goto="project_director"
            )
        else:
            # 默认approve
            logger.info(f"User {intent}, defaulting to approve")

            #  2025-11-18: 集成 BatchScheduler 计算批次（同上）
            from intelligent_project_analyzer.workflow.batch_scheduler import BatchScheduler

            scheduler = BatchScheduler()
            active_agents = state.get("active_agents", [])
            batches = scheduler.schedule_batches(active_agents)

            logger.info(f" BatchScheduler 计算得到 {len(batches)} 个批次")
            for i, batch in enumerate(batches, start=1):
                logger.info(f"  批次 {i}: {batch}")

            #  修复 (2025-11-18): 直接传递 batches 参数
            #  修复 (2025-11-19): 使用正确的节点名 agent_executor
            send_list = SendFactory.create_batch_sends(
                state=state,
                batch_number=1,
                node_name="agent_executor",  # 修复：使用 agent_executor 替代 first_batch_agent
                batches=batches  # 直接传递已计算的批次
            )

            return Command(
                update={
                    "task_assignment_approved": True,
                    "proceed_to_execution": True,
                    "execution_batches": batches,
                    "current_batch": 1,
                    "total_batches": len(batches)
                },
                goto=send_list
            )

    def _generate_detailed_task_list(
        self,
        selected_roles: List[Union[str, Any]],  #  支持字符串或 RoleObject
        task_distribution: Dict[str, Any]
    ) -> tuple[List[Dict[str, Any]], Dict[str, List[str]]]:
        """
        生成详细的任务清单（支持动态角色名称）

        Args:
            selected_roles: 选择的角色列表 (可以是 List[str] 或 List[RoleObject])
            task_distribution: 任务分配信息

        Returns:
            (详细的任务清单, 实际使用的任务字典)
        """
        detailed_list = []
        actual_tasks = {}  # 记录实际使用的任务（包括模板任务）

        for role in selected_roles:
            #  兼容两种格式：
            # 1. 新格式：selected_roles 是 List[RoleObject]
            # 2. 旧格式：selected_roles 是 List[str]
            
            if isinstance(role, dict) or hasattr(role, 'role_id'):
                # 新格式：RoleObject - 直接使用动态名称
                if isinstance(role, dict):
                    role_id = role.get('role_id', '')
                    dynamic_role_name = role.get('dynamic_role_name', '')
                    tasks = role.get('tasks', [])
                    focus_areas = role.get('focus_areas', [])
                    expected_output = role.get('expected_output', '')
                    dependencies = role.get('dependencies', [])
                else:
                    # Pydantic BaseModel
                    role_id = role.role_id
                    dynamic_role_name = role.dynamic_role_name
                    tasks = role.tasks
                    focus_areas = role.focus_areas
                    expected_output = role.expected_output
                    dependencies = role.dependencies
                
                # 构造完整角色ID
                full_role_id = self._construct_full_role_id(role_id)
                actual_tasks[full_role_id] = tasks
                
                logger.info(f" {full_role_id} (动态名称: {dynamic_role_name}) 包含 {len(tasks)} 个任务")
                
                detailed_list.append({
                    "role_id": full_role_id,
                    "static_role_name": full_role_id,  #  主角色名称（静态，用于配置查找）
                    "dynamic_role_name": dynamic_role_name,  #  动态角色名称（显示用）
                    "role_name": dynamic_role_name,  # ️ 保留兼容旧代码
                    "tasks": [
                        {
                            "task_id": f"{full_role_id}_task_{i+1}",
                            "description": task,
                            "priority": "high" if i < 2 else "medium",
                            "estimated_effort": "待评估"
                        }
                        for i, task in enumerate(tasks)
                    ],
                    "focus_areas": focus_areas,
                    "expected_output": expected_output,
                    "dependencies": dependencies,
                    "task_count": len(tasks)
                })
                continue  # 处理完新格式，跳到下一个角色
            
            # 旧格式：字符串 role_id
            role_tasks = task_distribution.get(role, {})

            #  调试日志：输出每个角色的 task_data
            logger.info(f" [DEBUG] 处理角色: {role}")
            logger.info(f" [DEBUG] role_tasks 类型: {type(role_tasks)}")
            if hasattr(role_tasks, '__dict__'):
                logger.info(f" [DEBUG] role_tasks 属性: {role_tasks.__dict__}")
            elif isinstance(role_tasks, dict):
                logger.info(f" [DEBUG] role_tasks keys: {list(role_tasks.keys())}")
            elif isinstance(role_tasks, str):
                logger.info(f" [DEBUG] role_tasks 字符串长度: {len(role_tasks)}")

            # 提取任务列表 - 兼容 TaskDetail 对象、字典和字符串格式
            tasks = []
            focus_areas = []
            expected_output = ""
            dependencies = []

            # 情况1: TaskDetail 对象（新格式）
            if hasattr(role_tasks, 'tasks'):
                tasks = role_tasks.tasks
                focus_areas = role_tasks.focus_areas
                expected_output = role_tasks.expected_output
                dependencies = role_tasks.dependencies
                logger.info(f" {role} 使用 TaskDetail 格式，包含 {len(tasks)} 个定制任务")

            # 情况2: 字典格式（兼容）
            elif isinstance(role_tasks, dict):
                tasks = role_tasks.get("tasks", [])
                focus_areas = role_tasks.get("focus_areas", [])
                expected_output = role_tasks.get("expected_output", "")
                dependencies = role_tasks.get("dependencies", [])
                if tasks:
                    logger.info(f" {role} 使用字典格式，包含 {len(tasks)} 个定制任务")

            # 情况3: 字符串格式（旧格式兼容）
            elif isinstance(role_tasks, str):
                tasks = [role_tasks]
                logger.info(f" {role} 使用字符串格式，已转换为任务列表")

            # 如果没有任务,使用模板生成默认任务
            if not tasks:
                tasks = self.strategy_manager.get_task_template(role)
                logger.info(f"️ {role} 没有定制任务，使用 {len(tasks)} 个模板任务")

            # 记录实际使用的任务
            actual_tasks[role] = tasks

            # 获取显示名称
            display_name = self._get_role_display_name(role)
            
            detailed_list.append({
                "role_id": role,
                "static_role_name": role,  #  主角色名称（静态）
                "dynamic_role_name": display_name,  #  动态显示名称
                "role_name": display_name,  # ️ 保留兼容旧代码
                "tasks": [
                    {
                        "task_id": f"{role}_task_{i+1}",
                        "description": task,
                        "priority": "high" if i < 2 else "medium",  # 前两个任务优先级高
                        "estimated_effort": "待评估"
                    }
                    for i, task in enumerate(tasks)
                ],
                "focus_areas": focus_areas,
                "expected_output": expected_output,
                "dependencies": dependencies,
                "task_count": len(tasks)
            })

        return detailed_list, actual_tasks
    
    def _get_role_display_name(self, role_id: str) -> str:
        """获取角色的显示名称"""
        #  修正后的名称映射 - 与角色配置文件保持一致
        name_mapping = {
            "V2_设计总监": "设计总监",
            "V3_人物及叙事专家": "人物及叙事专家",  #  修复: 原来错误地映射为"技术架构师"
            "V4_设计研究员": "设计研究员",  #  修复: 原来错误地映射为"用户体验设计师"
            "V5_场景与用户生态专家": "场景与用户生态专家",  #  修复: 原来错误地映射为"商业分析师"
            "V6_专业总工程师": "专业总工程师"  #  修复: 原来键名为"V6_专业员工群"
        }

        for prefix, display_name in name_mapping.items():
            if role_id.startswith(prefix):
                return display_name

        return role_id
    
    def _construct_full_role_id(self, role_id: str) -> str:
        """构造完整角色ID"""
        # 如果已经是完整格式 (如 "V2_设计总监_2-1")，直接返回
        if role_id.count("_") >= 2:
            return role_id
        
        # 如果只是短ID (如 "2-1")，构造完整ID
        if role_id.startswith("2-"):
            return f"V2_设计总监_{role_id}"
        elif role_id.startswith("3-"):
            return f"V3_人物及叙事专家_{role_id}"
        elif role_id.startswith("4-"):
            return f"V4_设计研究员_{role_id}"
        elif role_id.startswith("5-"):
            return f"V5_场景与用户生态专家_{role_id}"
        elif role_id.startswith("6-"):
            return f"V6_专业总工程师_{role_id}"
        else:
            return role_id
    
    def _validate_task_assignment(
        self,
        selected_roles: List[str],
        actual_tasks: Dict[str, List[str]]
    ) -> Dict[str, Any]:
        """
        验证任务分配（使用实际任务，包括模板任务）

        Args:
            selected_roles: 选择的角色列表
            actual_tasks: 实际使用的任务字典（包括模板任务）

        Returns:
            验证结果
        """
        issues = []
        warnings = []

        # 检查每个角色是否都有任务
        for role in selected_roles:
            #  从 RoleObject 中提取 role_id
            if isinstance(role, dict):
                role_id = role.get('role_id', '')
            elif hasattr(role, 'role_id'):
                role_id = role.role_id
            else:
                role_id = role  # 兼容旧格式
            
            # 构造完整角色ID
            full_role_id = self._construct_full_role_id(role_id)
            tasks = actual_tasks.get(full_role_id, [])

            if not tasks:
                issues.append(f"角色 {full_role_id} 没有分配任务")
            elif len(tasks) < 2:
                warnings.append(f"角色 {full_role_id} 只有 {len(tasks)} 个任务,建议至少分配2个任务")

        # 检查任务描述是否具体
        for role, tasks in actual_tasks.items():
            for i, task in enumerate(tasks):
                if len(task) < 10:
                    warnings.append(f"角色 {role} 的任务 {i+1} 描述过于简单: '{task}'")

        # 计算总任务数
        total_tasks = sum(len(tasks) for tasks in actual_tasks.values())

        return {
            "is_valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "total_tasks": total_tasks
        }
    
    def _process_user_response(
        self,
        state: Dict[str, Any],
        user_response: Any,
        original_roles: List[str],
        original_tasks: Dict[str, Any],
        intent_result: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:
        """
        处理用户响应
        
        Args:
            state: 当前状态
            user_response: 用户响应
            original_roles: 原始角色列表
            original_tasks: 原始任务分配
        
        Returns:
            更新后的状态
        """
        #  优先使用意图解析结果（支持自然语言对话）
        if intent_result:
            intent = intent_result["intent"]
            content = intent_result.get("content", "")
            
            if intent == "approve":
                logger.info(" User approved task assignment, proceeding to execution")
                return {
                    "task_assignment_approved": True,
                    "task_assignment_modified": False
                }
            elif intent in ["reject", "revise"]:
                logger.warning(f"️ User {intent} task assignment, need to reassign")
                return {
                    "task_assignment_approved": False,
                    "task_assignment_modified": False,
                    "reassign_required": True,
                    "rejection_reason": content or f"User {intent}"
                }
            elif intent == "modify":
                logger.info(f" User requested task modifications: {content[:50]}")
                return {
                    "task_assignment_approved": False,
                    "task_assignment_modified": True,
                    "modification_request": content
                }
            else:
                logger.info(f"User {intent}, defaulting to approve")
                return {
                    "task_assignment_approved": True,
                    "task_assignment_modified": False
                }
        
        # 兼容原有逻辑：如果用户响应是字符串
        if isinstance(user_response, str):
            action = user_response.lower()
            
            if action == "approve":
                logger.info("User approved task assignment, proceeding to execution")
                return {
                    "task_assignment_approved": True,
                    "task_assignment_modified": False
                }
            
            elif action in ["reject", "revise"]:
                logger.warning(f"User {action} task assignment, need to reassign")
                return {
                    "task_assignment_approved": False,
                    "task_assignment_modified": False,
                    "reassign_required": True
                }
        
        # 如果用户响应是字典
        elif isinstance(user_response, dict):
            action = user_response.get("action", "approve")
            
            if action == "approve":
                logger.info("User approved task assignment")
                return {
                    "task_assignment_approved": True,
                    "task_assignment_modified": False
                }
            
            elif action == "modify":
                # 用户修改了任务分配
                modified_tasks = user_response.get("modified_tasks", original_tasks)
                
                logger.info("User modified task assignment")
                logger.debug(f"Modified tasks: {modified_tasks}")
                
                # 更新状态中的任务分配
                project_director_result = state.get("project_director", {})
                project_director_result["task_distribution"] = modified_tasks
                project_director_result["tasks_modified_by_user"] = True
                
                return {
                    "project_director": project_director_result,
                    "task_assignment_approved": True,
                    "task_assignment_modified": True
                }
            
            elif action == "add_tasks":
                # 用户为某个角色添加任务
                role_id = user_response.get("role_id")
                new_tasks = user_response.get("new_tasks", [])
                
                if role_id and new_tasks:
                    logger.info(f"User added {len(new_tasks)} tasks to {role_id}")
                    
                    # 更新任务分配
                    updated_tasks = original_tasks.copy()
                    if role_id in updated_tasks:
                        existing_tasks = updated_tasks[role_id].get("tasks", [])
                        updated_tasks[role_id]["tasks"] = existing_tasks + new_tasks
                    
                    project_director_result = state.get("project_director", {})
                    project_director_result["task_distribution"] = updated_tasks
                    project_director_result["tasks_modified_by_user"] = True
                    
                    return {
                        "project_director": project_director_result,
                        "task_assignment_approved": True,
                        "task_assignment_modified": True
                    }
            
            elif action == "remove_tasks":
                # 用户移除某些任务
                role_id = user_response.get("role_id")
                task_indices = user_response.get("task_indices", [])
                
                if role_id and task_indices:
                    logger.info(f"User removed {len(task_indices)} tasks from {role_id}")
                    
                    # 更新任务分配
                    updated_tasks = original_tasks.copy()
                    if role_id in updated_tasks:
                        existing_tasks = updated_tasks[role_id].get("tasks", [])
                        # 移除指定索引的任务
                        updated_tasks[role_id]["tasks"] = [
                            task for i, task in enumerate(existing_tasks) 
                            if i not in task_indices
                        ]
                    
                    project_director_result = state.get("project_director", {})
                    project_director_result["task_distribution"] = updated_tasks
                    project_director_result["tasks_modified_by_user"] = True
                    
                    return {
                        "project_director": project_director_result,
                        "task_assignment_approved": True,
                        "task_assignment_modified": True
                    }
            
            elif action == "reject":
                logger.warning("User rejected task assignment")
                return {
                    "task_assignment_approved": False,
                    "task_assignment_modified": False,
                    "reassign_required": True
                }
        
        # 默认情况: 批准原始分配
        logger.info("No clear user action, defaulting to approve")
        return {
            "task_assignment_approved": True,
            "task_assignment_modified": False
        }


def task_assignment_review_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    任务分派审核节点函数
    
    这是一个独立的节点函数,用于集成到LangGraph工作流中
    
    Args:
        state: 当前状态
    
    Returns:
        更新后的状态
    """
    node = TaskAssignmentReviewNode()
    return node.execute(state)

