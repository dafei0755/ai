"""
需求洞察节点 (Requirements Insight Node)

原名：问卷汇总节点 (Questionnaire Summary Node)

职责：
1. 整合三步问卷的所有用户输入
2. 调用需求重构引擎生成结构化需求文档
3. 与AI初步分析进行对比/融合
4. 更新 structured_requirements 字段
5.  v7.151: 合并需求确认功能，支持用户直接编辑
6.  v7.151: 直接路由到 project_director（跳过独立的 requirements_confirmation）

流程位置：
    progressive_step2_info_gather
      → requirements_insight (本节点，原 questionnaire_summary)
      → [用户确认/编辑 interrupt]
      → project_director  ( v7.151: 直接路由，不再经过 requirements_confirmation)

v7.135: 首次实现
v7.147: 添加用户确认 interrupt
v7.151: 升级为"需求洞察"，合并需求确认功能
"""

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from langgraph.store.base import BaseStore
from langgraph.types import Command, interrupt
from loguru import logger

from ...core.state import ProjectAnalysisState

# v8.2: 动态步骤追踪装饰器
from ...utils.node_tracker import track_active_step
from .requirements_restructuring import RequirementsRestructuringEngine


class QuestionnaireSummaryNode:
    """
    需求洞察节点 (原问卷汇总节点)

     v7.151: 升级为需求洞察，合并需求确认功能
    - 支持用户直接编辑需求理解
    - 智能修改检测（<50字符微调 vs 重大修改）
    - 直接路由到 project_director
    """

    @staticmethod
    def execute(
        state: ProjectAnalysisState, store: Optional[BaseStore] = None
    ) -> Command[Literal["project_director", "requirements_analyst"]]:
        """
        执行需求重构并展示给用户确认/编辑

        Args:
            state: 项目分析状态
            store: 存储接口（可选）

        Returns:
            Command对象，指向下一个节点
            - 确认无修改/微调 → project_director
            - 重大修改 → requirements_analyst 重新分析
        """
        #  v7.143: 添加明确的入口日志
        logger.info("=" * 100)
        logger.info(" [需求洞察]  ENTERING questionnaire_summary node")
        logger.info("=" * 100)

        # 诊断：检查必要的前置数据是否存在
        confirmed_tasks = state.get("confirmed_core_tasks") or []
        # LT-3: 优先从 questionnaire_responses["gap_filling_answers"] 读取，兼容旧 checkpoint 顶层字段
        gap_filling = (
            (state.get("questionnaire_responses") or {}).get("gap_filling_answers")
            or state.get("gap_filling_answers")  # backward-compat: 旧 checkpoint 顶层字段
            or {}
        )
        selected_dims = state.get("selected_dimensions") or []

        logger.info(f" [前置数据检查]")
        logger.info(f"   - confirmed_core_tasks: {len(confirmed_tasks)}个")
        logger.info(f"   - gap_filling_answers: {len(gap_filling)}个字段(via questionnaire_responses)")
        logger.info(f"   - selected_dimensions: {len(selected_dims)}个")

        if not confirmed_tasks:
            logger.warning("️ [数据缺失] confirmed_core_tasks为空，可能影响生成质量")
        if not gap_filling:
            logger.warning("️ [数据缺失] gap_filling_answers为空，可能影响生成质量")
        if not selected_dims:
            logger.warning("️ [数据缺失] selected_dimensions为空，可能影响生成质量")

        logger.info("=" * 80)
        logger.info(" [需求洞察] 开始生成结构化需求文档")
        logger.info("=" * 80)

        # 1. 提取问卷数据
        questionnaire_data = QuestionnaireSummaryNode._extract_questionnaire_data(state)

        # 2. 提取AI分析（包含L1-L5洞察）-  v7.153: 增强多路径获取
        ai_analysis = state.get("requirement_analysis", {})
        analysis_layers = ai_analysis.get("analysis_layers", {})
        analysis_layers_source = "requirement_analysis" if analysis_layers else None

        #  v7.153: 多路径备选获取 analysis_layers
        if not analysis_layers:
            # 路径2: agent_results.requirements_analyst
            agent_results = state.get("agent_results", {})
            requirements_analyst_result = agent_results.get("requirements_analyst", {})
            analysis_layers = requirements_analyst_result.get("analysis_layers", {})
            if analysis_layers:
                analysis_layers_source = "agent_results.requirements_analyst"

        if not analysis_layers:
            # 路径3: structured_requirements.analysis_layers
            # v9.3 fix: state.get(key, {}) 在 key 存在但值为 None 时仍返回 None，用 or {} 强制兜底
            structured_reqs = state.get("structured_requirements") or {}
            if not isinstance(structured_reqs, dict):
                logger.warning(f"⚠️ structured_requirements 类型异常 ({type(structured_reqs).__name__})，强制降级为空 dict")
                structured_reqs = {}
            analysis_layers = structured_reqs.get("analysis_layers", {})
            if analysis_layers:
                analysis_layers_source = "structured_requirements"

        if not analysis_layers:
            # 路径4: 直接从 state 顶层获取
            analysis_layers = state.get("analysis_layers", {})
            if analysis_layers:
                analysis_layers_source = "state.analysis_layers"

        #  v7.153: 详细日志记录获取结果
        if analysis_layers:
            logger.info(f" [analysis_layers] 成功获取，来源: {analysis_layers_source}")
            logger.info(f"   - L1_facts: {len(analysis_layers.get('L1_facts', []))} 项")
            logger.info(f"   - L2_user_model: {'有' if analysis_layers.get('L2_user_model') else '无'}")
            logger.info(f"   - L3_core_tension: {'有' if analysis_layers.get('L3_core_tension') else '无'}")
            logger.info(f"   - L4_project_task: {'有' if analysis_layers.get('L4_project_task') else '无'}")
            logger.info(f"   - L5_sharpness: {'有' if analysis_layers.get('L5_sharpness') else '无'}")
        else:
            logger.warning("️ [analysis_layers] 所有路径均未获取到数据，将使用降级模式")
            logger.warning(
                f"   已尝试路径: requirement_analysis, agent_results.requirements_analyst, structured_requirements, state.analysis_layers"
            )

        user_input = state.get("user_input", "")

        # 3. 执行需求重构
        try:
            #  v7.142: LLM调用的超时保护在 RequirementsRestructuringEngine._llm_generate_one_sentence 中实现
            # 双重超时保护：SDK timeout (15s) + ThreadPool timeout (20s)
            restructured_doc = RequirementsRestructuringEngine.restructure(
                questionnaire_data, ai_analysis, analysis_layers, user_input, use_llm=True  # 启用LLM优化描述
            )
        except Exception as e:
            logger.error(f" 需求重构失败: {e}")
            import traceback

            #  v7.149: 增强异常日志 - 记录完整堆栈到日志文件
            logger.error(f"异常堆栈:\n{traceback.format_exc()}")
            traceback.print_exc()

            # 降级：返回简化版本
            logger.warning("️ [降级模式] 使用简化需求重构")
            restructured_doc = QuestionnaireSummaryNode._fallback_restructure(
                questionnaire_data, ai_analysis, user_input
            )

        # 4. 生成简洁摘要（用于日志和前端快速展示）
        summary_text = QuestionnaireSummaryNode._generate_summary_text(restructured_doc)

        # 5. 更新 structured_requirements（融合重构文档）
        # v9.3 fix: 同 line 108，or {} 防止 key 存在但值为 None 时传入 None
        enhanced_requirements = QuestionnaireSummaryNode._update_structured_requirements(
            state.get("structured_requirements") or {}, restructured_doc
        )

        logger.info(f" 需求洞察完成")
        logger.info(f" 项目目标: {restructured_doc['project_objectives']['primary_goal'][:50]}...")
        logger.info(f" 设计重点: {len(restructured_doc['design_priorities'])}个维度")
        logger.info(f"️  风险识别: {len(restructured_doc['identified_risks'])}项")
        logger.info(f" 洞察评分: {restructured_doc['insight_summary']['L5_sharpness_score']}")

        #  v7.143: 添加明确的出口日志
        #  v7.147: 添加用户确认 interrupt
        #  v7.152: 添加 progressive_questionnaire_completed 确保问卷流程完整标记
        update_dict = {
            "restructured_requirements": restructured_doc,
            "requirements_summary_text": summary_text,
            "structured_requirements": enhanced_requirements,
            "questionnaire_summary_completed": True,
            "progressive_questionnaire_completed": True,  #  v7.152: 确保问卷完成标记
            "progressive_questionnaire_step": 4,  #  v7.152: 标记当前步骤
            "detail": "需求洞察与需求重构完成",
        }

        #  v7.144: 使用 WorkflowFlagManager 保留关键状态，防止覆盖
        from ...core.workflow_flags import WorkflowFlagManager

        update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)

        logger.info("=" * 100)
        logger.info(" [需求洞察]  Data prepared, showing to user for confirmation/editing")
        logger.info(f"   返回字段: {list(update_dict.keys())}")
        logger.info("=" * 100)

        #  v7.151: 升级为需求洞察交互，支持编辑
        # 🆕 v13.0: 应用任务校正 + 构建复盘对象
        confirmed_core_tasks = state.get("confirmed_core_tasks", [])
        snapshot = state.get("step1_confirmed_tasks_snapshot") or []
        radar_values = state.get("radar_dimension_values") or {}
        selected_dims_for_review = state.get("selected_dimensions") or []

        # 🆕 v14.0: 权重语义翻译 — 将数值比例转为设计驱动力
        from ...services.weight_semantic_translator import WeightSemanticTranslator

        translator = WeightSemanticTranslator()
        selected_radar_dims = state.get("selected_radar_dimensions") or selected_dims_for_review
        weight_interpretations = translator.translate(
            radar_dimension_values=radar_values,
            selected_radar_dimensions=selected_radar_dims,
        )
        logger.info(f"🎯 [v14.0] 权重语义翻译完成: {list(weight_interpretations.get('_summary', {}).keys())}")

        # 从 restructured_doc 提取 LLM/规则生成的 task_corrections
        task_corrections = restructured_doc.get("task_corrections", [])

        # 应用校正并构建复盘
        corrected_tasks, calibration_review = QuestionnaireSummaryNode._apply_corrections_and_build_review(
            snapshot=snapshot,
            current_tasks=confirmed_core_tasks,
            task_corrections=task_corrections,
            gap_filling=gap_filling,
            radar_values=radar_values,
            selected_dims=selected_dims_for_review,
            restructured_doc=restructured_doc,
            weight_interpretations=weight_interpretations,
        )

        # 更新 update_dict 中的 confirmed_core_tasks 为校正后版本
        update_dict["confirmed_core_tasks"] = corrected_tasks
        update_dict["task_calibration_review"] = calibration_review

        # 🆕 v14.0: 写入权重翻译结果 + 响应清单到 state
        update_dict["weight_interpretations"] = weight_interpretations
        update_dict["weight_response_manifest"] = translator.build_initial_manifest(weight_interpretations)

        task_groups = state.get("task_groups", [])
        # 若 state 中无 task_groups，按 category 字段自动分组（基于校正后任务）
        if not task_groups and corrected_tasks:
            from collections import defaultdict

            cat_map: dict = defaultdict(list)
            for t in corrected_tasks:
                cat = t.get("category") or "基础调研"
                cat_map[cat].append(t.get("id", ""))
            task_groups = [{"category": cat, "task_ids": ids} for cat, ids in cat_map.items()]

        payload = {
            "interaction_type": "requirements_insight",  #  新交互类型
            "step": 4,
            "total_steps": 4,
            "title": "需求洞察",  #  更名
            "message": calibration_review.get("summary_line", "AI 已综合您的补充信息和偏好，完成需求校正"),
            # 🆕 v13.0: 校正后的任务列表（替代原始 confirmed_core_tasks）
            "confirmed_core_tasks": corrected_tasks,
            "task_groups": task_groups,
            # 🆕 v13.0: 复盘对象（前端渲染复盘面板）
            "task_calibration_review": calibration_review,
            #  保留：供下游节点（deliverable_id_generator 等）消费，以及深度洞察折叠区
            "restructured_requirements": restructured_doc,
            "requirements_summary_text": summary_text,
            #  v7.151: 新增深度洞察字段
            "project_essence": restructured_doc.get("project_essence", ""),
            "implicit_requirements": restructured_doc.get("implicit_requirements", []),
            "key_conflicts": restructured_doc.get("key_conflicts", []),
            #  v7.151: 支持编辑的选项
            "editable_fields": ["primary_goal", "core_tension", "design_priorities"],
            "options": {"confirm": "确认无误，开始专家分析", "edit": "修改理解"},
        }

        logger.info(" [需求洞察] 即将调用 interrupt()，等待用户确认/编辑...")
        user_response = interrupt(payload)
        logger.info(f" [需求洞察] 收到用户响应: {type(user_response)}")

        #  v7.151: 处理用户响应（合并自 requirements_confirmation）
        return QuestionnaireSummaryNode._handle_user_response(state, update_dict, restructured_doc, user_response)

    @staticmethod
    def _handle_user_response(
        state: ProjectAnalysisState, update_dict: Dict[str, Any], restructured_doc: Dict[str, Any], user_response: Any
    ) -> Command:
        """
         v7.151: 处理用户响应（合并自 requirements_confirmation）

        - 确认无修改 → project_director
        - 微调(<50字符) → 更新本地状态，继续到 project_director
        - 重大修改(>=50字符) → requirements_analyst 重新分析
        """
        from ...services.capability_boundary_service import CapabilityBoundaryService, CheckType

        is_approved = False
        modifications = {}

        if isinstance(user_response, str):
            is_approved = user_response in ["confirm", "approve"]
        elif isinstance(user_response, dict):
            intent = user_response.get("intent") or user_response.get("action", "")
            is_approved = intent in ["confirm", "approve"]
            modifications = user_response.get("modifications", {})

        # 计算修改量
        total_diff_chars = 0
        if modifications:
            for field, new_value in modifications.items():
                old_value = ""
                if field == "primary_goal":
                    old_value = restructured_doc.get("project_objectives", {}).get("primary_goal", "")
                elif field == "core_tension":
                    old_value = restructured_doc.get("core_tension", {}).get("description", "")

                # 计算差异字符数：长度差 + 内容差异
                diff = abs(len(str(new_value)) - len(str(old_value)))
                diff += sum(1 for a, b in zip(str(new_value), str(old_value)) if a != b)
                total_diff_chars += diff

        has_major_modification = total_diff_chars >= 50
        has_minor_modification = 0 < total_diff_chars < 50
        no_modification = total_diff_chars == 0

        logger.info(f" [需求洞察] 修改分析: 差异字符数={total_diff_chars}, 重大修改={has_major_modification}")

        #  v7.151: 修正逻辑 - 重大修改优先于确认意图
        if has_major_modification:
            # 重大修改：返回 requirements_analyst 重新分析
            logger.info(" [需求洞察] 检测到重大修改(>=50字符)，返回需求分析师重新分析")

            # 将修改追加到 user_input
            original_input = state.get("user_input", "")
            mod_text = "\n".join([f"- {k}: {v}" for k, v in modifications.items()])
            update_dict["user_input"] = f"{original_input}\n\n【用户修改补充 v7.151】\n{mod_text}"
            update_dict["requirements_confirmed"] = False
            update_dict["has_user_modifications"] = True
            update_dict["user_modification_processed"] = True

            # 能力边界检查
            if modifications:
                mod_text_check = "\n".join([f"{k}: {v}" for k, v in modifications.items()])
                boundary_check = CapabilityBoundaryService.check_user_input(
                    user_input=mod_text_check,
                    context={"node": "requirements_insight", "modification_type": "major"},
                    check_type=CheckType.DELIVERABLE_ONLY,
                )
                if not boundary_check.within_capability:
                    alert = CapabilityBoundaryService.generate_boundary_alert(boundary_check)
                    update_dict["boundary_alert"] = alert
                    logger.warning(f"️ 用户修改包含超出能力的需求: {alert['message']}")

            return Command(update=update_dict, goto="requirements_analyst")

        elif is_approved or has_minor_modification:
            # 确认或微调：直接前进到 project_director
            if has_minor_modification:
                logger.info("️ [需求洞察] 检测到微调(<50字符)，更新本地状态")
                # 将微调融入 update_dict
                if "primary_goal" in modifications:
                    update_dict["restructured_requirements"]["project_objectives"]["primary_goal"] = modifications[
                        "primary_goal"
                    ]
                    update_dict["structured_requirements"]["project_task"] = modifications["primary_goal"]

                # 保存用户调整记录
                update_dict["user_requirement_adjustments"] = modifications

            update_dict["requirements_confirmed"] = True

            # 触发分类学习收集（fire-and-forget，不阻塞主流程）
            try:
                import asyncio

                from ...services.taxonomy_learning_collector import get_learning_collector

                session_id = state.get("session_id", "unknown")
                user_input = state.get("user_input", "")
                questionnaire_data = QuestionnaireSummaryNode._extract_questionnaire_data(state)

                collector = get_learning_collector()

                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(collector.collect_from_questionnaire(session_id, user_input, questionnaire_data))
                except RuntimeError:
                    # 无事件循环，同步运行
                    asyncio.run(collector.collect_from_questionnaire(session_id, user_input, questionnaire_data))

                logger.info(f" [自学习] 已触发分类学习收集: session={session_id}")
            except Exception as e:
                logger.warning(f" [自学习] 分类学习收集触发失败（不影响主流程）: {e}")

            logger.info("=" * 100)
            logger.info(" [需求洞察]  User confirmed, proceeding to project_director")
            logger.info("=" * 100)

            return Command(update=update_dict, goto="project_director")

        else:
            # 拒绝：也返回重新分析
            logger.info("️ [需求洞察] 用户拒绝当前理解，返回需求分析师")
            update_dict["requirements_confirmed"] = False
            return Command(update=update_dict, goto="requirements_analyst")

    @staticmethod
    def _extract_questionnaire_data(state: ProjectAnalysisState) -> Dict[str, Any]:
        """提取三步问卷的所有数据"""

        # Step1: 核心任务
        confirmed_tasks = state.get("confirmed_core_tasks") or []

        # Step2: 信息补全（LT-3: 优先从 questionnaire_responses["gap_filling_answers"] 读取）
        gap_filling = (
            (state.get("questionnaire_responses") or {}).get("gap_filling_answers")
            or state.get("gap_filling_answers")  # backward-compat: 旧 checkpoint 顶层字段
            or {}
        )

        # Step3: 雷达维度
        selected_dims = state.get("selected_dimensions") or []
        #  v7.150: 修复字段名 - 从 dimension_weights 改为 radar_dimension_values
        # step3_radar 保存的是 radar_dimension_values，而非 dimension_weights
        dimension_weights = state.get("radar_dimension_values") or state.get("dimension_weights") or {}

        # 🔄 v10.2: 输出意图（优先 structured_requirements.output_intent，回退到顶层字段）
        structured_req = state.get("structured_requirements") or {}
        output_intent = structured_req.get("output_intent")
        if not output_intent:
            # 回退：从顶层字段组装
            active_projs = state.get("active_projections") or []
            identity_modes = state.get("detected_identity_modes") or []
            if active_projs or identity_modes:
                output_intent = {
                    "active_projections": active_projs,
                    "identity_modes": [m.get("id", "") for m in identity_modes],
                    "identity_mode_details": identity_modes,
                    "source": "fallback_top_level_fields",
                }

        logger.info(f" 问卷数据提取:")
        logger.info(f"   - 核心任务: {len(confirmed_tasks)}个")
        logger.info(f"   - 信息补全: {len(gap_filling)}个字段")
        logger.info(f"   - 雷达维度: {len(selected_dims)}个")
        logger.info(f"   - 维度权重: {len(dimension_weights)}个")
        logger.info(f"   - 输出意图: {'有' if output_intent else '无'}")

        return {
            "core_tasks": confirmed_tasks,
            "gap_filling": gap_filling,
            "dimensions": {"selected": selected_dims, "weights": dimension_weights},
            "output_intent": output_intent,  # 🔄 v10.2
            "questionnaire_step": state.get("progressive_questionnaire_step", 0),
        }

    # ==================== 🆕 v13.0: 任务校正 + 复盘构建 ====================

    @staticmethod
    def _apply_corrections_and_build_review(
        snapshot: list,
        current_tasks: list,
        task_corrections: list,
        gap_filling: dict,
        radar_values: dict,
        selected_dims: list,
        restructured_doc: dict,
        weight_interpretations: dict = None,
    ) -> tuple:
        """
        应用任务校正指令并构建复盘对象。

        Returns:
            (corrected_tasks, task_calibration_review)
        """
        import copy

        # --- 1. 深拷贝当前任务列表作为工作副本 ---
        corrected = copy.deepcopy(current_tasks) if current_tasks else []
        task_by_id = {t.get("id"): t for t in corrected if t.get("id")}

        # --- 2. 应用校正指令 ---
        applied_actions = {}  # task_id -> action
        add_tasks = []

        for corr in task_corrections or []:
            action = corr.get("action", "")
            task_id = corr.get("task_id")

            if action == "reprioritize" and task_id and task_id in task_by_id:
                new_pri = corr.get("new_priority", "medium")
                task_by_id[task_id]["priority"] = new_pri
                task_by_id[task_id]["_correction_action"] = "reprioritized"
                task_by_id[task_id]["_correction_reason"] = corr.get("reason", "")
                applied_actions[task_id] = "reprioritized"

            elif action == "enhance" and task_id and task_id in task_by_id:
                note = corr.get("enhance_note", "")
                if note:
                    old_desc = task_by_id[task_id].get("description", "")
                    task_by_id[task_id]["description"] = f"{old_desc}（{note}）" if old_desc else note
                task_by_id[task_id]["_correction_action"] = "enhanced"
                task_by_id[task_id]["_correction_reason"] = corr.get("reason", "")
                applied_actions[task_id] = "enhanced"

            elif action == "invalidate" and task_id and task_id in task_by_id:
                task_by_id[task_id]["_correction_action"] = "invalidated"
                task_by_id[task_id]["_correction_reason"] = corr.get("reason", "")
                applied_actions[task_id] = "invalidated"

            elif action == "add":
                new_task = {
                    "id": f"task_correction_add_{len(add_tasks) + 1}",
                    "title": corr.get("title", "新增任务"),
                    "description": corr.get("description", ""),
                    "priority": corr.get("new_priority", "medium"),
                    "task_type": "research",
                    "source": "task_correction_v13",
                    "_correction_action": "added",
                    "_correction_reason": corr.get("reason", ""),
                }
                add_tasks.append(new_task)

        # 限制新增任务数量
        add_tasks = add_tasks[:3]

        # 给未标记的任务打 "unchanged" 标签
        for t in corrected:
            if "_correction_action" not in t:
                t["_correction_action"] = "unchanged"

        # 追加新增任务
        corrected.extend(add_tasks)

        # 重新编号 execution_order
        for idx, t in enumerate(corrected):
            t["execution_order"] = idx + 1

        # --- 3. 与 snapshot 对比，构建复盘对象 ---
        baseline = snapshot or current_tasks or []
        baseline_ids = {t.get("id") for t in baseline if t.get("id")}
        baseline_titles = {t.get("title", "").strip().lower() for t in baseline}
        current_ids = {t.get("id") for t in corrected if t.get("id")}

        # 增加：在 corrected 中但不在 baseline 中的任务
        added_items = []
        for t in corrected:
            tid = t.get("id", "")
            title = t.get("title", "").strip().lower()
            if tid and tid not in baseline_ids and not tid.startswith("task_correction_add_"):
                # gap_backflow 补充的任务
                added_items.append(
                    {
                        "title": t.get("title", ""),
                        "source": t.get("source", "gap_backflow"),
                        "reason": f"信息补全阶段发现新维度，自动补充",
                    }
                )
            elif tid and tid.startswith("task_correction_add_"):
                added_items.append(
                    {
                        "title": t.get("title", ""),
                        "source": "task_correction",
                        "reason": t.get("_correction_reason", "需求洞察阶段综合分析后新增"),
                    }
                )
            elif not tid and title and title not in baseline_titles:
                added_items.append(
                    {
                        "title": t.get("title", ""),
                        "source": "unknown",
                        "reason": "新增任务",
                    }
                )

        # 删减/无效：被标记为 invalidated 的任务
        invalidated_items = [
            {"title": t.get("title", ""), "reason": t.get("_correction_reason", "需求洞察后判定为无效动作")}
            for t in corrected
            if t.get("_correction_action") == "invalidated"
        ]

        # 优化：从 constraints 提取（信息补全的策略层增益）
        optimized_items = []
        constraints = restructured_doc.get("constraints", {}) or {}
        constraint_labels = {"budget": "预算边界明确", "timeline": "工期节点明确", "space": "空间条件明确"}
        for ck, cl in constraint_labels.items():
            cv = constraints.get(ck)
            if cv and isinstance(cv, dict):
                total_or_dur = cv.get("total") or cv.get("duration") or cv.get("area") or ""
                if total_or_dur and str(total_or_dur).lower() not in ("null", "none", ""):
                    optimized_items.append(
                        {
                            "label": cl,
                            "evidence": str(total_or_dur)[:60],
                            "source": "gap_filling",
                        }
                    )

        # 🔄 v14.0: 强化 — 从权重翻译结果提取设计驱动力（替代原始 weight 数字）
        strengthened_items = []
        wi = weight_interpretations or {}
        summary = wi.get("_summary", {})
        core_drivers = summary.get("core_drivers", [])
        important_dims = summary.get("important", [])
        for dim_id in (core_drivers + important_dims)[:4]:
            dim_info = wi.get(dim_id, {})
            strengthened_items.append(
                {
                    "label": dim_info.get("dimension_label", dim_id),
                    "design_driver": dim_info.get("design_intent", ""),
                    "tendency_label": dim_info.get("tendency_label", ""),
                    "tier_label": dim_info.get("tier", "important"),
                    "source": "radar_weight_translation",
                }
            )

        # --- 4. 效果检验 --- (🔄 v14.0: 基于覆盖率而非数量)
        gap_answer_count = len([k for k, v in gap_filling.items() if v and not str(k).startswith("_")])
        radar_dim_count = len(radar_values) if radar_values else 0

        added_count = len(added_items)
        invalidated_count = len(invalidated_items)
        optimized_count = len(optimized_items)
        strengthened_count = len(strengthened_items)

        gap_effective = (gap_answer_count > 0) and (added_count > 0 or optimized_count > 0)

        # 🔄 v14.0: radar_effective 基于覆盖率（core_driver 维度是否全部在 task_corrections 中被响应）
        responded_dim_ids = set()
        for corr in task_corrections or []:
            for tag in corr.get("tags") or []:
                if isinstance(tag, str):
                    responded_dim_ids.add(tag)
        all_core = set(summary.get("core_drivers", []))
        coverage_rate = len(all_core & responded_dim_ids) / max(len(all_core), 1)
        radar_effective = coverage_rate >= 0.9

        # 🆕 v14.0: 构建维度响应对账（radar_response_ledger）
        radar_response_ledger = []
        for dim_id in core_drivers + important_dims:
            dim_info = wi.get(dim_id, {})
            actions = [c.get("action", "") for c in (task_corrections or []) if dim_id in (c.get("tags") or [])]
            radar_response_ledger.append(
                {
                    "dimension_id": dim_id,
                    "dimension_label": dim_info.get("dimension_label", dim_id),
                    "tier": dim_info.get("tier", ""),
                    "design_driver": dim_info.get("design_intent", ""),
                    "responded": len(actions) > 0,
                    "actions": actions[:3],
                }
            )

        # Top dimensions for evidence (v14.0: 用设计驱动力替代数字)
        top_dims = []
        for dim_id in core_drivers[:3]:
            dim_info = wi.get(dim_id, {})
            top_dims.append(dim_info.get("tendency_label", dim_id))

        # --- 5. 生成 summary_line ---
        parts = []
        if added_count > 0:
            parts.append(f"新增{added_count}项")
        if invalidated_count > 0:
            parts.append(f"识别{invalidated_count}项无效动作")
        change_part = "、".join(parts) if parts else "未发生明显任务增删"

        opt_part = f"信息补全促成{optimized_count}项约束优化" if optimized_count > 0 else "信息补全已纳入策略考量"
        str_part = f"偏好雷达图强化{strengthened_count}项优先方向" if strengthened_count > 0 else "偏好权重已融入设计优先级"

        summary_line = f"相较任务梳理阶段，{change_part}；{opt_part}，{str_part}。"

        # --- 6. 构建 review 对象 ---
        review = {
            "counts": {
                "before": len(baseline),
                "after": len(corrected),
                "added": added_count,
                "invalidated": invalidated_count,
                "optimized": optimized_count,
                "strengthened": strengthened_count,
            },
            "added_items": added_items[:5],
            "invalidated_items": invalidated_items[:5],
            "optimized_items": optimized_items[:5],
            "strengthened_items": strengthened_items[:4],
            # 🆕 v14.0: 维度响应对账
            "radar_response_ledger": radar_response_ledger,
            "effectiveness": {
                "gap_filling_effective": gap_effective,
                "radar_effective": radar_effective,
                "gap_evidence": {
                    "answer_count": gap_answer_count,
                    "constraints_filled": optimized_count,
                },
                "radar_evidence": {
                    "dimension_count": radar_dim_count,
                    "top_dimensions": top_dims,
                    # 🆕 v14.0: 扩展雷达证据
                    "adjusted_dimensions": list(all_core | set(important_dims)),
                    "responded_dimensions": list(responded_dim_ids),
                    "coverage_rate": round(coverage_rate, 2),
                    "unresponded_dimensions": [d for d in all_core if d not in responded_dim_ids],
                },
            },
            "summary_line": summary_line,
        }

        logger.info(
            f"🔄 [v13.0 复盘] 校正应用完成: +{added_count} /{invalidated_count}无效 /{optimized_count}优化 /{strengthened_count}强化"
        )
        logger.info(f"   summary: {summary_line}")

        return corrected, review

    @staticmethod
    def _fallback_restructure(
        questionnaire_data: Dict[str, Any], ai_analysis: Dict[str, Any], user_input: str
    ) -> Dict[str, Any]:
        """降级重构逻辑（当主流程失败时）"""

        logger.warning("️ 使用降级重构逻辑")

        tasks = questionnaire_data.get("core_tasks", [])
        primary_goal = tasks[0].get("title", "待明确") if tasks else "待明确核心目标"

        return {
            "metadata": {
                "document_version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "generation_method": "fallback_restructure",
                "data_sources": ["user_questionnaire"],
            },
            "project_objectives": {
                "primary_goal": primary_goal,
                "primary_goal_source": "fallback",
                "secondary_goals": [t.get("title", "") for t in tasks[1:3]],
                "success_criteria": ["满足核心需求"],
            },
            "constraints": {},
            "design_priorities": [],
            "core_tension": {},
            "special_requirements": [],
            "identified_risks": [],
            "insight_summary": {
                "L1_key_facts": [],
                "L2_user_profile": {},
                "L3_core_tension": "",
                "L4_project_task_jtbd": "",
                "L5_sharpness_score": 0,
                "L5_sharpness_note": "降级模式",
            },
            "deliverable_expectations": ["设计策略文档"],
            "executive_summary": {
                "one_sentence": primary_goal,
                "what": primary_goal,
                "why": "满足用户需求",
                "how": "系统化设计",
                "constraints_summary": "待明确",
            },
        }

    @staticmethod
    def _generate_summary_text(doc: Dict[str, Any]) -> str:
        """生成文本摘要（用于日志和快速展示）"""

        objectives = doc.get("project_objectives", {})
        constraints = doc.get("constraints", {})
        priorities = doc.get("design_priorities", [])

        summary_parts = []

        # 目标部分
        primary_goal = objectives.get("primary_goal", "待明确")
        summary_parts.append(f"【项目目标】\n{primary_goal}")

        # 约束部分
        if constraints:
            constraint_texts = []
            if "budget" in constraints:
                constraint_texts.append(f"预算: {constraints['budget']['total']}")
            if "timeline" in constraints:
                constraint_texts.append(f"时间: {constraints['timeline']['duration']}")
            if "space" in constraints:
                constraint_texts.append(f"空间: {constraints['space']['area']}")

            if constraint_texts:
                summary_parts.append(f"\n【核心约束】\n" + " | ".join(constraint_texts))

        # 重点部分
        if priorities:
            priority_texts = [f"{p['label']}({int(p['weight']*100)}%)" for p in priorities[:3]]
            summary_parts.append(f"\n【设计重点】\n" + " > ".join(priority_texts))

        return "\n".join(summary_parts)

    @staticmethod
    def _update_structured_requirements(existing: Dict[str, Any], restructured_doc: Dict[str, Any]) -> Dict[str, Any]:
        """更新structured_requirements字段（融合重构文档）

        🔄 v7.900: 增加置信度加权合并逻辑
        - 高置信度 Phase2 分析 → 直接采纳
        - 中置信度 Phase2 分析 + 问卷 → 合并补充
        - 低置信度 Phase2 分析 → 被问卷结果覆盖
        """

        updated = existing.copy() if existing else {}

        # 🔄 v7.900: 获取 info_quality_metadata 和 uncertainty_map
        info_quality_metadata = existing.get("info_quality_metadata", {})
        uncertainty_map = existing.get("uncertainty_map", {})
        confidence_level = info_quality_metadata.get("confidence_level", "medium")

        if info_quality_metadata or uncertainty_map:
            logger.info(f"🔍 [v7.900] 合并策略: confidence_level={confidence_level}, " f"{len(uncertainty_map)}项不确定性")

        # 更新核心字段
        objectives = restructured_doc.get("project_objectives", {})
        if objectives.get("primary_goal"):
            # 🔄 v7.900: 检查 project_task 的置信度
            if uncertainty_map.get("project_task") == "high" or uncertainty_map.get("l2_用户身份") == "high":
                # Phase2 推测性强，优先采纳问卷结果
                logger.info("🔄 [v7.900] project_task 高不确定性，优先采纳问卷重构结果")
                updated["project_task"] = objectives["primary_goal"]
            elif existing.get("project_task") and confidence_level in ["very_high", "high"]:
                # Phase2 置信度高，保留 Phase2 分析
                logger.info("🔄 [v7.900] project_task 高置信度，保留 Phase2 分析")
                # 不覆盖，保留 existing 中的值
            else:
                # 中低置信度，采纳问卷结果
                updated["project_task"] = objectives["primary_goal"]

        constraints = restructured_doc.get("constraints", {})

        # 🔄 v7.900: 预算约束的置信度合并
        if "budget" in constraints:
            budget_uncertainty = uncertainty_map.get("预算范围", uncertainty_map.get("预算", "medium"))
            if budget_uncertainty in ["high", "medium"]:
                # 预算不确定性高，采纳问卷补充
                updated["budget_range"] = constraints["budget"]["total"]
                if constraints["budget"].get("breakdown"):
                    updated["budget_breakdown"] = constraints["budget"]["breakdown"]
                logger.info(f"🔄 [v7.900] 预算信息({budget_uncertainty}不确定性)，采纳问卷补充")
            elif existing.get("budget_range"):
                # Phase2 已有预算分析且置信度高，合并
                logger.info("🔄 [v7.900] 预算信息(Phase2已有)，保持 Phase2 + 问卷合并")
                updated["budget_range"] = constraints["budget"]["total"]

        # 🔄 v7.900: 工期约束的置信度合并
        if "timeline" in constraints:
            timeline_uncertainty = uncertainty_map.get("工期", uncertainty_map.get("时间约束", "medium"))
            if timeline_uncertainty in ["high", "medium"] or not existing.get("timeline"):
                updated["timeline"] = constraints["timeline"]["duration"]
                logger.info(f"🔄 [v7.900] 工期信息({timeline_uncertainty}不确定性)，采纳问卷补充")

        # 🔄 v7.900: 空间约束的置信度合并
        if "space" in constraints:
            space_uncertainty = uncertainty_map.get("空间约束", uncertainty_map.get("物理环境", "low"))
            if space_uncertainty in ["high", "medium"]:
                updated["space_area"] = constraints["space"]["area"]
                if constraints["space"].get("layout"):
                    updated["space_layout"] = constraints["space"]["layout"]
                logger.info(f"🔄 [v7.900] 空间信息({space_uncertainty}不确定性)，采纳问卷补充")
            elif existing.get("physical_context") and confidence_level in ["very_high", "high"]:
                # Phase2 的 physical_context 置信度高，保留
                logger.info("🔄 [v7.900] 空间信息(Phase2高置信)，保留 Phase2 分析")
                # 仍然更新 space_area（问卷更精确）
                updated["space_area"] = constraints["space"]["area"]

        # 添加设计重点（问卷总是更精确）
        priorities = restructured_doc.get("design_priorities", [])
        if priorities:
            updated["design_focus"] = [p["label"] for p in priorities[:3]]
            # v8.1: 保留完整结构体（含维度ID、权重、key_requirements），供 project_director / search_strategy 等下游读取
            updated["design_priorities_structured"] = priorities

        # v3.0: B层映射 - 补充下游消费者需要的字段

        # project_overview ← executive_summary.one_sentence (project_director, result_aggregator)
        exec_summary = restructured_doc.get("executive_summary", {})
        if exec_summary.get("one_sentence"):
            updated["project_overview"] = exec_summary["one_sentence"]

        # core_objectives ← [primary_goal] + secondary_goals (project_director, result_aggregator)
        if objectives.get("primary_goal"):
            secondary = objectives.get("secondary_goals", [])
            updated["core_objectives"] = [objectives["primary_goal"]] + (
                secondary if isinstance(secondary, list) else []
            )

        # functional_requirements ← design_priorities[].key_requirements 展平 (project_director)
        if priorities:
            func_reqs = []
            for p in priorities:
                for req in p.get("key_requirements", []):
                    if req and req not in func_reqs:
                        func_reqs.append(req)
            if func_reqs:
                updated["functional_requirements"] = func_reqs[:10]

        # character_narrative ← project_essence + L2 user model (core_task_decomposer, strategy_generator)
        project_essence = restructured_doc.get("project_essence", "")
        if project_essence:
            insight_summary = restructured_doc.get("insight_summary", {})
            l2_profile = insight_summary.get("L2_user_profile", {})
            narrative_parts = [project_essence]
            if l2_profile.get("psychological"):
                narrative_parts.append(f"心理需求: {l2_profile['psychological']}")
            if l2_profile.get("aesthetic"):
                narrative_parts.append(f"审美偏好: {l2_profile['aesthetic']}")
            updated["character_narrative"] = "。".join(narrative_parts)

        # business_goals ← project_objectives (ClientReviewer)
        if objectives.get("primary_goal"):
            goals = [objectives["primary_goal"]]
            for g in objectives.get("secondary_goals", [])[:2]:
                if g:
                    goals.append(g)
            updated["business_goals"] = "；".join(goals)

        # constraints 保持嵌套结构 (project_director, result_aggregator)
        if constraints:
            updated["constraints"] = constraints

        # 标记来源
        updated["_source"] = "questionnaire_restructured"
        updated["_restructured_at"] = restructured_doc.get("metadata", {}).get("generated_at", "")
        updated["_questionnaire_enhanced"] = True
        # 🔄 v7.900: 保留质量元数据
        updated["_confidence_level"] = confidence_level
        updated["_merge_strategy"] = "confidence_weighted"

        return updated


# 便捷函数（用于工作流节点调用）
@track_active_step("questionnaire_summary")
def questionnaire_summary_node(
    state: ProjectAnalysisState, store: Optional[BaseStore] = None
) -> Command[Literal["project_director", "requirements_analyst"]]:
    """问卷汇总节点函数

     v7.152: 修复返回类型声明，正确返回 Command 对象以支持动态路由
    - 确认/微调 → project_director
    - 重大修改 → requirements_analyst
    """
    return QuestionnaireSummaryNode.execute(state, store)
