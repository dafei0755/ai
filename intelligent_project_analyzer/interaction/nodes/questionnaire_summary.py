"""
需求洞察节点 (Requirements Insight Node)

原名：问卷汇总节点 (Questionnaire Summary Node)

职责：
1. 整合三步问卷的所有用户输入
2. 调用需求重构引擎生成结构化需求文档
3. 与AI初步分析进行对比/融合
4. 更新 structured_requirements 字段
5. 🆕 v7.151: 合并需求确认功能，支持用户直接编辑
6. 🆕 v7.151: 直接路由到 project_director（跳过独立的 requirements_confirmation）

流程位置：
    progressive_step3_gap_filling
      → requirements_insight (本节点，原 questionnaire_summary)
      → [用户确认/编辑 interrupt]
      → project_director  (🆕 v7.151: 直接路由，不再经过 requirements_confirmation)

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
from .requirements_restructuring import RequirementsRestructuringEngine


class QuestionnaireSummaryNode:
    """
    需求洞察节点 (原问卷汇总节点)

    🆕 v7.151: 升级为需求洞察，合并需求确认功能
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
        # 🔧 v7.143: 添加明确的入口日志
        logger.info("=" * 100)
        logger.info("📋 [需求洞察] ✅ ENTERING questionnaire_summary node")
        logger.info("=" * 100)

        # 诊断：检查必要的前置数据是否存在
        confirmed_tasks = state.get("confirmed_core_tasks", [])
        gap_filling = state.get("gap_filling_answers", {})
        selected_dims = state.get("selected_dimensions", [])

        logger.info(f"🔍 [前置数据检查]")
        logger.info(f"   - confirmed_core_tasks: {len(confirmed_tasks)}个")
        logger.info(f"   - gap_filling_answers: {len(gap_filling)}个字段")
        logger.info(f"   - selected_dimensions: {len(selected_dims)}个")

        if not confirmed_tasks:
            logger.warning("⚠️ [数据缺失] confirmed_core_tasks为空，可能影响生成质量")
        if not gap_filling:
            logger.warning("⚠️ [数据缺失] gap_filling_answers为空，可能影响生成质量")
        if not selected_dims:
            logger.warning("⚠️ [数据缺失] selected_dimensions为空，可能影响生成质量")

        logger.info("=" * 80)
        logger.info("📋 [需求洞察] 开始生成结构化需求文档")
        logger.info("=" * 80)

        # 1. 提取问卷数据
        questionnaire_data = QuestionnaireSummaryNode._extract_questionnaire_data(state)

        # 2. 提取AI分析（包含L1-L5洞察）- 🔧 v7.153: 增强多路径获取
        ai_analysis = state.get("requirement_analysis", {})
        analysis_layers = ai_analysis.get("analysis_layers", {})
        analysis_layers_source = "requirement_analysis" if analysis_layers else None

        # 🔧 v7.153: 多路径备选获取 analysis_layers
        if not analysis_layers:
            # 路径2: agent_results.requirements_analyst
            agent_results = state.get("agent_results", {})
            requirements_analyst_result = agent_results.get("requirements_analyst", {})
            analysis_layers = requirements_analyst_result.get("analysis_layers", {})
            if analysis_layers:
                analysis_layers_source = "agent_results.requirements_analyst"

        if not analysis_layers:
            # 路径3: structured_requirements.analysis_layers
            structured_reqs = state.get("structured_requirements", {})
            analysis_layers = structured_reqs.get("analysis_layers", {})
            if analysis_layers:
                analysis_layers_source = "structured_requirements"

        if not analysis_layers:
            # 路径4: 直接从 state 顶层获取
            analysis_layers = state.get("analysis_layers", {})
            if analysis_layers:
                analysis_layers_source = "state.analysis_layers"

        # 🔧 v7.153: 详细日志记录获取结果
        if analysis_layers:
            logger.info(f"✅ [analysis_layers] 成功获取，来源: {analysis_layers_source}")
            logger.info(f"   - L1_facts: {len(analysis_layers.get('L1_facts', []))} 项")
            logger.info(f"   - L2_user_model: {'有' if analysis_layers.get('L2_user_model') else '无'}")
            logger.info(f"   - L3_core_tension: {'有' if analysis_layers.get('L3_core_tension') else '无'}")
            logger.info(f"   - L4_project_task: {'有' if analysis_layers.get('L4_project_task') else '无'}")
            logger.info(f"   - L5_sharpness: {'有' if analysis_layers.get('L5_sharpness') else '无'}")
        else:
            logger.warning("⚠️ [analysis_layers] 所有路径均未获取到数据，将使用降级模式")
            logger.warning(
                f"   已尝试路径: requirement_analysis, agent_results.requirements_analyst, structured_requirements, state.analysis_layers"
            )

        user_input = state.get("user_input", "")

        # 3. 执行需求重构
        try:
            # 🔧 v7.142: LLM调用的超时保护在 RequirementsRestructuringEngine._llm_generate_one_sentence 中实现
            # 双重超时保护：SDK timeout (15s) + ThreadPool timeout (20s)
            restructured_doc = RequirementsRestructuringEngine.restructure(
                questionnaire_data, ai_analysis, analysis_layers, user_input, use_llm=True  # 启用LLM优化描述
            )
        except Exception as e:
            logger.error(f"❌ 需求重构失败: {e}")
            import traceback

            # 🔧 v7.149: 增强异常日志 - 记录完整堆栈到日志文件
            logger.error(f"异常堆栈:\n{traceback.format_exc()}")
            traceback.print_exc()

            # 降级：返回简化版本
            logger.warning("⚠️ [降级模式] 使用简化需求重构")
            restructured_doc = QuestionnaireSummaryNode._fallback_restructure(
                questionnaire_data, ai_analysis, user_input
            )

        # 4. 生成简洁摘要（用于日志和前端快速展示）
        summary_text = QuestionnaireSummaryNode._generate_summary_text(restructured_doc)

        # 5. 更新 structured_requirements（融合重构文档）
        enhanced_requirements = QuestionnaireSummaryNode._update_structured_requirements(
            state.get("structured_requirements", {}), restructured_doc
        )

        logger.info(f"✅ 需求洞察完成")
        logger.info(f"📝 项目目标: {restructured_doc['project_objectives']['primary_goal'][:50]}...")
        logger.info(f"🎯 设计重点: {len(restructured_doc['design_priorities'])}个维度")
        logger.info(f"⚠️  风险识别: {len(restructured_doc['identified_risks'])}项")
        logger.info(f"📊 洞察评分: {restructured_doc['insight_summary']['L5_sharpness_score']}")

        # 🔧 v7.143: 添加明确的出口日志
        # 🆕 v7.147: 添加用户确认 interrupt
        # 🔧 v7.152: 添加 progressive_questionnaire_completed 确保问卷流程完整标记
        update_dict = {
            "restructured_requirements": restructured_doc,
            "requirements_summary_text": summary_text,
            "structured_requirements": enhanced_requirements,
            "questionnaire_summary_completed": True,
            "progressive_questionnaire_completed": True,  # 🔧 v7.152: 确保问卷完成标记
            "progressive_questionnaire_step": 4,  # 🔧 v7.152: 标记当前步骤
            "detail": "需求洞察与需求重构完成",
        }

        # 🔧 v7.144: 使用 WorkflowFlagManager 保留关键状态，防止覆盖
        from ...core.workflow_flags import WorkflowFlagManager

        update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)

        logger.info("=" * 100)
        logger.info("📋 [需求洞察] ✅ Data prepared, showing to user for confirmation/editing")
        logger.info(f"   返回字段: {list(update_dict.keys())}")
        logger.info("=" * 100)

        # 🆕 v7.151: 升级为需求洞察交互，支持编辑
        payload = {
            "interaction_type": "requirements_insight",  # 🆕 新交互类型
            "step": 4,
            "total_steps": 4,
            "title": "需求洞察",  # 🆕 更名
            "message": "✅ 需求洞察完成！AI 已深度分析您的需求，请确认或编辑以下理解",
            "restructured_requirements": restructured_doc,
            "requirements_summary_text": summary_text,
            # 🆕 v7.151: 新增深度洞察字段
            "project_essence": restructured_doc.get("project_essence", ""),
            "implicit_requirements": restructured_doc.get("implicit_requirements", []),
            "key_conflicts": restructured_doc.get("key_conflicts", []),
            # 🆕 v7.151: 支持编辑的选项
            "editable_fields": ["primary_goal", "core_tension", "design_priorities"],
            "options": {"confirm": "确认无误，开始专家分析", "edit": "修改理解"},
        }

        logger.info("🛑 [需求洞察] 即将调用 interrupt()，等待用户确认/编辑...")
        user_response = interrupt(payload)
        logger.info(f"✅ [需求洞察] 收到用户响应: {type(user_response)}")

        # 🆕 v7.151: 处理用户响应（合并自 requirements_confirmation）
        return QuestionnaireSummaryNode._handle_user_response(state, update_dict, restructured_doc, user_response)

    @staticmethod
    def _handle_user_response(
        state: ProjectAnalysisState, update_dict: Dict[str, Any], restructured_doc: Dict[str, Any], user_response: Any
    ) -> Command:
        """
        🆕 v7.151: 处理用户响应（合并自 requirements_confirmation）

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

        logger.info(f"📊 [需求洞察] 修改分析: 差异字符数={total_diff_chars}, 重大修改={has_major_modification}")

        # 🔧 v7.151: 修正逻辑 - 重大修改优先于确认意图
        if has_major_modification:
            # 重大修改：返回 requirements_analyst 重新分析
            logger.info("🔄 [需求洞察] 检测到重大修改(>=50字符)，返回需求分析师重新分析")

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
                    logger.warning(f"⚠️ 用户修改包含超出能力的需求: {alert['message']}")

            return Command(update=update_dict, goto="requirements_analyst")

        elif is_approved or has_minor_modification:
            # 确认或微调：直接前进到 project_director
            if has_minor_modification:
                logger.info("✏️ [需求洞察] 检测到微调(<50字符)，更新本地状态")
                # 将微调融入 update_dict
                if "primary_goal" in modifications:
                    update_dict["restructured_requirements"]["project_objectives"]["primary_goal"] = modifications[
                        "primary_goal"
                    ]
                    update_dict["structured_requirements"]["project_task"] = modifications["primary_goal"]

                # 保存用户调整记录
                update_dict["user_requirement_adjustments"] = modifications

            update_dict["requirements_confirmed"] = True

            logger.info("=" * 100)
            logger.info("📋 [需求洞察] ✅ User confirmed, proceeding to project_director")
            logger.info("=" * 100)

            return Command(update=update_dict, goto="project_director")

        else:
            # 拒绝：也返回重新分析
            logger.info("⚠️ [需求洞察] 用户拒绝当前理解，返回需求分析师")
            update_dict["requirements_confirmed"] = False
            return Command(update=update_dict, goto="requirements_analyst")

    @staticmethod
    def _extract_questionnaire_data(state: ProjectAnalysisState) -> Dict[str, Any]:
        """提取三步问卷的所有数据"""

        # Step1: 核心任务
        confirmed_tasks = state.get("confirmed_core_tasks", [])

        # Step2: 信息补全（可能在gap_filling_answers或questionnaire_responses中）
        gap_filling = state.get("gap_filling_answers", {})
        if not gap_filling:
            # 🔧 v7.143: 添加防御性代码，避免 questionnaire_responses 为 None 时崩溃
            questionnaire_responses = state.get("questionnaire_responses") or {}
            gap_filling = questionnaire_responses.get("gap_filling", {})

        # Step3: 雷达维度
        selected_dims = state.get("selected_dimensions", [])
        # 🔧 v7.150: 修复字段名 - 从 dimension_weights 改为 radar_dimension_values
        # step2_radar 保存的是 radar_dimension_values，而非 dimension_weights
        dimension_weights = state.get("radar_dimension_values") or state.get("dimension_weights") or {}

        logger.info(f"📊 问卷数据提取:")
        logger.info(f"   - 核心任务: {len(confirmed_tasks)}个")
        logger.info(f"   - 信息补全: {len(gap_filling)}个字段")
        logger.info(f"   - 雷达维度: {len(selected_dims)}个")
        logger.info(f"   - 维度权重: {len(dimension_weights)}个")

        return {
            "core_tasks": confirmed_tasks,
            "gap_filling": gap_filling,
            "dimensions": {"selected": selected_dims, "weights": dimension_weights},
            "questionnaire_step": state.get("progressive_questionnaire_step", 0),
        }

    @staticmethod
    def _fallback_restructure(
        questionnaire_data: Dict[str, Any], ai_analysis: Dict[str, Any], user_input: str
    ) -> Dict[str, Any]:
        """降级重构逻辑（当主流程失败时）"""

        logger.warning("⚠️ 使用降级重构逻辑")

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
        """更新structured_requirements字段（融合重构文档）"""

        updated = existing.copy() if existing else {}

        # 更新核心字段
        objectives = restructured_doc.get("project_objectives", {})
        if objectives.get("primary_goal"):
            updated["project_task"] = objectives["primary_goal"]

        constraints = restructured_doc.get("constraints", {})
        if "budget" in constraints:
            updated["budget_range"] = constraints["budget"]["total"]
            if constraints["budget"].get("breakdown"):
                updated["budget_breakdown"] = constraints["budget"]["breakdown"]

        if "timeline" in constraints:
            updated["timeline"] = constraints["timeline"]["duration"]

        if "space" in constraints:
            updated["space_area"] = constraints["space"]["area"]
            if constraints["space"].get("layout"):
                updated["space_layout"] = constraints["space"]["layout"]

        # 添加设计重点
        priorities = restructured_doc.get("design_priorities", [])
        if priorities:
            updated["design_focus"] = [p["label"] for p in priorities[:3]]

        # 标记来源
        updated["_source"] = "questionnaire_restructured"
        updated["_restructured_at"] = restructured_doc.get("metadata", {}).get("generated_at", "")
        updated["_questionnaire_enhanced"] = True

        return updated


# 便捷函数（用于工作流节点调用）
def questionnaire_summary_node(
    state: ProjectAnalysisState, store: Optional[BaseStore] = None
) -> Command[Literal["project_director", "requirements_analyst"]]:
    """问卷汇总节点函数

    🆕 v7.152: 修复返回类型声明，正确返回 Command 对象以支持动态路由
    - 确认/微调 → project_director
    - 重大修改 → requirements_analyst
    """
    return QuestionnaireSummaryNode.execute(state, store)
