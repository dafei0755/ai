"""
角色选择审核交互节点
Role Selection Review Interaction Node

在项目总监选择角色后,允许用户审核和调整选择
"""

from typing import Dict, Any, List, Optional, Literal
from loguru import logger
from langgraph.types import interrupt, Command

from intelligent_project_analyzer.core.strategy_manager import StrategyManager


class RoleSelectionReviewNode:
    """角色选择审核节点"""
    
    def __init__(self):
        """初始化审核节点"""
        self.strategy_manager = StrategyManager()
        logger.info("Role selection review node initialized")
    
    def execute(self, state: Dict[str, Any]) -> Command[Literal["task_assignment_review", "project_director"]]:
        """
        执行角色选择审核

        Args:
            state: 当前状态

        Returns:
            更新后的状态
        """
        logger.info("Starting role selection review interaction")

        # ✅ 检查是否是重新执行模式，如果是则跳过审核
        if state.get("skip_role_review"):
            logger.info("🔄 重新执行模式，跳过角色选择审核，直接进入任务分配审核")
            return Command(
                update={"role_selection_approved": True},
                goto="task_assignment_review"
            )

        # 获取项目总监的角色选择结果
        # 项目总监返回的数据在 strategic_analysis 键中
        strategic_analysis = state.get("strategic_analysis") or {}  # 🔥 修复：确保不为 None

        if not strategic_analysis:
            logger.error("No strategic analysis found in state")
            logger.debug(f"Available state keys: {list(state.keys())}")
            return state

        # 提取角色选择信息
        selected_roles = strategic_analysis.get("selected_roles", [])
        selection_reasoning = strategic_analysis.get("strategy_overview", "")
        task_distribution = strategic_analysis.get("task_distribution", {})
        strategy_name = "default"  # 当前项目总监没有返回策略名称

        logger.info(f"Project director selected {len(selected_roles)} roles using '{strategy_name}' strategy")
        logger.debug(f"Selected roles: {selected_roles}")

        # 🆕 Phase 1.3增强：交付物约束验证（审核层）
        constraint_validation_result = self._validate_deliverable_constraints(state, selected_roles)
        if not constraint_validation_result["is_valid"]:
            logger.error(f"❌ 约束验证失败：{constraint_validation_result['error_message']}")
            # 自动拒绝并返回项目总监重新选择
            return Command(
                update={
                    "role_selection_approved": False,
                    "role_selection_rejected": True,
                    "rejection_reason": constraint_validation_result["error_message"]
                },
                goto="project_director"
            )

        # 验证角色选择
        validation_result = self.strategy_manager.validate_role_selection(
            selected_roles,
            strategy_name
        )

        # 获取互补性推荐
        complementary_recommendations = self.strategy_manager.get_complementary_recommendations(
            selected_roles,
            strategy_name
        )

        # 生成决策说明
        decision_explanation = self.strategy_manager.generate_decision_explanation(
            strategy_name=strategy_name,
            selected_roles=selected_roles,
            reasoning=selection_reasoning,
            alternatives=None,  # TODO: 可以从LLM获取备选方案
            confidence=strategic_analysis.get("confidence", None)
        )
        
        # 准备交互数据
        interaction_data = {
            "interaction_type": "role_selection_review",
            "message": "项目总监已完成角色选择,请审核并确认:",
            "decision_explanation": decision_explanation,
            "selected_roles": self._format_roles_for_display(selected_roles, task_distribution),
            "validation": validation_result,
            "recommendations": complementary_recommendations,
            "strategy_info": {
                "current_strategy": strategy_name,
                "available_strategies": self.strategy_manager.list_available_strategies()
            },
            "options": {
                "approve": "确认选择,继续执行",
                "modify": "修改角色选择",
                "change_strategy": "更换选择策略",
                "reject": "拒绝并重新选择"
            }
        }
        
        logger.debug(f"Prepared interaction data with {len(selected_roles)} roles")
        logger.debug(f"Validation result: {validation_result}")
        
        # 调用 interrupt 暂停工作流,等待用户输入
        logger.info("Calling interrupt() to wait for user review")
        user_response = interrupt(interaction_data)
        
        # 处理用户响应
        logger.info(f"Received user response: {type(user_response)}")
        logger.debug(f"User response content: {user_response}")
        
        # 🆕 使用意图解析器（支持自然语言）
        from ..utils.intent_parser import parse_user_intent
        
        intent_result = parse_user_intent(
            user_response,
            context="角色选择审核",
            stage="role_selection_review"
        )
        
        logger.info(f"💬 用户意图解析: {intent_result['intent']} (方法: {intent_result['method']})")
        
        # 🆕 根据意图直接返回Command进行路由
        intent = intent_result["intent"]
        
        if intent == "approve":
            logger.info("✅ User approved role selection, proceeding to task assignment")
            return Command(
                update={
                    "role_selection_approved": True,
                    "role_selection_modified": False
                },
                goto="task_assignment_review"
            )
        elif intent in ["reject", "revise"]:
            logger.warning(f"⚠️ User {intent} role selection, returning to project director")
            return Command(
                update={
                    "role_selection_approved": False,
                    "role_selection_rejected": True,
                    "rejection_reason": intent_result.get("content", f"User {intent}")
                },
                goto="project_director"
            )
        elif intent == "modify":
            logger.info(f"📝 User requested modifications, returning to project director")
            return Command(
                update={
                    "role_selection_approved": False,
                    "role_selection_modified": True,
                    "modification_request": intent_result.get("content", "")
                },
                goto="project_director"
            )
        else:
            # 默认approve
            logger.info(f"User {intent}, defaulting to approve")
            return Command(
                update={"role_selection_approved": True},
                goto="task_assignment_review"
            )
    
    def _format_roles_for_display(
        self, 
        selected_roles: List[str], 
        task_distribution: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        格式化角色信息用于显示
        
        Args:
            selected_roles: 选择的角色列表 (兼容 List[str] 和 List[RoleObject])
            task_distribution: 任务分配信息
        
        Returns:
            格式化的角色信息列表
        """
        formatted_roles = []

        for i, role in enumerate(selected_roles):
            # ✅ 兼容两种格式：
            # 1. 新格式：selected_roles 是 List[RoleObject]
            # 2. 旧格式：selected_roles 是 List[str]
            
            if isinstance(role, dict) or hasattr(role, 'role_id'):
                # 新格式：RoleObject
                if isinstance(role, dict):
                    role_id = role.get('role_id', '')
                    role_name = role.get('role_name', '')
                    dynamic_role_name = role.get('dynamic_role_name', '')
                    tasks = role.get('tasks', [])
                    focus_areas = role.get('focus_areas', [])
                    expected_output = role.get('expected_output', '')
                    dependencies = role.get('dependencies', [])
                else:
                    # Pydantic BaseModel
                    role_id = role.role_id
                    role_name = role.role_name
                    dynamic_role_name = role.dynamic_role_name
                    tasks = role.tasks
                    focus_areas = role.focus_areas
                    expected_output = role.expected_output
                    dependencies = role.dependencies
                
                # 构造完整角色ID用于编号
                full_role_id = self._construct_full_role_id(role_id, i)
                
                formatted_roles.append({
                    "role_id": full_role_id,
                    "role_name": dynamic_role_name,  # ✅ 使用动态名称
                    "tasks": tasks,
                    "focus_areas": focus_areas,
                    "expected_output": expected_output,
                    "dependencies": dependencies
                })
            else:
                # 旧格式：字符串 role_id
                role_id = role
                
                # 获取该角色的任务
                role_tasks = task_distribution.get(role_id, {})

                # 兼容多种数据格式：TaskDetail对象、字典、字符串
                if hasattr(role_tasks, 'tasks'):
                    # TaskDetail 对象（Pydantic BaseModel）
                    tasks = role_tasks.tasks
                    focus_areas = role_tasks.focus_areas
                    expected_output = role_tasks.expected_output
                    dependencies = getattr(role_tasks, 'dependencies', [])
                elif isinstance(role_tasks, dict):
                    # 字典格式
                    tasks = role_tasks.get("tasks", [])
                    focus_areas = role_tasks.get("focus_areas", [])
                    expected_output = role_tasks.get("expected_output", "")
                    dependencies = role_tasks.get("dependencies", [])
                elif isinstance(role_tasks, str):
                    # 字符串格式（旧版兼容）
                    tasks = [role_tasks]
                    focus_areas = []
                    expected_output = ""
                    dependencies = []
                else:
                    # 未知格式，记录警告并使用默认值
                    logger.warning(f"⚠️ 未知的 task_distribution 格式: {type(role_tasks)} for role {role_id}")
                    tasks = []
                    focus_areas = []
                    expected_output = ""
                    dependencies = []

                formatted_roles.append({
                    "role_id": role_id,
                    "role_name": self._get_role_display_name(role_id),  # 旧格式使用映射
                    "tasks": tasks,
                    "focus_areas": focus_areas,
                    "expected_output": expected_output,
                    "dependencies": dependencies
                })

        return formatted_roles
    
    def _construct_full_role_id(self, role_id: str, index: int) -> str:
        """构造完整角色ID用于显示编号"""
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
            # 未知格式，使用索引编号
            return f"Role_{index + 1}"

    def _validate_deliverable_constraints(
        self,
        state: Dict[str, Any],
        selected_roles: List[str]
    ) -> Dict[str, Any]:
        """
        🆕 Phase 1.3: 验证角色分配是否符合交付物约束

        本方法是审核层的第二道防线，用于拦截不符合约束的角色分配：
        1. 检查配置文件中的must_include/must_exclude规则
        2. 检查需求分析师的anti_pattern建议

        Args:
            state: 当前状态（包含需求分析结果和角色分配）
            selected_roles: 已选择的角色列表（格式：List[str] 或 List[RoleObject]）

        Returns:
            {"is_valid": bool, "error_message": str}
        """
        from intelligent_project_analyzer.utils.constraint_loader import validate_allocation

        logger.info("🔍 [约束验证] 开始验证角色分配约束...")

        # 1. 提取交付物列表
        requirements_analysis = state.get("requirements_analysis", {})
        if not requirements_analysis:
            # 兼容旧数据结构：可能直接在state根级别
            requirements_analysis = state

        primary_deliverables = requirements_analysis.get("primary_deliverables", [])

        if not primary_deliverables:
            logger.warning("[约束验证] ⚠️ 未找到primary_deliverables，跳过验证")
            return {"is_valid": True, "error_message": ""}

        logger.info(f"[约束验证] 找到 {len(primary_deliverables)} 个交付物")

        # 2. 提取角色ID列表（兼容多种格式）
        role_ids = []
        for role in selected_roles:
            if isinstance(role, dict):
                role_ids.append(role.get("role_id", ""))
            elif hasattr(role, "role_id"):
                role_ids.append(role.role_id)
            elif isinstance(role, str):
                role_ids.append(role)
            else:
                logger.warning(f"[约束验证] ⚠️ 未知角色格式: {type(role)}")

        logger.info(f"[约束验证] 提取到 {len(role_ids)} 个角色ID: {role_ids}")

        # 3. 执行约束验证
        try:
            is_valid, error_msg = validate_allocation(primary_deliverables, role_ids)

            if not is_valid:
                logger.error(f"[约束验证] ❌ 验证失败: {error_msg}")
            else:
                logger.info("[约束验证] ✅ 验证通过")

            return {
                "is_valid": is_valid,
                "error_message": error_msg
            }

        except Exception as e:
            logger.error(f"[约束验证] ⚠️ 验证过程出错: {str(e)}", exc_info=True)
            # 出错时默认通过，避免阻塞流程
            return {
                "is_valid": True,
                "error_message": f"验证过程出错（已放行）: {str(e)}"
            }

    def _get_role_display_name(self, role_id: str) -> str:
        """
        获取角色的显示名称

        Args:
            role_id: 角色ID (如 "V2_设计总监_2-1")

        Returns:
            显示名称
        """
        # ✅ 修正后的名称映射 - 与角色配置文件保持一致
        name_mapping = {
            "V2_设计总监": "设计总监",
            "V3_人物及叙事专家": "人物及叙事专家",  # ✅ 修复: 原来错误地映射为"技术架构师"
            "V4_设计研究员": "设计研究员",  # ✅ 修复: 原来错误地映射为"用户体验设计师"
            "V5_场景与用户生态专家": "场景与用户生态专家",  # ✅ 修复: 原来错误地映射为"商业分析师"
            "V6_专业总工程师": "专业总工程师"  # ✅ 修复: 原来键名为"V6_专业员工群"
        }

        # 提取角色类别前缀
        for prefix, display_name in name_mapping.items():
            if role_id.startswith(prefix):
                return display_name

        return role_id
    
    def _process_user_response(
        self,
        state: Dict[str, Any],
        user_response: Any,
        original_roles: List[str],
        original_tasks: Dict[str, Any],
        original_strategy: str,
        intent_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        处理用户响应
        
        Args:
            state: 当前状态
            user_response: 用户响应
            original_roles: 原始角色列表
            original_tasks: 原始任务分配
            original_strategy: 原始策略名称
        
        Returns:
            更新后的状态
        """
        # 🆕 优先使用意图解析结果（支持自然语言对话）
        if intent_result:
            intent = intent_result["intent"]
            content = intent_result.get("content", "")
            
            if intent == "approve":
                logger.info("✅ User approved role selection, proceeding")
                return {
                    "role_selection_approved": True,
                    "role_selection_modified": False
                }
            elif intent in ["reject", "revise"]:
                logger.warning(f"⚠️ User {intent} role selection, need to reselect")
                return {
                    "role_selection_approved": False,
                    "role_selection_modified": False,
                    "reselect_required": True,
                    "rejection_reason": content or f"User {intent}"
                }
            elif intent == "modify":
                logger.info(f"📝 User requested modifications: {content[:50]}")
                return {
                    "role_selection_approved": False,
                    "role_selection_modified": True,
                    "modification_request": content
                }
            else:
                # skip等，默认approve
                logger.info(f"User {intent}, defaulting to approve")
                return {
                    "role_selection_approved": True,
                    "role_selection_modified": False
                }
        
        # 兼容原有逻辑：如果用户响应是字符串
        if isinstance(user_response, str):
            action = user_response.lower()
            
            if action == "approve":
                logger.info("User approved role selection, proceeding with original selection")
                return {
                    "role_selection_approved": True,
                    "role_selection_modified": False
                }
            
            elif action in ["reject", "revise"]:
                logger.warning(f"User {action} role selection, need to reselect")
                return {
                    "role_selection_approved": False,
                    "role_selection_modified": False,
                    "reselect_required": True
                }
        
        # 如果用户响应是字典 (包含修改信息)
        elif isinstance(user_response, dict):
            action = user_response.get("action", "approve")
            
            if action == "approve":
                logger.info("User approved role selection")
                return {
                    "role_selection_approved": True,
                    "role_selection_modified": False
                }
            
            elif action == "modify":
                # 用户修改了角色选择
                modified_roles = user_response.get("modified_roles", original_roles)
                modified_tasks = user_response.get("modified_tasks", original_tasks)
                
                logger.info(f"User modified role selection: {len(modified_roles)} roles")
                logger.debug(f"Modified roles: {modified_roles}")
                
                # 更新状态中的角色选择
                project_director_result = state.get("project_director", {})
                project_director_result["selected_roles"] = modified_roles
                project_director_result["task_distribution"] = modified_tasks
                project_director_result["modified_by_user"] = True
                
                return {
                    "project_director": project_director_result,
                    "role_selection_approved": True,
                    "role_selection_modified": True
                }
            
            elif action == "change_strategy":
                # 用户更换了策略
                new_strategy = user_response.get("new_strategy", original_strategy)
                
                logger.info(f"User changed strategy from '{original_strategy}' to '{new_strategy}'")
                
                return {
                    "role_selection_approved": False,
                    "role_selection_modified": False,
                    "reselect_required": True,
                    "new_strategy": new_strategy
                }
            
            elif action == "reject":
                logger.warning("User rejected role selection")
                return {
                    "role_selection_approved": False,
                    "role_selection_modified": False,
                    "reselect_required": True
                }
        
        # 默认情况: 批准原始选择
        logger.info("No clear user action, defaulting to approve")
        return {
            "role_selection_approved": True,
            "role_selection_modified": False
        }


def role_selection_review_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    角色选择审核节点函数
    
    这是一个独立的节点函数,用于集成到LangGraph工作流中
    
    Args:
        state: 当前状态
    
    Returns:
        更新后的状态
    """
    node = RoleSelectionReviewNode()
    return node.execute(state)

