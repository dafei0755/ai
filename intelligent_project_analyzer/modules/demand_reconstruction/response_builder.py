"""Response construction for demand reconstruction."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict

from .contracts import (
    DEMAND_RECONSTRUCTION_CARD_TYPE,
    DEMAND_RECONSTRUCTION_INTENT,
)


class DemandReconstructionResponseBuilder:
    """Build user-visible replies, guidance cards, and public context payloads."""

    def render_reply(self, plan: Dict[str, Any]) -> str:
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

    def build_card(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "card_id": f"demand_reconstruction-{uuid.uuid4().hex[:8]}",
            "card_type": DEMAND_RECONSTRUCTION_CARD_TYPE,
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
            "summary": self.public_card_summary(plan),
            "sections": plan.get("sections") or [],
        }

    def build_result(
        self,
        *,
        reply: str,
        card: Dict[str, Any],
        source_message: str,
        adapter_context: Dict[str, Any],
        blueprint: Dict[str, Any],
        alignment_shadow: Dict[str, Any],
    ) -> Dict[str, Any]:
        context = {
            "schema_version": "demand_reconstruction_context.v1",
            "reconstruction_type": "demand_reconstruction",
            "artifact_name": "action_blueprint",
            "display_title": "需求重构",
            "display_artifact_name": "行动蓝图",
            "created_at": datetime.now().isoformat(),
            "source_message": source_message,
            "adapter_context": self.public_adapter_context(adapter_context),
            "blueprint": blueprint,
            "brief_handoff_slots": blueprint["brief_handoff_slots"],
            "semantic_alignment_shadow": alignment_shadow,
        }
        return {
            "reply": reply,
            "intent": DEMAND_RECONSTRUCTION_INTENT,
            "dialogue_layer": "demand_reconstruction",
            "handoff_available": True,
            "guidance_card": card,
            "demand_reconstruction_context": context,
            "drafts": [],
            "upgrade_signal": None,
            "upgrade_suggested": False,
        }

    @staticmethod
    def public_card_summary(plan: Dict[str, Any]) -> Dict[str, Any]:
        hidden_keys = {
            "governance_signals",
            "governance_persistence",
            "semantic_alignment_shadow",
            "alignment_gate",
            "llm_semantic_scan",
            "insight_quality",
        }
        return {key: value for key, value in plan.items() if key not in hidden_keys}

    @staticmethod
    def public_adapter_context(adapter_context: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "project_type": adapter_context.get("project_type"),
            "project_type_name": adapter_context.get("project_type_name"),
            "space_label": adapter_context.get("space_label"),
            "semantic_axes": adapter_context.get("semantic_axes"),
            "main_tensions": adapter_context.get("main_tensions"),
            "missing_slots": adapter_context.get("missing_slots"),
            "knowledge_coverage_ceiling": adapter_context.get("knowledge_coverage_ceiling"),
            "semantic_candidate_set": adapter_context.get("semantic_candidate_set"),
            "archetype": adapter_context.get("archetype"),
            "llm_semantic_understanding": adapter_context.get("llm_semantic_understanding"),
            "llm_semantic_scan": adapter_context.get("llm_semantic_scan"),
            "latent_model": adapter_context.get("latent_model"),
            "governed_knowledge_assets": adapter_context.get("governed_knowledge_assets"),
            "context_source": adapter_context.get("context_source"),
        }
