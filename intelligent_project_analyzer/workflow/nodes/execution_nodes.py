# -*- coding: utf-8 -*-
"""
LT-1 执行节点 Mixin — 动态批次执行、Agent 并发调度

自动由 _lt1_split_workflow.py 生成 — 勿手动修改。
通过 Mixin 继承为 MainWorkflow 提供节点方法；完整 `self` 上下文由 MainWorkflow.__init__ 保证。
"""
# ruff: noqa (generated file)
# type: ignore
#  v7.16: LangGraph Agent 升级版本（通过环境变量控制）
import asyncio
import os
import sqlite3
import time
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


class ExecutionNodesMixin:
    """
    LT-1 执行节点 Mixin — 动态批次执行、Agent 并发调度

    Mixin for MainWorkflow. All methods receive full `self` access because
    MainWorkflow inherits from this class along with other Mixin classes.
    Do NOT instantiate this class directly.
    """

    async def _execute_agent_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
        执行单个智能体节点（仅 Dynamic Mode）

        根据LangGraph Send API,这个节点接收的state是通过Send传递的完整状态
        状态中应该包含role_id字段,指示要执行哪个智能体

         集成实时质量监控（第2层预防）:
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
                logger.error(" No role_id specified in state")
                logger.debug(f"State keys: {list(state.keys())}")
                return {"error": "No role_id specified"}

            # 获取质量检查清单
            quality_checklists = state.get("quality_checklists", {})
            quality_checklist = quality_checklists.get(role_id, {})

            # 获取重试信息
            review_round = state.get("review_round", 0)
            review_feedback = state.get("review_feedback")
            retry_count = state.get(f"retry_count_{role_id}", 0)  #  重试计数

            # 动态模式: 使用 TaskOrientedExpertFactory (v2.0)
            logger.info(f" Executing task-oriented agent: {role_id} (轮次{review_round}, 重试{retry_count})")

            # 导入任务导向专家工厂
            from intelligent_project_analyzer.agents.task_oriented_expert_factory import TaskOrientedExpertFactory
            from intelligent_project_analyzer.core.role_manager import RoleManager

            # 初始化角色管理器
            role_manager = RoleManager()

            # 解析角色ID
            logger.info(f" [DEBUG] Parsing role_id: {role_id}")
            base_type, rid = role_manager.parse_full_role_id(role_id)
            logger.info(f" [DEBUG] Parsed: base_type={base_type}, rid={rid}")

            #  尝试直接获取配置，如果失败则用前缀匹配
            role_config = role_manager.get_role_config(base_type, rid)

            if not role_config:
                # 使用前缀匹配（如 "V5"）查找配置
                v_prefix = role_id.split("_")[0]  # 提取 "V5"
                logger.info(f" [DEBUG] Direct match failed, trying prefix: {v_prefix}")

                # 遍历所有角色配置，找到匹配前缀的
                for config_key in role_manager.roles.keys():
                    if config_key.startswith(v_prefix):
                        role_config = role_manager.get_role_config(config_key, rid)
                        if role_config:
                            logger.info(f" Found config using prefix match: {config_key}")
                            break

            logger.info(f" [DEBUG] role_config found: {role_config is not None}")

            if not role_config:
                logger.error(f" Role config not found for {role_id}")
                return {"error": f"Role config not found for {role_id}"}

            #  P0-1修复：执行前总是注入质量约束（无论是否重试）
            if quality_checklist:
                risk_level = quality_checklist.get("risk_level", "low")
                # 只对medium和high风险任务注入质量约束
                if risk_level in ["medium", "high"]:
                    logger.info(f" 注入质量约束到 {role_id} (风险等级: {risk_level}, 轮次: {review_round}, 重试: {retry_count})")
                    original_prompt = role_config.get("system_prompt", "")
                    enhanced_prompt = QualityMonitor.inject_quality_constraints(original_prompt, quality_checklist)
                    role_config["system_prompt"] = enhanced_prompt
                else:
                    logger.debug(f"️ {role_id} 风险等级为 {risk_level}，跳过质量约束注入")

            #  v2.0 分层动态本体论注入逻辑
            # ================================================
            # 三层架构：
            # 1. 基础层：meta_framework（所有专家共享）
            # 2. 项目类型层：按项目类型的领域框架
            # 3. 专家强化层：针对特定专家的额外维度（可选）
            # ================================================

            # 1. 获取项目类型
            project_type = state.get("project_type")

            # 2. 提取专家角色标识（从role_id中剥离版本前缀）
            # 例如：V3_spatial_planner -> spatial_planner
            expert_role = None
            if "_" in role_id:
                parts = role_id.split("_", 1)
                if len(parts) == 2:
                    expert_role = parts[1]  # "spatial_planner"

            # 3. 使用分层加载器获取合并后的本体论
            ontology_merged = self.ontology_loader.get_layered_ontology(
                project_type=project_type or "meta_framework", expert_role=expert_role, include_base=True
            )

            # 4. 格式化为系统提示文本
            expert_name = role_config.get("name", "专家") if role_config else "专家"
            ontology_text = self.ontology_loader.format_as_prompt(ontology_merged, expert_name=expert_name)

            # 5. 注入到 system_prompt 占位符
            if role_config and "system_prompt" in role_config:
                prompt = role_config["system_prompt"]
                if "{{DYNAMIC_ONTOLOGY_INJECTION}}" in prompt:
                    injected = prompt.replace("{{DYNAMIC_ONTOLOGY_INJECTION}}", ontology_text)
                    role_config["system_prompt"] = injected

                    # 记录注入详情
                    layer_info = f"项目类型:{project_type or 'meta'}"
                    if expert_role:
                        layer_info += f" + 专家强化:{expert_role}"
                    logger.info(f" 已分层注入本体论到 {role_id} ({layer_info})")
                else:
                    logger.debug(f"ℹ️ {role_id} 的 system_prompt 未包含动态注入占位符")

            # 创建任务导向专家工厂实例
            expert_factory = TaskOrientedExpertFactory()

            # 构建上下文
            context = self._build_context_for_expert(state)

            # 构建角色对象（包含TaskInstruction）
            # 注意：ProjectAnalysisState是TypedDict，不能直接实例化
            # 我们直接使用state作为上下文

            #  修复v4.0：从 strategic_analysis.selected_roles 中获取 role_object
            # 支持两种匹配方式：精确匹配 和 短格式匹配
            strategic_analysis = state.get("strategic_analysis", {})
            selected_roles = strategic_analysis.get("selected_roles", [])
            role_object = None

            # 提取当前 role_id 的短格式 (e.g., "V4_设计研究员_4-1" -> "4-1")
            current_short_id = role_id.split("_")[-1] if "_" in role_id else role_id

            #  调试日志
            logger.debug(f" [TaskInstruction查找] role_id={role_id}, current_short_id={current_short_id}")
            logger.debug(f" [TaskInstruction查找] selected_roles数量={len(selected_roles)}")
            if selected_roles:
                sample_ids = [r.get("role_id", "N/A") for r in selected_roles[:3]]
                logger.debug(f" [TaskInstruction查找] 前3个stored_role_id: {sample_ids}")

            for role in selected_roles:
                stored_role_id = role.get("role_id", "")
                # 提取存储的 role_id 的短格式
                stored_short_id = stored_role_id.split("_")[-1] if "_" in stored_role_id else stored_role_id

                # 支持多种匹配方式：
                # 1. 精确匹配 (e.g., "V4_设计研究员_4-1" == "V4_设计研究员_4-1")
                # 2. 短格式匹配 (e.g., "4-1" == "4-1")
                # 3. 存储的是短格式，查询的是完整格式
                if stored_role_id == role_id or stored_short_id == current_short_id:
                    role_object = role
                    logger.info(f" 找到 {role_id} 的TaskInstruction (stored_role_id={stored_role_id})")
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
                                "success_criteria": ["分析深入且专业", "建议具有可操作性"],
                            }
                        ],
                        "success_criteria": ["输出符合专业标准", "建议具有实用价值"],
                        "constraints": [],
                        "context_requirements": [],
                    },
                }
                logger.warning(f"️ 未找到{role_id}的TaskInstruction，使用默认结构")

            #  v7.105: 创建搜索工具
            from intelligent_project_analyzer.services.tool_factory import ToolFactory

            # 创建所有可用工具
            all_tools = ToolFactory.create_all_tools()

            #  v7.105: 根据角色类型筛选工具
            role_tools = self._filter_tools_for_role(role_id, all_tools, role_config)

            if role_tools:
                logger.info(f" [v7.105] {role_id} 获得 {len(role_tools)} 个工具: {list(role_tools.keys())}")
            else:
                logger.debug(f"ℹ️ [v7.105] {role_id} 无工具（综合者模式）")

            # 执行任务导向专家分析
            try:
                expert_result = await expert_factory.execute_expert(
                    role_object=role_object,
                    context=context,
                    state=state,  # 直接传递state
                    tools=list(role_tools.values()) if role_tools else None,  #  传递工具列表
                )

                # 构建兼容的结果格式
                result_content = expert_result.get("analysis", "")
                structured_output = expert_result.get("structured_output")

                # 记录执行信息
                logger.info(f" 任务导向专家 {role_id} 执行完成")
                if structured_output:
                    logger.info(f" 结构化输出验证成功")
                else:
                    logger.warning(f"️ 结构化输出验证失败，使用原始输出")

            except Exception as e:
                logger.error(f" 执行任务导向专家失败: {str(e)}")
                result_content = f"执行失败: {str(e)}"
                expert_result = {
                    "expert_id": role_id,
                    "expert_name": role_config.get("name", role_id),
                    "analysis": result_content,
                    "structured_output": None,
                    "error": True,
                }

            #  执行后：快速验证
            quality_checklist = state.get("quality_checklist", {})
            if quality_checklist and result_content:
                logger.info(f" 快速验证 {role_id} 的输出质量")
                validation_result = QualityMonitor.quick_validation(result_content, quality_checklist, role_id)

                # 判断是否需要重试
                should_retry = QualityMonitor.should_retry(validation_result)

                if should_retry and retry_count == 0:
                    logger.warning(f"️ {role_id} 质量不达标，触发重试")

                    try:
                        #  v7.129: 重试时也传递tools
                        state[f"retry_count_{role_id}"] = 1
                        expert_result_retry = await expert_factory.execute_expert(
                            role_object=role_object,
                            context=context,
                            state=state,
                            tools=list(role_tools.values()) if role_tools else None,  #  传递工具列表
                        )

                        # 更新结果
                        result_content = expert_result_retry.get("analysis", "")
                        expert_result = expert_result_retry
                        logger.info(f" {role_id} 重试完成")

                    except Exception as retry_error:
                        logger.error(f" {role_id} 重试失败: {str(retry_error)}")

                # 将验证结果附加到输出
                if "quality_validation" not in expert_result:
                    expert_result["quality_validation"] = validation_result

            #  修复：将成功返回逻辑移出quality_checklist条件块
            logger.info(f" Dynamic agent {role_id} completed successfully")
            logger.debug(f"Result length: {len(result_content)} characters")

            #  字段名修复：使用 structured_output（而非 parsed_result）
            structured_output = expert_result.get("structured_output", {})
            if structured_output:
                structured_data = structured_output
                # 确保content字段存在
                if "content" not in structured_data:
                    structured_data["content"] = result_content

                #  Debug: 检查challenge_flags是否存在
                if "challenge_flags" in structured_data:
                    challenge_count = len(structured_data["challenge_flags"])
                    logger.info(f" [DEBUG] {role_id} 的 structured_data 包含 {challenge_count} 个 challenge_flags")
                else:
                    logger.debug(f"ℹ️ [DEBUG] {role_id} 的 structured_data 不包含 challenge_flags")
            else:
                structured_data = {"content": result_content}
                logger.debug(f"ℹ️ [DEBUG] {role_id} 无 structured_output，使用默认 structured_data")

            # 返回结果 - 使用 role_id 作为 key
            role_name = role_config.get("name", "未知角色")
            dynamic_role_name = role_object.get("dynamic_role_name", role_name)

            #  修复（2025-11-30）：detail 显示完整的 role_id，便于前端同步显示
            # 格式：专家【角色ID】执行中
            detail_message = f"专家【{role_id}】完成分析"

            # 只有在result_content真正为空时才返回错误
            if not result_content:
                logger.warning(f"️ Dynamic agent {role_id} returned no results")
                return {"error": f"No results from {role_id}"}

            #  P4优化：单个专家完成即推送结果（渐进式展示）
            # 获取session_id用于WebSocket推送
            session_id = state.get("session_id")
            if session_id:
                try:
                    # 推送专家结果（通过注册表，规避 workflow→api 层级直接导入）
                    import asyncio

                    from intelligent_project_analyzer.api._broadcast_registry import get_broadcast
                    broadcast_to_websockets = get_broadcast()
                    if not broadcast_to_websockets:
                        raise RuntimeError("broadcast_to_websockets not registered yet")

                    #  v7.153: 提取该专家的搜索引用用于WebSocket推送
                    expert_search_refs = expert_result.get("search_references", [])

                    broadcast_payload = {
                        "type": "agent_result",
                        "role_id": role_id,
                        "role_name": role_name,
                        "dynamic_role_name": dynamic_role_name,
                        "analysis": result_content,
                        "structured_data": structured_data,
                        "timestamp": datetime.now().isoformat(),
                    }

                    #  v7.153: 包含搜索引用（如果有）
                    if expert_search_refs:
                        broadcast_payload["search_references"] = expert_search_refs
                        logger.info(f" [v7.153] 专家 {role_id} 推送包含 {len(expert_search_refs)} 个搜索引用")

                    asyncio.create_task(broadcast_to_websockets(session_id, broadcast_payload))
                    logger.info(f" [Progressive] 已推送专家结果: {role_id} ({dynamic_role_name})")
                except Exception as broadcast_error:
                    logger.warning(f"️ WebSocket推送失败: {broadcast_error}")

            #  v7.108: 为该专家的交付物生成概念图
            #  v7.120: 优先使用 expert_result 中已生成的 concept_images
            concept_images = expert_result.get("concept_images", [])

            # 如果工厂已经生成了概念图，直接使用
            if concept_images:
                logger.info(f" [v7.120] 使用工厂生成的 {len(concept_images)} 张概念图（跳过重复生成）")
            else:
                # 否则在workflow中生成
                logger.debug(f" [v7.120] 工厂未生成概念图，在workflow中生成")
                try:
                    #  检查配置开关
                    from intelligent_project_analyzer.settings import settings

                    if not settings.image_generation.enabled:
                        logger.info(f"ℹ️ [v7.108] 图像生成已禁用（IMAGE_GENERATION_ENABLED=false），跳过")
                    else:
                        deliverable_owner_map = state.get("deliverable_owner_map", {})
                        deliverable_metadata = state.get("deliverable_metadata", {})
                        deliverable_ids = deliverable_owner_map.get(role_id, [])

                        #  详细诊断日志
                        logger.debug(f" [v7.108] deliverable_owner_map 非空: {bool(deliverable_owner_map)}")
                        logger.debug(f" [v7.108] deliverable_metadata 非空: {bool(deliverable_metadata)}")
                        logger.debug(f" [v7.108] 角色 {role_id} 交付物数量: {len(deliverable_ids)}")

                        if not deliverable_metadata:
                            logger.warning(f"️ [v7.108] deliverable_metadata 为空，可能 deliverable_id_generator 节点失败")

                        if deliverable_ids and deliverable_metadata:
                            logger.info(f" [v7.108] 为角色 {role_id} 的 {len(deliverable_ids)} 个交付物生成概念图...")

                            # 导入图片生成服务
                            from intelligent_project_analyzer.services.image_generator import ImageGeneratorService

                            # 初始化图片生成器
                            image_generator = ImageGeneratorService()

                            #  v7.128: 准备专家分析内容（现在result_content已是完整内容）
                            session_id_for_image = state.get("session_id", "unknown")
                            project_type = state.get("project_type", "interior")

                            #  v7.121: 读取问卷数据用于概念图生成
                            questionnaire_summary = state.get("questionnaire_summary", {})

                            # 为每个交付物生成概念图
                            for deliverable_id in deliverable_ids:
                                metadata = deliverable_metadata.get(deliverable_id)
                                if not metadata:
                                    logger.warning(f"  ️ 交付物 {deliverable_id} 元数据缺失，跳过图片生成")
                                    continue

                                try:
                                    #  v7.128: 提取特定交付物的专家分析内容
                                    deliverable_name = metadata.get("name", "")
                                    deliverable_specific_content = ""

                                    # 从 expert_result 的 structured_output 中提取
                                    structured_output = expert_result.get("structured_output", {})
                                    task_exec_report = structured_output.get("task_execution_report", {})
                                    deliverable_outputs = task_exec_report.get("deliverable_outputs", [])

                                    # 精准匹配交付物名称
                                    for deliverable in deliverable_outputs:
                                        if deliverable.get("deliverable_name") == deliverable_name:
                                            deliverable_specific_content = deliverable.get("content", "")[:3000]
                                            logger.info(
                                                f"  [v7.128] 为交付物 '{deliverable_name}' 提取专家分析: {len(deliverable_specific_content)} 字符"
                                            )
                                            break

                                    # 降级：如果没找到，使用完整内容
                                    if not deliverable_specific_content:
                                        deliverable_specific_content = result_content[:3000]
                                        logger.warning(f"  [v7.128] 未找到交付物 '{deliverable_name}' 的精准匹配，使用完整内容")

                                    #  v7.127: 返回值改为 List[ImageMetadata]
                                    #  v7.128: 传递完整专家分析内容
                                    image_metadata_list = await image_generator.generate_deliverable_image(
                                        deliverable_metadata=metadata,
                                        expert_analysis=deliverable_specific_content,  #  v7.128: 完整内容
                                        session_id=session_id_for_image,
                                        project_type=project_type,
                                        aspect_ratio="16:9",
                                        questionnaire_data=questionnaire_summary,  #  v7.121: 传递问卷数据
                                    )

                                    #  v7.127: 遍历添加所有生成的图片
                                    #  Phase 0优化: 排除None和默认值
                                    #  v7.402: 防止 base64 数据进入 concept_images
                                    for img_metadata in image_metadata_list:
                                        img_dict = img_metadata.model_dump(exclude_none=True, exclude_defaults=True)

                                        #  v7.402: 防御性清理 - 移除 base64_data 字段
                                        if "base64_data" in img_dict:
                                            logger.warning(f"  ️ [v7.402] 发现 base64_data 字段，已移除")
                                            del img_dict["base64_data"]

                                        #  v7.402: 确保 image_url/url 不包含 base64 数据
                                        for key in ["image_url", "url"]:
                                            if key in img_dict and isinstance(img_dict[key], str):
                                                if img_dict[key].startswith("data:image/"):
                                                    logger.error(f"   [v7.402] 发现 base64 数据在 {key}，已替换为错误标记")
                                                    img_dict[key] = "[ERROR_BASE64_FOUND_IN_WORKFLOW]"

                                        concept_images.append(img_dict)

                                    logger.info(f"   生成 {len(image_metadata_list)} 张概念图（交付物 {deliverable_id}）")

                                except Exception as img_error:
                                    logger.error(f"   生成概念图失败 (交付物 {deliverable_id}): {img_error}")
                                    # 不阻塞workflow，继续执行

                            if concept_images:
                                logger.info(f" [v7.108] 成功为角色 {role_id} 生成 {len(concept_images)} 张概念图")
                            else:
                                logger.warning(f"️ [v7.108] 角色 {role_id} 未生成任何概念图")
                        else:
                            logger.debug(f"[v7.108] 角色 {role_id} 无交付物或元数据，跳过图片生成")

                except Exception as e:
                    logger.error(f" [v7.108] 概念图生成流程失败: {e}")
                    logger.exception(e)
                    # 不阻塞workflow，专家分析仍然有效
            return {
                "agent_results": {
                    role_id: {
                        "role_id": role_id,
                        "role_name": role_name,
                        "analysis": result_content,
                        "confidence": 0.8,  # 默认置信度
                        "structured_data": structured_data,  #  使用完整的parsed_result
                        "concept_images": concept_images,  #  v7.108: 关联的概念图
                    }
                },
                "detail": detail_message,
            }

        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            import traceback

            traceback.print_exc()
            return {"error": str(e)}

    @track_active_step("batch_executor")
    async def _batch_executor_node(self, state: ProjectAnalysisState) -> Dict[str, Any]:
        """
         P0优化: 批次执行器节点 - 真并行执行当前批次所有专家

         v7.502优化: 使用asyncio.gather实现真正的并行执行
         新增: 支持 specific_agents_to_run（审核触发的重新执行）
         性能: Batch1 10s → 3.3s (67%加速), Batch2 6s → 2s (67%加速)

        架构变化:
        - 旧架构: batch_executor → _create_batch_sends → [Send API串行]
        - 新架构: batch_executor [asyncio.gather并行] → 直接返回结果

        工作原理:
        1. 检查是否有 specific_agents_to_run（审核触发的重新执行）
        2. 获取当前批次的角色列表
        3. 使用 asyncio.gather 并行执行所有专家
        4. 返回所有专家的执行结果

        状态输入:
        - specific_agents_to_run: List[str] - 审核指定需要重新执行的专家（优先）
        - execution_batches: List[List[str]] - 所有批次的角色列表
        - current_batch: int - 当前批次编号（1-based）
        - agent_results: Dict - 已完成专家的结果

        返回:
        - Dict[str, Any] - 包含 agent_results 的状态更新
        """
        try:
            batch_start = time.time()

            #  优先检查是否有审核触发的重新执行
            specific_agents = state.get("specific_agents_to_run", [])

            if specific_agents:
                logger.info(f" 审核触发的重新执行: {len(specific_agents)} 个专家")
                logger.info(f"   专家列表: {specific_agents}")
                batch_roles = specific_agents
                current_batch = state.get("current_batch", 1)
                is_rerun = True
            else:
                # 正常批次执行
                batches = state.get("execution_batches", [])
                current_batch = state.get("current_batch", 1)
                total_batches = len(batches)

                logger.info(f" Batch executor: preparing batch {current_batch}/{total_batches}")

                # 验证批次编号
                if current_batch < 1 or current_batch > total_batches:
                    logger.error(f" Invalid batch number: {current_batch} (total: {total_batches})")
                    return {"errors": [f"Invalid batch number: {current_batch}"]}

                if not batches:
                    logger.error(" No execution_batches found in state")
                    return {"errors": ["No execution batches defined"]}

                # 获取当前批次的角色列表（0-indexed）
                batch_roles = batches[current_batch - 1]
                is_rerun = False

            display_roles = [format_role_display_name(r) for r in batch_roles]
            logger.info(f" [BatchParallel] 开始真并行执行: {len(batch_roles)} 个专家 {display_roles}")

            #  v8.2: 构建批次详情（前端动态步骤条）
            total_batches_for_detail = total_batches if not is_rerun else (state.get("total_batches") or len(batches))
            batch_detail = {
                "current_batch": current_batch,
                "total_batches": total_batches_for_detail,
                "batch_agents": batch_roles,
                "completed_agents": [],
                "active_agent": None,
                "batch_progress": 0.0,
            }

            #  v8.2: 推送批次开始消息
            session_id = state.get("session_id")
            if session_id:
                try:
                    from intelligent_project_analyzer.api._broadcast_registry import get_broadcast
                    broadcast_to_websockets = get_broadcast()
                    if not broadcast_to_websockets:
                        raise RuntimeError("broadcast_to_websockets not registered yet")

                    await broadcast_to_websockets(
                        session_id,
                        {
                            "type": "batch_started",
                            "batch_detail": batch_detail,
                            "timestamp": datetime.now().isoformat(),
                        },
                    )
                    logger.info(f"📡 [v8.2] 已推送批次开始消息: Batch{current_batch}/{total_batches_for_detail}")
                except Exception as broadcast_error:
                    logger.warning(f"️ [v8.2] WebSocket推送失败: {broadcast_error}")

            #  P0优化: 使用asyncio.gather真正并行执行
            tasks = []
            for role_id in batch_roles:
                # 为每个专家创建独立的状态副本
                agent_state = dict(state)
                agent_state["role_id"] = role_id
                agent_state["execution_batch"] = f"batch_{current_batch}"
                agent_state["current_stage"] = "parallel_analysis"
                agent_state["is_rerun"] = is_rerun

                #  P1优化: 传递批次信息供上下文压缩器使用
                agent_state["current_batch_number"] = current_batch
                agent_state["total_batches"] = total_batches if not is_rerun else len(batches)

                # 创建异步任务
                task = asyncio.create_task(self._execute_single_agent_with_timing(agent_state, role_id))
                tasks.append((role_id, task))

            #  真并行执行 - asyncio.gather
            logger.info(f" [BatchParallel] 启动 {len(tasks)} 个并行任务...")
            results = await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

            # 处理结果
            agent_results = {}
            successful = 0
            failed = 0

            for (role_id, _), result in zip(tasks, results):
                if isinstance(result, Exception):
                    logger.error(f" [BatchParallel] {role_id} 执行失败: {result}")
                    agent_results[role_id] = {
                        "role_id": role_id,
                        "error": str(result),
                        "analysis": f"执行失败: {result}",
                        "confidence": 0.0,
                    }
                    failed += 1
                else:
                    # 从结果中提取agent_results字段
                    if "agent_results" in result and role_id in result["agent_results"]:
                        agent_results[role_id] = result["agent_results"][role_id]
                        successful += 1
                    else:
                        logger.warning(f"️ [BatchParallel] {role_id} 结果格式异常")
                        agent_results[role_id] = result
                        failed += 1

                #  v8.2: 更新批次进度并推送
                batch_detail["completed_agents"].append(role_id)
                batch_detail["batch_progress"] = len(batch_detail["completed_agents"]) / len(batch_roles)

                if session_id:
                    try:
                        await broadcast_to_websockets(
                            session_id,
                            {
                                "type": "batch_progress",
                                "batch_detail": batch_detail,
                                "timestamp": datetime.now().isoformat(),
                            },
                        )
                        logger.debug(f"📊 [v8.2] 批次进度更新: {len(batch_detail['completed_agents'])}/{len(batch_roles)}")
                    except Exception as broadcast_error:
                        logger.warning(f"️ [v8.2] 进度推送失败: {broadcast_error}")

            batch_elapsed = time.time() - batch_start

            # 性能日志
            logger.info(f" [BatchParallel] Batch{current_batch} 完成:")
            logger.info(f"   - 总耗时: {batch_elapsed:.2f}s")
            logger.info(f"   - 成功: {successful}/{len(batch_roles)}")
            logger.info(f"   - 失败: {failed}/{len(batch_roles)}")
            theoretical_serial = batch_elapsed * len(batch_roles)
            logger.info(f"   - 平均延迟: {batch_elapsed/len(batch_roles):.2f}s/expert")
            logger.info(f"   -  加速比: {theoretical_serial/batch_elapsed:.1f}x (理论串行: {theoretical_serial:.2f}s)")

            # 详细日志
            for role_id in batch_roles:
                if role_id in agent_results:
                    result = agent_results[role_id]
                    analysis_len = len(result.get("analysis", ""))
                    confidence = result.get("confidence", 0.0)
                    logger.info(f"   - {role_id}: {analysis_len}字符, 置信度{confidence:.1%}")

            # 返回状态更新
            return {
                "agent_results": agent_results,
                "batch_elapsed_seconds": batch_elapsed,
                "batch_execution_detail": batch_detail,  #  v8.2: 批次执行详情
                "detail": f"批次 {current_batch} 完成：{successful}/{len(batch_roles)} 位专家",
            }

        except Exception as e:
            logger.error(f" Batch executor failed: {e}")
            import traceback

            traceback.print_exc()
            return {"errors": [str(e)]}

    async def _execute_single_agent_with_timing(self, agent_state: Dict[str, Any], role_id: str) -> Dict[str, Any]:
        """
         P0优化: 执行单个专家并记录耗时

        Args:
            agent_state: 专家状态
            role_id: 角色ID

        Returns:
            执行结果，格式: {"agent_results": {role_id: {...}}}
        """
        start = time.time()
        logger.info(f"▶️ [Agent] {role_id} 开始执行...")

        try:
            result = await self._execute_agent_node(agent_state)
            elapsed = time.time() - start
            logger.info(f" [Agent] {role_id} 完成，耗时 {elapsed:.2f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error(f" [Agent] {role_id} 失败，耗时 {elapsed:.2f}s: {e}")
            raise
            import traceback

            traceback.print_exc()
            return {"errors": [str(e)]}

    def _create_batch_sends(self, state: ProjectAnalysisState) -> List[Send]:
        """
        批次 Send 创建器 - 条件边函数，返回并行任务列表

         新增：专门负责创建 Send 对象的条件边函数，配合 _batch_executor_node 使用
         修复：支持审核触发的重新执行（specific_agents_to_run）

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
            logger.warning(f"️ No batches found, batches is None or empty")
            return []

        if current_batch < 1 or current_batch > len(batches):
            logger.warning(f"️ No valid batch to execute: current={current_batch}, total={len(batches)}")
            return []

        # 获取当前批次的角色列表（0-indexed）
        batch_roles = batches[current_batch - 1]

        if is_rerun:
            display_roles = [format_role_display_name(r) for r in batch_roles]
            logger.info(f" 创建重新执行任务: {len(batch_roles)} 个专家 {display_roles}")
        else:
            display_roles = [format_role_display_name(r) for r in batch_roles]
            logger.info(f" 创建批次 {current_batch} 任务: {len(batch_roles)} 个专家 {display_roles}")

        # 创建 Send 对象列表
        send_list = []
        for role_id in batch_roles:
            # 为每个智能体创建独立的状态副本
            agent_state = dict(state)
            agent_state["role_id"] = role_id
            agent_state["execution_batch"] = f"batch_{current_batch}"
            agent_state["current_stage"] = AnalysisStage.PARALLEL_ANALYSIS.value
            agent_state["is_rerun"] = is_rerun

            #  如果是重新执行，添加针对该专家的审核反馈
            if is_rerun and review_feedback:
                feedback_by_agent = review_feedback.get("feedback_by_agent", {})
                agent_feedback = feedback_by_agent.get(role_id, {})
                if agent_feedback:
                    agent_state["review_feedback_for_agent"] = agent_feedback
                    logger.info(f"   {role_id}: 附加审核反馈 ({len(agent_feedback.get('issues', []))} 个问题)")

            send_list.append(Send("agent_executor", agent_state))
            logger.debug(f"   Created Send for: {role_id}")

        logger.info(f" Created {len(send_list)} parallel tasks for batch {current_batch}")
        return send_list
