from intelligent_project_analyzer.services.capability_plan_service import CapabilityPlanService
from intelligent_project_analyzer.services.space_context_packet_service import SpaceContextPacketService


def _activation_with_coverage_gap():
    return {
        "space_classification": {
            "schema_version": "space_classification.v1.8",
            "project_type": "personal_residential",
            "project_type_name": "私人住宅",
            "confidence": 0.9,
            "confidence_level": "high",
            "status": "classified",
            "coverage_gap": True,
            "knowledge_gap_ticket": {
                "gap_type": "knowledge_coverage",
                "project_type": "personal_residential",
            },
        },
        "project_definition_activation_pack": {
            "schema_version": "project_definition_activation_pack.v1.8",
            "_v18_extensions": {
                "ontology_framework_id": "personal_residential",
                "subdomain_id": "private_residence",
                "founding_type": "life_stage",
                "project_scale": "room_or_interior",
                "spatial_layer_ids": ["interior_layer"],
                "active_ontology_dimension_ids": ["E7_social_relations"],
                "priority_ontology_dimension_ids": ["E7_social_relations"],
                "activation_pack_id": None,
                "knowledge_card_weights": {},
            },
            "knowledge_base_binding": {
                "knowledge_packages": [],
            },
        },
    }


def test_context_packet_declares_knowledge_coverage_ceiling_for_uncovered_type():
    packet = SpaceContextPacketService().build_from_activation(
        "深圳湾一线海景别墅，业主为第一代创业者，需要完整室内设计概念。",
        _activation_with_coverage_gap(),
    )

    ceiling = packet["knowledge_binding"]["coverage_ceiling"]

    assert ceiling["coverage_level"] == "general_method_only"
    assert ceiling["ceiling_level"] == "strategy_framework"
    assert ceiling["must_not_claim_specialist_coverage"] is True
    assert "不能套用专科知识包" in ceiling["user_visible_note"]
    assert "精确施工尺寸" in ceiling["forbidden_outputs"]


def test_capability_plan_uses_knowledge_coverage_ceiling_even_without_missing_hard_slots():
    packet = SpaceContextPacketService().build_from_activation(
        "深圳湾一线海景别墅，业主为第一代创业者，需要完整室内设计概念。",
        _activation_with_coverage_gap(),
    )

    plan = CapabilityPlanService().build(
        context_packet=packet,
        knowledge_context=packet["knowledge_binding"],
    )

    assert plan["status"] == "degraded"
    assert plan["maturity_ceiling"] == "strategy_framework"
    assert plan["knowledge_coverage"]["coverage_level"] == "general_method_only"

    retrieval = next(node for node in plan["capability_nodes"] if node["capability_group"] == "Retrieval")
    generation = next(node for node in plan["capability_nodes"] if node["capability_group"] == "Generation")

    assert retrieval["status"] == "degraded"
    assert "knowledge_coverage_ceiling" in retrieval["blocking_reasons"]
    assert generation["maturity_ceiling_rule"] == "knowledge coverage gap caps output to strategy framework"
