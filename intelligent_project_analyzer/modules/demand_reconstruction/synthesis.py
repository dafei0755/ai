"""LLM final synthesis for demand reconstruction.

This module owns Stage 5 synthesis only: invoking the LLM with the insight
protocol prompt, handling provider fallback, repair attempts, and clamping the
accepted blueprint. It does not decide whether synthesis is required and does
not render user-facing output.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from loguru import logger


class DemandReconstructionSynthesis:
    """Build a fused demand reconstruction blueprint from rule context and LLM output."""

    def __init__(self, *, llm: Any, insight_protocol: Any, output_planner: Any) -> None:
        self._llm = llm
        self._insight_protocol = insight_protocol
        self._output_planner = output_planner

    def build_blueprint(
        self,
        adapter_context: Dict[str, Any],
        rule_plan: Dict[str, Any],
    ) -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        prompt = self._insight_protocol.build_prompt(adapter_context, rule_plan)
        fallback_instances = getattr(self._llm, "llm_instances", None)
        if isinstance(fallback_instances, dict) and fallback_instances:
            best_partial: Optional[tuple[Dict[str, Any], Dict[str, Any]]] = None
            last_diagnostics: Dict[str, Any] = {"status": "fallback_exhausted"}
            for provider, llm in fallback_instances.items():
                merged, diagnostics = self.build_blueprint_with_llm(
                    llm=llm,
                    prompt=prompt,
                    rule_plan=rule_plan,
                    provider=str(provider),
                )
                last_diagnostics = diagnostics
                if merged is not None and diagnostics.get("status") == "used":
                    return merged, diagnostics
                if merged is not None and diagnostics.get("status") == "partial" and best_partial is None:
                    best_partial = (merged, diagnostics)
                    logger.info(
                        "[DemandReconstruction] partial LLM insight kept as backup; "
                        f"provider={provider}"
                    )
                    continue
                logger.info(
                    "[DemandReconstruction] trying next LLM provider after non-final insight: "
                    f"provider={provider}, status={diagnostics.get('status')}"
                )
            if best_partial is not None:
                return best_partial
            return None, last_diagnostics

        return self.build_blueprint_with_llm(
            llm=self._llm,
            prompt=prompt,
            rule_plan=rule_plan,
            provider="default",
        )

    def build_blueprint_with_llm(
        self,
        *,
        llm: Any,
        prompt: str,
        rule_plan: Dict[str, Any],
        provider: str,
    ) -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        started_at = time.perf_counter()
        try:
            response = llm.invoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            logger.info(
                "[DemandReconstruction] LLM insight response received: "
                f"provider={provider}, prompt_chars={len(prompt)}, "
                f"content_chars={len(str(content or ''))}, elapsed_ms={elapsed_ms}"
            )
            merged, diagnostics = self._insight_protocol.build_blueprint_from_response_detailed(
                rule_plan=rule_plan,
                content=str(content or ""),
            )
            if merged is None and diagnostics.get("status") in {"quality_rejected", "invalid_json", "empty_response"}:
                repair_prompt = self._insight_protocol.build_repair_prompt(
                    original_prompt=prompt,
                    rejected_content=str(content or ""),
                    rejection_reason=str(diagnostics.get("reason") or diagnostics.get("status") or "quality_rejected"),
                )
                repair_response = llm.invoke(repair_prompt)
                repair_content = repair_response.content if hasattr(repair_response, "content") else str(repair_response)
                repaired, repair_diagnostics = self._insight_protocol.build_blueprint_from_response_detailed(
                    rule_plan=rule_plan,
                    content=str(repair_content or ""),
                )
                if repaired is not None:
                    return self._output_planner.clamp_existing_plan(repaired), repair_diagnostics
                return None, repair_diagnostics
            if merged is None:
                return None, diagnostics
            return self._output_planner.clamp_existing_plan(merged), diagnostics
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started_at) * 1000)
            logger.warning(
                "[DemandReconstruction] LLM insight failed, fallback used: "
                f"provider={provider}, prompt_chars={len(prompt)}, elapsed_ms={elapsed_ms}, "
                f"error_type={type(exc).__name__}, error={exc}"
            )
            return None, {"status": "invoke_failed", "error": str(exc), "error_type": type(exc).__name__}