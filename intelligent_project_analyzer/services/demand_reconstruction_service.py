"""Demand reconstruction orchestration for Scheme Advisor.

This layer is the purchase-before-proof shape for Design Brief 2.0:
it returns an action blueprint that reconstructs vague demand, not a formal
intake questionnaire.
"""

from __future__ import annotations

import time
from typing import Any, Dict, Optional

from loguru import logger

from intelligent_project_analyzer.modules.demand_reconstruction.alignment_gate import (
    DemandReconstructionAlignmentGate,
)
from intelligent_project_analyzer.modules.demand_reconstruction.insight_quality_gate import (
    DemandReconstructionInsightQualityGate,
)
from intelligent_project_analyzer.modules.demand_reconstruction.response_builder import (
    DemandReconstructionResponseBuilder,
)
from intelligent_project_analyzer.modules.demand_reconstruction.blueprint_coordinator import (
    DemandReconstructionBlueprintCoordinator,
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
from intelligent_project_analyzer.modules.demand_reconstruction.contracts import (
    DEMAND_RECONSTRUCTION_CARD_TYPE,
    DEMAND_RECONSTRUCTION_INTENT,
    SYNTHESIS_UNAVAILABLE,
    UNDERSTANDING_UNAVAILABLE,
)
from .demand_reconstruction_context_adapter import DemandReconstructionContextAdapter
from .demand_reconstruction_insight_quality import DemandReconstructionInsightQualityEvaluator
from .demand_reconstruction_insight_protocol import DemandReconstructionInsightProtocol
from .demand_reconstruction_output_planner import DemandReconstructionOutputPlanner
from .latent_model_adapter import LatentModelAdapter
from .scheme_advisor_semantic_axes import should_enter_demand_reconstruction


class DemandReconstructionUnavailable(RuntimeError):
    """Raised when the LLM-first demand reconstruction path cannot produce output."""

    def __init__(
        self,
        *,
        error_code: str,
        diagnostics: Optional[Dict[str, Any]] = None,
        user_message: str = "智能识别暂不可用，请重试。",
    ) -> None:
        super().__init__(user_message)
        self.error_code = error_code
        self.user_message = user_message
        self.diagnostics = dict(diagnostics or {})


class DemandReconstructionService:
    """Generate a non-freezing demand reconstruction for early ambiguous inputs."""

    CARD_TYPE = DEMAND_RECONSTRUCTION_CARD_TYPE
    INTENT = DEMAND_RECONSTRUCTION_INTENT
    _LLM_SEMANTIC_TARGET_ALIASES = {
        "life_identity": "life_identity",
        "personal_residential": "life_identity",
        "residential": "life_identity",
        "home": "life_identity",
        "commercial_operation": "commercial_operation",
        "commercial": "commercial_operation",
        "retail_commercial": "commercial_operation",
        "brand_experience": "commercial_operation",
        "commercial_dining": "commercial_operation",
        "public_cultural_experience": "public_cultural_experience",
        "public_cultural": "public_cultural_experience",
        "cultural_exhibition": "public_cultural_experience",
        "education_public": "public_cultural_experience",
        "media_production": "media_production",
        "digital_media_studio": "media_production",
        "content_production": "media_production",
        "style_semantics": "style_semantics",
        "hard_constraint": "hard_constraint",
        "technical_constraint": "hard_constraint",
        "cultural_research": "cultural_research",
        "healthcare_care": "healthcare_care",
        "workplace_headquarters": "workplace_headquarters",
        "urban_renewal": "urban_renewal",
        "collection_museum": "collection_museum",
        "general_project": "general_project",
    }

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
        require_llm: bool = False,
        governance_store: Any = None,
    ) -> None:
        self._llm = llm
        self._require_llm = require_llm
        self._governance_store = governance_store
        self._governance = governance or DemandReconstructionGovernance(
            governance_store=governance_store,
        )
        self._context_adapter = context_adapter or DemandReconstructionContextAdapter()
        self._insight_protocol = insight_protocol or DemandReconstructionInsightProtocol()
        # LLM Semantic Router remains the first understanding boundary; the
        # implementation lives in modules/demand_reconstruction/semantic_router.py.
        self._semantic_router = semantic_router or DemandReconstructionSemanticRouter(
            llm=self._llm,
            parse_response_json=self._insight_protocol.parse_response_json,
            target_aliases=self._LLM_SEMANTIC_TARGET_ALIASES,
        )
        self._semantic_context_applier = (
            semantic_context_applier
            or DemandReconstructionSemanticContextApplier(
                target_aliases=self._LLM_SEMANTIC_TARGET_ALIASES,
            )
        )
        self._output_planner = output_planner or DemandReconstructionOutputPlanner()
        self._synthesis = synthesis or DemandReconstructionSynthesis(
            llm=self._llm,
            insight_protocol=self._insight_protocol,
            output_planner=self._output_planner,
        )
        self._blueprint_coordinator = (
            blueprint_coordinator
            or DemandReconstructionBlueprintCoordinator(
                llm=self._llm,
                output_planner=self._output_planner,
                synthesis=self._synthesis,
                require_llm=self._require_llm,
                unavailable_factory=DemandReconstructionUnavailable,
            )
        )
        self._response_builder = response_builder or DemandReconstructionResponseBuilder()
        self._alignment_gate = alignment_gate or DemandReconstructionAlignmentGate(
            output_planner=self._output_planner,
            render_reply=self._response_builder.render_reply,
            build_card=self._response_builder.build_card,
        )
        self._latent_model_adapter = latent_model_adapter or LatentModelAdapter()
        self._insight_quality_evaluator = (
            insight_quality_evaluator or DemandReconstructionInsightQualityEvaluator()
        )
        self._insight_quality_gate = insight_quality_gate or DemandReconstructionInsightQualityGate(
            evaluator=self._insight_quality_evaluator,
        )

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
                return self._result(user_message, previous_context=context, session=session)
            return None

        if not self.should_handle(user_message):
            return None
        return self._result(user_message, session=session)

    def should_handle(self, message: str) -> bool:
        return should_enter_demand_reconstruction(message)

    def is_formal_brief_request(self, message: str) -> bool:
        text = str(message or "")
        if any(term in text for term in self._FORMAL_TERMS):
            return True
        has_complete = "完整" in text
        has_framework = any(term in text for term in ("框架", "概念", "方案"))
        has_multi_topic = sum(1 for term in ("光", "材料", "动线", "自然", "空间", "界面", "精神性") if term in text) >= 3
        return has_complete and has_framework and has_multi_topic

    def _result(
        self,
        message: str,
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
            self._apply_llm_semantic_understanding_to_adapter_context(
                adapter_context,
                llm_semantic_understanding,
            )
        self._apply_governed_knowledge_assets(
            adapter_context=adapter_context,
            session=session or {},
            source_message=message,
        )
        latent_model = self._latent_model_adapter.build(
            source_message=message,
            adapter_context=adapter_context,
        )
        adapter_context["latent_model"] = latent_model.model_dump(mode="json")
        if previous_context and previous_context.get("blueprint", {}).get("task_reframe"):
            adapter_context["previous_blueprint"] = previous_context["blueprint"]
        blueprint = self._build_blueprint(adapter_context)
        reply = self._response_builder.render_reply(blueprint)
        card = self._response_builder.build_card(blueprint)
        alignment_shadow = self._evaluate_alignment_shadow(
            source_message=message,
            visible_text=reply,
            adapter_context=adapter_context,
            card=card,
        )
        blueprint, reply, card, alignment_shadow = self._alignment_gate.maybe_reject_to_semantic_fallback(
            blueprint=blueprint,
            reply=reply,
            card=card,
            alignment_shadow=alignment_shadow,
            adapter_context=adapter_context,
            source_message=message,
        )
        self._insight_quality_gate.apply(
            source_message=message,
            adapter_context=adapter_context,
            blueprint=blueprint,
            visible_reply=reply,
        )
        blueprint["semantic_alignment_shadow"] = alignment_shadow
        governance_persistence = self._persist_governance_signals(
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
        return bool(str(message or "").strip())

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
