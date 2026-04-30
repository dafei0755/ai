# DEPRECATED: 已被 v2.0 双态架构 gatekeeper_v2 + conversation_engine 节点取代。
# 当 ENABLE_DUAL_MODE_V2=true 时本模块不再被主工作流调用，仅保留以供回退兼容。
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
import json
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from langgraph.store.base import BaseStore
from langgraph.types import Command, interrupt
from loguru import logger

from ...core.state import ProjectAnalysisState
from ...core.workflow_flags import WorkflowFlagManager
from ...services.capability_boundary_service import CapabilityBoundaryService, CheckType

# 🆕 v13.1: 交付类型 ID → 中文标签映射（模块级常量，step1 & step3 共用）
PROJ_LABEL_MAP = {
    "design_professional": "设计专业报告",
    "investor_operator": "投资运营分析",
    "government_policy": "政策汇报方案",
    "construction_execution": "施工深化方案",
    "aesthetic_critique": "美学评论文本",
}

from ...services.core_task_decomposer import (
    _simple_fallback_decompose, 
    decompose_core_tasks,
    decompose_core_tasks_hybrid  # 🆕 v7.995 P2: 混合生成策略
)
from ...services.dimension_selector import DimensionSelector, RadarGapAnalyzer, select_dimensions_for_state
# v7.700 P0: Mode Question Templates 集成
from ...services.mode_question_loader import (
    ModeQuestionLoader,
    extract_detected_modes_from_state,
    enrich_step1_payload_with_mode_questions
)


class ProgressiveQuestionnaireNode:
    """三步递进式问卷节点"""

    # ==========================================================================
    # Step 1: 任务梳理（v7.80.1 智能拆解版）
    # ==========================================================================

    @staticmethod
    def step1_core_task(
        state: ProjectAnalysisState, store: Optional[BaseStore] = None
    ) -> Command[Literal["progressive_step2_radar", "requirements_analyst"]]:
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
            return Command(update={"progressive_questionnaire_step": 1}, goto="progressive_step3_gap_filling")

        # 追问模式跳过
        if state.get("is_followup"):
            logger.info(" Follow-up session, skipping progressive questionnaire")
            update_dict = {"progressive_questionnaire_completed": True, "progressive_questionnaire_step": 3}
            update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)
            return Command(update=update_dict, goto="project_director")

        #  v7.80.1: 使用 LLM 拆解核心任务
        user_input = state.get("user_input", "")
        structured_data = state.get("agent_results", {}).get("requirements_analyst", {}).get("structured_data", {})
        
        # 🔄 v7.900: 获取信息质量元数据和不确定性地图（用于指导任务拆解）
        info_quality_metadata = structured_data.get("info_quality_metadata", {})
        uncertainty_map = structured_data.get("uncertainty_map", {})
        
        if info_quality_metadata or uncertainty_map:
            logger.info("🔍 [v7.900] 检测到信息缺口分析结果")
            logger.info(f"   信息质量: score={info_quality_metadata.get('score', 0):.2f}, "
                       f"confidence={info_quality_metadata.get('confidence_level', 'unknown')}")
            logger.info(f"   不确定性项: {len(uncertainty_map)}项需验证")
            
            # 记录缺失维度（用于后续问卷补全）
            missing_dims = info_quality_metadata.get('missing_dimensions', [])
            if missing_dims:
                logger.info(f"   缺失维度: {', '.join(missing_dims[:5])}")
        
        # 🔄 v7.900: 缺口信息注入（已废弃，core_task_decomposer 未消费这两个键）
        # v10.1 P4 清理: _v7900_info_quality / _v7900_uncertainty_map 为死数据，不再注入
        # 保留 info_quality_metadata / uncertainty_map 变量本身供日志使用

        # 🆕 v10.0: 注入输出意图检测结果（来自 output_intent_detection 节点）
        active_projections = state.get("active_projections", [])
        detected_identity_modes = state.get("detected_identity_modes", [])
        output_framework_signals = state.get("output_framework_signals", {})
        if active_projections:
            structured_data['_v10_active_projections'] = active_projections
            logger.info(f"🎯 [v10.0] 注入 {len(active_projections)} 个已确认输出投射: {active_projections}")
        if detected_identity_modes:
            structured_data['_v10_identity_modes'] = detected_identity_modes
            logger.info(f"🎭 [v10.0] 注入 {len(detected_identity_modes)} 个身份模式")
        if output_framework_signals:
            structured_data['_v10_framework_signals'] = output_framework_signals
            logger.info(f"📐 [v10.1] 注入框架信号: {output_framework_signals.get('reasoning', '')[:80]}")

        #  v7.80.15 (P1.1): 诗意解读子流程
        poetic_metadata = None
        if _contains_poetic_expression(user_input):
            logger.info(" [诗意解读] 检测到诗意/哲学表达，启动诗意解读子流程")
            try:
                import functools
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
        # 🆕 v7.995 P2: 优先使用混合生成策略 (LLM + 规则并行)
        # v7.80.1.2: 使用 ThreadPoolExecutor 在独立线程中运行 LLM 异步调用
        # 解决 LangGraph 异步上下文与 asyncio.run 不兼容的问题
        try:
            import functools
            from concurrent.futures import ThreadPoolExecutor
            import os

            # 🆕 v7.995: 通过环境变量控制是否启用混合策略
            use_hybrid_strategy = os.getenv("USE_HYBRID_TASK_GENERATION", "true").lower() == "true"

            def _run_async_decompose(user_input: str, structured_data: dict):
                """在独立线程中运行异步任务拆解"""
                if use_hybrid_strategy:
                    logger.info("🔀 [v7.995 P2] 使用混合生成策略 (LLM + 规则)")
                    return asyncio.run(decompose_core_tasks_hybrid(user_input, structured_data, enable_hybrid=True))
                else:
                    logger.info("🤖 [v7.995] 使用纯LLM模式")
                    return asyncio.run(decompose_core_tasks(user_input, structured_data))

            logger.info(" [v7.80.1.2] 使用 ThreadPoolExecutor 执行任务拆解")
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_run_async_decompose, user_input, structured_data)
                # v7.999.10: 超时从60s→300s，两阶段生成(Phase1+15类别×Phase2+元数据推断)实际耗时约120s
                extracted_tasks = future.result(timeout=300)

            if not extracted_tasks:
                logger.warning("️ 任务拆解返回空列表，使用回退策略")
                extracted_tasks = _simple_fallback_decompose(user_input, structured_data)

        except TimeoutError:
            logger.error(" [v7.999.10] 任务拆解超时(>300s)，使用回退策略")
            extracted_tasks = _simple_fallback_decompose(user_input, structured_data)
        except Exception as e:
            logger.error(f" LLM 任务拆解失败: {type(e).__name__}: {e}")
            logger.info("️ 使用回退策略进行关键词匹配拆解")
            extracted_tasks = _simple_fallback_decompose(user_input, structured_data)

        logger.info(f" [v7.80.1] 拆解出 {len(extracted_tasks)} 个核心任务")
        for i, task in enumerate(extracted_tasks):
            logger.info(f"   {i+1}. {task.get('title', '未命名')}")

        # 🆕 v15.0: 为每个任务分配稳定的确定性 ID（CT-{hash8}）
        # 确保 task_id 不依赖 LLM 输出的不稳定 ID，而是基于内容哈希
        from ...core.task_oriented_models import generate_stable_task_id
        for task in extracted_tasks:
            title = task.get('title', '')
            desc = task.get('description', '')
            stable_id = generate_stable_task_id(title, desc)
            task['task_id'] = stable_id
            # 保留旧的 id 字段以兼容前端
            if not task.get('id'):
                task['id'] = stable_id
        logger.info(f"🆔 [v15.0] 已为 {len(extracted_tasks)} 个任务分配稳定 ID: "
                     f"{[t.get('task_id') for t in extracted_tasks[:3]]}...")

        # 🔧 P1修复: 从任务中提取detected_modes并写回state（修复模式问题注入跳过的bug）
        # _simple_mode_detection的结果保存在任务的metadata中，需要回写到state供enrich_step1_payload读取
        try:
            from ...services.core_task_decomposer import CoreTaskDecomposer
            _temp_decomposer = CoreTaskDecomposer()
            project_features = structured_data.get('project_features', {}) if structured_data else {}
            project_type = structured_data.get('project_type', '') if structured_data else ''
            local_detected_modes = _temp_decomposer._simple_mode_detection(user_input, project_type, project_features)
            if local_detected_modes:
                # 写入 state 中 extract_detected_modes_from_state 会读取的路径
                agent_results = state.get("agent_results", {})
                req_analyst = agent_results.get("requirements_analyst", {})
                sd = req_analyst.get("structured_data", {})
                if not sd.get("detected_modes") and not sd.get("detected_design_modes"):
                    sd["detected_modes"] = local_detected_modes
                    req_analyst["structured_data"] = sd
                    agent_results["requirements_analyst"] = req_analyst
                    state["agent_results"] = agent_results
                    logger.info(f"🔧 [P1修复] 回写 {len(local_detected_modes)} 个detected_modes到state: "
                               f"{[m['mode'] for m in local_detected_modes]}")
        except Exception as e:
            logger.warning(f"⚠️ [P1修复] 模式回写失败: {e}，不影响主流程")

        # 同时保留旧格式（兼容性）
        old_format_task = ProgressiveQuestionnaireNode._extract_core_task(state)

        # 生成用户输入摘要
        user_input_summary = user_input[:100] + ("..." if len(user_input) > 100 else "")

        # v8.001: 构建 task_groups 分组元数据（基于 category 字段聚合，保留 Phase 1 结构）
        def _build_task_groups(tasks):
            """将平铺任务列表按 category 归组，保持任务在列表中的相对顺序"""
            groups = []
            seen_categories = []
            category_to_group = {}
            for task in tasks:
                cat = task.get('category', '基础调研') or '基础调研'
                if cat not in category_to_group:
                    group = {'category': cat, 'count': 0, 'task_ids': []}
                    groups.append(group)
                    category_to_group[cat] = group
                    seen_categories.append(cat)
                category_to_group[cat]['count'] += 1
                category_to_group[cat]['task_ids'].append(task.get('id', ''))
            return groups

        task_groups = _build_task_groups(extracted_tasks)
        logger.info(f"📦 [v8.001] 构建 {len(task_groups)} 个任务分组: {[g['category'] for g in task_groups]}")

        #  v7.80.1: 构建新的 interrupt payload
        payload = {
            "interaction_type": "progressive_questionnaire_step1",
            "step": 1,
            "total_steps": 3,
            "title": "任务梳理",
            "message": "系统已从您的描述中识别以下核心任务，请确认、调整或补充",
            #  新字段：任务列表
            "extracted_tasks": extracted_tasks,
            # v8.001 新字段：分组元数据（前端按此渲染分组标题）
            "task_groups": task_groups,
            "user_input_summary": user_input_summary,
            # 旧字段：保留兼容
            "extracted_task": old_format_task,
            "editable": True,
            "options": {"confirm": "确认任务列表", "skip": "跳过问卷"},
        }
        
        # v7.700 P0: 注入模式特定引导问题
        try:
            payload = enrich_step1_payload_with_mode_questions(state, payload)
            logger.info("✅ [v7.700 P0] 模式问题注入成功")
        except Exception as e:
            logger.warning(f"⚠️ [v7.700 P0] 模式问题注入失败: {e}，继续使用基础payload")

        # 🆕 v13.1: 构建意图确认复盘卡片（纯字段提取，零 LLM 调用）
        _active_proj = state.get("active_projections") or []
        _identity_modes = state.get("detected_identity_modes") or []
        _intent_changed = state.get("intent_changed", False)
        _user_constraints = state.get("user_intent_constraints") or []
        _framework_sig = state.get("output_framework_signals") or {}
        intent_review = {
            "confirmed_deliveries": [
                {"id": p, "label": PROJ_LABEL_MAP.get(p, p)}
                for p in _active_proj
            ],
            "confirmed_identity_modes": [
                {"id": m.get("id", ""), "label": m.get("label", "")}
                for m in (_identity_modes[:3] if isinstance(_identity_modes, list) else [])
            ],
            "confirmed_constraints": [
                {"label": c.get("label", ""), "desc": c.get("desc", "")}
                for c in (_user_constraints[:5] if isinstance(_user_constraints, list) else [])
            ],
            "intent_changed": _intent_changed,
            "depth_hint": _framework_sig.get("output_calibration", {}).get("depth_hint", ""),
            "mandatory_dimensions": _framework_sig.get("mandatory_dimensions", []),
        }
        payload["intent_review"] = intent_review
        logger.info(f"📋 [v13.1] intent_review: deliveries={len(intent_review['confirmed_deliveries'])}, constraints={len(intent_review['confirmed_constraints'])}, changed={_intent_changed}")

        # 🆕 v11.0: output_intent 已在 Step0 独立确认，Step1 直接使用已确认的 active_projections
        logger.info(f"📍 [v11.0] Step1 使用已确认的意图: active_projections={state.get('active_projections', [])}")

        logger.info(" [Step 1] 即将调用 interrupt()，等待用户输入...")
        user_response = interrupt(payload)
        logger.info(f" [Step 1] 收到用户响应: {type(user_response)}")

        #  v7.401: interrupt()返回后立即检查状态（防止并发重复执行）
        # 竞态条件检测：如果在interrupt期间其他线程已完成Step 1，则跳过
        if state.get("progressive_questionnaire_step", 0) >= 1 and state.get("confirmed_core_tasks"):
            logger.warning("️ [v7.401 并发检测] Step 1 已在interrupt期间被其他线程完成，跳过重复执行")
            logger.info(f"   当前state['progressive_questionnaire_step'] = {state.get('progressive_questionnaire_step')}")
            logger.info(f"   当前state['confirmed_core_tasks'] 数量 = {len(state.get('confirmed_core_tasks', []))}")
            return Command(update={"progressive_questionnaire_step": 1}, goto="progressive_step3_gap_filling")

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
            logger.info(f"️ [v7.87 P0] 已设置默认 questionnaire_summary（Step 1跳过）")

            update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)
            return Command(update=update_dict, goto="project_director")

        # 构建任务摘要
        task_summary = ProgressiveQuestionnaireNode._build_task_summary(confirmed_tasks)

        # =====================================================================
        # ⚠️ v9.1 G1/G2: 用户修改后质量校验（软验证，不阻塞流程）
        # 解决: 用户确认空列表/删除所有高优先级任务等极端情况
        # =====================================================================
        quality_warnings = []
        
        # G1-Rule1: 非空检查（至少保留3个任务）
        if len(confirmed_tasks) < 3:
            quality_warnings.append(
                f"⚠️ 任务数量过少（{len(confirmed_tasks)}个），建议至少保留3个核心任务"
            )
            logger.warning(f"[v9.1 G1] 任务数量不足: {len(confirmed_tasks)} < 3")
        
        # G1-Rule2: 高优先级任务保留检查
        high_priority_tasks = [
            t for t in confirmed_tasks
            if t.get("priority") in ("high", "P0", "critical", "MUST_HAVE")
        ]
        original_high_priority = [
            t for t in extracted_tasks
            if t.get("priority") in ("high", "P0", "critical", "MUST_HAVE")
        ]
        if original_high_priority and not high_priority_tasks:
            quality_warnings.append(
                f"⚠️ 原始高优先级任务({len(original_high_priority)}个)全部被移除，"
                "可能导致关键需求遗漏"
            )
            logger.warning(f"[v9.1 G1] 高优先级任务全部被移除: "
                          f"original={len(original_high_priority)}, remaining=0")
        
        # G1-Rule3: 内容质量检查（任务描述不能为空）
        empty_desc_count = sum(
            1 for t in confirmed_tasks
            if not (t.get("description", "") or t.get("title", "")).strip()
        )
        if empty_desc_count > 0:
            quality_warnings.append(
                f"⚠️ {empty_desc_count}个任务缺少标题/描述"
            )
            logger.warning(f"[v9.1 G1] {empty_desc_count}个任务缺少内容")
        
        if quality_warnings:
            logger.warning(f"[v9.1 G1] 质量校验发现 {len(quality_warnings)} 个警告:")
            for w in quality_warnings:
                logger.warning(f"  {w}")
        else:
            logger.info("✅ [v9.1 G1] 用户确认任务质量校验通过")

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

            logger.info(f" 任务能力边界检查结果:")
            logger.info(f"   在能力范围内: {boundary_check.within_capability}")
            logger.info(f"   能力匹配度: {boundary_check.capability_score:.2f}")

            # 标记有风险的任务
            if not boundary_check.within_capability:
                logger.warning(f"️ 部分任务可能超出能力范围")

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

        # 🆕 v11.0: output_intent 已在 Step0 独立确认，此处无需处理

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
            # ⚠️ v9.1 G1: 质量校验警告（供下游诊断使用）
            "step1_quality_warnings": quality_warnings if quality_warnings else None,
            # 🆕 v13.0: 锁定 Step 1 基线快照（供需求洞察复盘对比）
            "step1_confirmed_tasks_snapshot": [dict(t) for t in confirmed_tasks] if confirmed_tasks else [],
        }
        update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)

        # 信息补全（gap_filling）先于偏好雷达图执行
        # 正确顺序：任务梳理 → 信息补全 → 偏好雷达图 → 需求洞察
        logger.info("🎛️  [Step1→Step2] 路由 → step3_gap_filling（信息补全）")
        return Command(update=update_dict, goto="progressive_step3_gap_filling")

    # ==========================================================================
    # Step 2: 雷达图维度
    # ==========================================================================

    @staticmethod
    def step2_radar(
        state: ProjectAnalysisState, store: Optional[BaseStore] = None
    ) -> Command[Literal["progressive_step3_gap_filling", "questionnaire_summary"]]:
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
            return Command(update={"progressive_questionnaire_step": 2}, goto="questionnaire_summary")

        #  v7.80.4: 动态维度选择 + 智能生成
        #  v7.110: 集成混合策略 AdaptiveDimensionGenerator
        #  v8.0: 项目专属维度生成（三层架构：校准+决策+洞察）
        import os

        # ⚠️ v9.1: AdaptiveDimensionGenerator / DynamicDimensionGenerator 已废弃
        # 所有维度编排由 RadarDimensionOrchestrator 统一处理

        #  v7.80.5: 强制生成模式（用于测试/演示）
        FORCE_GENERATE = os.getenv("FORCE_GENERATE_DIMENSIONS", "false").lower() == "true"

        #  v7.80.16: 动态生成开关（v7.150: 默认启用，实现真正的智能维度生成）
        USE_DYNAMIC_GENERATION = os.getenv("USE_DYNAMIC_GENERATION", "true").lower() == "true"

        #  v7.110: 智能学习开关
        ENABLE_DIMENSION_LEARNING = os.getenv("ENABLE_DIMENSION_LEARNING", "false").lower() == "true"

        # 🎯 v8.0: 项目专属维度生成开关
        USE_PROJECT_SPECIFIC = os.getenv("USE_PROJECT_SPECIFIC_DIMENSIONS", "true").lower() == "true"

        #  v7.117: 增强调试日志，排查智能维度问题
        logger.info(f" [Step 2 环境变量] FORCE_GENERATE_DIMENSIONS={FORCE_GENERATE}")
        logger.info(f" [Step 2 环境变量] USE_DYNAMIC_GENERATION={USE_DYNAMIC_GENERATION}")
        logger.info(f" [Step 2 环境变量] ENABLE_DIMENSION_LEARNING={ENABLE_DIMENSION_LEARNING}")
        logger.info(f"🎯 [Step 2 环境变量] USE_PROJECT_SPECIFIC_DIMENSIONS={USE_PROJECT_SPECIFIC}")

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

        # ====================================================================
        # 🎯 v9.0: 维度生成统一编排器（动态优先 + 三级重试 + 显式降级）
        # 替代: v8.0 USE_PROJECT_SPECIFIC 单次生成 + 静默降级机制
        # ====================================================================
        from ...services.radar_dimension_orchestrator import RadarDimensionOrchestrator

        _orch_result = RadarDimensionOrchestrator().orchestrate(state)
        dimensions                  = _orch_result["dimensions"]
        dimension_generation_method = _orch_result["dimension_generation_method"]
        generation_summary_text     = _orch_result["generation_summary_text"]
        generated_count             = _orch_result["generated_count"]
        dimension_meta              = _orch_result["dimension_meta"]
        generation_trace            = _orch_result.get("generation_trace", [])
        existing_dimensions         = []   # 编排器已完成全过程，保留兼容字段
        radar_generation_source     = dimension_meta.get("generation_source")
        radar_error_code            = dimension_meta.get("error_code")

        # v9.4: 优先复用快照维度，避免 interrupt/resume 场景下维度 ID 漂移
        dimensions_snapshot = state.get("_radar_dimensions_snapshot")
        if isinstance(dimensions_snapshot, list) and dimensions_snapshot:
            dimensions = dimensions_snapshot
            dimension_generation_method = "snapshot_reuse"
            logger.info(f" [v9.4] 复用雷达维度快照: {len(dimensions)} 个维度")

        # 从 state 取下游仍需要的字段
        user_input          = state.get("user_input", "")
        agent_results       = state.get("agent_results", {})
        requirements_result = agent_results.get("requirements_analyst", {})
        structured_data     = requirements_result.get("structured_data", {})

        logger.info(
            f"📊 [v9.0] 维度编排完成: method={dimension_generation_method}, "
            f"dims={len(dimensions)}, degraded={dimension_meta.get('degraded')}, "
            f"quality={dimension_meta.get('quality_score', 0):.2f}, "
            f"attempts={dimension_meta.get('attempts', 0)}"
        )

        # ── 以下代码保留，维持与 payload 构建的兼容 ──────────────────────────
        # (旧 Step 2.1 + 2.2 全部由编排器内部处理)

        # 获取确认的核心任务
        confirmed_task = state.get("confirmed_core_task", "")

        #  v7.115: 获取用户原始输入，用于前端显示需求摘要
        user_input_summary = user_input[:100] + ("..." if len(user_input) > 100 else "")

        #  v7.146: 确保 dimensions 是列表格式（编排器已保证，此处为最终安全保护）
        if not isinstance(dimensions, list):
            logger.error(f" [payload构建] dimensions 不是列表，类型: {type(dimensions)}, 使用降级维度")
            dimensions = _get_default_dimensions()

            #  v7.146.1: 降级后再次校验，强制解包 v7.139 dict 格式
            if isinstance(dimensions, dict):
                logger.warning(f"️ [降级后] dimensions 仍为 dict，强制提取 dimensions 字段")
                dimensions = dimensions.get("dimensions", [])
            if not isinstance(dimensions, list):
                logger.error(f" [降级失败] dimensions 最终仍非列表: {type(dimensions)}，使用空列表")
                dimensions = []

        # 构建interrupt payload
        #  v7.146: 修正事件类型，step2_radar函数对应前端第3步（雷达图）
        # 🎯 v8.0: 为项目专属维度添加分层信息
        dimension_layers = {}
        if dimension_generation_method == "project_specific":
            # 🎯 v8.0: 按 source（校准/决策/洞察）分层，展示三层架构
            for dim in dimensions:
                layer_key = dim.get("source", dim.get("category", "unknown"))
                if layer_key not in dimension_layers:
                    dimension_layers[layer_key] = []
                dimension_layers[layer_key].append(dim.get("id", ""))

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
            # 🎯 v9.0: 维度生成元信息（含降级可观测性）
            "dimension_generation_method": dimension_generation_method,
            "dimension_layers": dimension_layers,
            "generation_summary": generation_summary_text,
            "dimension_meta": dimension_meta,
            "generation_source": radar_generation_source,
            "error_code": radar_error_code,
            "generation_trace": generation_trace,
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
            dimension_values = user_response.get("values") or user_response.get("dimension_values") or user_response.get("selected_dimensions") or {}
            # 如果没有values字段，尝试直接从响应中提取
            if not dimension_values:
                for key, value in user_response.items():
                    if key in [d["id"] for d in dimensions] and isinstance(value, (int, float)):
                        dimension_values[key] = int(value)

        # v9.2 fix: 校验维度 ID 映射一致性
        # 确保 dimension_values 的 key 与 dimensions 的 id 匹配
        valid_dim_ids = {d["id"] for d in dimensions}
        if dimension_values:
            original_dimension_values = dict(dimension_values)
            unmatched_keys = set(dimension_values.keys()) - valid_dim_ids
            if unmatched_keys:
                logger.warning(f"⚠️ [v9.2] 雷达维度 ID 不匹配: 用户响应包含未知维度 {unmatched_keys}")
                # 尝试按 name 回填匹配
                name_to_id = {d.get("name", ""): d["id"] for d in dimensions}
                remapped = {}
                for key, value in dimension_values.items():
                    if key in valid_dim_ids:
                        remapped[key] = value
                    elif key in name_to_id:
                        remapped[name_to_id[key]] = value
                        logger.info(f"   🔄 将 '{key}' 重映射为 '{name_to_id[key]}'")
                    else:
                        logger.warning(f"   ❌ 无法映射维度 '{key}'，丢弃")

                # v9.3 fix: 若常规映射命中率过低，按顺序兜底映射
                # 背景：interrupt 恢复时节点会重跑，维度可能被再次生成导致 ID 漂移；
                # 前端提交的是上一次展示的 ID，此处使用“顺序一致性”尽量保留用户输入。
                total_count = len(original_dimension_values)
                remap_ratio = (len(remapped) / total_count) if total_count else 1.0
                if remap_ratio < 0.8 and dimensions and original_dimension_values:
                    logger.warning(
                        f"⚠️ [v9.3] 常规映射命中率过低 ({remap_ratio:.0%})，启用顺序兜底映射"
                    )
                    ordered_values = list(original_dimension_values.values())
                    fallback_mapped = {}
                    for idx, dim in enumerate(dimensions):
                        if idx >= len(ordered_values):
                            break
                        fallback_mapped[dim["id"]] = ordered_values[idx]

                    if fallback_mapped:
                        remapped = fallback_mapped
                        logger.info(
                            f"   ✅ 顺序兜底映射完成: {len(remapped)}/{len(dimensions)}"
                        )

                dimension_values = remapped
                logger.info(f"   映射后有效维度: {len(dimension_values)}/{len(valid_dim_ids)}")

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
            "_radar_dimensions_snapshot": dimensions,  # v9.4: 维度快照（下次优先复用）
            "radar_dimension_values": dimension_values,
            "radar_analysis_summary": analysis,
            "progressive_questionnaire_step": 3,  # v9.3 fix: 前端 Step3（雷达图）完成，应为 3 而非 2
            "dimension_generation_method": dimension_generation_method,
            "radar_dimension_meta": dimension_meta,       # v9.0: 可观测性
            "radar_generation_trace": generation_trace,    # v9.0: 生成追踪
            "radar_generation_source": radar_generation_source,
            "radar_error_code": radar_error_code,
        }
        update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)

        #  v7.146: 修正路由 - Step3(雷达图)完成后进入需求洞察
        logger.info(" [Step 3] 雷达图维度收集完成，准备进入需求洞察")

        # 保存雷达图分析结果
        gap_dimensions = analysis.get("gap_dimensions", [])
        if gap_dimensions:
            logger.info(f"   雷达图短板维度: {gap_dimensions}")

        # 进入需求洞察节点（雷达图是问卷最后一步）
        return Command(update=update_dict, goto="questionnaire_summary")

    # ==========================================================================
    # Step 3: 密度补齐追问
    # ==========================================================================

    @staticmethod
    def step3_gap_filling(
        state: ProjectAnalysisState, store: Optional[BaseStore] = None
    ) -> Command[Literal["questionnaire_summary"]]:
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
            return Command(update={"progressive_questionnaire_step": 3}, goto="project_director")

        #  v7.80.6: 针对核心任务进行信息完整性分析
        from ...services.task_completeness_analyzer import TaskCompletenessAnalyzer

        # 获取核心任务和相关数据
        confirmed_tasks = state.get("confirmed_core_tasks", [])
        user_input = state.get("user_input", "")
        agent_results = state.get("agent_results", {})
        requirements_result = agent_results.get("requirements_analyst", {})
        structured_data = requirements_result.get("structured_data", {})

        # 🆕 B8: 读取已确认命题与排除方向（用于过滤无关追问）
        confirmed_proposition = state.get("confirmed_proposition", "")
        confirmed_exclusions = state.get("confirmed_exclusions", [])
        if confirmed_proposition:
            logger.info(f"📜 [B8] Step3 已获取命题约束: {confirmed_proposition[:60]}...")
        if confirmed_exclusions:
            logger.info(f"🚫 [B8] Step3 排除方向: {confirmed_exclusions}")

        # 🔄 v7.900: 获取不确定性地图，优先提问高不确定性项
        uncertainty_map = structured_data.get("uncertainty_map", {})
        info_quality_metadata = structured_data.get("info_quality_metadata", {})
        
        if uncertainty_map:
            high_uncertainty_items = [k for k, v in uncertainty_map.items() if v == "high"]
            medium_uncertainty_items = [k for k, v in uncertainty_map.items() if v == "medium"]
            logger.info(f"🔍 [v7.900] Step3 将针对不确定性项提问")
            logger.info(f"   高不确定性: {len(high_uncertainty_items)}项 - {', '.join(high_uncertainty_items[:3])}")
            logger.info(f"   中不确定性: {len(medium_uncertainty_items)}项 - {', '.join(medium_uncertainty_items[:3])}")

        # 执行任务完整性分析（v8.2: 透传 project_type + active_projections）
        analyzer = TaskCompletenessAnalyzer()
        active_projections = state.get("active_projections", [])
        project_type = state.get("project_type", "")
        completeness = analyzer.analyze(
            confirmed_tasks, user_input, structured_data,
            active_projections=active_projections,
            project_type=project_type,
        )

        # v8.0: 若 active_projections 非空（Step0已确认输出意向），则"交付要求"维度视为已覆盖
        # v8.3: 交付要求的过滤已在 TaskCompletenessAnalyzer.analyze() 中完成，此处仅做日志记录
        if active_projections:
            logger.info(
                f"✅ [v8.0] active_projections={active_projections} → '交付要求'维度已在 analyzer 中标记为已覆盖"
            )
        
        # 🔄 v7.900: 将 uncertainty_map 合并到 completeness 分析中
        if uncertainty_map:
            # 将高不确定性项添加到 critical_gaps
            original_gaps = completeness.get('critical_gaps', [])
            uncertainty_gaps = [
                {
                    "dimension": dim,
                    "reason": f"Phase2标记为{level}不确定性",
                    "priority": "high" if level == "high" else "medium",
                    "source": "uncertainty_map"
                }
                for dim, level in uncertainty_map.items()
            ]
            completeness['critical_gaps'] = original_gaps + uncertainty_gaps
            completeness['uncertainty_map'] = uncertainty_map
            logger.info(f"🔍 [v7.900] 合并不确定性缺口: 原{len(original_gaps)}项 + 新{len(uncertainty_gaps)}项")

        logger.info(f" 任务信息完整性评分: {completeness.get('completeness_score', 0):.2f}")
        logger.info(f"   已覆盖维度: {completeness.get('covered_dimensions', [])}")
        logger.info(f"   缺失维度: {completeness.get('missing_dimensions', [])}")
        logger.info(f"   关键缺失点: {completeness.get('critical_gaps', [])}")

        # 判断是否需要补充问题
        critical_gaps = completeness.get("critical_gaps", [])
        completeness_score = completeness.get("completeness_score", 0)
        missing_dims = completeness.get("missing_dimensions", [])

        # v8.3: 兜底检查 - critical_gaps 为空但 completeness_score 低/缺失维度多时，
        # 将 missing_dimensions 转为 critical_gaps，防止信息补全步骤被错误跳过
        if not critical_gaps and (completeness_score < 0.7 or len(missing_dims) > 2):
            logger.warning(
                f"⚠️ [v8.3] critical_gaps 为空但 completeness_score={completeness_score:.2f}, "
                f"缺失{len(missing_dims)}个维度 {missing_dims}，强制生成补充缺口"
            )
            critical_gaps = [
                {"dimension": dim, "reason": f"未覆盖{dim}相关信息，需要进一步了解", "priority": "medium"}
                for dim in missing_dims[:5]  # 最多取5个，避免问题过多
            ]
            completeness["critical_gaps"] = critical_gaps

        if not critical_gaps:
            logger.info(" 任务信息完整，无需补充，跳过问题生成，直接进入雷达图")
            update_dict = {
                "progressive_questionnaire_completed": False,  # 还未完全完成，需要进行雷达图
                "progressive_questionnaire_step": 2,
                "task_completeness_analysis": completeness,  # 保存分析结果
                "gap_filling_answers": {},  # 空答案
            }
            update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)
            #  v7.146: 即使无需补充，也要进入雷达图环节
            return Command(update=update_dict, goto="progressive_step2_radar")

        #  v7.107: 启用LLM智能生成补充问题
        import os

        existing_info_summary = ProgressiveQuestionnaireNode._build_existing_info_summary(structured_data)

        # 🆕 B8: 将命题约束前置注入 existing_info_summary，引导LLM过滤无关追问
        if confirmed_proposition or confirmed_exclusions:
            proposition_constraint_section = "\n\n【⚠️ 命题语义约束 - 追问必须聚焦于此命题范围内】\n"
            if confirmed_proposition:
                proposition_constraint_section += f"• 已确认设计命题：{confirmed_proposition}\n"
                proposition_constraint_section += "  → 追问须有助于深化该命题，避免发散到命题以外的需求\n"
            if confirmed_exclusions:
                excl_str = "、".join(confirmed_exclusions)
                proposition_constraint_section += f"• 已排除的方向：{excl_str}\n"
                proposition_constraint_section += "  → 不得针对以上排除方向生成任何追问题\n"
            existing_info_summary = proposition_constraint_section + existing_info_summary
            logger.info(f"📜 [B8] 命题约束已注入 existing_info_summary 前缀（{len(proposition_constraint_section)}字符）")

        # v8.0: 输出意向已确认时，前置注入"交付形式无需追问"约束
        if active_projections:
            proj_names = "、".join(PROJ_LABEL_MAP.get(p, p) for p in active_projections)
            delivery_section = (
                f"\n\n【✅ 输出意向已确认 - 交付形式无需再追问】\n"
                f"• 已确认输出意向：{proj_names}\n"
                f"  → 交付形式已明确，禁止生成交付物类型/成果形式相关追问题\n"
            )
            existing_info_summary = delivery_section + existing_info_summary
            logger.info(f"✅ [v8.0] 输出意向约束已注入 existing_info_summary（{proj_names}）")

        # 环境变量开关控制LLM生成（默认启用）
        enable_llm_generation = os.getenv("USE_LLM_GAP_QUESTIONS", "true").lower() == "true"

        if enable_llm_generation:
            gap_generation_source = "llm"
            gap_error_code = None
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
                    # v7.200: 透传输出意向
                    active_projections=state.get("active_projections", []),
                    detected_identity_modes=state.get("detected_identity_modes", []),
                    output_framework_signals=state.get("output_framework_signals", {}),
                )

                gap_meta = getattr(generator, "last_generation_metadata", {}) or {}
                gap_generation_source = gap_meta.get("generation_source", "llm")
                gap_error_code = gap_meta.get("error_code")

                logger.info(f" [LLM智能生成] 成功生成 {len(questions)} 个针对性问题")
                logger.info(f" [LLM智能生成] source={gap_generation_source}, error_code={gap_error_code}")

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
                err_text = str(e).lower()
                gap_error_code = (
                    "LLM_AUTH_401"
                    if "401" in err_text and ("authentication" in err_text or "user not found" in err_text or "invalid_api_key" in err_text)
                    else "LLM_RUNTIME_ERROR"
                )
                gap_generation_source = "fallback_auth_failed" if gap_error_code == "LLM_AUTH_401" else "fallback_runtime_failed"
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
            gap_generation_source = "fallback_llm_disabled"
            gap_error_code = "LLM_DISABLED"

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
            "generation_source": gap_generation_source,
            "error_code": gap_error_code,
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

        # =====================================================================
        # ⚠️ v9.1 G5: Step3 gap回流机制
        # 检查补充答案中是否包含新发现的关键信息，需要补充到 confirmed_core_tasks
        # =====================================================================
        gap_supplement_tasks = []
        try:
            if answers and confirmed_tasks:
                # 收集现有任务覆盖的关键词
                existing_task_text = " ".join(
                    (t.get("title", "") + " " + t.get("description", ""))
                    for t in confirmed_tasks
                ).lower()

                # 分析每个补充答案，检查是否引入了新的关键信息
                high_value_keywords = [
                    "预算", "造价", "成本", "时间", "工期", "进度", "分期",
                    "法规", "规范", "限高", "容积率", "退界", "消防",
                    "甲方", "业主", "投资方", "使用方", "运营方",
                    "材料", "结构", "施工", "工艺", "技术",
                    "安全", "无障碍", "节能", "环保", "绿建",
                ]

                new_dimensions = []
                for q_id, answer_text in answers.items():
                    if not isinstance(answer_text, str) or len(answer_text) < 10:
                        continue
                    # 检查答案中是否包含尚未被现有任务覆盖的关键词
                    for kw in high_value_keywords:
                        if kw in answer_text and kw not in existing_task_text:
                            new_dimensions.append((kw, answer_text[:60]))
                            break

                if new_dimensions:
                    # 按发现的新维度生成补充任务（最多2个）
                    for i, (kw, context) in enumerate(new_dimensions[:2]):
                        supplement_task = {
                            "id": f"task_gap_supplement_{i+1}",
                            "title": f"[补充] {kw}相关深度调研",
                            "description": f"Step3补充信息发现新关键维度（{kw}），需针对性调研: {context}...",
                            "task_type": "research",
                            "priority": "P1",
                            "source": "gap_backflow_v9.1",
                        }
                        gap_supplement_tasks.append(supplement_task)

                    # 追加到 confirmed_core_tasks
                    confirmed_tasks = confirmed_tasks + gap_supplement_tasks
                    logger.info(
                        f"🔄 [v9.1 G5] Gap回流: 发现 {len(new_dimensions)} 个新维度，"
                        f"补充 {len(gap_supplement_tasks)} 个任务"
                    )
                    for dim_kw, dim_ctx in new_dimensions[:2]:
                        logger.info(f"  ✚ {dim_kw}: {dim_ctx}")
                else:
                    logger.info("✅ [v9.1 G5] Gap回流: 补充信息未发现新关键维度，无需补充任务")
        except Exception as e:
            logger.warning(f"⚠️ [v9.1 G5] Gap回流分析失败: {e}，继续")

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
                "generation_source": gap_generation_source,
                "error_code": gap_error_code,
            },
            "gap_filling_answers": answers,
            "gap_filling_generation_source": gap_generation_source,
            "gap_filling_error_code": gap_error_code,
            "progressive_questionnaire_completed": False,  #  改为 False，因为还有雷达图步骤
            "progressive_questionnaire_step": 2,  #  这是 UI 的 Step 2
            # "questionnaire_summary": questionnaire_summary,  #  删除，改为在雷达图后生成
            "calibration_processed": False,  #  改为 False，雷达图完成后才算完成
        }
        # ⚠️ v9.1 G5: 如果gap回流产生了补充任务，更新 confirmed_core_tasks
        if gap_supplement_tasks:
            update_dict["confirmed_core_tasks"] = confirmed_tasks
        update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)

        #  v7.146: 修正路由 - Step2(信息补全)完成后进入Step3(雷达图)
        return Command(update=update_dict, goto="progressive_step2_radar")

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

        for i, dim_id in enumerate(gap_dimensions[:5]):  # 最多5个问题
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
    import json

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


def progressive_step1_core_task_node(state: ProjectAnalysisState, store: Optional[BaseStore] = None) -> Command:
    """Step 1 节点函数"""
    return ProgressiveQuestionnaireNode.step1_core_task(state, store)


def progressive_step2_radar_node(state: ProjectAnalysisState, store: Optional[BaseStore] = None) -> Command:
    """Step 2 节点函数"""
    return ProgressiveQuestionnaireNode.step2_radar(state, store)


def progressive_step3_gap_filling_node(state: ProjectAnalysisState, store: Optional[BaseStore] = None) -> Command:
    """Step 3 节点函数"""
    return ProgressiveQuestionnaireNode.step3_gap_filling(state, store)
