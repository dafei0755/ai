"""
批次策略审核交互节点（重构版 - 支持动态批次）
Batch Strategy Review Interaction Node (Refactored - Dynamic Batch Support)

在每批专家执行前,允许用户审核和调整其工作策略

🎯 重构亮点:
- 使用 StrategyGenerator 服务消除 V2/V6 重复逻辑 (~240 行)
- 路由到 batch_executor 节点，由它创建 Send 对象 (2025-11-19)
- 支持动态批次调度（1-N批）- 2025-11-18
- 代码行数从 928 行减少到 ~150 行 (-84%)

🔧 修复记录 (2025-11-19):
- 修复 InvalidUpdateError: 不再返回 Command(goto=List[Send])
- 改为返回 Command(goto="batch_executor")，由 batch_executor 根据 current_batch 创建 Send 对象
- **修复批次2跳过问题**: 移除重复的 `next_batch = current_batch + 1` 操作
  - batch_router 已将 current_batch 更新为即将执行的批次
  - batch_strategy_review 直接使用 current_batch，不再 +1
  - 不再更新 current_batch 到 next_batch，避免跳过批次
"""

from typing import Dict, Any, Literal, Optional
from loguru import logger
from langgraph.types import interrupt, Command

from intelligent_project_analyzer.core.role_manager import RoleManager
from .services import StrategyGenerator


class SecondBatchStrategyReviewNode:
    """批次策略审核节点 - 重构版（支持动态批次调度）

    重构日期: 2025-11-18
    新特性:
    - 支持动态批次数量（1-N批）
    - 基于 execution_batches 自动判断下一批次
    - 为任意角色生成策略预览（不再硬编码 V2/V6）
    """

    def __init__(self, role_manager: Optional[RoleManager] = None, llm_model=None):
        """
        初始化审核节点

        Args:
            role_manager: 角色管理器实例（可选）
            llm_model: LLM模型实例（用于动态生成搜索查询）
        """
        self.role_manager = role_manager or RoleManager()
        self.llm_model = llm_model

        # 🆕 初始化 StrategyGenerator 服务
        self.strategy_generator = StrategyGenerator(
            role_manager=self.role_manager,
            llm_model=self.llm_model
        )

        logger.info("Batch strategy review node initialized (dynamic batch support)")

    def execute(self, state: Dict[str, Any], skip_review: bool = True) -> Command[Literal["analysis_review", "intermediate_aggregator"]]:
        """
        执行批次策略审核（动态批次支持）

        重构说明 (2025-11-18):
        - 不再硬编码 V2/V6，支持任意批次
        - 基于 execution_batches 自动判断下一批次
        - 如果没有下一批次，直接进入 analysis_review

        🚀 方案C优化 (2025-11-25): 全自动批次执行
        - skip_review=True（默认）: 自动批准，不触发 interrupt
        - skip_review=False: 正常审核流程，触发 interrupt（保留以便未来启用）

        Args:
            state: 当前状态
            skip_review: 是否跳过审核直接批准（默认True，全自动执行）

        Returns:
            Command 对象，包含更新和路由信息
        """
        logger.info(f"Starting batch strategy review interaction (dynamic mode, skip_review={skip_review})")

        # ========================================
        # 1. 检查批次信息，判断是否还有下一批次
        # ========================================
        batches = state.get("execution_batches", [])
        current_batch = state.get("current_batch", 1)
        total_batches = state.get("total_batches", len(batches))
        completed_batches = state.get("completed_batches", [])

        logger.info(f"📊 批次状态: 当前批次={current_batch}/{total_batches}, 已完成={completed_batches}")

        # 🔧 修复 (2025-11-19): batch_router已经将current_batch更新为即将执行的批次
        # 这里直接使用current_batch，不再+1
        logger.info(f"🎯 准备审核即将执行的批次: 批次 {current_batch}/{total_batches}")

        # 检查批次是否已超出范围
        if current_batch > total_batches:
            logger.info("✅ 所有批次已完成，直接进入多视角审核")
            return Command(
                update={"all_batches_completed": True},
                goto="analysis_review"  # 直接进入审核
            )

        # 获取当前批次的角色列表
        if not batches or current_batch > len(batches):
            logger.error(f"批次信息异常: batches={batches}, current_batch={current_batch}")
            return Command(
                update={"error": "批次信息不完整"},
                goto="intermediate_aggregator"
            )

        current_batch_roles = batches[current_batch - 1]
        logger.info(f"📋 批次 {current_batch} 角色列表: {current_batch_roles}")

        # ========================================
        # 2. 动态生成当前批次的策略预览
        # ========================================
        agent_results = state.get("agent_results", {})
        structured_requirements = state.get("structured_requirements", {})
        project_task = structured_requirements.get("project_task", "")
        character_narrative = structured_requirements.get("character_narrative", "")

        # 为当前批次的每个角色生成策略预览
        batch_strategies = {}
        for role_id in current_batch_roles:
            # 提取角色前缀 (V2, V3, V4, V5, V6)
            role_prefix = role_id.split("_")[0] if "_" in role_id else role_id

            logger.info(f"🔍 生成 {role_id} 的策略预览...")
            strategy = self.strategy_generator.generate_strategy_preview(
                expert_type=role_prefix,
                agent_results=agent_results,
                project_task=project_task,
                character_narrative=character_narrative,
                state=state
            )
            batch_strategies[role_id] = strategy

        # ========================================
        # 3. 准备交互数据
        # ========================================
        dependency_summary = state.get("dependency_summary", {})
        # 计算上一批次编号（用于显示已完成的批次）
        previous_batch = current_batch - 1 if current_batch > 1 else 0
        interaction_data = {
            "interaction_type": "batch_strategy_review",
            "message": f"批次 {previous_batch} 已完成，请审核即将执行的批次 {current_batch} 的工作策略:" if previous_batch > 0 else f"请审核即将执行的批次 {current_batch} 的工作策略:",
            "previous_batch_summary": {
                "batch_number": previous_batch,
                "completed_agents": dependency_summary.get("completed_agents", []),
                "completed_count": dependency_summary.get("completed_count", 0),
                "total_count": dependency_summary.get("total_count", 0)
            } if previous_batch > 0 else None,
            "current_batch_info": {
                "batch_number": current_batch,
                "total_batches": total_batches,
                "roles": current_batch_roles,
                "role_count": len(current_batch_roles)
            },
            "batch_strategies": batch_strategies,
            "options": {
                "approve": f"确认策略，开始执行批次 {current_batch}",
                "modify": "修改策略",
                "reject": "拒绝策略，重新规划"
            }
        }

        logger.info(f"准备批次 {current_batch} 策略审核数据")
        logger.debug(f"策略预览: {list(batch_strategies.keys())}")

        # ========================================
        # 4. 调用 interrupt 等待用户审核（或自动批准）
        # ========================================
        # 🚀 方案C优化：默认自动批准（skip_review=True）
        if skip_review:
            logger.info(f"⚡ 批次 {current_batch} 自动批准（方案C：全自动批次执行）")
            return Command(
                update={
                    "batch_strategy_approved": True,
                    "batch_strategies": batch_strategies,
                    "auto_approved": True,
                    "auto_approval_reason": "方案C：全自动批次策略执行"
                },
                goto="batch_executor"
            )
        
        logger.info("Calling interrupt() to wait for user review")
        user_response = interrupt(interaction_data)

        logger.info(f"Received user response: {type(user_response)}")
        logger.debug(f"User response content: {user_response}")

        # ========================================
        # 5. 解析用户意图并路由
        # ========================================
        from ..utils.intent_parser import parse_user_intent

        intent_result = parse_user_intent(
            user_response,
            context=f"批次 {current_batch} 策略审核",
            stage="batch_strategy_review"
        )

        logger.info(f"💬 用户意图解析: {intent_result['intent']} (方法: {intent_result['method']})")

        intent = intent_result["intent"]

        if intent == "approve":
            logger.info(f"✅ User approved batch {current_batch} strategies, proceeding to execution")

            # 🔧 修复 (2025-11-19): 不再更新 current_batch，batch_router 已经更新过了
            # batch_executor 会根据 current_batch 自动创建对应批次的 Send 对象
            return Command(
                update={
                    "batch_strategy_approved": True,
                    "batch_strategies": batch_strategies
                },
                goto="batch_executor"  # 路由到 batch_executor 节点
            )

        elif intent in ["reject", "revise"]:
            logger.warning(f"⚠️ User {intent} batch {current_batch} strategies")
            return Command(
                update={
                    "batch_strategy_approved": False,
                    "batch_strategy_rejected": True,
                    "rejection_reason": intent_result.get("content", f"User {intent}"),
                    "need_replan": True
                },
                goto="intermediate_aggregator"
            )

        elif intent == "modify":
            logger.info(f"📝 User requested strategy modifications for batch {current_batch}")
            return Command(
                update={
                    "batch_strategy_approved": False,
                    "batch_strategy_modified": True,
                    "modification_request": intent_result.get("content", "")
                },
                goto="intermediate_aggregator"
            )

        else:
            # 默认批准
            logger.info(f"User {intent}, defaulting to approve")

            # 🔧 修复 (2025-11-19): 不再更新 current_batch，batch_router 已经更新过了
            # batch_executor 会根据 current_batch 自动创建对应批次的 Send 对象
            return Command(
                update={
                    "batch_strategy_approved": True,
                    "batch_strategies": batch_strategies
                },
                goto="batch_executor"  # 路由到 batch_executor 节点
            )
