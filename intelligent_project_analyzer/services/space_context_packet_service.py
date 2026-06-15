"""Build the v3.3 context packet for space classification.

This service is an adapter layer around the existing v1.8 classification and
activation-pack pipeline. It does not mutate registries and does not replace the
older payloads; it gives downstream consumers a stable v3.3 container.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml
from loguru import logger

from .governed_knowledge_retrieval import GovernedKnowledgeRetrievalService
from .knowledge_asset_runtime import resolve_governed_knowledge_cards
from .missing_slot_service import MissingSlotService
from .retrieval_planner import RetrievalPlanner
from .space_classification_service import SpaceClassificationService


_ROOT = Path(__file__).resolve().parent.parent
_KB = _ROOT / "knowledge_base"
_ACTIVATION_PACK_DIR = _KB / "activation_packs"


class SpaceContextPacketValidationError(ValueError):
    """Raised when a context_packet does not satisfy the v3.3 runtime contract."""


def validate_context_packet(packet: Dict[str, Any]) -> None:
    """Validate the stable v3.3 sections expected by runtime consumers."""
    allowed_missing_slot_actions = {
        "certainty_ceiling",
        "option_menu",
        "branch_answer_plus_followup",
    }
    allowed_missing_slot_severities = {"critical", "high", "medium", "low"}
    allowed_missing_slot_priorities = {"P1", "P2", "P3"}
    allowed_discipline_coverages = {"covered", "partial", "out_of_scope"}

    required_sections = [
        "schema_version",
        "classification",
        "context_vector",
        "subject_axis",
        "meta_context_drivers",
        "output_mode",
        "discipline_switch",
        "missing_slots",
        "ontology_binding",
        "knowledge_binding",
        "activation_pack_coordination",
    ]
    missing = [section for section in required_sections if section not in packet]
    if missing:
        raise SpaceContextPacketValidationError(f"missing context_packet sections: {', '.join(missing)}")

    if packet.get("schema_version") != "context_packet.v3.3":
        raise SpaceContextPacketValidationError("schema_version must be context_packet.v3.3")

    classification = packet.get("classification") or {}
    if not isinstance(classification, dict):
        raise SpaceContextPacketValidationError("classification must be an object")
    for key in ("project_type_id", "subdomain", "confidence"):
        if key not in classification:
            raise SpaceContextPacketValidationError(f"classification.{key} is required")

    output_mode = packet.get("output_mode") or {}
    if not output_mode.get("primary_output_mode"):
        raise SpaceContextPacketValidationError("output_mode.primary_output_mode is required")

    discipline_switch = packet.get("discipline_switch") or {}
    if "required_disciplines" not in discipline_switch:
        raise SpaceContextPacketValidationError("discipline_switch.required_disciplines is required")
    if discipline_switch.get("current_coverage") not in allowed_discipline_coverages:
        raise SpaceContextPacketValidationError(
            "discipline_switch.current_coverage must be one of: "
            f"{', '.join(sorted(allowed_discipline_coverages))}"
        )

    missing_slots = packet.get("missing_slots")
    if not isinstance(missing_slots, list):
        raise SpaceContextPacketValidationError("missing_slots must be a list")
    for index, slot in enumerate(missing_slots):
        if not isinstance(slot, dict):
            raise SpaceContextPacketValidationError(f"missing_slots[{index}] must be an object")
        for key in ("name", "type", "severity", "action", "priority", "user_visible_note"):
            if key not in slot:
                raise SpaceContextPacketValidationError(f"missing_slots[{index}].{key} is required")
        if slot.get("action") not in allowed_missing_slot_actions:
            raise SpaceContextPacketValidationError(
                f"missing_slots[{index}].action must be one of: "
                f"{', '.join(sorted(allowed_missing_slot_actions))}"
            )
        if slot.get("severity") not in allowed_missing_slot_severities:
            raise SpaceContextPacketValidationError(
                f"missing_slots[{index}].severity must be one of: "
                f"{', '.join(sorted(allowed_missing_slot_severities))}"
            )
        if slot.get("priority") not in allowed_missing_slot_priorities:
            raise SpaceContextPacketValidationError(
                f"missing_slots[{index}].priority must be one of: "
                f"{', '.join(sorted(allowed_missing_slot_priorities))}"
            )

    coordination = packet.get("activation_pack_coordination") or {}
    if not isinstance(coordination, dict):
        raise SpaceContextPacketValidationError("activation_pack_coordination must be an object")
    for key in ("schema_version", "mode", "loaded_pack_ids", "merge_policy", "secondary_packs"):
        if key not in coordination:
            raise SpaceContextPacketValidationError(f"activation_pack_coordination.{key} is required")

    knowledge_binding = packet.get("knowledge_binding") or {}
    if "approved_knowledge_cards" not in knowledge_binding:
        raise SpaceContextPacketValidationError("knowledge_binding.approved_knowledge_cards is required")
    if not isinstance(knowledge_binding.get("approved_knowledge_cards"), list):
        raise SpaceContextPacketValidationError("knowledge_binding.approved_knowledge_cards must be a list")


class SpaceContextPacketService:
    """Compile a v3.3 context_packet from the current classification chain."""

    def __init__(
        self,
        classification_service: Optional[SpaceClassificationService] = None,
    ) -> None:
        self.classification_service = classification_service or SpaceClassificationService()
        self.missing_slot_service = MissingSlotService()

    def build(
        self,
        user_input: str,
        structured_requirements: Optional[Dict[str, Any]] = None,
        confirmed_tasks: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        activation = self.classification_service.classify_and_activate(
            user_input=user_input,
            structured_requirements=structured_requirements,
            confirmed_tasks=confirmed_tasks,
        )
        return self.build_from_activation(user_input, activation)

    def build_from_activation(self, user_input: str, activation: Dict[str, Any]) -> Dict[str, Any]:
        classification = activation.get("space_classification") or {}
        pack = activation.get("project_definition_activation_pack") or {}
        v18 = pack.get("_v18_extensions") or {}
        activation_pack = self._load_activation_pack(v18.get("activation_pack_id"))
        secondary_activation_packs = self._load_secondary_activation_packs(classification, v18)
        effective_activation_pack = self._merge_activation_packs(
            activation_pack,
            [item["pack"] for item in secondary_activation_packs],
        )
        activation_pack_coordination = self._build_activation_pack_coordination(
            primary_pack_id=v18.get("activation_pack_id"),
            secondary_activation_packs=secondary_activation_packs,
        )

        context_vector = self._build_context_vector(user_input, classification, v18)
        task_intent = self._detect_task_intent(user_input, classification)
        missing_slots = self._build_missing_slots(user_input, classification, effective_activation_pack, task_intent)
        required_disciplines = self._build_required_disciplines(
            user_input,
            classification,
            effective_activation_pack,
            v18,
            task_intent,
        )
        knowledge_package_ids = self._build_knowledge_package_ids(pack, effective_activation_pack)
        ontology_dimension_ids = self._unique(
            self._as_list(v18.get("active_ontology_dimension_ids"))
            + self._as_list(v18.get("priority_ontology_dimension_ids"))
        )
        approved_knowledge_cards = resolve_governed_knowledge_cards(
            package_ids=knowledge_package_ids,
            ontology_dimension_ids=ontology_dimension_ids,
            intended_use="theme_generation",
            min_evidence_level="weak_evidence",
        )
        knowledge_coverage_ceiling = self._build_knowledge_coverage_ceiling(
            classification=classification,
            activation_pack=effective_activation_pack,
            knowledge_package_ids=knowledge_package_ids,
            approved_knowledge_cards=approved_knowledge_cards,
        )

        spatial_extent_level = self._spatial_extent_from_context(user_input, classification, v18)
        output_mode = self._build_output_mode(user_input, classification, task_intent)
        classification_status = classification.get("status")
        if not task_intent.get("project_type_required") and not classification.get("project_type"):
            classification_status = "task_intent_routed"
        ontology_unmatched = self._as_list(classification.get("ontology_unmatched"))
        if not task_intent.get("project_type_required"):
            ontology_unmatched = [
                item
                for item in ontology_unmatched
                if item not in {"project_type_unmatched", "industry_domain_unspecified"}
            ]
        classification_ambiguity = {
            **(classification.get("ambiguity") or {}),
            "ontology_unmatched": ontology_unmatched,
        }
        governance_candidate = self._classification_governance_candidate(classification, task_intent)
        if governance_candidate:
            classification_ambiguity["governance_candidate"] = governance_candidate
        subdomain = {
            "primary_subdomain_id": v18.get("subdomain_id"),
            "secondary_subdomain_ids": classification.get("secondary_types") or [],
            "complement_roles": self._build_complement_roles(user_input, classification),
        }
        ontology_binding = {
            "ontology_framework_id": v18.get("ontology_framework_id"),
            "activation_pack_id": v18.get("activation_pack_id"),
            "secondary_activation_pack_ids": [
                item["pack_id"] for item in secondary_activation_packs
            ],
            "spatial_layer_ids": self._as_list(v18.get("spatial_layer_ids")),
            "ontology_dimension_ids": ontology_dimension_ids,
            "priority_ontology_dimension_ids": self._as_list(v18.get("priority_ontology_dimension_ids")),
        }
        retrieval_seed_packet = {
            "schema_version": "context_packet.v3.3",
            "classification": {
                "project_type_id": classification.get("project_type"),
                "subdomain": subdomain,
            },
            "context_vector": context_vector,
            "ontology_binding": ontology_binding,
            "knowledge_binding": {
                "knowledge_package_ids": knowledge_package_ids,
                "approved_knowledge_cards": approved_knowledge_cards,
            },
            "activation_pack_coordination": activation_pack_coordination,
        }
        retrieval_plan = RetrievalPlanner().plan(retrieval_seed_packet)
        retrieval_result = GovernedKnowledgeRetrievalService().retrieve(retrieval_seed_packet)
        packet = {
            "schema_version": "context_packet.v3.3",
            "classification": {
                "project_type_id": classification.get("project_type"),
                "project_type_name": classification.get("project_type_name"),
                "task_intent": task_intent,
                "subdomain": subdomain,
                "founding_type_id": v18.get("founding_type"),
                "spatial_extent_id": spatial_extent_level,
                "lifecycle_id": self._lifecycle_from_scale(v18.get("project_scale")),
                "project_scale": v18.get("project_scale"),
                "industry_domain": {
                    "id": v18.get("industry_domain") or classification.get("industry_domain"),
                    "source": "derived" if (v18.get("industry_domain") or classification.get("industry_domain")) else "none",
                },
                "confidence": {
                    "score": classification.get("confidence"),
                    "level": classification.get("confidence_level"),
                    "status": classification_status,
                },
                "ambiguity": classification_ambiguity,
                "freeze_state": classification.get("freeze_state") or {},
            },
            "context_vector": context_vector,
            "subject_axis": self._build_subject_axis(user_input, classification),
            "meta_context_drivers": self._build_meta_context_drivers(user_input, context_vector),
            "output_mode": output_mode,
            "discipline_switch": {
                "spatial_extent_level": spatial_extent_level,
                "required_disciplines": required_disciplines,
                "current_coverage": self._coverage(required_disciplines, effective_activation_pack),
            },
            "missing_slots": missing_slots,
            "translation_engine": self._build_translation_engine_seed(user_input, classification, context_vector),
            "ontology_binding": ontology_binding,
            "knowledge_binding": {
                "knowledge_package_ids": knowledge_package_ids,
                "knowledge_card_weights": v18.get("knowledge_card_weights") or {},
                "approved_knowledge_cards": approved_knowledge_cards,
                "coverage_ceiling": knowledge_coverage_ceiling,
                "retrieval_plan": retrieval_plan.model_dump(),
                "retrieval_policy": retrieval_result.policy,
                "graph_context": retrieval_result.graph_context,
                "retrieval_trace": retrieval_result.retrieval_trace,
            },
            "activation_pack_coordination": activation_pack_coordination,
            "trace": {
                "source": "SpaceClassificationService.classify_and_activate",
                "classification_schema_version": classification.get("schema_version"),
                "activation_pack_schema_version": pack.get("schema_version"),
                "secondary_activation_pack_count": len(secondary_activation_packs),
            },
        }
        validate_context_packet(packet)
        return packet

    @staticmethod
    def _classification_governance_candidate(
        classification: Dict[str, Any],
        task_intent: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if task_intent.get("project_type_required") is False and not classification.get("project_type"):
            return None

        raw_score = classification.get("confidence")
        score: Optional[float]
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            score = None

        low_confidence = score is None or score < 0.55
        missing_type = not classification.get("project_type")
        if not low_confidence and not missing_type:
            return None

        ambiguity = classification.get("ambiguity") or {}
        nearby_type_ids = [
            str(item)
            for item in (
                classification.get("secondary_types")
                or classification.get("candidate_types")
                or []
            )
            if str(item)
        ]
        return {
            "schema_version": "classification_governance_candidate.v1",
            "candidate_type": "project_type_boundary",
            "requires_human_review": True,
            "must_not_update_registry_automatically": True,
            "confidence_score": score,
            "confidence_level": classification.get("confidence_level"),
            "status": classification.get("status"),
            "nearby_type_ids": nearby_type_ids,
            "reason": ambiguity.get("reason") or classification.get("status") or "low_confidence_or_missing_type",
        }

    def _load_secondary_activation_packs(
        self,
        classification: Dict[str, Any],
        v18: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        detector_full = (classification.get("evidence") or {}).get("_detector_full") or {}
        subdomain_signals = detector_full.get("subdomain_signals") or []
        project_type = classification.get("project_type")
        primary_pack_id = v18.get("activation_pack_id")
        secondary: List[Dict[str, Any]] = []
        seen = {primary_pack_id} if primary_pack_id else set()

        for signal in subdomain_signals:
            if not isinstance(signal, dict):
                continue
            pack_id = signal.get("activation_pack_id")
            if not pack_id or pack_id in seen:
                continue
            confidence = float(signal.get("confidence") or 0.0)
            parent_matches = bool(signal.get("parent_type_match"))
            is_composite_context = project_type in {
                "hybrid_residential_commercial",
                "commercial_hospitality",
                "commercial_enterprise",
            }
            if confidence < 0.50 and not (is_composite_context and confidence >= 0.25):
                continue
            pack = self._load_activation_pack(pack_id)
            if not pack:
                continue
            seen.add(pack_id)
            secondary.append({
                "pack_id": pack_id,
                "subdomain_id": signal.get("suggested_subdomain_id"),
                "parent_project_type_id": signal.get("parent_project_type_id"),
                "confidence": confidence,
                "matched_keywords": self._as_list(signal.get("matched_keywords")),
                "role": "secondary_function_pack" if not parent_matches else "supporting_subdomain_pack",
                "pack": pack,
            })
        return secondary

    def _build_activation_pack_coordination(
        self,
        primary_pack_id: Optional[str],
        secondary_activation_packs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        secondary_packs = [
            {
                "pack_id": item["pack_id"],
                "subdomain_id": item.get("subdomain_id"),
                "parent_project_type_id": item.get("parent_project_type_id"),
                "confidence": item.get("confidence"),
                "matched_keywords": item.get("matched_keywords") or [],
                "role": item.get("role"),
            }
            for item in secondary_activation_packs
        ]
        loaded_pack_ids = self._unique(
            ([primary_pack_id] if primary_pack_id else [])
            + [item["pack_id"] for item in secondary_activation_packs]
        )
        if primary_pack_id and secondary_packs:
            mode = "primary_plus_secondary_pack_merge"
        elif secondary_packs:
            mode = "composite_secondary_pack_merge"
        elif primary_pack_id:
            mode = "single_primary_pack"
        else:
            mode = "general_ontology_fallback"
        return {
            "schema_version": "activation_pack_coordination.v1",
            "mode": mode,
            "primary_pack_id": primary_pack_id,
            "secondary_pack_ids": [item["pack_id"] for item in secondary_activation_packs],
            "loaded_pack_ids": loaded_pack_ids,
            "merge_policy": "additive_no_primary_classification_override",
            "secondary_packs": secondary_packs,
        }

    def _merge_activation_packs(
        self,
        primary_pack: Dict[str, Any],
        secondary_packs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        packs = [pack for pack in [primary_pack, *secondary_packs] if pack]
        if not packs:
            return {}

        merged: Dict[str, Any] = {}
        active_disciplines: List[Any] = []
        required_slots: List[Any] = []
        package_ids: List[Any] = []
        search_tags: List[Any] = []

        for pack in packs:
            active_disciplines.extend(self._as_list(pack.get("active_discipline_ids")))
            required_slots.extend(
                self._as_list((pack.get("questionnaire_profile") or {}).get("required_slots"))
            )
            binding = self._pack_knowledge_binding(pack)
            package_ids.extend(
                self._as_list(binding.get("package_ids"))
                + self._as_list(binding.get("knowledge_packages"))
            )
            search_tags.extend(self._as_list(binding.get("search_tags")))

        if primary_pack:
            merged.update(primary_pack)
        else:
            merged.update(packs[0])

        merged["active_discipline_ids"] = self._unique(active_disciplines)
        questionnaire_profile = dict(merged.get("questionnaire_profile") or {})
        questionnaire_profile["required_slots"] = self._unique(required_slots)
        merged["questionnaire_profile"] = questionnaire_profile

        knowledge_recall_profile = dict(merged.get("knowledge_recall_profile") or {})
        knowledge_recall_profile["package_ids"] = self._unique(package_ids)
        knowledge_recall_profile["search_tags"] = self._unique(search_tags)
        merged["knowledge_recall_profile"] = knowledge_recall_profile
        merged["knowledge_base_binding"] = {
            "knowledge_packages": knowledge_recall_profile["package_ids"],
            "search_tags": knowledge_recall_profile["search_tags"],
        }
        return merged

    @staticmethod
    def _pack_knowledge_binding(pack: Dict[str, Any]) -> Dict[str, Any]:
        return (
            pack.get("knowledge_recall_profile")
            or pack.get("knowledge_base_binding")
            or pack.get("knowledge_binding")
            or {}
        )

    def _build_context_vector(
        self,
        user_input: str,
        classification: Dict[str, Any],
        v18: Dict[str, Any],
    ) -> Dict[str, str]:
        text = user_input or ""
        project_type = classification.get("project_type")
        subdomain = v18.get("subdomain_id")
        is_tea = subdomain == "tea_drink_store" or any(term in text for term in ("茶饮", "奶茶", "新茶饮"))

        return {
            "industry_category": "FoodBeverage" if project_type == "commercial_dining" or is_tea else self._pascal(project_type),
            "primary_space_type": "TeaDrinkSpace" if is_tea else self._pascal(project_type),
            "site_context": self._site_context(text),
            "area_scale": self._area_scale(text),
            "service_mode": "TakeawayPriority" if any(term in text for term in ("外带", "取餐", "外卖", "自提")) else "Unknown",
            "business_model": self._business_model(text, is_tea),
            "operation_pressure": "PotentialHighPeak" if any(term in text for term in ("高峰", "效率", "排队", "出杯")) else "Unknown",
            "compliance_intensity": "MediumFoodSafetyConstraint" if project_type == "commercial_dining" or is_tea else "Unknown",
            "mep_complexity": "NeedsCheck" if any(term in text for term in ("给排水", "机电", "设备", "厨房")) else "Unknown",
            "investment_boundary": "CostSensitive" if any(term in text for term in ("预算", "成本", "回本", "租金", "有限")) else "Unknown",
            **self._general_composite_context_vector(text, project_type),
            **self._hybrid_context_vector(text, project_type),
        }

    @staticmethod
    def _detect_task_intent(user_input: str, classification: Dict[str, Any]) -> Dict[str, Any]:
        text = user_input or ""
        rules = [
            (
                "competition_strategy",
                ("竞标", "投标", "赢得竞标", "对手包括", "不知名设计团队"),
                True,
            ),
            (
                "concept_naming_system",
                ("命名", "概念名称", "主题名称", "命名体系"),
                True,
            ),
            (
                "planning_strategy",
                (
                    "规划策略",
                    "城市更新策略",
                    "前期定位",
                    "新区",
                    "地块",
                    "片区",
                    "小镇",
                    "聚落",
                    "轴线",
                    "长廊",
                    "整体更新",
                    "土地价值",
                    "建筑密度",
                    "景观系统",
                ),
                True,
            ),
            (
                "research_space_framework",
                (
                    "研究中心",
                    "研究与生活中心",
                    "极地研究",
                    "实验空间",
                    "实验室",
                    "体验馆",
                    "行为经济学",
                    "神经科学",
                    "社会学",
                    "传播学",
                    "政治经济学",
                    "后人类",
                ),
                True,
            ),
            (
                "methodology_framework",
                ("方法论", "方法论框架", "应用路径", "能力升级路径", "设计流程"),
                False,
            ),
            (
                "design_framework",
                ("完整设计框架", "设计框架", "完整室内设计框架", "完整室内设计概念", "完整设计概念", "完整设计方案"),
                True,
            ),
        ]

        evidence: List[str] = []
        primary_intent = "design_brief"
        project_type_required = True
        for intent, keywords, requires_project_type in rules:
            hits = [keyword for keyword in keywords if keyword in text]
            if hits:
                primary_intent = intent
                project_type_required = requires_project_type
                evidence = hits[:5]
                break

        if primary_intent == "methodology_framework" and classification.get("project_type"):
            project_type_required = True

        return {
            "primary_intent": primary_intent,
            "project_type_required": project_type_required,
            "confidence": 0.82 if evidence else 0.55,
            "evidence_terms": evidence,
        }

    def _build_subject_axis(self, user_input: str, classification: Dict[str, Any]) -> Dict[str, List[str]]:
        text = user_input or ""
        subject_psyche: List[str] = []
        stakeholder_power: List[str] = []
        if any(term in text for term in ("预算", "成本", "回本", "租金")):
            subject_psyche.append("cost_and_payback_pressure")
        if any(term in text for term in ("首店", "新店", "新茶饮")):
            subject_psyche.append("new_store_uncertainty")
        if any(term in text for term in ("投资人", "合伙", "老板", "业主")):
            stakeholder_power.append("owner_or_investor_decision_power")
        has_family_context = any(term in text for term in ("事业与家庭", "家庭精神", "家庭住宅", "家庭", "夫妻"))
        has_business_context = any(term in text for term in ("办公室", "公司", "会所", "事业"))
        has_spiritual_context = any(term in text for term in ("佛堂", "禅修", "精神融合", "禅意"))
        if (
            classification.get("project_type") == "hybrid_residential_commercial"
            and has_family_context
            and has_business_context
            and has_spiritual_context
        ):
            subject_psyche.append("family_business_spiritual_integration")
        if any(term in text for term in ("公司", "办公室", "家庭住宅", "会所")):
            stakeholder_power.append("mixed_use_stakeholder_boundary")
        if any(term in text for term in ("人物", "精神结构", "品牌", "学科", "理论", "文化", "方法论")):
            subject_psyche.append("source_translation_pressure")
        return {"subject_psyche": subject_psyche, "stakeholder_power": stakeholder_power}

    def _build_meta_context_drivers(self, user_input: str, context_vector: Dict[str, str]) -> List[str]:
        drivers: List[str] = []
        if context_vector.get("operation_pressure") == "PotentialHighPeak":
            drivers.append("peak_efficiency_pressure")
        if context_vector.get("investment_boundary") == "CostSensitive":
            drivers.append("cost_sensitive_decision")
        if context_vector.get("service_mode") == "TakeawayPriority":
            drivers.append("takeaway_flow_priority")
        if "首店" in (user_input or ""):
            drivers.append("first_store_validation")
        if context_vector.get("conversion_context") == "SalesOfficeAdaptiveReuse":
            drivers.append("adaptive_reuse_existing_sales_office")
        if context_vector.get("privacy_gradient") == "PublicToPrivateVerticalStack":
            drivers.append("public_private_vertical_layering")
        if context_vector.get("material_strategy") == "RestrainedMinimalMaterialSystem":
            drivers.append("restrained_material_and_old_new_collision")
        if context_vector.get("conversion_context") == "IndustrialAdaptiveReuse":
            drivers.append("adaptive_reuse_existing_industrial_site")
        if context_vector.get("functional_mix") == "MultiRoleComposite":
            drivers.append("multi_role_composite_program")
        if any(term in (user_input or "") for term in ("竞标", "投标", "赢得竞标", "对手包括")):
            drivers.append("competition_positioning_pressure")
        if any(term in (user_input or "") for term in ("方法论", "研究", "学科", "理论", "转译")):
            drivers.append("source_to_space_translation_pressure")
        return drivers

    def _build_missing_slots(
        self,
        user_input: str,
        classification: Dict[str, Any],
        activation_pack: Dict[str, Any],
        task_intent: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        required_slots = (
            (activation_pack.get("questionnaire_profile") or {}).get("required_slots")
            or []
        )
        contextual_conditions = set(
            self._as_list(classification.get("contextual_project_conditions"))
        )
        conditional_slots: List[str] = []
        if "transit_connection" in contextual_conditions:
            conditional_slots.append("traffic_node_conversion")
        if "payback_pressure" in contextual_conditions:
            conditional_slots.append("payback_model_inputs")
        required_slots = self._unique(
            [str(slot) for slot in required_slots[:7]]
            + conditional_slots
            + self._derive_subjective_preference_slots(user_input, classification, task_intent)
        )
        slot_result = self.missing_slot_service.build(
            required_slots=required_slots,
            user_input=user_input,
        )
        slots = list(slot_result["missing_slots"])

        project_type_required = (task_intent or {}).get("project_type_required", True)
        classification_confidence = self._as_float(classification.get("confidence"), 0.0)
        has_confident_project_type = bool(classification.get("project_type")) and classification_confidence >= 0.70
        clarification_questions = []
        if project_type_required and not has_confident_project_type:
            clarification_questions = self._as_list(classification.get("clarification_questions"))
        for question in clarification_questions:
            slots.append({
                "name": "classification_clarification",
                "type": "business_fact",
                "severity": "medium",
                "action": "branch_answer_plus_followup",
                "priority": "P2",
                "affected_lens": [],
                "unlock_condition": str(question),
                "user_visible_note": str(question),
            })

        if classification.get("coverage_gap") and not slots and project_type_required:
            slots.append({
                "name": "context_coverage_gap",
                "type": "business_fact",
                "severity": "medium",
                "action": "branch_answer_plus_followup",
                "priority": "P2",
                "affected_lens": [],
                "unlock_condition": "补齐空间用途、行业语境、使用者和约束边界",
                "user_visible_note": "当前语境信息不足，需要先补齐项目用途、行业语境和关键约束。",
            })

        if classification.get("project_type") == "hybrid_residential_commercial":
            existing_names = {slot.get("name") for slot in slots}
            hybrid_slots = [
                {
                    "name": "structural_modification_boundary",
                    "type": "physical_constraint",
                    "severity": "high",
                    "action": "certainty_ceiling",
                    "priority": "P1",
                    "affected_lens": ["structure", "mep", "vertical_circulation"],
                    "unlock_condition": "known(existing_structure_and_vertical_circulation_boundary)",
                    "user_visible_note": "需要确认原售楼处结构、楼梯/电梯、承重与机电条件，否则结构改造只能给条件级判断。",
                },
                {
                    "name": "public_private_access_control",
                    "type": "business_fact",
                    "severity": "high",
                    "action": "branch_answer_plus_followup",
                    "priority": "P2",
                    "affected_lens": ["privacy", "access", "operation"],
                    "unlock_condition": "known(public_private_access_and_time_sharing_rules)",
                    "user_visible_note": "需要确认展厅、办公室、家庭住宅、会所是否共用入口、动线和时段，才能判断公共与私密分层。",
                },
            ]
            slots.extend(slot for slot in hybrid_slots if slot["name"] not in existing_names)

        return self.missing_slot_service.apply_policy(slots)

    def _derive_subjective_preference_slots(
        self,
        user_input: str,
        classification: Dict[str, Any],
        task_intent: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        primary_intent = (task_intent or {}).get("primary_intent")
        project_type = classification.get("project_type")
        text = user_input or ""
        design_like_intents = {
            "design_brief",
            "design_framework",
            "competition_strategy",
            "research_space_framework",
            "planning_strategy",
        }
        if primary_intent not in design_like_intents and not project_type:
            return []
        if any(term in text for term in ("方法论", "研究框架", "理论框架")) and not project_type:
            return []
        return ["style_preference", "tone_preference"]

    def _slot_from_required_slot(self, slot: str) -> Dict[str, Any]:
        return self.missing_slot_service.slot_from_required_slot(slot)

    @staticmethod
    def _canonical_slot_name(slot: str) -> str:
        return MissingSlotService.canonical_slot_name(slot)

    @staticmethod
    def _slot_note(slot: str) -> str:
        return MissingSlotService.slot_note(slot)

    @staticmethod
    def _build_required_disciplines(
        user_input: str,
        classification: Dict[str, Any],
        activation_pack: Dict[str, Any],
        v18: Dict[str, Any],
        task_intent: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        disciplines = SpaceContextPacketService._as_list(activation_pack.get("active_discipline_ids"))
        if not disciplines and v18.get("spatial_layer_ids"):
            disciplines = ["interior"]
        if "interior" not in disciplines:
            disciplines.insert(0, "interior")
        if (task_intent or {}).get("primary_intent") == "competition_strategy":
            disciplines.append("operations")
        if classification.get("project_type") == "hybrid_residential_commercial":
            text = user_input or ""
            if any(term in text for term in ("四层", "4楼", "结构改造", "售楼处改造", "别墅")):
                disciplines.extend(["architecture", "structure", "mep", "fire_safety"])
            if any(term in text for term in ("办公室", "会所", "展厅", "公共与私密", "动线")):
                disciplines.append("operations")
        spatial_extent = SpaceContextPacketService._spatial_extent_from_context(user_input, classification, v18)
        if spatial_extent in {"site", "district", "region"}:
            disciplines.extend(["architecture", "landscape", "urban_planning", "operations"])
        text = user_input or ""
        if any(term in text for term in ("改造", "更新", "旧厂房", "废弃", "结构", "消防", "既有")):
            disciplines.extend(["structure", "fire_safety"])
        if any(term in text for term in ("医疗", "康养", "研究", "实验", "培训")):
            disciplines.append("specialist_programming")
        return SpaceContextPacketService._unique(disciplines)

    @staticmethod
    def _build_knowledge_package_ids(pack: Dict[str, Any], activation_pack: Dict[str, Any]) -> List[str]:
        binding = SpaceContextPacketService._pack_knowledge_binding(activation_pack)
        runtime_binding = pack.get("knowledge_base_binding") or pack.get("knowledge_binding") or {}
        return SpaceContextPacketService._unique(
            SpaceContextPacketService._as_list(binding.get("package_ids"))
            + SpaceContextPacketService._as_list(binding.get("knowledge_packages"))
            + SpaceContextPacketService._as_list(runtime_binding.get("knowledge_packages"))
        )

    @staticmethod
    def _build_knowledge_coverage_ceiling(
        *,
        classification: Dict[str, Any],
        activation_pack: Dict[str, Any],
        knowledge_package_ids: List[str],
        approved_knowledge_cards: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        has_pack = bool(activation_pack)
        has_packages = bool(knowledge_package_ids)
        has_cards = bool(approved_knowledge_cards)
        coverage_gap = bool(classification.get("coverage_gap"))
        project_type = classification.get("project_type")

        if has_pack and (has_packages or has_cards) and not coverage_gap:
            return {
                "schema_version": "knowledge_coverage_ceiling.v1",
                "coverage_level": "specialist_covered",
                "ceiling_level": "full_specialist",
                "must_not_claim_specialist_coverage": False,
                "source": "activation_pack+approved_knowledge",
                "reasons": [],
                "allowed_outputs": ["完整设计框架", "专科知识调用", "条件明确后的任务书深化"],
                "forbidden_outputs": [],
                "user_visible_note": "当前已有可用专科知识支撑，可以进入较完整的方案判断。",
            }

        if has_pack or has_packages or has_cards:
            return {
                "schema_version": "knowledge_coverage_ceiling.v1",
                "coverage_level": "partial_specialist",
                "ceiling_level": "conditional_framework",
                "must_not_claim_specialist_coverage": True,
                "source": "partial_activation_or_knowledge",
                "reasons": SpaceContextPacketService._unique(
                    [
                        "分类链路存在覆盖缺口" if coverage_gap else "",
                        "专科知识包或 approved cards 不完整",
                    ]
                ),
                "allowed_outputs": ["条件级设计框架", "风险清单", "下一步补充资料"],
                "forbidden_outputs": ["精确施工尺寸", "确定设备型号", "保证性经营结论"],
                "user_visible_note": "当前只有部分专科依据，可以给条件级判断，不能当成完整专科方案。",
            }

        return {
            "schema_version": "knowledge_coverage_ceiling.v1",
            "coverage_level": "general_method_only",
            "ceiling_level": "strategy_framework",
            "must_not_claim_specialist_coverage": True,
            "source": "classification_without_specialist_knowledge",
            "reasons": SpaceContextPacketService._unique(
                [
                    "没有绑定正式激活包",
                    "没有可用知识包",
                    "没有可用 approved knowledge cards",
                    "分类链路存在覆盖缺口" if coverage_gap else "",
                    f"当前项目类型: {project_type}" if project_type else "",
                ]
            ),
            "allowed_outputs": ["通用空间方法论", "策略级判断", "风险提示", "需要核验的资料清单"],
            "forbidden_outputs": ["精确施工尺寸", "确定设备型号", "保证性经营结论", "专科知识包结论"],
            "user_visible_note": "当前还没有足够的专科知识支撑，只能先给通用方法论和策略级判断，不能套用专科知识包。",
        }

    @staticmethod
    def _coverage(required_disciplines: List[str], activation_pack: Dict[str, Any]) -> str:
        if not required_disciplines:
            return "partial"
        if activation_pack:
            return "covered"
        return "partial"

    @staticmethod
    def _site_context(text: str) -> str:
        if any(term in text for term in ("购物中心", "商场", "mall", "Mall")):
            return "MallStore"
        if any(term in text for term in ("街边", "沿街", "社区")):
            return "StreetStore"
        return "Unknown"

    @staticmethod
    def _area_scale(text: str) -> str:
        match = re.search(r"(\d+(?:\.\d+)?)\s*(?:㎡|平|m2|m²)", text)
        if not match:
            return "Unknown"
        area = float(match.group(1))
        if area <= 80:
            return "SmallArea"
        if area <= 200:
            return "MediumArea"
        return "LargeArea"

    @staticmethod
    def _business_model(text: str, is_tea: bool) -> str:
        if is_tea and any(term in text for term in ("外带", "取餐", "外卖", "预算", "成本")):
            return "CostSensitiveQuickService"
        if is_tea:
            return "QuickServiceBeverage"
        return "Unknown"

    @staticmethod
    def _general_composite_context_vector(text: str, project_type: Optional[str]) -> Dict[str, str]:
        roles = SpaceContextPacketService._extract_complement_roles(text, project_type)
        vector: Dict[str, str] = {}
        if len(roles) >= 3:
            vector["functional_mix"] = "MultiRoleComposite"
        if any(term in text for term in ("旧厂房", "废弃陶瓷工厂", "工业遗存", "厂房地块")):
            vector["conversion_context"] = "IndustrialAdaptiveReuse"
        elif any(term in text for term in ("老码头", "历史街区", "旧城", "城市更新")):
            vector["conversion_context"] = "UrbanRenewalAdaptiveReuse"
        if any(term in text for term in ("土地价值", "功能混合比例", "公共开放空间", "景观系统")):
            vector["planning_pressure"] = "LandValueMixedUsePublicRealm"
        return vector

    @staticmethod
    def _hybrid_context_vector(text: str, project_type: Optional[str]) -> Dict[str, str]:
        if project_type != "hybrid_residential_commercial":
            return {}

        lower_text = text.lower()
        vector: Dict[str, str] = {}
        if all(
            any(term in lower_text for term in terms)
            for terms in (
                ("展厅", "美术馆", "艺术"),
                ("办公室", "办公", "公司"),
                ("住宅", "别墅", "家庭"),
                ("会所", "ktv", "健身房", "高尔夫"),
            )
        ):
            vector["functional_mix"] = "ExhibitionOfficeResidenceClubhouse"
        if any(term in text for term in ("公共与私密", "公共与私密的分层", "分层逻辑")):
            vector["privacy_gradient"] = "PublicToPrivateVerticalStack"
        if any(term in text for term in ("售楼处改造", "销售中心改造", "地产售楼处")):
            vector["conversion_context"] = "SalesOfficeAdaptiveReuse"
        if any(term in text for term in ("极简", "材料克制", "纯粹")):
            vector["material_strategy"] = "RestrainedMinimalMaterialSystem"
        if any(term in text for term in ("新旧对撞", "新旧")):
            vector["heritage_tension"] = "OldNewCollision"
        if any(term in text for term in ("佛堂", "禅意", "精神融合")):
            vector["spiritual_layer"] = "ZenFamilyRitual"
        if any(term in text for term in ("佛堂", "禅修", "精神融合")):
            vector["spiritual_program"] = "IndependentBuddhistRoom"
        if any(term in text for term in ("事业与家庭", "家庭精神", "家庭住宅")) and any(
            term in text for term in ("办公室", "公司", "会所")
        ):
            vector["business_family_relation"] = "IntegratedButLayered"
        return vector

    @staticmethod
    def _spatial_extent_from_scale(project_scale: Optional[str]) -> str:
        if not project_scale:
            return "interior"
        return str(project_scale).split("_", 1)[0]

    @staticmethod
    def _spatial_extent_from_context(
        user_input: str,
        classification: Dict[str, Any],
        v18: Dict[str, Any],
    ) -> str:
        text = user_input or ""
        if any(
            term in text
            for term in (
                "城市更新策略",
                "整体更新",
                "地块",
                "片区",
                "新区",
                "小镇",
                "轴线",
                "长廊",
                "土地价值",
                "建筑密度",
                "复合型社区",
                "示范区",
            )
        ):
            return "district"
        if any(term in text for term in ("山谷度假聚落", "旅游目的地", "市民农场", "公共开放空间")):
            return "site"
        if any(term in text for term in ("研究中心", "研究与生活中心", "会客中心", "综合体")) and any(
            term in text for term in ("打造", "建设", "一座", "建筑", "保温构造", "极昼极夜")
        ):
            return "building"
        if classification.get("project_type") == "hybrid_residential_commercial":
            if any(term in text for term in ("四层", "4楼", "别墅", "售楼处改造", "结构改造")):
                return "building"
        return SpaceContextPacketService._spatial_extent_from_scale(v18.get("project_scale"))

    @staticmethod
    def _build_complement_roles(user_input: str, classification: Dict[str, Any]) -> List[str]:
        text = (user_input or "").lower()
        roles = SpaceContextPacketService._extract_complement_roles(text, classification.get("project_type"))
        if classification.get("project_type") == "hybrid_residential_commercial":
            return roles
        if len(roles) >= 2 or "复合" in text:
            return roles
        return []

    @staticmethod
    def _extract_complement_roles(text: str, project_type: Optional[str]) -> List[str]:
        lower_text = (text or "").lower()
        role_rules = [
            ("exhibition", ("展厅", "美术馆", "艺术")),
            ("office_business", ("办公室", "办公", "公司")),
            ("family_residence", ("住宅", "别墅", "家庭", "居住")),
            ("spiritual_room", ("佛堂", "禅意", "精神")),
            ("clubhouse", ("会所", "露台会所", "高尔夫")),
            ("wellness", ("中医", "理疗", "康养")),
            ("entertainment", ("ktv", "健身房", "娱乐")),
            ("production_workshop", ("工厂", "车间", "工作室", "生产", "陶瓷")),
            ("retail_commerce", ("买手店", "商业", "零售", "市集", "主展示区")),
            ("dining_cafe", ("咖啡", "餐饮", "轻餐饮", "餐饮与市集")),
            ("residence_stay", ("驻留公寓", "民宿", "住宿", "居住")),
            ("education_training", ("培训", "科普", "教育", "亲子厨房")),
            ("public_realm", ("公共客厅", "公共开放空间", "市民活动", "滨水界面")),
        ]
        roles = [role for role, terms in role_rules if any(term in lower_text for term in terms)]
        if project_type == "hybrid_residential_commercial":
            preferred = [
                "exhibition",
                "office_business",
                "family_residence",
                "spiritual_room",
                "clubhouse",
                "wellness",
                "entertainment",
            ]
            return [role for role in preferred if role in roles]
        return SpaceContextPacketService._unique(roles)

    @staticmethod
    def _build_output_mode(
        user_input: str,
        classification: Dict[str, Any],
        task_intent: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        secondary_modes: List[str] = []
        text = user_input or ""
        primary_output_mode = (task_intent or {}).get("primary_intent") or "design_brief"
        if primary_output_mode == "design_brief":
            primary_output_mode = "design_brief"
        if classification.get("project_type") == "hybrid_residential_commercial":
            if any(term in text for term in ("框架", "路径", "逻辑", "策略")):
                secondary_modes.append("methodology")
            if any(term in text for term in ("精神融合", "禅意", "新旧对撞", "材料克制")):
                secondary_modes.append("concept_matrix")
        if primary_output_mode == "competition_strategy":
            secondary_modes.append("methodology_framework")
        elif primary_output_mode == "planning_strategy":
            secondary_modes.append("design_framework")
        elif primary_output_mode == "research_space_framework":
            secondary_modes.extend(["methodology_framework", "evidence_mapping"])
        elif primary_output_mode == "concept_naming_system":
            secondary_modes.append("concept_matrix")

        return {
            "primary_output_mode": primary_output_mode,
            "secondary_output_modes": SpaceContextPacketService._unique(secondary_modes),
            "user_visible_container": "DesignBrief_2_0",
        }

    @staticmethod
    def _build_translation_engine_seed(
        user_input: str,
        classification: Dict[str, Any],
        context_vector: Dict[str, str],
    ) -> Dict[str, Any]:
        text = user_input or ""
        source_roles: List[str] = []
        decode: List[str] = []
        map_steps: List[str] = []
        solve: List[str] = []
        anti_slippage: List[str] = []

        if classification.get("project_type") == "hybrid_residential_commercial":
            source_roles.extend(["constraint_boundary", "transformed_source", "tool_material"])

        if context_vector.get("functional_mix") == "MultiRoleComposite":
            source_roles.extend(["constraint_boundary", "transformed_source", "tool_material"])
            decode.append("解码多功能复合项目的主次角色、共用界面和运营闭环")
            map_steps.append("把复合功能映射为角色分区、共享节点、服务后场和时段管理")
            solve.append("用动线、权限、声光气味和运营边界求解多角色互扰")
            anti_slippage.append("避免只罗列功能房间，必须说明角色关系和复合收益")

        if context_vector.get("conversion_context") == "IndustrialAdaptiveReuse":
            source_roles.extend(["existing_site_source", "heritage_constraint"])
            decode.append("解码工业遗存、生产记忆和再利用边界")
            map_steps.append("把旧厂房结构、材料痕迹和产业展示转成空间叙事骨架")
            anti_slippage.append("避免把工业遗存简化为装饰风格，需回到结构、工艺和运营")

        if any(term in text for term in ("品牌", "人物", "精神结构", "文化", "学科", "理论", "劳斯莱斯", "赫本", "行为经济学", "神经科学")):
            source_roles.extend(["reference_source", "disciplinary_source"])
            decode.append("解码外部来源背后的行为、价值和审美秩序")
            map_steps.append("把来源秩序映射为空间序列、材料等级、交互机制和叙事节奏")
            anti_slippage.append("避免把来源符号化、表皮化或只做主题装饰")

        if context_vector.get("spiritual_layer") == "ZenFamilyRitual":
            decode.append("解码禅意、极简和事业家庭精神融合的不变结构")
            map_steps.append("把精神源映射为留白、序列、静区、仪式尺度和光线克制")
            anti_slippage.append("避免把禅意退化为佛像符号堆砌或伪新中式装饰")
        if context_vector.get("privacy_gradient") == "PublicToPrivateVerticalStack":
            solve.append("用垂直分层、入口权限、时段管理和缓冲界面求解公共私密冲突")
        if context_vector.get("conversion_context") == "SalesOfficeAdaptiveReuse":
            solve.append("先锁定原售楼处结构、机电和消防边界，再讨论空间立意落地")
        if context_vector.get("heritage_tension") == "OldNewCollision":
            anti_slippage.append("避免把新旧对撞做成表皮拼贴，必须回到结构、材料和时间痕迹")

        return {
            "source_roles": SpaceContextPacketService._unique(source_roles),
            "steps": {
                "decode": SpaceContextPacketService._unique(decode),
                "map": SpaceContextPacketService._unique(map_steps),
                "solve": SpaceContextPacketService._unique(solve),
                "anti_slippage": SpaceContextPacketService._unique(anti_slippage),
            },
            "anti_slippage_checks": SpaceContextPacketService._unique(anti_slippage),
        }

    @staticmethod
    def _lifecycle_from_scale(project_scale: Optional[str]) -> Optional[str]:
        if not project_scale or "_" not in str(project_scale):
            return None
        return str(project_scale).split("_", 1)[1]

    @staticmethod
    def _pascal(value: Optional[str]) -> str:
        if not value:
            return "Unknown"
        return "".join(part.capitalize() for part in str(value).split("_") if part)

    @staticmethod
    def _load_yaml(path: Path) -> Dict[str, Any]:
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        except Exception as exc:
            logger.warning(f"[SpaceContextPacket] failed to load {path}: {exc}")
            return {}

    def _load_activation_pack(self, pack_id: Optional[str]) -> Dict[str, Any]:
        if not pack_id:
            return {}
        return self._load_yaml(_ACTIVATION_PACK_DIR / f"{pack_id}.yaml")

    @staticmethod
    def _as_list(value: Any) -> List[Any]:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        if isinstance(value, set):
            return list(value)
        return [value]

    @staticmethod
    def _as_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _unique(values: Iterable[Any]) -> List[str]:
        result: List[str] = []
        seen = set()
        for value in values:
            if value in (None, ""):
                continue
            item = str(value)
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result
