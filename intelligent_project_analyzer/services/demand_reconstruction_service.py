"""Demand reconstruction orchestration for Scheme Advisor.

This layer is the purchase-before-proof shape for Design Brief 2.0:
it returns an action blueprint that reconstructs vague demand, not a formal
intake questionnaire.
"""

from __future__ import annotations

import os
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger

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
from .scheme_advisor_semantic_axes import (
    evaluate_semantic_alignment,
    should_enter_demand_reconstruction,
)


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
        self._semantic_router = semantic_router or DemandReconstructionSemanticRouter(
            llm=self._llm,
            parse_response_json=self._insight_protocol.parse_response_json,
            target_aliases=self._LLM_SEMANTIC_TARGET_ALIASES,
        )
        self._output_planner = output_planner or DemandReconstructionOutputPlanner()
        self._synthesis = synthesis or DemandReconstructionSynthesis(
            llm=self._llm,
            insight_protocol=self._insight_protocol,
            output_planner=self._output_planner,
        )
        self._latent_model_adapter = latent_model_adapter or LatentModelAdapter()
        self._insight_quality_evaluator = (
            insight_quality_evaluator or DemandReconstructionInsightQualityEvaluator()
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
        reply = self._render_reply(blueprint)
        card = self._card(blueprint)
        alignment_shadow = self._evaluate_alignment_shadow(
            source_message=message,
            visible_text=reply,
            adapter_context=adapter_context,
            card=card,
        )
        # Pre-render hard gate. An LLM-fused blueprint that produced a blocking
        # semantic-alignment violation is dropped in favour of the registry-driven
        # semantic pack, which is safer than showing a wrong-domain first screen.
        # Shadow-only mode is available only through an explicit diagnostic env flag.
        if (
            self._alignment_hard_gate_enabled()
            and alignment_shadow.get("blocking_count", 0) > 0
            and blueprint.get("insight_source") != "semantic_fallback"
        ):
            blueprint, reply, card, alignment_shadow = self._reject_to_semantic_fallback(
                adapter_context=adapter_context,
                source_message=message,
                rejected_alignment=alignment_shadow,
            )
        insight_quality = self._insight_quality_evaluator.evaluate(
            source_message=message,
            semantic_package=adapter_context.get("llm_semantic_understanding") or {},
            latent_model=adapter_context.get("latent_model") or {},
            blueprint=blueprint,
            visible_reply=reply,
        )
        blueprint["insight_quality"] = insight_quality
        blueprint["governance_signals"] = self._append_insight_quality_signal(
            blueprint.get("governance_signals") or [],
            insight_quality,
        )
        blueprint["semantic_alignment_shadow"] = alignment_shadow
        governance_persistence = self._persist_governance_signals(
            session=session or {},
            source_message=message,
            blueprint=blueprint,
        )
        if governance_persistence:
            blueprint["governance_persistence"] = governance_persistence
        context = {
            "schema_version": "demand_reconstruction_context.v1",
            "reconstruction_type": "demand_reconstruction",
            "artifact_name": "action_blueprint",
            "display_title": "需求重构",
            "display_artifact_name": "行动蓝图",
            "created_at": datetime.now().isoformat(),
            "source_message": message,
            "adapter_context": self._public_adapter_context(adapter_context),
            "blueprint": blueprint,
            "brief_handoff_slots": blueprint["brief_handoff_slots"],
            "semantic_alignment_shadow": alignment_shadow,
        }
        return {
            "reply": reply,
            "intent": self.INTENT,
            "dialogue_layer": "demand_reconstruction",
            "handoff_available": True,
            "guidance_card": card,
            "demand_reconstruction_context": context,
            "drafts": [],
            "upgrade_signal": None,
            "upgrade_suggested": False,
        }

    @staticmethod
    def _alignment_hard_gate_enabled() -> bool:
        """Whether the semantic-alignment gate may reject output (read at call time).

        Defaults to on because demand reconstruction is a user-visible first
        screen: blocking semantic drift should fall back before rendering. Set
        ``DEMAND_RECONSTRUCTION_ALIGNMENT_GATE=0`` only for diagnostic shadow
        runs where we intentionally observe drift without altering output.
        """
        flag = os.getenv("DEMAND_RECONSTRUCTION_ALIGNMENT_GATE", "1")
        return str(flag).strip().lower() not in {"0", "false", "off", "no"}

    def _reject_to_semantic_fallback(
        self,
        *,
        adapter_context: Dict[str, Any],
        source_message: str,
        rejected_alignment: Dict[str, Any],
    ) -> tuple[Dict[str, Any], str, Dict[str, Any], Dict[str, Any]]:
        """Replace a blocking LLM blueprint with the registry-driven semantic pack.

        Rebuilds the semantic plan, re-renders the reply and card, and
        re-evaluates the alignment shadow so observability reflects the version
        the user actually sees.
        """
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
        blueprint["governance_signals"] = self._append_alignment_rejection_signal(
            semantic_plan.get("governance_signals") or [],
            blocking_codes,
        )
        reply = self._render_reply(blueprint)
        card = self._card(blueprint)
        alignment_shadow = self._evaluate_alignment_shadow(
            source_message=source_message,
            visible_text=reply,
            adapter_context=adapter_context,
            card=card,
        )
        return blueprint, reply, card, alignment_shadow

    @staticmethod
    def _append_alignment_rejection_signal(
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
        semantic_plan = self._output_planner.build_plan(adapter_context)
        if self._llm is None:
            if self._require_llm:
                raise DemandReconstructionUnavailable(
                    error_code=UNDERSTANDING_UNAVAILABLE,
                    diagnostics={"status": "not_configured"},
                )
            return {**semantic_plan, "insight_source": "semantic_fallback", "llm_status": "not_configured"}
        llm_plan, llm_diagnostics = self._build_llm_insight_blueprint(adapter_context, semantic_plan)
        if llm_plan is None:
            if self._require_llm:
                raise DemandReconstructionUnavailable(
                    error_code=SYNTHESIS_UNAVAILABLE,
                    diagnostics=llm_diagnostics,
                )
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
        return llm_plan

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
        """Let Stage 1 LLM understanding drive the Stage 2 rule scanner.

        The deterministic context adapter remains the offline/rule fallback.
        In the LLM-required path, evidence-backed semantic router candidates are
        promoted before the keyword-derived candidates so blueprint selection
        follows the first LLM understanding rather than raw keyword hits.
        """
        adapter_context["llm_semantic_understanding"] = package
        llm_candidates = self._llm_semantic_candidates(package)
        fragment_targets = self._llm_semantic_fragment_targets(package)
        scan_result = self._llm_semantic_scan_result(package, llm_candidates)
        adapter_context["llm_semantic_scan"] = scan_result
        if fragment_targets:
            adapter_context["llm_semantic_fragment_targets"] = fragment_targets
        self._refresh_llm_semantic_asset_scan(adapter_context, fragment_targets=fragment_targets)
        self._apply_llm_semantic_governance_context(adapter_context, package, scan_result)
        context_source = dict(adapter_context.get("context_source") or {})
        context_source["llm_semantic_router"] = True
        context_source["llm_semantic_scan_result"] = scan_result["result"]
        if fragment_targets:
            context_source["llm_semantic_fragment_targets"] = True
        adapter_context["context_source"] = context_source
        if scan_result["result"] == "no_match":
            merged = self._merge_llm_and_rule_candidates(
                [self._llm_no_match_candidate(package)],
                adapter_context.get("semantic_candidate_set") or [],
            )
            adapter_context["semantic_candidate_set"] = merged
            adapter_context["archetype"] = DemandReconstructionContextAdapter._archetype_from_candidates(merged)
            return
        if not llm_candidates:
            return
        merged = self._merge_llm_and_rule_candidates(
            llm_candidates,
            adapter_context.get("semantic_candidate_set") or [],
        )
        adapter_context["semantic_candidate_set"] = merged
        adapter_context["archetype"] = DemandReconstructionContextAdapter._archetype_from_candidates(merged)

    def _refresh_llm_semantic_asset_scan(
        self,
        adapter_context: Dict[str, Any],
        *,
        fragment_targets: Optional[list[Dict[str, Any]]] = None,
    ) -> None:
        scan = adapter_context.get("llm_semantic_scan")
        if not isinstance(scan, dict):
            return
        asset_scan: Dict[str, Any] = {}
        targets = fragment_targets
        if targets is None:
            targets = adapter_context.get("llm_semantic_fragment_targets") or []
        rule_fragments = []
        for target in targets or []:
            if not isinstance(target, dict):
                continue
            item = {
                key: target.get(key)
                for key in ("group_id", "fragment_id", "confidence", "source")
                if target.get(key) not in (None, "", [], {})
            }
            evidence = [str(value) for value in (target.get("evidence") or []) if str(value)][:3]
            if evidence:
                item["evidence"] = evidence
            if item:
                rule_fragments.append(item)
        if rule_fragments:
            asset_scan["rule_fragments"] = rule_fragments[:5]

        axes = adapter_context.get("semantic_axes")
        if isinstance(axes, dict) and axes:
            asset_scan["semantic_axes"] = {
                "axis_ids": [str(key) for key in axes.keys() if str(key)][:8],
            }

        tensions = []
        for tension in adapter_context.get("main_tensions") or []:
            if isinstance(tension, dict) and tension.get("title"):
                tensions.append(str(tension.get("title")))
            if len(tensions) >= 5:
                break
        if tensions:
            asset_scan["main_tensions"] = {
                "count": len(adapter_context.get("main_tensions") or []),
                "titles": tensions,
            }

        coverage = adapter_context.get("knowledge_coverage_ceiling")
        if isinstance(coverage, dict) and coverage:
            asset_scan["knowledge_coverage"] = {
                key: coverage.get(key)
                for key in ("level", "coverage_level", "ceiling_level", "source")
                if coverage.get(key) not in (None, "", [], {})
            }

        approved_assets = []
        for asset in adapter_context.get("governed_knowledge_assets") or []:
            if not isinstance(asset, dict):
                continue
            approved_assets.append(
                {
                    key: asset.get(key)
                    for key in ("card_id", "title", "project_type", "evidence_level", "match_metadata")
                    if asset.get(key) not in (None, "", [], {})
                }
            )
            if len(approved_assets) >= 3:
                break
        if approved_assets:
            asset_scan["approved_knowledge_assets"] = approved_assets

        if asset_scan:
            scan["asset_scan"] = asset_scan
            adapter_context["llm_semantic_scan"] = scan

    def _apply_llm_semantic_governance_context(
        self,
        adapter_context: Dict[str, Any],
        package: Dict[str, Any],
        scan_result: Dict[str, Any],
    ) -> None:
        result = str(scan_result.get("result") or "")
        if result not in {"no_match", "partial_match"}:
            return
        classification = dict(adapter_context.get("classification") or {})
        evidence = self._llm_semantic_package_evidence(package)
        project_object = str(package.get("project_object") or "").strip() or "未覆盖空间项目"
        classification["coverage_gap"] = True
        classification["knowledge_gap"] = True
        classification["knowledge_gap_ticket"] = {
            "gap_type": "llm_semantic_no_match" if result == "no_match" else "llm_semantic_partial_match",
            "project_type": project_object,
            "summary": f"LLM Semantic Router 判断“{project_object}”缺少稳定专科规则/知识覆盖。",
            "source": "llm_semantic_router",
            "evidence": evidence,
            "scan_result": result,
            "matched_targets": list(scan_result.get("matched_targets") or []),
            "package_ids": self._llm_semantic_taxonomy_ids(package, "package_ids", "knowledge_package_ids"),
            "ontology_dimension_ids": self._llm_semantic_taxonomy_ids(
                package,
                "ontology_dimension_ids",
                "dimension_ids",
                "semantic_dimension_ids",
            ),
        }
        if result == "no_match":
            classification["new_fragment_candidate"] = {
                "fragment_id": self._candidate_fragment_id(project_object),
                "project_object": project_object,
                "summary": f"评估是否需要为“{project_object}”沉淀新的需求重构规则碎片。",
                "source": "llm_semantic_router",
                "evidence": evidence,
                "scan_result": result,
            }
        adapter_context["knowledge_coverage_ceiling"] = self._llm_semantic_coverage_ceiling(
            scan_result=result,
            project_object=project_object,
            evidence=evidence,
            matched_targets=list(scan_result.get("matched_targets") or []),
        )
        adapter_context["classification"] = classification

    @staticmethod
    def _llm_semantic_coverage_ceiling(
        *,
        scan_result: str,
        project_object: str,
        evidence: list[str],
        matched_targets: list[str],
    ) -> Dict[str, Any]:
        if scan_result == "partial_match":
            return {
                "level": "partial_specialist",
                "coverage_level": "partial_specialist",
                "ceiling_level": "l1_neighbor_transfer",
                "source": "llm_semantic_router",
                "must_not_claim_specialist_coverage": True,
                "matched_targets": matched_targets,
                "evidence": evidence,
                "reasons": [
                    "LLM Semantic Router 判断当前需求只部分命中稳定规则碎片。",
                    "可使用命中的邻近规则做结构约束，但不能冒充完整专科覆盖。",
                ],
                "allowed_outputs": ["邻近迁移判断", "关键未知边界", "需要补充的专科问题"],
                "forbidden_outputs": ["完整专科结论", "施工级建议", "题面无支撑的专名或案例"],
                "user_visible_note": f"“{project_object}”只部分命中现有规则蓝图，需要按邻近迁移处理并标注边界。",
            }
        return {
            "level": "general_method_only",
            "coverage_level": "general_method_only",
            "ceiling_level": "l0_general",
            "source": "llm_semantic_router",
            "must_not_claim_specialist_coverage": True,
            "matched_targets": matched_targets,
            "evidence": evidence,
            "reasons": [
                "LLM Semantic Router 判断当前需求没有可靠命中稳定规则碎片。",
                "只能做通用方法论重构，不能伪造专科规则覆盖。",
            ],
            "allowed_outputs": ["通用第一性推理", "成立条件", "知识缺口与下一步追问"],
            "forbidden_outputs": ["套用相近模板", "完整专科结论", "施工级建议"],
            "user_visible_note": f"“{project_object}”未命中稳定规则蓝图，只能按通用方法论先收束判断。",
        }

    @staticmethod
    def _llm_semantic_taxonomy_ids(package: Dict[str, Any], *keys: str) -> list[str]:
        values: list[str] = []
        for key in keys:
            raw_values = package.get(key) if isinstance(package, dict) else None
            if not isinstance(raw_values, list):
                continue
            for value in raw_values:
                text = str(value or "").strip()
                if text:
                    values.append(text)
        return DemandReconstructionService._dedupe_strings(values)

    @staticmethod
    def _candidate_fragment_id(project_object: str) -> str:
        normalized = str(project_object or "").strip().lower()
        ascii_slug = "".join(char if char.isalnum() and ord(char) < 128 else "_" for char in normalized)
        ascii_slug = "_".join(part for part in ascii_slug.split("_") if part)
        return ascii_slug or "llm_semantic_new_fragment"

    def _llm_semantic_package_evidence(self, package: Dict[str, Any]) -> list[str]:
        evidence: list[str] = []
        for item in package.get("space_candidates") or []:
            if isinstance(item, dict):
                evidence.extend(self._take_evidence(item.get("evidence")))
        for item in package.get("core_tensions") or []:
            if isinstance(item, dict):
                evidence.extend(self._take_evidence(item.get("evidence")))
        return self._dedupe_strings(evidence)

    def _llm_semantic_candidates(self, package: Dict[str, Any]) -> list[Dict[str, Any]]:
        recommended = [
            normalized
            for value in (package.get("recommended_scan_targets") or [])
            if (normalized := self._normalize_llm_semantic_target(value))
        ]
        recommended_order = {candidate_id: index for index, candidate_id in enumerate(recommended)}
        candidates_by_id: Dict[str, Dict[str, Any]] = {}
        for index, item in enumerate(package.get("space_candidates") or []):
            if not isinstance(item, dict):
                continue
            candidate_id = self._normalize_llm_semantic_target(item.get("label"))
            if not candidate_id:
                continue
            evidence = self._take_evidence(item.get("evidence"))
            if not evidence:
                continue
            confidence = self._safe_confidence(item.get("confidence"))
            if confidence < 0.5:
                continue
            score = 120 + int(confidence * 30)
            if candidate_id in recommended_order:
                score += max(0, 10 - recommended_order[candidate_id])
            score -= index
            existing = candidates_by_id.get(candidate_id)
            if existing and int(existing.get("score") or 0) >= score:
                existing["evidence"] = self._dedupe_strings(list(existing.get("evidence") or []) + evidence)
                existing["confidence"] = max(float(existing.get("confidence") or 0), confidence)
                continue
            candidates_by_id[candidate_id] = {
                "id": candidate_id,
                "score": score,
                "role": "secondary",
                "evidence": evidence,
                "counter_evidence": [],
                "routing_target": "demand_reconstruction",
                "source": "llm_semantic_router",
                "confidence": confidence,
            }
        return sorted(
            candidates_by_id.values(),
            key=lambda item: (-int(item.get("score") or 0), str(item.get("id") or "")),
        )

    def _llm_semantic_fragment_targets(self, package: Dict[str, Any]) -> list[Dict[str, Any]]:
        targets: list[Dict[str, Any]] = []
        for item in package.get("recommended_fragment_targets") or []:
            if not isinstance(item, dict):
                continue
            group_id = str(item.get("group_id") or "").strip()
            fragment_id = str(item.get("fragment_id") or "").strip()
            if not group_id or not fragment_id:
                continue
            confidence = self._safe_confidence(item.get("confidence"))
            if confidence < 0.5:
                continue
            evidence = self._take_evidence(item.get("evidence"))
            if not evidence:
                continue
            targets.append(
                {
                    "group_id": group_id,
                    "fragment_id": fragment_id,
                    "confidence": confidence,
                    "evidence": evidence,
                    "source": "llm_semantic_router",
                }
            )
        return targets

    def _merge_llm_and_rule_candidates(
        self,
        llm_candidates: list[Dict[str, Any]],
        rule_candidates: list[Dict[str, Any]],
    ) -> list[Dict[str, Any]]:
        merged_by_id: Dict[str, Dict[str, Any]] = {}
        for candidate in llm_candidates:
            merged_by_id[str(candidate.get("id"))] = dict(candidate)
        for candidate in rule_candidates:
            if not isinstance(candidate, dict) or not candidate.get("id"):
                continue
            candidate_id = str(candidate["id"])
            if candidate_id in merged_by_id:
                merged = merged_by_id[candidate_id]
                merged["score"] = max(int(merged.get("score") or 0), int(candidate.get("score") or 0))
                merged["evidence"] = self._dedupe_strings(
                    list(merged.get("evidence") or []) + list(candidate.get("evidence") or [])
                )
                merged["counter_evidence"] = self._dedupe_strings(
                    list(merged.get("counter_evidence") or []) + list(candidate.get("counter_evidence") or [])
                )
            else:
                merged_by_id[candidate_id] = dict(candidate)
        ranked = sorted(
            merged_by_id.values(),
            key=lambda item: (
                0 if item.get("source") == "llm_semantic_router" else 1,
                -int(item.get("score") or 0),
                str(item.get("id") or ""),
            ),
        )
        for index, item in enumerate(ranked):
            if index == 0:
                item["role"] = "primary"
            elif int(item.get("score") or 0) < 50:
                item["role"] = "downweighted"
            else:
                item["role"] = "secondary"
        return ranked

    def _llm_no_match_candidate(self, package: Dict[str, Any]) -> Dict[str, Any]:
        evidence = []
        for item in package.get("space_candidates") or []:
            if isinstance(item, dict):
                evidence.extend(self._take_evidence(item.get("evidence")))
        for item in package.get("core_tensions") or []:
            if isinstance(item, dict):
                evidence.extend(self._take_evidence(item.get("evidence")))
        project_object = str(package.get("project_object") or "").strip()
        if project_object:
            evidence.append(project_object)
        return {
            "id": "general_project",
            "score": 150,
            "role": "primary",
            "evidence": self._dedupe_strings(evidence) or ["LLM Semantic Router 判断现有规则碎片无可靠命中。"],
            "counter_evidence": [],
            "routing_target": "demand_reconstruction",
            "source": "llm_semantic_router_no_match",
            "confidence": 1.0,
        }

    @staticmethod
    def _llm_semantic_scan_result(package: Dict[str, Any], candidates: list[Dict[str, Any]]) -> Dict[str, Any]:
        novelty_level = str(package.get("novelty_level") or "").strip() or "unknown"
        matched_targets = [str(item.get("id")) for item in candidates if item.get("id")]
        confidences = [
            DemandReconstructionService._safe_confidence(item.get("confidence"))
            for item in candidates
            if item.get("id")
        ]
        max_confidence = round(max(confidences), 4) if confidences else 0.0
        if max_confidence >= 0.75:
            confidence_band = "high"
        elif max_confidence >= 0.5:
            confidence_band = "medium"
        else:
            confidence_band = "low"
        if not matched_targets or novelty_level == "unknown" or confidence_band == "low":
            result = "no_match"
        elif novelty_level == "partial_unknown" or confidence_band == "medium":
            result = "partial_match"
        else:
            result = "strong_match"
        return {
            "result": result,
            "matched_targets": matched_targets,
            "novelty_level": novelty_level,
            "confidence_band": confidence_band,
            "max_confidence": max_confidence,
            "source": "llm_semantic_router",
        }

    @classmethod
    def _normalize_llm_semantic_target(cls, value: Any) -> Optional[str]:
        normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
        return cls._LLM_SEMANTIC_TARGET_ALIASES.get(normalized)

    @staticmethod
    def _safe_confidence(value: Any) -> float:
        try:
            confidence = float(value)
        except (TypeError, ValueError):
            return 0.0
        return max(0.0, min(1.0, confidence))

    @staticmethod
    def _take_evidence(value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return DemandReconstructionService._dedupe_strings(
            [str(item).strip() for item in value if str(item).strip()]
        )

    @staticmethod
    def _dedupe_strings(values: list[str]) -> list[str]:
        result = []
        seen = set()
        for value in values:
            text = str(value or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result

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

    @staticmethod
    def _evaluate_alignment_shadow(
        *,
        source_message: str,
        visible_text: str,
        adapter_context: Dict[str, Any],
        card: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Shadow-mode semantic alignment gate (observe-only).

        Runs the local semantic alignment guardrails against the rendered
        output and records the result for observability. Rejection is decided
        by the caller so the same evaluation result can support either the
        default hard gate or an explicit shadow-only diagnostic run.
        """
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

    @staticmethod
    def _card(plan: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "card_id": f"demand_reconstruction-{uuid.uuid4().hex[:8]}",
            "card_type": DemandReconstructionService.CARD_TYPE,
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
            "summary": DemandReconstructionService._public_card_summary(plan),
            "sections": plan.get("sections") or [],
        }

    @staticmethod
    def _public_card_summary(plan: Dict[str, Any]) -> Dict[str, Any]:
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
    def _public_adapter_context(adapter_context: Dict[str, Any]) -> Dict[str, Any]:
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


    @staticmethod
    def _append_insight_quality_signal(
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
