"""Blueprint coordination for LLM-first demand reconstruction.

This module owns the decision around rule blueprint preparation, LLM synthesis,
and the explicit required-LLM failure contract. It does not build semantic
understanding and does not render user-facing output.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from intelligent_project_analyzer.modules.demand_reconstruction.contracts import (
    SYNTHESIS_UNAVAILABLE,
    UNDERSTANDING_UNAVAILABLE,
)


UnavailableFactory = Callable[..., Exception]


class DemandReconstructionBlueprintCoordinator:
    """Coordinate rule plan and LLM synthesis under the LLM-first contract."""

    def __init__(
        self,
        *,
        llm: Any,
        output_planner: Any,
        synthesis: Any,
        require_llm: bool,
        unavailable_factory: UnavailableFactory,
    ) -> None:
        self._llm = llm
        self._output_planner = output_planner
        self._synthesis = synthesis
        self._require_llm = require_llm
        self._unavailable_factory = unavailable_factory

    def build_blueprint(self, adapter_context: Dict[str, Any]) -> Dict[str, Any]:
        semantic_plan = self._output_planner.build_plan(adapter_context)
        if self._llm is None:
            if self._require_llm:
                raise self._unavailable_factory(
                    error_code=UNDERSTANDING_UNAVAILABLE,
                    diagnostics={"status": "not_configured"},
                )
            return {
                **semantic_plan,
                "insight_source": "semantic_fallback",
                "llm_status": "not_configured",
            }

        llm_plan, llm_diagnostics = self._synthesis.build_blueprint(
            adapter_context,
            semantic_plan,
        )
        if llm_plan is None:
            if self._require_llm:
                raise self._unavailable_factory(
                    error_code=SYNTHESIS_UNAVAILABLE,
                    diagnostics=llm_diagnostics,
                )
            return self._fallback_plan(semantic_plan, llm_diagnostics)
        return llm_plan

    @staticmethod
    def _fallback_plan(
        semantic_plan: Dict[str, Any],
        llm_diagnostics: Dict[str, Any],
    ) -> Dict[str, Any]:
        fallback_plan = {
            **semantic_plan,
            "insight_source": "semantic_fallback",
            "llm_status": llm_diagnostics.get("status", "fallback"),
        }
        if llm_diagnostics.get("reason"):
            fallback_plan["llm_rejection_reason"] = llm_diagnostics["reason"]
        if llm_diagnostics.get("error"):
            fallback_plan["llm_error"] = llm_diagnostics["error"]
        if llm_diagnostics.get("error_type"):
            fallback_plan["llm_error_type"] = llm_diagnostics["error_type"]
        return fallback_plan
