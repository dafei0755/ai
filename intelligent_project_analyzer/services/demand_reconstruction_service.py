"""Demand reconstruction orchestration for Scheme Advisor.

This layer is the purchase-before-proof shape for Design Brief 2.0:
it returns an action blueprint that reconstructs vague demand, not a formal
intake questionnaire.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from .demand_reconstruction_context_adapter import DemandReconstructionContextAdapter
from .demand_reconstruction_output_planner import DemandReconstructionOutputPlanner


class DemandReconstructionService:
    """Generate a non-freezing demand reconstruction for early ambiguous inputs."""

    CARD_TYPE = "demand_reconstruction_blueprint"
    INTENT = "demand_reconstruction_blueprint"

    _FORMAL_TERMS = (
        "设计任务书",
        "任务书",
        "完整设计",
        "完整室内设计",
        "完整室内设计概念框架",
        "完整概念框架",
        "完整框架",
        "可执行版本",
        "按这个做",
        "定稿",
        "输出方案",
    )
    _ADVICE_TERMS = ("给出建议", "给点建议", "怎么建议", "帮我想想", "怎么看", "如何", "怎么")
    _SPACE_TERMS = (
        "民居",
        "住宅",
        "老家",
        "乡村",
        "自宅",
        "茶饮",
        "茶空间",
        "咖啡",
        "店",
        "办公室",
        "展厅",
        "民宿",
        "酒店",
        "社区",
        "改造",
        "会所",
        "空间",
        "冷藏柜",
    )

    def __init__(
        self,
        *,
        context_adapter: Optional[DemandReconstructionContextAdapter] = None,
        output_planner: Optional[DemandReconstructionOutputPlanner] = None,
    ) -> None:
        self._context_adapter = context_adapter or DemandReconstructionContextAdapter()
        self._output_planner = output_planner or DemandReconstructionOutputPlanner()

    def handle_message(
        self,
        *,
        session: Dict[str, Any],
        user_message: str,
        in_response_to_card_id: Optional[str],
        selected_option_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        pending_card = session.get("pending_guidance_card") or {}
        if pending_card.get("card_type") == self.CARD_TYPE:
            context = dict(session.get("demand_reconstruction_context") or {})
            if selected_option_id == "handoff_to_brief":
                context["handoff_requested"] = True
                return {
                    "handoff_requested": True,
                    "demand_reconstruction_context": context,
                }
            if selected_option_id == "continue_demand_reconstruction" or self._is_demand_reconstruction_followup(user_message):
                return self._result(user_message, previous_context=context)
            return None

        if not self.should_handle(user_message):
            return None
        return self._result(user_message)

    def should_handle(self, message: str) -> bool:
        text = str(message or "").strip()
        if not text:
            return False
        if self.is_formal_brief_request(text):
            return False
        has_advice_intent = any(term in text for term in self._ADVICE_TERMS)
        has_space_hint = any(term in text for term in self._SPACE_TERMS)
        has_research_hint = any(term in text for term in ("研究", "源流", "历史", "文人", "雅集", "文化", "转译"))
        return has_advice_intent and (has_space_hint or has_research_hint)

    def is_formal_brief_request(self, message: str) -> bool:
        text = str(message or "")
        if any(term in text for term in self._FORMAL_TERMS):
            return True
        has_complete = "完整" in text
        has_framework = any(term in text for term in ("框架", "概念", "方案"))
        has_multi_topic = sum(1 for term in ("光", "材料", "动线", "自然", "空间", "界面", "精神性") if term in text) >= 3
        return has_complete and has_framework and has_multi_topic

    def _result(self, message: str, previous_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        adapter_context = self._context_adapter.build(message)
        if previous_context and previous_context.get("blueprint", {}).get("task_reframe"):
            adapter_context["previous_blueprint"] = previous_context["blueprint"]
        blueprint = self._build_blueprint(adapter_context)
        context = {
            "schema_version": "demand_reconstruction_context.v1",
            "reconstruction_type": "demand_reconstruction",
            "artifact_name": "action_blueprint",
            "display_title": "需求重构",
            "display_artifact_name": "行动蓝图",
            "created_at": datetime.now().isoformat(),
            "source_message": message,
            "adapter_context": self._public_adapter_context(adapter_context),
            "blueprint": blueprint,
            "brief_handoff_slots": blueprint["brief_handoff_slots"],
        }
        reply = self._render_reply(blueprint)
        return {
            "reply": reply,
            "intent": self.INTENT,
            "dialogue_layer": "demand_reconstruction",
            "handoff_available": True,
            "guidance_card": self._card(blueprint),
            "demand_reconstruction_context": context,
            "drafts": [],
            "upgrade_signal": None,
            "upgrade_suggested": False,
        }

    @staticmethod
    def _is_demand_reconstruction_followup(message: str) -> bool:
        return bool(str(message or "").strip())

    def _build_blueprint(self, adapter_context: Dict[str, Any]) -> Dict[str, Any]:
        return self._output_planner.build_plan(adapter_context)

    @staticmethod
    def _render_reply(plan: Dict[str, Any]) -> str:
        forks = "\n".join(f"- {item}" for item in plan["key_forks"][:3])
        unknowns = "\n".join(f"- {item}" for item in plan["unknowns"][:4])
        section_blocks = []
        for section in plan.get("sections") or []:
            items = "\n".join(f"- {item}" for item in section.get("items") or [])
            section_blocks.append(
                f"**{section.get('title')}**\n{section.get('body')}\n{items}".strip()
            )
        dynamic_sections = "\n\n".join(section_blocks)
        next_question = (plan.get("next_question") or (plan.get("key_forks") or [""])[0]).strip("？?")
        return (
            "## 需求重构\n\n"
            f"{plan['task_reframe']}\n\n"
            f"我先不急着给方案。这里真正要先判断的是：{plan['project_viability_judgment']}\n\n"
            f"**关键判断**\n{plan['primary_risk']}\n\n"
            f"{dynamic_sections}\n\n"
            f"**会改变后续判断的分叉**\n{forks}\n\n"
            f"**现在不能直接下结论的原因**\n{unknowns}\n\n"
            f"**我建议先追问一个关键点**\n{next_question}？\n\n"
            f"**下一步**\n{plan['routing_recommendation']}"
        )

    @staticmethod
    def _card(plan: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "card_id": f"demand_reconstruction-{uuid.uuid4().hex[:8]}",
            "card_type": DemandReconstructionService.CARD_TYPE,
            "title": "需求重构",
            "display_label": "需求重构",
            "artifact_name": "行动蓝图",
            "reconstruction_type": "demand_reconstruction",
            "prompt_text": plan["task_reframe"],
            "options": [
                {
                    "id": "continue_demand_reconstruction",
                    "label": "继续需求重构",
                    "description": "继续把这个问题想清楚，不进入正式任务书。",
                },
                {
                    "id": "handoff_to_brief",
                    "label": "整理成设计任务书草稿",
                    "description": "把当前行动蓝图带入正式任务书问诊。",
                    "recommended": True,
                },
            ],
            "allow_freetext": True,
            "summary": plan,
            "sections": plan.get("sections") or [],
        }

    @staticmethod
    def _public_adapter_context(adapter_context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "project_type": adapter_context.get("project_type"),
            "project_type_name": adapter_context.get("project_type_name"),
            "space_label": adapter_context.get("space_label"),
            "semantic_axes": adapter_context.get("semantic_axes"),
            "main_tensions": adapter_context.get("main_tensions"),
            "archetype": adapter_context.get("archetype"),
            "context_source": adapter_context.get("context_source"),
        }
