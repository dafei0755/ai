"""需求确认节点 - 重构版 (继承 InteractionAgent基类)

示例展示如何使用统一的 InteractionAgent 基类实现需求确认节点。

原文件: requirements_confirmation.py (260行)
重构后: requirements_confirmation_refactored.py (约100行，减少60%)
"""

from typing import Dict, Any, Literal, Optional
from datetime import datetime
from loguru import logger
from langgraph.types import Command
from langgraph.store.base import BaseStore

from .interaction_agent_base import InteractionAgent, extract_intent_from_response
from ...core.state import ProjectAnalysisState, AnalysisStage
from ...core.types import InteractionType


class RequirementsConfirmationNode(InteractionAgent):
    """需求确认节点 - 继承统一基类"""

    # ========== 实现抽象方法 ==========

    def _get_interaction_type(self) -> str:
        """返回交互类型"""
        return "requirements_confirmation"

    def _should_skip(self, state: ProjectAnalysisState) -> tuple[bool, str]:
        """检查是否应跳过需求确认"""
        # 🔥 检查是否是用户修改后的重新分析（应直接跳过确认）
        if state.get("user_modification_processed"):
            return True, "用户修改已重新分析完成，跳过二次确认"

        # 追问模式下可能需要跳过（根据业务逻辑）
        if state.get("is_followup") and state.get("skip_requirements_confirmation"):
            return True, "追问模式下跳过需求确认"

        return False, ""

    def _validate_state(self, state: ProjectAnalysisState) -> tuple[bool, str]:
        """验证状态完整性"""
        structured_requirements = state.get("structured_requirements")

        if not structured_requirements:
            return False, "No structured requirements found"

        # 检查必需字段
        required_fields = ["project_task", "character_narrative"]
        missing_fields = [f for f in required_fields if not structured_requirements.get(f)]

        if missing_fields:
            return False, f"Missing required fields: {', '.join(missing_fields)}"

        return True, ""

    def _prepare_interaction_data(
        self,
        state: ProjectAnalysisState,
        store: Optional[BaseStore] = None
    ) -> Dict[str, Any]:
        """准备需求确认交互数据"""
        structured_requirements = state.get("structured_requirements", {})
        current_datetime = datetime.now().strftime("%Y年%m月%d日 %H:%M")

        # ✅ 构建带中文标签的需求摘要
        requirements_summary = []

        field_mapping = [
            ("project_task", "项目任务", "📋"),
            ("character_narrative", "核心用户画像", "👤"),
            ("space_constraints", "空间约束", "📐"),
            ("inspiration_references", "灵感参考", "💡"),
            ("experience_behavior", "体验行为", "🎯"),
            ("core_tension", "核心张力", "⚡")
        ]

        for field_key, field_label, icon in field_mapping:
            field_value = structured_requirements.get(field_key, "")
            if field_value and field_value != "待进一步分析":
                requirements_summary.append({
                    "key": field_key,
                    "label": field_label,
                    "icon": icon,
                    "content": field_value
                })

        # 检查是否已融合问卷信息
        message = "请确认以下需求分析是否准确（如需修改，直接编辑后提交即可）："
        if state.get("calibration_processed"):
            message = "✅ 已根据您的问卷反馈更新分析结果。请确认以下需求分析是否准确（如需修改，直接编辑后提交即可）："

        return {
            "interaction_type": self.interaction_type,
            "message": message,
            "analysis_metadata": {
                "analysis_datetime": current_datetime,
                "datetime_enabled": True,
                "datetime_purpose": "确保分析结果基于最新的设计趋势和行业数据"
            },
            "requirements_summary": requirements_summary,
            "options": {
                "approve": "确认需求分析准确，继续项目分析",
                "revise": "需求分析需要修改，重新分析需求"
            }
        }

    def _process_response(
        self,
        state: ProjectAnalysisState,
        user_response: Any,
        store: Optional[BaseStore] = None
    ) -> Command[Literal["project_director", "requirements_analyst"]]:
        """处理用户响应"""
        # 解析用户意图
        intent = extract_intent_from_response(user_response)

        logger.info(f"User intent: {intent}")

        # 提取详细信息
        feedback = None
        additional_info = None
        modifications = None

        if isinstance(user_response, dict):
            feedback = user_response.get("feedback")
            additional_info = user_response.get("additional_info", "")
            modifications = user_response.get("modifications", {})

        # 智能修改检测
        has_real_modifications = self._detect_real_modifications(state, modifications)
        has_additions = additional_info and len(str(additional_info).strip()) > 10

        is_approved = intent in ["approve", "confirm"]

        if is_approved:
            if has_real_modifications or has_additions:
                # 用户批准但提供了修改/补充
                logger.info("⚠️ User approved BUT provided modifications/additions")
                return self._handle_approved_with_modifications(
                    state, modifications, additional_info, has_real_modifications
                )
            else:
                # 纯粹的批准
                logger.info("✅ Requirements confirmed without modifications")
                return Command(
                    update={"requirements_confirmed": True, "modification_confirmation_round": 0},
                    goto="project_director"
                )
        else:
            # 需要修订
            logger.info("⚠️ Requirements need revision")
            return self._handle_revision(state, feedback, modifications, additional_info)

    # ========== 辅助方法 ==========

    def _detect_real_modifications(
        self,
        state: ProjectAnalysisState,
        modifications: Any
    ) -> bool:
        """智能检测用户是否真的修改了内容

        使用深度规范化比较，过滤掉格式差异。

        Args:
            state: 项目分析状态
            modifications: 用户修改内容

        Returns:
            bool: 是否有真实修改
        """
        if not modifications or not isinstance(modifications, dict):
            return False

        current_requirements = state.get("structured_requirements", {})

        def normalize_text(text: str) -> str:
            """深度规范化文本"""
            import re
            text = str(text).strip()
            text = text.replace('\r\n', '\n').replace('\r', '\n')
            text = re.sub(r' +', ' ', text)
            text = re.sub(r'\n+', '\n', text)
            text = text.replace('；', ';').replace('：', ':').replace('，', ',')
            text = text.replace(''', "'").replace(''', "'").replace('"', '"').replace('"', '"')
            return text.strip()

        for field, new_value in modifications.items():
            current_value = current_requirements.get(field, "")

            # 深度规范化比较
            new_normalized = normalize_text(new_value)
            current_normalized = normalize_text(current_value)

            if new_normalized != current_normalized:
                # 计算实际差异长度
                diff_chars = sum(1 for a, b in zip(new_normalized, current_normalized) if a != b)
                diff_chars += abs(len(new_normalized) - len(current_normalized))

                # 只有差异超过10个字符才算真实修改
                if diff_chars > 10:
                    logger.info(f"🔍 检测到字段 '{field}' 有真实修改 (差异字符数: {diff_chars})")
                    return True

        logger.info("✅ 用户提交的 modifications 与当前值相同(或差异<10字符),视为无修改")
        return False

    def _handle_approved_with_modifications(
        self,
        state: ProjectAnalysisState,
        modifications: Dict,
        additional_info: str,
        has_real_modifications: bool
    ) -> Command[Literal["requirements_analyst"]]:
        """处理：用户批准但提供了修改/补充"""
        logger.info("🔄 用户修改需要重新分析以更新 expert_handoff，但不再返回确认页面")

        updated_state = {}

        # 融入用户修改到结构化需求
        if has_real_modifications:
            current_requirements = state.get("structured_requirements", {})
            updated_requirements = dict(current_requirements)

            for field_key, new_value in modifications.items():
                if field_key in updated_requirements:
                    logger.info(f"📝 融入用户修改: {field_key}")
                    updated_requirements[field_key] = new_value

            updated_state["structured_requirements"] = updated_requirements

        # 追加修改到 user_input
        original_input = state.get("user_input", "")
        supplement_text = ""

        if has_real_modifications:
            mod_text = "\n".join([f"- {k}: {v}" for k, v in modifications.items()])
            supplement_text += f"\n\n【用户修改补充】\n{mod_text}"

        if additional_info and len(str(additional_info).strip()) > 10:
            supplement_text += f"\n\n【用户补充信息】\n{additional_info}"

        updated_state["user_input"] = original_input + supplement_text
        updated_state["requirements_confirmed"] = False
        updated_state["has_user_modifications"] = True
        updated_state["user_modification_processed"] = True
        updated_state["user_modification_summary"] = supplement_text

        logger.info("🔄 返回 requirements_analyst 重新分析以更新 expert_handoff")

        return Command(update=updated_state, goto="requirements_analyst")

    def _handle_revision(
        self,
        state: ProjectAnalysisState,
        feedback: Optional[str],
        modifications: Any,
        additional_info: Optional[str]
    ) -> Command[Literal["requirements_analyst"]]:
        """处理：用户明确要求修订"""
        updated_state = {"requirements_confirmed": False}

        # 收集所有反馈信息
        if feedback:
            updated_state["user_feedback"] = feedback

        if modifications:
            original_input = state.get("user_input", "")
            updated_state["user_input"] = f"{original_input}\n\n【用户修改意见】\n{modifications}"

        if additional_info:
            original_input = updated_state.get("user_input", state.get("user_input", ""))
            updated_state["user_input"] = f"{original_input}\n\n【用户补充信息】\n{additional_info}"

        return Command(update=updated_state, goto="requirements_analyst")

    def _get_fallback_node(self, state: ProjectAnalysisState) -> str:
        """重写回退节点"""
        return "requirements_analyst"

    def _get_next_node_after_skip(self, state: ProjectAnalysisState) -> str:
        """重写跳过后的下一节点"""
        return "project_director"


# ========== 向后兼容的工厂函数 ==========

_node_instance = None

def get_requirements_confirmation_node() -> RequirementsConfirmationNode:
    """获取单例节点实例"""
    global _node_instance
    if _node_instance is None:
        _node_instance = RequirementsConfirmationNode()
    return _node_instance


# 向后兼容: 原有调用方式
def execute_requirements_confirmation(
    state: ProjectAnalysisState,
    store: Optional[BaseStore] = None
) -> Command:
    """向后兼容的执行函数

    原调用: RequirementsConfirmationNode.execute(state, store)
    新调用: get_requirements_confirmation_node().execute(state, store)
    """
    node = get_requirements_confirmation_node()
    return node.execute(state, store)
