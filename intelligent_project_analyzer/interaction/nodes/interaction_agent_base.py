"""InteractionAgent 统一基类

提供人机交互节点的统一架构和接口，减少代码重复，提升一致性。

设计原则:
1. 单一职责: 每个子类专注一个交互场景
2. 模板方法模式: 父类定义流程，子类实现细节
3. 统一异常处理: 基类统一处理 interrupt 和错误
4. 性能监控: 集成 PerformanceMonitor
5. 持久化标志管理: 统一管理 WorkflowFlagManager
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Literal, List
from datetime import datetime
from loguru import logger
from langgraph.types import interrupt, Command
from langgraph.store.base import BaseStore

from ...core.state import ProjectAnalysisState
from ...core.workflow_flags import WorkflowFlagManager


class InteractionAgent(ABC):
    """人机交互Agent基类

    所有人机交互节点继承此类，统一执行流程:
    1. 前置检查 (skip conditions, validation)
    2. 准备交互数据 (子类实现)
    3. 发送 interrupt 等待用户响应
    4. 解析用户响应
    5. 处理响应并路由到下一节点 (子类实现)
    """

    def __init__(self):
        """初始化交互Agent"""
        self.interaction_type = self._get_interaction_type()
        self.node_name = self.__class__.__name__

    # ========== 抽象方法 (子类必须实现) ==========

    @abstractmethod
    def _get_interaction_type(self) -> str:
        """返回交互类型标识

        Examples:
            - "calibration_questionnaire"
            - "requirements_confirmation"
            - "role_task_unified_review"

        Returns:
            str: 交互类型字符串
        """
        pass

    @abstractmethod
    def _prepare_interaction_data(
        self,
        state: ProjectAnalysisState,
        store: Optional[BaseStore] = None
    ) -> Dict[str, Any]:
        """准备交互数据 (子类实现)

        Args:
            state: 项目分析状态
            store: 存储接口

        Returns:
            Dict: 包含 interaction_type, message, 和其他交互特定字段

        Raises:
            ValueError: 如果状态数据不完整
        """
        pass

    @abstractmethod
    def _process_response(
        self,
        state: ProjectAnalysisState,
        user_response: Any,
        store: Optional[BaseStore] = None
    ) -> Command:
        """处理用户响应并路由到下一节点 (子类实现)

        Args:
            state: 项目分析状态
            user_response: 用户响应数据
            store: 存储接口

        Returns:
            Command: LangGraph Command 对象，指定下一节点
        """
        pass

    # ========== 可选重写的方法 ==========

    def _should_skip(self, state: ProjectAnalysisState) -> tuple[bool, str]:
        """检查是否应跳过此交互 (子类可选重写)

        Args:
            state: 项目分析状态

        Returns:
            tuple: (should_skip: bool, skip_reason: str)
        """
        return False, ""

    def _validate_state(self, state: ProjectAnalysisState) -> tuple[bool, str]:
        """验证状态是否满足执行条件 (子类可选重写)

        Args:
            state: 项目分析状态

        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        return True, ""

    def _get_fallback_node(self, state: ProjectAnalysisState) -> str:
        """获取回退节点 (子类可选重写)

        当状态验证失败时，返回此节点进行修复。

        Args:
            state: 项目分析状态

        Returns:
            str: 回退节点名称
        """
        return "requirements_analyst"  # 默认返回需求分析师

    def _update_interaction_history(
        self,
        state: ProjectAnalysisState,
        interaction_data: Dict[str, Any],
        user_response: Any
    ) -> List[Dict[str, Any]]:
        """更新交互历史 (子类可选重写)

        Args:
            state: 项目分析状态
            interaction_data: 发送的交互数据
            user_response: 用户响应

        Returns:
            List: 更新后的交互历史
        """
        history = state.get("interaction_history", [])
        history.append({
            "type": self.interaction_type,
            "interaction_data": interaction_data,
            "user_response": user_response,
            "timestamp": datetime.now().isoformat(),
            "node_name": self.node_name
        })
        return history

    # ========== 统一执行流程 (不建议重写) ==========

    def execute(
        self,
        state: ProjectAnalysisState,
        store: Optional[BaseStore] = None
    ) -> Command:
        """统一的执行流程 (模板方法)

        执行顺序:
        1. 日志记录开始
        2. 检查是否应跳过
        3. 验证状态
        4. 准备交互数据
        5. 发送 interrupt
        6. 接收用户响应
        7. 更新交互历史
        8. 处理响应并路由
        9. 保留持久化标志

        Args:
            state: 项目分析状态
            store: 存储接口

        Returns:
            Command: 指向下一节点的Command对象
        """
        # Step 1: 日志记录
        logger.info("=" * 80)
        logger.info(f"🤝 Starting {self.interaction_type} interaction")
        logger.info(f"   Node: {self.node_name}")
        logger.info("=" * 80)

        # Step 2: 检查是否应跳过
        should_skip, skip_reason = self._should_skip(state)
        if should_skip:
            logger.info(f"⏩ Skipping {self.interaction_type}: {skip_reason}")
            # 保留持久化标志
            update_dict = {f"{self.interaction_type}_skipped": True}
            update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)
            return self._process_skip(state, skip_reason, update_dict)

        # Step 3: 验证状态
        is_valid, error_message = self._validate_state(state)
        if not is_valid:
            logger.warning(f"⚠️ State validation failed: {error_message}")
            fallback_node = self._get_fallback_node(state)
            return Command(
                update={"error": error_message},
                goto=fallback_node
            )

        try:
            # Step 4: 准备交互数据
            logger.info(f"📋 Preparing interaction data for {self.interaction_type}")
            interaction_data = self._prepare_interaction_data(state, store)

            # 确保包含必需字段
            if "interaction_type" not in interaction_data:
                interaction_data["interaction_type"] = self.interaction_type
            if "timestamp" not in interaction_data:
                interaction_data["timestamp"] = datetime.now().isoformat()

            logger.info(f"✅ Interaction data prepared")
            logger.info(f"   Keys: {list(interaction_data.keys())}")

            # Step 5: 发送 interrupt
            logger.info(f"🛑 [INTERRUPT] Sending interrupt, waiting for user response...")
            user_response = interrupt(interaction_data)
            logger.info(f"✅ Received user response: {type(user_response)}")

            # Step 6: 更新交互历史
            updated_history = self._update_interaction_history(
                state,
                interaction_data,
                user_response
            )

            # Step 7: 处理响应
            logger.info(f"🔄 Processing user response...")
            command = self._process_response(state, user_response, store)

            # Step 8: 合并交互历史到 Command.update
            if isinstance(command.update, dict):
                command.update["interaction_history"] = updated_history
                # 保留持久化标志
                command.update = WorkflowFlagManager.preserve_flags(state, command.update)

            logger.info(f"✅ Response processed, routing to: {command.goto}")
            logger.info(f"   Update keys: {list(command.update.keys()) if command.update else []}")
            logger.info("=" * 80)

            return command

        except Exception as e:
            # 重新抛出 Interrupt 异常 (LangGraph控制流)
            if "Interrupt" in str(type(e)):
                logger.debug(f"Re-raising Interrupt exception (normal LangGraph flow)")
                raise

            # 记录其他异常
            logger.error(f"❌ {self.node_name} execution failed: {e}")
            import traceback
            traceback.print_exc()

            # 返回错误处理
            fallback_node = self._get_fallback_node(state)
            return Command(
                update={"error": f"{self.node_name} failed: {str(e)}"},
                goto=fallback_node
            )

    def _process_skip(
        self,
        state: ProjectAnalysisState,
        skip_reason: str,
        update_dict: Dict[str, Any]
    ) -> Command:
        """处理跳过逻辑 (子类可选重写)

        Args:
            state: 项目分析状态
            skip_reason: 跳过原因
            update_dict: 更新字典 (已包含持久化标志)

        Returns:
            Command: 指向下一节点的Command对象
        """
        # 默认实现: 跳过后继续到下一个标准节点
        # 子类可以重写此方法以自定义跳过后的行为
        next_node = self._get_next_node_after_skip(state)
        logger.info(f"⏩ Skipping to: {next_node}")
        return Command(update=update_dict, goto=next_node)

    def _get_next_node_after_skip(self, state: ProjectAnalysisState) -> str:
        """获取跳过后的下一个节点 (子类可选重写)

        Args:
            state: 项目分析状态

        Returns:
            str: 下一节点名称
        """
        # 默认实现: 根据交互类型决定
        if self.interaction_type == "calibration_questionnaire":
            return "requirements_confirmation"
        elif self.interaction_type == "requirements_confirmation":
            return "project_director"
        elif self.interaction_type == "role_task_unified_review":
            return "batch_executor"
        else:
            # 通用回退
            return "project_director"


# ========== 工具函数 ==========

def normalize_user_response(user_response: Any) -> Dict[str, Any]:
    """规范化用户响应为统一格式

    处理多种可能的响应格式:
    - str: 简单字符串响应
    - dict: 结构化响应 (最常见)
    - 其他类型: 转为字符串

    Args:
        user_response: 原始用户响应

    Returns:
        Dict: 规范化的响应字典，包含:
            - intent/action: 用户意图
            - value: 响应值
            - 其他原始字段
    """
    if isinstance(user_response, dict):
        return user_response
    elif isinstance(user_response, str):
        return {"intent": user_response.strip(), "value": user_response}
    else:
        return {"intent": "unknown", "value": str(user_response)}


def extract_intent_from_response(user_response: Any) -> str:
    """从用户响应中提取意图

    Args:
        user_response: 用户响应

    Returns:
        str: 用户意图 (approve/revise/modify/skip/etc.)
    """
    normalized = normalize_user_response(user_response)

    # 尝试多个字段名
    intent = (
        normalized.get("intent") or
        normalized.get("action") or
        normalized.get("type") or
        ""
    )

    return str(intent).strip().lower()
