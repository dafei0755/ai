"""Boundary checks for demand reconstruction output."""

from __future__ import annotations

from typing import Any, Dict


class DemandReconstructionBoundaryGuard:
    """Keep demand reconstruction as an action blueprint, not a complete brief or report."""

    def routing_for(self, context: Dict[str, Any]) -> Dict[str, str]:
        archetype = (context.get("archetype") or {}).get("primary")
        requested_target = (context.get("archetype") or {}).get("routing_target") or "demand_reconstruction"
        if archetype == "cultural_research" or requested_target == "deep_research":
            return {
                "target": "deep_research",
                "label": "建议进入深度研究",
                "reason": "问题涉及文化、历史或行为证据，需求重构只能定义研究路径，不能伪装成已完成论证。",
            }
        return {
            "target": "demand_reconstruction_or_brief",
            "label": "继续需求重构或整理成设计任务书",
            "reason": "当前适合先看见命门与路径；若要完整处置，应进入正式任务书。",
        }

    @staticmethod
    def clamp_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize shape and cap oversized lists so the output remains a plan."""
        normalized = dict(plan)
        normalized["key_forks"] = [str(item) for item in normalized.get("key_forks") or []][:4]
        normalized["unknowns"] = [str(item) for item in normalized.get("unknowns") or []][:5]
        sections = []
        for section in normalized.get("sections") or []:
            next_section = dict(section)
            next_section["items"] = [str(item) for item in next_section.get("items") or []][:5]
            sections.append(next_section)
        normalized["sections"] = sections[:6]
        return normalized
