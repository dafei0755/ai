"""Insight quality gate for demand reconstruction."""

from __future__ import annotations

from typing import Any, Dict

from intelligent_project_analyzer.services.demand_reconstruction_insight_quality import (
    DemandReconstructionInsightQualityEvaluator,
)


class DemandReconstructionInsightQualityGate:
    """Evaluate insight quality and attach non-visible governance signals."""

    def __init__(
        self,
        *,
        evaluator: DemandReconstructionInsightQualityEvaluator | None = None,
    ) -> None:
        self._evaluator = evaluator or DemandReconstructionInsightQualityEvaluator()

    def apply(
        self,
        *,
        source_message: str,
        adapter_context: Dict[str, Any],
        blueprint: Dict[str, Any],
        visible_reply: str,
    ) -> Dict[str, Any]:
        insight_quality = self._evaluator.evaluate(
            source_message=source_message,
            semantic_package=adapter_context.get("llm_semantic_understanding") or {},
            latent_model=adapter_context.get("latent_model") or {},
            blueprint=blueprint,
            visible_reply=visible_reply,
        )
        blueprint["insight_quality"] = insight_quality
        blueprint["governance_signals"] = self.append_insight_quality_signal(
            blueprint.get("governance_signals") or [],
            insight_quality,
        )
        return insight_quality

    @staticmethod
    def append_insight_quality_signal(
        signals: Any,
        insight_quality: Dict[str, Any],
    ) -> list[Dict[str, Any]]:
        result = [signal for signal in (signals or []) if isinstance(signal, dict)]
        result.append(
            {
                "type": "insight_quality_watch",
                "code": "insight_quality_watch",
                "severity": "P3",
                "review_queue": "demand_reconstruction_quality",
                "level": insight_quality.get("level"),
                "score": insight_quality.get("score"),
                "missing_high_value_signals": insight_quality.get("missing_high_value_signals") or [],
                "warning_count": len(insight_quality.get("warning_issues") or []),
                "user_visible": False,
            }
        )
        return result
