# -*- coding: utf-8 -*-
"""
LT-1 聚合节点 Mixin — 批次路由、挑战检测、结果聚合、输出生成

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

# v8.2: 动态步骤追踪装饰器
from ...utils.node_tracker import track_active_step

# 动态本体论注入工具
from ...utils.ontology_loader import OntologyLoader
from ...workflow.nodes.search_query_generator_node import search_query_generator_node  # v7.109

#  v7.502 P1优化: 智能上下文压缩器
from ..context_compressor import create_context_compressor


class AggregationNodesMixin:
    """
    LT-1 聚合节点 Mixin — 批次路由、挑战检测、结果聚合、输出生成

    Mixin for MainWorkflow. All methods receive full `self` access because
    MainWorkflow inherits from this class along with other Mixin classes.
    Do NOT instantiate this class directly.
    """

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

         P1修复（2025-11-25）：
        - 等待当前批次所有agent完成后再执行聚合
        - 通过检查agent_results确保不会过早触发

         N2优化（2025-11-25）：
        - LangGraph Send API会在每个并行任务完成时触发此节点（预期行为）
        - 本节点检查所有任务是否完成，未完成时返回空字典等待
        - 这是LangGraph并行执行的标准"轮询模式"
        """
        try:
            agent_results = state.get("agent_results", {})
            batches = state.get("execution_batches", [])
            current_batch = state.get("current_batch", 1)
            total_batches = state.get("total_batches", len(batches))

            logger.info(f" 当前批次: {current_batch}/{total_batches}")

            if not batches:
                logger.warning("未找到 execution_batches，无法验证批次完成情况")
                # 降级到旧逻辑（保留兼容性）
                return self._intermediate_aggregator_node_legacy(state)

            # 获取当前批次的角色列表
            if current_batch < 1 or current_batch > len(batches):
                logger.error(f"当前批次编号 {current_batch} 超出范围")
                return {"error": f"Invalid batch number: {current_batch}"}

            current_batch_roles = batches[current_batch - 1]

            #  N2优化：快速检查是否所有agent已完成（减少无效日志）
            pending_agents = [role_id for role_id in current_batch_roles if role_id not in agent_results]
            if pending_agents:
                #  LangGraph并行模式：部分任务完成时会触发此节点，这是预期行为
                # 返回空字典，等待所有任务完成后再次调用

                #  P2优化：添加轮询计数器，优化日志级别
                poll_count_key = f"_aggregator_poll_count_batch_{current_batch}"
                poll_count = state.get(poll_count_key, 0) + 1

                # 只在第一次轮询时记录 info 级别日志，后续使用 debug 级别
                if poll_count == 1:
                    logger.info(
                        f" [Polling] 批次 {current_batch} 开始等待: {len(pending_agents)}/{len(current_batch_roles)} 未完成"
                    )
                else:
                    logger.debug(
                        f" [Polling #{poll_count}] 批次 {current_batch} 等待中: {len(pending_agents)}/{len(current_batch_roles)} 未完成"
                    )

                # 返回更新的轮询计数
                return {poll_count_key: poll_count}

            #  所有agent已完成，开始详细聚合
            #  P2优化：记录总轮询次数
            poll_count_key = f"_aggregator_poll_count_batch_{current_batch}"
            total_polls = state.get(poll_count_key, 0)
            if total_polls > 0:
                logger.info(f" [Aggregator] 批次 {current_batch}/{total_batches} 所有任务完成（经过 {total_polls} 次轮询），开始聚合")
            else:
                logger.info(f" [Aggregator] 批次 {current_batch}/{total_batches} 所有任务完成，开始聚合")

            # 检查完成情况
            completed_agents = []
            failed_agents = []

            for role_id in current_batch_roles:
                if role_id in agent_results:
                    result = agent_results[role_id]
                    confidence = result.get("confidence", 0)
                    has_error = "error" in result

                    #  v7.122: 工具使用率监控
                    protocol_execution = result.get("protocol_execution", {})
                    tools_used = protocol_execution.get("tools_used", [])

                    if len(tools_used) == 0:
                        logger.warning(f"️ [{role_id}] 未使用任何工具，质量存疑")
                        logger.warning(f"   原始 confidence: {confidence:.2%}")

                        # 强制降低置信度（按照 Expert Autonomy Protocol v4.2）
                        if confidence > 0.6:
                            original_confidence = confidence
                            confidence = 0.6
                            result["confidence"] = confidence
                            logger.warning(f"    置信度已降低: {original_confidence:.2%} → {confidence:.2%} (未使用工具)")
                    else:
                        logger.info(f" [{role_id}] 使用了 {len(tools_used)} 个工具调用")
                        logger.debug(f"   工具列表: {', '.join(tools_used[:3])}" + ("..." if len(tools_used) > 3 else ""))

                    if has_error:
                        failed_agents.append(role_id)
                        logger.warning(f"{role_id} completed with error: {result.get('error')}")
                    else:
                        completed_agents.append(role_id)
                        logger.info(f" {role_id} completed successfully (confidence: {confidence:.2%})")
                else:
                    failed_agents.append(role_id)
                    logger.warning(f"️ {role_id} not found in results")

            # 记录汇总信息
            logger.info(f"批次 {current_batch} 汇总: {len(completed_agents)}/{len(current_batch_roles)} 成功完成")
            if completed_agents:
                logger.info(f" 已完成: {', '.join(completed_agents)}")
            if failed_agents:
                logger.warning(f" 失败/缺失: {', '.join(failed_agents)}")

            # 准备依赖数据摘要
            dependency_summary = {
                "batch_number": current_batch,
                "batch_completed": len(completed_agents) == len(current_batch_roles),
                "completed_count": len(completed_agents),
                "total_count": len(current_batch_roles),
                "completed_agents": completed_agents,
                "failed_agents": failed_agents,
                "timestamp": datetime.now().isoformat(),
            }

            # 更新已完成批次列表
            completed_batches = state.get("completed_batches", [])
            if current_batch not in completed_batches:
                completed_batches_updated = completed_batches + [current_batch]
            else:
                completed_batches_updated = completed_batches

            logger.info(f" 批次 {current_batch} 聚合完成")
            logger.info(f" 已完成批次: {completed_batches_updated}")

            #  v7.271: 合并各专家的搜索引用到全局状态
            all_search_refs = []
            for role_id in current_batch_roles:
                if role_id in agent_results:
                    result = agent_results[role_id]
                    # 从 structured_output 中提取搜索引用
                    structured_output = result.get("structured_output", {})
                    if structured_output:
                        task_report = structured_output.get("task_execution_report", {})
                        deliverable_outputs = task_report.get("deliverable_outputs", [])
                        for deliverable in deliverable_outputs:
                            refs = deliverable.get("search_references", [])
                            if refs:
                                all_search_refs.extend(refs)

                    # 也检查顶层的 search_references
                    top_level_refs = result.get("search_references", [])
                    if top_level_refs:
                        all_search_refs.extend(top_level_refs)

            if all_search_refs:
                logger.info(f" [v7.271] 批次 {current_batch} 合并了 {len(all_search_refs)} 条搜索引用")
            else:
                logger.debug(f"ℹ️ [v7.271] 批次 {current_batch} 无搜索引用")

            # 返回状态更新（下一步由second_batch_strategy_review决定路由）

            #  修复（2025-11-30）：构造更具体的detail消息，显示刚完成的专家
            if completed_agents:
                # 如果只有1个专家，显示具体名称；如果多个，显示数量和列表
                if len(completed_agents) == 1:
                    detail_message = f"专家【{completed_agents[0]}】分析完成"
                else:
                    agent_list = "、".join(
                        [agent.split("_")[-1] if "_" in agent else agent for agent in completed_agents]
                    )
                    detail_message = f"批次 {current_batch} 完成：{agent_list} 等 {len(completed_agents)} 位专家"
            else:
                detail_message = f"批次 {current_batch} 执行中..."

            return {
                "dependency_summary": dependency_summary,
                "completed_batches": completed_batches_updated,
                "updated_at": datetime.now().isoformat(),
                "detail": detail_message,
                "search_references": all_search_refs,  #  v7.271: 添加搜索引用到返回值
            }

        except Exception as e:
            logger.error(f"Intermediate aggregator node failed: {e}")
            import traceback

            traceback.print_exc()
            return {"error": str(e), "updated_at": datetime.now().isoformat()}

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
            role_id
            for role_id in active_agents
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
            "timestamp": datetime.now().isoformat(),
        }

        return {"dependency_summary": dependency_summary, "updated_at": datetime.now().isoformat()}

    # ============================================================================
    #  v3.5 Expert Collaboration: Challenge Detection Node
    # ============================================================================

    def _detect_challenges_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
         v3.5 挑战检测节点 - 检测专家输出中的challenge_flags并处理

         v7.16: 支持新版 LangGraph ChallengeDetectionAgent

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
        logger.info(" [v3.5] 开始检测专家挑战...")

        try:
            # 调用核心挑战检测函数（现在只返回新增字段）
            updated_state = detect_and_handle_challenges_node(state)

            # 记录检测结果
            if updated_state.get("has_active_challenges"):
                challenge_count = len(updated_state.get("challenge_detection", {}).get("challenges", []))
                logger.info(f" [v3.5] 检测到 {challenge_count} 个专家挑战")

                if updated_state.get("requires_feedback_loop"):
                    logger.warning("️ [v3.5] 需要启动反馈循环回访需求分析师")
            else:
                logger.info(" [v3.5] 未检测到挑战，专家接受需求分析师的洞察")

            return updated_state

        except Exception as e:
            logger.error(f" [v3.5] 挑战检测失败: {e}")
            import traceback

            logger.error(traceback.format_exc())
            # 返回安全的默认值
            return {
                "has_active_challenges": False,
                "requires_feedback_loop": False,
                "challenge_detection": {"has_challenges": False, "challenges": []},
                "challenge_handling": {"requires_revisit": False},
            }
            # 失败时返回原状态，不影响工作流继续
            return {
                **state,
                "has_active_challenges": False,
                "requires_feedback_loop": False,
                "challenge_detection_error": str(e),
            }

    def _route_after_challenge_detection(self, state: ProjectAnalysisState) -> str:
        """
         v3.5 挑战检测后的路由决策

        根据挑战检测结果决定下一步:
        - 如果requires_manual_review=True → "manual_review" (>3个must_fix问题)
        - 如果requires_client_review=True → "manual_review" (甲方裁决，改由人工审核节点处理）
        - 如果requires_feedback_loop=True → "revisit_requirements" (回访需求分析师)
        - 否则 → "continue_workflow" (继续正常流程)

        优先级: manual_review > escalate > revisit_ra > continue

        修复 QW-1 (v3.5+): analysis_review 节点已在 v2.2 废弃，requires_client_review 改路由到 manual_review

        Args:
            state: 当前工作流状态

        Returns:
            路由目标: "manual_review" | "revisit_requirements" | "continue_workflow"
        """
        #  最高优先级：检查是否需要人工审核（>3个must_fix）
        requires_manual_review = state.get("requires_manual_review", False)
        if requires_manual_review:
            issues_count = state.get("critical_issues_count", 0)
            logger.error(f" [Manual Review] 发现{issues_count}个严重质量问题（超过阈值），触发人工审核")
            return "manual_review"

        #  优先检查是否需要甲方裁决（escalate闭环）
        # 修复 QW-1：analysis_review 节点已在 v2.2 废弃，改路由到 manual_review（人工裁决）
        requires_client_review = state.get("requires_client_review", False)
        if requires_client_review:
            escalated_count = len(state.get("escalated_challenges", []))
            logger.warning(f" [v3.5 Escalate] {escalated_count}个挑战需要甲方裁决，路由到 manual_review")
            return "manual_review"

        # 检查是否需要回访需求分析师（revisit_ra闭环）
        requires_feedback = state.get("requires_feedback_loop", False)
        if requires_feedback:
            reason = state.get("feedback_loop_reason", "专家挑战需要澄清")
            logger.info(f" [v3.5] 启动反馈循环: {reason}")
            return "revisit_requirements"

        # 默认继续正常流程
        logger.info("️ [v3.5] 继续正常工作流")
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

            logger.info(
                f" Batch router: current={current_batch}, total={total_batches}, is_rerun={is_rerun}, skip_second_review={skip_second_review}"
            )

            #  优先检查：如果是审核触发的重新执行（整改）
            if is_rerun:
                #  关键改进：检查是否跳过二次审核
                if skip_second_review:
                    logger.info(" 专家整改完成，跳过二次审核，直接进入挑战检测和报告生成")
                    return Command(
                        update={
                            "is_rerun": False,  # 清除标记
                            "skip_second_review": False,  # 清除标记
                            "specific_agents_to_run": [],  # 清空
                            "analysis_approved": True,  # 标记为审核通过（整改视为通过）
                        },
                        goto="detect_challenges",  #  跳过审核，直接进入挑战检测
                    )
                else:
                    # 需要二次审核（一般不会走到这里，因为我们设置了skip_second_review=True）
                    logger.info(" 重新执行完成，返回挑战检测进行评估")
                    return Command(
                        update={"is_rerun": False, "specific_agents_to_run": []},  # 清除标记  # 清空
                        goto="detect_challenges",  #  v2.2: 直接到detect_challenges，跳过analysis_review
                    )

            # 验证批次完成情况
            batch_completed = dependency_summary.get("batch_completed", False)
            if not batch_completed:
                logger.warning(f"️ Batch {current_batch} not fully completed, but routing to next step")
                completed_count = dependency_summary.get("completed_count", 0)
                total_count = dependency_summary.get("total_count", 0)
                logger.warning(f"   Completed: {completed_count}/{total_count}")

            # 决策路由
            if current_batch < total_batches:
                # 还有下一批次，增加批次号
                next_batch = current_batch + 1
                logger.info(f"️  Routing to next batch: {next_batch}/{total_batches}")
                logger.info(f"   Next batch will contain: {len(batches[next_batch - 1])} agents")

                return Command(update={"current_batch": next_batch}, goto="batch_strategy_review")
            else:
                # 所有批次完成，直接进入挑战检测
                logger.info(f" All {total_batches} batches completed")

                #  修复：如果已审核通过（第1轮触发detect_challenges），不再重复触发
                if state.get("analysis_approved", False):
                    logger.info(" 分析已审核通过，跳过重复审核")
                    return Command(goto=END)

                logger.info("️  Routing to detect_challenges ( v2.2: 跳过analysis_review)")
                return Command(goto="detect_challenges")  #  v2.2: 直接到detect_challenges

        except Exception as e:
            logger.error(f" Batch router failed: {e}")
            import traceback

            traceback.print_exc()
            # 出错时默认进入挑战检测
            return Command(goto="detect_challenges")  #  v2.2: 直接到detect_challenges

    def _batch_strategy_review_node(self, state: ProjectAnalysisState) -> Command:
        """
        批次策略审核节点 - 支持多种执行模式 (v3.6优化)

         v3.6优化 (2025-11-29): 支持用户确认模式
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

            #  v3.6: 根据执行模式决定是否需要用户确认
            if execution_mode == "automatic":
                # 方案C：全自动执行（旧行为）
                logger.info(f" 批次 {current_batch}/{len(batches)} 自动执行（方案C：全自动批次调度）")
                return Command(
                    update={
                        "batch_strategy_approved": True,
                        "auto_approved": True,
                        "auto_approval_reason": "execution_mode=automatic",
                    },
                    goto="batch_executor",
                )
            elif execution_mode == "preview":
                # 方案D：显示计划后自动执行
                logger.info(f" 批次 {current_batch}/{len(batches)} 显示计划后自动执行")
                # TODO: 可以在这里发送通知给前端
                return Command(
                    update={
                        "batch_strategy_approved": True,
                        "auto_approved": True,
                        "auto_approval_reason": "execution_mode=preview",
                    },
                    goto="batch_executor",
                )
            else:
                # 方案A：手动确认模式（默认）
                logger.info(f" 批次 {current_batch}/{len(batches)} 等待用户确认")

                # 构建批次信息
                batch_info = {
                    "interaction_type": "batch_confirmation",  #  修复：与其他 interrupt 保持一致使用 interaction_type
                    "current_batch": current_batch,
                    "total_batches": len(batches),
                    "agents_in_batch": batch_agents,
                    "execution_strategy": "parallel" if len(batch_agents) > 1 else "sequential",
                    "message": f"准备执行批次 {current_batch}/{len(batches)}",
                    "details": {
                        "专家列表": batch_agents,
                        "执行方式": "并行执行" if len(batch_agents) > 1 else "顺序执行",
                        "预计耗时": f"{len(batch_agents) * 3}分钟" if len(batch_agents) == 1 else f"{4}分钟",
                    },
                    "options": {"approve": "批准执行", "skip": "跳过此批次", "modify": "修改批次配置"},
                }

                # 触发中断，等待用户确认
                logger.info(f" [DEBUG] 触发批次确认中断: {batch_info}")
                user_response = interrupt(batch_info)
                logger.info(f" 收到用户响应: {user_response}")

                # 处理用户响应
                if user_response == "skip" or (
                    isinstance(user_response, dict) and user_response.get("action") == "skip"
                ):
                    logger.info("️ 用户选择跳过此批次")
                    # 跳过当前批次，进入下一批次
                    return Command(
                        update={
                            "current_batch": current_batch + 1,
                            "batch_strategy_approved": False,
                            "batch_skipped": True,
                        },
                        goto="batch_router",  # 返回路由器检查是否还有更多批次
                    )
                else:
                    # 批准执行（默认行为）
                    logger.info(" 用户批准执行此批次")
                    return Command(
                        update={"batch_strategy_approved": True, "auto_approved": False, "user_confirmed": True},
                        goto="batch_executor",
                    )

        except Exception as e:
            # 只捕获非Interrupt异常
            if "Interrupt" not in str(type(e)):
                logger.error(f" Batch strategy review failed: {e}")
                import traceback

                traceback.print_exc()
                # 出错时默认批准并继续
                return Command(goto="batch_executor")
            else:
                # 重新抛出Interrupt异常（LangGraph需要）
                raise

    # def _analysis_review_node(self, state: ProjectAnalysisState) -> Command:
    #     """
    #     ️ v2.2: 分析审核节点 - 已废弃
    #
    #     原功能: 递进式单轮审核 (v2.0) - 红→蓝→评委→甲方
    #     新方案: 质量审核已前移到 role_selection_quality_review（角色选择后）
    #
    #     核心改进:
    #     1. 移除多轮迭代逻辑
    #     2. 递进式三阶段：红→蓝→评委→甲方
    #     3. 输出改进建议（而非重新执行）
    #     4. 记录final_ruling到state
    #
    #      v7.16: 支持新版 LangGraph AnalysisReviewAgent
    #     """
    #     logger.info("Executing progressive single-round analysis review node")
    #
    #     #  v7.16: 使用新版 LangGraph Agent（如果启用）
    #     if USE_V716_AGENTS:
    #         logger.info(" [v7.16] 使用 AnalysisReviewAgent")
    #         return AnalysisReviewNodeCompat.execute(
    #             state=state, store=self.store, llm_model=self.llm_model, config=self.config
    #         )
    #
    #     return AnalysisReviewNode.execute(state=state, store=self.store, llm_model=self.llm_model, config=self.config)

    def _manual_review_node(self, state: ProjectAnalysisState) -> Command:
        """
        人工审核节点 - 处理严重质量问题 ()

        当审核系统发现>3个must_fix问题时触发，暂停流程等待用户裁决：
        1. 继续：接受风险生成报告
        2. 终止：全面整改后再生成报告
        3. 选择性整改：用户选择关键问题进行整改

        注意: 不要捕获Interrupt异常!
        Interrupt是LangGraph的正常控制流,必须让它传播到框架层
        """
        logger.info(" Executing manual review node for critical quality issues")
        return ManualReviewNode.execute(state=state, store=self.store)

    @track_active_step("result_aggregator")
    def _result_aggregator_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        结果聚合节点

        注意: 只返回需要更新的字段,不返回完整状态
        这样可以避免并发更新冲突

         修复: 不更新current_stage,避免与pdf_generator并发冲突
         v7.16: 支持新版 LangGraph ResultAggregatorAgentV2
        """
        try:
            logger.info("Executing result aggregator node")

            # 创建结果聚合器智能体
            agent = ResultAggregatorAgent(llm_model=self.llm_model, config=self.config)

            # 执行聚合
            result = agent.execute(state, {}, self.store)

            # 只返回需要更新的字段 (不更新current_stage)
            sd = result.structured_data or {}
            return {
                "final_report": sd,
                "agent_results": {"RESULT_AGGREGATOR": result.to_dict()},
                # ── v8.0: 透传投射调度结果到 state ──────────────────────────
                "meta_axis_scores": sd.get("meta_axis_scores"),
                "active_projections": sd.get("active_projections"),
                "perspective_outputs": sd.get("perspective_outputs"),
                "projection_reports": sd.get("projection_reports"),
                "updated_at": datetime.now().isoformat(),
                "detail": "整合专家成果，生成最终报告（含多视角投射）",
            }

        except Exception as e:
            logger.error(f"Result aggregator node failed: {e}")
            return {"error": str(e), "updated_at": datetime.now().isoformat(), "detail": "结果聚合失败"}

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
            from ...report.text_generator import TextGeneratorAgent

            agent = TextGeneratorAgent(config=self.config)

            # 执行报告生成
            result = agent.execute(state, {}, self.store)

            # 只返回需要更新的字段
            return {
                "current_stage": AnalysisStage.COMPLETED.value,
                "pdf_path": result.structured_data.get("file_path"),
                "agent_results": {"REPORT_GENERATOR": result.to_dict()},
                "updated_at": datetime.now().isoformat(),
                "detail": "生成最终交付文档",
            }

        except Exception as e:
            logger.error(f"Report generator node failed: {e}")
            return {"error": str(e), "updated_at": datetime.now().isoformat(), "detail": "报告生成失败"}

    def _user_question_node(self, state: ProjectAnalysisState) -> Command:
        """
        用户追问节点

         修复 (2025-11-27): 不要捕获 Interrupt 异常
        Interrupt 是 LangGraph 的正常控制流，必须让它传播到框架层
        """
        logger.info("Executing user question node")
        #  不要用 try-except 捕获！Interrupt 必须传播
        return UserQuestionNode.execute(state, self.store)

    # 路由函数

    # 路由函数
    def _route_from_batch_aggregator(self, state: ProjectAnalysisState) -> str:
        """
        批次聚合器后的路由函数

         修复（2025-11-30）：移除 analysis_approved 的 END 路径
        - Bug原因：当 analysis_approved=True 时直接 END，跳过了 result_aggregator 和 pdf_generator
        - 修复：始终路由到 batch_router，让 batch_router 决定是否进入 analysis_review
        - analysis_review → detect_challenges → result_aggregator 是唯一生成报告的路径

        逻辑:
        - 始终 → batch_router
          - batch_router 检查批次完成情况：
            - 如果还有批次：继续下一批
            - 如果所有批次完成：进入 analysis_review → detect_challenges → result_aggregator → pdf_generator
        """
        logger.info(" [batch_aggregator] 路由到 batch_router 检查批次状态")
        return "batch_router"

    #  v7.151: _route_after_requirements_confirmation 已移除
    # 需求确认逻辑已合并到 questionnaire_summary（需求洞察）节点，使用 Command 动态路由

    def _route_after_pdf_generator(self, state: ProjectAnalysisState) -> Union[str, Any]:
        """报告生成后的路由: 直接结束，由前端负责结果呈现和追问交互"""
        # 标记追问功能可用，前端会根据此标志显示追问入口
        state["post_completion_followup_available"] = self.config.get("post_completion_followup_enabled", True)

        logger.info(" [pdf_generator] 报告已生成，流程结束，前端接管结果呈现")
        return END

    def _route_after_user_question(self, state: ProjectAnalysisState) -> Literal["project_director", END]:
        """
        用户追问后的路由

         修复 (2025-11-27): 追问完成后应该结束流程，而不是回到 result_aggregator
        避免无限循环：pdf_generator → user_question → result_aggregator → pdf_generator

         修复 (2025-11-29): additional_questions是list类型，不能调用.strip()
        """
        additional_questions = state.get("additional_questions")

        #  修复：additional_questions 是list，不是string
        if additional_questions and len(additional_questions) > 0:
            logger.info(f" 用户提出追问({len(additional_questions)}个)，返回 project_director 重新分析")
            return "project_director"
        else:
            logger.info(" 用户未追问或追问完成，流程结束")
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
            initial_state = StateManager.create_initial_state(user_input=user_input, session_id=session_id)

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
                "execution_time": final_state.get("execution_time"),
            }

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return {"session_id": session_id, "status": "failed", "error": str(e)}

    def _filter_tools_for_role(
        self, role_id: str, all_tools: Dict[str, Any], role_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
         v7.105: 根据角色类型筛选工具
         v7.110: 优先使用用户在任务审批时配置的搜索工具设置

        Args:
            role_id: 角色ID（如 V4_设计研究员_4-1）
            all_tools: 所有可用工具
            role_config: 角色配置（包含用户设置的 enable_search）

        Returns:
            该角色应该拥有的工具字典
        """
        #  优先检查用户设置
        enable_search = role_config.get("enable_search", None)

        if enable_search is False:
            # 用户明确禁用搜索工具
            logger.info(f" [{role_id}] 用户禁用搜索工具，返回空工具集")
            return {}

        if enable_search is True:
            # 用户明确启用搜索工具，返回所有可用工具
            logger.info(f" [{role_id}] 用户启用搜索工具，返回全部工具")
            return all_tools

        # enable_search 为 None 时，降级到硬编码规则
        logger.debug(f" [{role_id}] 未检测到用户设置，使用默认规则")

        # 提取角色类型前缀（V2/V3/V4/V5/V6）
        role_type = role_id.split("_")[0] if "_" in role_id else role_id[:2]

        # 角色工具映射（基于角色YAML配置）
        #  v7.153: V2 设计总监改为只能使用知识库（内部知识，不做外部搜索）
        # V2: 设计总监 - 仅知识库（高层决策者，可查阅内部知识库，但不做外部搜索）
        # V3: 叙事专家 - 中文搜索(Bocha) + 国际搜索(Tavily) + 知识库(Milvus)
        # V4: 设计研究员 - 全部工具（学术论文Arxiv + 所有搜索 + Milvus）
        # V5: 场景专家 - 中文搜索(Bocha) + 国际搜索(Tavily) + 知识库(Milvus)
        # V6: 总工程师 - 全部工具（技术规范需要Arxiv + Milvus）
        role_tool_mapping = {
            "V2": ["milvus"],  #  v7.153: 设计总监仅知识库搜索（内部知识）
            "V3": ["bocha", "tavily", "milvus"],  # 叙事专家 (博查主导+Tavily辅助+Milvus知识库)
            "V4": ["bocha", "tavily", "arxiv", "milvus"],  # 设计研究员（博查+Tavily+学术+Milvus）
            "V5": ["bocha", "tavily", "milvus"],  # 场景专家 (博查主导+Tavily辅助+Milvus)
            "V6": ["bocha", "tavily", "arxiv", "milvus"],  # 总工程师（博查+Tavily+学术+Milvus）
            "V7": ["bocha", "tavily", "arxiv", "milvus"],  #  v7.156: 情感洞察专家（博查+Tavily+学术+Milvus）
        }

        allowed_tool_names = role_tool_mapping.get(role_type, [])

        # 筛选工具
        filtered_tools = {name: tool for name, tool in all_tools.items() if name in allowed_tool_names}

        return filtered_tools

    def _build_context_for_expert(self, state: ProjectAnalysisState) -> str:
        """
        为任务导向专家构建上下文信息

         v7.18 升级4: 专家协作通道 - 传递前序专家的完整输出
         v7.502 P1优化: 使用智能上下文压缩器减少Token消耗

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

        #  P1优化: 压缩结构化需求
        batch_number = state.get("current_batch_number", 1)
        total_batches = state.get("total_batches", 3)
        current_role_id = state.get("role_id", "")

        # 创建上下文压缩器
        compressor = create_context_compressor(batch_number, total_batches)

        # 添加结构化需求（使用压缩器）
        structured_requirements = state.get("structured_requirements", {})
        if structured_requirements:
            compressed_req = compressor.compress_user_requirements(structured_requirements)
            if compressed_req:
                context_parts.append(compressed_req)

        #  v7.106: 添加用户确认的核心任务
        confirmed_tasks = state.get("confirmed_core_tasks", [])
        if confirmed_tasks:
            context_parts.append("\n## 用户确认的核心任务\n")
            context_parts.append("以下是用户在问卷环节确认的核心任务，你的分析应该围绕这些任务展开：\n")
            for i, task in enumerate(confirmed_tasks, 1):
                context_parts.append(f"\n**核心任务 {i}: {task.get('title')}**")
                context_parts.append(f"- 描述: {task.get('description')}")
                context_parts.append(f"- 类型: {task.get('type')}")

        #  v7.106: 添加用户补充的信息（Step 3 问卷答案）
        gap_filling_answers = state.get("gap_filling_answers", {})
        if gap_filling_answers:
            context_parts.append("\n## 用户补充的关键信息\n")
            for question_id, answer in gap_filling_answers.items():
                context_parts.append(f"- {question_id}: {answer}")

        #  P1优化: 使用压缩器处理前序专家输出
        agent_results = state.get("agent_results", {})
        if agent_results:
            compressed_results = compressor.compress_agent_results(agent_results, current_role_id)
            if compressed_results:
                context_parts.append(compressed_results)

        # 添加项目状态信息
        context_parts.append(f"\n## 项目状态信息")
        context_parts.append(f"- 当前阶段: {state.get('current_phase', 'unknown')}")
        context_parts.append(f"- 已完成专家数: {len(agent_results)}")

        # 添加质量检查清单（如果有）
        quality_checklist = state.get("quality_checklist", {})
        if quality_checklist:
            context_parts.append("## 质量要求")
            for category, criteria in quality_checklist.items():
                if isinstance(criteria, list):
                    context_parts.append(f"**{category}**: {', '.join(criteria)}")
                else:
                    context_parts.append(f"**{category}**: {criteria}")

        final_context = "\n\n".join(context_parts)

        #  P1优化: 记录压缩统计
        stats = compressor.get_compression_stats()
        if stats["original_length"] > 0:
            logger.info(
                f"️ [ContextCompressor] Batch{batch_number} {current_role_id} - "
                f"原始: {stats['original_length']}字符, "
                f"压缩后: {stats['compressed_length']}字符, "
                f"压缩率: {stats['compression_ratio']:.2%}, "
                f"节省: {stats['savings_percent']:.1f}%"
            )

        return final_context
