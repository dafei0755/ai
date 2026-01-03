"""
输入预检节点 - 工作流的第一道防线
"""

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from langgraph.store.base import BaseStore
from langgraph.types import Command, interrupt
from loguru import logger

from intelligent_project_analyzer.core.state import AnalysisStage, ProjectAnalysisState
from intelligent_project_analyzer.security.content_safety_guard import ContentSafetyGuard
from intelligent_project_analyzer.security.domain_classifier import DomainClassifier
from intelligent_project_analyzer.security.violation_logger import ViolationLogger
from intelligent_project_analyzer.services.capability_boundary_service import CapabilityBoundaryService, CheckType


class InputGuardNode:
    """输入预检节点 - 内容安全 + 领域过滤"""

    @staticmethod
    def execute(
        state: ProjectAnalysisState, store: Optional[BaseStore] = None, llm_model=None
    ) -> Command[Literal["requirements_analyst", "input_rejected"]]:
        """
        执行输入预检

        检查流程：
        1. 内容安全检测（优先级最高）
        2. 领域分类检测
        3. 记录违规/拒绝原因
        4. 路由决策

        Args:
            state: 项目分析状态
            store: 存储接口
            llm_model: LLM模型实例

        Returns:
            Command对象，指向下一个节点
        """
        logger.info("=" * 100)
        logger.info("🛡️ 输入预检：内容安全 + 领域过滤")
        logger.info("=" * 100)

        user_input = state.get("user_input", "")
        session_id = state.get("session_id", "")

        # 初始化检测器
        safety_guard = ContentSafetyGuard(llm_model=llm_model)
        domain_classifier = DomainClassifier(llm_model=llm_model)
        violation_logger = ViolationLogger()

        # === 第1关：内容安全检测 ===
        logger.info("🔍 第1关：内容安全检测")
        safety_result = safety_guard.check(user_input, context="input")

        if not safety_result["is_safe"]:
            logger.error(f"🚨 内容安全检测失败: {safety_result['violations']}")

            # 记录违规尝试
            violation_logger.log(
                {
                    "session_id": session_id,
                    "violation_type": "content_safety",
                    "details": safety_result["violations"],
                    "user_input": user_input[:200],  # 只记录前200字符
                }
            )

            # 构造拒绝响应
            rejection_message = InputGuardNode._build_safety_rejection_message(safety_result)

            updated_state = {
                "current_stage": AnalysisStage.INPUT_REJECTED.value
                if hasattr(AnalysisStage, "INPUT_REJECTED")
                else "INPUT_REJECTED",
                "rejection_reason": "content_safety_violation",
                "rejection_message": rejection_message,
                "violations": safety_result["violations"],
                "final_status": "rejected",
            }

            return Command(update=updated_state, goto="input_rejected")

        logger.info("✅ 内容安全检测通过")

        # === 第2关：领域分类检测 ===
        logger.info("🔍 第2关：领域分类检测")
        domain_result = domain_classifier.classify(user_input)

        # 🆕 优化：如果LLM判断非常明确（置信度>0.8），直接拒绝，不问用户
        if domain_result["is_design_related"] == False:
            confidence = domain_result.get("confidence", 0)

            # 高置信度（>0.8）：直接拒绝
            if confidence > 0.8:
                logger.warning(f"❌ 非设计领域问题（置信度{confidence:.2f}），直接拒绝")

                violation_logger.log(
                    {
                        "session_id": session_id,
                        "violation_type": "domain_mismatch",
                        "details": domain_result,
                        "user_input": user_input[:200],
                    }
                )

                domain_message = InputGuardNode._build_domain_guidance_message(domain_result)

                updated_state = {
                    "current_stage": "DOMAIN_MISMATCH",
                    "rejection_reason": "not_design_related",
                    "rejection_message": domain_message,
                    "domain_result": domain_result,
                    "final_status": "rejected",
                }

                return Command(update=updated_state, goto="input_rejected")

            # 中低置信度（0.5-0.8）：标记风险但继续
            else:
                logger.warning(f"⚠️ 可能非设计领域（置信度{confidence:.2f}），标记风险但继续")
                # 不拒绝，继续到后面的通过检测

        elif domain_result["is_design_related"] == "unclear":
            logger.info("⚠️ 领域不明确，需要用户澄清")

            # 使用interrupt让用户澄清
            clarification_data = {
                "interaction_type": "domain_clarification",
                "message": "您的需求不太明确，请帮我确认一下：",
                "questions": domain_result.get("suggested_questions", ["您是否需要进行空间设计方面的分析？", "这个项目是否涉及建筑、室内或景观设计？"]),
                "options": {"yes": "是的，这是空间设计相关的需求", "no": "不是，我问的是其他领域的问题", "clarify": "让我重新描述一下需求"},
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
                domain_message = InputGuardNode._build_domain_guidance_message(domain_result)
                updated_state = {
                    "current_stage": "DOMAIN_MISMATCH",
                    "rejection_reason": "user_confirmed_non_design",
                    "rejection_message": domain_message,
                    "final_status": "rejected",
                }
                return Command(update=updated_state, goto="input_rejected")

            elif action == "clarify" and clarification_text:
                # 用户重新描述，更新user_input并重新检测
                logger.info("🔄 用户重新描述需求，更新输入")
                updated_state = {
                    "user_input": clarification_text,
                    "original_input": user_input,
                    "clarification_provided": True,
                }
                # 递归调用自己，重新检测
                return InputGuardNode.execute({**state, **updated_state}, store=store, llm_model=llm_model)

            # 默认：用户确认是设计类，继续流程
            logger.info("✅ 用户确认为设计类需求")

        logger.info(f"✅ 领域检测通过 (置信度: {domain_result.get('confidence', 0):.2f})")
        if domain_result.get("matched_categories"):
            logger.info(f"   匹配类别: {domain_result['matched_categories']}")

        # 🆕 === 第3关：能力边界检查 + 任务复杂度评估 ===
        logger.info("🔍 第3关：能力边界检查 + 任务复杂度评估")

        # 3.1 能力边界检查
        logger.info("🔍 [CapabilityBoundary] 检查初始输入的能力边界")
        boundary_check = CapabilityBoundaryService.check_user_input(
            user_input=user_input,
            context={"node": "input_guard_node", "stage": "initial", "session_id": session_id},
            check_type=CheckType.FULL,
        )

        logger.info(f"📊 能力边界检查结果:")
        logger.info(f"   在能力范围内: {boundary_check.within_capability}")
        logger.info(f"   能力匹配度: {boundary_check.capability_score:.2f}")
        logger.info(f"   警告级别: {boundary_check.alert_level}")
        if boundary_check.transformations_needed:
            logger.info(f"   需要转化: {len(boundary_check.transformations_needed)} 项")
            for trans in boundary_check.transformations_needed:
                logger.info(f"     - '{trans['original']}' → '{trans['transformed_to']}'")

        # 3.2 任务复杂度评估
        complexity_result = domain_classifier.assess_task_complexity(user_input)

        logger.info(f"📊 复杂度评估结果:")
        logger.info(f"   复杂度: {complexity_result['complexity']}")
        logger.info(f"   置信度: {complexity_result['confidence']:.2f}")
        logger.info(f"   推理: {complexity_result['reasoning']}")
        logger.info(f"   推荐工作流: {complexity_result['suggested_workflow']}")
        logger.info(f"   推荐专家: {complexity_result['suggested_experts']}")
        logger.info(f"   预估时长: {complexity_result['estimated_duration']}")

        # === 通过所有检测 ===
        updated_state = {
            "input_guard_passed": True,
            "domain_classification": domain_result,
            "safety_check_passed": True,
            "domain_confidence": domain_result.get("confidence", 0),
            # 🆕 添加复杂度信息到状态
            "task_complexity": complexity_result["complexity"],
            "suggested_workflow": complexity_result["suggested_workflow"],
            "suggested_experts": complexity_result["suggested_experts"],
            "estimated_duration": complexity_result["estimated_duration"],
            "complexity_reasoning": complexity_result["reasoning"],
            "complexity_confidence": complexity_result["confidence"],
            # 🆕 添加能力边界检查结果到状态
            "initial_boundary_check": boundary_check,
            "capability_score": boundary_check.capability_score,
            "capability_alert_level": boundary_check.alert_level,
            "capability_transformations": boundary_check.transformations_needed,
        }

        logger.info("🎉 输入预检通过，进入需求分析")
        logger.info("=" * 100)
        return Command(update=updated_state, goto="requirements_analyst")

    @staticmethod
    def _build_safety_rejection_message(safety_result: Dict) -> str:
        """构造内容安全拒绝消息"""
        return """很抱歉，您的输入包含不适当的内容，我无法处理此类请求。

作为空间设计专业智能体，我专注于提供：

✅ **建筑与室内空间设计分析**
   - 办公空间、零售空间、展厅设计
   - 住宅、餐饮、酒店空间规划

✅ **商业空间规划与优化**
   - 功能分区与动线设计
   - 品牌形象与空间定位

✅ **用户体验与设计方案**
   - 用户行为分析
   - 空间体验优化

✅ **技术架构与实施方案**
   - 材料与工艺选择
   - 施工计划与成本控制

如果您有空间设计相关的需求，欢迎重新描述您的项目！"""

    @staticmethod
    def _build_domain_guidance_message(domain_result: Dict) -> str:
        """构造领域引导消息"""
        return """感谢您的咨询！不过，您的问题似乎不在我的专业领域范围内。

🏢 **我的专业领域：空间设计**

我擅长以下类型的设计分析：

✅ **办公空间设计**
   - 企业办公室、联合办公
   - 开放式/传统式办公布局

✅ **零售空间设计**
   - 品牌专卖店、集合店
   - 购物中心、商业街店铺

✅ **展览展厅设计**
   - 企业展厅、博物馆
   - 体验中心、艺术空间

✅ **餐饮空间设计**
   - 餐厅、咖啡厅、酒吧
   - 快餐店、主题餐饮

✅ **住宅空间设计**
   - 公寓、别墅、样板间
   - 室内装修与软装方案

✅ **其他空间类型**
   - 酒店、会所、公共空间
   - 景观设计、户外空间

📝 **如何正确提问？**

请尝试这样描述您的需求：
• "我需要设计一个200平米的咖啡厅"
• "帮我规划一个科技公司的办公空间"
• "品牌展厅如何体现企业文化"
• "小户型住宅如何优化空间布局"

期待为您提供专业的空间设计服务！"""


class InputRejectedNode:
    """输入拒绝节点 - 终止节点"""

    @staticmethod
    def execute(state: ProjectAnalysisState, store: Optional[BaseStore] = None) -> Dict[str, Any]:
        """
        处理输入拒绝

        Args:
            state: 项目分析状态
            store: 存储接口

        Returns:
            最终状态
        """
        logger.info("=" * 100)
        logger.info("❌ 输入被拒绝，流程终止")
        logger.info("=" * 100)

        # 🆕 调试：查看state内容
        logger.debug(f"State keys: {state.keys()}")
        logger.debug(f"rejection_reason in state: {'rejection_reason' in state}")
        logger.debug(f"rejection_message in state: {'rejection_message' in state}")

        rejection_reason = state.get("rejection_reason", "unknown")
        rejection_message = state.get("rejection_message", "输入不符合要求")

        logger.info(f"拒绝原因: {rejection_reason}")
        logger.info(f"拒绝消息: {rejection_message[:100]}...")

        return {
            "current_stage": "REJECTED",
            "rejection_message": rejection_message,
            "rejection_reason": rejection_reason,
            "final_status": "rejected",
            "completed_at": datetime.now().isoformat(),
        }
