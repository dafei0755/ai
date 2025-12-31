"""
三步递进式问卷节点

v7.80: 将问卷升级为「核心任务确认 → 雷达图多维度画像 → 密度补齐追问」的三步递进式体验
v7.80.1: Step 1 升级为 LLM 驱动的智能任务拆解（从复述 → 明确）

节点流程：
    requirements_analyst
        → progressive_step1_core_task
        → progressive_step2_radar
        → progressive_step3_gap_filling
        → requirements_confirmation
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
from ...services.core_task_decomposer import _simple_fallback_decompose, decompose_core_tasks
from ...services.dimension_selector import DimensionSelector, RadarGapAnalyzer, select_dimensions_for_state


class ProgressiveQuestionnaireNode:
    """三步递进式问卷节点"""

    # ==========================================================================
    # Step 1: 核心任务确认（v7.80.1 智能拆解版）
    # ==========================================================================

    @staticmethod
    def step1_core_task(
        state: ProjectAnalysisState, store: Optional[BaseStore] = None
    ) -> Command[Literal["progressive_step2_radar", "requirements_analyst"]]:
        """
        Step 1: 核心任务智能拆解与确认

        v7.80.1: 使用 LLM 将用户输入拆解为结构化任务列表，让用户确认/调整/补充。

        Args:
            state: 项目分析状态
            store: 存储接口

        Returns:
            Command对象，指向下一个节点
        """
        logger.info("=" * 80)
        logger.info("🎯 [v7.80.1 Step 1] 核心任务智能拆解")
        logger.info("=" * 80)

        # 检查是否已完成此步骤（使用新字段）
        if state.get("progressive_questionnaire_step", 0) >= 1 and state.get("confirmed_core_tasks"):
            logger.info("✅ Step 1 已完成，跳过")
            return Command(update={"progressive_questionnaire_step": 1}, goto="progressive_step2_radar")

        # 追问模式跳过
        if state.get("is_followup"):
            logger.info("⏩ Follow-up session, skipping progressive questionnaire")
            logger.info("   - 下一步: requirements_confirmation")
            update_dict = {"progressive_questionnaire_completed": True, "progressive_questionnaire_step": 3}
            update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)
            return Command(update=update_dict, goto="requirements_confirmation")

        # 🆕 v7.80.1: 使用 LLM 拆解核心任务
        user_input = state.get("user_input", "")
        structured_data = state.get("agent_results", {}).get("requirements_analyst", {}).get("structured_data", {})

        # 🆕 v7.80.15 (P1.1): 诗意解读子流程
        poetic_metadata = None
        if _contains_poetic_expression(user_input):
            logger.info("🎨 [诗意解读] 检测到诗意/哲学表达，启动诗意解读子流程")
            try:
                import functools
                from concurrent.futures import ThreadPoolExecutor

                def _run_async_poetic_interpret(user_input: str):
                    """在独立线程中运行诗意解读"""
                    return asyncio.run(_llm_interpret_poetry(user_input))

                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_run_async_poetic_interpret, user_input)
                    poetic_metadata = future.result(timeout=30)  # 30秒超时

                logger.info(f"✅ [诗意解读] 解读完成: {poetic_metadata.get('metaphor_explanation', '')[:50]}...")
            except Exception as e:
                logger.warning(f"⚠️ [诗意解读] 解读失败: {e}，继续正常流程")
                poetic_metadata = None

        # 执行任务拆解
        # v7.80.1.2: 使用 ThreadPoolExecutor 在独立线程中运行 LLM 异步调用
        # 解决 LangGraph 异步上下文与 asyncio.run 不兼容的问题
        try:
            import functools
            from concurrent.futures import ThreadPoolExecutor

            def _run_async_decompose(user_input: str, structured_data: dict):
                """在独立线程中运行异步任务拆解"""
                return asyncio.run(decompose_core_tasks(user_input, structured_data))

            logger.info("🔄 [v7.80.1.2] 使用 ThreadPoolExecutor 执行 LLM 任务拆解")
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(_run_async_decompose, user_input, structured_data)
                extracted_tasks = future.result(timeout=60)  # 60秒超时

            if not extracted_tasks:
                logger.warning("⚠️ LLM 任务拆解返回空列表，使用回退策略")
                extracted_tasks = _simple_fallback_decompose(user_input)

        except Exception as e:
            logger.error(f"❌ LLM 任务拆解失败: {e}")
            logger.info("⚠️ 使用回退策略进行关键词匹配拆解")
            extracted_tasks = _simple_fallback_decompose(user_input)

        logger.info(f"📝 [v7.80.1] 拆解出 {len(extracted_tasks)} 个核心任务")
        for i, task in enumerate(extracted_tasks):
            logger.info(f"   {i+1}. {task.get('title', '未命名')}")

        # 同时保留旧格式（兼容性）
        old_format_task = ProgressiveQuestionnaireNode._extract_core_task(state)

        # 生成用户输入摘要
        user_input_summary = user_input[:100] + ("..." if len(user_input) > 100 else "")

        # 🆕 v7.80.1: 构建新的 interrupt payload
        payload = {
            "interaction_type": "progressive_questionnaire_step1",
            "step": 1,
            "total_steps": 3,
            "title": "明确核心任务",
            "message": "系统已从您的描述中识别以下核心任务，请确认、调整或补充",
            # 🆕 新字段：任务列表
            "extracted_tasks": extracted_tasks,
            "user_input_summary": user_input_summary,
            # 旧字段：保留兼容
            "extracted_task": old_format_task,
            "editable": True,
            "options": {"confirm": "确认任务列表", "skip": "跳过问卷"},
        }

        logger.info("🛑 [Step 1] 即将调用 interrupt()，等待用户输入...")
        user_response = interrupt(payload)
        logger.info(f"✅ [Step 1] 收到用户响应: {type(user_response)}")

        # 🆕 v7.80.1: 解析用户响应（支持新旧格式）
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
            logger.info("⏭️ 用户跳过问卷")

            # 🔧 v7.87 P0: 设置默认 questionnaire_summary
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
                # 🔧 v7.87 P0: 默认 questionnaire_summary
                "questionnaire_summary": default_questionnaire_summary,
                "questionnaire_responses": default_questionnaire_summary,
            }
            logger.info(f"⏭️ [v7.87 P0] 已设置默认 questionnaire_summary（Step 1跳过）")
            logger.info("   - 下一步: requirements_confirmation")

            update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)
            return Command(update=update_dict, goto="requirements_confirmation")

        # 构建任务摘要
        task_summary = ProgressiveQuestionnaireNode._build_task_summary(confirmed_tasks)
        logger.info(f"✅ [Step 1] 确认 {len(confirmed_tasks)} 个核心任务")

        # 🆕 v7.80.15 (P1.2): 检测特殊场景
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
            logger.info(f"🎯 [Step 1] 识别特殊场景: {scene_tags}")

        update_dict = {
            # 🆕 v7.80.1 新字段
            "extracted_core_tasks": extracted_tasks,
            "confirmed_core_tasks": confirmed_tasks,
            "core_task_summary": task_summary,
            # 旧字段（兼容）
            "extracted_core_task": old_format_task,
            "confirmed_core_task": confirmed_task if confirmed_task != old_format_task else task_summary,
            "progressive_questionnaire_step": 1,
            # 🆕 v7.80.15 (P1.1): 诗意解读元数据
            "poetic_metadata": poetic_metadata,
            # 🆕 v7.80.15 (P1.2): 特殊场景元数据
            "special_scene_metadata": special_scene_metadata,
        }
        update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)

        return Command(update=update_dict, goto="progressive_step2_radar")

    # ==========================================================================
    # Step 2: 雷达图维度
    # ==========================================================================

    @staticmethod
    def step2_radar(
        state: ProjectAnalysisState, store: Optional[BaseStore] = None
    ) -> Command[Literal["progressive_step3_gap_filling", "requirements_confirmation"]]:
        """
        Step 2: 雷达图多维度偏好收集

        展示9-12个维度滑块，让用户表达设计偏好。

        Args:
            state: 项目分析状态
            store: 存储接口

        Returns:
            Command对象，指向下一个节点
        """
        logger.info("=" * 80)
        logger.info("📊 [v7.80 Step 2] 雷达图维度收集")
        logger.info("=" * 80)

        # 检查是否已完成此步骤
        if state.get("progressive_questionnaire_step", 0) >= 2 and state.get("radar_dimension_values"):
            logger.info("✅ Step 2 已完成，跳过")
            return Command(update={"progressive_questionnaire_step": 2}, goto="progressive_step3_gap_filling")

        # 🆕 v7.80.4: 动态维度选择 + 智能生成
        # 🔧 v7.80.16: 性能优化 - 默认禁用LLM动态生成，依赖P0.3场景注入
        import os

        from ...services.dynamic_dimension_generator import DynamicDimensionGenerator

        # 🆕 v7.80.5: 强制生成模式（用于测试/演示）
        FORCE_GENERATE = os.getenv("FORCE_GENERATE_DIMENSIONS", "false").lower() == "true"

        # 🔧 v7.80.16: 动态生成开关（默认关闭，避免LLM调用延迟）
        USE_DYNAMIC_GENERATION = os.getenv("USE_DYNAMIC_GENERATION", "false").lower() == "true"

        # Step 2.1: 先选择现有维度
        existing_dimensions = select_dimensions_for_state(state)
        logger.info(f"📊 已选择 {len(existing_dimensions)} 个现有维度")

        # Step 2.2: 分析覆盖度，必要时生成新维度
        user_input = state.get("user_input", "")
        agent_results = state.get("agent_results", {})
        requirements_result = agent_results.get("requirements_analyst", {})
        structured_data = requirements_result.get("structured_data", {})

        generator = DynamicDimensionGenerator()
        dimensions = existing_dimensions
        generated_count = 0

        if FORCE_GENERATE:
            # 🚀 强制生成模式：跳过覆盖度检查，直接生成
            logger.info("🚀 [动态维度] 强制生成模式已启用")
            missing_aspects = ["用户独特需求", "项目特色要求"]

            new_dimensions = generator.generate_dimensions(
                user_input,
                structured_data,
                missing_aspects,
                target_count=min(2, 12 - len(existing_dimensions)),  # 强制模式生成2个
            )

            if new_dimensions:
                dimensions = existing_dimensions + new_dimensions
                generated_count = len(new_dimensions)
                logger.info(f"✅ [动态维度] 强制新增 {generated_count} 个定制维度")
                for dim in new_dimensions:
                    logger.info(f"   + {dim['name']}: {dim['left_label']} ← → {dim['right_label']}")
        elif USE_DYNAMIC_GENERATION:
            # 正常模式：基于覆盖度分析（仅在环境变量启用时）
            logger.info("🔍 [动态维度] LLM覆盖度分析已启用")
            coverage = generator.analyze_coverage(user_input, structured_data, existing_dimensions)

            if coverage.get("should_generate", False) and coverage.get("missing_aspects"):
                logger.info(f"🤖 [动态维度] 检测到覆盖不足 (评分: {coverage.get('coverage_score', 0):.2f})")
                logger.info(f"   缺失方面: {coverage.get('missing_aspects', [])}")

                # 生成新维度
                new_dimensions = generator.generate_dimensions(
                    user_input,
                    structured_data,
                    coverage.get("missing_aspects", []),
                    target_count=min(3, 12 - len(existing_dimensions)),  # 确保总数不超过12
                )

                if new_dimensions:
                    dimensions = existing_dimensions + new_dimensions
                    generated_count = len(new_dimensions)
                    logger.info(f"✅ [动态维度] 新增 {generated_count} 个定制维度")
                    for dim in new_dimensions:
                        logger.info(f"   + {dim['name']}: {dim['left_label']} ← → {dim['right_label']}")
        else:
            # 🔧 v7.80.16: 默认禁用LLM调用，仅使用P0.3场景注入
            logger.info("⚡ [性能优化] 跳过LLM动态生成，使用P0.3场景注入机制")

        # 🆕 v7.80.15 (P1.3): 基于特殊场景注入专用维度
        special_scene_metadata = state.get("special_scene_metadata")
        confirmed_tasks = state.get("confirmed_core_tasks", [])

        if special_scene_metadata or confirmed_tasks:
            from ...services.dimension_selector import DimensionSelector

            selector = DimensionSelector()

            # 调用场景检测和维度注入
            dimensions = selector.detect_and_inject_specialized_dimensions(
                user_input=user_input,
                confirmed_tasks=confirmed_tasks,
                current_dimensions=dimensions,
                special_scene_metadata=special_scene_metadata,
            )
            logger.info(f"🎯 [特殊场景] 维度注入完成: 最终 {len(dimensions)} 个维度")

        logger.info(f"📊 最终维度数量: {len(dimensions)} ({len(existing_dimensions)} 现有 + {generated_count} 动态生成)")

        # 获取确认的核心任务
        confirmed_task = state.get("confirmed_core_task", "")

        # 构建interrupt payload
        payload = {
            "interaction_type": "progressive_questionnaire_step2",
            "step": 2,
            "total_steps": 3,
            "title": "多维度偏好设置",
            "message": "请通过拖动滑块表达您的设计偏好。每个维度代表两种不同的设计方向。",
            "core_task": confirmed_task,
            "dimensions": dimensions,
            "instructions": "拖动滑块到您偏好的位置（0-100）",
            "options": {"confirm": "确认偏好设置", "back": "返回修改核心任务"},
        }

        logger.info("🛑 [Step 2] 即将调用 interrupt()，等待用户输入...")
        user_response = interrupt(payload)
        logger.info(f"✅ [Step 2] 收到用户响应: {type(user_response)}")

        # 解析用户响应
        dimension_values = {}
        # 🔧 v7.87: 移除返回上一步功能

        if isinstance(user_response, dict):
            # 🔧 v7.87: 移除 action == "back" 处理
            dimension_values = user_response.get("values") or user_response.get("dimension_values") or {}
            # 如果没有values字段，尝试直接从响应中提取
            if not dimension_values:
                for key, value in user_response.items():
                    if key in [d["id"] for d in dimensions] and isinstance(value, (int, float)):
                        dimension_values[key] = int(value)

        # 如果用户没有设置任何值，使用默认值
        if not dimension_values:
            logger.warning("⚠️ 用户未设置任何维度值，使用默认值")
            dimension_values = {d["id"]: d.get("default_value", 50) for d in dimensions}

        logger.info(f"📊 [Step 2] 收集到 {len(dimension_values)} 个维度值")

        # 分析雷达图
        analyzer = RadarGapAnalyzer()
        analysis = analyzer.analyze(dimension_values, dimensions)

        update_dict = {
            "selected_radar_dimensions": dimensions,
            "radar_dimension_values": dimension_values,
            "radar_analysis_summary": analysis,
            "progressive_questionnaire_step": 2,
        }
        update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)

        # 🔧 v7.80.18: 总是执行 Step 3（任务信息完整性分析）
        # v7.80.6 革新：Step 3 不再基于雷达图短板，而是基于任务完整性
        logger.info("📊 [Step 2] 雷达图维度收集完成，准备进入 Step 3（任务完整性分析）")

        # 保存雷达图分析结果（供 Step 3 参考，但不作为是否执行的依据）
        gap_dimensions = analysis.get("gap_dimensions", [])
        if gap_dimensions:
            logger.info(f"   雷达图短板维度: {gap_dimensions}")

        # ✅ 总是进入 Step 3，由 Step 3 内部决定是否需要补充问题
        return Command(update=update_dict, goto="progressive_step3_gap_filling")

    # ==========================================================================
    # Step 3: 密度补齐追问
    # ==========================================================================

    @staticmethod
    def step3_gap_filling(
        state: ProjectAnalysisState, store: Optional[BaseStore] = None
    ) -> Command[Literal["requirements_confirmation"]]:
        """
        Step 3: 核心任务信息完整性查漏补缺

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
        logger.info("❓ [v7.80.6 Step 3] 核心任务信息完整性查漏补缺")
        logger.info("=" * 80)

        # 检查是否已完成此步骤
        if state.get("progressive_questionnaire_completed"):
            logger.info("✅ 问卷已完成，跳过 Step 3")
            logger.info("   - 下一步: requirements_confirmation")
            return Command(update={"progressive_questionnaire_step": 3}, goto="requirements_confirmation")

        # 🆕 v7.80.6: 针对核心任务进行信息完整性分析
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

        logger.info(f"📊 任务信息完整性评分: {completeness.get('completeness_score', 0):.2f}")
        logger.info(f"   已覆盖维度: {completeness.get('covered_dimensions', [])}")
        logger.info(f"   缺失维度: {completeness.get('missing_dimensions', [])}")
        logger.info(f"   关键缺失点: {completeness.get('critical_gaps', [])}")

        # 判断是否需要补充问题
        critical_gaps = completeness.get("critical_gaps", [])
        if not critical_gaps:
            logger.info("✅ 任务信息完整，无需补充，跳过 Step 3")
            logger.info("   - 下一步: requirements_confirmation")
            update_dict = {
                "progressive_questionnaire_completed": True,
                "progressive_questionnaire_step": 3,
                "task_completeness_analysis": completeness,  # 保存分析结果
            }
            update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)
            return Command(update=update_dict, goto="requirements_confirmation")

        # 🔧 v7.80.8: 生成针对性补充问题（目标数量从5提升至10）
        existing_info_summary = ProgressiveQuestionnaireNode._build_existing_info_summary(structured_data)
        questions = analyzer.generate_gap_questions(
            missing_dimensions=completeness.get("missing_dimensions", []),
            critical_gaps=critical_gaps,
            confirmed_tasks=confirmed_tasks,
            existing_info_summary=existing_info_summary,
            target_count=10,  # 🔧 v7.80.8: 从5改为10
        )
        logger.info(f"📝 [v7.80.8] 生成 {len(questions)} 个针对性补充问题（目标10个）")

        # 🆕 v7.80.17: 应用问题排序（必答问题在前，按priority排序）
        questions = sorted(
            questions,
            key=lambda q: (
                0 if q.get("is_required", False) else 1,  # 必答问题在前
                q.get("priority", 999),  # 优先级数字小的在前
                -q.get("weight", 5),  # 权重大的在前（负号反转）
            ),
        )
        logger.info(
            f"📊 [v7.80.17] 问题排序完成：{len([q for q in questions if q.get('is_required')])}个必答，{len([q for q in questions if not q.get('is_required')])}个选答"
        )

        # 获取上下文信息
        confirmed_task = state.get("confirmed_core_task", "")
        task_summary = ProgressiveQuestionnaireNode._build_task_summary(confirmed_tasks)

        # 🆕 v7.80.6: 构建新的 interrupt payload（任务完整性导向）
        payload = {
            "interaction_type": "progressive_questionnaire_step3",
            "step": 3,
            "total_steps": 3,
            "title": "补充关键信息",
            "message": "为了更精准地理解您的项目需求，请补充以下关键信息：",
            "core_task": confirmed_task,
            "task_summary": task_summary,
            # 🆕 任务完整性信息
            "completeness_score": completeness.get("completeness_score", 0),
            "covered_dimensions": completeness.get("covered_dimensions", []),
            "missing_dimensions": completeness.get("missing_dimensions", []),
            "critical_gaps": critical_gaps,
            "questionnaire": {
                "introduction": f"已完整度: {int(completeness.get('completeness_score', 0) * 100)}% | 缺失维度: {', '.join(completeness.get('missing_dimensions', []))}",
                "questions": questions,
                "note": "这些问题涉及预算、时间、交付等关键决策点，请根据实际情况作答",
            },
            "options": {"submit": "提交问卷", "back": "返回修改核心任务"},
        }

        logger.info("🛑 [Step 3] 即将调用 interrupt()，等待用户输入...")
        user_response = interrupt(payload)
        logger.info(f"✅ [Step 3] 收到用户响应: {type(user_response)}")

        # 解析用户响应
        answers = {}
        # 🔧 v7.87: 移除返回上一步功能

        if isinstance(user_response, dict):
            # 🔧 v7.87: 移除 action == "back" 处理
            answers = user_response.get("answers") or {}
            # 尝试从其他格式提取答案
            if not answers and "responses" in user_response:
                answers = user_response["responses"]

        logger.info(f"✅ [Step 3] 收集到 {len(answers)} 个补充答案")

        # 构建问卷摘要
        questionnaire_summary = ProgressiveQuestionnaireNode._build_questionnaire_summary(state, answers)

        # 🆕 v7.80.6: 保存任务完整性分析和补充答案
        update_dict = {
            "task_completeness_analysis": completeness,  # 完整性分析
            "task_gap_filling_questionnaire": {
                "questions": questions,
                "missing_dimensions": completeness.get("missing_dimensions", []),
                "critical_gaps": critical_gaps,
            },
            "gap_filling_answers": answers,
            "progressive_questionnaire_completed": True,
            "progressive_questionnaire_step": 3,
            "questionnaire_summary": questionnaire_summary,  # 兼容旧字段
            "calibration_processed": True,  # 兼容旧字段
        }
        update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)

        logger.info("✅ [Step 3] 问卷完成，路由到需求确认节点")
        logger.info(f"   - 收集到 {len(answers)} 个补充答案")
        logger.info(f"   - 下一步: requirements_confirmation")
        return Command(update=update_dict, goto="requirements_confirmation")

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
        """
        timestamp = datetime.now().isoformat()

        # 合并所有数据
        radar_values = state.get("radar_dimension_values", {})
        radar_summary = state.get("radar_analysis_summary", {})
        confirmed_task = state.get("confirmed_core_task", "")

        entries = []

        # 添加核心任务
        if confirmed_task:
            entries.append({"id": "core_task", "question": "核心任务", "value": confirmed_task, "type": "text"})

        # 添加雷达图数据
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
# 🆕 v7.80.15 (P1.1): 诗意解读辅助函数
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
        logger.error(f"❌ 诗意解读LLM调用失败: {e}")
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
