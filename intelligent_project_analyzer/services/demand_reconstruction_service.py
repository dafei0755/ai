"""Demand reconstruction orchestration for Scheme Advisor.

This layer is the purchase-before-proof shape for Design Brief 2.0:
it returns an action blueprint that reconstructs vague demand, not a formal
intake questionnaire.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from intelligent_project_analyzer.modules.demand_reconstruction.alignment_gate import (
    DemandReconstructionAlignmentGate,
)
from intelligent_project_analyzer.modules.demand_reconstruction.insight_quality_gate import (
    DemandReconstructionInsightQualityGate,
)
from intelligent_project_analyzer.modules.demand_reconstruction.response_builder import (
    DemandReconstructionResponseBuilder,
)
from intelligent_project_analyzer.modules.demand_reconstruction.runtime_factory import (
    DemandReconstructionRuntimeFactory,
)
from intelligent_project_analyzer.modules.demand_reconstruction.blueprint_coordinator import (
    DemandReconstructionBlueprintCoordinator,
)
from intelligent_project_analyzer.modules.demand_reconstruction.conversation_handler import (
    DemandReconstructionConversationHandler,
)
from intelligent_project_analyzer.modules.demand_reconstruction.entry_classifier import (
    DemandReconstructionEntryClassifier,
)
from intelligent_project_analyzer.modules.demand_reconstruction.pipeline import (
    DemandReconstructionPipeline,
)
from intelligent_project_analyzer.modules.demand_reconstruction.semantic_context_applier import (
    DemandReconstructionSemanticContextApplier,
)
from intelligent_project_analyzer.modules.demand_reconstruction.synthesis import (
    DemandReconstructionSynthesis,
)
from intelligent_project_analyzer.modules.demand_reconstruction.governance import (
    DemandReconstructionGovernance,
)
from intelligent_project_analyzer.modules.demand_reconstruction.semantic_router import (
    DemandReconstructionSemanticRouter,
)
from intelligent_project_analyzer.modules.demand_reconstruction.semantic_targets import (
    LLM_SEMANTIC_TARGET_ALIASES,
)
from intelligent_project_analyzer.modules.demand_reconstruction.contracts import (
    DEMAND_RECONSTRUCTION_CARD_TYPE,
    DEMAND_RECONSTRUCTION_INTENT,
    DemandReconstructionUnavailable,
    UNDERSTANDING_UNAVAILABLE,
)
from .demand_reconstruction_context_adapter import DemandReconstructionContextAdapter
from .demand_reconstruction_insight_quality import DemandReconstructionInsightQualityEvaluator
from .demand_reconstruction_insight_protocol import DemandReconstructionInsightProtocol
from .demand_reconstruction_output_planner import DemandReconstructionOutputPlanner
from .latent_model_adapter import LatentModelAdapter


class DemandReconstructionService:
    """Generate a non-freezing demand reconstruction for early ambiguous inputs."""

    CARD_TYPE = DEMAND_RECONSTRUCTION_CARD_TYPE
    INTENT = DEMAND_RECONSTRUCTION_INTENT
    _LLM_SEMANTIC_TARGET_ALIASES = LLM_SEMANTIC_TARGET_ALIASES

    def __init__(
        self,
        *,
        llm: Any = None,
        context_adapter: Optional[DemandReconstructionContextAdapter] = None,
        insight_protocol: Optional[DemandReconstructionInsightProtocol] = None,
        output_planner: Optional[DemandReconstructionOutputPlanner] = None,
        latent_model_adapter: Optional[LatentModelAdapter] = None,
        insight_quality_evaluator: Optional[DemandReconstructionInsightQualityEvaluator] = None,
        semantic_router: Optional[DemandReconstructionSemanticRouter] = None,
        synthesis: Optional[DemandReconstructionSynthesis] = None,
        governance: Optional[DemandReconstructionGovernance] = None,
        alignment_gate: Optional[DemandReconstructionAlignmentGate] = None,
        insight_quality_gate: Optional[DemandReconstructionInsightQualityGate] = None,
        response_builder: Optional[DemandReconstructionResponseBuilder] = None,
        semantic_context_applier: Optional[DemandReconstructionSemanticContextApplier] = None,
        blueprint_coordinator: Optional[DemandReconstructionBlueprintCoordinator] = None,
        conversation_handler: Optional[DemandReconstructionConversationHandler] = None,
        entry_classifier: Optional[DemandReconstructionEntryClassifier] = None,
        pipeline: Optional[DemandReconstructionPipeline] = None,
        require_llm: bool = False,
        governance_store: Any = None,
    ) -> None:
        self._llm = llm
        self._require_llm = require_llm
        self._governance_store = governance_store
        runtime = DemandReconstructionRuntimeFactory.build(
            llm=llm,
            require_llm=require_llm,
            governance_store=governance_store,
            card_type=self.CARD_TYPE,
            result_builder=self._result,
            context_adapter=context_adapter,
            insight_protocol=insight_protocol,
            output_planner=output_planner,
            latent_model_adapter=latent_model_adapter,
            insight_quality_evaluator=insight_quality_evaluator,
            semantic_router=semantic_router,
            synthesis=synthesis,
            governance=governance,
            alignment_gate=alignment_gate,
            insight_quality_gate=insight_quality_gate,
            response_builder=response_builder,
            semantic_context_applier=semantic_context_applier,
            blueprint_coordinator=blueprint_coordinator,
            conversation_handler=conversation_handler,
            entry_classifier=entry_classifier,
        )
        self._governance = runtime.governance
        self._entry_classifier = runtime.entry_classifier
        self._context_adapter = runtime.context_adapter
        self._insight_protocol = runtime.insight_protocol
        self._semantic_router = runtime.semantic_router
        self._semantic_context_applier = runtime.semantic_context_applier
        self._output_planner = runtime.output_planner
        self._synthesis = runtime.synthesis
        self._blueprint_coordinator = runtime.blueprint_coordinator
        self._response_builder = runtime.response_builder
        self._alignment_gate = runtime.alignment_gate
        self._latent_model_adapter = runtime.latent_model_adapter
        self._insight_quality_evaluator = runtime.insight_quality_evaluator
        self._insight_quality_gate = runtime.insight_quality_gate
        self._pipeline = runtime.pipeline
        self._conversation_handler = runtime.conversation_handler

    def handle_message(
        self,
        *,
        session: Dict[str, Any],
        user_message: str,
        in_response_to_card_id: Optional[str],
        selected_option_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        return self._conversation_handler.handle_message(
            session=session,
            user_message=user_message,
            in_response_to_card_id=in_response_to_card_id,
            selected_option_id=selected_option_id,
        )

    def should_handle(self, message: str) -> bool:
        return self._entry_classifier.should_handle(message)

    def is_formal_brief_request(self, message: str) -> bool:
        return self._entry_classifier.is_formal_brief_request(message)

    def _result(
        self,
        message: str,
        previous_context: Optional[Dict[str, Any]] = None,
        session: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self._pipeline.run(
            message,
            previous_context=previous_context,
            session=session,
        )

    @staticmethod
    def _alignment_hard_gate_enabled() -> bool:
        return DemandReconstructionAlignmentGate.hard_gate_enabled()

    def _reject_to_semantic_fallback(
        self,
        *,
        adapter_context: Dict[str, Any],
        source_message: str,
        rejected_alignment: Dict[str, Any],
    ) -> tuple[Dict[str, Any], str, Dict[str, Any], Dict[str, Any]]:
        return self._alignment_gate.reject_to_semantic_fallback(
            adapter_context=adapter_context,
            source_message=source_message,
            rejected_alignment=rejected_alignment,
        )

    @staticmethod
    def _append_alignment_rejection_signal(
        existing_signals: Any,
        blocking_codes: list[Any],
    ) -> list[Dict[str, Any]]:
        return DemandReconstructionAlignmentGate.append_alignment_rejection_signal(
            existing_signals,
            blocking_codes,
        )

    def _persist_governance_signals(
        self,
        *,
        session: Dict[str, Any],
        source_message: str,
        blueprint: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        return self._governance.persist_governance_signals(
            session=session,
            source_message=source_message,
            blueprint=blueprint,
        )

    def _apply_governed_knowledge_assets(
        self,
        *,
        adapter_context: Dict[str, Any],
        session: Dict[str, Any],
        source_message: str,
    ) -> None:
        self._governance.apply_governed_knowledge_assets(
            adapter_context=adapter_context,
            session=session,
            source_message=source_message,
            refresh_asset_scan=self._refresh_llm_semantic_asset_scan,
        )

    @staticmethod
    def _governed_knowledge_match_terms(adapter_context: Dict[str, Any], source_message: str) -> list[str]:
        return DemandReconstructionGovernance.governed_knowledge_match_terms(
            adapter_context,
            source_message,
        )

    @staticmethod
    def _approved_card_matches_terms(card: Dict[str, Any], terms: list[str]) -> bool:
        return DemandReconstructionGovernance.approved_card_matches_terms(card, terms)

    @staticmethod
    def _approved_card_match_metadata(card: Dict[str, Any], terms: list[str]) -> Dict[str, Any]:
        return DemandReconstructionGovernance.approved_card_match_metadata(card, terms)

    @staticmethod
    def _compact_governed_knowledge_asset(
        card: Dict[str, Any],
        *,
        match_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return DemandReconstructionGovernance.compact_governed_knowledge_asset(
            card,
            match_metadata=match_metadata,
        )

    @staticmethod
    def _governance_scope(session: Dict[str, Any]) -> Dict[str, str]:
        return DemandReconstructionGovernance.governance_scope(session)

    @staticmethod
    def _is_demand_reconstruction_followup(message: str) -> bool:
        return DemandReconstructionEntryClassifier.is_demand_reconstruction_followup(message)

    def _build_blueprint(self, adapter_context: Dict[str, Any]) -> Dict[str, Any]:
        return self._blueprint_coordinator.build_blueprint(adapter_context)

    def _build_llm_insight_blueprint(
        self,
        adapter_context: Dict[str, Any],
        rule_plan: Dict[str, Any],
    ) -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        return self._synthesis.build_blueprint(adapter_context, rule_plan)

    def _build_llm_insight_blueprint_with_llm(
        self,
        *,
        llm: Any,
        prompt: str,
        rule_plan: Dict[str, Any],
        provider: str,
    ) -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        return self._synthesis.build_blueprint_with_llm(
            llm=llm,
            prompt=prompt,
            rule_plan=rule_plan,
            provider=provider,
        )

    def _build_llm_semantic_understanding(self, message: str) -> Dict[str, Any]:
        if self._llm is None:
            raise DemandReconstructionUnavailable(
                error_code=UNDERSTANDING_UNAVAILABLE,
                diagnostics={"status": "not_configured"},
            )
        package, diagnostics = self._semantic_router.build_understanding(message)
        if package is None:
            raise DemandReconstructionUnavailable(
                error_code=UNDERSTANDING_UNAVAILABLE,
                diagnostics=diagnostics,
            )
        return package

    def _apply_llm_semantic_understanding_to_adapter_context(
        self,
        adapter_context: Dict[str, Any],
        package: Dict[str, Any],
    ) -> None:
        self._semantic_context_applier.apply(adapter_context, package)

    def _refresh_llm_semantic_asset_scan(
        self,
        adapter_context: Dict[str, Any],
        *,
        fragment_targets: Optional[list[Dict[str, Any]]] = None,
    ) -> None:
        DemandReconstructionSemanticContextApplier.refresh_asset_scan(
            adapter_context,
            fragment_targets=fragment_targets,
        )

    def _apply_llm_semantic_governance_context(
        self,
        adapter_context: Dict[str, Any],
        package: Dict[str, Any],
        scan_result: Dict[str, Any],
    ) -> None:
        self._semantic_context_applier.apply_governance_context(
            adapter_context,
            package,
            scan_result,
        )

    @staticmethod
    def _llm_semantic_coverage_ceiling(
        *,
        scan_result: str,
        project_object: str,
        evidence: list[str],
        matched_targets: list[str],
    ) -> Dict[str, Any]:
        return DemandReconstructionSemanticContextApplier.llm_semantic_coverage_ceiling(
            scan_result=scan_result,
            project_object=project_object,
            evidence=evidence,
            matched_targets=matched_targets,
        )

    @staticmethod
    def _llm_semantic_taxonomy_ids(package: Dict[str, Any], *keys: str) -> list[str]:
        return DemandReconstructionSemanticContextApplier.llm_semantic_taxonomy_ids(package, *keys)

    @staticmethod
    def _candidate_fragment_id(project_object: str) -> str:
        return DemandReconstructionSemanticContextApplier.candidate_fragment_id(project_object)

    def _llm_semantic_package_evidence(self, package: Dict[str, Any]) -> list[str]:
        return DemandReconstructionSemanticContextApplier.llm_semantic_package_evidence(package)

    def _llm_semantic_candidates(self, package: Dict[str, Any]) -> list[Dict[str, Any]]:
        return self._semantic_context_applier.llm_semantic_candidates(package)

    def _llm_semantic_fragment_targets(self, package: Dict[str, Any]) -> list[Dict[str, Any]]:
        return DemandReconstructionSemanticContextApplier.llm_semantic_fragment_targets(package)

    def _merge_llm_and_rule_candidates(
        self,
        llm_candidates: list[Dict[str, Any]],
        rule_candidates: list[Dict[str, Any]],
    ) -> list[Dict[str, Any]]:
        return DemandReconstructionSemanticContextApplier.merge_llm_and_rule_candidates(
            llm_candidates,
            rule_candidates,
        )

    def _llm_no_match_candidate(self, package: Dict[str, Any]) -> Dict[str, Any]:
        return DemandReconstructionSemanticContextApplier.llm_no_match_candidate(package)

    @staticmethod
    def _llm_semantic_scan_result(package: Dict[str, Any], candidates: list[Dict[str, Any]]) -> Dict[str, Any]:
        return DemandReconstructionSemanticContextApplier.llm_semantic_scan_result(
            package,
            candidates,
        )

    @classmethod
    def _normalize_llm_semantic_target(cls, value: Any) -> Optional[str]:
        return DemandReconstructionSemanticContextApplier(
            target_aliases=cls._LLM_SEMANTIC_TARGET_ALIASES,
        ).normalize_llm_semantic_target(value)

    @staticmethod
    def _safe_confidence(value: Any) -> float:
        return DemandReconstructionSemanticContextApplier.safe_confidence(value)

    @staticmethod
    def _take_evidence(value: Any) -> list[str]:
        return DemandReconstructionSemanticContextApplier.take_evidence(value)

    @staticmethod
    def _dedupe_strings(values: list[str]) -> list[str]:
        return DemandReconstructionSemanticContextApplier.dedupe_strings(values)

    @staticmethod
    def _build_semantic_router_prompt(message: str) -> str:
        return DemandReconstructionSemanticRouter.build_prompt(
            message,
            target_aliases=DemandReconstructionService._LLM_SEMANTIC_TARGET_ALIASES,
        )

    def _invoke_semantic_router_with_llm(
        self,
        *,
        llm: Any,
        prompt: str,
        provider: str,
    ) -> tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        return self._semantic_router.invoke_with_llm(llm=llm, prompt=prompt, provider=provider)

    @staticmethod
    def _build_semantic_router_repair_prompt(*, original_prompt: str, rejected_content: str) -> str:
        return DemandReconstructionSemanticRouter.build_repair_prompt(
            original_prompt=original_prompt,
            rejected_content=rejected_content,
        )

    def _parse_semantic_understanding(self, content: str) -> Optional[Dict[str, Any]]:
        return self._semantic_router.parse(content)

    @staticmethod
    def _semantic_understanding_is_valid(package: Dict[str, Any]) -> bool:
        return DemandReconstructionSemanticRouter.is_valid(package)

    @staticmethod
    def _render_reply(plan: Dict[str, Any]) -> str:
        return DemandReconstructionResponseBuilder().render_reply(plan)

    @staticmethod
    def _evaluate_alignment_shadow(
        *,
        source_message: str,
        visible_text: str,
        adapter_context: Dict[str, Any],
        card: Dict[str, Any],
    ) -> Dict[str, Any]:
        return DemandReconstructionAlignmentGate.evaluate_alignment_shadow(
            source_message=source_message,
            visible_text=visible_text,
            adapter_context=adapter_context,
            card=card,
        )

    @staticmethod
    def _card(plan: Dict[str, Any]) -> Dict[str, Any]:
        return DemandReconstructionResponseBuilder().build_card(plan)

    @staticmethod
    def _public_card_summary(plan: Dict[str, Any]) -> Dict[str, Any]:
        return DemandReconstructionResponseBuilder.public_card_summary(plan)

    @staticmethod
    def _public_adapter_context(adapter_context: Dict[str, Any]) -> Dict[str, Any]:
        return DemandReconstructionResponseBuilder.public_adapter_context(adapter_context)


    @staticmethod
    def _append_insight_quality_signal(
        signals: Any,
        insight_quality: Dict[str, Any],
    ) -> list[Dict[str, Any]]:
        return DemandReconstructionInsightQualityGate.append_insight_quality_signal(
            signals,
            insight_quality,
        )
