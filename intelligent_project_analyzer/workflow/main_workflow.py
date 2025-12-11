"""
主工作流编排器

基于LangGraph实现的多智能体协作工作流
"""

import uuid
from typing import Dict, List, Optional, Any, Literal, Union
from datetime import datetime
from pathlib import Path
from loguru import logger
import yaml

from langgraph.graph import StateGraph, START, END
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Send, Command

from ..core.state import ProjectAnalysisState, AnalysisStage, StateManager
from ..core.types import AgentType, format_role_display_name
# 显式导入智能体类以触发 AgentFactory 注册
from ..agents import AgentFactory, RequirementsAnalystAgent, ProjectDirectorAgent
from ..agents.feasibility_analyst import FeasibilityAnalystAgent  # 🆕 V1.5可行性分析师
from ..agents.base import NullLLM
from ..interaction.interaction_nodes import (
    CalibrationQuestionnaireNode,
    RequirementsConfirmationNode,
    AnalysisReviewNode,
    # FinalReviewNode,  # 已移除：客户需求中没有最终审核阶段
    UserQuestionNode
)
# 🆕 统一审核节点（合并角色选择和任务分派审核）
from ..interaction.role_task_unified_review import role_task_unified_review_node
# from ..interaction.role_selection_review import role_selection_review_node  # 已废弃
# from ..interaction.task_assignment_review import task_assignment_review_node  # 已废弃
from ..interaction.second_batch_strategy_review import SecondBatchStrategyReviewNode
from ..interaction.nodes.quality_preflight import QualityPreflightNode  # 🆕
from ..agents.quality_monitor import QualityMonitor  # 🆕
from ..interaction.nodes.manual_review import ManualReviewNode  # 🆕 人工审核节点
from ..agents.dynamic_project_director import detect_and_handle_challenges_node  # 🆕 v3.5
from ..report.result_aggregator import ResultAggregatorAgent
from ..report.pdf_generator import PDFGeneratorAgent
from ..security import (  # 🆕 内容安全与领域过滤
    ReportGuardNode
)
# 🆕 v7.3 统一输入验证节点（合并 input_guard 和 domain_validator）
from ..security.unified_input_validator_node import (
    UnifiedInputValidatorNode,
    InputRejectedNode
)
# 动态本体论注入工具
from ..utils.ontology_loader import OntologyLoader


class MainWorkflow:
    """主工作流编排器"""
    
    def __init__(self, llm_model: Optional[Any] = None, config: Optional[Dict[str, Any]] = None):
        """
        初始化主工作流
        
        Args:
            llm_model: LLM模型实例
            config: 配置参数
        """
        if llm_model is None:
            llm_model = NullLLM("MainWorkflow")
        self.llm_model = llm_model
        self.config = config or {}
        if isinstance(self.llm_model, NullLLM):
            self.config.setdefault("llm_placeholder", True)
        # 启用完成后追问交互（可通过配置覆盖）
        self.config.setdefault("post_completion_followup_enabled", True)
        
        # 初始化存储和检查点
        self.store = InMemoryStore()
        self.checkpointer = MemorySaver()
        
        # 初始化本体论加载器
        self.ontology_loader = OntologyLoader(
            "d:/11-20/langgraph-design/intelligent_project_analyzer/knowledge_base/ontology.yaml"
        )

        # 构建工作流图
        self.graph = self._build_workflow_graph()
        
        logger.info("Main workflow initialized successfully")
    
    def _build_workflow_graph(self) -> StateGraph:
        """
        构建工作流图（2025-11-19重构：支持动态N批次执行）

        重要变更:
        - 移除硬编码的 first_batch_agent 和 second_batch_agent
        - 添加动态批次节点：batch_executor, agent_executor, batch_aggregator, batch_router
        - 实现循环执行：batch_executor → agent_executor → batch_aggregator → batch_router
        - 支持 1-N 个批次的动态执行
        """
        # 创建状态图
        workflow = StateGraph(ProjectAnalysisState)

        # ============================================================================
        # 0. 🆕 安全节点（第一道防线）
        # ============================================================================
        # 🆕 v7.3 统一输入验证节点（合并 input_guard 和 domain_validator）
        workflow.add_node("unified_input_validator_initial", self._unified_input_validator_initial_node)  # 初始验证
        workflow.add_node("unified_input_validator_secondary", self._unified_input_validator_secondary_node)  # 二次验证
        workflow.add_node("input_rejected", self._input_rejected_node)        # 拒绝终止
        workflow.add_node("report_guard", self._report_guard_node)            # 报告审核

        # ============================================================================
        # 1. 前置流程节点（需求收集与确认）
        # ============================================================================
        workflow.add_node("requirements_analyst", self._requirements_analyst_node)
        workflow.add_node("feasibility_analyst", self._feasibility_analyst_node)  # 🆕 V1.5可行性分析师
        workflow.add_node("calibration_questionnaire", self._calibration_questionnaire_node)
        workflow.add_node("requirements_confirmation", self._requirements_confirmation_node)

        # ============================================================================
        # 2. 角色选择与任务分派节点
        # ============================================================================
        workflow.add_node("project_director", self._project_director_node)
        # 🆕 统一审核节点（合并角色选择和任务分派）
        workflow.add_node("role_task_unified_review", self._role_task_unified_review_node)
        workflow.add_node("quality_preflight", self._quality_preflight_node)  # 🆕 质量预检

        # ============================================================================
        # 3. 🆕 动态批次执行节点（核心重构）
        # ============================================================================
        workflow.add_node("batch_executor", self._batch_executor_node)           # 批次执行器
        workflow.add_node("agent_executor", self._execute_agent_node)            # 智能体执行器
        workflow.add_node("batch_aggregator", self._intermediate_aggregator_node) # 批次聚合器
        workflow.add_node("batch_router", self._batch_router_node)               # 批次路由器
        workflow.add_node("batch_strategy_review", self._batch_strategy_review_node)  # 批次策略审核
        workflow.add_node("detect_challenges", self._detect_challenges_node)     # 🆕 v3.5 挑战检测

        # ============================================================================
        # 4. 审核与结果生成节点
        # ============================================================================
        workflow.add_node("analysis_review", self._analysis_review_node)
        workflow.add_node("manual_review", self._manual_review_node)  # 🆕 人工审核节点
        workflow.add_node("result_aggregator", self._result_aggregator_node)
        workflow.add_node("pdf_generator", self._pdf_generator_node)
        workflow.add_node("user_question", self._user_question_node)

        # ============================================================================
        # 边连接：前置流程
        # ============================================================================
        # 🆕 v7.3 统一输入验证流程
        workflow.add_edge(START, "unified_input_validator_initial")  # 第一道防线：初始验证
        # unified_input_validator_initial 使用 Command 路由到 requirements_analyst 或 input_rejected
        workflow.add_edge("input_rejected", END)  # 拒绝后终止

        workflow.add_edge("requirements_analyst", "feasibility_analyst")  # 🆕 V1.5可行性分析
        workflow.add_edge("feasibility_analyst", "unified_input_validator_secondary")  # 第二道防线：二次验证
        workflow.add_edge("unified_input_validator_secondary", "calibration_questionnaire")  # 验证后继续
        # ✅ calibration_questionnaire 使用 Command 完全动态路由（无静态 edge）
        # ✅ requirements_confirmation 使用 Command 动态路由到 requirements_analyst 或 project_director

        workflow.add_edge("project_director", "role_task_unified_review")  # 🆕 统一审核
        # ❌ 移除静态边，让 role_task_unified_review 使用 Command 动态路由
        # workflow.add_edge("role_task_unified_review", "quality_preflight")  # 🆕 质量预检
        workflow.add_edge("quality_preflight", "batch_executor")  # 🆕 预检后执行
        # role_task_unified_review 使用 Command 路由到 batch_executor 或 quality_preflight

        # ============================================================================
        # 🆕 动态批次执行流程（核心循环）
        # ============================================================================
        # 批次执行器 → 智能体执行器（并行）→ 批次聚合器 → 批次路由器
        workflow.add_edge("agent_executor", "batch_aggregator")
        # workflow.add_edge("batch_aggregator", "detect_challenges")  # ❌ 暂时禁用：导致状态冲突
        
        # 🆕 v3.5: 挑战检测移至 result_aggregator 之前
        # batch_aggregator → batch_router → analysis_review → detect_challenges → result_aggregator
        # workflow.add_conditional_edges(
        #     "detect_challenges",
        #     self._route_after_challenge_detection,
        #     {
        #         "revisit_requirements": "requirements_analyst",  # 反馈循环
        #         "continue_workflow": "batch_router"  # 继续正常流程
        #     }
        # )

        # 🆕 batch_aggregator → batch_router (条件边：检查审核状态)
        workflow.add_conditional_edges(
            "batch_aggregator",
            self._route_from_batch_aggregator,
            ["batch_router", END]  # 🔧 N1修复：移除detect_challenges，避免重复调用result_aggregator
        )
        
        # 批次路由器根据 current_batch 和 total_batches 决定：
        # - 如果还有下一批次 → batch_strategy_review（审核后继续）
        # - 如果所有批次完成 → analysis_review
        # 路由逻辑在 _batch_router_node 中通过 Command 实现

        # 批次策略审核 → 批次执行器（形成循环）
        workflow.add_edge("batch_strategy_review", "batch_executor")
        # batch_strategy_review 使用 Command 路由，可以跳过审核直接到 batch_executor

        # ✅ 批次执行器 → 智能体执行器（条件边 + Send API）
        # 使用条件边函数动态创建并行任务
        workflow.add_conditional_edges(
            "batch_executor",              # 源节点
            self._create_batch_sends,      # 条件边函数：返回 List[Send]
            ["agent_executor"]             # 可能的目标节点列表
        )

        # ============================================================================
        # 审核与结果生成流程
        # ============================================================================
        # analysis_review 使用 Command 动态路由到：
        # - detect_challenges（批准后先检测挑战）
        # - batch_executor（重执行特定批次）
        # - project_director（重新规划）
        
        # 🆕 v3.5: 挑战检测在审核通过后、结果聚合前执行
        workflow.add_conditional_edges(
            "detect_challenges",
            self._route_after_challenge_detection,
            {
                "revisit_requirements": "requirements_analyst",  # 反馈循环
                "manual_review": "manual_review",  # 🆕 人工审核（>3个must_fix）
                "continue_workflow": "result_aggregator"  # 继续到结果聚合
            }
        )
        
        # 🆕 人工审核节点：manual_review 使用 Command 动态路由到：
        # - batch_executor（重新执行特定专家）
        # - detect_challenges（继续挑战检测）
        # - END（终止流程）

        workflow.add_edge("result_aggregator", "report_guard")  # 🆕 报告审核
        workflow.add_edge("report_guard", "pdf_generator")      # 🆕 审核后生成PDF

        workflow.add_conditional_edges(
            "pdf_generator",
            self._route_after_pdf_generator,
            ["user_question", END]
        )

        workflow.add_conditional_edges(
            "user_question",
            self._route_after_user_question,
            ["project_director", "result_aggregator"]
        )

        # ============================================================================
        # 编译图
        # ============================================================================
        logger.info("🔧 Workflow graph built with dynamic batch execution support")
        logger.info("   Nodes: batch_executor, agent_executor, batch_aggregator, batch_router, batch_strategy_review")
        logger.info("   Supports: 1-N batches with dependency-based execution")

        return workflow.compile(
            checkpointer=self.checkpointer,
            store=self.store
        )
    
    # ============================================================================
    # 🆕 安全节点包装方法
    # ============================================================================
    
    # ============================================================================
    # 🆕 v7.3 统一输入验证节点包装方法
    # ============================================================================

    def _unified_input_validator_initial_node(self, state: ProjectAnalysisState) -> Command:
        """
        统一输入验证 - 阶段1: 初始验证

        执行内容安全检测、领域分类检测、任务复杂度评估
        """
        try:
            logger.info("Executing unified input validator - initial validation")
            result = UnifiedInputValidatorNode.execute_initial_validation(
                state,
                store=self.store,
                llm_model=self.llm_model
            )

            if not isinstance(result, Command):
                logger.error("UnifiedInputValidatorNode.execute_initial_validation did not return Command object")
                return Command(
                    update={"rejection_reason": "system_error"},
                    goto="input_rejected"
                )

            # 提取状态更新
            update_payload = dict(result.update or {})
            update_payload["detail"] = "检测输入内容安全性与领域适配性"

            # 读取复杂度评估结果
            suggested_workflow = update_payload.get("suggested_workflow", "full_analysis")
            task_complexity = update_payload.get("task_complexity", "complex")

            # 如果原本要去 input_rejected，保持不变
            if result.goto == "input_rejected":
                return Command(update=update_payload, goto="input_rejected")

            # 🔄 统一路由：所有任务都走完整流程
            # 🔧 v7.1 修复：不再自动跳过问卷，让用户决定
            # 原逻辑：medium 复杂度跳过问卷，但低置信度的默认 medium 恰恰需要问卷补充信息
            # 新逻辑：所有任务都显示问卷，用户可以选择跳过
            complexity_confidence = update_payload.get("complexity_confidence", 0.5)
            logger.info(f"📋 {task_complexity} 任务检测（置信度: {complexity_confidence:.2f}），使用完整流程")
            logger.info(f"   suggested_workflow: {suggested_workflow}")
            # skip_calibration 默认为 False，由校准问卷节点自身逻辑或用户选择决定

            return Command(update=update_payload, goto="requirements_analyst")

        except Interrupt:
            # 🔥 修复：Interrupt 是正常的交互中断，不应该捕获，应该向上传播
            logger.info("Input guard node raised an interrupt (user interaction required)")
            raise
        except Exception as e:
            logger.error(f"Error in input guard node: {e}")
            import traceback
            traceback.print_exc()
            # 出错时保守拒绝
            return Command(
                update={
                    "rejection_reason": "system_error",
                    "rejection_message": "系统错误，请稍后重试。",
                    "detail": "安全检测异常"
                },
                goto="input_rejected"
            )
    
    def _input_rejected_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """输入拒绝节点包装"""
        try:
            logger.info("Executing input rejected node")
            return InputRejectedNode.execute(state, store=self.store)
        except Exception as e:
            logger.error(f"Error in input rejected node: {e}")
            return {
                "final_status": "rejected",
                "rejection_message": "系统错误，流程终止。"
            }
    
    def _unified_input_validator_secondary_node(self, state: ProjectAnalysisState) -> Union[Dict[str, Any], Command]:
        """
        统一输入验证 - 阶段2: 二次验证

        在需求分析后，重新验证领域一致性，检测领域漂移
        """
        from langgraph.types import Interrupt
        try:
            logger.info("Executing unified input validator - secondary validation")
            result = UnifiedInputValidatorNode.execute_secondary_validation(
                state,
                store=self.store,
                llm_model=self.llm_model
            )

            # ✅ 正常情况：返回字典（由静态 edge 路由到 calibration_questionnaire）
            # ✅ 拒绝情况：返回 Command(goto="input_rejected")（终止工作流）
            # ✅ 调整情况：返回 Command(goto="requirements_analyst")（重新分析）
            if isinstance(result, Command):
                logger.warning("⚠️ Secondary validation returned Command (rejection or re-analysis)")
                return result

            # 🔥 保留 skip_unified_review 标志
            if state.get("skip_unified_review"):
                result["skip_unified_review"] = True
                logger.info("🔍 [DEBUG] secondary_validation 保留 skip_unified_review=True")

            # 添加 detail 字段
            result["detail"] = "二次验证领域适配性"

            logger.info("🔄 [DEBUG] Secondary validation completed, proceeding to calibration_questionnaire")
            return result

        except Interrupt:
            # 🔥 修复：Interrupt 是正常的交互中断，不应该捕获，应该向上传播
            logger.info("Secondary validation raised an interrupt (user interaction required)")
            raise
        except Exception as e:
            logger.error(f"Error in secondary validation node: {e}")
            import traceback
            traceback.print_exc()
            # 出错时信任初始判断
            logger.warning("Secondary validation failed, trusting initial judgment")
            return {
                "secondary_validation_skipped": True,
                "secondary_validation_reason": "error_occurred"
            }
    
    def _report_guard_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """报告审核节点包装"""
        try:
            logger.info("Executing report guard node")
            result = ReportGuardNode.execute(state, store=self.store, llm_model=self.llm_model)
            result["detail"] = "审核报告内容"
            return result
        except Exception as e:
            logger.error(f"Error in report guard node: {e}")
            # 出错时放行（避免误拦）
            logger.warning("Report guard failed, allowing report to pass")
            return {"report_safety_status": "error_passthrough", "detail": "报告审核异常"}

    def _requirements_analyst_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        需求分析师节点

        注意: 只返回需要更新的字段,不返回完整状态
        这样可以避免并发更新冲突
        """
        try:
            logger.info("Executing requirements analyst node")
            
            # 🔍 调试：检查进入时的标志状态
            logger.info(f"🔍 [DEBUG] requirements_analyst 进入时 calibration_processed: {state.get('calibration_processed')}")
            logger.info(f"🔍 [DEBUG] requirements_analyst 进入时 calibration_skipped: {state.get('calibration_skipped')}")
            logger.info(f"🔍 [DEBUG] requirements_analyst 进入时 state 所有键: {list(state.keys())}")
            
            # 🔍 深度调试：检查 state 是否包含这些键
            if "calibration_processed" in state:
                logger.info(f"🔍 [DEBUG] 'calibration_processed' 键存在，值={state['calibration_processed']}")
            else:
                logger.info("🔍 [DEBUG] 'calibration_processed' 键不存在")

            # 创建需求分析师智能体
            agent = AgentFactory.create_agent(
                AgentType.REQUIREMENTS_ANALYST,
                llm_model=self.llm_model,
                config=self.config
            )

            # 执行分析
            result = agent.execute(state, {}, self.store)

            # 🆕 提取项目类型（从 structured_data 中）
            project_type = result.structured_data.get("project_type") if result.structured_data else None

            # 🆕 v7.0: 从 primary_deliverables 中提取交付物元数据和责任者映射
            deliverable_owner_map = {}
            deliverable_metadata = {}

            if result.structured_data:
                primary_deliverables = result.structured_data.get("primary_deliverables", [])

                for deliverable in primary_deliverables:
                    if not isinstance(deliverable, dict):
                        continue

                    deliverable_id = deliverable.get("deliverable_id", "")
                    if not deliverable_id:
                        continue

                    # 提取 owner 信息
                    owner_suggestion = deliverable.get("deliverable_owner_suggestion", {})
                    primary_owner = owner_suggestion.get("primary_owner", "")
                    supporters = owner_suggestion.get("supporters", [])

                    # 🔧 修复问题1: 标记为预测值，后续由 project_director 校正
                    # 填充 deliverable_owner_map（此时是需求分析师的预测）
                    if primary_owner:
                        deliverable_owner_map[deliverable_id] = primary_owner

                    # 填充 deliverable_metadata（包含完整信息）
                    deliverable_metadata[deliverable_id] = {
                        "name": deliverable.get("description", deliverable_id),
                        "type": deliverable.get("type", "unknown"),
                        "priority": deliverable.get("priority", "MUST_HAVE"),
                        "owner": primary_owner,  # 预测值，待校正
                        "owner_predicted": True,  # 🆕 标记为预测值
                        "supporters": supporters,
                        "acceptance_criteria": deliverable.get("acceptance_criteria", []),
                        "format_requirements": deliverable.get("format_requirements", {}),
                        "source_requirement": deliverable.get("source_requirement", "")
                    }

                if deliverable_owner_map:
                    logger.info(f"🎯 [v7.0] 提取到 {len(deliverable_owner_map)} 个交付物责任者映射（预测值）: {deliverable_owner_map}")

            # 只返回需要更新的字段
            # ✅ 修复: 使用 agent_type.value 保持一致性
            # 🔧 修复: 保留重要的流程控制标志，避免循环
            update_dict = {
                "current_stage": AnalysisStage.REQUIREMENT_COLLECTION.value,
                "structured_requirements": result.structured_data,
                "project_type": project_type,  # 🆕 添加项目类型字段
                "deliverable_owner_map": deliverable_owner_map,  # 🆕 v7.0: 交付物责任者映射
                "deliverable_metadata": deliverable_metadata,  # 🆕 v7.0: 交付物完整元数据
                "agent_results": {
                    AgentType.REQUIREMENTS_ANALYST.value: result.to_dict()
                },
                "updated_at": datetime.now().isoformat()
            }
            
            # 🔧 关键修复: 从完整状态中提取并保留流程控制标志
            # 注意: Command.update 的字段在目标节点执行时不可见,
            # 所以这里需要从 agent_results 中获取原始 state 的标志值
            # 但实际上,我们应该让这些标志"穿透"整个分析过程
            full_state = dict(state)  # 获取完整状态副本
            
            # 🛡️ 增强修复：检查标志 OR 检查答案是否存在
            has_processed = (
                ("calibration_processed" in full_state and full_state["calibration_processed"]) or 
                ("calibration_answers" in full_state and full_state["calibration_answers"])
            )
            
            if has_processed:
                update_dict["calibration_processed"] = True
                logger.info("🔍 [DEBUG] 保留/恢复 calibration_processed=True 标志")
                
            if "calibration_skipped" in full_state and full_state["calibration_skipped"]:
                update_dict["calibration_skipped"] = True
                logger.info("🔍 [DEBUG] 保留 calibration_skipped=True 标志")
            # 🔥 关键修复：保留 modification_confirmation_round 轮次计数
            if "modification_confirmation_round" in full_state:
                update_dict["modification_confirmation_round"] = full_state["modification_confirmation_round"]
                logger.info(f"🔍 [DEBUG] 保留 modification_confirmation_round={full_state['modification_confirmation_round']} 标志")
            # 🔥 关键修复：保留 skip_unified_review 标志
            if "skip_unified_review" in full_state and full_state["skip_unified_review"]:
                update_dict["skip_unified_review"] = True
                logger.info("🔍 [DEBUG] 保留 skip_unified_review=True 标志")
            
            logger.info(f"🔍 [DEBUG] requirements_analyst 返回的字段: {list(update_dict.keys())}")
            return update_dict

        except Exception as e:
            logger.error(f"Requirements analyst node failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": str(e),
                "updated_at": datetime.now().isoformat()
            }

    def _feasibility_analyst_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        V1.5 可行性分析师节点（后台决策支持）

        职责:
        1. 基于V1的structured_requirements进行可行性分析
        2. 检测预算/时间/空间冲突
        3. 计算需求优先级
        4. 生成决策建议
        5. 将结果存储到state.feasibility_assessment（不展示在前端）
        6. 后续在project_director中用于指导专家任务分派
        """
        try:
            logger.info("Executing V1.5 feasibility analyst node")

            # 创建V1.5可行性分析师智能体
            feasibility_agent = FeasibilityAnalystAgent(
                llm_model=self.llm_model,
                config=self.config
            )

            # 验证输入：V1的structured_requirements必须存在
            if not state.get("structured_requirements"):
                logger.warning("⚠️ V1.5跳过：structured_requirements不存在")
                return {"updated_at": datetime.now().isoformat()}

            # 执行可行性分析
            result = feasibility_agent.execute(state, {}, self.store)

            # 存储分析结果到state（仅后台存储，不展示到前端）
            update_dict = {
                "feasibility_assessment": result.structured_data,  # 完整的可行性分析结果
                "updated_at": datetime.now().isoformat()
            }

            # 日志记录关键发现（用于调试和监控）
            if result.structured_data:
                feasibility = result.structured_data.get("feasibility_assessment", {})
                overall = feasibility.get("overall_feasibility", "unknown")
                conflicts = result.structured_data.get("conflict_detection", {})

                logger.info(f"✅ V1.5可行性分析完成: overall_feasibility={overall}")

                # 记录冲突检测结果
                budget_conflicts = conflicts.get("budget_conflicts", [])
                if budget_conflicts and budget_conflicts[0].get("detected"):
                    severity = budget_conflicts[0].get("severity", "unknown")
                    logger.info(f"⚠️ 预算冲突检测: severity={severity}")

                # 记录优先级矩阵
                priority_matrix = result.structured_data.get("priority_matrix", [])
                if priority_matrix:
                    top_req = priority_matrix[0]
                    logger.info(f"🎯 最高优先级需求: {top_req.get('requirement')} (score={top_req.get('priority_score')})")

            return update_dict

        except Exception as e:
            logger.error(f"V1.5 Feasibility analyst node failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": str(e),
                "updated_at": datetime.now().isoformat()
            }

    def _calibration_questionnaire_node(self, state: ProjectAnalysisState) -> Command:
        """
        战略校准问卷节点

        根据需求分析师文档v1.0的要求：
        在完成需求分析后，必须生成"战略校准问卷"并等待用户回答。

        注意: 不要捕获Interrupt异常!
        Interrupt是LangGraph的正常控制流,必须让它传播到框架层
        """
        logger.info("Executing calibration questionnaire node")
        return CalibrationQuestionnaireNode.execute(state, self.store)

    def _requirements_confirmation_node(self, state: ProjectAnalysisState) -> Command:
        """
        需求确认节点

        注意: 不要捕获Interrupt异常!
        Interrupt是LangGraph的正常控制流,必须让它传播到框架层
        """
        logger.info("Executing requirements confirmation node")
        return RequirementsConfirmationNode.execute(state, self.store)
    
    def _find_matching_role(self, predicted_role: str, active_agents: List[str]) -> Optional[str]:
        """
        🔧 修复问题1: 查找预测角色在实际选定角色中的匹配项

        Args:
            predicted_role: 需求分析师预测的角色ID（如 "V2_设计策略专家_3-2"）
            active_agents: 项目总监实际选定的角色列表（如 ["V2_设计总监_2-2", ...]）

        Returns:
            匹配的实际角色ID，如果未找到则返回None

        匹配规则：
        1. 精确匹配（predicted_role in active_agents）
        2. 前缀匹配（提取 V2_设计 前缀，查找以此开头的角色）
        3. 层级匹配（提取 V2 层级，查找同层级角色）
        """
        # 规则1: 精确匹配
        if predicted_role in active_agents:
            return predicted_role

        # 规则2: 前缀匹配（V2_设计）
        parts = predicted_role.split("_")
        if len(parts) >= 2:
            prefix = f"{parts[0]}_{parts[1]}"  # V2_设计

            for agent_id in active_agents:
                if agent_id.startswith(prefix):
                    logger.debug(f"🔍 [匹配] 前缀匹配: {predicted_role} → {agent_id}")
                    return agent_id

        # 规则3: 层级匹配（V2）
        if len(parts) >= 1:
            level_prefix = parts[0]  # V2

            for agent_id in active_agents:
                if agent_id.startswith(level_prefix):
                    logger.debug(f"🔍 [匹配] 层级匹配: {predicted_role} → {agent_id}")
                    return agent_id

        logger.warning(f"⚠️ [匹配失败] 未找到 {predicted_role} 的匹配角色")
        return None

    def _project_director_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        项目总监节点 - 进行战略分析并准备并行任务（仅 Dynamic Mode）

        注意:
        - ProjectDirector返回Command对象,但我们需要提取状态更新
        - 仅支持动态模式: 使用 active_agents 和 execution_mode
        """
        try:
            logger.info("Executing project director node (Dynamic Mode)")

            # 创建项目总监智能体
            agent = AgentFactory.create_agent(
                AgentType.PROJECT_DIRECTOR,
                llm_model=self.llm_model,
                config=self.config
            )

            # 执行分析 - 返回Command对象
            command = agent.execute(state, {}, self.store)

            # 提取状态更新
            if isinstance(command, Command):
                state_update = command.update or {}
            else:
                logger.error(f"Unexpected return type from ProjectDirector: {type(command)}")
                state_update = {"error": "ProjectDirector returned unexpected type"}

            # 🔥 保留关键状态标志（避免被覆盖）
            if state.get("skip_unified_review"):
                state_update["skip_unified_review"] = True
                logger.info("🔄 保留 skip_unified_review 标志")
            else:
                logger.warning("⚠️ [DEBUG] project_director 进入时 skip_unified_review 不存在或为False")
                logger.info(f"🔍 [DEBUG] project_director 输入 state keys: {list(state.keys())}")

            # 动态模式: 使用 active_agents
            active_agents = state_update.get("active_agents", [])
            logger.info(f"📌 Dynamic mode: Project director selected {len(active_agents)} dynamic roles")
            logger.debug(f"Active agents: {active_agents}")

            # 🔧 修复问题1: 校正交付物责任者映射
            deliverable_metadata = state.get("deliverable_metadata") or {}
            deliverable_owner_map = state.get("deliverable_owner_map") or {}

            if deliverable_metadata and active_agents:
                corrected_owner_map = {}
                corrected_metadata = {}

                for deliverable_id, metadata in deliverable_metadata.items():
                    predicted_owner = metadata.get("owner", "")

                    if metadata.get("owner_predicted") and predicted_owner:
                        # 查找实际选定的匹配角色
                        actual_owner = self._find_matching_role(predicted_owner, active_agents)

                        if actual_owner and actual_owner != predicted_owner:
                            logger.info(f"🔧 [修复] 交付物 {deliverable_id} 责任者校正: {predicted_owner} → {actual_owner}")
                            corrected_owner_map[deliverable_id] = actual_owner

                            # 更新元数据
                            corrected_metadata[deliverable_id] = {
                                **metadata,
                                "owner": actual_owner,
                                "owner_predicted": False,  # 标记为已校正
                                "owner_original_prediction": predicted_owner  # 保留原始预测
                            }
                        else:
                            # 未找到匹配或已匹配，保持原值
                            corrected_owner_map[deliverable_id] = predicted_owner
                            corrected_metadata[deliverable_id] = metadata
                    else:
                        # 非预测值，保持原值
                        corrected_owner_map[deliverable_id] = predicted_owner
                        corrected_metadata[deliverable_id] = metadata

                # 更新状态
                if corrected_owner_map:
                    state_update["deliverable_owner_map"] = corrected_owner_map
                    state_update["deliverable_metadata"] = corrected_metadata
                    logger.info(f"✅ [修复] 已校正 {len(corrected_owner_map)} 个交付物责任者映射")

            # 确保 execution_mode 被设置为 dynamic
            state_update["execution_mode"] = "dynamic"

            logger.info(f"Project director completed, prepared {len(active_agents)} agents for execution")

            # 只返回状态更新,不返回Command
            # 路由由条件边处理
            state_update.setdefault("detail", f"规划专家团队并创建 {len(active_agents)} 名专家批次")
            return state_update

        except Exception as e:
            logger.error(f"Project director node failed: {e}")
            import traceback
            traceback.print_exc()
            
            # 🔥 返回明确的错误状态，防止下游节点崩溃
            return {
                "error": str(e),
                "strategic_analysis": None,  # 明确标记为 None
                "active_agents": [],
                "execution_mode": "dynamic",
                "errors": [{"node": "project_director", "error": str(e), "type": "ProjectDirectorFailure"}]
            }

    def _role_task_unified_review_node(self, state: ProjectAnalysisState):
        """
        🆕 角色任务统一审核节点

        合并角色选择审核和任务分派审核，减少人机交互次数

        注意: 不要捕获Interrupt异常!
        Interrupt是LangGraph的正常控制流,必须让它传播到框架层
        
        返回: Command对象（用于动态路由到 batch_executor 或 project_director）
        """
        try:
            logger.info("🔍 Executing unified role & task review node")
            return role_task_unified_review_node(state)  # 返回Command
        except Exception as e:
            # 只捕获非Interrupt异常
            if "Interrupt" not in str(type(e)):
                logger.error(f"❌ Unified review node failed: {e}")
                import traceback
                traceback.print_exc()
                return {"error": str(e)}
            else:
                # 重新抛出Interrupt异常
                raise

    # ============================================================================
    # 🗑️ 已废弃的独立审核节点（保留注释作为历史参考）
    # ============================================================================
    # def _role_selection_review_node(self, state: ProjectAnalysisState):
    #     """角色选择审核节点 - 已合并到 role_task_unified_review"""
    #     pass
    
    # def _task_assignment_review_node(self, state: ProjectAnalysisState):
    #     """任务分派审核节点 - 已合并到 role_task_unified_review"""
    #     pass
    

    async def _quality_preflight_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        质量预检节点 - 前置预防第1层（异步版本）

        🚀 P1优化：使用异步调用，配合 QualityPreflightNode 的异步实现

        在专家执行前进行:
        1. 风险预判
        2. 质量检查清单生成
        3. 能力匹配度验证
        """
        try:
            logger.info("🔍 Executing quality preflight node (async)")
            node = QualityPreflightNode(self.llm_model)
            result = await node(state)  # 🚀 P1优化：使用 await 调用异步方法
            result["detail"] = "质量预检与风险评估"
            return result
        except Exception as e:
            logger.error(f"❌ Quality preflight node failed: {e}")
            import traceback
            traceback.print_exc()
            return {"preflight_completed": False, "error": str(e), "detail": "质量预检失败"}

    def _continue_to_first_batch_agents(self, state: ProjectAnalysisState) -> List[Send]:
        """
        路由函数 - 创建第一批并行任务(V3-V4-V5)（仅 Dynamic Mode）

        第一批专家:
        - V3: 技术架构师
        - V4: 用户体验设计师
        - V5: 商业分析师

        这些专家的分析结果将被V2和V6使用

        支持针对性重执行：
        - 如果 state 中有 specific_agents_to_run，只执行指定的专家
        """
        try:
            logger.info("Creating first batch parallel tasks (V3-V4-V5) using Send API (Dynamic Mode)")

            # 检查是否有指定需要重新执行的专家
            specific_agents = state.get("specific_agents_to_run", [])

            # 动态模式: 从 active_agents 中筛选第一批专家 (V3, V4, V5)
            active_agents = state.get("active_agents", [])
            logger.info(f"🎯 Dynamic mode: filtering first batch from {len(active_agents)} active agents")

            # 第一批专家: 以 V3_, V4_, V5_ 开头的角色
            first_batch_roles = [
                role_id for role_id in active_agents
                if role_id.startswith("V3_") or role_id.startswith("V4_") or role_id.startswith("V5_")
            ]

            logger.info(f"Preparing to execute {len(first_batch_roles)} dynamic agents in first batch")
            logger.debug(f"First batch roles: {first_batch_roles}")

            # 创建Send对象列表
            send_list = []
            for role_id in first_batch_roles:
                # 创建一个包含role_id的新状态
                agent_state = dict(state)  # 复制完整状态
                agent_state["role_id"] = role_id  # 添加role_id (动态模式)
                agent_state["current_stage"] = AnalysisStage.PARALLEL_ANALYSIS.value
                agent_state["execution_batch"] = "first"  # 标记为第一批
                agent_state["is_rerun"] = bool(specific_agents)  # 标记是否为重新执行

                # 🔧 修复 (2025-11-19): 使用正确的节点名 agent_executor
                send_list.append(Send("agent_executor", agent_state))
                logger.debug(f"Created Send for first batch dynamic agent: {role_id}")

            return send_list

        except Exception as e:
            logger.error(f"Failed to create first batch parallel tasks: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": str(e),
                "strategic_analysis": None,  # 明确标记为 None
                "active_agents": [],
                "detail": "项目总监分析失败"
            }

    def _continue_to_second_batch_agents(self, state: ProjectAnalysisState) -> List[Send]:
        """
        路由函数 - 创建第二批并行任务(V2-V6)（仅 Dynamic Mode）

        第二批专家:
        - V2: 设计研究分析师 (依赖V3-V4-V5的输出)
        - V6: 实施规划师 (依赖V3-V4-V5的输出)

        这些专家可以访问 state["agent_results"] 中 V3-V4-V5 的分析结果

        支持针对性重执行:
        - 如果 state 中有 specific_agents_to_run，只执行指定的专家
        """
        try:
            logger.info("Creating second batch parallel tasks (V2-V6) using Send API (Dynamic Mode)")

            # 检查是否有指定需要重新执行的专家
            specific_agents = state.get("specific_agents_to_run", [])

            # 动态模式: 从 active_agents 中筛选第二批专家 (V2, V6)
            active_agents = state.get("active_agents", [])
            logger.info(f"🎯 Dynamic mode: filtering second batch from {len(active_agents)} active agents")

            # 第二批专家: 以 V2_, V6_ 开头的角色
            second_batch_roles = [
                role_id for role_id in active_agents
                if role_id.startswith("V2_") or role_id.startswith("V6_")
            ]

            logger.info(f"Preparing to execute {len(second_batch_roles)} dynamic agents in second batch")
            logger.debug(f"Second batch roles: {second_batch_roles}")

            # 验证第一批结果是否存在
            agent_results = state.get("agent_results", {})
            first_batch_roles = [
                role_id for role_id in active_agents
                if role_id.startswith("V3_") or role_id.startswith("V4_") or role_id.startswith("V5_")
            ]

            first_batch_completed = all(
                role_id in agent_results
                for role_id in first_batch_roles
            )

            if not first_batch_completed:
                logger.warning(f"⚠️ First batch agents not all completed, but proceeding with second batch")
                logger.debug(f"Expected: {first_batch_roles}, Got: {list(agent_results.keys())}")

            # 创建Send对象列表
            send_list = []
            for role_id in second_batch_roles:
                # 创建一个包含role_id的新状态
                agent_state = dict(state)  # 复制完整状态
                agent_state["role_id"] = role_id  # 添加role_id (动态模式)
                agent_state["current_stage"] = AnalysisStage.PARALLEL_ANALYSIS.value
                agent_state["execution_batch"] = "second"  # 标记为第二批
                agent_state["is_rerun"] = bool(specific_agents)  # 标记是否为重新执行

                # 🔧 修复 (2025-11-19): 使用正确的节点名 agent_executor
                send_list.append(Send("agent_executor", agent_state))
                logger.debug(f"Created Send for second batch dynamic agent: {role_id}")

            return send_list

        except Exception as e:
            logger.error(f"Failed to create second batch parallel tasks: {e}")
            import traceback
            traceback.print_exc()
            return []

    async def _execute_agent_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        执行单个智能体节点（仅 Dynamic Mode）

        根据LangGraph Send API,这个节点接收的state是通过Send传递的完整状态
        状态中应该包含role_id字段,指示要执行哪个智能体

        ✨ 集成实时质量监控（第2层预防）:
        - 执行前：注入质量约束到prompt
        - 执行后：快速验证输出质量
        - 如果质量不达标：给予一次重试机会

        重要:
        - 只返回需要更新的字段,不要返回完整状态
        - agent_results使用了Annotated[Dict, merge_agent_results]
        - 多个并发节点的agent_results会被自动合并
        """
        try:
            # 获取 role_id
            role_id = state.get("role_id")

            if not role_id:
                logger.error("❌ No role_id specified in state")
                logger.debug(f"State keys: {list(state.keys())}")
                return {"error": "No role_id specified"}

            # 获取质量检查清单
            quality_checklists = state.get("quality_checklists", {})
            quality_checklist = quality_checklists.get(role_id, {})

            # 获取重试信息
            review_round = state.get("review_round", 0)
            review_feedback = state.get("review_feedback")
            retry_count = state.get(f"retry_count_{role_id}", 0)  # 🆕 重试计数

            # 动态模式: 使用 TaskOrientedExpertFactory (v2.0)
            logger.info(f"🎯 Executing task-oriented agent: {role_id} (轮次{review_round}, 重试{retry_count})")

            # 导入任务导向专家工厂
            from intelligent_project_analyzer.agents.task_oriented_expert_factory import TaskOrientedExpertFactory
            from intelligent_project_analyzer.core.role_manager import RoleManager

            # 初始化角色管理器
            role_manager = RoleManager()

            # 解析角色ID
            logger.info(f"🔍 [DEBUG] Parsing role_id: {role_id}")
            base_type, rid = role_manager.parse_full_role_id(role_id)
            logger.info(f"🔍 [DEBUG] Parsed: base_type={base_type}, rid={rid}")

            # ✅ 尝试直接获取配置，如果失败则用前缀匹配
            role_config = role_manager.get_role_config(base_type, rid)
            
            if not role_config:
                # 使用前缀匹配（如 "V5"）查找配置
                v_prefix = role_id.split("_")[0]  # 提取 "V5"
                logger.info(f"🔍 [DEBUG] Direct match failed, trying prefix: {v_prefix}")
                
                # 遍历所有角色配置，找到匹配前缀的
                for config_key in role_manager.roles.keys():
                    if config_key.startswith(v_prefix):
                        role_config = role_manager.get_role_config(config_key, rid)
                        if role_config:
                            logger.info(f"✅ Found config using prefix match: {config_key}")
                            break
            
            logger.info(f"🔍 [DEBUG] role_config found: {role_config is not None}")

            if not role_config:
                logger.error(f"❌ Role config not found for {role_id}")
                return {"error": f"Role config not found for {role_id}"}

            # 🆕 P0-1修复：执行前总是注入质量约束（无论是否重试）
            if quality_checklist:
                risk_level = quality_checklist.get("risk_level", "low")
                # 只对medium和high风险任务注入质量约束
                if risk_level in ["medium", "high"]:
                    logger.info(f"🔍 注入质量约束到 {role_id} (风险等级: {risk_level}, 轮次: {review_round}, 重试: {retry_count})")
                    original_prompt = role_config.get("system_prompt", "")
                    enhanced_prompt = QualityMonitor.inject_quality_constraints(
                        original_prompt, quality_checklist
                    )
                    role_config["system_prompt"] = enhanced_prompt
                else:
                    logger.debug(f"⏭️ {role_id} 风险等级为 {risk_level}，跳过质量约束注入")

            # 🆕 动态本体论注入逻辑
            # 1. 判断项目类型（如 personal_residential）
            project_type = state.get("project_type")
            if project_type:
                ontology_fragment = self.ontology_loader.get_ontology_by_type(project_type)
            else:
                ontology_fragment = self.ontology_loader.get_meta_framework()
            # 2. 注入到 system_prompt 占位符
            if role_config and "system_prompt" in role_config:
                prompt = role_config["system_prompt"]
                if "{{DYNAMIC_ONTOLOGY_INJECTION}}" in prompt:
                    injected = prompt.replace("{{DYNAMIC_ONTOLOGY_INJECTION}}", yaml.dump(ontology_fragment, allow_unicode=True, default_flow_style=False))
                    role_config["system_prompt"] = injected
                    logger.info(f"✅ 已动态注入本体论片段到 {role_id} 的 system_prompt")
                else:
                    logger.warning(f"⚠️ {role_id} 的 system_prompt 未包含动态注入占位符")

            # 创建任务导向专家工厂实例
            expert_factory = TaskOrientedExpertFactory()

            # 构建上下文
            context = self._build_context_for_expert(state)
            
            # 构建角色对象（包含TaskInstruction）
            # 注意：ProjectAnalysisState是TypedDict，不能直接实例化
            # 我们直接使用state作为上下文
            
            # 🔧 修复v4.0：从 strategic_analysis.selected_roles 中获取 role_object
            # 支持两种匹配方式：精确匹配 和 短格式匹配
            strategic_analysis = state.get("strategic_analysis", {})
            selected_roles = strategic_analysis.get("selected_roles", [])
            role_object = None
            
            # 提取当前 role_id 的短格式 (e.g., "V4_设计研究员_4-1" -> "4-1")
            current_short_id = role_id.split('_')[-1] if '_' in role_id else role_id
            
            # 🔍 调试日志
            logger.debug(f"🔍 [TaskInstruction查找] role_id={role_id}, current_short_id={current_short_id}")
            logger.debug(f"🔍 [TaskInstruction查找] selected_roles数量={len(selected_roles)}")
            if selected_roles:
                sample_ids = [r.get("role_id", "N/A") for r in selected_roles[:3]]
                logger.debug(f"🔍 [TaskInstruction查找] 前3个stored_role_id: {sample_ids}")
            
            for role in selected_roles:
                stored_role_id = role.get("role_id", "")
                # 提取存储的 role_id 的短格式
                stored_short_id = stored_role_id.split('_')[-1] if '_' in stored_role_id else stored_role_id
                
                # 支持多种匹配方式：
                # 1. 精确匹配 (e.g., "V4_设计研究员_4-1" == "V4_设计研究员_4-1")
                # 2. 短格式匹配 (e.g., "4-1" == "4-1")
                # 3. 存储的是短格式，查询的是完整格式
                if (stored_role_id == role_id or 
                    stored_short_id == current_short_id):
                    role_object = role
                    logger.info(f"✅ 找到 {role_id} 的TaskInstruction (stored_role_id={stored_role_id})")
                    break
            
            if not role_object:
                # 构建默认role_object（向后兼容）
                role_object = {
                    "role_id": role_id,
                    "role_name": role_config.get("name", role_id),
                    "dynamic_role_name": role_config.get("name", role_id),
                    "task_instruction": {
                        "objective": f"基于{role_config.get('name', '专业领域')}进行深度分析",
                        "deliverables": [
                            {
                                "name": "专业分析报告",
                                "description": "基于专业领域提供深度分析和建议",
                                "format": "analysis",
                                "priority": "high",
                                "success_criteria": ["分析深入且专业", "建议具有可操作性"]
                            }
                        ],
                        "success_criteria": ["输出符合专业标准", "建议具有实用价值"],
                        "constraints": [],
                        "context_requirements": []
                    }
                }
                logger.warning(f"⚠️ 未找到{role_id}的TaskInstruction，使用默认结构")

            # 执行任务导向专家分析
            try:
                expert_result = await expert_factory.execute_expert(
                    role_object=role_object,
                    context=context,
                    state=state  # 直接传递state
                )
                
                # 构建兼容的结果格式
                result_content = expert_result.get("analysis", "")
                structured_output = expert_result.get("structured_output")
                
                # 记录执行信息
                logger.info(f"✅ 任务导向专家 {role_id} 执行完成")
                if structured_output:
                    logger.info(f"📊 结构化输出验证成功")
                else:
                    logger.warning(f"⚠️ 结构化输出验证失败，使用原始输出")
                    
            except Exception as e:
                logger.error(f"❌ 执行任务导向专家失败: {str(e)}")
                result_content = f"执行失败: {str(e)}"
                expert_result = {
                    "expert_id": role_id,
                    "expert_name": role_config.get("name", role_id),
                    "analysis": result_content,
                    "structured_output": None,
                    "error": True
                }

            # 🆕 执行后：快速验证
            quality_checklist = state.get("quality_checklist", {})
            if quality_checklist and result_content:
                logger.info(f"🔍 快速验证 {role_id} 的输出质量")
                validation_result = QualityMonitor.quick_validation(
                    result_content, quality_checklist, role_id
                )
                
                # 判断是否需要重试
                should_retry = QualityMonitor.should_retry(validation_result)
                
                if should_retry and retry_count == 0:
                    logger.warning(f"⚠️ {role_id} 质量不达标，触发重试")
                    
                    try:
                        # 使用相同的role_object进行重试
                        state[f"retry_count_{role_id}"] = 1
                        expert_result_retry = await expert_factory.execute_expert(
                            role_object=role_object,
                            context=context,
                            state=state  # 直接使用state
                        )
                        
                        # 更新结果
                        result_content = expert_result_retry.get("analysis", "")
                        expert_result = expert_result_retry
                        logger.info(f"✅ {role_id} 重试完成")
                        
                    except Exception as retry_error:
                        logger.error(f"❌ {role_id} 重试失败: {str(retry_error)}")
                
                # 将验证结果附加到输出
                if 'quality_validation' not in expert_result:
                    expert_result["quality_validation"] = validation_result

            # 🔧 修复：将成功返回逻辑移出quality_checklist条件块
            logger.info(f"✅ Dynamic agent {role_id} completed successfully")
            logger.debug(f"Result length: {len(result_content)} characters")

            # 🔧 字段名修复：使用 structured_output（而非 parsed_result）
            structured_output = expert_result.get("structured_output", {})
            if structured_output:
                structured_data = structured_output
                # 确保content字段存在
                if "content" not in structured_data:
                    structured_data["content"] = result_content
                
                # 🔥 Debug: 检查challenge_flags是否存在
                if "challenge_flags" in structured_data:
                    challenge_count = len(structured_data["challenge_flags"])
                    logger.info(f"🔥 [DEBUG] {role_id} 的 structured_data 包含 {challenge_count} 个 challenge_flags")
                else:
                    logger.debug(f"ℹ️ [DEBUG] {role_id} 的 structured_data 不包含 challenge_flags")
            else:
                structured_data = {"content": result_content}
                logger.debug(f"ℹ️ [DEBUG] {role_id} 无 structured_output，使用默认 structured_data")

            # 返回结果 - 使用 role_id 作为 key
            role_name = role_config.get("name", "未知角色")
            dynamic_role_name = role_object.get("dynamic_role_name", role_name)

            # 🔧 修复（2025-11-30）：detail 显示完整的 role_id，便于前端同步显示
            # 格式：专家【角色ID】执行中
            detail_message = f"专家【{role_id}】完成分析"

            # 只有在result_content真正为空时才返回错误
            if not result_content:
                logger.warning(f"⚠️ Dynamic agent {role_id} returned no results")
                return {"error": f"No results from {role_id}"}

            # 🚀 P4优化：单个专家完成即推送结果（渐进式展示）
            # 获取session_id用于WebSocket推送
            session_id = state.get("session_id")
            if session_id:
                try:
                    # 导入broadcast函数
                    from intelligent_project_analyzer.api.server import broadcast_to_websockets

                    # 推送专家结果
                    import asyncio
                    asyncio.create_task(broadcast_to_websockets(session_id, {
                        "type": "agent_result",
                        "role_id": role_id,
                        "role_name": role_name,
                        "dynamic_role_name": dynamic_role_name,
                        "analysis": result_content,
                        "structured_data": structured_data,
                        "timestamp": datetime.now().isoformat()
                    }))
                    logger.info(f"📤 [Progressive] 已推送专家结果: {role_id} ({dynamic_role_name})")
                except Exception as broadcast_error:
                    logger.warning(f"⚠️ WebSocket推送失败: {broadcast_error}")

            return {
                "agent_results": {
                    role_id: {
                        "role_id": role_id,
                        "role_name": role_name,
                        "analysis": result_content,
                        "confidence": 0.8,  # 默认置信度
                        "structured_data": structured_data  # 🆕 使用完整的parsed_result
                    }
                },
                "detail": detail_message
            }

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    def _batch_executor_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        批次执行器节点 - 验证并准备执行当前批次

        ✅ 修复：节点函数只返回状态更新（Dict），Send 对象的创建交给条件边函数
        ✅ 新增：支持 specific_agents_to_run（审核触发的重新执行）

        这是动态批次执行的核心节点，替代了硬编码的 first_batch_agent 和 second_batch_agent。

        工作原理:
        1. 检查是否有 specific_agents_to_run（审核触发的重新执行）
        2. 如果有，创建一个临时批次只包含指定的专家
        3. 否则，从 state["execution_batches"] 读取正常批次
        4. 返回空字典（状态无需更新）
        5. 后续由条件边函数 _create_batch_sends 创建 Send 任务

        状态输入:
        - specific_agents_to_run: List[str] - 审核指定需要重新执行的专家（优先）
        - execution_batches: List[List[str]] - 所有批次的角色列表
        - current_batch: int - 当前批次编号（1-based）
        - agent_results: Dict - 已完成专家的结果

        返回:
        - Dict[str, Any] - 状态更新（通常为空字典）
        """
        try:
            # ✅ 优先检查是否有审核触发的重新执行
            specific_agents = state.get("specific_agents_to_run", [])
            
            if specific_agents:
                logger.info(f"🔄 审核触发的重新执行: {len(specific_agents)} 个专家")
                logger.info(f"   专家列表: {specific_agents}")
                
                # 创建临时批次
                return {
                    "execution_batches": [specific_agents],
                    "current_batch": 1,
                    "total_batches": 1,
                    "is_rerun": True,
                    "skip_role_review": True,
                    "skip_task_review": True
                }
            
            # 正常批次执行
            batches = state.get("execution_batches", [])
            current_batch = state.get("current_batch", 1)
            total_batches = len(batches)

            logger.info(f"🎯 Batch executor: preparing batch {current_batch}/{total_batches}")

            # 验证批次编号
            if current_batch < 1 or current_batch > total_batches:
                logger.error(f"❌ Invalid batch number: {current_batch} (total: {total_batches})")
                return {"errors": [f"Invalid batch number: {current_batch}"]}

            if not batches:
                logger.error("❌ No execution_batches found in state")
                return {"errors": ["No execution batches defined"]}

            # 获取当前批次的角色列表（0-indexed）
            batch_roles = batches[current_batch - 1]
            display_roles = [format_role_display_name(r) for r in batch_roles]
            logger.info(f"📋 Batch {current_batch} contains {len(batch_roles)} agents: {display_roles}")

            # ✅ 只返回状态更新，不创建 Send 对象
            return {"detail": f"批次 {current_batch}/{total_batches}: {len(batch_roles)} 位专家"}

        except Exception as e:
            logger.error(f"❌ Batch executor failed: {e}")
            import traceback
            traceback.print_exc()
            return {"errors": [str(e)]}

    def _create_batch_sends(self, state: ProjectAnalysisState) -> List[Send]:
        """
        批次 Send 创建器 - 条件边函数，返回并行任务列表

        ✅ 新增：专门负责创建 Send 对象的条件边函数，配合 _batch_executor_node 使用
        ✅ 修复：支持审核触发的重新执行（specific_agents_to_run）

        这个函数作为条件边函数，根据当前批次创建对应的 Send 任务列表。
        LangGraph 会自动并行执行这些任务。

        工作原理:
        1. 从 state["execution_batches"] 读取所有批次
        2. 根据 state["current_batch"] 确定当前要执行的批次
        3. 为批次中的每个角色创建 Send 对象
        4. 返回 Send 列表，LangGraph 自动并行调度

        状态输入:
        - execution_batches: List[List[str]] - 所有批次的角色列表
        - current_batch: int - 当前批次编号（1-based）
        - is_rerun: bool - 是否为审核触发的重新执行
        - review_feedback: Dict - 审核反馈（如果是重新执行）

        返回:
        - List[Send] - 并行任务列表，每个 Send 执行一个智能体

        注意:
        - 这个函数必须是条件边函数，不能是节点函数
        - 通过 add_conditional_edges 配置到图中
        """
        batches = state.get("execution_batches") or []
        current_batch = state.get("current_batch", 1)
        is_rerun = state.get("is_rerun", False)
        review_feedback = state.get("review_feedback", {})

        # 边界检查
        if not batches:
            logger.warning(f"⚠️ No batches found, batches is None or empty")
            return []
        
        if current_batch < 1 or current_batch > len(batches):
            logger.warning(
                f"⚠️ No valid batch to execute: current={current_batch}, total={len(batches)}"
            )
            return []

        # 获取当前批次的角色列表（0-indexed）
        batch_roles = batches[current_batch - 1]
        
        if is_rerun:
            display_roles = [format_role_display_name(r) for r in batch_roles]
            logger.info(f"🔄 创建重新执行任务: {len(batch_roles)} 个专家 {display_roles}")
        else:
            display_roles = [format_role_display_name(r) for r in batch_roles]
            logger.info(f"📋 创建批次 {current_batch} 任务: {len(batch_roles)} 个专家 {display_roles}")

        # 创建 Send 对象列表
        send_list = []
        for role_id in batch_roles:
            # 为每个智能体创建独立的状态副本
            agent_state = dict(state)
            agent_state["role_id"] = role_id
            agent_state["execution_batch"] = f"batch_{current_batch}"
            agent_state["current_stage"] = AnalysisStage.PARALLEL_ANALYSIS.value
            agent_state["is_rerun"] = is_rerun
            
            # ✅ 如果是重新执行，添加针对该专家的审核反馈
            if is_rerun and review_feedback:
                feedback_by_agent = review_feedback.get("feedback_by_agent", {})
                agent_feedback = feedback_by_agent.get(role_id, {})
                if agent_feedback:
                    agent_state["review_feedback_for_agent"] = agent_feedback
                    logger.info(f"   {role_id}: 附加审核反馈 ({len(agent_feedback.get('issues', []))} 个问题)")

            send_list.append(Send("agent_executor", agent_state))
            logger.debug(f"  ➤ Created Send for: {role_id}")

        logger.info(f"✅ Created {len(send_list)} parallel tasks for batch {current_batch}")
        return send_list

    def _intermediate_aggregator_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        批次聚合节点 - 验证当前批次的执行结果（通用版，2025-11-18重构）

        功能:
        1. 验证当前批次的所有专家是否成功完成
        2. 记录详细日志
        3. 标记当前批次为已完成
        4. 为下一批次准备依赖数据
        5. 返回状态更新，触发下一批次或进入审核

        重构说明：
        - 从固定的V3/V4/V5检查改为基于execution_batches的动态检查
        - 支持任意数量的批次（1-N批）
        - 通过current_batch跟踪当前批次
        
        🔧 P1修复（2025-11-25）：
        - 等待当前批次所有agent完成后再执行聚合
        - 通过检查agent_results确保不会过早触发
        
        🔧 N2优化（2025-11-25）：
        - LangGraph Send API会在每个并行任务完成时触发此节点（预期行为）
        - 本节点检查所有任务是否完成，未完成时返回空字典等待
        - 这是LangGraph并行执行的标准"轮询模式"
        """
        try:
            agent_results = state.get("agent_results", {})
            batches = state.get("execution_batches", [])
            current_batch = state.get("current_batch", 1)
            total_batches = state.get("total_batches", len(batches))

            logger.info(f"📊 当前批次: {current_batch}/{total_batches}")

            if not batches:
                logger.warning("未找到 execution_batches，无法验证批次完成情况")
                # 降级到旧逻辑（保留兼容性）
                return self._intermediate_aggregator_node_legacy(state)

            # 获取当前批次的角色列表
            if current_batch < 1 or current_batch > len(batches):
                logger.error(f"当前批次编号 {current_batch} 超出范围")
                return {"error": f"Invalid batch number: {current_batch}"}

            current_batch_roles = batches[current_batch - 1]

            # 🔧 N2优化：快速检查是否所有agent已完成（减少无效日志）
            pending_agents = [role_id for role_id in current_batch_roles if role_id not in agent_results]
            if pending_agents:
                # ⚡ LangGraph并行模式：部分任务完成时会触发此节点，这是预期行为
                # 返回空字典，等待所有任务完成后再次调用

                # 🚀 P2优化：添加轮询计数器，优化日志级别
                poll_count_key = f"_aggregator_poll_count_batch_{current_batch}"
                poll_count = state.get(poll_count_key, 0) + 1

                # 只在第一次轮询时记录 info 级别日志，后续使用 debug 级别
                if poll_count == 1:
                    logger.info(f"⏳ [Polling] 批次 {current_batch} 开始等待: {len(pending_agents)}/{len(current_batch_roles)} 未完成")
                else:
                    logger.debug(f"⏳ [Polling #{poll_count}] 批次 {current_batch} 等待中: {len(pending_agents)}/{len(current_batch_roles)} 未完成")

                # 返回更新的轮询计数
                return {poll_count_key: poll_count}
            
            # ✅ 所有agent已完成，开始详细聚合
            # 🚀 P2优化：记录总轮询次数
            poll_count_key = f"_aggregator_poll_count_batch_{current_batch}"
            total_polls = state.get(poll_count_key, 0)
            if total_polls > 0:
                logger.info(f"✅ [Aggregator] 批次 {current_batch}/{total_batches} 所有任务完成（经过 {total_polls} 次轮询），开始聚合")
            else:
                logger.info(f"✅ [Aggregator] 批次 {current_batch}/{total_batches} 所有任务完成，开始聚合")

            # 检查完成情况
            completed_agents = []
            failed_agents = []

            for role_id in current_batch_roles:
                if role_id in agent_results:
                    result = agent_results[role_id]
                    confidence = result.get("confidence", 0)
                    has_error = "error" in result

                    if has_error:
                        failed_agents.append(role_id)
                        logger.warning(f"{role_id} completed with error: {result.get('error')}")
                    else:
                        completed_agents.append(role_id)
                        logger.info(f"✅ {role_id} completed successfully (confidence: {confidence:.2%})")
                else:
                    failed_agents.append(role_id)
                    logger.warning(f"⚠️ {role_id} not found in results")

            # 记录汇总信息
            logger.info(f"批次 {current_batch} 汇总: {len(completed_agents)}/{len(current_batch_roles)} 成功完成")
            if completed_agents:
                logger.info(f"✅ 已完成: {', '.join(completed_agents)}")
            if failed_agents:
                logger.warning(f"❌ 失败/缺失: {', '.join(failed_agents)}")

            # 准备依赖数据摘要
            dependency_summary = {
                "batch_number": current_batch,
                "batch_completed": len(completed_agents) == len(current_batch_roles),
                "completed_count": len(completed_agents),
                "total_count": len(current_batch_roles),
                "completed_agents": completed_agents,
                "failed_agents": failed_agents,
                "timestamp": datetime.now().isoformat()
            }

            # 更新已完成批次列表
            completed_batches = state.get("completed_batches", [])
            if current_batch not in completed_batches:
                completed_batches_updated = completed_batches + [current_batch]
            else:
                completed_batches_updated = completed_batches

            logger.info(f"✅ 批次 {current_batch} 聚合完成")
            logger.info(f"🔄 已完成批次: {completed_batches_updated}")

            # 返回状态更新（下一步由second_batch_strategy_review决定路由）

            # 🔧 修复（2025-11-30）：构造更具体的detail消息，显示刚完成的专家
            if completed_agents:
                # 如果只有1个专家，显示具体名称；如果多个，显示数量和列表
                if len(completed_agents) == 1:
                    detail_message = f"专家【{completed_agents[0]}】分析完成"
                else:
                    agent_list = "、".join([agent.split("_")[-1] if "_" in agent else agent for agent in completed_agents])
                    detail_message = f"批次 {current_batch} 完成：{agent_list} 等 {len(completed_agents)} 位专家"
            else:
                detail_message = f"批次 {current_batch} 执行中..."

            return {
                "dependency_summary": dependency_summary,
                "completed_batches": completed_batches_updated,
                "updated_at": datetime.now().isoformat(),
                "detail": detail_message
            }

        except Exception as e:
            logger.error(f"Intermediate aggregator node failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "error": str(e),
                "updated_at": datetime.now().isoformat()
            }

    def _intermediate_aggregator_node_legacy(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        旧版批次聚合逻辑（保留兼容性）

        当state中没有execution_batches时使用此方法
        """
        logger.warning("使用旧版intermediate_aggregator逻辑")

        agent_results = state.get("agent_results", {})
        active_agents = state.get("active_agents", [])

        # 硬编码检查V3/V4/V5
        first_batch_roles = [
            role_id for role_id in active_agents
            if role_id.startswith("V3_") or role_id.startswith("V4_") or role_id.startswith("V5_")
        ]

        completed_agents = []
        failed_agents = []

        for role_id in first_batch_roles:
            if role_id in agent_results:
                result = agent_results[role_id]
                has_error = "error" in result
                if has_error:
                    failed_agents.append(role_id)
                else:
                    completed_agents.append(role_id)
            else:
                failed_agents.append(role_id)

        dependency_summary = {
            "first_batch_completed": len(completed_agents) == len(first_batch_roles),
            "completed_count": len(completed_agents),
            "total_count": len(first_batch_roles),
            "completed_agents": completed_agents,
            "failed_agents": failed_agents,
            "timestamp": datetime.now().isoformat()
        }

        return {
            "dependency_summary": dependency_summary,
            "updated_at": datetime.now().isoformat()
        }

    # ============================================================================
    # 🆕 v3.5 Expert Collaboration: Challenge Detection Node
    # ============================================================================
    
    def _detect_challenges_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        🆕 v3.5 挑战检测节点 - 检测专家输出中的challenge_flags并处理
        
        工作流程:
        1. 从state中提取所有专家的输出
        2. 调用detect_and_handle_challenges_node()检测挑战
        3. 更新state包含挑战检测和处理结果
        4. 设置requires_feedback_loop标志
        
        状态输入:
        - batch_results: Dict - 各批次专家的输出
        - (可选) v2_output, v3_output等直接字段
        
        状态输出:
        - challenge_detection: Dict - 挑战检测结果
        - challenge_handling: Dict - 挑战处理结果
        - has_active_challenges: bool - 是否有活跃挑战
        - requires_feedback_loop: bool - 是否需要反馈循环
        - feedback_loop_reason: str - 反馈循环原因（如有）
        
        Returns:
            更新的状态字典（只包含新增/修改的字段）
        """
        logger.info("🔍 [v3.5] 开始检测专家挑战...")
        
        try:
            # 调用核心挑战检测函数（现在只返回新增字段）
            updated_state = detect_and_handle_challenges_node(state)
            
            # 记录检测结果
            if updated_state.get("has_active_challenges"):
                challenge_count = len(updated_state.get("challenge_detection", {}).get("challenges", []))
                logger.info(f"🔥 [v3.5] 检测到 {challenge_count} 个专家挑战")
                
                if updated_state.get("requires_feedback_loop"):
                    logger.warning("⚠️ [v3.5] 需要启动反馈循环回访需求分析师")
            else:
                logger.info("✅ [v3.5] 未检测到挑战，专家接受需求分析师的洞察")
            
            return updated_state
            
        except Exception as e:
            logger.error(f"❌ [v3.5] 挑战检测失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # 返回安全的默认值
            return {
                "has_active_challenges": False,
                "requires_feedback_loop": False,
                "challenge_detection": {"has_challenges": False, "challenges": []},
                "challenge_handling": {"requires_revisit": False}
            }
            # 失败时返回原状态，不影响工作流继续
            return {
                **state,
                "has_active_challenges": False,
                "requires_feedback_loop": False,
                "challenge_detection_error": str(e)
            }
    
    def _route_after_challenge_detection(self, state: ProjectAnalysisState) -> str:
        """
        🆕 v3.5 挑战检测后的路由决策
        
        根据挑战检测结果决定下一步:
        - 如果requires_manual_review=True → "manual_review" (>3个must_fix问题)
        - 如果requires_client_review=True → "analysis_review" (交甲方裁决)
        - 如果requires_feedback_loop=True → "revisit_requirements" (回访需求分析师)
        - 否则 → "continue_workflow" (继续正常流程)
        
        优先级: manual_review > escalate > revisit_ra > continue
        
        Args:
            state: 当前工作流状态
            
        Returns:
            路由目标: "manual_review" | "analysis_review" | "revisit_requirements" | "continue_workflow"
        """
        # 🆕 最高优先级：检查是否需要人工审核（>3个must_fix）
        requires_manual_review = state.get("requires_manual_review", False)
        if requires_manual_review:
            issues_count = state.get("critical_issues_count", 0)
            logger.error(f"🚨 [Manual Review] 发现{issues_count}个严重质量问题（超过阈值），触发人工审核")
            return "manual_review"
        
        # 🆕 优先检查是否需要甲方裁决（escalate闭环）
        requires_client_review = state.get("requires_client_review", False)
        if requires_client_review:
            escalated_count = len(state.get("escalated_challenges", []))
            logger.warning(f"🚨 [v3.5 Escalate] {escalated_count}个挑战需要甲方裁决，路由到审核节点")
            return "analysis_review"
        
        # 检查是否需要回访需求分析师（revisit_ra闭环）
        requires_feedback = state.get("requires_feedback_loop", False)
        if requires_feedback:
            reason = state.get("feedback_loop_reason", "专家挑战需要澄清")
            logger.info(f"🔄 [v3.5] 启动反馈循环: {reason}")
            return "revisit_requirements"
        
        # 默认继续正常流程
        logger.info("➡️ [v3.5] 继续正常工作流")
        return "continue_workflow"

    def _batch_router_node(self, state: ProjectAnalysisState) -> Command:
        """
        批次路由器节点 - 决定下一步执行什么

        这是动态批次执行的关键路由节点，替代了硬编码的边连接。

        工作原理:
        1. 检查是否为审核触发的重新执行
        2. 如果是重新执行且skip_second_review=True → 跳过审核，直接进入后续流程
        3. 如果是重新执行且需要审核 → 返回分析审核
        4. 检查当前批次和总批次数
        5. 如果还有下一批次 → 增加批次号并路由到批次策略审核
        6. 如果所有批次完成 → 路由到分析审核

        状态输入:
        - is_rerun: bool - 是否为审核触发的重新执行
        - skip_second_review: bool - 整改后是否跳过二次审核
        - current_batch: int - 当前已完成的批次编号
        - total_batches: int - 总批次数
        - dependency_summary: Dict - 当前批次的完成摘要

        返回:
        - Command(goto="detect_challenges") - 如果是整改后跳过审核
        - Command(goto="analysis_review") - 如果需要审核
        - Command(goto="batch_strategy_review") - 如果还有下一批次
        """
        try:
            is_rerun = state.get("is_rerun", False)
            skip_second_review = state.get("skip_second_review", False)
            current_batch = state.get("current_batch", 1)
            batches = state.get("execution_batches", [])
            total_batches = state.get("total_batches", len(batches))
            dependency_summary = state.get("dependency_summary", {})

            logger.info(f"🔀 Batch router: current={current_batch}, total={total_batches}, is_rerun={is_rerun}, skip_second_review={skip_second_review}")

            # ✅ 优先检查：如果是审核触发的重新执行（整改）
            if is_rerun:
                # 🎯 关键改进：检查是否跳过二次审核
                if skip_second_review:
                    logger.info("✅ 专家整改完成，跳过二次审核，直接进入挑战检测和报告生成")
                    return Command(
                        update={
                            "is_rerun": False,  # 清除标记
                            "skip_second_review": False,  # 清除标记
                            "specific_agents_to_run": [],  # 清空
                            "analysis_approved": True,  # 标记为审核通过（整改视为通过）
                        },
                        goto="detect_challenges"  # 🔑 跳过审核，直接进入挑战检测
                    )
                else:
                    # 需要二次审核（一般不会走到这里，因为我们设置了skip_second_review=True）
                    logger.info("🔄 重新执行完成，返回分析审核进行评估")
                    return Command(
                        update={
                            "is_rerun": False,  # 清除标记
                            "specific_agents_to_run": []  # 清空
                        },
                        goto="analysis_review"
                    )

            # 验证批次完成情况
            batch_completed = dependency_summary.get("batch_completed", False)
            if not batch_completed:
                logger.warning(f"⚠️ Batch {current_batch} not fully completed, but routing to next step")
                completed_count = dependency_summary.get("completed_count", 0)
                total_count = dependency_summary.get("total_count", 0)
                logger.warning(f"   Completed: {completed_count}/{total_count}")

            # 决策路由
            if current_batch < total_batches:
                # 还有下一批次，增加批次号
                next_batch = current_batch + 1
                logger.info(f"➡️  Routing to next batch: {next_batch}/{total_batches}")
                logger.info(f"   Next batch will contain: {len(batches[next_batch - 1])} agents")

                return Command(
                    update={"current_batch": next_batch},
                    goto="batch_strategy_review"
                )
            else:
                # 所有批次完成，检查是否已审核通过
                logger.info(f"✅ All {total_batches} batches completed")
                
                # ✅ 修复：如果已审核通过（第1轮触发detect_challenges），不再重复触发
                if state.get("analysis_approved", False):
                    logger.info("✅ 分析已审核通过，跳过重复审核")
                    return Command(goto=END)
                
                logger.info("➡️  Routing to analysis review")
                return Command(goto="analysis_review")

        except Exception as e:
            logger.error(f"❌ Batch router failed: {e}")
            import traceback
            traceback.print_exc()
            # 出错时默认进入审核
            return Command(goto="analysis_review")

    def _batch_strategy_review_node(self, state: ProjectAnalysisState) -> Command:
        """
        批次策略审核节点 - 支持多种执行模式 (v3.6优化)

        🔄 v3.6优化 (2025-11-29): 支持用户确认模式
        - 默认：手动确认模式，用户可查看并批准每个批次
        - 可选：自动执行模式（通过execution_mode配置）

        支持的执行模式:
        - "manual": 每批次都需要用户确认（默认）
        - "automatic": 全自动执行（旧方案C行为）
        - "preview": 显示计划后自动执行

        设计理念:
        - 批次策略是技术实现细节，但用户应该有选择权
        - 提供透明度和控制感，同时保持灵活性
        - 默认安全（需确认），但支持高效模式（自动）

        工作原理:
        1. 读取执行模式配置
        2. 根据模式选择是否触发用户确认
        3. 收集批次信息并显示给用户

        状态输入:
        - current_batch: int - 即将执行的批次编号
        - execution_batches: List[List[str]] - 所有批次
        - execution_mode: str - 执行模式配置（可选）

        返回:
        - Command - 根据模式返回不同的命令
        """
        try:
            from langgraph.types import interrupt

            current_batch = state.get("current_batch", 1)
            batches = state.get("execution_batches", [])
            execution_mode = state.get("execution_mode", "manual")  # 默认手动确认

            # 获取当前批次的专家列表
            batch_agents = batches[current_batch - 1] if current_batch <= len(batches) else []

            # 🔥 v3.6: 根据执行模式决定是否需要用户确认
            if execution_mode == "automatic":
                # 方案C：全自动执行（旧行为）
                logger.info(f"⚡ 批次 {current_batch}/{len(batches)} 自动执行（方案C：全自动批次调度）")
                return Command(
                    update={
                        "batch_strategy_approved": True,
                        "auto_approved": True,
                        "auto_approval_reason": "execution_mode=automatic"
                    },
                    goto="batch_executor"
                )
            elif execution_mode == "preview":
                # 方案D：显示计划后自动执行
                logger.info(f"📋 批次 {current_batch}/{len(batches)} 显示计划后自动执行")
                # TODO: 可以在这里发送通知给前端
                return Command(
                    update={
                        "batch_strategy_approved": True,
                        "auto_approved": True,
                        "auto_approval_reason": "execution_mode=preview"
                    },
                    goto="batch_executor"
                )
            else:
                # 方案A：手动确认模式（默认）
                logger.info(f"👤 批次 {current_batch}/{len(batches)} 等待用户确认")

                # 构建批次信息
                batch_info = {
                    "interaction_type": "batch_confirmation",  # 🔥 修复：与其他 interrupt 保持一致使用 interaction_type
                    "current_batch": current_batch,
                    "total_batches": len(batches),
                    "agents_in_batch": batch_agents,
                    "execution_strategy": "parallel" if len(batch_agents) > 1 else "sequential",
                    "message": f"准备执行批次 {current_batch}/{len(batches)}",
                    "details": {
                        "专家列表": batch_agents,
                        "执行方式": "并行执行" if len(batch_agents) > 1 else "顺序执行",
                        "预计耗时": f"{len(batch_agents) * 3}分钟" if len(batch_agents) == 1 else f"{4}分钟"
                    },
                    "options": {
                        "approve": "批准执行",
                        "skip": "跳过此批次",
                        "modify": "修改批次配置"
                    }
                }

                # 触发中断，等待用户确认
                logger.info(f"🔍 [DEBUG] 触发批次确认中断: {batch_info}")
                user_response = interrupt(batch_info)
                logger.info(f"📥 收到用户响应: {user_response}")

                # 处理用户响应
                if user_response == "skip" or (isinstance(user_response, dict) and user_response.get("action") == "skip"):
                    logger.info("⏭️ 用户选择跳过此批次")
                    # 跳过当前批次，进入下一批次
                    return Command(
                        update={
                            "current_batch": current_batch + 1,
                            "batch_strategy_approved": False,
                            "batch_skipped": True
                        },
                        goto="batch_router"  # 返回路由器检查是否还有更多批次
                    )
                else:
                    # 批准执行（默认行为）
                    logger.info("✅ 用户批准执行此批次")
                    return Command(
                        update={
                            "batch_strategy_approved": True,
                            "auto_approved": False,
                            "user_confirmed": True
                        },
                        goto="batch_executor"
                    )

        except Exception as e:
            # 只捕获非Interrupt异常
            if "Interrupt" not in str(type(e)):
                logger.error(f"❌ Batch strategy review failed: {e}")
                import traceback
                traceback.print_exc()
                # 出错时默认批准并继续
                return Command(goto="batch_executor")
            else:
                # 重新抛出Interrupt异常（LangGraph需要）
                raise

    def _analysis_review_node(self, state: ProjectAnalysisState) -> Command:
        """
        分析审核节点 - 递进式单轮审核 (v2.0)

        核心改进:
        1. 移除多轮迭代逻辑
        2. 递进式三阶段：红→蓝→评委→甲方
        3. 输出改进建议（而非重新执行）
        4. 记录final_ruling到state
        """
        logger.info("Executing progressive single-round analysis review node")
        return AnalysisReviewNode.execute(
            state=state,
            store=self.store,
            llm_model=self.llm_model,
            config=self.config
        )
    
    def _manual_review_node(self, state: ProjectAnalysisState) -> Command:
        """
        人工审核节点 - 处理严重质量问题 (🆕)
        
        当审核系统发现>3个must_fix问题时触发，暂停流程等待用户裁决：
        1. 继续：接受风险生成报告
        2. 终止：全面整改后再生成报告
        3. 选择性整改：用户选择关键问题进行整改
        
        注意: 不要捕获Interrupt异常!
        Interrupt是LangGraph的正常控制流,必须让它传播到框架层
        """
        logger.info("🚨 Executing manual review node for critical quality issues")
        return ManualReviewNode.execute(
            state=state,
            store=self.store
        )
    
    def _result_aggregator_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        结果聚合节点

        注意: 只返回需要更新的字段,不返回完整状态
        这样可以避免并发更新冲突
        
        🔧 修复: 不更新current_stage,避免与pdf_generator并发冲突
        """
        try:
            logger.info("Executing result aggregator node")

            # 创建结果聚合器智能体
            agent = ResultAggregatorAgent(
                llm_model=self.llm_model,
                config=self.config
            )

            # 执行聚合
            result = agent.execute(state, {}, self.store)

            # 只返回需要更新的字段 (不更新current_stage)
            return {
                "final_report": result.structured_data,
                "agent_results": {
                    "RESULT_AGGREGATOR": result.to_dict()
                },
                "updated_at": datetime.now().isoformat(),
                "detail": "整合专家成果，生成最终报告草稿"
            }

        except Exception as e:
            logger.error(f"Result aggregator node failed: {e}")
            return {
                "error": str(e),
                "updated_at": datetime.now().isoformat(),
                "detail": "结果聚合失败"
            }
    
    # def _final_review_node(self, state: ProjectAnalysisState) -> Command:
    #     """
    #     最终审核节点 - 已移除
    #
    #     根据客户需求,工作流程应该是:
    #     结果聚合 → PDF生成 → 结束
    #     不需要最终审核阶段
    #
    #     注意: 不要捕获Interrupt异常!
    #     Interrupt是LangGraph的正常控制流,必须让它传播到框架层
    #     """
    #     logger.info("Executing final review node")
    #     return FinalReviewNode.execute(state, self.store)
    
    def _pdf_generator_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        报告生成节点 (使用纯文本生成器进行测试)

        注意: 只返回需要更新的字段,不返回完整状态
        这样可以避免并发更新冲突
        """
        try:
            logger.info("Executing report generator node (text mode for testing)")

            # 使用纯文本生成器进行测试
            from ..report.text_generator import TextGeneratorAgent
            agent = TextGeneratorAgent(config=self.config)

            # 执行报告生成
            result = agent.execute(state, {}, self.store)

            # 只返回需要更新的字段
            return {
                "current_stage": AnalysisStage.COMPLETED.value,
                "pdf_path": result.structured_data.get("file_path"),
                "agent_results": {
                    "REPORT_GENERATOR": result.to_dict()
                },
                "updated_at": datetime.now().isoformat(),
                "detail": "生成最终交付文档"
            }

        except Exception as e:
            logger.error(f"Report generator node failed: {e}")
            return {
                "error": str(e),
                "updated_at": datetime.now().isoformat(),
                "detail": "报告生成失败"
            }
    
    def _user_question_node(self, state: ProjectAnalysisState) -> Command:
        """
        用户追问节点
        
        🔧 修复 (2025-11-27): 不要捕获 Interrupt 异常
        Interrupt 是 LangGraph 的正常控制流，必须让它传播到框架层
        """
        logger.info("Executing user question node")
        # ❌ 不要用 try-except 捕获！Interrupt 必须传播
        return UserQuestionNode.execute(state, self.store)
    
    # 路由函数
    def _route_from_batch_aggregator(self, state: ProjectAnalysisState) -> str:
        """
        批次聚合器后的路由函数

        🔧 修复（2025-11-30）：移除 analysis_approved 的 END 路径
        - Bug原因：当 analysis_approved=True 时直接 END，跳过了 result_aggregator 和 pdf_generator
        - 修复：始终路由到 batch_router，让 batch_router 决定是否进入 analysis_review
        - analysis_review → detect_challenges → result_aggregator 是唯一生成报告的路径

        逻辑:
        - 始终 → batch_router
          - batch_router 检查批次完成情况：
            - 如果还有批次：继续下一批
            - 如果所有批次完成：进入 analysis_review → detect_challenges → result_aggregator → pdf_generator
        """
        logger.info("🔀 [batch_aggregator] 路由到 batch_router 检查批次状态")
        return "batch_router"
    
    def _route_after_requirements_confirmation(self, state: ProjectAnalysisState) -> Literal["project_director", "requirements_analyst"]:
        """需求确认后的路由"""
        if state.get("requirements_confirmed"):
            return "project_director"
        else:
            return "requirements_analyst"
    
    def _route_after_pdf_generator(self, state: ProjectAnalysisState) -> Union[str, Any]:
        """报告生成后的路由: 直接结束，由前端负责结果呈现和追问交互"""
        # 标记追问功能可用，前端会根据此标志显示追问入口
        state["post_completion_followup_available"] = self.config.get("post_completion_followup_enabled", True)
        
        logger.info("✅ [pdf_generator] 报告已生成，流程结束，前端接管结果呈现")
        return END

    def _route_after_analysis_review(self, state: ProjectAnalysisState) -> Literal["result_aggregator", "project_director", "user_question"]:
        """分析审核后的路由"""
        if state.get("analysis_approved"):
            return "result_aggregator"
        elif state.get("additional_questions"):
            return "user_question"
        else:
            return "project_director"
    
    # def _route_after_final_review(self, state: ProjectAnalysisState) -> Literal["pdf_generator", "result_aggregator"]:
    #     """最终审核后的路由 - 已移除，因为不再有最终审核阶段"""
    #     if state.get("final_approved"):
    #         return "pdf_generator"
    #     else:
    #         return "result_aggregator"
    
    def _route_after_user_question(self, state: ProjectAnalysisState) -> Literal["project_director", END]:
        """
        用户追问后的路由

        🔧 修复 (2025-11-27): 追问完成后应该结束流程，而不是回到 result_aggregator
        避免无限循环：pdf_generator → user_question → result_aggregator → pdf_generator

        🔥 修复 (2025-11-29): additional_questions是list类型，不能调用.strip()
        """
        additional_questions = state.get("additional_questions")

        # 🔥 修复：additional_questions 是list，不是string
        if additional_questions and len(additional_questions) > 0:
            logger.info(f"📝 用户提出追问({len(additional_questions)}个)，返回 project_director 重新分析")
            return "project_director"
        else:
            logger.info("✅ 用户未追问或追问完成，流程结束")
            return END
    
    def run(self, user_input: str, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        运行工作流
        
        Args:
            user_input: 用户输入
            session_id: 会话ID
            
        Returns:
            工作流执行结果
        """
        try:
            # 生成会话ID
            if not session_id:
                session_id = str(uuid.uuid4())
            
            # 初始化状态
            initial_state = StateManager.create_initial_state(
                user_input=user_input,
                session_id=session_id
            )
            
            logger.info(f"Starting workflow execution for session {session_id}")
            
            # 执行工作流
            config = {"configurable": {"thread_id": session_id}}
            final_state = self.graph.invoke(initial_state, config)
            
            logger.info(f"Workflow execution completed for session {session_id}")
            
            return {
                "session_id": session_id,
                "status": "completed",
                "final_state": final_state,
                "pdf_path": final_state.get("pdf_path"),
                "execution_time": final_state.get("execution_time")
            }
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return {
                "session_id": session_id,
                "status": "failed",
                "error": str(e)
            }

    def _build_context_for_expert(self, state: ProjectAnalysisState) -> str:
        """
        为任务导向专家构建上下文信息
        
        Args:
            state: 当前项目状态
            
        Returns:
            str: 格式化的上下文字符串
        """
        context_parts = []
        
        # 添加用户需求
        task_description = state.get("task_description", "")
        if task_description:
            context_parts.append(f"## 用户需求\n{task_description}")
        
        # 添加结构化需求
        structured_requirements = state.get("structured_requirements", {})
        if structured_requirements:
            context_parts.append("## 结构化需求")
            for key, value in structured_requirements.items():
                if value:
                    context_parts.append(f"**{key}**: {value}")
        
        # 添加已完成的分析
        expert_analyses = state.get("expert_analyses", {})
        if expert_analyses:
            context_parts.append("## 已完成的专家分析")
            for expert_id, analysis in expert_analyses.items():
                if isinstance(analysis, dict):
                    analysis_content = analysis.get("analysis", str(analysis))
                else:
                    analysis_content = str(analysis)
                
                # 只显示前500字符，避免上下文过长
                preview = analysis_content[:500]
                if len(analysis_content) > 500:
                    preview += "..."
                    
                context_parts.append(f"### {expert_id}\n{preview}")
        
        # 添加项目状态信息
        context_parts.append(f"\n## 项目状态信息")
        context_parts.append(f"- 当前阶段: {state.get('current_phase', 'unknown')}")
        context_parts.append(f"- 已完成专家数: {len(expert_analyses)}")
        
        # 添加质量检查清单（如果有）
        quality_checklist = state.get("quality_checklist", {})
        if quality_checklist:
            context_parts.append("## 质量要求")
            for category, criteria in quality_checklist.items():
                if isinstance(criteria, list):
                    context_parts.append(f"**{category}**: {', '.join(criteria)}")
                else:
                    context_parts.append(f"**{category}**: {criteria}")
        
        return "\n\n".join(context_parts)
