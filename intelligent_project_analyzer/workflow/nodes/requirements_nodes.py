# -*- coding: utf-8 -*-
"""
LT-1 需求节点 Mixin — 需求分析师、可行性、问卷流程

自动由 _lt1_split_workflow.py 生成 — 勿手动修改。
通过 Mixin 继承为 MainWorkflow 提供节点方法；完整 `self` 上下文由 MainWorkflow.__init__ 保证。
"""
# ruff: noqa (generated file)
# type: ignore
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
from ...agents import AgentFactory, ProjectDirectorAgent, RequirementsAnalystAgent
from ...agents.base import NullLLM
from ...agents.dynamic_project_director import detect_and_handle_challenges_node  # v3.5
from ...agents.feasibility_analyst import FeasibilityAnalystAgent  # V1.5可行性分析师
from ...agents.quality_monitor import QualityMonitor
from ...agents.requirements_analyst_agent import RequirementsAnalystAgentV2  # v7.17 StateGraph Agent

#  从 feature_flags 统一导入，消除与 main_workflow.py 默认值分裂
# USE_V717_REQUIREMENTS_ANALYST 已冻结为 True，直接使用 V2 路径
from ...core.state import AnalysisStage, ProjectAnalysisState, StateManager
from ...core.types import AgentType, format_role_display_name
from ...interaction.interaction_nodes import (  # FinalReviewNode,  # 已移除：客户需求中没有最终审核阶段; AnalysisReviewNode,  # ️ v2.2: 已废弃，质量审核已前置化
    CalibrationQuestionnaireNode,
    UserQuestionNode,
)
from ...interaction.nodes.manual_review import ManualReviewNode  # 人工审核节点
from ...interaction.nodes.output_intent_detection import output_intent_detection_node

#  v7.87: 三步递进式问卷节点
from ...interaction.nodes.progressive_questionnaire import (
    ProgressiveQuestionnaireNode,
    progressive_step1_core_task_node,
    progressive_step2_radar_node,
    progressive_step3_gap_filling_node,
)
from ...interaction.nodes.quality_preflight import QualityPreflightNode

#  v7.135: 问卷汇总节点（需求重构）
from ...interaction.nodes.questionnaire_summary import questionnaire_summary_node

#  统一审核节点（合并角色选择和任务分派审核）
from ...interaction.role_task_unified_review import role_task_unified_review_node

# from ..interaction.role_selection_review import role_selection_review_node  # 已废弃
# from ..interaction.task_assignment_review import task_assignment_review_node  # 已废弃
from ...interaction.second_batch_strategy_review import SecondBatchStrategyReviewNode
from ...report.pdf_generator import PDFGeneratorAgent
from ...report.result_aggregator import ResultAggregatorAgent

#  v7.87: 三步递进式问卷（默认启用）
from ...security import ReportGuardNode  # 内容安全与领域过滤

#  v7.3 统一输入验证节点（合并 input_guard 和 domain_validator）
from ...security.unified_input_validator_node import InputRejectedNode, UnifiedInputValidatorNode

# Step 0 fix: detect_design_modes（之前从未被调用，导致 projection_dispatcher 的 when_modes 始终为空列表）
from ...services.mode_detector import detect_design_modes

# v8.2: 动态步骤追踪装饰器
from ...utils.node_tracker import track_active_step

# 动态本体论注入工具
from ...utils.ontology_loader import OntologyLoader
from ...workflow.nodes.search_query_generator_node import search_query_generator_node  # v7.109

#  v7.502 P1优化: 智能上下文压缩器
from ..context_compressor import create_context_compressor

# ST-3: 节点 Fallback 守卫装饰器
from ..node_guard import node_guard


def _build_motivation_routing_profile(
    project_motivation: Dict[str, Any],
    designer_behavioral_motivation: Dict[str, Any],
    detected_modes: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    合并 project_motivation + designer_behavioral_motivation 为统一路由画像。

    这是「双动机驱动」缺失的组装者 — 将两个独立动机信号合并为
    motivation_routing_profile，供前半链路节点（progressive_questionnaire）
    的 Self-Skip 决策和前端双动机卡片展示消费。

    Returns:
        dict with keys:
        - primary_mode: 主要动机类型（如 "commercial", "wellness"）
        - confidence: 综合置信度
        - d_type: 设计师行为动机类型（D1-D6）
        - skip_candidates: 可跳过的步骤列表
        - routing_strategy: 路由策略（"full_flow" / "skip_gap_filling" / "skip_radar"）
    """
    pm = project_motivation or {}
    dbm = designer_behavioral_motivation or {}
    pm_primary = pm.get("primary", "unknown")
    pm_confidence = float(pm.get("confidence", 0.0))
    d_type = dbm.get("primary", dbm.get("type", "D1"))
    d_confidence = float(dbm.get("confidence", 0.0))

    # 综合置信度（项目动机权重 0.6，行为动机权重 0.4）
    combined_confidence = pm_confidence * 0.6 + d_confidence * 0.4

    skip_candidates: List[str] = []
    routing_strategy = "full_flow"

    HIGH_CONF = 0.75
    # 规则1: 高置信度 + 商业/展示类 → 信息充足，可跳过 gap_filling
    SKIP_GAP_MODES = {"commercial", "exhibition", "showcase", "portfolio", "competition"}
    if pm_confidence >= HIGH_CONF and pm_primary in SKIP_GAP_MODES:
        skip_candidates.append("gap_filling")
        routing_strategy = "skip_gap_filling"

    # 规则2: D3（纯展示偏好型）+ 高置信度 → 可跳过 radar
    if d_type == "D3" and d_confidence >= HIGH_CONF:
        skip_candidates.append("radar")
        routing_strategy = "skip_all_optional" if routing_strategy == "skip_gap_filling" else "skip_radar"

    return {
        "primary_mode": pm_primary,
        "confidence": round(combined_confidence, 3),
        "d_type": d_type,
        "d_confidence": round(d_confidence, 3),
        "pm_confidence": round(pm_confidence, 3),
        "detected_modes_count": len(detected_modes),
        "skip_candidates": skip_candidates,
        "routing_strategy": routing_strategy,
    }


class RequirementsNodesMixin:
    """
    LT-1 需求节点 Mixin — 需求分析师、可行性、问卷流程

    Mixin for MainWorkflow. All methods receive full `self` access because
    MainWorkflow inherits from this class along with other Mixin classes.
    Do NOT instantiate this class directly.
    """

    @track_active_step("requirements_analyst")
    def _requirements_analyst_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        需求分析师节点

        注意: 只返回需要更新的字段,不返回完整状态
        这样可以避免并发更新冲突

        v7.17: 支持 StateGraph Agent 模式（通过环境变量控制）
        """
        try:
            logger.info("Executing requirements analyst node")

            #  调试：检查进入时的标志状态
            logger.info(
                f" [DEBUG] requirements_analyst 进入时 calibration_processed: {state.get('calibration_processed')}"
            )
            logger.info(f" [DEBUG] requirements_analyst 进入时 calibration_skipped: {state.get('calibration_skipped')}")
            logger.info(f" [DEBUG] requirements_analyst 进入时 state 所有键: {list(state.keys())}")

            #  深度调试：检查 state 是否包含这些键
            if "calibration_processed" in state:
                logger.info(f" [DEBUG] 'calibration_processed' 键存在，值={state['calibration_processed']}")
            else:
                logger.info(" [DEBUG] 'calibration_processed' 键不存在")

            # v7.17: StateGraph Agent 模式（已稳定，不再需要 flag 切换）
            logger.info(" [v7.17] 使用 StateGraph Agent 执行需求分析")
            agent = RequirementsAnalystAgentV2(llm_model=self.llm_model, config=self.config)
            result = agent.execute(
                user_input=state.get("user_input", ""), session_id=state.get("session_id", "unknown")
            )

            # 记录 StateGraph 执行元数据
            if result.metadata:
                logger.info(f" [v7.17] StateGraph 执行完成:")
                logger.info(f"   - 分析模式: {result.metadata.get('analysis_mode')}")
                logger.info(f"   - 节点路径: {result.metadata.get('node_path')}")
                logger.info(f"   - 总耗时: {result.metadata.get('total_elapsed_ms')}ms")

            #  提取项目类型（从 structured_data 中）
            project_type = result.structured_data.get("project_type") if result.structured_data else None

            #  v7.0: 从 primary_deliverables 中提取交付物元数据和责任者映射
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

                    #  修复问题1: 标记为预测值，后续由 project_director 校正
                    # 填充 deliverable_owner_map（此时是需求分析师的预测）
                    if primary_owner:
                        deliverable_owner_map[deliverable_id] = primary_owner

                    # 填充 deliverable_metadata（包含完整信息）
                    deliverable_metadata[deliverable_id] = {
                        "name": deliverable.get("description", deliverable_id),
                        "type": deliverable.get("type", "unknown"),
                        "priority": deliverable.get("priority", "MUST_HAVE"),
                        "owner": primary_owner,  # 预测值，待校正
                        "owner_predicted": True,  #  标记为预测值
                        "supporters": supporters,
                        "acceptance_criteria": deliverable.get("acceptance_criteria", []),
                        "format_requirements": deliverable.get("format_requirements", {}),
                        "source_requirement": deliverable.get("source_requirement", ""),
                    }

                if deliverable_owner_map:
                    logger.info(f" [v7.0] 提取到 {len(deliverable_owner_map)} 个交付物责任者映射（预测值）: {deliverable_owner_map}")

            # 只返回需要更新的字段
            #  修复: 使用 agent_type.value 保持一致性
            #  修复: 保留重要的流程控制标志，避免循环
            update_dict = {
                "current_stage": AnalysisStage.REQUIREMENT_COLLECTION.value,
                "structured_requirements": result.structured_data,
                "project_type": project_type,  #  添加项目类型字段
                "deliverable_owner_map": deliverable_owner_map,  #  v7.0: 交付物责任者映射
                "deliverable_metadata": deliverable_metadata,  #  v7.0: 交付物完整元数据
                "agent_results": {AgentType.REQUIREMENTS_ANALYST.value: result.to_dict()},
                "updated_at": datetime.now().isoformat(),
            }

            # ── Step 0 fix: 调用 detect_design_modes，修复 projection_dispatcher.when_modes 死路 ──
            user_input_str = state.get("user_input", "")
            sd = result.structured_data or {}
            try:
                detected_modes = detect_design_modes(user_input_str, sd)
            except Exception as _mode_err:
                logger.warning(f"[motivation] detect_design_modes 失败，跳过: {_mode_err}")
                detected_modes = []
            if detected_modes:
                update_dict["detected_design_modes"] = detected_modes

            # ── 动机字段写入（来自 Phase1 LLM 输出，置信度门控 >= 0.3）──
            project_motivation_raw = sd.get("motivation_preliminary")
            designer_behavioral_raw = sd.get("designer_behavioral_motivation")

            if isinstance(project_motivation_raw, dict) and project_motivation_raw.get("confidence", 0) >= 0.3:
                update_dict["project_motivation"] = project_motivation_raw

            if isinstance(designer_behavioral_raw, dict) and designer_behavioral_raw.get("confidence", 0) >= 0.3:
                update_dict["designer_behavioral_motivation"] = designer_behavioral_raw

            # motivation_trace：记录本次推断摘要，便于调试
            trace_entries: List[str] = []
            if detected_modes:
                top_mode = detected_modes[0].get("mode", "?")
                trace_entries.append(f"[Phase1] modes={len(detected_modes)} top={top_mode}")
            if update_dict.get("project_motivation"):
                pm = update_dict["project_motivation"]
                trace_entries.append(
                    f"[Phase1] project_motivation={pm.get('primary','?')} conf={pm.get('confidence',0):.2f}"
                )
            if update_dict.get("designer_behavioral_motivation"):
                dbm = update_dict["designer_behavioral_motivation"]
                trace_entries.append(f"[Phase1] D={dbm.get('primary','?')} conf={dbm.get('confidence',0):.2f}")
            if trace_entries:
                update_dict["motivation_trace"] = trace_entries

            # ── 双动机统一画像组装（motivation_routing_profile）──────────────────────
            # 解决「中间缺少组装者」断链：合并两个动机信号为前半链路路由决策所需的统一画像
            _pm = update_dict.get("project_motivation") or state.get("project_motivation") or {}
            _dbm = (
                update_dict.get("designer_behavioral_motivation") or state.get("designer_behavioral_motivation") or {}
            )
            if _pm or _dbm:
                update_dict["motivation_routing_profile"] = _build_motivation_routing_profile(_pm, _dbm, detected_modes)
                logger.info(
                    f"[Phase1] motivation_routing_profile built: "
                    f"strategy={update_dict['motivation_routing_profile']['routing_strategy']} "
                    f"skip_candidates={update_dict['motivation_routing_profile']['skip_candidates']}"
                )

            #  关键修复: 从完整状态中提取并保留流程控制标志
            # 注意: Command.update 的字段在目标节点执行时不可见,
            # 所以这里需要从 agent_results 中获取原始 state 的标志值
            # 但实际上,我们应该让这些标志"穿透"整个分析过程
            full_state = dict(state)  # 获取完整状态副本

            # ️ 增强修复：检查标志 OR 检查答案是否存在
            # LT-3: calibration_answers 已删除，改从 questionnaire_responses["answers"] 检查
            has_processed = ("calibration_processed" in full_state and full_state["calibration_processed"]) or bool(
                (full_state.get("questionnaire_responses") or {}).get("answers")
            )

            if has_processed:
                update_dict["calibration_processed"] = True
                logger.info(" [DEBUG] 保留/恢复 calibration_processed=True 标志")

            if "calibration_skipped" in full_state and full_state["calibration_skipped"]:
                update_dict["calibration_skipped"] = True
                logger.info(" [DEBUG] 保留 calibration_skipped=True 标志")
            #  关键修复：保留 modification_confirmation_round 轮次计数
            if "modification_confirmation_round" in full_state:
                update_dict["modification_confirmation_round"] = full_state["modification_confirmation_round"]
                logger.info(
                    f" [DEBUG] 保留 modification_confirmation_round={full_state['modification_confirmation_round']} 标志"
                )
            #  关键修复：保留 skip_unified_review 标志
            if "skip_unified_review" in full_state and full_state["skip_unified_review"]:
                update_dict["skip_unified_review"] = True
                logger.info(" [DEBUG] 保留 skip_unified_review=True 标志")

            logger.info(f" [DEBUG] requirements_analyst 返回的字段: {list(update_dict.keys())}")
            return update_dict

        except Exception as e:
            logger.error(f"Requirements analyst node failed: {e}")
            import traceback

            traceback.print_exc()
            #  显式失败状态：阻止工作流静默降级到 Step 1
            return {
                "requirements_analysis_status": "failed",
                "requirements_analysis_error": f"{type(e).__name__}: {e}",
                "current_stage": AnalysisStage.REQUIREMENT_COLLECTION.value,
                "updated_at": datetime.now().isoformat(),
            }

    def _route_after_requirements_analyst(self, state: ProjectAnalysisState) -> str:
        """
        需求分析后路由判断。
        失败时终止主链路（不降级为 Step 1 伪成功）；成功时继续可行性分析。
        """
        if state.get("requirements_analysis_status") == "failed":
            error = state.get("requirements_analysis_error", "unknown")
            logger.error(f"[route] requirements_analyst 失败，终止主链路 | error={error}")
            return END
        return "output_intent_detection"

    @node_guard(fallback={"errors": [], "output_intent_skipped": True})
    def _output_intent_detection_node(self, state: ProjectAnalysisState) -> Command:
        """Step 0: 输出意图确认（主闸门）。"""
        logger.info(" [v11] Executing output intent detection node")
        return output_intent_detection_node(state, self.store)

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
            feasibility_agent = FeasibilityAnalystAgent(llm_model=self.llm_model, config=self.config)

            # 验证输入：V1的structured_requirements必须存在
            if not state.get("structured_requirements"):
                logger.warning("️ V1.5跳过：structured_requirements不存在")
                return {"updated_at": datetime.now().isoformat()}

            # 执行可行性分析
            result = feasibility_agent.execute(state, {}, self.store)

            # 存储分析结果到state（仅后台存储，不展示到前端）
            update_dict = {
                "feasibility_assessment": result.structured_data,  # 完整的可行性分析结果
                "updated_at": datetime.now().isoformat(),
            }

            # 日志记录关键发现（用于调试和监控）
            if result.structured_data:
                feasibility = result.structured_data.get("feasibility_assessment", {})
                overall = feasibility.get("overall_feasibility", "unknown")
                conflicts = result.structured_data.get("conflict_detection", {})

                logger.info(f" V1.5可行性分析完成: overall_feasibility={overall}")

                # 记录冲突检测结果
                budget_conflicts = conflicts.get("budget_conflicts", [])
                if budget_conflicts and budget_conflicts[0].get("detected"):
                    severity = budget_conflicts[0].get("severity", "unknown")
                    logger.info(f"️ 预算冲突检测: severity={severity}")

                # 记录优先级矩阵
                priority_matrix = result.structured_data.get("priority_matrix", [])
                if priority_matrix:
                    top_req = priority_matrix[0]
                    logger.info(f" 最高优先级需求: {top_req.get('requirement')} (score={top_req.get('priority_score')})")

            return update_dict

        except Exception as e:
            logger.error(f"V1.5 Feasibility analyst node failed: {e}")
            import traceback

            traceback.print_exc()
            return {"error": str(e), "updated_at": datetime.now().isoformat()}

    @node_guard(fallback={"errors": [], "calibration_skipped": True})
    def _calibration_questionnaire_node(self, state: ProjectAnalysisState) -> Command:
        """
        战略校准问卷节点（旧版单轮问卷）

        根据需求分析师文档v1.0的要求：
        在完成需求分析后，必须生成"战略校准问卷"并等待用户回答。

        注意: 不要捕获Interrupt异常!
        Interrupt是LangGraph的正常控制流,必须让它传播到框架层
        @node_guard 会正确重新抛出 GraphInterrupt，保证交互中断语义不变。
        """
        logger.info("Executing calibration questionnaire node (legacy single-round)")
        return CalibrationQuestionnaireNode.execute(state, self.store)

    #  v7.87: 三步递进式问卷节点函数

    #  v7.87: 三步递进式问卷节点函数
    @node_guard(fallback={"errors": [], "progressive_step1_skipped": True})
    def _progressive_step1_node(self, state: ProjectAnalysisState) -> Command:
        """Step 1: 核心任务拆解与确认"""
        logger.info(" [v7.87 Step 1] Executing progressive questionnaire - Core Task Decomposition")
        return progressive_step1_core_task_node(state, self.store)

    @node_guard(fallback={"errors": [], "progressive_step2_skipped": True})
    def _progressive_step2_node(self, state: ProjectAnalysisState) -> Command:
        """Step 2: 雷达图维度选择"""
        logger.info(" [v7.87 Step 2] Executing progressive questionnaire - Radar Dimension Selection")
        return progressive_step2_radar_node(state, self.store)

    @node_guard(fallback={"errors": [], "progressive_step3_skipped": True})
    def _progressive_step3_node(self, state: ProjectAnalysisState) -> Command:
        """Step 3: 差距填补追问"""
        logger.info(" [v7.87 Step 3] Executing progressive questionnaire - Gap Filling")
        return progressive_step3_gap_filling_node(state, self.store)

    @node_guard(fallback={"errors": [], "questionnaire_summary_skipped": True})
    def _questionnaire_summary_node(self, state: ProjectAnalysisState) -> Command:
        """
         v7.135: 需求洞察节点（需求重构）
         v7.151: 升级为"需求洞察"节点，合并了原 requirements_confirmation 功能
         v7.152: 修复返回类型声明，正确返回 Command 对象

        在三步问卷完成后，智能重构生成结构化需求文档，而非机械回顾问卷。
        用户可直接在此节点确认/微调需求。

        Returns:
            Command 对象，指向 project_director 或 requirements_analyst
        """
        logger.info(" [v7.152] Executing questionnaire summary - Requirements Insight (Command routing)")
        return questionnaire_summary_node(state, self.store)
