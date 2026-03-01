"""
主工作流编排器

基于LangGraph实现的多智能体协作工作流
"""

#  v7.16: LangGraph Agent 升级版本（通过环境变量控制）
import os
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

import yaml
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command, Send
from loguru import logger

# 显式导入智能体类以触发 AgentFactory 注册
from ..agents import AgentFactory, ProjectDirectorAgent, RequirementsAnalystAgent
from ..agents.base import NullLLM
from ..agents.dynamic_project_director import detect_and_handle_challenges_node  #  v3.5
from ..agents.feasibility_analyst import FeasibilityAnalystAgent  #  V1.5可行性分析师
from ..agents.quality_monitor import QualityMonitor  #
from ..core.state import AnalysisStage, ProjectAnalysisState, StateManager
from ..core.types import AgentType, format_role_display_name
from ..interaction.interaction_nodes import (  # FinalReviewNode,  # 已移除：客户需求中没有最终审核阶段; AnalysisReviewNode,  # ️ v2.2: 已废弃，质量审核已前置化
    CalibrationQuestionnaireNode,
    UserQuestionNode,
)
from ..interaction.nodes.manual_review import ManualReviewNode  #  人工审核节点

#  v7.87: 三步递进式问卷节点
from ..interaction.nodes.progressive_questionnaire import (
    ProgressiveQuestionnaireNode,
    progressive_step1_core_task_node,
    progressive_step2_radar_node,
    progressive_step3_gap_filling_node,
)
from ..interaction.nodes.quality_preflight import QualityPreflightNode  #

#  v7.135: 问卷汇总节点（需求重构）
from ..interaction.nodes.questionnaire_summary import questionnaire_summary_node

#  统一审核节点（合并角色选择和任务分派审核）
from ..interaction.role_task_unified_review import role_task_unified_review_node

#  v7.502 P1优化: 智能上下文压缩器
from .context_compressor import create_context_compressor

# from ..interaction.role_selection_review import role_selection_review_node  # 已废弃
# from ..interaction.task_assignment_review import task_assignment_review_node  # 已废弃
from ..interaction.second_batch_strategy_review import SecondBatchStrategyReviewNode
from ..report.pdf_generator import PDFGeneratorAgent
from ..report.result_aggregator import ResultAggregatorAgent
from ..workflow.nodes.search_query_generator_node import search_query_generator_node  #  v7.109

USE_V716_AGENTS = os.getenv("USE_V716_AGENTS", "false").lower() == "true"
USE_V717_REQUIREMENTS_ANALYST = os.getenv("USE_V717_REQUIREMENTS_ANALYST", "false").lower() == "true"
USE_V718_QUESTIONNAIRE_AGENT = os.getenv("USE_V718_QUESTIONNAIRE_AGENT", "false").lower() == "true"
#  v7.87: 三步递进式问卷（默认启用）
USE_PROGRESSIVE_QUESTIONNAIRE = os.getenv("USE_PROGRESSIVE_QUESTIONNAIRE", "true").lower() == "true"
USE_MULTI_ROUND_QUESTIONNAIRE = os.getenv("USE_MULTI_ROUND_QUESTIONNAIRE", "false").lower() == "true"
if USE_V716_AGENTS:
    # from ..agents.analysis_review_agent import AnalysisReviewAgent, AnalysisReviewNodeCompat  # ️ v2.2: 已废弃
    from ..agents.challenge_detection_agent import ChallengeDetectionAgent, detect_and_handle_challenges_v2
    from ..agents.quality_preflight_agent import QualityPreflightAgent, QualityPreflightNodeCompat
    from ..agents.questionnaire_agent import LLMQuestionGeneratorCompat, QuestionnaireAgent
    from ..agents.result_aggregator_agent import ResultAggregatorAgentCompat, ResultAggregatorAgentV2

    logger.info(" [v7.16] 启用 LangGraph Agent 升级版本")
if USE_V717_REQUIREMENTS_ANALYST:
    from ..agents.requirements_analyst_agent import RequirementsAnalystAgentV2

    logger.info(" [v7.17] 启用需求分析师 StateGraph Agent")
if USE_V718_QUESTIONNAIRE_AGENT:
    from ..agents.questionnaire_agent import QuestionnaireAgent

    logger.info(" [v7.18] 启用问卷生成 StateGraph Agent")
from ..security import ReportGuardNode  #  内容安全与领域过滤

#  v7.3 统一输入验证节点（合并 input_guard 和 domain_validator）
from ..security.unified_input_validator_node import InputRejectedNode, UnifiedInputValidatorNode

# 动态本体论注入工具
from ..utils.ontology_loader import OntologyLoader

# LT-1: Mixin classes split from this file
from .nodes.security_nodes import SecurityNodesMixin
from .nodes.requirements_nodes import RequirementsNodesMixin
from .nodes.planning_nodes import PlanningNodesMixin
from .nodes.execution_nodes import ExecutionNodesMixin
from .nodes.aggregation_nodes import AggregationNodesMixin


class MainWorkflow(
    SecurityNodesMixin,
    RequirementsNodesMixin,
    PlanningNodesMixin,
    ExecutionNodesMixin,
    AggregationNodesMixin,
):
    """主工作流编排器"""

    def __init__(
        self,
        llm_model: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        checkpointer: Optional[BaseCheckpointSaver[str]] = None,
    ):
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

        #  支持外部传入 AsyncSqliteSaver（默认回退到同步版）
        self._sqlite_conn: Optional[sqlite3.Connection] = None
        if checkpointer is not None:
            self.checkpointer = checkpointer
            logger.info(" 使用外部提供的检查点存储 (AsyncSqliteSaver/自定义)")
        else:
            #  P1修复: 使用SqliteSaver替代MemorySaver，实现持久化存储
            # 解决服务器重启后工作流状态丢失导致76%进度停滞问题
            db_path = Path("./data/checkpoints/workflow.db")
            db_path.parent.mkdir(parents=True, exist_ok=True)

            self._sqlite_conn = sqlite3.connect(str(db_path), check_same_thread=False, isolation_level=None)  # 自动提交模式
            self.checkpointer = SqliteSaver(self._sqlite_conn)
            logger.info(f" 使用持久化检查点存储: {db_path}")

        # 初始化本体论加载器
        self.ontology_loader = OntologyLoader(
            "d:/11-20/langgraph-design/intelligent_project_analyzer/knowledge_base/ontology.yaml"
        )

        # 构建工作流图
        self.graph = self._build_workflow_graph()

        #  v7.108: 验证图像生成配置
        from intelligent_project_analyzer.settings import settings

        image_gen_enabled = settings.image_generation.enabled
        logger.info(f" [配置验证] 图像生成: {' 启用' if image_gen_enabled else '️ 禁用'}")

        if image_gen_enabled:
            logger.info(f"   模型: {settings.image_generation.model}")
            logger.info(f"   每报告最大图片: {settings.image_generation.max_images_per_report}")
            logger.info(f"   超时时间: {settings.image_generation.timeout}s")
        else:
            logger.warning("  ️ 图像生成已禁用，概念图不会生成（检查 .env 中的 IMAGE_GENERATION_ENABLED）")

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
        # 0.  安全节点（第一道防线）
        # ============================================================================
        #  v7.3 统一输入验证节点（合并 input_guard 和 domain_validator）
        workflow.add_node("unified_input_validator_initial", self._unified_input_validator_initial_node)  # 初始验证
        workflow.add_node("unified_input_validator_secondary", self._unified_input_validator_secondary_node)  # 二次验证
        workflow.add_node("input_rejected", self._input_rejected_node)  # 拒绝终止
        workflow.add_node("report_guard", self._report_guard_node)  # 报告审核

        # ============================================================================
        # 1. 前置流程节点（需求收集与确认）
        # ============================================================================
        workflow.add_node("requirements_analyst", self._requirements_analyst_node)
        workflow.add_node("feasibility_analyst", self._feasibility_analyst_node)  #  V1.5可行性分析师

        #  v7.87: 根据环境变量选择问卷类型
        if USE_PROGRESSIVE_QUESTIONNAIRE:
            # 三步递进式问卷（v7.80+）
            workflow.add_node("progressive_step1_core_task", self._progressive_step1_node)
            workflow.add_node("progressive_step2_radar", self._progressive_step2_node)
            workflow.add_node("progressive_step3_gap_filling", self._progressive_step3_node)
            #  v7.135: 需求洞察节点（需求重构）
            workflow.add_node("questionnaire_summary", self._questionnaire_summary_node)
            logger.info(" [v7.87] 启用三步递进式问卷（progressive_questionnaire）")
        else:
            # 旧版单轮问卷（向后兼容）
            workflow.add_node("calibration_questionnaire", self._calibration_questionnaire_node)
            logger.info("️ [v7.87] 使用旧版单轮问卷（calibration_questionnaire），建议设置 USE_PROGRESSIVE_QUESTIONNAIRE=true")

        #  v7.151: requirements_confirmation 已合并到 questionnaire_summary（需求洞察）

        # ============================================================================
        # 2. 角色选择与任务分派节点
        # ============================================================================
        workflow.add_node("project_director", self._project_director_node)
        #  v7.108 交付物ID生成器（概念图精准关联）
        workflow.add_node("deliverable_id_generator", self._deliverable_id_generator_node)
        #  v7.109 搜索查询生成器（为交付物生成搜索查询和概念图配置）
        workflow.add_node("search_query_generator", self._search_query_generator_node)
        #  统一审核节点（合并角色选择和任务分派）
        workflow.add_node("role_task_unified_review", self._role_task_unified_review_node)
        # ️ v7.280: role_selection_quality_review 已合并到 role_task_unified_review 的 TaskGenerationGuard
        # workflow.add_node("role_selection_quality_review", self._role_selection_quality_review_node)
        workflow.add_node("quality_preflight", self._quality_preflight_node)  #  质量预检（静默模式）

        # ============================================================================
        # 3.  动态批次执行节点（核心重构）
        # ============================================================================
        workflow.add_node("batch_executor", self._batch_executor_node)  # 批次执行器
        workflow.add_node("agent_executor", self._execute_agent_node)  # 智能体执行器
        workflow.add_node("batch_aggregator", self._intermediate_aggregator_node)  # 批次聚合器
        workflow.add_node("batch_router", self._batch_router_node)  # 批次路由器
        workflow.add_node("batch_strategy_review", self._batch_strategy_review_node)  # 批次策略审核
        workflow.add_node("detect_challenges", self._detect_challenges_node)  #  v3.5 挑战检测

        # ============================================================================
        # 4. 审核与结果生成节点
        # ============================================================================
        # workflow.add_node("analysis_review", self._analysis_review_node)  # ️ v2.2: 已废弃，被role_selection_quality_review替代
        workflow.add_node("manual_review", self._manual_review_node)  #  人工审核节点
        workflow.add_node("result_aggregator", self._result_aggregator_node)
        workflow.add_node("pdf_generator", self._pdf_generator_node)
        workflow.add_node("user_question", self._user_question_node)

        # ============================================================================
        # 边连接：前置流程
        # ============================================================================
        #  v7.3 统一输入验证流程
        workflow.add_edge(START, "unified_input_validator_initial")  # 第一道防线：初始验证
        # unified_input_validator_initial 使用 Command 路由到 requirements_analyst 或 input_rejected
        workflow.add_edge("input_rejected", END)  # 拒绝后终止

        workflow.add_edge("requirements_analyst", "feasibility_analyst")  #  V1.5可行性分析
        workflow.add_edge("feasibility_analyst", "unified_input_validator_secondary")  # 第二道防线：二次验证

        #  v7.87: 根据环境变量配置问卷流程
        if USE_PROGRESSIVE_QUESTIONNAIRE:
            # 三步递进式问卷流程
            workflow.add_edge("unified_input_validator_secondary", "progressive_step1_core_task")
            # progressive_step1 使用 Command 路由到 progressive_step2_radar 或 requirements_analyst
            # progressive_step2 使用 Command 路由到 progressive_step3_gap_filling 或 progressive_step1
            # progressive_step3 使用 Command 路由到 questionnaire_summary（v7.135: 需求重构）
            #  v7.151: questionnaire_summary 升级为需求洞察，使用 Command 动态路由
            # - 确认/微调 → project_director
            # - 重大修改 → requirements_analyst
            #  移除静态边: workflow.add_edge("questionnaire_summary", "requirements_confirmation")
            logger.info(" [v7.151] 配置需求洞察流程（合并需求洞察+需求确认）")
        elif USE_MULTI_ROUND_QUESTIONNAIRE:
            # 多轮迭代问卷已停用，回退到三步递进式
            logger.warning("️ [v7.87] 多轮迭代问卷已停用，回退到三步递进式问卷")
            workflow.add_edge("unified_input_validator_secondary", "progressive_step1_core_task")
            #  v7.151: 同样使用 Command 动态路由
        else:
            # 旧版单轮问卷
            workflow.add_edge("unified_input_validator_secondary", "calibration_questionnaire")
            #  calibration_questionnaire 使用 Command 完全动态路由（无静态 edge）

        workflow.add_edge("project_director", "deliverable_id_generator")  #  v7.108 生成交付物ID
        workflow.add_edge("deliverable_id_generator", "search_query_generator")  #  v7.109 搜索查询生成
        workflow.add_edge("search_query_generator", "role_task_unified_review")  #  统一审核
        #  v7.280: 质量控制前置化重构
        # - role_selection_quality_review 已合并到 role_task_unified_review 的 TaskGenerationGuard
        # - 统一审核直接连接到 quality_preflight（静默模式，不再阻塞用户）
        workflow.add_edge("role_task_unified_review", "quality_preflight")
        #  质量预检节点快速通过，静态边连接到批次执行
        workflow.add_edge("quality_preflight", "batch_executor")  #  预检后执行

        # ============================================================================
        #  动态批次执行流程（核心循环）
        # ============================================================================
        #  P0优化 (v7.502): 真并行批次执行
        # 旧架构: batch_executor → _create_batch_sends → [agent_executor (串行)] → batch_aggregator
        # 新架构: batch_executor [asyncio.gather并行] → batch_aggregator
        #
        # ️ 注意: agent_executor 节点保留用于向后兼容，但不再被主流程使用
        workflow.add_edge("batch_executor", "batch_aggregator")  #  直接并行执行后聚合

        #  保留旧节点以支持向后兼容（如有特殊路由需要）
        workflow.add_edge("agent_executor", "batch_aggregator")
        # workflow.add_edge("batch_aggregator", "detect_challenges")  #  暂时禁用：导致状态冲突

        #  v3.5: 挑战检测移至 result_aggregator 之前
        # batch_aggregator → batch_router → analysis_review → detect_challenges → result_aggregator
        # workflow.add_conditional_edges(
        #     "detect_challenges",
        #     self._route_after_challenge_detection,
        #     {
        #         "revisit_requirements": "requirements_analyst",  # 反馈循环
        #         "continue_workflow": "batch_router"  # 继续正常流程
        #     }
        # )

        #  batch_aggregator → batch_router (条件边：检查审核状态)
        workflow.add_conditional_edges(
            "batch_aggregator",
            self._route_from_batch_aggregator,
            ["batch_router", END],  #  N1修复：移除detect_challenges，避免重复调用result_aggregator
        )

        # 批次路由器根据 current_batch 和 total_batches 决定：
        # - 如果还有下一批次 → batch_strategy_review（审核后继续）
        # - 如果所有批次完成 → detect_challenges → result_aggregator（ v2.2: 跳过analysis_review）
        # 路由逻辑在 _batch_router_node 中通过 Command 实现

        # 批次策略审核 → 批次执行器（形成循环）
        workflow.add_edge("batch_strategy_review", "batch_executor")
        # batch_strategy_review 使用 Command 路由，可以跳过审核直接到 batch_executor

        #  P0优化移除: 不再使用Send API，改为batch_executor内部并行
        # 旧代码:
        # workflow.add_conditional_edges(
        #     "batch_executor", self._create_batch_sends, ["agent_executor"]
        # )
        #  新代码: 已在上方改为 workflow.add_edge("batch_executor", "batch_aggregator")

        # ============================================================================
        # 审核与结果生成流程
        # ============================================================================
        # ️ v2.2: analysis_review 已废弃，质量审核已前移到 role_selection_quality_review
        # 新流程: batch_router → detect_challenges → result_aggregator → pdf_generator

        #  v3.5: 挑战检测在所有批次完成后、结果聚合前执行
        workflow.add_conditional_edges(
            "detect_challenges",
            self._route_after_challenge_detection,
            {
                "revisit_requirements": "requirements_analyst",  # 反馈循环
                "manual_review": "manual_review",  #  人工审核（>3个must_fix）
                "continue_workflow": "result_aggregator",  # 继续到结果聚合
            },
        )

        #  人工审核节点：manual_review 使用 Command 动态路由到：
        # - batch_executor（重新执行特定专家）
        # - detect_challenges（继续挑战检测）
        # - END（终止流程）

        workflow.add_edge("result_aggregator", "report_guard")  #  报告审核
        workflow.add_edge("report_guard", "pdf_generator")  #  审核后生成PDF

        workflow.add_conditional_edges("pdf_generator", self._route_after_pdf_generator, ["user_question", END])

        workflow.add_conditional_edges(
            "user_question", self._route_after_user_question, ["project_director", "result_aggregator"]
        )

        # ============================================================================
        # 编译图
        # ============================================================================
        logger.info(" Workflow graph built with dynamic batch execution support")
        logger.info("   Nodes: batch_executor, agent_executor, batch_aggregator, batch_router, batch_strategy_review")
        logger.info("   Supports: 1-N batches with dependency-based execution")

        return workflow.compile(checkpointer=self.checkpointer, store=self.store)
