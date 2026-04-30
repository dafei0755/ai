"""需求确认节点"""

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from langgraph.store.base import BaseStore
from langgraph.types import Command, interrupt
from loguru import logger

from ...core.state import AnalysisStage, ProjectAnalysisState
from ...core.types import InteractionType
from ...services.capability_boundary_service import CapabilityBoundaryService, CheckType


class RequirementsConfirmationNode:
    """需求确认节点"""

    @staticmethod
    def execute(
        state: ProjectAnalysisState, store: Optional[BaseStore] = None
    ) -> Command[Literal["project_director", "requirements_analyst"]]:
        """
        执行需求确认交互

        Args:
            state: 项目分析状态
            store: 存储接口

        Returns:
            Command对象，指向下一个节点
        """
        logger.info("Starting requirements confirmation interaction")

        #  检查是否是用户修改后的重新分析（应直接跳过确认）
        if state.get("user_modification_processed"):
            logger.info(" 用户修改已重新分析完成，跳过二次确认，直接进入项目总监")
            return Command(
                update={"requirements_confirmed": True, "user_modification_processed": False}, goto="project_director"
            )

        # 准备确认信息
        structured_requirements = state.get("structured_requirements")

        if not structured_requirements:
            logger.warning("No structured requirements found, returning to requirements analyst")
            return Command(update={"error": "No structured requirements found"}, goto="requirements_analyst")

        # 获取当前日期时间
        current_datetime = datetime.now().strftime("%Y年%m月%d日 %H:%M")

        #  构建带中文标签的需求摘要（标签与内容不分离）
        requirements_summary = []

        field_mapping = [
            ("project_task", "项目任务", ""),
            ("character_narrative", "核心用户画像", ""),
            ("space_constraints", "空间约束", ""),
            ("inspiration_references", "灵感参考", ""),
            ("experience_behavior", "体验行为", ""),
            ("core_tension", "核心张力", ""),
        ]

        for field_key, field_label, icon in field_mapping:
            field_value = structured_requirements.get(field_key, "")
            if field_value and field_value != "待进一步分析":
                requirements_summary.append(
                    {"key": field_key, "label": field_label, "icon": icon, "content": field_value}
                )

        # 检查是否已融合问卷信息
        message = "请确认以下需求分析是否准确（如需修改，直接编辑后提交即可）："
        if state.get("calibration_processed"):
            message = " 已根据您的问卷反馈更新分析结果。请确认以下需求分析是否准确（如需修改，直接编辑后提交即可）："

        confirmation_data = {
            "interaction_type": "requirements_confirmation",
            "message": message,
            #  分析元数据（datetime 功能可见性）
            "analysis_metadata": {
                "analysis_datetime": current_datetime,
                "datetime_enabled": True,
                "datetime_purpose": "确保分析结果基于最新的设计趋势和行业数据",
            },
            #  优化：标签与内容组合，便于前端直接渲染
            "requirements_summary": requirements_summary,
            "options": {"approve": "确认需求分析准确，继续项目分析", "revise": "需求分析需要修改，重新分析需求"},
        }

        logger.info(f" [DEBUG] 准备 requirements_confirmation interrupt 数据")
        logger.info(f" [DEBUG] requirements_summary 字段数: {len(requirements_summary)}")
        logger.info(f" [DEBUG] message: {message}")

        # 使用interrupt暂停执行，等待用户确认
        user_response = interrupt(confirmation_data)
        logger.info(f"Received user response: {user_response}")
        logger.info(f" [DEBUG] user_response type: {type(user_response)}")
        logger.info(f" [DEBUG] user_response content: {user_response}")

        # 更新状态
        #  修复: 移除 current_stage 更新，避免与后续节点冲突
        updated_state = {
            "interaction_history": state.get("interaction_history", [])
            + [
                {
                    "type": InteractionType.CONFIRMATION.value,
                    "data": confirmation_data,
                    "response": user_response,
                    "timestamp": "2024-01-01T00:00:00Z",
                }
            ]
        }

        # 根据用户响应决定下一步
        is_approved = False
        feedback = None
        additional_info = None
        modifications = None

        if isinstance(user_response, str):
            #  修复: 兼容 'approve' 和 'confirm' 两种确认值
            is_approved = user_response in ["approve", "confirm"]
        elif isinstance(user_response, dict):
            #  修复: 兼容 "intent" 和 "action" 两种字段名
            intent_or_action = user_response.get("intent") or user_response.get("action", "")
            is_approved = intent_or_action == "approve"
            feedback = user_response.get("feedback")
            additional_info = user_response.get("additional_info", "")
            modifications = user_response.get("modifications", {})  #  改为 {},避免空字符串
        else:
            logger.warning(f"Unexpected user_response type: {type(user_response)}, defaulting to revise")
            is_approved = False

        #  智能修改检测: 检查用户提交的修改是否真的改变了内容
        has_real_modifications = False
        has_additions = additional_info and len(str(additional_info).strip()) > 10

        def normalize_text(text: str) -> str:
            """深度规范化文本,忽略格式差异"""
            import re

            # 转字符串并去除首尾空格
            text = str(text).strip()
            # 统一换行符
            text = text.replace("\r\n", "\n").replace("\r", "\n")
            # 去除多余空格(连续空格变单个)
            text = re.sub(r" +", " ", text)
            # 去除多余换行(连续换行变单个)
            text = re.sub(r"\n+", "\n", text)
            # 统一中英文标点
            text = text.replace("；", ";").replace("：", ":").replace("，", ",")
            text = text.replace(""", "'").replace(""", "'").replace('"', '"').replace('"', '"')
            return text.strip()

        if modifications and isinstance(modifications, dict):
            # 获取当前需求
            current_requirements = state.get("structured_requirements", {})

            # 逐字段比对,检测是否有真实改动
            for field, new_value in modifications.items():
                current_value = current_requirements.get(field, "")

                # 深度规范化比较
                new_normalized = normalize_text(new_value)
                current_normalized = normalize_text(current_value)

                # 计算实际差异长度
                if new_normalized != current_normalized:
                    # 找出真正不同的部分
                    diff_chars = sum(1 for a, b in zip(new_normalized, current_normalized) if a != b)
                    diff_chars += abs(len(new_normalized) - len(current_normalized))

                    # 只有差异超过10个字符才算真实修改
                    if diff_chars > 10:
                        has_real_modifications = True
                        logger.info(f" [DEBUG] 检测到字段 '{field}' 有真实修改 (差异字符数: {diff_chars})")
                        logger.info(f"   原值长度: {len(current_normalized)}, 新值长度: {len(new_normalized)}")
                        logger.info(f"   原值前100字: {current_normalized[:100]}...")
                        logger.info(f"   新值前100字: {new_normalized[:100]}...")
                        break

            if not has_real_modifications:
                logger.info(" 用户提交的 modifications 与当前值相同(或差异<10字符),视为无修改")

        has_modifications = has_real_modifications

        if is_approved:
            if has_modifications or has_additions:
                logger.info("️ User approved BUT provided modifications/additions")
                logger.info(" 用户修改需要重新分析以更新 expert_handoff，但不再返回确认页面")
                logger.info(f" [DEBUG] has_modifications={has_modifications}, has_additions={has_additions}")

                #  关键修改：将用户修改融入 structured_requirements
                if has_modifications:
                    # 先复制当前的结构化需求
                    current_requirements = state.get("structured_requirements", {})
                    updated_requirements = dict(current_requirements)  # 创建副本

                    # 将修改内容更新到结构化需求中
                    for field_key, new_value in modifications.items():
                        if field_key in updated_requirements:
                            logger.info(f" 融入用户修改: {field_key}")
                            updated_requirements[field_key] = new_value

                    updated_state["structured_requirements"] = updated_requirements

                #  能力边界检查：检查用户修改是否引入超范围需求
                modification_text = ""
                if has_modifications:
                    mod_text = "\n".join([f"{k}: {v}" for k, v in modifications.items()])
                    modification_text += mod_text
                if has_additions:
                    modification_text += f"\n{additional_info}"

                if modification_text:
                    logger.info(" [CapabilityBoundary] 检查用户修改的能力边界")
                    boundary_check = CapabilityBoundaryService.check_user_input(
                        user_input=modification_text,
                        context={
                            "node": "requirements_confirmation",
                            "original_requirements": state.get("structured_requirements"),
                            "modification_type": "user_supplement",
                        },
                        check_type=CheckType.DELIVERABLE_ONLY,
                    )

                    # 记录检查结果
                    if not boundary_check.within_capability:
                        alert = CapabilityBoundaryService.generate_boundary_alert(boundary_check)
                        updated_state["boundary_alert"] = alert
                        logger.warning(f"️ 用户修改包含超出能力的需求: {alert['message']}")
                        logger.info(f"   转化建议: {alert['transformations']}")
                    else:
                        logger.info(" 用户修改在能力范围内")

                    # 保存检查记录
                    updated_state["boundary_check_record"] = boundary_check

                #  将修改追加到 user_input，让需求分析师知道用户补充了什么
                original_input = state.get("user_input", "")
                supplement_text = ""

                if has_modifications:
                    # 将修改内容格式化为文本
                    mod_text = "\n".join([f"- {k}: {v}" for k, v in modifications.items()])
                    supplement_text += f"\n\n【用户修改补充】\n{mod_text}"

                if has_additions:
                    supplement_text += f"\n\n【用户补充信息】\n{additional_info}"

                updated_state["user_input"] = original_input + supplement_text
                updated_state["requirements_confirmed"] = False  # 标记为未确认，需要重新分析
                updated_state["has_user_modifications"] = True
                updated_state["user_modification_processed"] = True  #  新增标志：用户修改已处理，跳过二次确认
                #  保存用户修改摘要（用于前端展示）
                updated_state["user_modification_summary"] = supplement_text
                #  强制触发角色任务审核 - 即使用户修改了需求也需要审核
                logger.info(" 返回 requirements_analyst 重新分析以更新 expert_handoff")
                logger.info(" 用户修改后将重新分析，并继续到任务审批")

                return Command(update=updated_state, goto="requirements_analyst")
            else:
                logger.info(" Requirements confirmed without modifications")

            updated_state["requirements_confirmed"] = True
            #  强制触发角色任务审核 - 不再自动跳过
            #  重置修改确认轮次
            updated_state["modification_confirmation_round"] = 0
            logger.info(f" [DEBUG] Routing to project_director with updated_state keys: {list(updated_state.keys())}")
            logger.info(" 需求已确认，将继续到项目拆分和任务审批")
            return Command(update=updated_state, goto="project_director")
        else:
            logger.info("️ Requirements need revision")
            updated_state["requirements_confirmed"] = False
            logger.info(
                f" [DEBUG] Routing back to requirements_analyst with updated_state keys: {list(updated_state.keys())}"
            )

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
