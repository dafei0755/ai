# -*- coding: utf-8 -*-
"""
LT-1 规划节点 Mixin — 项目总监、角色选择、任务分派、质量预检

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
from ...agents.dynamic_project_director import detect_and_handle_challenges_node  #  v3.5
from ...agents.feasibility_analyst import FeasibilityAnalystAgent  #  V1.5可行性分析师
from ...agents.quality_monitor import QualityMonitor  #
from ...core.state import AnalysisStage, ProjectAnalysisState, StateManager
from ...core.types import AgentType, format_role_display_name
from ...interaction.interaction_nodes import (  # FinalReviewNode,  # 已移除：客户需求中没有最终审核阶段; AnalysisReviewNode,  # ️ v2.2: 已废弃，质量审核已前置化
    CalibrationQuestionnaireNode,
    UserQuestionNode,
)
from ...interaction.nodes.manual_review import ManualReviewNode  #  人工审核节点

#  v7.87: 三步递进式问卷节点
from ...interaction.nodes.progressive_questionnaire import (
    ProgressiveQuestionnaireNode,
    progressive_step1_core_task_node,
    progressive_step2_radar_node,
    progressive_step3_gap_filling_node,
)
from ...interaction.nodes.quality_preflight import QualityPreflightNode  #

#  v7.135: 问卷汇总节点（需求重构）
from ...interaction.nodes.questionnaire_summary import questionnaire_summary_node

#  统一审核节点（合并角色选择和任务分派审核）
from ...interaction.role_task_unified_review import role_task_unified_review_node

#  v7.502 P1优化: 智能上下文压缩器
from ..context_compressor import create_context_compressor

# from ..interaction.role_selection_review import role_selection_review_node  # 已废弃
# from ..interaction.task_assignment_review import task_assignment_review_node  # 已废弃
from ...interaction.second_batch_strategy_review import SecondBatchStrategyReviewNode
from ...report.pdf_generator import PDFGeneratorAgent
from ...report.result_aggregator import ResultAggregatorAgent
from ...workflow.nodes.search_query_generator_node import search_query_generator_node  #  v7.109

#  v7.87: 三步递进式问卷（默认启用）
from ...security import ReportGuardNode  #  内容安全与领域过滤

#  v7.3 统一输入验证节点（合并 input_guard 和 domain_validator）
from ...security.unified_input_validator_node import InputRejectedNode, UnifiedInputValidatorNode

# 动态本体论注入工具
from ...utils.ontology_loader import OntologyLoader


class PlanningNodesMixin:
    """
    LT-1 规划节点 Mixin — 项目总监、角色选择、任务分派、质量预检

    Mixin for MainWorkflow. All methods receive full `self` access because
    MainWorkflow inherits from this class along with other Mixin classes.
    Do NOT instantiate this class directly.
    """

    def _find_matching_role(self, predicted_role: str, active_agents: List[str]) -> Optional[str]:
        """
         修复问题1: 查找预测角色在实际选定角色中的匹配项

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
                    logger.debug(f" [匹配] 前缀匹配: {predicted_role} → {agent_id}")
                    return agent_id

        # 规则3: 层级匹配（V2）
        if len(parts) >= 1:
            level_prefix = parts[0]  # V2

            for agent_id in active_agents:
                if agent_id.startswith(level_prefix):
                    logger.debug(f" [匹配] 层级匹配: {predicted_role} → {agent_id}")
                    return agent_id

        logger.warning(f"️ [匹配失败] 未找到 {predicted_role} 的匹配角色")
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
            agent = AgentFactory.create_agent(AgentType.PROJECT_DIRECTOR, llm_model=self.llm_model, config=self.config)

            # 执行分析 - 返回Command对象
            command = agent.execute(state, {}, self.store)

            # 提取状态更新
            if isinstance(command, Command):
                state_update = command.update or {}
            else:
                logger.error(f"Unexpected return type from ProjectDirector: {type(command)}")
                state_update = {"error": "ProjectDirector returned unexpected type"}

            #  保留关键状态标志（避免被覆盖）
            if state.get("skip_unified_review"):
                state_update["skip_unified_review"] = True
                logger.info(" 保留 skip_unified_review 标志")
            else:
                logger.warning("️ [DEBUG] project_director 进入时 skip_unified_review 不存在或为False")
                logger.info(f" [DEBUG] project_director 输入 state keys: {list(state.keys())}")

            # 动态模式: 使用 active_agents
            active_agents = state_update.get("active_agents", [])
            logger.info(f" Dynamic mode: Project director selected {len(active_agents)} dynamic roles")
            logger.debug(f"Active agents: {active_agents}")

            #  修复问题1: 校正交付物责任者映射
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
                            logger.info(f" [修复] 交付物 {deliverable_id} 责任者校正: {predicted_owner} → {actual_owner}")
                            corrected_owner_map[deliverable_id] = actual_owner

                            # 更新元数据
                            corrected_metadata[deliverable_id] = {
                                **metadata,
                                "owner": actual_owner,
                                "owner_predicted": False,  # 标记为已校正
                                "owner_original_prediction": predicted_owner,  # 保留原始预测
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
                    logger.info(f" [修复] 已校正 {len(corrected_owner_map)} 个交付物责任者映射")

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

            #  返回明确的错误状态，防止下游节点崩溃
            return {
                "error": str(e),
                "strategic_analysis": None,  # 明确标记为 None
                "active_agents": [],
                "execution_mode": "dynamic",
                "errors": [{"node": "project_director", "error": str(e), "type": "ProjectDirectorFailure"}],
            }

    def _deliverable_id_generator_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
         v7.108 交付物ID生成节点

        在project_director之后、role_task_unified_review之前执行，
        为所有选定角色预生成交付物ID，以便后续专家执行阶段生成概念图时使用。

        Returns:
            包含deliverable_metadata和deliverable_owner_map的状态更新
        """
        try:
            logger.info(" [deliverable_id_generator] 开始生成交付物ID...")

            # 导入节点函数
            from ..workflow.nodes.deliverable_id_generator_node import deliverable_id_generator_node

            # 执行交付物ID生成
            result = deliverable_id_generator_node(state)

            # 记录生成结果
            total_deliverables = len(result.get("deliverable_metadata", {}))
            logger.info(f" [deliverable_id_generator] 成功生成 {total_deliverables} 个交付物ID")

            return result

        except Exception as e:
            logger.error(f" [deliverable_id_generator] 生成交付物ID失败: {e}")
            logger.exception(e)

            #  详细诊断信息
            strategic_analysis = state.get("strategic_analysis", {})
            selected_roles = strategic_analysis.get("selected_roles", [])

            logger.error(f" [诊断] strategic_analysis 键: {list(strategic_analysis.keys())}")
            logger.error(f" [诊断] selected_roles 类型: {type(selected_roles)}")

            if selected_roles:
                logger.error(f" [诊断] selected_roles 长度: {len(selected_roles)}")
                logger.error(f" [诊断] 第一个元素类型: {type(selected_roles[0])}")
                logger.error(f" [诊断] 第一个元素内容: {str(selected_roles[0])[:300]}")

            return {"deliverable_metadata": {}, "deliverable_owner_map": {}, "detail": f"交付物ID生成失败: {str(e)}"}

    def _search_query_generator_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """搜索查询生成节点包装器 v7.109"""
        try:
            logger.info(" [search_query_generator] 开始生成搜索查询和概念图配置...")
            result = search_query_generator_node(state)
            deliverable_metadata = result.get("deliverable_metadata", {})
            processed_count = len([m for m in deliverable_metadata.values() if "search_queries" in m])
            logger.info(f" [search_query_generator] 成功为 {processed_count} 个交付物生成配置")
            return result
        except Exception as e:
            logger.error(f" [search_query_generator] 生成配置失败: {e}")
            return {"project_image_aspect_ratio": "16:9", "detail": f"搜索查询生成失败: {str(e)}"}

    def _role_task_unified_review_node(self, state: ProjectAnalysisState):
        """
         角色任务统一审核节点

        合并角色选择审核和任务分派审核，减少人机交互次数

        注意: 不要捕获Interrupt异常!
        Interrupt是LangGraph的正常控制流,必须让它传播到框架层

        返回: Command对象（用于动态路由到 batch_executor 或 project_director）
        """
        try:
            logger.info(" Executing unified role & task review node")
            return role_task_unified_review_node(state)  # 返回Command
        except Exception as e:
            # 只捕获非Interrupt异常
            if "Interrupt" not in str(type(e)):
                logger.error(f" Unified review node failed: {e}")
                import traceback

                traceback.print_exc()
                return {"error": str(e)}
            else:
                # 重新抛出Interrupt异常
                raise

    # ============================================================================
    # ️ 已废弃的独立审核节点（保留注释作为历史参考）
    # ============================================================================
    # def _role_selection_review_node(self, state: ProjectAnalysisState):
    #     """角色选择审核节点 - 已合并到 role_task_unified_review"""
    #     pass

    # def _task_assignment_review_node(self, state: ProjectAnalysisState):
    #     """任务分派审核节点 - 已合并到 role_task_unified_review"""
    #     pass

    def _role_selection_quality_review_node(self, state: ProjectAnalysisState):
        """
         v2.2 角色选择质量审核节点（红蓝对抗）

        在角色选择后、任务分解前运行，审核角色配置的合理性

        返回: Command对象（用于动态路由到 user_question 或 quality_preflight）
        """
        try:
            logger.info(" Executing role selection quality review node")
            from ..interaction.nodes.role_selection_quality_review import role_selection_quality_review_node

            # 传递 llm_model 通过 config
            config = {"configurable": {"llm_model": self.llm_model}}

            return role_selection_quality_review_node(state, config=config)
        except Exception as e:
            # 只捕获非Interrupt异常
            if "Interrupt" not in str(type(e)):
                logger.error(f" Role selection quality review node failed: {e}")
                import traceback

                traceback.print_exc()
                # 失败时跳过审核，继续流程
                return Command(
                    update={"role_quality_review_result": {"skipped": True, "reason": f"审核失败: {str(e)}"}},
                    goto="quality_preflight",
                )
            else:
                # 重新抛出Interrupt异常
                raise

    async def _quality_preflight_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        质量预检节点 - 前置预防第1层（异步版本）

         P1优化：使用异步调用，配合 QualityPreflightNode 的异步实现
         v7.16: 支持新版 LangGraph QualityPreflightAgent
         v7.23: 修复 interrupt 被错误捕获的问题

        在专家执行前进行:
        1. 风险预判
        2. 质量检查清单生成
        3. 能力匹配度验证
        """
        try:
            logger.info(" Executing quality preflight node (async)")

            #  v7.16: 使用新版 LangGraph Agent（如果启用）
            if USE_V716_AGENTS:
                logger.info(" [v7.16] 使用 QualityPreflightAgent")
                node = QualityPreflightNodeCompat(self.llm_model)
            else:
                node = QualityPreflightNode(self.llm_model)

            result = await node(state)  #  P1优化：使用 await 调用异步方法
            result["detail"] = "质量预检与风险评估"
            return result
        except Exception as e:
            #  v7.24: 增强 Interrupt 检测，支持多种异常格式
            from langgraph.types import Interrupt

            # 检测 Interrupt 的多种情况：
            # 1. 直接是 Interrupt 类型
            # 2. e.args[0] 是 Interrupt（部分 LangGraph 版本）
            # 3. e 是包含 Interrupt 的 tuple（某些异常包装情况）
            is_interrupt = False
            if isinstance(e, Interrupt):
                is_interrupt = True
            elif hasattr(e, "args") and e.args:
                if isinstance(e.args[0], Interrupt):
                    is_interrupt = True
                elif isinstance(e.args[0], tuple) and e.args[0] and isinstance(e.args[0][0], Interrupt):
                    is_interrupt = True

            if is_interrupt:
                logger.info(" Quality preflight interrupt triggered, pausing for user confirmation")
                raise  # 重新抛出 Interrupt，让 LangGraph 正常处理

            #  v7.24: 额外检查 - 检查错误消息中是否包含 Interrupt 关键字
            error_str = str(e)
            if "Interrupt" in error_str and "value=" in error_str:
                logger.warning(f"️ Detected Interrupt in error message, re-raising: {error_str[:100]}...")
                raise

            logger.error(f" Quality preflight node failed: {e}")
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
            logger.info(f" Dynamic mode: filtering first batch from {len(active_agents)} active agents")

            # 第一批专家: 以 V3_, V4_, V5_ 开头的角色
            first_batch_roles = [
                role_id
                for role_id in active_agents
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

                #  修复 (2025-11-19): 使用正确的节点名 agent_executor
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
                "detail": "项目总监分析失败",
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
            logger.info(f" Dynamic mode: filtering second batch from {len(active_agents)} active agents")

            # 第二批专家: 以 V2_, V6_ 开头的角色
            second_batch_roles = [
                role_id for role_id in active_agents if role_id.startswith("V2_") or role_id.startswith("V6_")
            ]

            logger.info(f"Preparing to execute {len(second_batch_roles)} dynamic agents in second batch")
            logger.debug(f"Second batch roles: {second_batch_roles}")

            # 验证第一批结果是否存在
            agent_results = state.get("agent_results", {})
            first_batch_roles = [
                role_id
                for role_id in active_agents
                if role_id.startswith("V3_") or role_id.startswith("V4_") or role_id.startswith("V5_")
            ]

            first_batch_completed = all(role_id in agent_results for role_id in first_batch_roles)

            if not first_batch_completed:
                logger.warning(f"️ First batch agents not all completed, but proceeding with second batch")
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

                #  修复 (2025-11-19): 使用正确的节点名 agent_executor
                send_list.append(Send("agent_executor", agent_state))
                logger.debug(f"Created Send for second batch dynamic agent: {role_id}")

            return send_list

        except Exception as e:
            logger.error(f"Failed to create second batch parallel tasks: {e}")
            import traceback

            traceback.print_exc()
            return []
