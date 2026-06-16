"""Adapter that projects existing Scheme Advisor intelligence into demand_reconstruction context."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .scheme_advisor_context_intelligence import SchemeAdvisorContextIntelligence
from .scheme_advisor_semantic_axes import derive_semantic_axes, rank_main_tensions


class DemandReconstructionContextAdapter:
    """Build the demand-reconstruction-layer context without creating a second classifier."""

    def __init__(self, context_intelligence: Optional[SchemeAdvisorContextIntelligence] = None) -> None:
        self._context_intelligence = context_intelligence or SchemeAdvisorContextIntelligence()

    def build(self, user_message: str) -> Dict[str, Any]:
        text = str(user_message or "")
        advisor_packet = self._safe_context_packet(text)
        semantic_axes = derive_semantic_axes(text)
        main_tensions = rank_main_tensions(text)
        classification = advisor_packet.get("classification") or {}
        context_vector = advisor_packet.get("context_vector") or {}
        archetype = self._derive_archetype(
            text,
            semantic_axes=semantic_axes,
            classification=classification,
            context_vector=context_vector,
        )
        return {
            "schema_version": "demand_reconstruction_context_adapter.v1",
            "source_message": text,
            "advisor_packet": advisor_packet,
            "project_type": advisor_packet.get("project_type") or classification.get("project_type"),
            "project_type_name": advisor_packet.get("project_type_name") or classification.get("project_type_name"),
            "space_label": advisor_packet.get("space_label") or "空间项目",
            "classification": classification,
            "context_vector": context_vector,
            "semantic_axes": semantic_axes,
            "main_tensions": main_tensions,
            "missing_slots": advisor_packet.get("missing_slots") or [],
            "archetype": archetype,
            "context_source": {
                "context_intelligence": bool(advisor_packet),
                "space_classification": bool(classification),
                "semantic_axes": True,
                "ontology_focus": bool(advisor_packet.get("ontology_focus")),
                "knowledge_context": bool(advisor_packet.get("knowledge_context")),
            },
        }

    def _safe_context_packet(self, text: str) -> Dict[str, Any]:
        try:
            return self._context_intelligence.build(text)
        except Exception:
            return {}

    @staticmethod
    def _derive_archetype(
        text: str,
        *,
        semantic_axes: Dict[str, List[str]],
        classification: Dict[str, Any],
        context_vector: Dict[str, Any],
    ) -> Dict[str, Any]:
        normalized = str(text or "")
        project_type = str(classification.get("project_type") or "")
        primary_bucket = str(classification.get("primary_bucket") or "")
        domains = set(semantic_axes.get("space_domains") or [])
        drivers = set(semantic_axes.get("founding_drivers") or [])
        subject_profiles = set(semantic_axes.get("subject_profiles") or [])
        vector_values = {str(value) for value in context_vector.values() if value}

        if DemandReconstructionContextAdapter._has_any(
            normalized,
            ("研究", "源流", "历史", "宋代", "文人", "雅集", "文化母题", "证据", "转译", "启发"),
        ):
            return {"primary": "cultural_research", "secondary": [], "routing_target": "deep_research"}

        if DemandReconstructionContextAdapter._has_any(
            normalized,
            ("冷藏柜", "留多大", "尺寸", "设备", "给排水", "上下水", "多少平", "多大", "预算"),
        ):
            return {"primary": "hard_constraint", "secondary": [], "routing_target": "demand_reconstruction"}

        if DemandReconstructionContextAdapter._has_any(
            normalized,
            ("东方感", "不老气", "风格", "侘寂", "松弛感", "安藤", "精神性", "材料气质", "氛围"),
        ):
            return {"primary": "style_semantics", "secondary": [], "routing_target": "demand_reconstruction"}

        is_commercial = (
            "retail_commercial" in domains
            or "operational_efficiency" in drivers
            or project_type in {"commercial_dining", "tea_drink_store", "commercial_retail"}
            or bool({"FoodBeverage", "CommercialDining", "TakeawayPriority", "PotentialHighPeak"}.intersection(vector_values))
            or DemandReconstructionContextAdapter._has_any(normalized, ("咖啡", "茶饮", "店", "翻台", "外带", "坪效", "出杯", "客流"))
        )
        if is_commercial:
            return {"primary": "commercial_operation", "secondary": [], "routing_target": "demand_reconstruction"}

        is_life_identity = (
            project_type == "personal_residential"
            or primary_bucket == "residential"
            or "residential" in domains
            or "professional_user" in subject_profiles
            or DemandReconstructionContextAdapter._has_any(
                normalized,
                ("返乡", "老家", "背井离乡", "民居", "自宅", "住宅", "家族", "退休", "后半生", "乡土"),
            )
        )
        if is_life_identity:
            return {"primary": "life_identity", "secondary": [], "routing_target": "demand_reconstruction"}

        return {"primary": "general_project", "secondary": [], "routing_target": "demand_reconstruction"}

    @staticmethod
    def _has_any(text: str, terms: tuple[str, ...]) -> bool:
        return any(term in text for term in terms)
