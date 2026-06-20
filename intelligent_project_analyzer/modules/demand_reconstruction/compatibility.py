"""Compatibility helpers for the legacy demand reconstruction service facade."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .alignment_gate import DemandReconstructionAlignmentGate
from .entry_classifier import DemandReconstructionEntryClassifier
from .governance import DemandReconstructionGovernance
from .insight_quality_gate import DemandReconstructionInsightQualityGate
from .response_builder import DemandReconstructionResponseBuilder
from .semantic_context_applier import DemandReconstructionSemanticContextApplier
from .semantic_router import DemandReconstructionSemanticRouter
from .semantic_targets import LLM_SEMANTIC_TARGET_ALIASES


class DemandReconstructionCompatibility:
    """Centralize legacy private-method behavior kept by the service facade."""

    @staticmethod
    def alignment_hard_gate_enabled() -> bool:
        return DemandReconstructionAlignmentGate.hard_gate_enabled()

    @staticmethod
    def append_alignment_rejection_signal(
        existing_signals: Any,
        blocking_codes: list[Any],
    ) -> list[Dict[str, Any]]:
        return DemandReconstructionAlignmentGate.append_alignment_rejection_signal(
            existing_signals,
            blocking_codes,
        )

    @staticmethod
    def governed_knowledge_match_terms(adapter_context: Dict[str, Any], source_message: str) -> list[str]:
        return DemandReconstructionGovernance.governed_knowledge_match_terms(
            adapter_context,
            source_message,
        )

    @staticmethod
    def approved_card_matches_terms(card: Dict[str, Any], terms: list[str]) -> bool:
        return DemandReconstructionGovernance.approved_card_matches_terms(card, terms)

    @staticmethod
    def approved_card_match_metadata(card: Dict[str, Any], terms: list[str]) -> Dict[str, Any]:
        return DemandReconstructionGovernance.approved_card_match_metadata(card, terms)

    @staticmethod
    def compact_governed_knowledge_asset(
        card: Dict[str, Any],
        *,
        match_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return DemandReconstructionGovernance.compact_governed_knowledge_asset(
            card,
            match_metadata=match_metadata,
        )

    @staticmethod
    def governance_scope(session: Dict[str, Any]) -> Dict[str, str]:
        return DemandReconstructionGovernance.governance_scope(session)

    @staticmethod
    def is_demand_reconstruction_followup(message: str) -> bool:
        return DemandReconstructionEntryClassifier.is_demand_reconstruction_followup(message)

    @staticmethod
    def refresh_llm_semantic_asset_scan(
        adapter_context: Dict[str, Any],
        *,
        fragment_targets: Optional[list[Dict[str, Any]]] = None,
    ) -> None:
        DemandReconstructionSemanticContextApplier.refresh_asset_scan(
            adapter_context,
            fragment_targets=fragment_targets,
        )

    @staticmethod
    def llm_semantic_coverage_ceiling(
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
    def llm_semantic_taxonomy_ids(package: Dict[str, Any], *keys: str) -> list[str]:
        return DemandReconstructionSemanticContextApplier.llm_semantic_taxonomy_ids(package, *keys)

    @staticmethod
    def candidate_fragment_id(project_object: str) -> str:
        return DemandReconstructionSemanticContextApplier.candidate_fragment_id(project_object)

    @staticmethod
    def llm_semantic_package_evidence(package: Dict[str, Any]) -> list[str]:
        return DemandReconstructionSemanticContextApplier.llm_semantic_package_evidence(package)

    @staticmethod
    def llm_semantic_fragment_targets(package: Dict[str, Any]) -> list[Dict[str, Any]]:
        return DemandReconstructionSemanticContextApplier.llm_semantic_fragment_targets(package)

    @staticmethod
    def merge_llm_and_rule_candidates(
        llm_candidates: list[Dict[str, Any]],
        rule_candidates: list[Dict[str, Any]],
    ) -> list[Dict[str, Any]]:
        return DemandReconstructionSemanticContextApplier.merge_llm_and_rule_candidates(
            llm_candidates,
            rule_candidates,
        )

    @staticmethod
    def llm_no_match_candidate(package: Dict[str, Any]) -> Dict[str, Any]:
        return DemandReconstructionSemanticContextApplier.llm_no_match_candidate(package)

    @staticmethod
    def llm_semantic_scan_result(package: Dict[str, Any], candidates: list[Dict[str, Any]]) -> Dict[str, Any]:
        return DemandReconstructionSemanticContextApplier.llm_semantic_scan_result(
            package,
            candidates,
        )

    @staticmethod
    def normalize_llm_semantic_target(value: Any) -> Optional[str]:
        return DemandReconstructionSemanticContextApplier(
            target_aliases=LLM_SEMANTIC_TARGET_ALIASES,
        ).normalize_llm_semantic_target(value)

    @staticmethod
    def safe_confidence(value: Any) -> float:
        return DemandReconstructionSemanticContextApplier.safe_confidence(value)

    @staticmethod
    def take_evidence(value: Any) -> list[str]:
        return DemandReconstructionSemanticContextApplier.take_evidence(value)

    @staticmethod
    def dedupe_strings(values: list[str]) -> list[str]:
        return DemandReconstructionSemanticContextApplier.dedupe_strings(values)

    @staticmethod
    def build_semantic_router_prompt(message: str) -> str:
        return DemandReconstructionSemanticRouter.build_prompt(
            message,
            target_aliases=LLM_SEMANTIC_TARGET_ALIASES,
        )

    @staticmethod
    def build_semantic_router_repair_prompt(*, original_prompt: str, rejected_content: str) -> str:
        return DemandReconstructionSemanticRouter.build_repair_prompt(
            original_prompt=original_prompt,
            rejected_content=rejected_content,
        )

    @staticmethod
    def semantic_understanding_is_valid(package: Dict[str, Any]) -> bool:
        return DemandReconstructionSemanticRouter.is_valid(package)

    @staticmethod
    def render_reply(plan: Dict[str, Any]) -> str:
        return DemandReconstructionResponseBuilder().render_reply(plan)

    @staticmethod
    def evaluate_alignment_shadow(
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
    def card(plan: Dict[str, Any]) -> Dict[str, Any]:
        return DemandReconstructionResponseBuilder().build_card(plan)

    @staticmethod
    def public_card_summary(plan: Dict[str, Any]) -> Dict[str, Any]:
        return DemandReconstructionResponseBuilder.public_card_summary(plan)

    @staticmethod
    def public_adapter_context(adapter_context: Dict[str, Any]) -> Dict[str, Any]:
        return DemandReconstructionResponseBuilder.public_adapter_context(adapter_context)

    @staticmethod
    def append_insight_quality_signal(
        signals: Any,
        insight_quality: Dict[str, Any],
    ) -> list[Dict[str, Any]]:
        return DemandReconstructionInsightQualityGate.append_insight_quality_signal(
            signals,
            insight_quality,
        )
