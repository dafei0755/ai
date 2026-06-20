"""Runtime pipeline for demand reconstruction.

This module owns the end-to-end reconstruction flow after entry classification:
semantic understanding, adapter context preparation, governed knowledge
injection, latent model attachment, blueprint coordination, alignment gating,
insight quality gating, governance persistence, and public response assembly.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from intelligent_project_analyzer.modules.demand_reconstruction.contracts import (
    UNDERSTANDING_UNAVAILABLE,
)


class DemandReconstructionPipeline:
    """Run the demand reconstruction pipeline from user message to response."""

    def __init__(
        self,
        *,
        llm: Any,
        require_llm: bool,
        unavailable_factory: Any,
        context_adapter: Any,
        semantic_router: Any,
        semantic_context_applier: Any,
        governance: Any,
        latent_model_adapter: Any,
        blueprint_coordinator: Any,
        response_builder: Any,
        alignment_gate: Any,
        insight_quality_gate: Any,
    ) -> None:
        self._llm = llm
        self._require_llm = require_llm
        self._unavailable_factory = unavailable_factory
        self._context_adapter = context_adapter
        self._semantic_router = semantic_router
        self._semantic_context_applier = semantic_context_applier
        self._governance = governance
        self._latent_model_adapter = latent_model_adapter
        self._blueprint_coordinator = blueprint_coordinator
        self._response_builder = response_builder
        self._alignment_gate = alignment_gate
        self._insight_quality_gate = insight_quality_gate

    def run(
        self,
        message: str,
        *,
        previous_context: Optional[Dict[str, Any]] = None,
        session: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        llm_semantic_understanding = (
            self._build_llm_semantic_understanding(message)
            if self._require_llm
            else None
        )
        adapter_context = self._context_adapter.build(message)
        if llm_semantic_understanding:
            self._semantic_context_applier.apply(
                adapter_context,
                llm_semantic_understanding,
            )

        self._governance.apply_governed_knowledge_assets(
            adapter_context=adapter_context,
            session=session or {},
            source_message=message,
            refresh_asset_scan=self._semantic_context_applier.refresh_asset_scan,
        )

        latent_model = self._latent_model_adapter.build(
            source_message=message,
            adapter_context=adapter_context,
        )
        adapter_context["latent_model"] = latent_model.model_dump(mode="json")
        if previous_context and previous_context.get("blueprint", {}).get("task_reframe"):
            adapter_context["previous_blueprint"] = previous_context["blueprint"]

        blueprint = self._blueprint_coordinator.build_blueprint(adapter_context)
        reply = self._response_builder.render_reply(blueprint)
        card = self._response_builder.build_card(blueprint)
        alignment_shadow = self._alignment_gate.evaluate_alignment_shadow(
            source_message=message,
            visible_text=reply,
            adapter_context=adapter_context,
            card=card,
        )
        blueprint, reply, card, alignment_shadow = (
            self._alignment_gate.maybe_reject_to_semantic_fallback(
                blueprint=blueprint,
                reply=reply,
                card=card,
                alignment_shadow=alignment_shadow,
                adapter_context=adapter_context,
                source_message=message,
            )
        )
        self._insight_quality_gate.apply(
            source_message=message,
            adapter_context=adapter_context,
            blueprint=blueprint,
            visible_reply=reply,
        )
        blueprint["semantic_alignment_shadow"] = alignment_shadow

        governance_persistence = self._governance.persist_governance_signals(
            session=session or {},
            source_message=message,
            blueprint=blueprint,
        )
        if governance_persistence:
            blueprint["governance_persistence"] = governance_persistence

        return self._response_builder.build_result(
            reply=reply,
            card=card,
            source_message=message,
            adapter_context=adapter_context,
            blueprint=blueprint,
            alignment_shadow=alignment_shadow,
        )

    def _build_llm_semantic_understanding(self, message: str) -> Dict[str, Any]:
        if self._llm is None:
            raise self._unavailable_factory(
                error_code=UNDERSTANDING_UNAVAILABLE,
                diagnostics={"status": "not_configured"},
            )
        package, diagnostics = self._semantic_router.build_understanding(message)
        if package is None:
            raise self._unavailable_factory(
                error_code=UNDERSTANDING_UNAVAILABLE,
                diagnostics=diagnostics,
            )
        return package
