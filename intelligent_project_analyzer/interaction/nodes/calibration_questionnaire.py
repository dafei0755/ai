"""战略校准问卷节点"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional, Tuple

from langgraph.store.base import BaseStore
from langgraph.types import Command, interrupt
from loguru import logger

from ...core.state import ProjectAnalysisState
from ...core.workflow_flags import WorkflowFlagManager
from ..questionnaire import (
    AnswerParser,
    BiddingStrategyGenerator,
    ConflictQuestionGenerator,
    FallbackQuestionGenerator,
    PhilosophyQuestionGenerator,
    QuestionAdjuster,
    QuestionContext,
)

# 🆕 v7.18: 环境变量控制是否使用 QuestionnaireAgent
USE_V718_QUESTIONNAIRE_AGENT = os.getenv("USE_V718_QUESTIONNAIRE_AGENT", "false").lower() == "true"


class CalibrationQuestionnaireNode:
    """战略校准问卷节点"""

    @staticmethod
    def _identify_scenario_type(user_input: str, structured_data: Dict[str, Any]) -> str:
        """
        🚀 P0优化：识别项目场景类型，避免生成无关问题

        场景类型：
        - bidding_strategy: 竞标/策略咨询场景（B2B专业人士）
        - design_execution: 设计执行/施工场景（实际项目落地）
        - concept_exploration: 概念探索场景（C端用户）
        - unknown: 未知场景（使用保守策略）
        """
        # 关键词簇定义
        bidding_keywords = ["竞标", "投标", "策略", "对手", "如何取胜", "差异化", "突围", "评委", "方案竞争"]
        execution_keywords = ["施工", "工期", "材料", "预算", "落地", "实施", "建造", "装修"]

        # 计算激活度
        bidding_score = sum(1 for kw in bidding_keywords if kw in user_input)
        execution_score = sum(1 for kw in execution_keywords if kw in user_input)

        # 判断场景
        if bidding_score >= 2:
            logger.info(f"🎯 场景识别：竞标策略场景（bidding_score={bidding_score}）")
            return "bidding_strategy"
        elif execution_score >= 2:
            logger.info(f"🎯 场景识别：设计执行场景（execution_score={execution_score}）")
            return "design_execution"
        else:
            logger.info(f"🎯 场景识别：未知场景")
            return "unknown"

    # 🔧 修复: 移除重复的 _build_conflict_questions 方法
    # 该方法与 ConflictQuestionGenerator.generate() 重复
    # 现在统一使用 ConflictQuestionGenerator.generate()

    @staticmethod
    def _extract_raw_answers(user_response: Any) -> Tuple[Optional[Any], str]:
        """从用户响应中提取问卷答案原始结构和补充说明."""
        if user_response is None:
            return None, ""

        additional_notes = ""
        raw_answers: Optional[Any] = None

        if isinstance(user_response, dict):
            additional_notes = str(user_response.get("additional_info") or user_response.get("notes") or "").strip()
            raw_answers = user_response.get("answers") or user_response.get("entries") or user_response.get("responses")
        elif isinstance(user_response, list):
            raw_answers = user_response
        elif isinstance(user_response, str):
            stripped = user_response.strip()
            if not stripped:
                return None, ""
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return None, ""
            if isinstance(parsed, dict):
                additional_notes = str(parsed.get("additional_info") or parsed.get("notes") or "").strip()
                raw_answers = parsed.get("answers") or parsed.get("entries") or parsed
            elif isinstance(parsed, list):
                raw_answers = parsed

        return raw_answers, additional_notes

    @staticmethod
    def _build_answer_entries(
        questionnaire: Dict[str, Any], raw_answers: Optional[Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """将原始答案与问卷元数据合并为结构化摘要."""
        if not raw_answers:
            return [], {}

        answer_lookup: Dict[str, Any] = {}

        if isinstance(raw_answers, dict):
            answer_lookup = {str(key): value for key, value in raw_answers.items()}
        elif isinstance(raw_answers, list):
            for idx, item in enumerate(raw_answers, 1):
                if not isinstance(item, dict):
                    continue
                q_id = item.get("question_id") or item.get("id") or f"Q{idx}"
                answer_value = (
                    item.get("answer")
                    or item.get("value")
                    or item.get("response")
                    or item.get("selected")
                    or item.get("answers")
                )
                if answer_value is None:
                    continue
                key = str(q_id)
                answer_lookup[key] = answer_value
                question_label = item.get("question")
                if question_label:
                    answer_lookup[str(question_label)] = answer_value
        else:
            return [], {}

        questions = questionnaire.get("questions", []) if questionnaire else []
        entries: List[Dict[str, Any]] = []
        compact_answers: Dict[str, Any] = {}

        for idx, question in enumerate(questions, 1):
            q_id = question.get("id") or f"Q{idx}"
            potential_keys = [str(q_id), f"q{idx}", question.get("question"), str(idx)]

            answer_value = None
            for key in potential_keys:
                if key is None:
                    continue
                key_str = str(key)
                if key_str in answer_lookup:
                    answer_value = answer_lookup[key_str]
                    break
                if key in answer_lookup:  # 兼容原始键
                    answer_value = answer_lookup[key]
                    break

            if answer_value is None:
                continue

            normalized_value = CalibrationQuestionnaireNode._normalize_answer_value(question, answer_value)
            if normalized_value is None:
                continue

            entry = {
                "id": q_id,
                "question": question.get("question", ""),
                "value": normalized_value,
                "type": question.get("type"),
                "context": question.get("context", ""),
            }
            entries.append(entry)
            compact_answers[q_id] = normalized_value

        return entries, compact_answers

    @staticmethod
    def _normalize_answer_value(question: Dict[str, Any], answer: Any) -> Optional[Any]:
        """根据题型对答案进行归一化，便于后续处理."""
        if answer is None:
            return None

        q_type = (question.get("type") or "open_ended").lower()

        if q_type == "multiple_choice":
            if isinstance(answer, str):
                values = [item.strip() for item in answer.split(",") if item.strip()]
                return values or None
            if isinstance(answer, (list, tuple, set)):
                values = [str(item).strip() for item in answer if str(item).strip()]
                return values or None
            coerced = str(answer).strip()
            return [coerced] if coerced else None

        if q_type == "single_choice":
            if isinstance(answer, (list, tuple, set)):
                for item in answer:
                    candidate = str(item).strip()
                    if candidate:
                        return candidate
                return None
            return str(answer).strip() or None

        if isinstance(answer, (list, tuple, set)):
            values = [str(item).strip() for item in answer if str(item).strip()]
            return "、".join(values) if values else None

        if isinstance(answer, dict):
            try:
                serialized = json.dumps(answer, ensure_ascii=False)
            except (TypeError, ValueError):
                serialized = str(answer)
            return serialized.strip() or None

        return str(answer).strip() or None

    @staticmethod
    def execute(
        state: ProjectAnalysisState, store: Optional[BaseStore] = None
    ) -> Command[Literal["project_director", "requirements_analyst"]]:
        """
        执行战略校准问卷交互

        根据需求分析师文档v1.0的要求：
        在完成需求分析后，必须生成"战略校准问卷"并等待用户回答。
        这是确保战略方向正确无误的关键步骤。

        Args:
            state: 项目分析状态
            store: 存储接口

        Returns:
            Command对象，指向下一个节点
        """
        logger.info("=" * 80)
        logger.info("🎯 Starting calibration questionnaire interaction")
        logger.info("=" * 80)

        # 🔍 v7.154: 增强诊断日志
        logger.info(f"🔍 [v7.154 问卷诊断] skip_calibration 标志: {state.get('skip_calibration')}")
        logger.info(f"🔍 [v7.154 问卷诊断] is_followup 标志: {state.get('is_followup')}")
        logger.info(f"🔍 [v7.154 问卷诊断] calibration_questionnaire 存在: {bool(state.get('calibration_questionnaire'))}")
        logger.info(f"🔍 [v7.154 问卷诊断] questionnaire_responses 存在: {bool(state.get('questionnaire_responses'))}")

        # 如果问卷存在，记录详细信息
        questionnaire = state.get("calibration_questionnaire", {})
        if questionnaire:
            questions = questionnaire.get("questions", [])
            logger.info(f"🔍 [v7.154 问卷诊断] 问卷包含 {len(questions)} 个问题")
        else:
            logger.info(f"🔍 [v7.154 问卷诊断] 问卷尚未生成")

        # 🆕 v7.4: 问卷不可跳过
        # 原 v3.7 逻辑已移除：即使是中等复杂度任务，也必须完成问卷
        # 但可以减少问题数量（通过 QuestionAdjuster 动态调整）
        if state.get("skip_calibration"):
            logger.warning("⚠️ [v7.4] skip_calibration 标志已设置，但问卷不可跳过。将生成精简版问卷。")
            # 不再跳过，继续执行问卷生成
            # 后续通过 QuestionAdjuster 减少问题数量

        # ✅ 追问模式下直接跳过
        if state.get("is_followup"):
            logger.info("⏩ Follow-up session detected, skipping calibration questionnaire")
            # 自动保留持久化标志
            update_dict = {"calibration_processed": True, "calibration_skipped": True}
            update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)

            return Command(update=update_dict, goto="project_director")  # 🔧 v7.152: 改为 project_director

        # ✅ 检查是否已经处理过问卷（避免死循环）
        calibration_processed = state.get("calibration_processed")
        calibration_answers = state.get("calibration_answers")
        questionnaire_summary = state.get("questionnaire_summary")

        logger.info(f"🔍 [DEBUG] calibration_processed 标志: {calibration_processed}")
        logger.info(f"🔍 [DEBUG] calibration_answers 存在: {bool(calibration_answers)}")
        logger.info(f"🔍 [DEBUG] questionnaire_summary 存在: {bool(questionnaire_summary)}")

        # 🛡️ v7.24 增强防御：检查多个信号源判断问卷是否已处理
        # 信号源优先级：calibration_processed > calibration_answers > questionnaire_summary
        if not calibration_processed:
            if calibration_answers:
                logger.warning("⚠️ v7.24: calibration_processed=False 但 calibration_answers 存在，视为已处理")
                calibration_processed = True
            elif questionnaire_summary and questionnaire_summary.get("answers"):
                logger.warning("⚠️ v7.24: calibration_processed=False 但 questionnaire_summary.answers 存在，视为已处理")
                calibration_processed = True

        if calibration_processed:
            logger.info("✅ Calibration already processed, skipping to project_director")
            logger.info("🔄 [DEBUG] Returning Command(goto='project_director')")
            # 自动保留持久化标志
            update_dict = {"calibration_processed": True}  # 🔧 v7.24: 显式设置，确保传递
            update_dict = WorkflowFlagManager.preserve_flags(state, update_dict)
            return Command(update=update_dict, goto="project_director")  # 🆕 v7.151: 直接路由到 project_director

        # 获取需求分析结果
        agent_results = state.get("agent_results", {})
        requirements_result = agent_results.get("requirements_analyst")

        logger.info(f"📊 Debug - requirements_result exists: {bool(requirements_result)}")
        if requirements_result:
            logger.info(f"📊 Debug - requirements_result keys: {list(requirements_result.keys())}")

        if not requirements_result:
            logger.warning("⚠️ No requirements analysis found, returning to requirements analyst")
            return Command(update={"error": "No requirements analysis found"}, goto="requirements_analyst")

        # 🆕 v7.3: 问卷生成架构调整
        # 获取分析结果，用于动态生成问卷
        structured_data = requirements_result.get("structured_data") or {}

        # 检查是否存在预生成的问卷（向后兼容旧数据）
        questionnaire_from_agent = structured_data.get("calibration_questionnaire") or {}
        state_questionnaire = state.get("calibration_questionnaire") or {}

        logger.info(f"📊 分析结果字段: {list(structured_data.keys())}")

        # 🔥 v7.4.3: 获取 user_input（在所有代码块之前定义，确保全局可用）
        user_input = state.get("user_input", "")

        # 🆕 v7.3: 新架构 - 问卷动态生成逻辑
        # 优先使用基于分析结果的动态生成，而非依赖预生成问卷
        questionnaire = None
        generation_source = None

        # Step 1: 检查是否有预生成问卷（向后兼容）
        if questionnaire_from_agent.get("questions") and questionnaire_from_agent.get("source") != "to_be_regenerated":
            questionnaire = questionnaire_from_agent
            generation_source = "llm_pregenerated"
            logger.info(f"ℹ️ 使用LLM预生成的问卷（向后兼容旧架构）：{len(questionnaire.get('questions', []))} 个问题")
        elif state_questionnaire.get("questions"):
            questionnaire = state_questionnaire
            generation_source = "state_persisted"
            logger.info(f"ℹ️ 使用state中持久化的问卷：{len(questionnaire.get('questions', []))} 个问题")

        # Step 2: 如果没有预生成问卷，或标记为需要重新生成，则动态生成
        if not questionnaire or not questionnaire.get("questions"):
            logger.info("🚀 v7.5新架构：LLM驱动的智能问卷生成（提升问题与用户需求的结合度）")

            # 🆕 v7.18: 优先使用 QuestionnaireAgent (StateGraph) 生成问卷
            if USE_V718_QUESTIONNAIRE_AGENT:
                try:
                    from ...agents.questionnaire_agent import QuestionnaireAgent

                    logger.info("🤖 [v7.18] 使用 QuestionnaireAgent (StateGraph) 生成问卷...")
                    questionnaire_agent = QuestionnaireAgent(llm_model=None)
                    base_questions, generation_method = questionnaire_agent.generate(
                        user_input=user_input, structured_data=structured_data
                    )

                    if base_questions and generation_method in ("llm_generated", "regenerated"):
                        logger.info(f"✅ [v7.18] QuestionnaireAgent 生成成功：{len(base_questions)} 个问题")
                        questionnaire = {
                            "introduction": "以下问题基于您的具体需求定制，旨在深入理解您的期望和偏好",
                            "questions": base_questions,
                            "note": "这些问题直接针对您提到的具体内容，帮助我们提供更精准的设计建议",
                            "source": generation_method,
                            "generation_method": "stategraph_agent",
                        }
                        generation_source = generation_method
                    else:
                        logger.warning(f"⚠️ [v7.18] QuestionnaireAgent 返回回退方案，将使用规则生成")
                        raise Exception("QuestionnaireAgent 返回回退方案")

                except Exception as agent_error:
                    logger.warning(f"⚠️ [v7.18] QuestionnaireAgent 失败: {agent_error}，回退到 LLMQuestionGenerator")
                    # 回退到原有 v7.5 逻辑
                    USE_V718_QUESTIONNAIRE_AGENT_FALLBACK = True
            else:
                USE_V718_QUESTIONNAIRE_AGENT_FALLBACK = True

            # v7.5 原有逻辑（作为 v7.18 的回退或独立使用）
            if not questionnaire or not questionnaire.get("questions"):
                try:
                    from ..questionnaire.llm_generator import LLMQuestionGenerator

                    logger.info("🤖 [v7.5] 尝试使用 LLM 生成问卷...")
                    base_questions, generation_method = LLMQuestionGenerator.generate(
                        user_input=user_input, structured_data=structured_data, llm_model=None, timeout=30  # 使用默认LLM实例
                    )

                    if base_questions and generation_method == "llm_generated":
                        logger.info(f"✅ [v7.5] LLM生成成功：{len(base_questions)} 个定制问题")
                        questionnaire = {
                            "introduction": "以下问题基于您的具体需求定制，旨在深入理解您的期望和偏好",
                            "questions": base_questions,
                            "note": "这些问题直接针对您提到的具体内容，帮助我们提供更精准的设计建议",
                            "source": "llm_generated",
                            "generation_method": "llm_driven",
                        }
                        generation_source = "llm_generated"
                    else:
                        logger.warning(f"⚠️ [v7.5] LLM生成返回回退方案，将使用规则生成")
                        raise Exception("LLM返回回退方案")

                except Exception as llm_error:
                    logger.warning(f"⚠️ [v7.5] LLM生成失败: {llm_error}，使用回退方案")

                    # 🔄 回退到原有的 FallbackQuestionGenerator
                    logger.info("🔄 [v7.5] 回退到规则驱动的问卷生成...")

                    # 智能提取关键信息
                    import sys

                    from ..questionnaire.context import KeywordExtractor

                    try:
                        extracted_info = KeywordExtractor.extract(user_input, structured_data)
                        logger.info(f"🔍 关键词提取完成，提取了 {len(extracted_info)} 个字段")
                    except Exception as e:
                        logger.error(f"❌ KeywordExtractor.extract() 失败: {e}")
                        extracted_info = KeywordExtractor._empty_result()

                    # 使用 FallbackQuestionGenerator 生成基础问题集
                    base_questions = FallbackQuestionGenerator.generate(
                        structured_data, user_input=user_input, extracted_info=extracted_info
                    )
                    logger.info(f"✅ 规则生成完成：{len(base_questions)} 个问题")

                    questionnaire = {
                        "introduction": "以下问题旨在深入理解您的需求和期望，帮助我们提供更精准的设计建议",
                        "questions": base_questions,
                        "note": "基于您的需求深度分析结果生成的定制问卷",
                        "source": "dynamic_generation",
                        "generation_method": "rule_based_fallback",
                    }
                    generation_source = "dynamic_generation"

        logger.info(f"🔍 问卷源: {generation_source}, 问题数: {len(questionnaire.get('questions', []))}")

        # 🆕 V1集成：基于战略洞察注入理念探索问题（优先级更高）
        logger.info(f"🔍 [DEBUG] Step 2: 构建理念探索问题...")
        try:
            philosophy_questions = PhilosophyQuestionGenerator.generate(structured_data)
            logger.info(f"🔍 [DEBUG] Step 2 完成: 生成 {len(philosophy_questions)} 个理念问题")
        except Exception as e:
            logger.error(f"❌ [DEBUG] Step 2 异常: {type(e).__name__}: {e}")
            import traceback

            traceback.print_exc()
            philosophy_questions = []
        if philosophy_questions:
            logger.info(f"🎨 V1战略洞察生成 {len(philosophy_questions)} 个理念探索问题")

        # 🚀 P0优化：识别场景类型，避免生成无关问题
        logger.info(f"🔍 [DEBUG] Step 2.5: 识别场景类型...")
        # user_input 已在第305行定义
        scenario_type = CalibrationQuestionnaireNode._identify_scenario_type(user_input, structured_data)
        logger.info(f"🔍 [DEBUG] Step 2.5 完成: scenario_type={scenario_type}")

        # 🚀 P1优化：竞标策略场景生成专用问题
        bidding_strategy_questions = []
        if scenario_type == "bidding_strategy":
            logger.info(f"🔍 [DEBUG] Step 2.6: 构建竞标策略专用问题...")
            try:
                bidding_strategy_questions = BiddingStrategyGenerator.generate(user_input, structured_data)
                logger.info(f"🔍 [DEBUG] Step 2.6 完成: 生成 {len(bidding_strategy_questions)} 个竞标策略问题")
            except Exception as e:
                logger.error(f"❌ [DEBUG] Step 2.6 异常: {type(e).__name__}: {e}")
                import traceback

                traceback.print_exc()
                bidding_strategy_questions = []
            if bidding_strategy_questions:
                logger.info(f"🎯 [P1] 竞标策略场景注入 {len(bidding_strategy_questions)} 个专用问题")

        # 🆕 V1.5集成：利用可行性分析结果注入资源冲突问题（价值体现点1）
        # 🆕 v7.4: 冲突问题必须由用户约束激活
        logger.info(f"🔍 [DEBUG] Step 3: 构建资源冲突问题...")
        feasibility = state.get("feasibility_assessment", {})
        conflict_questions = []

        # 🆕 v7.4: 获取用户提及的约束（从 extracted_info 或重新提取）
        if "extracted_info" not in dir() or extracted_info is None:
            from ..questionnaire.context import KeywordExtractor

            extracted_info = KeywordExtractor.extract(user_input, structured_data)
        user_mentioned_constraints = extracted_info.get("user_mentioned_constraints", [])

        if feasibility:
            try:
                # 🚀 v7.4优化：传入 user_mentioned_constraints 参数
                conflict_questions = ConflictQuestionGenerator.generate(
                    feasibility, scenario_type, user_mentioned_constraints=user_mentioned_constraints
                )
                logger.info(f"🔍 [DEBUG] Step 3 完成: 生成 {len(conflict_questions)} 个冲突问题")
            except Exception as e:
                logger.error(f"❌ [DEBUG] Step 3 异常: {type(e).__name__}: {e}")
                import traceback

                traceback.print_exc()
                conflict_questions = []
            if conflict_questions:
                logger.info(f"🔍 V1.5可行性分析检测到冲突，注入 {len(conflict_questions)} 个资源约束问题")
            elif user_mentioned_constraints:
                logger.info(f"🔍 [v7.4] 用户提及约束 {user_mentioned_constraints}，但无对应冲突检测")
        else:
            logger.info(f"🔍 [DEBUG] Step 3 跳过: feasibility 为空")

        # 🆕 P2功能：动态调整问题数量
        # 根据问卷长度、冲突严重性、V1输出丰富度智能裁剪
        logger.info(f"🔍 [DEBUG] Step 4: 动态调整问题数量...")
        original_questions = questionnaire.get("questions", [])
        try:
            adjusted_philosophy_questions, adjusted_conflict_questions = QuestionAdjuster.adjust(
                philosophy_questions=philosophy_questions,
                conflict_questions=conflict_questions,
                original_question_count=len(original_questions),
                feasibility_data=feasibility,
            )
            logger.info(
                f"🔍 [DEBUG] Step 4 完成: 调整后理念={len(adjusted_philosophy_questions)}, 冲突={len(adjusted_conflict_questions)}"
            )
        except Exception as e:
            logger.error(f"❌ [DEBUG] Step 4 异常: {type(e).__name__}: {e}")
            import traceback

            traceback.print_exc()
            adjusted_philosophy_questions = philosophy_questions
            adjusted_conflict_questions = conflict_questions

        # 合并调整后的理念问题和冲突问题
        # 🚀 P1优化：竞标策略问题优先级最高，放在最前面
        all_injected_questions = (
            bidding_strategy_questions + adjusted_philosophy_questions + adjusted_conflict_questions
        )

        if all_injected_questions:
            if bidding_strategy_questions:
                logger.info(f"🎯 [P1] 竞标策略问题 {len(bidding_strategy_questions)} 个已加入注入队列")
            logger.info(
                f"✨ 总计注入 {len(all_injected_questions)} 个动态问题（理念{len(adjusted_philosophy_questions)}个 + 资源{len(adjusted_conflict_questions)}个）"
            )
            if len(adjusted_philosophy_questions) < len(philosophy_questions) or len(adjusted_conflict_questions) < len(
                conflict_questions
            ):
                logger.info(
                    f"📊 动态调整: 理念问题 {len(philosophy_questions)}→{len(adjusted_philosophy_questions)}, 冲突问题 {len(conflict_questions)}→{len(adjusted_conflict_questions)}"
                )

            # 将问题插入到问卷中（单选题之后）
            # 找到第一个非单选题的位置
            insert_position = 0
            for i, q in enumerate(original_questions):
                if q.get("type") != "single_choice":
                    insert_position = i
                    break
            # 插入所有动态问题
            updated_questions = (
                original_questions[:insert_position] + all_injected_questions + original_questions[insert_position:]
            )
            questionnaire["questions"] = updated_questions
            logger.info(f"✅ 已将动态问题插入到位置 {insert_position}，总问题数: {len(updated_questions)}")

        structured_data["calibration_questionnaire"] = questionnaire
        requirements_result["structured_data"] = structured_data
        agent_results["requirements_analyst"] = requirements_result
        state["calibration_questionnaire"] = questionnaire

        logger.info(f"✅ Active questionnaire contains {len(questionnaire.get('questions', []))} questions")

        # 🔧 修复问卷题型顺序（确保：单选→多选→文字输入）
        questions = questionnaire.get("questions", [])
        original_order = [q.get("type", "") for q in questions]

        single_choice = [q for q in questions if q.get("type") == "single_choice"]
        multiple_choice = [q for q in questions if q.get("type") == "multiple_choice"]
        open_ended = [q for q in questions if q.get("type") == "open_ended"]

        fixed_questions = single_choice + multiple_choice + open_ended
        fixed_order = [q.get("type", "") for q in fixed_questions]

        if original_order != fixed_order:
            logger.warning(f"⚠️ 问卷题型顺序不正确，已自动修复：")
            logger.warning(f"   原始: {original_order}")
            logger.warning(f"   修复: {fixed_order}")
            logger.info(f"   📊 统计: {len(single_choice)}个单选 + {len(multiple_choice)}个多选 + {len(open_ended)}个文字输入")
            questionnaire["questions"] = fixed_questions
        else:
            logger.info(f"✅ 问卷题型顺序正确：{len(single_choice)}个单选 → {len(multiple_choice)}个多选 → {len(open_ended)}个文字输入")

        warning_message = state.get("calibration_warning")
        skip_attempts = int(state.get("calibration_skip_attempts", 0) or 0)

        intent = ""
        content = ""
        additional_info = ""
        modifications = ""
        entries: List[Dict[str, Any]] = []
        answers_map: Dict[str, Any] = {}
        notes = ""

        skip_tokens = {"skip", "close", "cancel", "退出", "关闭", "取消", "放弃"}

        from ...utils.intent_parser import parse_user_intent

        while True:
            message_text = "请回答以下战略校准问题，以帮助我们更好地理解您的需求："
            if warning_message:
                message_text = f"{warning_message}\n\n{message_text}"

            questionnaire_payload = {
                "interaction_type": "calibration_questionnaire",
                "message": message_text,
                "questionnaire": {
                    "introduction": questionnaire.get("introduction", "以下问题旨在精准捕捉您在战术执行和美学表达层面的个人偏好"),
                    "questions": questionnaire.get("questions", []),
                    "note": questionnaire.get("note") or "这些问题不会改变核心战略方向，只是帮助我们更好地实现既定目标",
                },
                "options": {"submit": "提交问卷答案"},
            }

            logger.info(f"🛑 [QUESTIONNAIRE] 即将调用 interrupt()，等待用户输入...")
            logger.info(f"🛑 [QUESTIONNAIRE] payload keys: {list(questionnaire_payload.keys())}")
            logger.info(
                f"🛑 [QUESTIONNAIRE] questions count: {len(questionnaire_payload['questionnaire']['questions'])}"
            )

            user_response = interrupt(questionnaire_payload)
            logger.info(f"Received questionnaire response: {type(user_response)}")

            intent_result = parse_user_intent(user_response, context="战略校准问卷", stage="calibration_questionnaire")

            intent = intent_result["intent"]
            content = intent_result.get("content", "")
            additional_info = intent_result.get("additional_info", "")
            modifications = intent_result.get("modifications", "")

            logger.info(f"💬 用户意图解析: {intent} (方法: {intent_result['method']})")

            normalized_response = ""
            if isinstance(user_response, str):
                normalized_response = user_response.strip().lower()
            elif isinstance(user_response, dict):
                possible_keys = [
                    str(user_response.get("intent", "")),
                    str(user_response.get("action", "")),
                    str(user_response.get("value", "")),
                    str(user_response.get("resume_value", "")),
                ]
                normalized_response = next((val.strip().lower() for val in possible_keys if val), "")

            raw_answers_payload, implicit_notes = AnswerParser.extract_raw_answers(user_response)
            answers_payload = intent_result.get("answers") or raw_answers_payload
            entries, answers_map = AnswerParser.build_answer_entries(questionnaire, answers_payload)

            notes = (additional_info or implicit_notes or content).strip()

            skip_detected = (intent in {"skip"}) or (normalized_response in skip_tokens)
            if skip_detected:
                logger.info("⏭️ User chose to skip questionnaire, proceeding without answers")
                # 🔥 初始化 updated_state（在 skip 分支中提前返回需要初始化）
                updated_state: Dict[str, Any] = {}
                updated_state["calibration_processed"] = True
                updated_state["calibration_skipped"] = True
                updated_state["calibration_skip_attempts"] = skip_attempts
                updated_state["agent_results"] = agent_results

                # 保留 skip_unified_review 标志
                if state.get("skip_unified_review"):
                    updated_state["skip_unified_review"] = True
                    logger.info("🔍 [DEBUG] 保留 skip_unified_review=True")

                # 记录跳过交互
                skip_entry = {
                    "type": "calibration_questionnaire",
                    "intent": "skip",
                    "timestamp": datetime.now().isoformat(),
                    "question_count": len(questionnaire.get("questions", [])),
                }
                history = state.get("interaction_history", [])
                updated_state["interaction_history"] = history + [skip_entry]

                # 自动保留持久化标志
                updated_state = WorkflowFlagManager.preserve_flags(state, updated_state)

                logger.info(f"🔍 [DEBUG] Command.update 包含的键: {list(updated_state.keys())}")
                return Command(update=updated_state, goto="project_director")  # 🆕 v7.151

            if intent not in {"modify", "add", "revise"} and not answers_map:
                skip_attempts += 1
                warning_message = "请至少回答一个问题以继续。"
                logger.warning("⚠️ No valid answers captured, prompting questionnaire again")
                continue

            if intent == "add" and not (answers_map or notes):
                skip_attempts += 1
                warning_message = "请补充至少一个答案或说明，方便我们继续。"
                logger.warning("⚠️ Additional info intent received without content, prompting again")
                continue

            warning_message = None
            break

        timestamp = datetime.now().isoformat()

        updated_state: Dict[str, Any] = {
            "calibration_questionnaire": questionnaire,
            "calibration_skip_attempts": skip_attempts,
            "calibration_warning": warning_message,
            "agent_results": agent_results,
        }

        # 自动保留持久化标志
        updated_state = WorkflowFlagManager.preserve_flags(state, updated_state)

        interaction_entry = {
            "type": "calibration_questionnaire",
            "intent": intent,
            "timestamp": timestamp,
            "question_count": len(questionnaire.get("questions", [])),
        }
        if answers_map:
            interaction_entry["answers"] = answers_map
        if notes:
            interaction_entry["notes"] = notes

        history = state.get("interaction_history", [])
        updated_state["interaction_history"] = history + [interaction_entry]

        next_node = "project_director"  # 🆕 v7.151: 直接路由到 project_director
        should_reanalyze = False

        if intent == "modify":
            logger.info(f"⚠️ User requested modifications: {content[:100]}")
            modification_text = modifications or content
            updated_state["calibration_modifications"] = modification_text
            updated_state["user_feedback"] = notes or modification_text
            original_input = state.get("user_input", "")
            updated_state["user_input"] = f"{original_input}\n\n【用户修改意见】\n{modification_text}"
            next_node = "requirements_analyst"
            should_reanalyze = True

        elif intent == "add":
            logger.info(f"📝 User provided additional information: {content[:100]}")
            supplement_text = notes or content

            # ✅ 修复: 无论是否有补充文本，都要保存问卷答案（用于后续聚合）
            if answers_map:
                updated_state["calibration_answers"] = answers_map

                # 🔧 新增: 构建并保存 questionnaire_summary/responses（与 approve 分支一致）
                summary_entries = entries
                summary_payload = {
                    "entries": summary_entries,
                    "answers": answers_map,
                    "submitted_at": timestamp,
                    "timestamp": timestamp,
                    "notes": notes,
                    "source": "calibration_questionnaire",
                }
                updated_state["questionnaire_summary"] = summary_payload
                updated_state["questionnaire_responses"] = summary_payload
                # 🔥 v7.13: 修复 - add 意图也需要标记问卷已处理，防止 resume 后重复生成
                updated_state["calibration_processed"] = True
                logger.info(f"✅ [add 意图] 已保存 {len(answers_map)} 个问卷答案到 questionnaire_summary")

            if supplement_text:
                updated_state["additional_requirements"] = supplement_text

            if supplement_text and len(str(supplement_text).strip()) > 10:
                logger.info("🔄 Significant additional info detected, returning to requirements analyst")
                original_input = state.get("user_input", "")
                updated_state["user_input"] = f"{original_input}\n\n【用户补充信息】\n{supplement_text}"
                next_node = "requirements_analyst"
                should_reanalyze = True
            else:
                logger.info("✅ Minor additions, proceeding to confirmation")

        elif intent == "revise":
            logger.info("🔄 User requested re-analysis")
            next_node = "requirements_analyst"
            should_reanalyze = True

        else:
            logger.info("✅ User approved questionnaire")
            if answers_map:
                logger.info(f"📝 Integrating {len(answers_map)} questionnaire answers into requirements")

                summary_entries = entries
                summary_payload = {
                    "entries": summary_entries,
                    "answers": answers_map,
                    "submitted_at": timestamp,
                    "timestamp": timestamp,
                    "notes": notes,
                    "source": "calibration_questionnaire",
                }

                updated_state["calibration_answers"] = answers_map
                updated_state["questionnaire_summary"] = summary_payload
                updated_state["questionnaire_responses"] = summary_payload
                updated_state["calibration_processed"] = True

                # 构建简要文本并合并到用户需求描述中
                summary_lines = []
                for entry in summary_entries:
                    value = entry.get("value")
                    if isinstance(value, (list, tuple, set)):
                        value_text = "、".join(str(v) for v in value if str(v).strip())
                    else:
                        value_text = str(value)
                    summary_lines.append(f"- {entry.get('question', '偏好')}: {value_text}")

                if notes:
                    summary_lines.append(f"- 补充说明: {notes}")

                if summary_lines:
                    original_input = state.get("user_input", "")
                    insight_block = "\n".join(summary_lines)
                    updated_state["user_input"] = f"{original_input}\n\n【问卷洞察】\n{insight_block}"

                # 更新结构化需求，嵌入问卷洞察
                existing_requirements = state.get("structured_requirements") or {}
                questionnaire_insights = {
                    "entries": summary_entries,
                    "insights": {entry["id"]: entry["value"] for entry in summary_entries},
                    "submitted_at": timestamp,
                    "notes": notes,
                    "source": "calibration_questionnaire",
                }
                updated_state["structured_requirements"] = {
                    **existing_requirements,
                    "questionnaire_insights": questionnaire_insights,
                }

                next_node = "requirements_analyst"
                should_reanalyze = True
            else:
                logger.warning("⚠️ No valid answers captured, re-prompting questionnaire")
                updated_state["calibration_skip_attempts"] = skip_attempts + 1
                updated_state["calibration_warning"] = "请至少回答一个问题以继续。"
                next_node = "calibration_questionnaire"

        if should_reanalyze:
            logger.info(f"🔄 Routing back to {next_node} for re-analysis")
        else:
            logger.info(f"✅ Proceeding to {next_node}")

        logger.info(f"🔍 [DEBUG] Command.update 包含的键: {list(updated_state.keys())}")
        logger.info(f"🔍 [DEBUG] calibration_processed 值: {updated_state.get('calibration_processed')}")
        return Command(update=updated_state, goto=next_node)
