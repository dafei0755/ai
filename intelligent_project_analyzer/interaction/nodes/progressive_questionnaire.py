"""
三步递进式问卷节点

v7.80: 将问卷升级为「任务梳理 → 雷达图多维度画像 → 密度补齐追问」的三步递进式体验
v7.80.1: Step 1 升级为 LLM 驱动的智能任务拆解（从复述 → 明确）
v7.151: 流程优化，直接路由到 questionnaire_summary（需求洞察）

节点流程：
    requirements_analyst
        → progressive_step1_core_task
        → progressive_step2_radar
        → progressive_step3_gap_filling
        → questionnaire_summary  #  v7.151: 合并了 requirements_confirmation
"""

import asyncio
import copy
import json
from datetime import datetime
from typing import Any, Dict, List, Literal

from langgraph.store.base import BaseStore
from langgraph.types import Command, interrupt
from loguru import logger

from ...core.state import ProjectAnalysisState
from ...core.workflow_flags import WorkflowFlagManager
from ...services.capability_boundary_service import CapabilityBoundaryService, CheckType
from ...services.core_task_decomposer import (
    _simple_fallback_decompose,
    decompose_core_tasks,
    decompose_core_tasks_hybrid,
)
from ...services.dimension_selector import (
    DimensionSelector,
    RadarGapAnalyzer,
    select_dimensions_for_state,
)
from ...services.mode_question_loader import enrich_step1_payload_with_mode_questions
from ._oid_signal import PROJECTION_DISPLAY

# v8.2: 动态步骤追踪装饰器
from ...utils.node_tracker import track_active_step

# ── 节点路由常量（消除硬编码字符串，防止拼写错误）────────────────────────────────
_NODE_STEP1 = "progressive_step1_core_task"
_NODE_STEP2_RADAR = "progressive_step2_radar"
_NODE_STEP3_GAP = "progressive_step3_gap_filling"
_NODE_SUMMARY = "questionnaire_summary"
_NODE_DIRECTOR = "project_director"
_NODE_REQUIREMENTS = "requirements_analyst"


def _check_step1_quality(tasks: List[Dict[str, Any]]) -> List[str]:
    """
    Step 1 软质量校验（v8.1）

    返回警告信息列表（空列表 = 无问题）。警告仅供参考，不阻断流程。
    """
    warnings: List[str] = []
    if len(tasks) < 3:
        warnings.append("任务数量偏少（<3），建议补充细化")
    if tasks and not any(t.get("priority") == "high" for t in tasks):
        warnings.append("无高优先级任务，请确认是否遗漏核心任务")
    if any(not t.get("description") for t in tasks):
        warnings.append("部分任务缺少描述，可能影响后续搜索质量")
    return warnings


class ProgressiveQuestionnaireNode:
    """三步递进式问卷节点"""

    @staticmethod
    def _build_self_skip_decision(
        state: "ProjectAnalysisState",
        current_node: str,
        default_next: str,
    ) -> str:
        """
        基于 motivation_routing_profile 决定下一步节点。

        当 ENABLE_SMART_NODE_SELF_SKIP=false（默认）时，直接返回 default_next，
        行为与原来 100% 一致，无任何副作用。

        当 ENABLE_SMART_NODE_SELF_SKIP=true 时，读取 motivation_routing_profile
        中的 skip_candidates，根据当前节点决定是否跳过某步骤。

        Args:
            state: 当前工作流状态
            current_node: 当前节点名称（用于日志）
            default_next: 默认下一节点（未开启 self-skip 时的回退路径）

        Returns:
            下一节点名称字符串
        """
        from ...config.feature_flags import (
            ENABLE_SMART_NODE_SELF_SKIP,
            ENABLE_SMART_NODE_SELF_SKIP_SHADOW,
        )

        profile = state.get("motivation_routing_profile")

        # Shadow 模式：记录决策意图但不实际跳步
        if ENABLE_SMART_NODE_SELF_SKIP_SHADOW and profile:
            skip_candidates = profile.get("skip_candidates", [])
            routing_strategy = profile.get("routing_strategy", "full_flow")
            logger.info(
                f"[SelfSkip Shadow] node={current_node} strategy={routing_strategy} "
                f"skip_candidates={skip_candidates} default_next={default_next}"
            )

        # 未开启实跳，直接走默认路径
        if not ENABLE_SMART_NODE_SELF_SKIP or not profile:
            return default_next

        skip_candidates = profile.get("skip_candidates", [])
        routing_strategy = profile.get("routing_strategy", "full_flow")

        # Step1 完成后：是否跳过 gap_filling，直接进入 radar
        if current_node == _NODE_STEP1 and default_next == _NODE_STEP3_GAP:
            if "gap_filling" in skip_candidates and routing_strategy in ("skip_gap_filling", "skip_all_optional"):
                logger.info(f"[SelfSkip] node={current_node} → 跳过 gap_filling，直达 {_NODE_STEP2_RADAR}")
                return _NODE_STEP2_RADAR

        # Step3(gap_filling) 完成后：是否跳过 radar，直接进入 summary
        if current_node == _NODE_STEP3_GAP and default_next == _NODE_STEP2_RADAR:
            if "radar" in skip_candidates and routing_strategy in ("skip_radar", "skip_all_optional"):
                logger.info(f"[SelfSkip] node={current_node} → 跳过 radar，直达 {_NODE_SUMMARY}")
                return _NODE_SUMMARY

        return default_next

    # ==========================================================================
    # Step 1: 任务梳理（v7.80.1 智能拆解版）
    # ==========================================================================

    @staticmethod
    def step1_core_task(
        state: ProjectAnalysisState, store: BaseStore | None = None
    ) -> Command[
        Literal[
            "progressive_step2_radar",
            "progressive_step3_gap_filling",
            "questionnaire_summary",
            "project_director",
            "requirements_analyst",
        ]
    ]:
        """
        Step 1: 任务梳理

        v7.80.1: 使用 LLM 将用户输入拆解为结构化任务列表，让用户确认/调整/补充。

        Args:
            state: 项目分析状态
            store: 存储接口

        Returns:
            Command对象，指向下一个节点
        """
        logger.info("=" * 80)
        logger.info(" [v7.80.1 Step 1] 任务梳理")
        logger.info("=" * 80)

        # 检查是否已完成此步骤（使用新字段）
        if state.get("progressive_questionnaire_step", 0) >= 1 and state.get("confirmed_core_tasks"):
            logger.info(" Step 1 已完成，跳过")
            return Command(update={"progressive_questionnaire_step": 1}, goto=_NODE_STEP2_RADAR)

        # 追问模式跳过
        if state.get("is_followup"):
            logger.info(" Follow-up session, skipping progressive questionnaire")
            update_dict = {"progressive_questionnaire_completed": True, "progressive_questionnaire_step": 3}
            update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)
            return Command(update=update_dict, goto=_NODE_DIRECTOR)

        #  v7.80.1: 使用 LLM 拆解核心任务
        user_input = state.get("user_input", "")
        structured_data = state.get("agent_results", {}).get("requirements_analyst", {}).get("structured_data", {})

        #  v7.80.15 (P1.1): 诗意解读子流程
        poetic_metadata = None
        if _contains_poetic_expression(user_input):
            logger.info(" [诗意解读] 检测到诗意/哲学表达，启动诗意解读子流程")
            try:
                from concurrent.futures import ThreadPoolExecutor

                def _run_async_poetic_interpret(user_input: str):
                    """在独立线程中运行诗意解读"""
                    return asyncio.run(_llm_interpret_poetry(user_input))

                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_run_async_poetic_interpret, user_input)
                    poetic_metadata = future.result(timeout=30)  # 30秒超时

                logger.info(f" [诗意解读] 解读完成: {poetic_metadata.get('metaphor_explanation', '')[:50]}...")
            except Exception as e:
                logger.warning(f"️ [诗意解读] 解读失败: {e}，继续正常流程")
                poetic_metadata = None

        # 执行任务拆解
        # v7.80.1.2: 使用 ThreadPoolExecutor 在独立线程中运行 LLM 异步调用
        # 解决 LangGraph 异步上下文与 asyncio.run 不兼容的问题
        try:
            from concurrent.futures import ThreadPoolExecutor

            def _run_async_decompose(user_input: str, structured_data: dict):
                """在独立线程中运行异步任务拆解"""
                return asyncio.run(decompose_core_tasks_hybrid(user_input, structured_data))

            logger.info(" [v8.1] 使用 ThreadPoolExecutor 执行 hybrid 任务拆解")
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_run_async_decompose, user_input, structured_data)
                extracted_tasks = future.result(timeout=300)  # v8.1: 300秒超时

            if not extracted_tasks:
                logger.warning("️ LLM 任务拆解返回空列表，使用回退策略")
                extracted_tasks = _simple_fallback_decompose(user_input, structured_data)

        except Exception as e:
            logger.error(f" LLM 任务拆解失败: {e}")
            logger.info("️ 使用回退策略进行关键词匹配拆解")
            extracted_tasks = _simple_fallback_decompose(user_input, structured_data)

        logger.info(f" [v7.80.1] 拆解出 {len(extracted_tasks)} 个核心任务")
        for i, task in enumerate(extracted_tasks):
            logger.info(f"   {i+1}. {task.get('title', '未命名')}")

        # 同时保留旧格式（兼容性）
        old_format_task = ProgressiveQuestionnaireNode._extract_core_task(state)

        # 生成用户输入摘要
        user_input_summary = user_input[:100] + ("..." if len(user_input) > 100 else "")

        #  v8.1: 构建任务分组（按 category 聚合，供前端分组展示）
        task_groups: Dict[str, List[Dict[str, Any]]] = {}
        for task in extracted_tasks:
            cat = task.get("category", "调研分析")
            task_groups.setdefault(cat, []).append(task)

        #  v8.1: 构建意图识别展示（基于 active_projections + PROJECTION_DISPLAY）
        intent_review: Dict[str, Any] = {}
        active_projections = state.get("active_projections") or []
        if active_projections:
            projection_labels = [
                PROJECTION_DISPLAY.get(p, {}).get("label", p)
                for p in active_projections
                if p in PROJECTION_DISPLAY
            ]
            detected_modes = state.get("detected_identity_modes") or []
            framework_signals = state.get("output_framework_signals") or []
            intent_review = {
                "projections": projection_labels,
                "identity_modes": detected_modes[:3],
                "framework_signals": framework_signals[:3],
            }

        #  v8.1: 构建 interrupt payload
        payload = {
            "interaction_type": "progressive_questionnaire_step1",
            "step": 1,
            "total_steps": 3,
            "title": "任务梳理",
            "message": "系统已从您的描述中识别以下核心任务，请确认、调整或补充",
            #  v8.1 新字段
            "extracted_tasks": extracted_tasks,
            "task_groups": task_groups,
            "intent_review": intent_review,
            "user_input_summary": user_input_summary,
            # 旧字段：保留兼容
            "extracted_task": old_format_task,
            "editable": True,
            "options": {"confirm": "确认任务列表", "skip": "跳过问卷"},
        }

        #  v8.1: 注入模式问题滚内容
        try:
            payload = enrich_step1_payload_with_mode_questions(state, payload)
        except Exception as _eq:
            logger.warning(f"️ [v8.1] enrich_step1_payload 失败，跳过: {_eq}")

        logger.info(" [Step 1] 即将调用 interrupt()，等待用户输入...")
        user_response = interrupt(payload)
        logger.info(f" [Step 1] 收到用户响应: {type(user_response)}")

        #  v7.401: interrupt()返回后立即检查状态（防止并发重复执行）
        # 竞态条件检测：如果在interrupt期间其他线程已完成Step 1，则跳过
        if state.get("progressive_questionnaire_step", 0) >= 1 and state.get("confirmed_core_tasks"):
            logger.warning("️ [v7.401 并发检测] Step 1 已在interrupt期间被其他线程完成，跳过重复执行")
            logger.info(f"   当前state['progressive_questionnaire_step'] = {state.get('progressive_questionnaire_step')}")
            logger.info(f"   当前state['confirmed_core_tasks'] 数量 = {len(state.get('confirmed_core_tasks', []))}")
            return Command(update={"progressive_questionnaire_step": 1}, goto=_NODE_STEP2_RADAR)

        #  v7.80.1: 解析用户响应（支持新旧格式）
        confirmed_tasks = extracted_tasks
        confirmed_task = old_format_task
        skip_requested = False

        if isinstance(user_response, dict):
            if user_response.get("action") == "skip" or user_response.get("intent") == "skip":
                skip_requested = True
            else:
                # 优先使用新格式
                if "confirmed_tasks" in user_response:
                    confirmed_tasks = user_response["confirmed_tasks"]
                elif "tasks" in user_response:
                    confirmed_tasks = user_response["tasks"]

                # 兼容旧格式
                if "confirmed_task" in user_response:
                    confirmed_task = user_response["confirmed_task"]
                elif "task" in user_response:
                    confirmed_task = user_response["task"]

        elif isinstance(user_response, str):
            if user_response.strip().lower() in {"skip", "跳过", "取消"}:
                skip_requested = True
            elif user_response.strip():
                confirmed_task = user_response.strip()

        if skip_requested:
            logger.info("️ 用户跳过问卷")

            #  v7.87 P0: 设置默认 questionnaire_summary
            timestamp_now = datetime.now().isoformat()
            default_questionnaire_summary = {
                "skipped": True,
                "reason": "user_skip_step1",
                "entries": [],
                "answers": {},
                "timestamp": timestamp_now,
                "submitted_at": timestamp_now,
                "source": "progressive_step1_skip",
            }

            update_dict = {
                "progressive_questionnaire_completed": True,
                "progressive_questionnaire_step": 3,
                # 新字段
                "extracted_core_tasks": extracted_tasks,
                "confirmed_core_tasks": extracted_tasks,
                "core_task_summary": ProgressiveQuestionnaireNode._build_task_summary(extracted_tasks),
                # 旧字段（兼容）
                "extracted_core_task": old_format_task,
                "confirmed_core_task": old_format_task,
                #  v7.87 P0: 默认 questionnaire_summary
                "questionnaire_summary": default_questionnaire_summary,
                "questionnaire_responses": default_questionnaire_summary,
            }
            logger.info("️ [v7.87 P0] 已设置默认 questionnaire_summary（Step 1跳过）")

            update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)
            return Command(update=update_dict, goto=_NODE_DIRECTOR)

        # 构建任务摘要
        task_summary = ProgressiveQuestionnaireNode._build_task_summary(confirmed_tasks)

        #  能力边界检查：检查用户确认的任务是否在能力范围内
        logger.info(" [CapabilityBoundary] 检查Step1确认任务的能力边界")
        task_texts = []
        for task in confirmed_tasks:
            task_text = task.get("description", "") or task.get("title", "")
            if task_text:
                task_texts.append(task_text)

        combined_text = "\n".join(task_texts)

        if combined_text:
            boundary_check = CapabilityBoundaryService.check_user_input(
                user_input=combined_text,
                context={
                    "node": "progressive_step1",
                    "task_count": len(confirmed_tasks),
                    "session_id": state.get("session_id", ""),
                },
                check_type=CheckType.DELIVERABLE_ONLY,
            )

            logger.info(" 任务能力边界检查结果:")
            logger.info(f"   在能力范围内: {boundary_check.within_capability}")
            logger.info(f"   能力匹配度: {boundary_check.capability_score:.2f}")

            # 标记有风险的任务
            if not boundary_check.within_capability:
                logger.warning("️ 部分任务可能超出能力范围")

                # 为每个任务检查是否包含超范围关键词
                for i, task in enumerate(confirmed_tasks):
                    task_desc = task.get("description", "") or task.get("title", "")

                    # 检查是否匹配到超出能力的交付物
                    has_capability_issue = False
                    suggested_transform = None

                    for check in boundary_check.deliverable_checks:
                        if not check.within_capability:
                            # 检查任务描述中是否包含超范围关键词
                            for keyword in check.detected_keywords:
                                if keyword.lower() in task_desc.lower():
                                    has_capability_issue = True
                                    suggested_transform = check.transformed_type
                                    logger.info(f"   ️ 任务 {i+1} 包含超范围关键词: '{keyword}'")
                                    break
                            if has_capability_issue:
                                break

                    if has_capability_issue:
                        confirmed_tasks[i]["capability_warning"] = True
                        confirmed_tasks[i]["warning_reason"] = "可能超出系统能力范围"
                        if suggested_transform:
                            confirmed_tasks[i]["suggested_transform"] = suggested_transform
                            logger.info(f"     建议转化为: {suggested_transform}")
            else:
                logger.info(" 所有任务在能力范围内")

        logger.info(f" [Step 1] 确认 {len(confirmed_tasks)} 个核心任务")

        #  v7.80.15 (P1.2): 检测特殊场景
        from ...services.task_completeness_analyzer import TaskCompletenessAnalyzer

        analyzer = TaskCompletenessAnalyzer()
        special_scenarios = analyzer.detect_special_scenarios(user_input, task_summary)

        special_scene_metadata = None
        if special_scenarios:
            # 构建场景元数据
            scene_tags = list(special_scenarios.keys())
            matched_keywords = {}
            for scene_id, scene_info in special_scenarios.items():
                matched_keywords[scene_id] = scene_info.get("matched_keywords", [])

            special_scene_metadata = {
                "scene_tags": scene_tags,
                "matched_keywords": matched_keywords,
                "trigger_messages": {
                    scene_id: info.get("trigger_message", "") for scene_id, info in special_scenarios.items()
                },
            }
            logger.info(f" [Step 1] 识别特殊场景: {scene_tags}")

        update_dict = {
            #  v7.80.1 新字段
            "extracted_core_tasks": extracted_tasks,
            "confirmed_core_tasks": confirmed_tasks,
            "core_task_summary": task_summary,
            # 旧字段（兼容）
            "extracted_core_task": old_format_task,
            "confirmed_core_task": confirmed_task if confirmed_task != old_format_task else task_summary,
            "progressive_questionnaire_step": 1,
            #  v7.80.15 (P1.1): 诗意解读元数据
            "poetic_metadata": poetic_metadata,
            #  v7.80.15 (P1.2): 特殊场景元数据
            "special_scene_metadata": special_scene_metadata,
            #  能力边界检查记录（ v7.147: 转换为dict避免序列化错误）
            "step1_boundary_check": boundary_check.to_dict() if (combined_text and boundary_check) else None,
            #  v8.1: 快照 + 软质量校验
            "step1_confirmed_tasks_snapshot": copy.deepcopy(confirmed_tasks),
            "step1_quality_warnings": _check_step1_quality(confirmed_tasks),
        }
        update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)

        #  v7.146: 修正路由顺序 - Step1 → Step2(信息补全)
        #  v8.4: 双动机驱动 — 根据 motivation_routing_profile 决定是否跳过 gap_filling
        _next = ProgressiveQuestionnaireNode._build_self_skip_decision(state, _NODE_STEP1, default_next=_NODE_STEP3_GAP)
        return Command(update=update_dict, goto=_next)

    # ==========================================================================
    # Step 2: 雷达图维度
    # ==========================================================================

    @staticmethod
    def step2_radar(
        state: ProjectAnalysisState, store: BaseStore | None = None
    ) -> Command[
        Literal["progressive_step2_radar", "progressive_step3_gap_filling", "questionnaire_summary", "project_director"]
    ]:
        """
        Step 2: 雷达图多维度偏好收集

         v7.151: 路由目标从 requirements_confirmation 改为 questionnaire_summary

        展示9-12个维度滑块，让用户表达设计偏好。

        Args:
            state: 项目分析状态
            store: 存储接口

        Returns:
            Command对象，指向下一个节点
        """
        logger.info("=" * 80)
        logger.info(" [v7.80 Step 2] 雷达图维度收集")
        logger.info("=" * 80)

        # 检查是否已完成此步骤
        if state.get("progressive_questionnaire_step", 0) >= 2 and state.get("radar_dimension_values"):
            logger.info(" Step 2 已完成，跳过")
            return Command(update={"progressive_questionnaire_step": 2}, goto=_NODE_SUMMARY)

        #  v7.80.4: 动态维度选择 + 智能生成
        #  v7.110: 集成混合策略 AdaptiveDimensionGenerator
        import os

        from ...services.adaptive_dimension_generator import AdaptiveDimensionGenerator
        from ...services.dynamic_dimension_generator import DynamicDimensionGenerator

        #  v7.80.5: 强制生成模式（用于测试/演示）
        FORCE_GENERATE = os.getenv("FORCE_GENERATE_DIMENSIONS", "false").lower() == "true"

        #  v7.80.16: 动态生成开关（v7.150: 默认启用，实现真正的智能维度生成）
        USE_DYNAMIC_GENERATION = os.getenv("USE_DYNAMIC_GENERATION", "true").lower() == "true"

        #  v7.110: 智能学习开关
        ENABLE_DIMENSION_LEARNING = os.getenv("ENABLE_DIMENSION_LEARNING", "false").lower() == "true"

        #  v7.117: 增强调试日志，排查智能维度问题
        logger.info(f" [Step 2 环境变量] FORCE_GENERATE_DIMENSIONS={FORCE_GENERATE}")
        logger.info(f" [Step 2 环境变量] USE_DYNAMIC_GENERATION={USE_DYNAMIC_GENERATION}")
        logger.info(f" [Step 2 环境变量] ENABLE_DIMENSION_LEARNING={ENABLE_DIMENSION_LEARNING}")

        #  v7.146: 定义默认维度作为降级方案
        def _get_default_dimensions():
            """获取静态默认维度列表（降级方案）

            注意：v7.139+ select_dimensions_for_state 可能返回 dict（包含 dimensions/conflicts/...）。
            这里必须保证返回值始终为 list，避免前端收到对象导致雷达图无法渲染。
            """
            from ...services.dimension_selector import select_dimensions_for_state

            logger.info("️ [降级] 使用静态默认维度列表")
            result = select_dimensions_for_state(state)
            if isinstance(result, dict):
                dims = result.get("dimensions", [])
                if isinstance(dims, list):
                    return dims
                return []
            return result

        # Step 2.0: v8.0 项目专属维度生成（最高优先级）
        #  v8.0: 当 USE_PROJECT_SPECIFIC_DIMENSIONS=true 时，优先使用 ProjectSpecificDimensionGenerator
        USE_PROJECT_SPECIFIC_DIMENSIONS = os.getenv("USE_PROJECT_SPECIFIC_DIMENSIONS", "false").lower() == "true"
        _v8_generation_result: dict = {}  # 存储 v8.0 生成结果（含 generation_summary）

        if USE_PROJECT_SPECIFIC_DIMENSIONS:
            logger.info("🎯 [v8.0] USE_PROJECT_SPECIFIC_DIMENSIONS=true，尝试项目专属维度生成")
            try:
                from ...services.project_specific_dimension_generator import (
                    ProjectSpecificDimensionGenerator,
                )

                ps_generator = ProjectSpecificDimensionGenerator()
                agent_results_v8 = state.get("agent_results", {})
                requirements_result_v8 = agent_results_v8.get("requirements_analyst", {})
                structured_data_v8 = requirements_result_v8.get("structured_data", {})
                confirmed_tasks_v8 = state.get("confirmed_core_tasks", [])

                _v8_generation_result = ps_generator.generate_dimensions(
                    user_input=state.get("user_input", ""),
                    structured_data=structured_data_v8,
                    confirmed_tasks=confirmed_tasks_v8,
                    project_type=state.get("project_type", ""),
                )

                if _v8_generation_result.get("dimensions") and len(_v8_generation_result["dimensions"]) >= 5:
                    # v8.0 成功：直接使用 ProjectSpecificDimensionGenerator 结果
                    _ps_dims = _v8_generation_result["dimensions"]
                    logger.info(f"🎯 [v8.0] 项目专属维度生成成功：{len(_ps_dims)} 个维度")
                    dimension_generation_method = "project_specific"

                    # 按 source/category 分组 dimension_layers（用于前端分层展示）
                    dimension_layers: dict = {}
                    for _d in _ps_dims:
                        _src = _d.get("source") or _d.get("category") or "other"
                        dimension_layers.setdefault(_src, []).append(_d)

                    # 构建 interrupt payload
                    confirmed_task_v8 = state.get("confirmed_core_task", "")
                    user_input_v8 = state.get("user_input", "")
                    user_input_summary_v8 = user_input_v8[:100] + ("..." if len(user_input_v8) > 100 else "")
                    payload_v8 = {
                        "interaction_type": "progressive_questionnaire_step3",
                        "step": 3,
                        "total_steps": 3,
                        "title": "多维度偏好设置",
                        "message": "请通过拖动滑块表达您的设计偏好。每个维度代表两种不同的设计方向。",
                        "core_task": confirmed_task_v8,
                        "dimensions": _ps_dims,
                        "dimension_layers": dimension_layers,
                        "dimension_generation_method": dimension_generation_method,
                        "generation_summary": _v8_generation_result.get("generation_summary", ""),
                        "instructions": "拖动滑块到您偏好的位置（0-100）",
                        "user_input": user_input_v8,
                        "user_input_summary": user_input_summary_v8,
                        "options": {"confirm": "确认偏好设置", "back": "返回修改核心任务"},
                    }

                    logger.info("🎯 [v8.0] 即将调用 interrupt()，等待用户输入...")
                    user_response_v8 = interrupt(payload_v8)

                    # 解析用户响应
                    dimension_values_v8: dict = {}
                    if isinstance(user_response_v8, dict):
                        dimension_values_v8 = (
                            user_response_v8.get("values") or user_response_v8.get("dimension_values") or {}
                        )
                        if not dimension_values_v8:
                            for k, v in user_response_v8.items():
                                if k in [d["id"] for d in _ps_dims] and isinstance(v, int | float):
                                    dimension_values_v8[k] = int(v)

                    if not dimension_values_v8:
                        dimension_values_v8 = {d["id"]: d.get("default_value", 50) for d in _ps_dims}

                    analyzer_v8 = RadarGapAnalyzer()
                    analysis_v8 = analyzer_v8.analyze(dimension_values_v8, _ps_dims)

                    update_dict_v8 = {
                        "selected_radar_dimensions": _ps_dims,
                        "selected_dimensions": _ps_dims,
                        "radar_dimension_values": dimension_values_v8,
                        "radar_analysis_summary": analysis_v8,
                        "progressive_questionnaire_step": 2,
                        "dimension_generation_method": dimension_generation_method,
                    }
                    update_dict_v8 = WorkflowFlagManager.preserve_flags(state, update_dict_v8)

                    logger.info("🎯 [v8.0] 项目专属维度完成，路由到 questionnaire_summary")
                    return Command(update=update_dict_v8, goto=_NODE_SUMMARY)
                else:
                    logger.warning("🎯 [v8.0] 项目专属维度不足（< 5），降级到传统流程")
                    dimension_generation_method = "static"
            except Exception as _e_v8:
                logger.error(f"🎯 [v8.0] ProjectSpecificDimensionGenerator 异常: {_e_v8}，降级到传统流程")
                dimension_generation_method = "static"
        else:
            dimension_generation_method = "static"
            logger.info("🎯 [v8.0] USE_PROJECT_SPECIFIC_DIMENSIONS=false，使用传统维度选择")

        # Step 2.1: 智能维度选择（混合策略）
        #  v7.146: 添加异常处理和超时保护
        existing_dimensions = []
        try:
            if ENABLE_DIMENSION_LEARNING:
                logger.info(" [维度选择] 使用 AdaptiveDimensionGenerator 混合策略")
                # 使用学习优化的混合策略生成器
                adaptive_generator = AdaptiveDimensionGenerator()

                #  v7.117: 从 Redis 加载历史维度数据（用于学习优化）
                historical_data = []
                try:
                    from concurrent.futures import ThreadPoolExecutor

                    from ...services.redis_session_manager import RedisSessionManager

                    def _load_historical_data():
                        """在独立线程中加载历史数据"""
                        import asyncio

                        session_manager = RedisSessionManager()

                        async def _async_load():
                            await session_manager.connect()
                            data = await session_manager.get_dimension_historical_data(limit=100)
                            return data

                        return asyncio.run(_async_load())

                    logger.info(" [v7.117] 正在加载历史维度数据...")
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(_load_historical_data)
                        historical_data = future.result(timeout=10)  # 10秒超时

                    logger.info(f" [历史数据] 成功加载 {len(historical_data)} 条记录")

                except Exception as e:
                    logger.warning(f"️ [历史数据] 加载失败: {e}，使用空列表继续")
                    historical_data = []

                # 检测特殊场景
                special_scene_metadata = state.get("special_scene_metadata")
                special_scenes = None
                if special_scene_metadata:
                    special_scenes = special_scene_metadata.get("scene_tags", [])

                result = adaptive_generator.select_for_project(
                    project_type=state.get("project_type", "personal_residential"),
                    user_input=state.get("user_input", ""),
                    min_dimensions=9,
                    max_dimensions=12,
                    special_scenes=special_scenes,
                    historical_data=historical_data,
                )

                #  v7.146: 兼容 v7.139 字典返回格式
                if isinstance(result, dict):
                    existing_dimensions = result.get("dimensions", [])
                    logger.info(f" [AdaptiveDimGen] v7.139格式: 选择了 {len(existing_dimensions)} 个智能维度")
                else:
                    existing_dimensions = result
                    logger.info(f" [AdaptiveDimGen] 选择了 {len(existing_dimensions)} 个智能维度")
            else:
                logger.info(" [维度选择] 使用传统 RuleEngine 规则引擎（ENABLE_DIMENSION_LEARNING=false）")
                # 使用传统规则引擎
                result = select_dimensions_for_state(state)
                #  v7.146: 兼容 v7.139 字典返回格式
                if isinstance(result, dict):
                    existing_dimensions = result.get("dimensions", [])
                else:
                    existing_dimensions = result
                logger.info(f" [RuleEngine] 选择了 {len(existing_dimensions)} 个传统维度")
        except Exception as e:
            #  v7.146: 维度选择失败时使用降级方案
            logger.error(f" [维度选择失败] {type(e).__name__}: {str(e)}")
            logger.error(f" [堆栈信息] {__import__('traceback').format_exc()}")
            logger.warning("️ [降级策略] 使用默认维度列表继续流程")
            existing_dimensions = _get_default_dimensions()

        logger.info(f" 已选择 {len(existing_dimensions)} 个现有维度")

        #  v7.150: 增强日志，追踪每个维度的来源
        for dim in existing_dimensions[:5]:  # 只显示前5个，避免日志过长
            source = dim.get("source", "static")
            recommended_by_llm = dim.get("recommended_by_llm", False)
            source_label = "LLM推荐" if recommended_by_llm else source
            logger.info(f"    维度: {dim.get('name', dim.get('id', 'unknown'))} (来源: {source_label})")
        if len(existing_dimensions) > 5:
            logger.info(f"   ... 还有 {len(existing_dimensions) - 5} 个维度")

        # Step 2.2: 分析覆盖度，必要时生成新维度
        user_input = state.get("user_input", "")
        agent_results = state.get("agent_results", {})
        requirements_result = agent_results.get("requirements_analyst", {})
        structured_data = requirements_result.get("structured_data", {})

        generator = DynamicDimensionGenerator()
        dimensions = existing_dimensions
        generated_count = 0

        if FORCE_GENERATE:
            #  强制生成模式：跳过覆盖度检查，直接生成
            logger.info(" [动态维度] 强制生成模式已启用")
            missing_aspects = ["用户独特需求", "项目特色要求"]

            #  v7.106: 传递existing_dimensions给generator
            structured_data_with_dims = {**structured_data, "existing_dimensions": existing_dimensions}

            new_dimensions = generator.generate_dimensions(
                user_input,
                structured_data_with_dims,
                missing_aspects,
                target_count=min(2, 12 - len(existing_dimensions)),  # 强制模式生成2个
            )

            if new_dimensions:
                dimensions = existing_dimensions + new_dimensions
                generated_count = len(new_dimensions)
                logger.info(f" [动态维度] 强制新增 {generated_count} 个定制维度")
                for dim in new_dimensions:
                    logger.info(f"   + {dim['name']}: {dim['left_label']} ← → {dim['right_label']}")
        elif USE_DYNAMIC_GENERATION:
            # 正常模式：基于覆盖度分析（仅在环境变量启用时）
            logger.info(" [动态维度] LLM覆盖度分析已启用")
            coverage = generator.analyze_coverage(user_input, structured_data, existing_dimensions)

            #  v7.154: 增强日志，追踪覆盖度分析结果
            logger.info(
                f" [覆盖度分析] coverage_score={coverage.get('coverage_score', 'N/A')}, "
                f"should_generate={coverage.get('should_generate', False)}, "
                f"missing_aspects={coverage.get('missing_aspects', [])}"
            )

            #  v7.154: 增强条件判断 - 降级模式也触发生成
            analysis_text = coverage.get("analysis", "")
            is_fallback_mode = "降级" in analysis_text or "失败" in analysis_text
            should_generate = coverage.get("should_generate", False)
            has_missing_aspects = bool(coverage.get("missing_aspects"))

            if (should_generate and has_missing_aspects) or is_fallback_mode:
                logger.info(f" [动态维度] 检测到覆盖不足 (评分: {coverage.get('coverage_score', 0):.2f})")
                logger.info(f"   缺失方面: {coverage.get('missing_aspects', [])}")

                #  v7.106: 传递existing_dimensions给generator
                structured_data_with_dims = {**structured_data, "existing_dimensions": existing_dimensions}

                # 生成新维度
                new_dimensions = generator.generate_dimensions(
                    user_input,
                    structured_data_with_dims,
                    coverage.get("missing_aspects", []),
                    target_count=min(3, 12 - len(existing_dimensions)),  # 确保总数不超过12
                )

                if new_dimensions:
                    dimensions = existing_dimensions + new_dimensions
                    generated_count = len(new_dimensions)
                    logger.info(f" [动态维度] 新增 {generated_count} 个定制维度")
                    for dim in new_dimensions:
                        logger.info(f"   + {dim['name']}: {dim['left_label']} ← → {dim['right_label']}")
        else:
            #  v7.80.16: 默认禁用LLM调用，仅使用P0.3场景注入
            logger.info(" [性能优化] 跳过LLM动态生成，使用P0.3场景注入机制")

        #  v7.80.15 (P1.3): 基于特殊场景注入专用维度
        #  v7.146: 添加异常处理，防止注入失败阻塞流程
        special_scene_metadata = state.get("special_scene_metadata")
        confirmed_tasks = state.get("confirmed_core_tasks", [])

        if special_scene_metadata or confirmed_tasks:
            try:
                from ...services.dimension_selector import DimensionSelector

                selector = DimensionSelector()

                # 调用场景检测和维度注入
                result = selector.detect_and_inject_specialized_dimensions(
                    user_input=user_input,
                    confirmed_tasks=confirmed_tasks,
                    current_dimensions=dimensions,
                    special_scene_metadata=special_scene_metadata,
                )

                #  v7.146: 兼容 v7.139 字典返回格式
                if isinstance(result, dict):
                    dimensions = result.get("dimensions", dimensions)
                    logger.info(f" [特殊场景] v7.139格式: 维度注入完成，最终 {len(dimensions)} 个维度")
                else:
                    dimensions = result
                    logger.info(f" [特殊场景] 维度注入完成: 最终 {len(dimensions)} 个维度")
            except Exception as e:
                #  v7.146: 注入失败时保留当前维度
                logger.error(f" [特殊场景注入失败] {type(e).__name__}: {str(e)}")
                logger.warning(f"️ [降级] 保留当前维度列表: {len(dimensions)} 个维度")

        logger.info(f" 最终维度数量: {len(dimensions)} ({len(existing_dimensions)} 现有 + {generated_count} 动态生成)")

        # 获取确认的核心任务
        confirmed_task = state.get("confirmed_core_task", "")

        #  v7.115: 获取用户原始输入，用于前端显示需求摘要
        user_input = state.get("user_input", "")
        user_input_summary = user_input[:100] + ("..." if len(user_input) > 100 else "")

        #  v7.146: 确保 dimensions 是列表格式
        if not isinstance(dimensions, list):
            logger.error(f" [payload构建] dimensions 不是列表，类型: {type(dimensions)}, 使用降级维度")
            dimensions = _get_default_dimensions()

            #  v7.146.1: 降级后再次校验，强制解包 v7.139 dict 格式
            if isinstance(dimensions, dict):
                logger.warning("️ [降级后] dimensions 仍为 dict，强制提取 dimensions 字段")
                dimensions = dimensions.get("dimensions", [])
            if not isinstance(dimensions, list):
                logger.error(f" [降级失败] dimensions 最终仍非列表: {type(dimensions)}，使用空列表")
                dimensions = []

        # 构建interrupt payload
        #  v7.146: 修正事件类型，step2_radar函数对应前端第3步（雷达图）
        payload = {
            "interaction_type": "progressive_questionnaire_step3",
            "step": 3,
            "total_steps": 3,
            "title": "多维度偏好设置",
            "message": "请通过拖动滑块表达您的设计偏好。每个维度代表两种不同的设计方向。",
            "core_task": confirmed_task,
            "dimensions": dimensions,
            "instructions": "拖动滑块到您偏好的位置（0-100）",
            #  v7.115: 添加用户需求信息，供前端顶部显示
            "user_input": user_input,
            "user_input_summary": user_input_summary,
            "options": {"confirm": "确认偏好设置", "back": "返回修改核心任务"},
            #  v8.0: 维度生成方法标识（传统路径固定为 static）
            "dimension_generation_method": dimension_generation_method,
            "dimension_layers": {
                src: [d for d in dimensions if (d.get("source") or d.get("category") or "other") == src]
                for src in dict.fromkeys((d.get("source") or d.get("category") or "other") for d in dimensions)
            },
            "generation_summary": "",
        }

        logger.info(" [Step 2] 即将调用 interrupt()，等待用户输入...")
        logger.info(f" [payload验证] dimensions类型: {type(dimensions)}, 长度: {len(dimensions)}")
        user_response = interrupt(payload)
        logger.info(f" [Step 2] 收到用户响应: {type(user_response)}")

        # 解析用户响应
        dimension_values = {}
        #  v7.87: 移除返回上一步功能

        if isinstance(user_response, dict):
            #  v7.87: 移除 action == "back" 处理
            dimension_values = user_response.get("values") or user_response.get("dimension_values") or {}
            # 如果没有values字段，尝试直接从响应中提取
            if not dimension_values:
                for key, value in user_response.items():
                    if key in [d["id"] for d in dimensions] and isinstance(value, int | float):
                        dimension_values[key] = int(value)

        # 如果用户没有设置任何值，使用默认值
        if not dimension_values:
            logger.warning("️ 用户未设置任何维度值，使用默认值")
            dimension_values = {d["id"]: d.get("default_value", 50) for d in dimensions}

        logger.info(f" [Step 2] 收集到 {len(dimension_values)} 个维度值")

        # 分析雷达图
        analyzer = RadarGapAnalyzer()
        analysis = analyzer.analyze(dimension_values, dimensions)

        update_dict = {
            "selected_radar_dimensions": dimensions,
            "selected_dimensions": dimensions,  #  兼容 questionnaire_summary 读取
            "radar_dimension_values": dimension_values,
            "radar_analysis_summary": analysis,
            "progressive_questionnaire_step": 2,
            "dimension_generation_method": dimension_generation_method,  #  v8.0: 维度生成方法标识
        }
        update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)

        #  v7.146: 修正路由 - Step3(雷达图)完成后进入需求洞察
        logger.info(" [Step 3] 雷达图维度收集完成，准备进入需求洞察")

        # 保存雷达图分析结果
        gap_dimensions = analysis.get("gap_dimensions", [])
        if gap_dimensions:
            logger.info(f"   雷达图短板维度: {gap_dimensions}")

        # 直接进入需求洞察节点
        return Command(update=update_dict, goto=_NODE_SUMMARY)

    # ==========================================================================
    # Step 3: 密度补齐追问
    # ==========================================================================

    @staticmethod
    def step3_gap_filling(
        state: ProjectAnalysisState, store: BaseStore | None = None
    ) -> Command[Literal["progressive_step2_radar", "questionnaire_summary", "project_director"]]:
        """
        Step 3: 核心任务信息完整性查漏补缺

         v7.151: 路由目标从 requirements_confirmation 改为 questionnaire_summary

        v7.80.6: 从"雷达图补充"转变为"任务信息完整性检查"
        - 分析核心任务是否包含足够信息
        - 识别缺失的关键维度（6大维度）
        - 生成针对性、导向性、敏感性的补充问题

        Args:
            state: 项目分析状态
            store: 存储接口

        Returns:
            Command对象，指向下一个节点
        """
        logger.info("=" * 80)
        logger.info(" [v7.80.6 Step 3] 核心任务信息完整性查漏补缺")
        logger.info("=" * 80)

        # 检查是否已完成此步骤
        if state.get("progressive_questionnaire_completed"):
            logger.info(" 问卷已完成，跳过 Step 3")
            return Command(update={"progressive_questionnaire_step": 3}, goto=_NODE_DIRECTOR)

        #  v7.80.6: 针对核心任务进行信息完整性分析
        from ...services.task_completeness_analyzer import TaskCompletenessAnalyzer

        # 获取核心任务和相关数据
        confirmed_tasks = state.get("confirmed_core_tasks", [])
        user_input = state.get("user_input", "")
        agent_results = state.get("agent_results", {})
        requirements_result = agent_results.get("requirements_analyst", {})
        structured_data = requirements_result.get("structured_data", {})

        # 执行任务完整性分析
        analyzer = TaskCompletenessAnalyzer()
        completeness = analyzer.analyze(confirmed_tasks, user_input, structured_data)

        logger.info(f" 任务信息完整性评分: {completeness.get('completeness_score', 0):.2f}")
        logger.info(f"   已覆盖维度: {completeness.get('covered_dimensions', [])}")
        logger.info(f"   缺失维度: {completeness.get('missing_dimensions', [])}")
        logger.info(f"   关键缺失点: {completeness.get('critical_gaps', [])}")

        # 判断是否需要补充问题
        critical_gaps = completeness.get("critical_gaps", [])

        # v7.900 G1: 合并 uncertainty_map 到 critical_gaps
        _uncertainty_map = (structured_data or {}).get("uncertainty_map", {})
        if isinstance(_uncertainty_map, dict) and _uncertainty_map:
            _existing_dims = {g.get("dimension") for g in critical_gaps}
            for _dim, _level in _uncertainty_map.items():
                if _level in ("high", "medium") and _dim not in _existing_dims:
                    critical_gaps.append({
                        "dimension": _dim,
                        "reason": f"需求分析阶段识别为{_level}不确定性维度",
                        "priority": _level,
                        "source": "uncertainty_map",
                    })
                    _existing_dims.add(_dim)
            logger.info(f" [G1] uncertainty_map 补充 {len(_uncertainty_map)} 条，critical_gaps 现有 {len(critical_gaps)} 条")

        # v7.900 G8: active_projections 已确认时自动覆盖"交付要求"维度，避免重复追问
        _active_projections = state.get("active_projections") or []
        if _active_projections:
            critical_gaps = [g for g in critical_gaps if g.get("dimension") != "交付要求"]
            _covered = completeness.get("covered_dimensions") or []
            if "交付要求" not in _covered:
                completeness.setdefault("covered_dimensions", []).append("交付要求")
            _missing = completeness.get("missing_dimensions") or []
            completeness["missing_dimensions"] = [d for d in _missing if d != "交付要求"]
            logger.info(f" [G8] active_projections 已设{_active_projections}，'交付要求' 维度已自动覆盖")

        if not critical_gaps:
            # v8.3 G4: 当 completeness_score 低或 missing_dims 多时，生成兜底追问
            _score = completeness.get("completeness_score", 0)
            _missing_dims = completeness.get("missing_dimensions", [])
            if _score < 0.7 or len(_missing_dims) > 2:
                for _dim in _missing_dims[:5]:
                    critical_gaps.append({
                        "dimension": _dim,
                        "reason": f"完整度不足({int(_score * 100)}%)，需补充{_dim}信息",
                        "priority": "medium",
                        "source": "fallback_v8.3",
                    })
                logger.info(f" [G4] v8.3 兜底注入 {len(critical_gaps)} 条，score={_score:.2f}")

        if not critical_gaps:
            logger.info(" 任务信息完整，无需补充，跳过问题生成，直接进入雷达图")
            update_dict = {
                "progressive_questionnaire_completed": False,  # 还未完全完成，需要进行雷达图
                "progressive_questionnaire_step": 2,
                "task_completeness_analysis": completeness,  # 保存分析结果
                # LT-3: gap_filling_answers 合并到 questionnaire_responses["gap_filling_answers"]
                "questionnaire_responses": {**(state.get("questionnaire_responses") or {}), "gap_filling_answers": {}},
            }
            update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)
            #  v7.146: 即使无需补充，也要进入雷达图环节
            #  v8.4: 双动机驱动 — 根据 motivation_routing_profile 决定是否跳过 radar
            _next = ProgressiveQuestionnaireNode._build_self_skip_decision(
                state, _NODE_STEP3_GAP, default_next=_NODE_STEP2_RADAR
            )
            return Command(update=update_dict, goto=_next)

        #  v7.107: 启用LLM智能生成补充问题
        import os

        existing_info_summary = ProgressiveQuestionnaireNode._build_existing_info_summary(structured_data)

        # v8.0 G2: 输出意图已确认时，注入禁止追问交付物的 prefix（防止 LLM 重复追问）
        if _active_projections:
            _PROJ_LABEL_MAP = {
                "design_professional": "空间策略报告",
                "investor_operator": "商业运营分析",
                "government_policy": "在地文化研究",
                "construction_execution": "落地实施指南",
                "aesthetic_critique": "叙事创意方案",
            }
            _proj_names = [_PROJ_LABEL_MAP.get(p, p) for p in _active_projections]
            _intent_prefix = (
                "【✅ 输出意向已确认 - 交付形式无需再追问】\n"
                f"• 已确认输出意向：{', '.join(_proj_names)}\n"
                "  → 禁止生成交付物类型相关追问\n\n"
            )
            existing_info_summary = _intent_prefix + (existing_info_summary or "")
            logger.info(f" [G2] 注入意图约束前缀，projections={_active_projections}")

        # 环境变量开关控制LLM生成（默认启用）
        enable_llm_generation = os.getenv("USE_LLM_GAP_QUESTIONS", "true").lower() == "true"

        if enable_llm_generation:
            try:
                from ...services.llm_gap_question_generator import LLMGapQuestionGenerator

                logger.info(" [v7.107] 使用LLM智能生成补充问题...")
                logger.info(f" [输入摘要] {user_input[:100]}...")  # v7.107.1：记录输入摘要
                logger.info(f" [缺失维度] {completeness.get('missing_dimensions', [])}")  # v7.107.1

                generator = LLMGapQuestionGenerator()

                # 调用同步包装器
                questions = generator.generate_sync(
                    user_input=user_input,
                    confirmed_tasks=confirmed_tasks,
                    missing_dimensions=completeness.get("missing_dimensions", []),
                    covered_dimensions=completeness.get("covered_dimensions", []),
                    existing_info_summary=existing_info_summary,
                    completeness_score=completeness.get("completeness_score", 0),
                    # v7.900 G5: 输出意图上下文透传
                    active_projections=_active_projections or None,
                    detected_identity_modes=state.get("detected_identity_modes") or None,
                    output_framework_signals=state.get("output_framework_signals") or None,
                )

                logger.info(f" [LLM智能生成] 成功生成 {len(questions)} 个针对性问题")

                # v7.107.1：记录首个问题示例
                if questions:
                    first_q = questions[0].get("question", "")[:80]
                    logger.info(f" [问题示例] {first_q}...")

                # 如果LLM生成失败或返回空，回退到硬编码
                if not questions:
                    raise ValueError("LLM返回空问题列表")

            except Exception as e:
                import traceback

                logger.error(f" [LLM生成失败] {type(e).__name__}: {str(e)}")  # v7.107.1：记录异常类型
                logger.error(f" [错误堆栈] {traceback.format_exc()}")  # v7.107.1：完整堆栈
                questions = analyzer.generate_gap_questions(
                    missing_dimensions=completeness.get("missing_dimensions", []),
                    critical_gaps=critical_gaps,
                    confirmed_tasks=confirmed_tasks,
                    existing_info_summary=existing_info_summary,
                    target_count=10,
                )
                logger.info(f" [硬编码回退] 生成 {len(questions)} 个问题")
        else:
            # 使用硬编码（性能优化模式）
            logger.info(" [性能优化] 使用硬编码问题模板（跳过LLM调用）")
            questions = analyzer.generate_gap_questions(
                missing_dimensions=completeness.get("missing_dimensions", []),
                critical_gaps=critical_gaps,
                confirmed_tasks=confirmed_tasks,
                existing_info_summary=existing_info_summary,
                target_count=10,
            )
            logger.info(f" [硬编码生成] 生成 {len(questions)} 个问题")

        #  v7.80.17: 应用问题排序（必答问题在前，按priority排序）
        questions = sorted(
            questions,
            key=lambda q: (
                0 if q.get("is_required", False) else 1,  # 必答问题在前
                q.get("priority", 999),  # 优先级数字小的在前
                -q.get("weight", 5),  # 权重大的在前（负号反转）
            ),
        )
        logger.info(
            f" [v7.80.17] 问题排序完成：{len([q for q in questions if q.get('is_required')])}个必答，{len([q for q in questions if not q.get('is_required')])}个选答"
        )

        # 获取上下文信息
        confirmed_task = state.get("confirmed_core_task", "")
        task_summary = ProgressiveQuestionnaireNode._build_task_summary(confirmed_tasks)

        #  v7.115: 获取用户原始输入，用于前端显示需求摘要
        user_input = state.get("user_input", "")
        user_input_summary = user_input[:100] + ("..." if len(user_input) > 100 else "")

        #  v7.80.6: 构建新的 interrupt payload（任务完整性导向）
        #  v7.146: 修正事件类型，与前端统一为 step2（信息补全环节）
        payload = {
            "interaction_type": "progressive_questionnaire_step2",
            "step": 2,
            "total_steps": 3,
            "title": "补充关键信息",
            "message": "为了更精准地理解您的项目需求，请补充以下关键信息：",
            "core_task": confirmed_task,
            "task_summary": task_summary,
            #  任务完整性信息
            "completeness_score": completeness.get("completeness_score", 0),
            "covered_dimensions": completeness.get("covered_dimensions", []),
            "missing_dimensions": completeness.get("missing_dimensions", []),
            "critical_gaps": critical_gaps,
            #  v7.115: 添加用户需求信息，供前端顶部显示
            "user_input": user_input,
            "user_input_summary": user_input_summary,
            "questionnaire": {
                "introduction": f"已完整度: {int(completeness.get('completeness_score', 0) * 100)}% | 缺失维度: {', '.join(completeness.get('missing_dimensions', []))}",
                "questions": questions,
                "note": "这些问题涉及预算、时间、交付等关键决策点，请根据实际情况作答",
            },
            "options": {"submit": "提交问卷", "back": "返回修改核心任务"},
        }

        logger.info(" [Step 3] 即将调用 interrupt()，等待用户输入...")
        user_response = interrupt(payload)
        logger.info(f" [Step 3] 收到用户响应: {type(user_response)}")

        # 解析用户响应
        answers = {}
        #  v7.87: 移除返回上一步功能

        if isinstance(user_response, dict):
            #  v7.87: 移除 action == "back" 处理
            answers = user_response.get("answers") or {}
            # 尝试从其他格式提取答案
            if not answers and "responses" in user_response:
                answers = user_response["responses"]

        logger.info(f" [Step 3] 收集到 {len(answers)} 个补充答案")

        # v7.900 G7: Gap 回流 — 将用户回答的关键信息注入 user_intent_constraints，供后续节点使用
        _gap_backflow: dict = {}
        _existing_constraints: dict = state.get("user_intent_constraints") or {}
        if answers and questions:
            _q_map = {q.get("id", ""): q for q in questions}
            for _qid, _ans in answers.items():
                _q = _q_map.get(_qid, {})
                _dim = _q.get("dimension") or _q.get("category") or ""
                if _dim and _ans:
                    _val = _ans if isinstance(_ans, str) else (", ".join(_ans) if isinstance(_ans, list) else str(_ans))
                    if _val.strip():
                        _gap_backflow[_dim] = _val.strip()
        if _gap_backflow:
            _merged_constraints = {**_existing_constraints, **_gap_backflow}
            logger.info(f" [G7] Gap 回流 {len(_gap_backflow)} 条约束到 user_intent_constraints: {list(_gap_backflow.keys())}")
        else:
            _merged_constraints = _existing_constraints

        #  v7.147: 移除此处的汇总调用，改为在雷达图完成后统一处理
        # 原因：此时 radar_dimension_values 尚未生成，会导致 NoneType 错误
        # questionnaire_summary = ProgressiveQuestionnaireNode._build_questionnaire_summary(state, answers)  #  删除

        #  v7.80.6: 保存任务完整性分析和补充答案
        update_dict = {
            "task_completeness_analysis": completeness,  # 完整性分析
            "task_gap_filling_questionnaire": {
                "questions": questions,
                "missing_dimensions": completeness.get("missing_dimensions", []),
                "critical_gaps": critical_gaps,
            },
            # LT-3: gap_filling_answers 合并到 questionnaire_responses["gap_filling_answers"]
            "questionnaire_responses": {**(state.get("questionnaire_responses") or {}), "gap_filling_answers": answers},
            "progressive_questionnaire_completed": False,  #  改为 False，因为还有雷达图步骤
            "progressive_questionnaire_step": 2,  #  这是 UI 的 Step 2
            # "questionnaire_summary": questionnaire_summary,  #  删除，改为在雷达图后生成
            "calibration_processed": False,  #  改为 False，雷达图完成后才算完成
            # v7.900 G7: Gap 回流约束
            "user_intent_constraints": _merged_constraints,
        }
        update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)

        #  v7.146: 修正路由 - Step2(信息补全)完成后进入Step3(雷达图)
        #  v8.4: 双动机驱动 — 根据 motivation_routing_profile 决定是否跳过 radar
        _next = ProgressiveQuestionnaireNode._build_self_skip_decision(
            state, _NODE_STEP3_GAP, default_next=_NODE_STEP2_RADAR
        )
        return Command(update=update_dict, goto=_next)

    # ==========================================================================
    # 辅助方法
    # ==========================================================================

    @staticmethod
    def _extract_core_task(state: ProjectAnalysisState) -> str:
        """
        从需求分析结果中提取核心任务

        优先级：
        1. structured_data.project_task
        2. structured_data.core_objectives
        3. structured_data.project_overview
        4. user_input 的摘要
        """
        agent_results = state.get("agent_results", {})
        requirements_result = agent_results.get("requirements_analyst", {})
        structured_data = requirements_result.get("structured_data", {})

        # 尝试从不同字段提取
        project_task = structured_data.get("project_task") or structured_data.get("project_tasks")
        if project_task:
            if isinstance(project_task, list):
                return "；".join(project_task[:3])
            return str(project_task)

        core_objectives = structured_data.get("core_objectives", [])
        if core_objectives:
            if isinstance(core_objectives, list):
                return "核心目标：" + "；".join(str(obj) for obj in core_objectives[:3])
            return f"核心目标：{core_objectives}"

        project_overview = structured_data.get("project_overview", "")
        if project_overview:
            # 截取前200字符
            return project_overview[:200] + ("..." if len(project_overview) > 200 else "")

        # 兜底：使用用户输入
        user_input = state.get("user_input", "")
        if user_input:
            return user_input[:300] + ("..." if len(user_input) > 300 else "")

        return "请描述您的核心需求和期望目标"

    @staticmethod
    def _build_task_summary(tasks: List[Dict[str, Any]]) -> str:
        """
        将任务列表构建为一句话摘要

        v7.80.1: 用于兼容旧的 confirmed_core_task 字段

        Args:
            tasks: 任务列表

        Returns:
            任务摘要字符串
        """
        if not tasks:
            return "请描述您的核心需求和期望目标"

        # 提取任务标题
        titles = [task.get("title", "") for task in tasks if task.get("title")]

        if not titles:
            return "请描述您的核心需求和期望目标"

        # 限制摘要长度
        if len(titles) <= 3:
            return "；".join(titles)
        else:
            return "；".join(titles[:3]) + f"等 {len(titles)} 项任务"

    @staticmethod
    def _build_existing_info_summary(structured_data: Dict[str, Any]) -> str:
        """
        构建已有信息摘要

        v7.80.6: 用于任务完整性分析

        Args:
            structured_data: 需求分析器的结构化数据

        Returns:
            已有信息摘要字符串
        """
        parts = []

        # 项目类型
        project_type = structured_data.get("project_type", "")
        if project_type:
            parts.append(f"项目类型: {project_type}")

        # 地点
        location = structured_data.get("location", "")
        if location:
            parts.append(f"地点: {location}")

        # 核心目标
        objectives = structured_data.get("core_objectives", [])
        if objectives:
            if isinstance(objectives, list):
                parts.append(f"核心目标: {', '.join(str(obj) for obj in objectives[:3])}")
            else:
                parts.append(f"核心目标: {objectives}")

        # 预算
        budget = structured_data.get("budget", "")
        if budget:
            parts.append(f"预算: {budget}")

        # 时间
        timeline = structured_data.get("timeline", "")
        if timeline:
            parts.append(f"时间: {timeline}")

        # 规模
        scale = structured_data.get("scale", "") or structured_data.get("area", "")
        if scale:
            parts.append(f"规模: {scale}")

        if not parts:
            return "（暂无结构化信息）"

        return " | ".join(parts)

    @staticmethod
    def _generate_gap_questions(gap_dimensions: List[str], state: ProjectAnalysisState) -> List[Dict[str, Any]]:
        """
        根据短板维度生成补充问题

        优先使用配置文件中的模板，回退到通用问题。
        """
        selector = DimensionSelector()
        questions = []

        for _i, dim_id in enumerate(gap_dimensions[:5]):  # 最多5个问题
            # 尝试获取模板
            template = selector.get_gap_question_template(dim_id)

            if template:
                questions.append(
                    {
                        "id": f"gap_{dim_id}",
                        "question": template.get("question", ""),
                        "type": template.get("type", "single_choice"),
                        "options": template.get("options", []),
                        "context": f"关于「{selector.get_dimension_by_id(dim_id).get('name', dim_id)}」维度的补充",
                        "source_dimension": dim_id,
                    }
                )
            else:
                # 使用通用问题
                dim_config = selector.get_dimension_by_id(dim_id) or {}
                questions.append(
                    {
                        "id": f"gap_{dim_id}",
                        "question": f"关于「{dim_config.get('name', dim_id)}」，您有什么具体的偏好或要求？",
                        "type": "open_ended",
                        "options": [],
                        "context": dim_config.get("description", "")[:100] if dim_config.get("description") else "",
                        "source_dimension": dim_id,
                    }
                )

        return questions

    @staticmethod
    def _build_questionnaire_summary(state: ProjectAnalysisState, gap_answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建问卷摘要（兼容旧格式）

         v7.147: 添加防御性检查，避免雷达图数据未生成时崩溃
        """
        timestamp = datetime.now().isoformat()

        # 合并所有数据
        radar_values = state.get("radar_dimension_values", {})
        radar_summary = state.get("radar_analysis_summary", {})
        confirmed_task = state.get("confirmed_core_task", "")

        #  v7.147: 防御性检查 - 避免 None 导致的 AttributeError
        if radar_values is None:
            logger.warning("️ [v7.147] radar_dimension_values 为 None，雷达图步骤可能被跳过或尚未执行")
            radar_values = {}

        if not isinstance(radar_values, dict):
            logger.warning(f"️ [v7.147] radar_dimension_values 类型错误: {type(radar_values)}，使用空字典")
            radar_values = {}

        if radar_summary is None:
            radar_summary = {}

        entries = []

        # 添加核心任务
        if confirmed_task:
            entries.append({"id": "core_task", "question": "核心任务", "value": confirmed_task, "type": "text"})

        # 添加雷达图数据（现在安全了）
        if radar_values:  #  v7.147: 额外检查确保非空
            for dim_id, value in radar_values.items():
                dim_detail = radar_summary.get("dimension_details", {}).get(dim_id, {})
                entries.append(
                    {
                        "id": f"radar_{dim_id}",
                        "question": dim_detail.get("name", dim_id),
                        "value": value,
                        "type": "slider",
                        "tendency": dim_detail.get("tendency", ""),
                    }
                )

        # 添加Gap问题答案
        for q_id, answer in gap_answers.items():
            entries.append({"id": q_id, "question": q_id, "value": answer, "type": "gap_filling"})  # 简化处理

        return {
            "entries": entries,
            "answers": {"core_task": confirmed_task, "radar_values": radar_values, "gap_answers": gap_answers},
            "submitted_at": timestamp,
            "timestamp": timestamp,
            "profile_label": radar_summary.get("profile_label", ""),
            "source": "progressive_questionnaire_v780",
            "notes": f"三步递进式问卷，风格标签：{radar_summary.get('profile_label', '未定义')}",
        }


# ==========================================================================
#  v7.80.15 (P1.1): 诗意解读辅助函数
# ==========================================================================


def _contains_poetic_expression(text: str) -> bool:
    """
    检测文本是否包含诗意/哲学/隐喻表达

    检测规则：
    1. 包含自然意象关键词（月亮、湖面、雪、云、风等）
    2. 包含哲学/精神关键词（虚无、对话、存在、灵魂等）
    3. 包含情感/氛围关键词（宁静、孤独、漂浮、沉浸等）
    4. 文本较短但富有意境（<50字但包含上述关键词）
    """
    poetic_keywords = [
        # 自然意象
        "月亮",
        "湖面",
        "结冰",
        "雪",
        "云",
        "风",
        "雨",
        "星空",
        "山",
        "水",
        "树",
        "花",
        "海",
        "天空",
        "日出",
        "日落",
        "晨曦",
        "黄昏",
        "夜",
        "光影",
        # 哲学/精神
        "虚无",
        "存在",
        "对话",
        "灵魂",
        "精神",
        "意识",
        "觉悟",
        "禅",
        "悟",
        "道",
        "永恒",
        "瞬间",
        "时间",
        "空间",
        "自我",
        "内心",
        "本质",
        "真实",
        # 情感/氛围
        "宁静",
        "孤独",
        "漂浮",
        "沉浸",
        "治愈",
        "重生",
        "回归",
        "游子",
        "乡愁",
        "诗意",
        "意境",
        "氛围",
        "感受",
        "体验",
        "心灵",
    ]

    text_lower = text.lower()
    matched = sum(1 for kw in poetic_keywords if kw in text_lower)

    # 规则1: 匹配3个或以上关键词
    if matched >= 3:
        return True

    # 规则2: 短文本(<50字) + 匹配1-2个关键词 + 包含比喻性描述
    if len(text) < 50 and matched >= 1:
        metaphor_patterns = ["像", "如同", "仿佛", "似乎", "犹如", "好似", "落在", "融入", "化作"]
        if any(pattern in text for pattern in metaphor_patterns):
            return True

    return False


async def _llm_interpret_poetry(text: str) -> Dict[str, Any]:
    """
    使用 LLM 解读诗意/隐喻表达

    Args:
        text: 用户的诗意输入

    Returns:
        {
            "literal_tasks": ["任务1", "任务2"],  # 字面意思的任务描述
            "metaphor_explanation": "月亮=宁静，湖面=镜像，结冰=克制",  # 隐喻解释
            "design_implications": ["光影设计", "镜面元素", "冷色调"]  # 设计指向
        }
    """

    from langchain_core.messages import HumanMessage, SystemMessage

    from ...services.llm_factory import LLMFactory

    system_prompt = """你是一个设计诗意表达解读专家。用户可能用诗意、隐喻、哲学性的语言描述设计需求。

你的任务：
1. 提取字面意思的核心任务（用简洁的设计语言）
2. 解读隐喻和意象（每个关键词的含义）
3. 转化为具体的设计指向（材料、色彩、光影、氛围等）

输出JSON：
{
  "literal_tasks": ["核心任务1", "核心任务2"],
  "metaphor_explanation": "关键词A=含义，关键词B=含义",
  "design_implications": ["设计元素1", "设计元素2", "设计元素3"]
}"""

    user_prompt = f"""用户输入：

{text}

请解读这段诗意表达，输出JSON格式的结果。"""

    try:
        llm = LLMFactory.create_llm(temperature=0.3)  # 降低温度提高一致性
        messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]

        response = await llm.ainvoke(messages)
        response_text = response.content if hasattr(response, "content") else str(response)

        # 解析JSON
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()

        result = json.loads(response_text)
        return result

    except Exception as e:
        logger.error(f" 诗意解读LLM调用失败: {e}")
        # 返回兜底结果
        return {
            "literal_tasks": [f"诗意空间设计：{text[:30]}"],
            "metaphor_explanation": "（解读失败）",
            "design_implications": ["氛围营造", "意境表达"],
        }


# ==========================================================================
# 导出节点函数（用于workflow注册）
# ==========================================================================


@track_active_step("progressive_step1_core_task")
def progressive_step1_core_task_node(state: ProjectAnalysisState, store: BaseStore | None = None) -> Command:
    """Step 1 节点函数"""
    return ProgressiveQuestionnaireNode.step1_core_task(state, store)


@track_active_step("progressive_step2_radar")
def progressive_step2_radar_node(state: ProjectAnalysisState, store: BaseStore | None = None) -> Command:
    """Step 2 节点函数"""
    return ProgressiveQuestionnaireNode.step2_radar(state, store)


@track_active_step("progressive_step3_gap_filling")
def progressive_step3_gap_filling_node(state: ProjectAnalysisState, store: BaseStore | None = None) -> Command:
    """Step 3 节点函数"""
    return ProgressiveQuestionnaireNode.step3_gap_filling(state, store)
