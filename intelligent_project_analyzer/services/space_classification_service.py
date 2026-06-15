"""
Space classification and project definition activation.

This service is intentionally side-effect free. It wraps the existing
ProjectTypeDetector, enriches its result with type operating profiles, and
returns dict payloads that can be written into state by workflow nodes.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml
from loguru import logger

from .project_type_detector import PARENT_TYPE_MAP, ProjectTypeDetector, get_type_label
from .scheme_advisor_semantic_axes import derive_semantic_axes
from ..utils.ontology_loader import DETECTOR_TO_ONTOLOGY, _resolve_detector_to_ontology


_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
_PROFILE_PATH = _CONFIG_DIR / "type_operating_profiles.yaml"
_BOUNDARY_PATH = _CONFIG_DIR / "space_classification" / "boundary_cases.yaml"
_MODIFIER_PATH = _CONFIG_DIR / "space_classification" / "runtime_modifiers.yaml"
_MASTER_INDEX_PATH = _CONFIG_DIR / "registries" / "classification_master_index.yaml"
_INDUSTRY_REGISTRY_PATH = _CONFIG_DIR / "registries" / "industry_registry.yaml"
_PROJECT_CONDITION_REGISTRY_PATH = _CONFIG_DIR / "registries" / "project_condition_registry.yaml"
_SPACE_AXIS_REGISTRY_PATH = _CONFIG_DIR / "registries" / "space_axis_registry.yaml"
_ACTIVATION_PACK_DIR = _CONFIG_DIR.parent / "knowledge_base" / "activation_packs"

_RUNTIME_MODIFIER_TO_PROJECT_CONDITION = {
    "mountain": "mountain_context",
    "waterfront": "waterfront_context",
    "rural": "rural_context",
    "urban": "urban_context",
    "social": "social_experience",
    "cultural": "local_culture",
}


class SpaceClassificationService:
    """Build SpaceClassificationResult and ProjectDefinitionActivationPack."""

    def __init__(
        self,
        profile_path: Optional[Path] = None,
        boundary_path: Optional[Path] = None,
        modifier_path: Optional[Path] = None,
        master_index_path: Optional[Path] = None,
    ) -> None:
        self.profile_path = Path(profile_path or _PROFILE_PATH)
        self.boundary_path = Path(boundary_path or _BOUNDARY_PATH)
        self.modifier_path = Path(modifier_path or _MODIFIER_PATH)
        self.master_index_path = Path(master_index_path or _MASTER_INDEX_PATH)
        self.detector = ProjectTypeDetector()
        self._profiles = self._load_yaml(self.profile_path)
        self._boundary_cases = self._load_yaml(self.boundary_path)
        self._modifier_rules = self._load_yaml(self.modifier_path)
        # v1.8: master_index 作为唯一入口, 缺失时回退 (零运行时风险)
        self._master_index = self._load_yaml(self.master_index_path)
        self._industry_registry = self._load_yaml(_INDUSTRY_REGISTRY_PATH)
        self._project_condition_registry = self._load_yaml(_PROJECT_CONDITION_REGISTRY_PATH)
        self._space_axis_registry = self._load_yaml(_SPACE_AXIS_REGISTRY_PATH)

    @staticmethod
    def _load_yaml(path: Path) -> Dict[str, Any]:
        if not path.exists():
            logger.warning(f"[SpaceClassification] config not found: {path}")
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as exc:
            logger.warning(f"[SpaceClassification] failed to load {path}: {exc}")
            return {}

    def classify(
        self,
        user_input: str,
        structured_requirements: Optional[Dict[str, Any]] = None,
        confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Return a SpaceClassificationResult v1-compatible dict."""
        structured_requirements = structured_requirements or {}
        detector_details = self.detector.detect_with_details(user_input or "", confirmed_tasks)

        structured_project_type = self._extract_structured_project_type(structured_requirements)
        detected_project_type = detector_details.get("project_type")
        fallback_project_type = None if structured_project_type else self._fallback_project_type(
            user_input,
            detector_details,
            detected_project_type,
        )
        project_type = structured_project_type or fallback_project_type or detected_project_type
        boundary_resolution = None
        if project_type and not structured_project_type:
            boundary_resolution = self._resolve_boundary_primary_project_type(
                user_input,
                detector_details,
                project_type,
            )
            if boundary_resolution:
                project_type = boundary_resolution["project_type"]
        confidence = detector_details.get("confidence", 0.0) if not structured_project_type else max(
            detector_details.get("confidence", 0.0), 0.70
        )
        confidence = self._confidence_with_fallback_floor(
            confidence,
            user_input,
            project_type,
            fallback_project_type,
            detected_project_type,
        )
        strong_subdomain_signal = self._strong_subdomain_signal(detector_details, project_type)
        confidence = self._confidence_with_subdomain_signal(confidence, strong_subdomain_signal)

        if not project_type:
            return self._unknown_result(user_input, detector_details)

        profile = self._get_profile(project_type)
        parent_type = (
            PARENT_TYPE_MAP.get(project_type)
            or detector_details.get("parent_type")
            or profile.get("primary_bucket")
            or "general"
        )
        primary_bucket = self._canonical_bucket(parent_type)
        runtime_modifiers = self._extract_runtime_modifiers(user_input, structured_requirements)
        profession_context_ids = self._extract_profession_context_ids(user_input, structured_requirements)

        industry_candidates = detector_details.get("industry_candidates") or []
        industry_profile = detector_details.get("industry_profile") or {}
        industry_domain = (
            industry_profile.get("industry_domain")
            or detector_details.get("industry_domain")
        )
        industry_domain_name = (
            industry_profile.get("industry_name")
            or detector_details.get("industry_domain_name")
        )
        industry_profile_status = (
            industry_profile.get("profile_status")
            or detector_details.get("industry_profile_status")
            or "unspecified"
        )
        needs_industry_clarification = bool(
            detector_details.get("needs_industry_clarification", False)
        )
        if strong_subdomain_signal:
            needs_industry_clarification = False

        secondary_types = self._extract_secondary_types(user_input, project_type)
        secondary_candidates = self._build_secondary_candidates(detector_details, secondary_types)
        founding_type = self._extract_primary_founding_type(detector_details)
        ambiguity = self._build_ambiguity(
            project_type,
            secondary_candidates,
            user_input,
            industry_domain,
            industry_candidates,
            self._as_list(detector_details.get("boundary_case_ids")),
            founding_type,
        )
        industry_clarification_questions = self._build_industry_clarification_questions(
            industry_domain, industry_profile_status, needs_industry_clarification
        )
        routing = self._build_routing(project_type, parent_type, profile)

        coverage_gap = (
            confidence < 0.55
            or (not industry_domain and not strong_subdomain_signal)
            or (
                industry_profile_status in {"unspecified", "unknown_detected"}
                and not strong_subdomain_signal
            )
        )
        ontology_unmatched = []
        if coverage_gap and not industry_domain:
            ontology_unmatched.append("industry_domain_unspecified")
        if confidence < 0.55:
            ontology_unmatched.append("low_project_type_confidence")

        knowledge_gap_ticket = None
        if coverage_gap:
            knowledge_gap_ticket = {
                "gap_type": "industry_or_context_gap",
                "proposed_parent_type": project_type,
                "industry_domain": industry_domain,
                "profile_status": industry_profile_status,
                "action": "review_before_registry_promotion",
            }

        _confidence_val = round(float(confidence or 0.0), 3)
        if ambiguity.get("is_ambiguous"):
            _status = "ambiguous"
        elif _confidence_val < 0.55 or needs_industry_clarification:
            _status = "needs_clarification"
        else:
            _status = "draft"

        space_axis = self._build_space_axis(
            user_input=user_input,
            project_type=project_type,
            parent_type=parent_type,
            detector_details=detector_details,
            confidence=_confidence_val,
            coverage_gap=coverage_gap,
        )

        result: Dict[str, Any] = {
            "schema_version": "space_classification.v1",
            "status": _status,
            "primary_bucket": primary_bucket,
            "parent_type": parent_type,
            "project_type": project_type,
            "project_type_name": get_type_label(project_type),
            "confidence": _confidence_val,
            "confidence_level": self._confidence_level(confidence),
            "specialty_tags": self._as_list(detector_details.get("specialty_tag")),
            "secondary_candidates": secondary_candidates,
            "secondary_types": secondary_types,
            "hybrid_weights": None,
            "runtime_modifiers": runtime_modifiers,
            "contextual_project_conditions": self._extract_contextual_project_conditions(user_input),
            "industry_domain": industry_domain,
            "industry_domain_name": industry_domain_name,
            "industry_profile_status": industry_profile_status,
            "industry_candidates": industry_candidates,
            "needs_industry_clarification": needs_industry_clarification,
            "profession_context_ids": profession_context_ids,
            "ambiguity": ambiguity,
            "clarification_questions": (
                ambiguity.get("clarification_questions", []) + industry_clarification_questions
            )[:3],
            "routing": routing,
            "space_axis": space_axis,
            "coverage_gap": coverage_gap,
            "ontology_unmatched": ontology_unmatched,
            "knowledge_gap_ticket": knowledge_gap_ticket,
            "evidence": {
                "detector_reason": detector_details.get("reason", ""),
                "source": "project_type_detector",
                "structured_project_type_used": bool(structured_project_type),
                "fallback_project_type_used": bool(fallback_project_type),
                "boundary_resolution": boundary_resolution,
                "normalization_trace": (
                    detector_details.get("normalization_trace")
                    or (detector_details.get("evidence") or {}).get("normalization_trace")
                    or {}
                ),
                # v1.8: 透传 detector candidate set 供 build_activation_pack._v18_extensions
                # 消费 (不破坏旧字段, 仅在 evidence 内层新增)
                "_detector_full": {
                    "subdomain_signals": detector_details.get("subdomain_signals", []),
                    "scale_signals": detector_details.get("scale_signals", {}),
                    "founding_type_candidates": detector_details.get("founding_type_candidates", []),
                    "industry_candidates": detector_details.get("industry_candidates", []),
                    "industry_profile": detector_details.get("industry_profile", {}),
                    "input_fingerprint": detector_details.get("input_fingerprint"),
                },
            },
            "freeze_state": {
                "classification_frozen": False,
                "can_reclassify_until": "Node3",
            },
        }
        return result

    def build_activation_pack(
        self,
        space_classification: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build ProjectDefinitionActivationPack from a SpaceClassificationResult."""
        project_type = space_classification.get("project_type")
        profile = self._get_profile(project_type)

        knowledge_base_binding = self._merge_knowledge_binding(
            profile.get("knowledge_base_binding") or profile.get("knowledge_binding", {}),
            space_classification.get("runtime_modifiers", {}),
            space_classification.get("secondary_types", []),
            space_classification.get("industry_domain"),
            space_classification.get("profession_context_ids", []),
        )

        v18_extensions = self._build_v18_extensions(space_classification)
        activation_pack_yaml = self._load_activation_pack(v18_extensions.get("activation_pack_id"))
        classification_output = self._build_classification_output_v18(
            space_classification=space_classification,
            v18_extensions=v18_extensions,
            profile=profile,
            runtime_knowledge_binding=knowledge_base_binding,
            activation_pack_yaml=activation_pack_yaml,
        )

        pack = {
            "schema_version": "project_definition_activation_pack.v1.8",
            "compat_schema_version": "project_definition_activation_pack.v1",
            "status": "draft",
            "classification_output": classification_output,
            "classification": space_classification,
            "ontology_profile": deepcopy(profile.get("ontology_profile", {})),
            "type_method_profile": self._get_type_method_profile(profile),
            # Backward-compatible alias. New consumers should read type_method_profile.
            "business_method_profile": self._get_type_method_profile(profile),
            "general_method_profile": deepcopy(profile.get("general_method_profile", {})),
            "domain_framework": deepcopy(profile.get("domain_framework", {})),
            "knowledge_base_binding": knowledge_base_binding,
            # Backward-compatible alias. New consumers should read knowledge_base_binding.
            "knowledge_binding": knowledge_base_binding,
            "system_binding": deepcopy(profile.get("system_binding", {})),
            "downstream_profiles": {
                "questionnaire_profile": profile.get("questionnaire_profile", "general"),
                "floorplan_profile": profile.get("floorplan_profile", "general_floorplan_reasoning"),
                "visual_prompt_profile": profile.get("visual_prompt_profile", "general_visual_profile"),
                "deliverable_profile": profile.get("deliverable_profile", "general_deliverable_profile"),
            },
        }
        # v1.8 扩展: 从 master_index 推导 axis_mappings 信息
        # 不破坏旧字段, 下游可选消费
        pack["_v18_extensions"] = v18_extensions
        return pack

    def _build_classification_output_v18(
        self,
        space_classification: Dict[str, Any],
        v18_extensions: Dict[str, Any],
        profile: Dict[str, Any],
        runtime_knowledge_binding: Dict[str, Any],
        activation_pack_yaml: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build the formal v1.8 classification object carried by activation packs."""
        project_scale = v18_extensions.get("project_scale")
        project_conditions = self._normalize_project_conditions(
            self._flatten_runtime_modifiers(space_classification.get("runtime_modifiers") or {})
            + self._as_list(activation_pack_yaml.get("default_project_conditions"))
            + self._as_list(space_classification.get("contextual_project_conditions"))
        )
        active_discipline_ids = self._unique_strings(
            self._as_list(activation_pack_yaml.get("active_discipline_ids"))
            + self._as_list(profile.get("active_discipline_ids"))
        )
        if not active_discipline_ids:
            active_discipline_ids = self._fallback_discipline_scope(
                project_type=space_classification.get("project_type"),
                spatial_layer_ids=self._as_list(v18_extensions.get("spatial_layer_ids")),
            )

        lead_discipline = "interior" if "interior" in active_discipline_ids else (
            active_discipline_ids[0] if active_discipline_ids else None
        )
        hard_constraint_discipline_ids = self._hard_constraint_disciplines(active_discipline_ids)
        knowledge_scope_ids = self._unique_strings(
            self._as_list((activation_pack_yaml.get("knowledge_base_binding") or {}).get("knowledge_packages"))
            + self._as_list(runtime_knowledge_binding.get("knowledge_packages"))
        )
        spatial_extent = self._spatial_extent_from_project_scale(project_scale)
        lifecycle = self._lifecycle_from_project_scale(project_scale)

        return {
            "schema_version": "classification_output.v1.8",
            "status": space_classification.get("status"),
            "founding_type": v18_extensions.get("founding_type"),
            "project_type_id": space_classification.get("project_type"),
            "project_type_name": space_classification.get("project_type_name"),
            "ontology_framework_id": v18_extensions.get("ontology_framework_id"),
            "subdomain_id": v18_extensions.get("subdomain_id"),
            "activation_pack_id": v18_extensions.get("activation_pack_id"),
            "spatial_extent": spatial_extent,
            "lifecycle": lifecycle,
            "project_scale": project_scale,
            "knowledge_scope_ids": knowledge_scope_ids,
            "project_conditions": project_conditions,
            "hybrid": {
                "secondary_types": space_classification.get("secondary_types") or [],
                "secondary_candidates": space_classification.get("secondary_candidates") or [],
                "hybrid_weights": space_classification.get("hybrid_weights"),
            },
            "discipline_scope": active_discipline_ids,
            "lead_discipline": lead_discipline,
            "hard_constraint_discipline_ids": hard_constraint_discipline_ids,
            "spatial_layer_ids": self._as_list(v18_extensions.get("spatial_layer_ids")),
            "active_ontology_dimension_ids": self._as_list(
                v18_extensions.get("active_ontology_dimension_ids")
            ),
            "priority_ontology_dimension_ids": self._as_list(
                v18_extensions.get("priority_ontology_dimension_ids")
            ),
            "industry_domain": v18_extensions.get("industry_domain") or space_classification.get("industry_domain"),
            "knowledge_card_weights": v18_extensions.get("knowledge_card_weights") or {},
            "confidence": {
                "score": space_classification.get("confidence"),
                "level": space_classification.get("confidence_level"),
            },
            "ambiguity": space_classification.get("ambiguity") or {},
            "ontology_unmatched": self._as_list(space_classification.get("ontology_unmatched")),
            "freeze_state": space_classification.get("freeze_state") or {},
            "source_trace": {
                "detector_source": (space_classification.get("evidence") or {}).get("source"),
                "master_index_source": v18_extensions.get("master_index_source"),
                "profile_id": profile.get("profile_id"),
                "activation_pack_loaded": bool(activation_pack_yaml),
            },
        }

    @staticmethod
    def _flatten_runtime_modifiers(runtime_modifiers: Dict[str, Any]) -> List[str]:
        values: List[str] = []
        for item in runtime_modifiers.values():
            if isinstance(item, list):
                values.extend(str(value) for value in item if value not in (None, ""))
            elif item not in (None, ""):
                values.append(str(item))
        return values

    @staticmethod
    def _strong_subdomain_signal(
        detector_details: Dict[str, Any],
        project_type: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        signals = detector_details.get("subdomain_signals") or []
        for signal in signals:
            if not isinstance(signal, dict):
                continue
            if signal.get("subdomain_registration_status") != "registered":
                continue
            if signal.get("status") not in {"active_mvp", "active", "active_light"}:
                continue
            if signal.get("parent_project_type_id") and signal.get("parent_project_type_id") != project_type:
                continue
            if float(signal.get("confidence") or 0.0) >= 0.70:
                return signal
        return None

    @staticmethod
    def _confidence_with_subdomain_signal(
        confidence: Any,
        signal: Optional[Dict[str, Any]],
    ) -> float:
        base = float(confidence or 0.0)
        if not signal:
            return base
        subdomain_confidence = float(signal.get("confidence") or 0.0)
        return max(base, min(0.82, subdomain_confidence))

    @staticmethod
    def _extract_contextual_project_conditions(user_input: str) -> List[str]:
        text = user_input or ""
        conditions: List[str] = []
        if any(term in text for term in ("地铁", "轨交", "交通通道", "商场连接处", "连接处", "通道")):
            conditions.append("transit_connection")
        if (
            any(term in text for term in ("回本", "收回成本", "投资回收", "回收成本"))
            or ("半年" in text and "成本" in text)
        ):
            conditions.append("payback_pressure")
        return conditions

    def _normalize_project_conditions(self, raw_conditions: Iterable[Any]) -> List[str]:
        """
        Convert detector-layer modifier labels into governed project_condition IDs.

        runtime_modifiers.yaml is a detection layer, while project_condition_registry.yaml
        is the output enum. Only governed IDs should leave classification_output.
        """
        items = (self._project_condition_registry.get("items") or {})
        if not items:
            return self._unique_strings(raw_conditions)

        alias_to_id: Dict[str, str] = dict(_RUNTIME_MODIFIER_TO_PROJECT_CONDITION)
        for condition_id, item in items.items():
            if not isinstance(item, dict):
                continue
            alias_to_id[condition_id] = condition_id
            for alias in self._as_list(item.get("aliases")):
                alias_to_id[str(alias)] = condition_id

        normalized: List[str] = []
        for raw in raw_conditions:
            if raw in (None, ""):
                continue
            condition_id = alias_to_id.get(str(raw), str(raw))
            if condition_id in items:
                normalized.append(condition_id)
        return self._unique_strings(normalized)

    @staticmethod
    def _unique_strings(values: Iterable[Any]) -> List[str]:
        result: List[str] = []
        seen = set()
        for value in values:
            if value in (None, ""):
                continue
            text = str(value)
            if text not in seen:
                seen.add(text)
                result.append(text)
        return result

    @staticmethod
    def _fallback_discipline_scope(project_type: Optional[str], spatial_layer_ids: List[str]) -> List[str]:
        disciplines = ["interior"] if spatial_layer_ids else []
        if project_type in {"hybrid_residential_commercial", "commercial_hospitality", "commercial_enterprise"}:
            disciplines.extend(["architecture", "mep", "fire_safety"])
        if project_type in {"urban_renewal_heritage", "urban_renewal_market"}:
            disciplines.extend(["architecture", "landscape", "urban_planning"])
        return SpaceClassificationService._unique_strings(disciplines or ["interior"])

    @staticmethod
    def _hard_constraint_disciplines(discipline_ids: List[str]) -> List[str]:
        hard_terms = ("mep", "fire", "safety", "structure", "equipment", "cost_construction")
        return [
            discipline_id
            for discipline_id in discipline_ids
            if any(term in discipline_id for term in hard_terms)
        ]

    @staticmethod
    def _spatial_extent_from_project_scale(project_scale: Optional[str]) -> Optional[str]:
        if not project_scale or "_" not in str(project_scale):
            return None
        return str(project_scale).split("_", 1)[0]

    @staticmethod
    def _lifecycle_from_project_scale(project_scale: Optional[str]) -> Optional[str]:
        if not project_scale or "_" not in str(project_scale):
            return None
        return str(project_scale).split("_", 1)[1]

    def _load_activation_pack(self, activation_pack_id: Optional[str]) -> Dict[str, Any]:
        if not activation_pack_id:
            return {}
        return self._load_yaml(_ACTIVATION_PACK_DIR / f"{activation_pack_id}.yaml")

    def _build_v18_extensions(self, space_classification: Dict[str, Any]) -> Dict[str, Any]:
        """
        v1.8 §17 下游消费契约: 从 master_index 推导扩展字段。

        输出字段:
          - ontology_framework_id    : 来自 axis_mappings.project_type_to_framework
          - subdomain_id             : 来自 detector subdomain_signals top-1 (若有)
          - activation_pack_id       : 来自 axis_mappings.subdomain_to_pack
          - spatial_layer_ids        : 来自 project_scale_registry 默认值 (若有 project_scale)
          - active_ontology_dimension_ids : 来自 spatial_layer_to_dimensions
                                            与 founding_type_to_dimensions 的并集
                    - industry_domain          : 来自 classification.industry_domain
                    - knowledge_card_weights   : founding_type / industry_domain 双来源召回偏置
          - master_index_source      : 标识本扩展来自 master_index
        """
        if not self._master_index:
            return {"master_index_source": "missing", "note": "master_index not loaded"}

        project_type = space_classification.get("project_type")
        axis_mappings = self._master_index.get("axis_mappings", {}) or {}

        # 1. project_type → framework
        pt_to_fw = (axis_mappings.get("project_type_to_framework") or {}).get("mappings") or {}
        framework_id = pt_to_fw.get(project_type) or _resolve_detector_to_ontology(project_type or "")

        # detector_full 由 classify() 透传到 evidence._detector_full
        detector_full = (
            (space_classification.get("evidence") or {}).get("_detector_full") or {}
        )

        # 2. subdomain (从 detector subdomain_signals 取 top-1)
        subdomain_signals = detector_full.get("subdomain_signals") or []
        subdomain_id: Optional[str] = None
        activation_pack_id: Optional[str] = None
        if subdomain_signals:
            top_signal = subdomain_signals[0]
            if isinstance(top_signal, dict) and top_signal.get("confidence", 0.0) >= 0.50:
                subdomain_id = top_signal.get("suggested_subdomain_id")
                activation_pack_id = top_signal.get("activation_pack_id")

        # 3. project_scale 合成 (从 detector scale_signals 笛卡尔积)
        scale_signals = detector_full.get("scale_signals") or {}
        spatial_extents = [c["id"] for c in (scale_signals.get("spatial_extent_candidates") or [])]
        lifecycles = [c["id"] for c in (scale_signals.get("lifecycle_candidates") or [])]
        project_scale = self._synthesize_project_scale(spatial_extents, lifecycles, project_type)

        spatial_layer_ids: List[str] = []
        if project_scale:
            scale_reg = self._load_yaml(_CONFIG_DIR / "registries" / "project_scale_registry.yaml")
            scale_item = (scale_reg.get("items") or {}).get(project_scale, {})
            spatial_layer_ids = scale_item.get("default_spatial_layer_ids") or []
        spatial_layer_ids = self._enhance_spatial_layers(
            project_type=project_type,
            project_scale=project_scale,
            spatial_layer_ids=spatial_layer_ids,
            evidence=space_classification.get("evidence") or {},
        )

        # 4. spatial_layer_ids → ontology_dimension_ids
        sl_to_dim = (axis_mappings.get("spatial_layer_to_dimensions") or {}).get("mappings") or {}
        active_dims: List[str] = []
        priority_dims: List[str] = []
        for layer_id in spatial_layer_ids:
            li = sl_to_dim.get(layer_id, {}) or {}
            active_dims.extend(li.get("active_dimensions", []))
            priority_dims.extend(li.get("priority_dimensions", []))

        founding_type = self._extract_primary_founding_type(detector_full)
        founding_dims = self._resolve_founding_dimensions(axis_mappings, founding_type)
        active_dims.extend(founding_dims.get("active_dimensions", []))
        priority_dims.extend(founding_dims.get("priority_dimensions", []))
        founding_card_weights = self._resolve_founding_card_weights(axis_mappings, founding_type)
        industry_domain = space_classification.get("industry_domain")
        industry_card_weights = self._resolve_industry_card_weights(axis_mappings, industry_domain)

        return {
            "master_index_source": "loaded",
            "ontology_framework_id": framework_id,
            "subdomain_id": subdomain_id,
            "activation_pack_id": activation_pack_id,
            "project_scale": project_scale,
            "spatial_layer_ids": spatial_layer_ids,
            "industry_domain": industry_domain,
            "founding_type": founding_type,
            "knowledge_card_weights": {
                "founding_type": founding_card_weights,
                "industry_domain": industry_card_weights,
            },
            "active_ontology_dimension_ids": list(dict.fromkeys(active_dims)),
            "priority_ontology_dimension_ids": list(dict.fromkeys(priority_dims)),
        }

    @staticmethod
    def _extract_primary_founding_type(detector_full: Dict[str, Any]) -> Optional[str]:
        candidates = detector_full.get("founding_type_candidates") or []
        if not candidates:
            return None
        top = candidates[0]
        if isinstance(top, dict):
            return top.get("founding_type_id")
        return None

    @staticmethod
    def _extract_founding_type_ids(detector_full: Dict[str, Any]) -> List[str]:
        ids: List[str] = []
        for candidate in detector_full.get("founding_type_candidates") or []:
            if not isinstance(candidate, dict):
                continue
            founding_type_id = candidate.get("founding_type_id")
            if founding_type_id:
                ids.append(str(founding_type_id))
        return list(dict.fromkeys(ids))

    @staticmethod
    def _extract_subdomain_ids(detector_full: Dict[str, Any]) -> List[str]:
        ids: List[str] = []
        for signal in detector_full.get("subdomain_signals") or []:
            if not isinstance(signal, dict):
                continue
            subdomain_id = signal.get("subdomain_id") or signal.get("suggested_subdomain_id")
            if subdomain_id:
                ids.append(str(subdomain_id))
        return list(dict.fromkeys(ids))

    def _build_space_axis(
        self,
        *,
        user_input: str,
        project_type: Optional[str],
        parent_type: Optional[str],
        detector_details: Dict[str, Any],
        confidence: float,
        coverage_gap: bool,
    ) -> Dict[str, Any]:
        """
        Produce the decision axis consumed by entry-stage questioning.

        This is not a per-question answer template. It is a stable routing layer that
        converts classification evidence into a human-facing decision center so the
        next service can ask relevant questions without exposing registry internals.
        """
        text = (user_input or "").lower()
        semantic_axes = self._derive_space_axis_semantic_axes(user_input)
        founding_type_ids = self._extract_founding_type_ids(detector_details)
        subdomain_ids = self._extract_subdomain_ids(detector_details)
        axis = self._space_axis_payload(
            axis_id="general_space_design_axis",
            matched_rule_id=None,
            project_type=project_type,
            parent_type=parent_type,
            founding_type_ids=founding_type_ids,
            subdomain_ids=subdomain_ids,
            semantic_axes=semantic_axes,
            confidence=confidence,
            coverage_gap=coverage_gap,
        )
        registry_axis = self._match_space_axis_registry(
            text=text,
            project_type=project_type,
            parent_type=parent_type,
            founding_type_ids=founding_type_ids,
            subdomain_ids=subdomain_ids,
            semantic_axes=semantic_axes,
            confidence=confidence,
            coverage_gap=coverage_gap,
        )
        if registry_axis:
            return registry_axis

        has_commercial_return_signal = any(
            keyword in text
            for keyword in (
                "回本",
                "收回成本",
                "成本",
                "预算",
                "坪效",
                "客流",
                "出杯",
                "翻台",
                "外卖",
                "排队",
                "门头",
            )
        )
        has_identity_legacy_signal = any(
            keyword in text
            for keyword in (
                "一代创业者",
                "创业者",
                "草根",
                "资本成功",
                "成就象征",
                "身份",
                "家族传承",
                "精神结构",
                "内心回归",
            )
        )
        founding_set = set(founding_type_ids)
        founding_identity = bool(
            "family_legacy" in founding_set
            or ("identity_expression" in founding_set and has_identity_legacy_signal)
        )

        if project_type == "personal_residential" and (founding_identity or has_identity_legacy_signal):
            axis.update(
                {
                    "primary_axis_id": "private_residential_identity_legacy",
                    "primary_axis_label": "私人住宅：身份表达、家族传承与日常安住",
                    "decision_focus": [
                        "主人精神气质与日常生活如何同时成立",
                        "家族传承、接待场景与私密边界如何分层",
                        "海景资源、材料克制和成就表达如何避免炫耀化",
                    ],
                    "must_not_route_to": ["urban_renewal_heritage", "commercial_enterprise"],
                }
            )
            return axis

        if (
            project_type == "commercial_dining"
            and (has_commercial_return_signal or "tea_drink_store" in subdomain_ids)
        ):
            axis.update(
                {
                    "primary_axis_id": "commercial_operation_roi",
                    "primary_axis_label": "商业餐饮：客流、效率与回本路径",
                    "decision_focus": [
                        "客流来源、排队取餐与出杯效率",
                        "前后场比例、设备制作范围与消防边界",
                        "投入上限、材料克制与半年回本模型",
                    ],
                    "must_not_route_to": [],
                }
            )
            return axis

        if project_type == "personal_residential":
            axis.update(
                {
                    "primary_axis_id": "private_residential_life_order",
                    "primary_axis_label": "私人住宅：家庭秩序、生活方式与精神需求",
                    "decision_focus": [
                        "家庭成员和日常生活节奏",
                        "公共接待与私密居住边界",
                        "风格表达、长期维护与预算取舍",
                    ],
                    "must_not_route_to": ["commercial_operation_roi"],
                }
            )
            return axis

        if not project_type:
            axis.update(
                {
                    "primary_axis_id": "unclassified_needs_axis",
                    "primary_axis_label": "待确认：空间目标和使用边界不足",
                    "decision_focus": [
                        "这个空间主要服务谁",
                        "最重要的使用目标是什么",
                        "是否存在不能突破的安全、合规或预算边界",
                    ],
                    "must_not_route_to": [],
                }
            )
            return axis

        axis["primary_axis_id"] = f"{project_type}_general_axis"
        return axis

    def _space_axis_payload(
        self,
        *,
        axis_id: str,
        matched_rule_id: Optional[str],
        project_type: Optional[str],
        parent_type: Optional[str],
        founding_type_ids: List[str],
        subdomain_ids: List[str],
        semantic_axes: Optional[Dict[str, List[str]]] = None,
        confidence: float,
        coverage_gap: bool,
    ) -> Dict[str, Any]:
        registry_axes = (self._space_axis_registry.get("axes") or {})
        axis_config = registry_axes.get(axis_id) or {}
        default_config = registry_axes.get("general_space_design_axis") or {}
        label = (
            axis_config.get("label")
            or default_config.get("label")
            or "空间设计：目标、约束与取舍关系"
        )
        decision_focus = self._as_list(
            axis_config.get("decision_focus")
            or default_config.get("decision_focus")
            or [
                "先明确这个空间最重要的使用目标",
                "再识别不能突破的现实约束",
                "最后判断哪些体验或成本需要取舍",
            ]
        )
        return {
            "schema_version": "space_axis.v1",
            "registry_source": (
                "space_axis_registry.yaml"
                if self._space_axis_registry.get("schema_version")
                else "code_fallback"
            ),
            "matched_rule_id": matched_rule_id,
            "primary_axis_id": axis_id,
            "primary_axis_label": str(label),
            "decision_focus": decision_focus,
            "must_not_route_to": self._as_list(axis_config.get("must_not_route_to")),
            "basis": {
                "project_type": project_type,
                "parent_type": parent_type,
                "founding_type_ids": founding_type_ids,
                "subdomain_ids": subdomain_ids,
                "semantic_axes": semantic_axes or {},
            },
            "confidence": confidence,
            "coverage_gap": coverage_gap,
        }

    def _match_space_axis_registry(
        self,
        *,
        text: str,
        project_type: Optional[str],
        parent_type: Optional[str],
        founding_type_ids: List[str],
        subdomain_ids: List[str],
        semantic_axes: Dict[str, List[str]],
        confidence: float,
        coverage_gap: bool,
    ) -> Optional[Dict[str, Any]]:
        registry = self._space_axis_registry or {}
        rules = registry.get("rules") or []
        sorted_rules = sorted(
            (rule for rule in rules if isinstance(rule, dict)),
            key=lambda rule: int(rule.get("priority") or 0),
            reverse=True,
        )
        for rule in sorted_rules:
            if not self._space_axis_rule_matches(
                rule,
                text=text,
                project_type=project_type,
                parent_type=parent_type,
                founding_type_ids=founding_type_ids,
                subdomain_ids=subdomain_ids,
                semantic_axes=semantic_axes,
            ):
                continue
            axis_id = str(rule.get("axis_id") or rule.get("id") or "general_space_design_axis")
            return self._space_axis_payload(
                axis_id=axis_id,
                matched_rule_id=str(rule.get("id") or axis_id),
                project_type=project_type,
                parent_type=parent_type,
                founding_type_ids=founding_type_ids,
                subdomain_ids=subdomain_ids,
                semantic_axes=semantic_axes,
                confidence=confidence,
                coverage_gap=coverage_gap,
            )
        return None

    def _space_axis_rule_matches(
        self,
        rule: Dict[str, Any],
        *,
        text: str,
        project_type: Optional[str],
        parent_type: Optional[str],
        founding_type_ids: List[str],
        subdomain_ids: List[str],
        semantic_axes: Dict[str, List[str]],
    ) -> bool:
        project_types = self._as_list(rule.get("project_types"))
        if project_types and project_type not in project_types:
            return False
        parent_types = self._as_list(rule.get("parent_types"))
        if parent_types and parent_type not in parent_types:
            return False

        all_group = self._as_list(rule.get("all_group"))
        if all_group and not all(
            self._space_axis_condition_matches(
                condition,
                text=text,
                founding_type_ids=founding_type_ids,
                subdomain_ids=subdomain_ids,
                semantic_axes=semantic_axes,
            )
            for condition in all_group
            if isinstance(condition, dict)
        ):
            return False

        any_group = self._as_list(rule.get("any_group"))
        if any_group:
            return any(
                self._space_axis_condition_matches(
                    condition,
                    text=text,
                    founding_type_ids=founding_type_ids,
                    subdomain_ids=subdomain_ids,
                    semantic_axes=semantic_axes,
                )
                for condition in any_group
                if isinstance(condition, dict)
            )

        return True

    def _space_axis_condition_matches(
        self,
        condition: Dict[str, Any],
        *,
        text: str,
        founding_type_ids: List[str],
        subdomain_ids: List[str],
        semantic_axes: Dict[str, List[str]],
    ) -> bool:
        if "all_group" in condition:
            nested_all = self._as_list(condition.get("all_group"))
            return all(
                self._space_axis_condition_matches(
                    item,
                    text=text,
                    founding_type_ids=founding_type_ids,
                    subdomain_ids=subdomain_ids,
                    semantic_axes=semantic_axes,
                )
                for item in nested_all
                if isinstance(item, dict)
            )
        if "any_group" in condition:
            nested_any = self._as_list(condition.get("any_group"))
            return any(
                self._space_axis_condition_matches(
                    item,
                    text=text,
                    founding_type_ids=founding_type_ids,
                    subdomain_ids=subdomain_ids,
                    semantic_axes=semantic_axes,
                )
                for item in nested_any
                if isinstance(item, dict)
            )
        if "founding_type_any" in condition:
            expected = set(self._as_list(condition.get("founding_type_any")))
            return bool(expected & set(founding_type_ids))
        if "subdomain_any" in condition:
            expected = set(self._as_list(condition.get("subdomain_any")))
            return bool(expected & set(subdomain_ids))
        if "text_any" in condition:
            return any(str(term).lower() in text for term in self._as_list(condition.get("text_any")))
        if "text_all" in condition:
            return all(str(term).lower() in text for term in self._as_list(condition.get("text_all")))
        if "semantic_axis_any" in condition:
            spec = condition.get("semantic_axis_any") or {}
            if not isinstance(spec, dict):
                return False
            return any(
                bool(set(self._as_list(axis_ids)) & set(semantic_axes.get(str(axis_name)) or []))
                for axis_name, axis_ids in spec.items()
            )
        if "semantic_axis_all" in condition:
            spec = condition.get("semantic_axis_all") or {}
            if not isinstance(spec, dict):
                return False
            return all(
                bool(set(self._as_list(axis_ids)) & set(semantic_axes.get(str(axis_name)) or []))
                for axis_name, axis_ids in spec.items()
            )
        return False

    @staticmethod
    def _derive_space_axis_semantic_axes(user_input: str) -> Dict[str, List[str]]:
        try:
            return derive_semantic_axes(user_input or "")
        except Exception as exc:
            logger.warning(f"[SpaceClassification] semantic axes unavailable: {exc}")
            return {}

    @staticmethod
    def _resolve_founding_dimensions(
        axis_mappings: Dict[str, Any],
        founding_type: Optional[str],
    ) -> Dict[str, List[str]]:
        if not founding_type:
            return {"active_dimensions": [], "priority_dimensions": []}
        fmap = (axis_mappings.get("founding_type_to_dimensions") or {}).get("mappings") or {}
        item = fmap.get(founding_type) or {}
        return {
            "active_dimensions": SpaceClassificationService._as_list(item.get("active_dimensions")),
            "priority_dimensions": SpaceClassificationService._as_list(item.get("priority_dimensions")),
        }

    @staticmethod
    def _resolve_founding_card_weights(
        axis_mappings: Dict[str, Any],
        founding_type: Optional[str],
    ) -> Dict[str, float]:
        if not founding_type:
            return {}
        fmap = (axis_mappings.get("founding_type_to_card_weights") or {}).get("mappings") or {}
        weights = fmap.get(founding_type) or {}
        return {k: float(v) for k, v in weights.items() if isinstance(v, (int, float))}

    @staticmethod
    def _resolve_industry_card_weights(
        axis_mappings: Dict[str, Any],
        industry_domain: Optional[str],
    ) -> Dict[str, float]:
        if not industry_domain:
            return {}
        imap = (axis_mappings.get("industry_to_card_weights") or {}).get("mappings") or {}
        weights = imap.get(industry_domain) or {}
        return {k: float(v) for k, v in weights.items() if isinstance(v, (int, float))}

    def _enhance_spatial_layers(
        self,
        project_type: Optional[str],
        project_scale: Optional[str],
        spatial_layer_ids: List[str],
        evidence: Dict[str, Any],
    ) -> List[str]:
        """
        Add required action layers when project_scale under-describes a compound input.

        A vertical mixed-use villa converted from a sales center can still synthesize as
        interior_renovation because the text contains strong interior/renovation signals.
        But multi-floor reuse and structural strategy requests require building_layer.
        """
        layers = self._unique_strings(spatial_layer_ids)
        trace = evidence.get("normalization_trace") or {}
        text = " ".join(
            str(value)
            for value in (
                trace.get("original_text"),
                trace.get("normalized_text"),
                evidence.get("detector_reason"),
            )
            if value
        ).lower()

        needs_building_layer = (
            project_type == "hybrid_residential_commercial"
            and project_scale in {"interior_renovation", "interior_fitout", None}
            and (
                self._has_multifloor_signal(text)
                or any(
                    keyword in text
                    for keyword in (
                        "售楼处改造",
                        "销售中心改造",
                        "展示中心改造",
                        "地产售楼处",
                        "结构改造",
                        "竖向",
                        "整栋",
                        "整楼",
                    )
                )
            )
        )
        if needs_building_layer and "building_layer" not in layers:
            layers.append("building_layer")
        return layers

    @staticmethod
    def _has_multifloor_signal(text: str) -> bool:
        floor_markers = ("1楼", "2楼", "3楼", "4楼", "一楼", "二楼", "三楼", "四楼")
        return sum(1 for marker in floor_markers if marker in text) >= 2

    def _synthesize_project_scale(
        self,
        spatial_extents: List[str],
        lifecycles: List[str],
        project_type: Optional[str],
    ) -> Optional[str]:
        """
        spatial_extent × lifecycle 笛卡尔积 → project_scale (v1.8 §7)。

        策略:
          1. 优先用检测到的最高命中 extent × lifecycle 查 canonical 表
          2. 单边缺失时, 用 project_scale_registry.synthesis_rule.fallback_priority
          3. 全部缺失时, 按 project_type 兜底 (商业类→interior_fitout, 住宅类→interior_renovation)
        """
        scale_reg = self._load_yaml(_CONFIG_DIR / "registries" / "project_scale_registry.yaml")
        items = scale_reg.get("items") or {}
        if not items:
            return None

        canonical_map: Dict[tuple, str] = {}
        for scale_id, info in items.items():
            extent = info.get("spatial_extent")
            lifecycle = info.get("lifecycle")
            if extent and lifecycle:
                canonical_map[(extent, lifecycle)] = scale_id

        # 1. 双边命中
        if spatial_extents and lifecycles:
            for ext in spatial_extents:
                for lc in lifecycles:
                    if (ext, lc) in canonical_map:
                        return canonical_map[(ext, lc)]

        # 2. 单边命中 + fallback
        fallback = ((scale_reg.get("synthesis_rule") or {}).get("fallback_priority") or {})
        if spatial_extents and not lifecycles:
            ext = spatial_extents[0]
            lc = fallback.get(ext)
            if lc and (ext, lc) in canonical_map:
                return canonical_map[(ext, lc)]
        if lifecycles and not spatial_extents:
            lc = lifecycles[0]
            for ext in self._fallback_extents_for_lifecycle(project_type, lc):
                if (ext, lc) in canonical_map:
                    return canonical_map[(ext, lc)]

        # 3. 按 project_type 兜底
        if project_type:
            if project_type in {"commercial_dining", "commercial_retail", "commercial_office",
                                "beauty_personal_care", "popup_temporary", "brand_experience"}:
                return "interior_fitout"
            if project_type in {"personal_residential", "residential_renovation"}:
                return "interior_renovation"

        return None

    @staticmethod
    def _fallback_extents_for_lifecycle(
        project_type: Optional[str],
        lifecycle: str,
    ) -> List[str]:
        if lifecycle in {"newbuild", "adaptive_reuse"}:
            if project_type in {
                "commercial_hospitality",
                "commercial_enterprise",
                "special_function",
                "industrial_conversion",
                "urban_renewal_heritage",
                "hybrid_residential_commercial",
            }:
                return ["building", "interior"]
        if lifecycle == "temporary":
            return ["interior", "site"]
        return ["interior", "building"]

    def classify_and_activate(
        self,
        user_input: str,
        structured_requirements: Optional[Dict[str, Any]] = None,
        confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        space_classification = self.classify(user_input, structured_requirements, confirmed_tasks)
        return {
            "space_classification": space_classification,
            "project_definition_activation_pack": self.build_activation_pack(space_classification),
        }

    @staticmethod
    def _extract_structured_project_type(structured_requirements: Dict[str, Any]) -> Optional[str]:
        value = structured_requirements.get("project_type")
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, dict):
            for key in ("primary", "project_type", "type"):
                candidate = value.get(key)
                if isinstance(candidate, str) and candidate.strip():
                    return candidate.strip()
        return None

    def _resolve_boundary_primary_project_type(
        self,
        user_input: str,
        detector_details: Dict[str, Any],
        current_project_type: str,
    ) -> Optional[Dict[str, Any]]:
        """Apply boundary primary-preference rules before finalizing the type.

        The detector ranks keyword candidates. Boundary cases decide the primary
        container when one candidate is the spatial object and another is only a
        support condition, such as a family home with medical-grade air support.
        """
        cases = self._boundary_cases.get("cases") or {}
        if not cases:
            return None

        text = (user_input or "").lower()
        detector_boundary_case_ids = {
            str(case_id) for case_id in self._as_list(detector_details.get("boundary_case_ids"))
        }
        candidate_types = self._detector_candidate_type_ids(detector_details)
        candidate_types.add(current_project_type)

        best_resolution: Optional[Dict[str, Any]] = None
        best_score = 0

        for case_id, case in cases.items():
            if not isinstance(case, dict):
                continue
            types = [str(item) for item in self._as_list(case.get("types")) if item]
            if current_project_type not in types:
                continue
            preference_rules = case.get("primary_preference_rules") or {}
            if not isinstance(preference_rules, dict):
                continue
            allow_boundary_declared_candidate = bool(
                case.get("allow_primary_from_boundary_signals")
            )
            min_boundary_signal_hits = int(case.get("minimum_primary_signal_hits") or 2)
            boundary_hits = self._boundary_keyword_hits(text, case)
            if case_id not in detector_boundary_case_ids and not boundary_hits:
                continue

            current_hits = self._preference_signal_hits(
                text,
                preference_rules.get(current_project_type),
            )
            for candidate_type in types:
                if candidate_type == current_project_type:
                    continue
                candidate_hits = self._preference_signal_hits(
                    text,
                    preference_rules.get(candidate_type),
                )
                if not candidate_hits:
                    continue
                candidate_was_detected = candidate_type in candidate_types
                if (
                    not candidate_was_detected
                    and (
                        not allow_boundary_declared_candidate
                        or len(candidate_hits) < min_boundary_signal_hits
                    )
                ):
                    continue
                if current_hits and len(candidate_hits) <= len(current_hits):
                    continue
                score = len(candidate_hits) - len(current_hits)
                if score <= best_score:
                    continue
                best_score = score
                best_resolution = {
                    "case_id": case_id,
                    "from_project_type": current_project_type,
                    "project_type": candidate_type,
                    "matched_signals": candidate_hits,
                    "suppressed_current_signals": current_hits,
                    "boundary_keyword_hits": boundary_hits,
                    "candidate_was_detected": candidate_was_detected,
                    "reason": "boundary_primary_preference",
                }

        return best_resolution

    @staticmethod
    def _boundary_keyword_hits(text: str, case: Dict[str, Any]) -> List[str]:
        hits: List[str] = []
        for raw_term in case.get("boundary_keywords") or []:
            term = str(raw_term).lower().strip()
            if term and term in text:
                hits.append(str(raw_term))
        return list(dict.fromkeys(hits))

    @staticmethod
    def _detector_candidate_type_ids(detector_details: Dict[str, Any]) -> set:
        ids = set()
        for key in ("all_matches", "secondary_candidates", "competing_candidates"):
            for item in detector_details.get(key) or []:
                if not isinstance(item, dict):
                    continue
                value = item.get("type_id") or item.get("project_type")
                if value:
                    ids.add(str(value))
        for item in detector_details.get("industry_candidates") or []:
            if not isinstance(item, dict):
                continue
            value = item.get("project_type")
            if value:
                ids.add(str(value))
        return ids

    @staticmethod
    def _preference_signal_hits(text: str, rule: Any) -> List[str]:
        if not isinstance(rule, dict):
            return []
        hits: List[str] = []
        for raw_term in rule.get("strong_signals") or []:
            term = str(raw_term).lower().strip()
            if not term or term not in text:
                continue
            if SpaceClassificationService._term_has_non_negated_hit(text, term):
                hits.append(str(raw_term))
        return list(dict.fromkeys(hits))

    @staticmethod
    def _term_has_non_negated_hit(text: str, term: str) -> bool:
        start = 0
        while True:
            index = text.find(term, start)
            if index < 0:
                return False
            if not SpaceClassificationService._term_hit_is_negated(text, index, len(term)):
                return True
            start = index + len(term)

    @staticmethod
    def _term_hit_is_negated(text: str, index: int, term_len: int) -> bool:
        window = text[max(0, index - 10): index + term_len + 4]
        negators = (
            "不是",
            "不能",
            "不要",
            "不应",
            "不该",
            "不宜",
            "避免",
            "不像",
            "非",
            "别像",
        )
        return any(negator in window for negator in negators)

    @staticmethod
    def _is_residential_privacy_conflict_context(user_input: str) -> bool:
        """Detect residential co-living privacy conflicts without adding broad keywords."""
        text = (user_input or "").lower()
        try:
            semantic_axes = derive_semantic_axes(user_input or "")
        except Exception:
            semantic_axes = {}

        domains = set(semantic_axes.get("space_domains") or [])
        subjects = set(semantic_axes.get("subject_profiles") or [])
        constraints = set(semantic_axes.get("critical_constraints") or [])
        drivers = set(semantic_axes.get("spatial_design_drivers") or [])

        residential_signal = "residential" in domains or any(
            keyword in text
            for keyword in ("家庭", "家中", "同一屋檐", "主卧", "卧室", "儿童房", "住宅")
        )
        family_relation_signal = bool(subjects & {"family_multi_generation", "children"}) or any(
            keyword in text
            for keyword in ("再婚家庭", "无血缘", "青春期", "家庭关系", "家人", "孩子")
        )
        privacy_boundary_signal = (
            "security_privacy" in constraints
            or "family_privacy_boundary" in drivers
            or any(
                keyword in text
                for keyword in ("隐私", "私密", "独立性", "心理安全边界", "冲突缓冲", "公共交流区")
            )
        )
        public_institution_signal = any(
            keyword in text
            for keyword in ("学校", "幼儿园", "托育", "社区中心", "公共服务", "活动中心", "儿童乐园", "培训中心")
        )

        return residential_signal and family_relation_signal and privacy_boundary_signal and not public_institution_signal

    @staticmethod
    def _is_extreme_resilience_prototype_context(user_input: str) -> bool:
        """Detect future / underground / extreme-environment resilience prototypes."""
        text = (user_input or "").lower()
        try:
            semantic_axes = derive_semantic_axes(user_input or "")
        except Exception:
            semantic_axes = {}

        drivers = set(semantic_axes.get("spatial_design_drivers") or [])
        domains = set(semantic_axes.get("space_domains") or [])
        constraints = set(semantic_axes.get("critical_constraints") or [])

        resilience_driver = "extreme_resilience_prototype" in drivers
        technical_signal = "technical_special" in domains or bool(
            constraints & {"mep_climate", "fire_structure"}
        )
        underground_or_extreme_signal = any(
            keyword in text
            for keyword in (
                "地下居住",
                "地下生活",
                "地下生活社区",
                "极端气候",
                "极端地质",
                "火山活跃带",
                "光井",
                "空气循环",
                "生命支持",
            )
        )
        weak_healthcare_only_signal = not any(
            keyword in text
            for keyword in ("医院", "诊所", "康养中心", "养老院", "康复", "治疗", "护理")
        )

        return (
            (resilience_driver or (technical_signal and underground_or_extreme_signal))
            and underground_or_extreme_signal
            and weak_healthcare_only_signal
        )

    @staticmethod
    def _is_high_constraint_prototype_context(user_input: str) -> bool:
        """Detect cross-type prototype spaces driven by energy, climate, or material constraints."""
        text = (user_input or "").lower()
        try:
            semantic_axes = derive_semantic_axes(user_input or "")
        except Exception:
            semantic_axes = {}

        drivers = set(semantic_axes.get("spatial_design_drivers") or [])
        constraints = set(semantic_axes.get("critical_constraints") or [])
        intents = set(semantic_axes.get("input_intents") or [])
        domains = set(semantic_axes.get("space_domains") or [])
        resources = set(semantic_axes.get("site_resources") or [])

        sustainability_signal = (
            "material_sustainability_value" in drivers
            or any(
                keyword in text
                for keyword in (
                    "零碳",
                    "后碳",
                    "可持续",
                    "碳足迹",
                    "储能",
                    "脱离化石能源",
                    "可追溯",
                    "可回收",
                    "能源使用可视化",
                )
            )
        )
        resilience_signal = (
            "mep_climate" in constraints
            or "technical_special" in domains
            or "mountain_nature" in resources
            or any(
                keyword in text
                for keyword in (
                    "极寒",
                    "极端",
                    "严酷自然环境",
                    "保温系统",
                    "光照补偿",
                    "生命支持",
                    "气候适应",
                )
            )
        )
        prototype_signal = (
            "technical_solution" in intents
            or any(
                keyword in text
                for keyword in (
                    "样板房",
                    "样板屋",
                    "示范",
                    "原型",
                    "实验",
                    "未来世代",
                    "生活方式",
                    "驻留中心",
                )
            )
        )

        return prototype_signal and (sustainability_signal or resilience_signal)

    @staticmethod
    def _has_structured_design_context(user_input: str) -> bool:
        """Detect inputs that are specific enough for a basic conditional design framework."""
        text = (user_input or "").lower()
        try:
            semantic_axes = derive_semantic_axes(user_input or "")
        except Exception:
            semantic_axes = {}

        intents = set(semantic_axes.get("input_intents") or [])
        complete_design_intent = "complete_design_framework" in intents or any(
            keyword in text
            for keyword in (
                "完整设计",
                "完整室内设计",
                "完整设计框架",
                "完整设计方案",
                "完整室内设计概念",
            )
        )
        semantic_anchor_count = sum(
            1
            for key in (
                "space_domains",
                "subject_profiles",
                "founding_drivers",
                "spatial_design_drivers",
                "site_resources",
                "lifecycle",
                "critical_constraints",
                "is_complex_project",
            )
            if semantic_axes.get(key)
        )
        design_detail_signal = any(
            keyword in text
            for keyword in (
                "情绪修复",
                "低成本实施",
                "公共厨房",
                "讨论区",
                "可变性",
                "可移动",
                "快速调整",
                "模块化",
                "拍摄",
                "直播",
                "社交展示",
                "品牌故事",
                "产品陈列",
                "销售",
                "动线",
                "灯光",
                "材料",
            )
        )
        concrete_space_carrier = any(
            keyword in text
            for keyword in (
                "主卧",
                "卧室",
                "宿舍",
                "公寓",
                "住宅",
                "别墅",
                "生活空间",
                "体验馆",
                "展示馆",
                "展馆",
                "会所",
                "中心",
                "社区",
                "店",
                "空间",
            )
        )

        return (
            complete_design_intent
            and concrete_space_carrier
            and (semantic_anchor_count >= 2 or (semantic_anchor_count >= 1 and design_detail_signal))
        )

    @staticmethod
    def _fallback_project_type(
        user_input: str,
        detector_details: Dict[str, Any],
        detected_project_type: Optional[str],
    ) -> Optional[str]:
        """Small, conservative corrections around known detector blind spots."""
        text = (user_input or "").lower()
        specialty_tag = detector_details.get("specialty_tag")
        detector_confidence = float(detector_details.get("confidence") or 0.0)

        if detected_project_type == "hybrid_residential_commercial" and detector_confidence >= 0.60:
            return None

        if (
            SpaceClassificationService._is_residential_privacy_conflict_context(user_input)
            and detector_confidence < 0.60
            and detected_project_type in {None, "children_family", "healthcare_wellness", "community_public"}
        ):
            return "personal_residential"

        if (
            SpaceClassificationService._is_extreme_resilience_prototype_context(user_input)
            and detector_confidence < 0.60
            and detected_project_type in {
                None,
                "healthcare_wellness",
                "community_public",
                "landscape_outdoor",
                "public_cultural",
            }
        ):
            return "special_function"

        private_home_container = any(
            keyword in text
            for keyword in (
                "家中",
                "家里",
                "自家",
                "主卧",
                "卧室",
                "家庭住宅",
                "住宅实验室",
                "居住4个月",
                "归家",
            )
        )
        home_inner_function = any(
            keyword in text
            for keyword in (
                "茶室",
                "冥想空间",
                "正念空间",
                "瑜伽",
                "家庭健身",
                "健身功能",
                "实验室",
                "佛堂",
            )
        )
        if (
            private_home_container
            and home_inner_function
            and detected_project_type
            in {
                None,
                "special_function",
                "commercial_dining",
                "healthcare_wellness",
                "religious_spiritual",
            }
        ):
            return "personal_residential"

        enterprise_context = any(
            keyword in text
            for keyword in ("公司", "企业", "集团", "投资人", "客户接待", "接待", "会客")
        )
        research_context = any(
            keyword in text
            for keyword in ("实验室", "研发", "洁净区", "技术", "研究中心", "极地研究", "科研")
        )
        generic_showcase_context = any(
            keyword in text
            for keyword in ("展示中心", "展示馆", "展厅", "体验中心")
        )
        if enterprise_context and research_context and generic_showcase_context:
            if detected_project_type in {
                None,
                "real_estate_showcase",
                "public_cultural",
                "commercial_office",
            }:
                return "commercial_enterprise"

        creator_context = any(
            keyword in text
            for keyword in ("up主", "博主", "主播", "kol", "mcn", "内容创作", "二次元")
        )
        media_activity_context = any(
            keyword in text
            for keyword in ("拍摄", "直播", "录制", "镜头", "背景可替换", "布景")
        )
        if creator_context and media_activity_context:
            if detected_project_type in {None, "commercial_office", "brand_experience"}:
                return "digital_media_studio"

        institutional_context = any(
            keyword in text
            for keyword in ("银行", "金融机构", "跨国", "企业", "公司", "集团")
        )
        private_reception_context = any(
            keyword in text
            for keyword in ("私人会客", "会客空间", "高净值", "vip", "权力象征", "客户接待")
        )
        if institutional_context and private_reception_context:
            if detected_project_type in {
                None,
                "children_family",
                "personal_residential",
                "commercial_office",
                "commercial_retail",
            }:
                return "commercial_enterprise"

        if specialty_tag in {"dental", "tcm", "age_friendly", "elderly_care", "aesthetic_medicine"}:
            return "healthcare_wellness"

        if any(keyword in text for keyword in ("牙科", "口腔", "中医", "诊所", "康复", "适老", "养老")):
            return "healthcare_wellness"

        if any(keyword in text for keyword in ("国际贸易会客中心", "会客中心", "接待中心")):
            if detected_project_type in {None, "commercial_office", "public_cultural"}:
                return "commercial_enterprise"

        if any(
            keyword in text
            for keyword in (
                "ai伦理研究中心",
                "研究中心",
                "研究与生活中心",
                "极地研究",
                "实验室",
                "实验空间",
            )
        ):
            if detected_project_type in {None, "commercial_office", "public_cultural", "educational_facility"}:
                return "special_function"

        brand_keywords = ("品牌体验", "品牌空间", "体验中心", "旗舰店", "品牌展示")
        if any(keyword in text for keyword in brand_keywords):
            if detected_project_type in {None, "commercial_enterprise", "commercial_retail"}:
                return "brand_experience"

        residential_container_signal = any(
            keyword in text
            for keyword in (
                "住宅",
                "别墅",
                "公寓",
                "大平层",
                "家中",
                "居住",
                "主卧",
                "卧室",
                "家庭",
            )
        )
        dedicated_religious_signal = any(
            keyword in text
            for keyword in (
                "宗教文化研究机构",
                "跨信仰",
                "不同宗教",
                "宗教背景",
                "宗教建筑",
                "寺庙",
                "寺院",
                "道观",
                "教堂",
                "礼拜堂",
                "清真寺",
                "神殿",
                "祠堂",
                "修道院",
                "殡仪馆",
                "火葬场",
                "公墓",
                "陵墓",
                "墓园",
            )
        )
        dedicated_spiritual_place_signal = any(
            keyword in text
            for keyword in (
                "私人冥想中心",
                "冥想中心",
                "静修中心",
                "禅修中心",
                "修行中心",
                "精神场所",
            )
        )
        standalone_buddhist_room_signal = "佛堂" in text and not residential_container_signal
        if (
            dedicated_religious_signal
            or dedicated_spiritual_place_signal
            or standalone_buddhist_room_signal
        ):
            return "religious_spiritual"

        return None

    @staticmethod
    def _confidence_with_fallback_floor(
        confidence: Any,
        user_input: str,
        project_type: Optional[str],
        fallback_project_type: Optional[str],
        detected_project_type: Optional[str],
    ) -> float:
        value = float(confidence or 0.0)
        text = (user_input or "").lower()

        site_scale_types = {
            "landscape_outdoor",
            "urban_renewal_market",
            "urban_renewal_heritage",
            "community_public",
            "rural_construction",
        }
        site_scale_terms = (
            "新区",
            "地块",
            "用地",
            "片区",
            "街区",
            "厂区",
            "园区",
            "社区",
            "聚落",
            "工坊聚落",
            "小镇",
            "乡镇",
            "城市核心区",
            "城郊",
            "滨海",
            "河岸",
            "长廊",
        )
        planning_intent_terms = (
            "规划",
            "开发",
            "建设",
            "打造",
            "改造",
            "整体更新",
            "转型",
            "示范区",
            "示范社区",
            "复合型社区",
            "产业园",
            "产业孵化",
            "前期定位",
            "战略定位",
            "功能混合",
            "产品线",
            "土地价值",
            "公共空间",
            "公共节点",
            "景观系统",
            "景观整合",
        )
        if (
            project_type in site_scale_types
            and any(keyword in text for keyword in site_scale_terms)
            and any(keyword in text for keyword in planning_intent_terms)
        ):
            value = max(value, 0.58)

        high_constraint_prototype_types = {
            "real_estate_showcase",
            "public_cultural",
            "commercial_hospitality",
            "special_function",
            "community_public",
            "educational_facility",
            "landscape_outdoor",
        }
        if (
            project_type in high_constraint_prototype_types
            and SpaceClassificationService._is_high_constraint_prototype_context(user_input)
        ):
            value = max(value, 0.58)

        if (
            project_type
            and value >= 0.40
            and SpaceClassificationService._has_structured_design_context(user_input)
        ):
            value = max(value, 0.56)

        if fallback_project_type:
            floors = {
                "healthcare_wellness": 0.65,
                "commercial_enterprise": 0.62,
                "personal_residential": 0.62,
                "special_function": 0.62,
                "brand_experience": 0.60,
                "digital_media_studio": 0.60,
                "religious_spiritual": 0.60,
            }
            value = max(value, floors.get(fallback_project_type, 0.56))

        if (
            not fallback_project_type
            and project_type == "commercial_office"
            and detected_project_type == "commercial_office"
            and any(keyword in text for keyword in ("公司", "集团", "机构", "团队"))
            and any(keyword in text for keyword in ("办公空间", "办公室", "办公", "工作场所"))
            and any(keyword in text for keyword in ("员工", "协作", "专注力", "组织", "信息过载"))
        ):
            value = max(value, 0.58)

        if (
            project_type == "commercial_enterprise"
            and any(keyword in text for keyword in ("企业", "公司", "集团"))
            and any(keyword in text for keyword in ("展示馆", "展示中心", "展厅", "体验中心"))
            and any(keyword in text for keyword in ("技术", "能源", "研发", "转型", "科普"))
        ):
            value = max(value, 0.58)

        if (
            project_type == "automotive_showroom"
            and any(keyword in text for keyword in ("汽车", "电动车", "nio house", "蔚来"))
            and any(keyword in text for keyword in ("体验", "品牌", "会员", "社交", "展示"))
        ):
            value = max(value, 0.58)

        return value

    def _unknown_result(self, user_input: str, detector_details: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "schema_version": "space_classification.v1",
            "status": "needs_input",
            "primary_bucket": "general",
            "parent_type": None,
            "project_type": None,
            "project_type_name": "未识别",
            "confidence": 0.0,
            "confidence_level": "low",
            "specialty_tags": [],
            "secondary_candidates": [],
            "secondary_types": [],
            "runtime_modifiers": self._extract_runtime_modifiers(user_input, {}),
            "industry_domain": None,
            "industry_domain_name": None,
            "industry_profile_status": "unspecified",
            "industry_candidates": detector_details.get("industry_candidates", []),
            "needs_industry_clarification": True,
            "profession_context_ids": [],
            "ambiguity": {
                "is_ambiguous": True,
                "ambiguity_type": "unclassified",
                "clarification_questions": ["这个空间主要服务什么活动、谁使用、以什么标准判断成功？"],
            },
            "clarification_questions": [
                "这个空间主要服务什么活动、谁使用、以什么标准判断成功？",
                "请补充行业语境（例如法律服务、医疗健康、科技研发、零售消费等）。",
            ],
            "routing": self._build_routing(None, "general", self._get_profile(None)),
            "space_axis": self._build_space_axis(
                user_input=user_input,
                project_type=None,
                parent_type=None,
                detector_details=detector_details,
                confidence=0.0,
                coverage_gap=True,
            ),
            "coverage_gap": True,
            "ontology_unmatched": ["project_type_unmatched", "industry_domain_unspecified"],
            "knowledge_gap_ticket": {
                "gap_type": "unclassified_space_input",
                "proposed_parent_type": None,
                "industry_domain": None,
                "profile_status": "unspecified",
                "action": "collect_more_input",
            },
            "evidence": {
                "detector_reason": detector_details.get("reason", ""),
                "source": "project_type_detector",
                "normalization_trace": (
                    detector_details.get("normalization_trace")
                    or (detector_details.get("evidence") or {}).get("normalization_trace")
                    or {}
                ),
                "_detector_full": {
                    "subdomain_signals": detector_details.get("subdomain_signals", []),
                    "scale_signals": detector_details.get("scale_signals", {}),
                    "founding_type_candidates": detector_details.get("founding_type_candidates", []),
                    "industry_candidates": detector_details.get("industry_candidates", []),
                    "industry_profile": detector_details.get("industry_profile", {}),
                    "input_fingerprint": detector_details.get("input_fingerprint"),
                },
            },
            "freeze_state": {
                "classification_frozen": False,
                "can_reclassify_until": "Node3",
            },
        }

    def _get_profile(self, project_type: Optional[str]) -> Dict[str, Any]:
        defaults = deepcopy(self._profiles.get("defaults", {}))
        profile = deepcopy((self._profiles.get("profiles") or {}).get(project_type or "", {}))
        return self._deep_merge(defaults, profile)

    @staticmethod
    def _get_type_method_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
        return deepcopy(profile.get("type_method_profile") or profile.get("business_method_profile") or {})

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        result = deepcopy(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = SpaceClassificationService._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    @staticmethod
    def _canonical_bucket(parent_type: str) -> str:
        return {
            "residential": "residential",
            "hospitality": "hospitality",
            "office": "office_workplace",
            "retail": "retail_dining",
            "leisure": "culture_education",
            "education": "culture_education",
            "healthcare": "healthcare_wellness",
            "public": "public_civic",
            "industrial": "industrial_production",
            "urban_renewal": "renewal_mixed_use",
            "outdoor": "landscape_outdoor",
            "special": "religious_contemplative",
            "general": "general",
        }.get(parent_type or "general", parent_type or "general")

    @staticmethod
    def _confidence_level(confidence: Any) -> str:
        try:
            value = float(confidence or 0.0)
        except (TypeError, ValueError):
            value = 0.0
        if value >= 0.80:
            return "high"
        if value >= 0.55:
            return "medium"
        return "low"

    @staticmethod
    def _as_list(value: Any) -> List[Any]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return value
        return [value]

    def _extract_runtime_modifiers(
        self,
        user_input: str,
        structured_requirements: Dict[str, Any],
    ) -> Dict[str, List[str]]:
        text = self._combined_text(user_input, structured_requirements)
        modifiers: Dict[str, List[str]] = {}
        axes = (self._modifier_rules.get("modifier_axes") or {})
        for axis, values in axes.items():
            for value, keywords in (values or {}).items():
                if any(str(keyword).lower() in text for keyword in keywords or []):
                    modifiers.setdefault(axis, []).append(value)
        return modifiers

    def _extract_secondary_types(self, user_input: str, project_type: Optional[str]) -> List[Dict[str, Any]]:
        text = (user_input or "").lower()
        secondary: List[Dict[str, Any]] = []
        triggers = self._modifier_rules.get("secondary_type_triggers") or {}
        for type_id, rule in triggers.items():
            if type_id == project_type:
                continue
            keywords = rule.get("keywords") or []
            if any(str(keyword).lower() in text for keyword in keywords):
                secondary.append(
                    {
                        "type": type_id,
                        "role": rule.get("role", "supporting_function"),
                        "confidence": 0.65,
                        "weight": None,
                        "weight_status": "unknown",
                        "reason": "keyword_trigger",
                    }
                )
        return secondary

    def _build_secondary_candidates(
        self,
        detector_details: Dict[str, Any],
        secondary_types: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []
        secondary_type = detector_details.get("secondary_type")
        if secondary_type:
            candidates.append(
                {
                    "project_type": secondary_type,
                    "project_type_name": detector_details.get("secondary_type_name") or get_type_label(secondary_type),
                    "score": None,
                    "reason": "detector_top2",
                }
            )
        for item in secondary_types:
            type_id = item.get("type")
            if type_id and not any(candidate.get("project_type") == type_id for candidate in candidates):
                candidates.append(
                    {
                        "project_type": type_id,
                        "project_type_name": get_type_label(type_id) if type_id in PARENT_TYPE_MAP else type_id,
                        "score": item.get("confidence"),
                        "reason": item.get("reason", "secondary_type_trigger"),
                    }
                )
        return candidates

    def _build_ambiguity(
        self,
        project_type: str,
        secondary_candidates: List[Dict[str, Any]],
        user_input: str,
        industry_domain: Optional[str],
        industry_candidates: List[Dict[str, Any]],
        boundary_case_ids: Optional[List[str]] = None,
        founding_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        cases = self._boundary_cases.get("cases") or {}
        candidate_types = [item.get("project_type") for item in secondary_candidates if item.get("project_type")]
        text = (user_input or "").lower()
        candidate_industries = [
            c.get("industry_id")
            for c in industry_candidates[:3]
            if isinstance(c, dict) and c.get("industry_id")
        ]

        for case_id in boundary_case_ids or []:
            case = cases.get(case_id)
            if not isinstance(case, dict):
                continue
            types = case.get("types") or []
            type_scope = case.get("project_type_scope")
            if types and project_type not in types:
                continue
            if type_scope and type_scope != project_type:
                continue
            return {
                "is_ambiguous": True,
                "ambiguity_type": "boundary_case",
                "case_id": case_id,
                "pair": types,
                "decision_axis": case.get("decision_axis", []),
                "clarification_questions": case.get("clarification_questions", [])[:2],
                "risk_if_wrong": case.get("risks", {}),
            }

        founding_conflict = self._build_founding_project_conflict(project_type, founding_type)
        if founding_conflict:
            return founding_conflict

        # 收集所有命中的边界案例，按证据强度评分（不再 first-match-wins）
        best_case_id: Optional[str] = None
        best_case: Optional[Dict[str, Any]] = None
        best_score: int = 0

        for case_id, case in cases.items():
            types = case.get("types") or []
            if project_type not in types:
                continue
            pair_hit = any(candidate in types for candidate in candidate_types)
            kw_hits = sum(
                1 for kw in (case.get("risk_keywords") or []) if str(kw).lower() in text
            )
            if not pair_hit and kw_hits == 0:
                continue
            # pair_hit 计 3 分（直接类型碰撞是更强证据），每个关键词命中计 1 分
            score = kw_hits + (3 if pair_hit else 0)
            if score > best_score:
                best_score = score
                best_case_id = case_id
                best_case = case

        # 行业冲突边界 (同一 project_type 下, 不同 industry_domain)
        if industry_domain:
            for case_id, case in cases.items():
                type_scope = case.get("project_type_scope")
                if type_scope and type_scope != project_type:
                    continue
                industry_pairs = case.get("industry_pairs") or []
                if not industry_pairs:
                    continue
                has_primary = False
                has_competing = False
                for pair in industry_pairs:
                    if not isinstance(pair, list) or len(pair) != 2:
                        continue
                    if industry_domain in pair:
                        has_primary = True
                    if any(ind in pair for ind in candidate_industries if ind != industry_domain):
                        has_competing = True
                kw_hits = sum(
                    1 for kw in (case.get("risk_keywords") or []) if str(kw).lower() in text
                )
                if not has_primary and not has_competing and kw_hits == 0:
                    continue
                score = kw_hits + (3 if has_primary and has_competing else 0)
                if score > best_score:
                    best_score = score
                    best_case_id = case_id
                    best_case = case

        if best_case_id and best_case:
            return {
                "is_ambiguous": True,
                "ambiguity_type": "boundary_case",
                "case_id": best_case_id,
                "pair": best_case.get("types", []),
                "decision_axis": best_case.get("decision_axis", []),
                "clarification_questions": best_case.get("clarification_questions", [])[:2],
                "risk_if_wrong": best_case.get("risks", {}),
            }

        return {
            "is_ambiguous": False,
            "ambiguity_type": None,
            "clarification_questions": [],
        }

    def _build_founding_project_conflict(
        self,
        project_type: str,
        founding_type: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        if not founding_type:
            return None
        axis_mappings = self._master_index.get("axis_mappings", {}) or {}
        conflict_rules = (
            (axis_mappings.get("founding_x_project_conflicts") or {}).get("rules") or []
        )
        for rule in conflict_rules:
            if not isinstance(rule, dict):
                continue
            if rule.get("founding_type") != founding_type:
                continue
            if project_type not in self._as_list(rule.get("project_type")):
                continue
            return {
                "is_ambiguous": True,
                "ambiguity_type": "founding_project_conflict",
                "case_id": rule.get("boundary_case_id") or "founding_project_conflict",
                "pair": [founding_type, project_type],
                "decision_axis": [
                    "project_motive",
                    "primary_user",
                    "success_standard",
                    "operation_logic",
                ],
                "clarification_questions": [
                    "这个项目的主导动因是自用/家庭生活，还是对外经营/商业运营？",
                    "最终成功标准更偏日常使用舒适，还是客流、营收、转化和运营效率？",
                ],
                "risk_if_wrong": {
                    "as_project_type_only": "会只按空间业态出方案，忽略项目成立动因和成功标准。",
                    "as_founding_type_only": "会只按动因理解项目，低估空间类型的规范、运营和功能边界。",
                },
            }
        return None

    def _build_routing(
        self,
        project_type: Optional[str],
        parent_type: str,
        profile: Dict[str, Any],
    ) -> Dict[str, Any]:
        ontology_framework = profile.get("ontology_framework")
        if project_type and project_type in DETECTOR_TO_ONTOLOGY:
            ontology_framework = DETECTOR_TO_ONTOLOGY[project_type]
        return {
            "ontology_framework": ontology_framework or "meta_framework",
            "questionnaire_profile": profile.get("questionnaire_profile") or parent_type or "general",
            "floorplan_profile": profile.get("floorplan_profile", "general_floorplan_reasoning"),
            "visual_prompt_profile": profile.get("visual_prompt_profile", "general_visual_profile"),
            "deliverable_profile": profile.get("deliverable_profile", "general_deliverable_profile"),
            "deliverable_label": profile.get("display_label") or (get_type_label(project_type) if project_type else "项目"),
            "expert_team_profile": None,
        }

    @staticmethod
    def _extract_profession_context_ids(
        user_input: str,
        structured_requirements: Dict[str, Any],
    ) -> List[str]:
        """轻量提取职业语境，优先结构化输入，次选关键词兜底。"""
        explicit = structured_requirements.get("profession_context_ids")
        if isinstance(explicit, list):
            values = [str(v).strip() for v in explicit if str(v).strip()]
            if values:
                return list(dict.fromkeys(values))

        explicit_single = structured_requirements.get("profession_context")
        if isinstance(explicit_single, str) and explicit_single.strip():
            return [explicit_single.strip()]

        text = (user_input or "").lower()
        keyword_map = {
            "lawyer": ["律师", "律所", "法律顾问"],
            "algorithm_engineer": ["算法工程师", "算法", "模型训练"],
            "doctor": ["医生", "诊疗", "临床"],
            "teacher": ["老师", "教学", "授课"],
            "streamer_creator": ["主播", "直播", "内容创作"],
            "investment_partner": ["合伙人", "投行", "投资人"],
        }
        hits: List[str] = []
        for ctx, kws in keyword_map.items():
            if any(kw in text for kw in kws):
                hits.append(ctx)
        return list(dict.fromkeys(hits))

    def _build_industry_clarification_questions(
        self,
        industry_domain: Optional[str],
        profile_status: str,
        needs_industry_clarification: bool,
    ) -> List[str]:
        if not needs_industry_clarification:
            return []

        if not industry_domain:
            return [
                "这个项目服务于哪个行业语境？例如法律服务、医疗健康、科技研发、教育培训或零售消费。",
                "该行业的核心运营目标是什么（效率、信任、转化、疗愈、展示等）？",
            ]

        maturity = self._resolve_industry_maturity(industry_domain, profile_status)
        if maturity in {"L0_unknown", "unknown_detected", "unspecified"}:
            return [
                "已检测到行业线索，但资料不足。请补充核心业务行为（咨询、试用、诊疗、展示、交付等）。",
                "请补充关键约束（隐私、合规、安全、设备、噪声、温控等）。",
            ]

        return []

    def _resolve_industry_maturity(self, industry_domain: str, fallback: str) -> str:
        items = (self._industry_registry.get("items") or {})
        item = items.get(industry_domain) or {}
        level = item.get("maturity_level")
        if isinstance(level, str) and level.strip():
            return level.strip()
        return fallback

    @staticmethod
    def _merge_knowledge_binding(
        binding: Dict[str, Any],
        runtime_modifiers: Dict[str, List[str]],
        secondary_types: List[Dict[str, Any]],
        industry_domain: Optional[str],
        profession_context_ids: List[str],
    ) -> Dict[str, Any]:
        merged = deepcopy(binding or {})
        tags = list(merged.get("search_tags", []) or [])
        for values in runtime_modifiers.values():
            tags.extend(values)
        for item in secondary_types:
            if item.get("type"):
                tags.append(item["type"])
        if industry_domain:
            tags.append(industry_domain)
        tags.extend([ctx for ctx in profession_context_ids if ctx])
        merged["search_tags"] = sorted({str(tag) for tag in tags if tag})
        return merged

    @staticmethod
    def _combined_text(user_input: str, structured_requirements: Dict[str, Any]) -> str:
        parts = [user_input or ""]
        try:
            parts.append(json.dumps(structured_requirements or {}, ensure_ascii=False))
        except Exception:
            parts.append(str(structured_requirements or ""))
        return " ".join(parts).lower()


def classify_space(
    user_input: str,
    structured_requirements: Optional[Dict[str, Any]] = None,
    confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Convenience wrapper for callers that only need the classification object."""
    return SpaceClassificationService().classify(user_input, structured_requirements, confirmed_tasks)


def build_project_definition_activation_pack(
    user_input: str,
    structured_requirements: Optional[Dict[str, Any]] = None,
    confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Convenience wrapper returning both classification and activation pack."""
    return SpaceClassificationService().classify_and_activate(user_input, structured_requirements, confirmed_tasks)
