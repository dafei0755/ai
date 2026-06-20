from intelligent_project_analyzer.services.demand_reconstruction_service import DemandReconstructionService


def test_governed_knowledge_card_match_requires_structural_anchor_or_strong_evidence():
    adapter_context = {
        "llm_semantic_understanding": {
            "project_object": "特殊儿童康复教室",
            "recommended_scan_targets": ["special_children_rehab_classroom", "sensory_recovery_boundary"],
            "space_candidates": [
                {"label": "special_children_rehab_classroom", "evidence": ["特殊儿童康复教室", "感统训练"]}
            ],
            "core_tensions": [
                {"title": "训练刺激与安静恢复之间的张力", "evidence": ["感统训练", "安静恢复"]}
            ],
        }
    }
    terms = DemandReconstructionService._governed_knowledge_match_terms(
        adapter_context,
        "一个特殊儿童康复教室，需要兼顾感统训练和安静恢复。",
    )

    weak_card = {
        "card_id": "weak_text_only_children_card",
        "title": "特殊儿童康复教室 弱文本候选",
        "project_type": "特殊儿童康复教室",
        "summary": "文本上相似，但没有知识包、维度或可信证据等级支撑。",
        "evidence": ["特殊儿童康复教室"],
        "package_ids": [],
        "ontology_dimension_ids": [],
        "evidence_level": "governance_signal",
    }
    strong_card = {
        "card_id": "strong_package_dimension_children_card",
        "title": "特殊儿童康复教室 强召回卡",
        "project_type": "特殊儿童康复教室",
        "summary": "带有知识包、维度和专家复核等级，可进入需求重构 Stage 3。",
        "evidence": ["特殊儿童康复教室", "感统训练", "安静恢复"],
        "package_ids": ["special_children_rehab_classroom"],
        "ontology_dimension_ids": ["sensory_recovery_boundary"],
        "evidence_level": "expert_review",
    }

    weak_match = DemandReconstructionService._approved_card_match_metadata(weak_card, terms)
    strong_match = DemandReconstructionService._approved_card_match_metadata(strong_card, terms)

    assert weak_match["decision"] == "rejected"
    assert weak_match["text_match"] is True
    assert weak_match["score"] < strong_match["score"]
    assert strong_match["decision"] == "accepted"
    assert strong_match["package_hits"] == ["special_children_rehab_classroom"]
    assert strong_match["dimension_hits"] == ["sensory_recovery_boundary"]
    assert strong_match["evidence_level"] == "expert_review"


def test_compact_governed_knowledge_asset_preserves_structural_match_metadata():
    card = {
        "card_id": "strong_package_dimension_children_card",
        "title": "特殊儿童康复教室 强召回卡",
        "project_type": "特殊儿童康复教室",
        "summary": "带有知识包、维度和专家复核等级，可进入需求重构 Stage 3。",
        "evidence": ["特殊儿童康复教室", "感统训练", "安静恢复"],
        "package_ids": ["special_children_rehab_classroom"],
        "ontology_dimension_ids": ["sensory_recovery_boundary"],
        "allowed_use": ["用于需求重构阶段提醒专科边界。"],
        "not_allowed_use": ["不得直接输出施工级康复医疗标准。"],
        "evidence_level": "expert_review",
    }
    match_metadata = {
        "decision": "accepted",
        "score": 7,
        "text_match": True,
        "package_hits": ["special_children_rehab_classroom"],
        "dimension_hits": ["sensory_recovery_boundary"],
        "evidence_level": "expert_review",
    }

    compact = DemandReconstructionService._compact_governed_knowledge_asset(
        card,
        match_metadata=match_metadata,
    )

    assert compact["package_ids"] == ["special_children_rehab_classroom"]
    assert compact["ontology_dimension_ids"] == ["sensory_recovery_boundary"]
    assert compact["match_metadata"] == match_metadata


def test_llm_semantic_governance_ticket_preserves_taxonomy_ids_for_asset_draft():
    service = DemandReconstructionService(require_llm=True)
    adapter_context = {"classification": {}}
    package = {
        "project_object": "????????",
        "space_candidates": [
            {"label": "special_children_rehab_classroom", "confidence": 0.9, "evidence": ["????????"]}
        ],
        "core_tensions": [
            {"title": "??????????????", "confidence": 0.86, "evidence": ["????", "????"]}
        ],
        "package_ids": ["special_children_rehab_classroom"],
        "ontology_dimension_ids": ["sensory_recovery_boundary"],
    }
    scan_result = {"result": "no_match", "matched_targets": [], "source": "llm_semantic_router"}

    service._apply_llm_semantic_governance_context(adapter_context, package, scan_result)

    ticket = adapter_context["classification"]["knowledge_gap_ticket"]
    assert ticket["package_ids"] == ["special_children_rehab_classroom"]
    assert ticket["ontology_dimension_ids"] == ["sensory_recovery_boundary"]

def test_semantic_router_prompt_exposes_controlled_scan_targets():
    prompt = DemandReconstructionService._build_semantic_router_prompt("test project")

    assert "Allowed scan targets" in prompt
    assert "media_production" in prompt
    assert "hard_constraint" in prompt
    assert "recommended_scan_targets must use these ids" in prompt

def test_llm_semantic_scan_result_uses_candidate_confidence_for_partial_match():
    package = {"novelty_level": "known"}
    candidates = [
        {
            "id": "media_production",
            "confidence": 0.62,
            "evidence": ["content production"],
        }
    ]

    scan = DemandReconstructionService._llm_semantic_scan_result(package, candidates)

    assert scan["result"] == "partial_match"
    assert scan["confidence_band"] == "medium"
    assert scan["max_confidence"] == 0.62


def test_llm_semantic_scan_result_allows_high_confidence_strong_match():
    package = {"novelty_level": "known"}
    candidates = [
        {
            "id": "media_production",
            "confidence": 0.86,
            "evidence": ["content production"],
        }
    ]

    scan = DemandReconstructionService._llm_semantic_scan_result(package, candidates)

    assert scan["result"] == "strong_match"
    assert scan["confidence_band"] == "high"
    assert scan["max_confidence"] == 0.86

def test_medium_confidence_semantic_understanding_marks_partial_coverage():
    service = DemandReconstructionService(require_llm=True)
    adapter_context = {
        "semantic_candidate_set": [],
        "archetype": {"primary": "general_project", "secondary": [], "downweighted": []},
        "classification": {},
        "context_source": {},
    }
    package = {
        "project_object": "content studio",
        "novelty_level": "known",
        "recommended_scan_targets": ["media_production"],
        "space_candidates": [
            {
                "label": "media_production",
                "confidence": 0.62,
                "evidence": ["content studio"],
            }
        ],
        "core_tensions": [
            {
                "title": "camera output versus operating efficiency",
                "confidence": 0.62,
                "evidence": ["content studio"],
            }
        ],
    }

    service._apply_llm_semantic_understanding_to_adapter_context(adapter_context, package)

    assert adapter_context["llm_semantic_scan"]["result"] == "partial_match"
    assert adapter_context["llm_semantic_scan"]["confidence_band"] == "medium"
    assert adapter_context["classification"]["coverage_gap"] is True
    assert adapter_context["classification"]["knowledge_gap_ticket"]["gap_type"] == "llm_semantic_partial_match"
    assert adapter_context["knowledge_coverage_ceiling"]["level"] == "partial_specialist"

def test_llm_semantic_scan_records_rule_algorithm_and_coverage_assets():
    service = DemandReconstructionService(require_llm=True)
    adapter_context = {
        "semantic_candidate_set": [],
        "archetype": {"primary": "general_project", "secondary": [], "downweighted": []},
        "classification": {},
        "context_source": {},
        "semantic_axes": {"critical_constraints": ["acoustics"], "subject_profiles": ["professional"]},
        "main_tensions": [
            {"title": "camera output versus operating efficiency", "score": 91}
        ],
        "knowledge_coverage_ceiling": {
            "level": "partial_specialist",
            "source": "test_coverage",
        },
    }
    package = {
        "project_object": "content studio",
        "novelty_level": "known",
        "recommended_scan_targets": ["media_production"],
        "recommended_fragment_targets": [
            {
                "group_id": "media_specialties",
                "fragment_id": "live_commerce_studio",
                "confidence": 0.82,
                "evidence": ["content studio"],
            }
        ],
        "space_candidates": [
            {
                "label": "media_production",
                "confidence": 0.82,
                "evidence": ["content studio"],
            }
        ],
    }

    service._apply_llm_semantic_understanding_to_adapter_context(adapter_context, package)

    asset_scan = adapter_context["llm_semantic_scan"]["asset_scan"]
    assert asset_scan["rule_fragments"][0]["group_id"] == "media_specialties"
    assert asset_scan["rule_fragments"][0]["fragment_id"] == "live_commerce_studio"
    assert asset_scan["semantic_axes"]["axis_ids"] == ["critical_constraints", "subject_profiles"]
    assert asset_scan["main_tensions"]["titles"] == ["camera output versus operating efficiency"]
    assert asset_scan["knowledge_coverage"]["level"] == "partial_specialist"

class _ApprovedCardStore:
    def find_approved_cards(self, **_kwargs):
        return [
            {
                "card_id": "approved_media_card",
                "title": "Approved media production card",
                "project_type": "content studio",
                "summary": "Approved knowledge for content studio demand reconstruction.",
                "evidence": ["content studio"],
                "package_ids": ["media_production"],
                "ontology_dimension_ids": ["camera_operation_boundary"],
                "evidence_level": "expert_review",
            }
        ]


def test_governed_knowledge_asset_scan_updates_llm_semantic_asset_scan():
    service = DemandReconstructionService(require_llm=True, governance_store=_ApprovedCardStore())
    adapter_context = {
        "llm_semantic_understanding": {
            "project_object": "content studio",
            "recommended_scan_targets": ["media_production"],
            "space_candidates": [
                {
                    "label": "media_production",
                    "confidence": 0.86,
                    "evidence": ["content studio"],
                }
            ],
        },
        "semantic_candidate_set": [{"id": "media_production", "label": "media production"}],
        "llm_semantic_scan": {"result": "strong_match", "matched_targets": ["media_production"]},
        "context_source": {},
    }

    service._apply_governed_knowledge_assets(
        adapter_context=adapter_context,
        session={"user_id": "tester"},
        source_message="content studio",
    )

    approved = adapter_context["llm_semantic_scan"]["asset_scan"]["approved_knowledge_assets"]
    assert approved[0]["card_id"] == "approved_media_card"
    assert approved[0]["match_metadata"]["decision"] == "accepted"
