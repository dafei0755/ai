"""
统一输入验证节点 - 内容安全 + 领域验证 + 复杂度评估

合并了原 input_guard_node 和 domain_validator_node 的功能，
通过智能路由减少重复检测，提升性能和用户体验。
"""

from datetime import datetime
from typing import Any, Dict, Literal, Union

from langgraph.store.base import BaseStore
from langgraph.types import Command, interrupt
from loguru import logger

from intelligent_project_analyzer.core.state import AnalysisStage, ProjectAnalysisState
from intelligent_project_analyzer.security.content_safety_guard import ContentSafetyGuard
from intelligent_project_analyzer.security.domain_classifier import DomainClassifier
from intelligent_project_analyzer.security.violation_logger import ViolationLogger


class UnifiedInputValidatorNode:
    """统一输入验证节点 - 两阶段验证策略"""

    @staticmethod
    def execute_initial_validation(
        state: ProjectAnalysisState,
        store: BaseStore | None = None,
        llm_model = None
    ) -> Command[Literal["requirements_analyst", "input_rejected"]]:
        """
        阶段1: 初始验证（原 input_guard 功能）

        执行流程：
        1. 内容安全检测（ContentSafetyGuard）
        2. 领域分类检测（DomainClassifier）
        3. 任务复杂度评估
        4. 决策是否需要二次验证

        Args:
            state: 项目分析状态
            store: 存储接口
            llm_model: LLM模型实例

        Returns:
            Command对象，指向下一个节点
        """
        logger.info("=" * 100)
        logger.info("️ 统一输入验证 - 阶段1: 初始验证")
        logger.info("=" * 100)

        user_input = state.get("user_input", "")
        session_id = state.get("session_id", "")

        # 初始化检测器
        safety_guard = ContentSafetyGuard(llm_model=llm_model)
        domain_classifier = DomainClassifier(llm_model=llm_model)
        violation_logger = ViolationLogger()

        # ============================================================================
        # 第1关：内容安全检测
        # ============================================================================
        logger.info(" 第1关：内容安全检测")
        safety_result = safety_guard.check(user_input, context="input")

        if not safety_result["is_safe"]:
            logger.error(f" 内容安全检测失败: {safety_result['violations']}")

            # 记录违规尝试
            violation_logger.log({
                "session_id": session_id,
                "violation_type": "content_safety",
                "details": safety_result["violations"],
                "user_input": user_input[:200]
            })

            # 构造拒绝响应
            rejection_message = UnifiedInputValidatorNode._build_safety_rejection_message(safety_result)

            updated_state = {
                "current_stage": AnalysisStage.INPUT_REJECTED.value if hasattr(AnalysisStage, 'INPUT_REJECTED') else "INPUT_REJECTED",
                "rejection_reason": "content_safety_violation",
                "rejection_message": rejection_message,
                "violations": safety_result["violations"],
                "final_status": "rejected"
            }

            return Command(update=updated_state, goto="input_rejected")

        logger.info(" 内容安全检测通过")

        # ============================================================================
        # 第2关：领域分类检测
        # ============================================================================
        logger.info(" 第2关：领域分类检测")
        domain_result = domain_classifier.classify(user_input)

        # 处理命名任务（特殊逻辑）
        is_naming_task = any(kw in user_input.lower() for kw in ["命名", "起名", "取名", "名字", "叫什么"])

        # 高置信度非设计类：直接拒绝
        if domain_result["is_design_related"] == False:
            confidence = domain_result.get("confidence", 0)

            if confidence > 0.8 and not is_naming_task:
                logger.warning(f" 非设计领域问题（置信度{confidence:.2f}），直接拒绝")

                violation_logger.log({
                    "session_id": session_id,
                    "violation_type": "domain_mismatch",
                    "details": domain_result,
                    "user_input": user_input[:200]
                })

                domain_message = UnifiedInputValidatorNode._build_domain_guidance_message(domain_result)

                updated_state = {
                    "current_stage": "DOMAIN_MISMATCH",
                    "rejection_reason": "not_design_related",
                    "rejection_message": domain_message,
                    "domain_result": domain_result,
                    "final_status": "rejected"
                }

                return Command(update=updated_state, goto="input_rejected")

            # 中低置信度：标记风险但继续
            else:
                logger.warning(f"️ 可能非设计领域（置信度{confidence:.2f}），标记风险但继续")

        # 领域不明确：interrupt 用户澄清
        elif domain_result["is_design_related"] == "unclear":
            logger.info("️ 领域不明确，需要用户澄清")

            clarification_data = {
                "interaction_type": "domain_clarification",
                "message": "您的需求不太明确，请帮我确认一下：",
                "questions": domain_result.get("suggested_questions", [
                    "您是否需要进行空间设计方面的分析？",
                    "这个项目是否涉及建筑、室内或景观设计？"
                ]),
                "options": {
                    "yes": "是的，这是空间设计相关的需求",
                    "no": "不是，我问的是其他领域的问题",
                    "clarify": "让我重新描述一下需求"
                }
            }

            user_response = interrupt(clarification_data)

            # 处理用户响应
            if isinstance(user_response, dict):
                action = user_response.get("action", "clarify")
                clarification_text = user_response.get("clarification", "")
            elif isinstance(user_response, str):
                action = user_response if user_response in ["yes", "no", "clarify"] else "clarify"
                clarification_text = user_response
            else:
                action = "clarify"
                clarification_text = str(user_response)

            if action == "no":
                # 用户确认非设计类
                domain_message = UnifiedInputValidatorNode._build_domain_guidance_message(domain_result)
                updated_state = {
                    "current_stage": "DOMAIN_MISMATCH",
                    "rejection_reason": "user_confirmed_non_design",
                    "rejection_message": domain_message,
                    "final_status": "rejected"
                }
                return Command(update=updated_state, goto="input_rejected")

            elif action == "clarify" and clarification_text:
                # 用户重新描述，更新user_input并重新检测
                logger.info(" 用户重新描述需求，更新输入")
                updated_state = {
                    "user_input": clarification_text,
                    "original_input": user_input,
                    "clarification_provided": True
                }
                # 递归调用自己，重新检测
                return UnifiedInputValidatorNode.execute_initial_validation(
                    {**state, **updated_state},
                    store=store,
                    llm_model=llm_model
                )

            # 默认：用户确认是设计类，继续流程
            logger.info(" 用户确认为设计类需求")

        logger.info(f" 领域检测通过 (置信度: {domain_result.get('confidence', 0):.2f})")
        if domain_result.get('matched_categories'):
            logger.info(f"   匹配类别: {domain_result['matched_categories']}")

        # ============================================================================
        # 第3关：决策是否需要二次验证
        # ============================================================================
        initial_confidence = domain_result.get("confidence", 0)
        needs_secondary_validation = initial_confidence < 0.85

        if needs_secondary_validation:
            logger.info(f"️ 初始置信度 {initial_confidence:.2f} < 0.85，标记需要二次验证")
        else:
            logger.info(f" 初始置信度 {initial_confidence:.2f} ≥ 0.85，跳过二次验证")

        # ============================================================================
        # 通过所有检测，放行
        # ============================================================================
        # 注意: 移除task_complexity等字段，复杂度判断已整合到项目总监
        updated_state = {
            "initial_validation_passed": True,
            "domain_classification": domain_result,
            "safety_check_passed": True,
            "domain_confidence": initial_confidence,
            "needs_secondary_validation": needs_secondary_validation
        }

        logger.info(" 初始验证通过，进入需求分析")
        logger.info("=" * 100)
        return Command(update=updated_state, goto="requirements_analyst")

    @staticmethod
    def execute_secondary_validation(
        state: ProjectAnalysisState,
        store: BaseStore | None = None,
        llm_model = None
    ) -> Union[Dict[str, Any], Command]:
        """
        阶段2: 二次验证（原 domain_validator 功能，条件触发）

        执行流程：
        1. 检查是否需要二次验证
        2. 提取需求分析结果的项目摘要
        3. 重新领域分类
        4. 领域漂移检测
        5. 置信度趋势分析

        Args:
            state: 项目分析状态
            store: 存储接口
            llm_model: LLM模型实例

        Returns:
            Dict: 状态更新（继续流程）
            Command(goto="input_rejected"): 拒绝
            Command(goto="requirements_analyst"): 重新分析
        """
        logger.info("=" * 100)
        logger.info("️ 统一输入验证 - 阶段2: 二次验证")
        logger.info("=" * 100)

        # ============================================================================
        # 第1步：检查是否需要二次验证
        # ============================================================================
        needs_secondary = state.get("needs_secondary_validation", False)
        initial_confidence = state.get("domain_confidence", 0)

        if not needs_secondary and initial_confidence >= 0.85:
            logger.info(f" 初始置信度 {initial_confidence:.2f} ≥ 0.85，跳过二次验证")
            return {
                "secondary_validation_skipped": True,
                "secondary_validation_reason": "high_initial_confidence"
            }

        logger.info(f" 初始置信度 {initial_confidence:.2f}，执行二次验证")

        # ============================================================================
        # 第2步：提取需求分析结果的项目摘要
        # ============================================================================
        agent_results = state.get("agent_results", {})
        requirements_analyst_result = agent_results.get("requirements_analyst", {})
        requirements_result = requirements_analyst_result.get("structured_data", {})

        # 兼容旧版本
        if not requirements_result:
            requirements_result = state.get("structured_requirements", {})

        user_input = state.get("user_input", "")
        session_id = state.get("session_id", "")

        logger.info(f" [DEBUG] requirements_result keys: {list(requirements_result.keys()) if requirements_result else 'None'}")

        # 提取项目摘要
        project_summary = UnifiedInputValidatorNode._extract_project_summary(requirements_result)

        if not project_summary:
            logger.error(" 需求分析结果为空，无法继续")
            return {
                "error": "Requirements analysis result is empty",
                "secondary_validation_skipped": True
            }

        logger.info(f" 项目摘要: {project_summary[:200]}...")

        # ============================================================================
        # 第3步：重新领域分类
        # ============================================================================
        domain_classifier = DomainClassifier(llm_model=llm_model)
        violation_logger = ViolationLogger()

        domain_result = domain_classifier.classify(project_summary)
        secondary_confidence = domain_result.get("confidence", 0)

        logger.info(" 二次验证结果:")
        logger.info(f"   是否设计类: {domain_result['is_design_related']}")
        logger.info(f"   置信度: {secondary_confidence:.2f}")
        logger.info(f"   匹配类别: {domain_result.get('matched_categories', [])}")

        # ============================================================================
        # 第4步：领域漂移检测
        # ============================================================================
        if domain_result["is_design_related"] == False:
            logger.error(" 领域漂移检测：需求分析结果偏离设计领域")

            # 记录漂移尝试
            violation_logger.log({
                "session_id": session_id,
                "violation_type": "domain_drift",
                "details": domain_result,
                "user_input": user_input[:200],
                "analysis_summary": project_summary[:200]
            })

            # Interrupt：让用户确认是否调整
            drift_data = {
                "interaction_type": "domain_drift_alert",
                "message": "️ 检测到需求可能偏离空间设计领域",
                "drift_details": {
                    "original_input": user_input[:300],
                    "analysis_summary": project_summary[:300],
                    "detected_domain": domain_result.get("detected_domain", "未知领域"),
                    "non_design_categories": domain_result.get("matched_non_design_categories", [])
                },
                "options": {
                    "adjust": "我想调整需求，回到设计领域",
                    "continue": "我确认这是设计类需求，请继续",
                    "reject": "确实不是设计类，终止分析"
                }
            }

            user_response = interrupt(drift_data)

            # 处理用户选择
            if isinstance(user_response, dict):
                action = user_response.get("action", "reject")
                adjustment = user_response.get("adjustment", "")
            elif isinstance(user_response, str):
                action = user_response if user_response in ["adjust", "continue", "reject"] else "reject"
                adjustment = user_response
            else:
                action = "reject"
                adjustment = ""

            if action == "reject":
                logger.info(" 用户确认终止分析")
                return Command(
                    update={
                        "rejection_reason": "domain_drift_confirmed",
                        "rejection_message": "分析过程中发现需求偏离空间设计领域，已终止分析。"
                    },
                    goto="input_rejected"
                )

            elif action == "adjust" and adjustment:
                logger.info(" 用户提供调整意见，重新分析需求")
                return Command(
                    update={
                        "user_input": adjustment,
                        "original_input": user_input,
                        "drift_adjustment": True
                    },
                    goto="requirements_analyst"
                )

            # action == "continue"：用户坚持继续，标记为风险项
            logger.warning("️ 用户坚持继续，标记为领域风险项")
            return {
                "domain_risk_flag": True,
                "domain_risk_details": domain_result,
                "secondary_validation_passed": True,
                "secondary_domain_confidence": secondary_confidence
            }

        # ============================================================================
        # 第5步：领域不明确处理
        # ============================================================================
        if domain_result["is_design_related"] == "unclear":
            logger.info("️ 领域一致性不明确，置信度不足")

            # 如果输入预检时置信度已经很高，这里不再打断
            if initial_confidence >= 0.7:
                logger.info(" 输入预检置信度高，信任初始判断")
                return {
                    "secondary_validation_passed": True,
                    "secondary_domain_confidence": secondary_confidence,
                    "trust_initial_judgment": True
                }

            # 否则，让用户确认
            unclear_data = {
                "interaction_type": "domain_unclear",
                "message": "需求的领域归属不太明确，需要您确认一下：",
                "analysis_summary": project_summary[:300],
                "questions": [
                    "这个项目是否涉及空间设计（建筑/室内/景观）？",
                    "您希望我从设计角度还是其他角度分析？"
                ],
                "options": {
                    "design": "是的，这是空间设计项目",
                    "other": "不是，请终止分析"
                }
            }

            user_response = interrupt(unclear_data)

            if isinstance(user_response, dict):
                action = user_response.get("action", "other")
            elif isinstance(user_response, str):
                action = user_response if user_response in ["design", "other"] else "other"
            else:
                action = "other"

            if action == "other":
                return Command(
                    update={
                        "rejection_reason": "domain_unclear_rejected",
                        "rejection_message": "无法确认需求属于空间设计领域，已终止分析。"
                    },
                    goto="input_rejected"
                )

            # 用户确认为设计类
            logger.info(" 用户确认为设计类，继续流程")
            return {
                "domain_user_confirmed": True,
                "secondary_validation_passed": True,
                "secondary_domain_confidence": secondary_confidence
            }

        # ============================================================================
        # 第6步：置信度趋势分析
        # ============================================================================
        confidence_delta = secondary_confidence - initial_confidence

        if confidence_delta > 0.2:
            logger.info(f" 置信度显著上升: {initial_confidence:.2f} → {secondary_confidence:.2f} (+{confidence_delta:.2f})")
            # 可以考虑更新推荐专家（未来优化）
        elif confidence_delta < -0.2:
            logger.warning(f" 置信度显著下降: {initial_confidence:.2f} → {secondary_confidence:.2f} ({confidence_delta:.2f})")
            # 警告但继续
        else:
            logger.info(f" 置信度稳定: {initial_confidence:.2f} → {secondary_confidence:.2f} ({confidence_delta:+.2f})")

        # ============================================================================
        # 第7步：通过验证
        # ============================================================================
        logger.info(f" 二次验证通过 (置信度: {secondary_confidence:.2f})")
        if domain_result.get('matched_categories'):
            logger.info(f"   匹配类别: {domain_result['matched_categories']}")

        logger.info("=" * 100)
        return {
            "secondary_validation_passed": True,
            "secondary_domain_confidence": secondary_confidence,
            "confidence_delta": confidence_delta,
            "validated_confidence": secondary_confidence
        }

    # ============================================================================
    # 辅助方法
    # ============================================================================

    @staticmethod
    def _extract_project_summary(requirements_result: Dict) -> str:
        """从需求分析结果中提取项目摘要"""
        if not requirements_result:
            return ""

        summary_parts = []

        # V3.5 新格式字段
        if "project_task" in requirements_result:
            task = requirements_result["project_task"]
            if task:
                summary_parts.append(f"项目任务: {task}")

        if "project_overview" in requirements_result:
            overview = requirements_result["project_overview"]
            if overview:
                summary_parts.append(f"项目概述: {overview}")

        if "core_objectives" in requirements_result:
            objs = requirements_result["core_objectives"]
            if isinstance(objs, list):
                summary_parts.append(f"核心目标: {', '.join(objs[:3])}")
            elif isinstance(objs, str):
                summary_parts.append(f"核心目标: {objs}")

        if "design_challenge" in requirements_result:
            challenge = requirements_result["design_challenge"]
            if challenge:
                summary_parts.append(f"设计挑战: {challenge}")

        if "physical_context" in requirements_result:
            context = requirements_result["physical_context"]
            if context:
                summary_parts.append(f"物理环境: {context}")

        # 兼容旧格式
        if not summary_parts:
            if "project_info" in requirements_result:
                info = requirements_result["project_info"]
                if isinstance(info, dict):
                    summary_parts.append(f"项目名称: {info.get('name', '')}")
                    summary_parts.append(f"项目类型: {info.get('type', '')}")
                    summary_parts.append(f"项目描述: {info.get('description', '')}")

            if "core_requirements" in requirements_result:
                reqs = requirements_result["core_requirements"]
                if isinstance(reqs, list):
                    summary_parts.append(f"核心需求: {', '.join(reqs[:5])}")
                elif isinstance(reqs, str):
                    summary_parts.append(f"核心需求: {reqs}")

            if "objectives" in requirements_result:
                objs = requirements_result["objectives"]
                if isinstance(objs, list):
                    summary_parts.append(f"目标: {', '.join(objs[:3])}")
                elif isinstance(objs, str):
                    summary_parts.append(f"目标: {objs}")

        # 如果所有字段都提取失败，直接转字符串
        if not summary_parts:
            summary_parts.append(str(requirements_result)[:500])

        return " | ".join(summary_parts)

    @staticmethod
    def _build_safety_rejection_message(safety_result: Dict) -> str:
        """构造内容安全拒绝消息"""
        return """很抱歉，您的输入包含不适当的内容，我无法处理此类请求。

作为空间设计专业智能体，我专注于提供：

 **建筑与室内空间设计分析**
   - 办公空间、零售空间、展厅设计
   - 住宅、餐饮、酒店空间规划

 **商业空间规划与优化**
   - 功能分区与动线设计
   - 品牌形象与空间定位

 **用户体验与设计方案**
   - 用户行为分析
   - 空间体验优化

 **技术架构与实施方案**
   - 材料与工艺选择
   - 施工计划与成本控制

如果您有空间设计相关的需求，欢迎重新描述您的项目！"""

    @staticmethod
    def _build_domain_guidance_message(domain_result: Dict) -> str:
        """构造领域引导消息"""
        return """感谢您的咨询！不过，您的问题似乎不在我的专业领域范围内。

 **我的专业领域：空间设计**

我擅长以下类型的设计分析：

 **办公空间设计**
   - 企业办公室、联合办公
   - 开放式/传统式办公布局

 **零售空间设计**
   - 品牌专卖店、集合店
   - 购物中心、商业街店铺

 **展览展厅设计**
   - 企业展厅、博物馆
   - 体验中心、艺术空间

 **餐饮空间设计**
   - 餐厅、咖啡厅、酒吧
   - 快餐店、主题餐饮

 **住宅空间设计**
   - 公寓、别墅、样板间
   - 室内装修与软装方案

 **其他空间类型**
   - 酒店、会所、公共空间
   - 景观设计、户外空间

 **如何正确提问？**

请尝试这样描述您的需求：
• "我需要设计一个200平米的咖啡厅"
• "帮我规划一个科技公司的办公空间"
• "品牌展厅如何体现企业文化"
• "小户型住宅如何优化空间布局"

期待为您提供专业的空间设计服务！"""


class InputRejectedNode:
    """输入拒绝节点 - 终止节点（保留兼容性）"""

    @staticmethod
    def execute(
        state: ProjectAnalysisState,
        store: BaseStore | None = None
    ) -> Dict[str, Any]:
        """
        处理输入拒绝

        Args:
            state: 项目分析状态
            store: 存储接口

        Returns:
            最终状态
        """
        logger.info("=" * 100)
        logger.info(" 输入被拒绝，流程终止")
        logger.info("=" * 100)

        rejection_reason = state.get("rejection_reason", "unknown")
        rejection_message = state.get("rejection_message", "输入不符合要求")

        logger.info(f"拒绝原因: {rejection_reason}")
        logger.info(f"拒绝消息: {rejection_message[:100]}...")

        return {
            "current_stage": "REJECTED",
            "rejection_message": rejection_message,
            "rejection_reason": rejection_reason,
            "final_status": "rejected",
            "completed_at": datetime.now().isoformat()
        }
