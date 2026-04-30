"""
人物审批节点（Persona Approval Node）

在需求洞察确认后、项目总监规划前增加独立审批关卡：
- 审批通过：进入 project_director
- 修改/驳回：回到 requirements_analyst
"""

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from langgraph.store.base import BaseStore
from langgraph.types import Command, interrupt
from loguru import logger

from ...core.state import ProjectAnalysisState


class PersonaApprovalNode:
    """人物审批节点"""

    @staticmethod
    def execute(
        state: ProjectAnalysisState, store: Optional[BaseStore] = None
    ) -> Command[Literal["project_director", "requirements_analyst"]]:
        logger.info("=" * 80)
        logger.info(" [Persona Approval] 人物审批节点")
        logger.info("=" * 80)

        restructured = state.get("restructured_requirements") or {}
        profile = {
            "project_essence": restructured.get("project_essence", ""),
            "primary_goal": restructured.get("project_objectives", {}).get("primary_goal", ""),
            "implicit_requirements": restructured.get("implicit_requirements", []),
            "key_conflicts": restructured.get("key_conflicts", []),
            "target_users": restructured.get("target_users", []),
        }

        payload = {
            "interaction_type": "persona_approval",
            "title": "人物审批",
            "message": "请确认目标人物画像与叙事定位，再进入专家规划。",
            "persona_profile": profile,
            "options": {
                "approve": "确认人物画像",
                "edit": "需要调整人物画像",
                "reject": "驳回并重新分析",
            },
        }

        user_response = interrupt(payload)
        logger.info(f" [Persona Approval] 收到用户响应: {type(user_response)}")

        action = "approve"
        note = ""
        if isinstance(user_response, str):
            action = user_response.strip().lower() or "approve"
        elif isinstance(user_response, dict):
            action = (user_response.get("action") or user_response.get("intent") or "approve").strip().lower()
            note = str(user_response.get("note") or user_response.get("comment") or "")

        change_log = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "note": note,
        }

        if action in {"approve", "confirm"}:
            logger.info(" [Persona Approval] 审批通过，进入 project_director")
            return Command(
                update={
                    "persona_approval_status": "approved",
                    "confirmed_persona_profile": profile,
                    "persona_change_log": [change_log],
                    "detail": "人物审批通过，进入专家规划",
                },
                goto="project_director",
            )

        logger.info(" [Persona Approval] 审批未通过，回到 requirements_analyst")
        original_input = state.get("user_input", "")
        revised_input = original_input
        if note:
            revised_input = f"{original_input}\n\n【人物审批反馈】\n{note}"

        return Command(
            update={
                "persona_approval_status": "rejected",
                "persona_change_log": [change_log],
                "requirements_confirmed": False,
                "user_input": revised_input,
                "detail": "人物审批未通过，返回需求分析",
            },
            goto="requirements_analyst",
        )


def persona_approval_node(state: ProjectAnalysisState, store: Optional[BaseStore] = None) -> Command:
    """导出节点函数（用于 workflow 注册）"""
    return PersonaApprovalNode.execute(state, store)
