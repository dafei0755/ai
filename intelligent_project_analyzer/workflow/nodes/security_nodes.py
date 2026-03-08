# -*- coding: utf-8 -*-
"""
LT-1 安全节点 Mixin — 输入验证、拒绝、报告审核

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
from ...core.state import AnalysisStage, ProjectAnalysisState, StateManager
from ...core.types import AgentType, format_role_display_name
from ...interaction.interaction_nodes import (  # FinalReviewNode,  # 已移除：客户需求中没有最终审核阶段; AnalysisReviewNode,  # ️ v2.2: 已废弃，质量审核已前置化
    CalibrationQuestionnaireNode,
    UserQuestionNode,
)
from ...interaction.nodes.manual_review import ManualReviewNode  # 人工审核节点

# 2026-03-06: progressive_step1_core_task_node 已删除（Step1 废弃）
from ...interaction.nodes.progressive_questionnaire import (
    ProgressiveQuestionnaireNode,
    progressive_step2_radar_node,
    progressive_step3_gap_filling_node,
)
from ...interaction.nodes.quality_preflight import QualityPreflightNode
from ...config.feature_flags import ENABLE_REQUIREMENTS_FAST_PATH

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

# 动态本体论注入工具
from ...utils.ontology_loader import OntologyLoader
from ...workflow.nodes.search_query_generator_node import search_query_generator_node  # v7.109

#  v7.502 P1优化: 智能上下文压缩器
from ..context_compressor import create_context_compressor


class SecurityNodesMixin:
    """
    LT-1 安全节点 Mixin — 输入验证、拒绝、报告审核

    Mixin for MainWorkflow. All methods receive full `self` access because
    MainWorkflow inherits from this class along with other Mixin classes.
    Do NOT instantiate this class directly.
    """

    def _unified_input_validator_initial_node(self, state: ProjectAnalysisState) -> Command:
        """
        统一输入验证 - 阶段1: 初始验证

        执行内容安全检测、领域分类检测、任务复杂度评估
        """
        try:
            logger.info("Executing unified input validator - initial validation")
            result = UnifiedInputValidatorNode.execute_initial_validation(
                state, store=self.store, llm_model=self.llm_model
            )

            if not isinstance(result, Command):
                logger.error("UnifiedInputValidatorNode.execute_initial_validation did not return Command object")
                return Command(update={"rejection_reason": "system_error"}, goto="input_rejected")

            # 提取状态更新
            update_payload = dict(result.update or {})
            update_payload["detail"] = "检测输入内容安全性与领域适配性"

            # 读取复杂度评估结果
            suggested_workflow = update_payload.get("suggested_workflow", "full_analysis")
            task_complexity = update_payload.get("task_complexity", "complex")

            # 如果原本要去 input_rejected，保持不变
            if result.goto == "input_rejected":
                return Command(update=update_payload, goto="input_rejected")

            #  统一路由：所有任务都走完整流程
            #  v7.1 修复：不再自动跳过问卷，让用户决定
            # 原逻辑：medium 复杂度跳过问卷，但低置信度的默认 medium 恰恰需要问卷补充信息
            # 新逻辑：所有任务都显示问卷，用户可以选择跳过
            complexity_confidence = update_payload.get("complexity_confidence", 0.5)
            logger.info(f" {task_complexity} 任务检测（置信度: {complexity_confidence:.2f}），使用完整流程")
            logger.info(f"   suggested_workflow: {suggested_workflow}")
            # skip_calibration 默认为 False，由校准问卷节点自身逻辑或用户选择决定

            return Command(update=update_payload, goto="requirements_analyst")

        except Interrupt:
            #  修复：Interrupt 是正常的交互中断，不应该捕获，应该向上传播
            logger.info("Input guard node raised an interrupt (user interaction required)")
            raise
        except Exception as e:
            logger.error(f"Error in input guard node: {e}")
            import traceback

            traceback.print_exc()
            # 出错时保守拒绝
            return Command(
                update={"rejection_reason": "system_error", "rejection_message": "系统错误，请稍后重试。", "detail": "安全检测异常"},
                goto="input_rejected",
            )

    def _input_rejected_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """输入拒绝节点包装"""
        try:
            logger.info("Executing input rejected node")
            return InputRejectedNode.execute(state, store=self.store)
        except Exception as e:
            logger.error(f"Error in input rejected node: {e}")
            return {"final_status": "rejected", "rejection_message": "系统错误，流程终止。"}

    def _unified_input_validator_secondary_node(self, state: ProjectAnalysisState) -> Union[Dict[str, Any], Command]:
        """
        统一输入验证 - 阶段2: 二次验证

        在需求分析后，重新验证领域一致性，检测领域漂移
        """
        from langgraph.types import Interrupt

        try:
            logger.info("Executing unified input validator - secondary validation")
            result = UnifiedInputValidatorNode.execute_secondary_validation(
                state, store=self.store, llm_model=self.llm_model
            )

            #  正常情况：返回字典（由静态 edge 路由到 calibration_questionnaire）
            #  拒绝情况：返回 Command(goto="input_rejected")（终止工作流）
            #  调整情况：返回 Command(goto="requirements_analyst")（重新分析）
            if isinstance(result, Command):
                logger.warning("️ Secondary validation returned Command (rejection or re-analysis)")
                return result

            #  保留 skip_unified_review 标志
            if state.get("skip_unified_review"):
                result["skip_unified_review"] = True
                logger.debug(" [DEBUG] secondary_validation 保留 skip_unified_review=True")

            # 最短路径：二次验证后直接进入项目总监，跳过二级需求步骤
            if ENABLE_REQUIREMENTS_FAST_PATH:
                fast_path_ok, fast_path_reasons = self._can_apply_requirements_fast_path(state)
                if fast_path_ok:
                    logger.warning(
                        " [FAST_PATH] ENABLE_REQUIREMENTS_FAST_PATH=true 且最小保障通过，"
                        "跳过 progressive_step3/progressive_step2/questionnaire_summary，直达 project_director"
                    )
                    result["requirements_fast_path"] = True
                    result["questionnaire_summary_skipped"] = True
                    result["progressive_step3_skipped"] = True
                    result["progressive_step2_skipped"] = True
                    result["requirements_fast_path_guard"] = {"passed": True, "reasons": fast_path_reasons}
                    result["detail"] = "二次验证通过（fast path）"
                    return Command(update=result, goto="project_director")

                logger.warning(
                    " [FAST_PATH] 已启用但最小保障未通过，回退默认链路继续补全 | reasons=%s"
                    % fast_path_reasons
                )
                result["requirements_fast_path"] = False
                result["requirements_fast_path_guard"] = {"passed": False, "reasons": fast_path_reasons}

            # 添加 detail 字段
            result["detail"] = "二次验证领域适配性"

            logger.debug(" [DEBUG] Secondary validation completed, proceeding via workflow routing")
            return result

        except Interrupt:
            #  修复：Interrupt 是正常的交互中断，不应该捕获，应该向上传播
            logger.info("Secondary validation raised an interrupt (user interaction required)")
            raise
        except Exception as e:
            logger.error(f"Error in secondary validation node: {e}")
            import traceback

            traceback.print_exc()
            # 出错时信任初始判断
            logger.warning("Secondary validation failed, trusting initial judgment")
            return {"secondary_validation_skipped": True, "secondary_validation_reason": "error_occurred"}

    def _can_apply_requirements_fast_path(self, state: ProjectAnalysisState) -> tuple[bool, list[str]]:
        """
        Fast Path 最小保障守卫：
        - 需求审阅门禁需通过（severity=pass）
        - 核心分析产物字段齐备（项目类型/空间分类/任务框架/结构化需求）
        - 关键方法字段存在（M18/M19/M22/M23/M24 的最小承载字段）
        """
        reasons: list[str] = []

        # 1) 审阅门禁要求 pass
        quality_gate = state.get("requirements_quality_gate") or {}
        severity = str((quality_gate or {}).get("severity") or "").lower()
        if severity != "pass":
            reasons.append(f"quality_gate_not_pass:{severity or 'missing'}")

        # 2) 核心结构化产物
        structured = state.get("structured_requirements") or {}
        if not isinstance(structured, dict):
            reasons.append("structured_requirements_missing")
            structured = {}

        if not state.get("project_type"):
            reasons.append("project_type_missing")
        if not state.get("space_classification"):
            reasons.append("space_classification_missing")
        if not state.get("task_framework"):
            reasons.append("task_framework_missing")

        # 3) 27方法最小保障（关键方法字段）
        stance = structured.get("stance_spectrum") if isinstance(structured.get("stance_spectrum"), dict) else {}
        handoff = (
            structured.get("expert_handoff_questions")
            if isinstance(structured.get("expert_handoff_questions"), dict)
            else {}
        )
        disruption = (
            structured.get("disruption_authorization")
            if isinstance(structured.get("disruption_authorization"), dict)
            else {}
        )

        if not structured.get("project_motivation_detail"):
            reasons.append("M18_missing_project_motivation_detail")
        if not structured.get("design_motivation_detail"):
            reasons.append("M19_missing_design_motivation_detail")
        if not stance.get("rationale"):
            reasons.append("M22_missing_stance_rationale")
        if not handoff.get("universal_disruption_challenge"):
            reasons.append("M23_missing_universal_disruption_challenge")
        if not disruption.get("disruption_rationale"):
            reasons.append("M24_missing_disruption_rationale")

        return (len(reasons) == 0, reasons)

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
