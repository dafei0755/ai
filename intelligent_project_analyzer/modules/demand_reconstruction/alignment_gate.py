"""Semantic alignment gate for demand reconstruction output."""

from __future__ import annotations

import os
from typing import Any, Callable, Dict

from loguru import logger

from intelligent_project_analyzer.services.scheme_advisor_semantic_axes import (
    evaluate_semantic_alignment,
)


class DemandReconstructionAlignmentGate:
    """Evaluate semantic drift and reject unsafe LLM-fused blueprints."""

    def __init__(
        self,
        *,
        output_planner: Any,
        render_reply: Callable[[Dict[str, Any]], str],
        build_card: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> None:
        self._output_planner = output_planner
        self._render_reply = render_reply
        self._build_card = build_card

    @staticmethod
    def hard_gate_enabled() -> bool:
        """Whether the semantic-alignment gate may reject output."""
        flag = os.getenv("DEMAND_RECONSTRUCTION_ALIGNMENT_GATE", "1")
        return str(flag).strip().lower() not in {"0", "false", "off", "no"}

    def maybe_reject_to_semantic_fallback(
        self,
        *,
        blueprint: Dict[str, Any],
        reply: str,
        card: Dict[str, Any],
        alignment_shadow: Dict[str, Any],
        adapter_context: Dict[str, Any],
        source_message: str,
    ) -> tuple[Dict[str, Any], str, Dict[str, Any], Dict[str, Any]]:
        if (
            not self.hard_gate_enabled()
            or alignment_shadow.get("blocking_count", 0) <= 0
            or blueprint.get("insight_source") == "semantic_fallback"
        ):
            return blueprint, reply, card, alignment_shadow
        return self.reject_to_semantic_fallback(
            adapter_context=adapter_context,
            source_message=source_message,
            rejected_alignment=alignment_shadow,
        )

    def reject_to_semantic_fallback(
        self,
        *,
        adapter_context: Dict[str, Any],
        source_message: str,
        rejected_alignment: Dict[str, Any],
    ) -> tuple[Dict[str, Any], str, Dict[str, Any], Dict[str, Any]]:
        """Replace a blocking LLM blueprint with the registry-driven semantic pack."""
        blocking_codes = [
            item.get("code")
            for item in (rejected_alignment.get("issues") or [])
            if item.get("severity") == "blocking"
        ]
        logger.warning(
            "[DemandReconstruction] alignment hard gate rejected LLM blueprint; "
            "falling back to semantic pack: "
            f"blocking={rejected_alignment.get('blocking_count', 0)}, codes={blocking_codes}"
        )
        semantic_plan = self._output_planner.build_plan(adapter_context)
        blueprint = {
            **semantic_plan,
            "insight_source": "semantic_fallback",
            "llm_status": "alignment_gate_rejected",
            "alignment_gate": {
                "action": "llm_rejected",
                "blocking_count": rejected_alignment.get("blocking_count", 0),
                "codes": blocking_codes,
            },
        }
        blueprint["governance_signals"] = self.append_alignment_rejection_signal(
            semantic_plan.get("governance_signals") or [],
            blocking_codes,
        )
        reply = self._render_reply(blueprint)
        card = self._build_card(blueprint)
        alignment_shadow = self.evaluate_alignment_shadow(
            source_message=source_message,
            visible_text=reply,
            adapter_context=adapter_context,
            card=card,
        )
        return blueprint, reply, card, alignment_shadow

    @staticmethod
    def append_alignment_rejection_signal(
        existing_signals: Any,
        blocking_codes: list[Any],
    ) -> list[Dict[str, Any]]:
        signals = [dict(signal) for signal in (existing_signals or []) if isinstance(signal, dict)]
        if any(signal.get("code") == "semantic_alignment_rejection" for signal in signals):
            return signals
        source_codes = [str(code) for code in blocking_codes if str(code)]
        signals.append(
            {
                "code": "semantic_alignment_rejection",
                "track": "semantic_alignment",
                "review_queue": "wrong_domain_output_review",
                "severity": "P0",
                "meaning": "LLM 融合结果被语义一致性硬门拒绝，需要复查错域、模板泄漏或内部步骤名外露。",
                "source_codes": source_codes,
                "user_visible": False,
            }
        )
        return signals

    @staticmethod
    def evaluate_alignment_shadow(
        *,
        source_message: str,
        visible_text: str,
        adapter_context: Dict[str, Any],
        card: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Evaluate semantic alignment without directly breaking rendering."""
        try:
            card_pages = [
                str(section.get("body") or "")
                for section in (card.get("sections") or [])
            ]
            issues = evaluate_semantic_alignment(
                source_message,
                visible_text,
                project_type=adapter_context.get("project_type"),
                card_pages=card_pages,
            )
        except Exception as exc:  # never let the shadow gate break rendering
            logger.warning(
                "[DemandReconstruction] semantic alignment shadow eval failed: "
                f"error_type={type(exc).__name__}, error={exc}"
            )
            return {"mode": "shadow", "status": "eval_failed", "error": str(exc)}

        blocking = [item for item in issues if item.get("severity") == "blocking"]
        warning = [item for item in issues if item.get("severity") == "warning"]
        result = {
            "mode": "shadow",
            "status": "evaluated",
            "issue_count": len(issues),
            "blocking_count": len(blocking),
            "warning_count": len(warning),
            "issues": issues,
        }
        if issues:
            logger.warning(
                "[DemandReconstruction] semantic alignment evaluation flagged issues: "
                f"blocking={len(blocking)}, warning={len(warning)}, "
                f"codes={[item.get('code') for item in issues]}"
            )
        else:
            logger.info("[DemandReconstruction] semantic alignment shadow: clean")
        return result
