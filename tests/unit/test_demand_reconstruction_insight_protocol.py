from intelligent_project_analyzer.services.demand_reconstruction_insight_protocol import (
    DemandReconstructionInsightProtocol,
)


def test_prompt_context_preserves_llm_semantic_evidence_and_confidence():
    protocol = DemandReconstructionInsightProtocol()

    context = protocol._build_prompt_context(
        {
            "llm_semantic_understanding": {
                "space_candidates": [
                    {
                        "label": "media_production",
                        "confidence": 0.86,
                        "evidence": ["content studio"],
                    }
                ],
                "core_tensions": [
                    {
                        "title": "camera output versus operating efficiency",
                        "confidence": 0.77,
                        "evidence": ["content studio"],
                    }
                ],
            },
            "llm_semantic_scan": {
                "result": "strong_match",
                "confidence_band": "high",
                "max_confidence": 0.86,
            },
        }
    )

    semantic_package = context["llm_semantic_understanding"]
    assert semantic_package["space_candidates"][0]["label"] == "media_production"
    assert semantic_package["space_candidates"][0]["confidence"] == 0.86
    assert semantic_package["space_candidates"][0]["evidence"] == ["content studio"]
    assert semantic_package["core_tensions"][0]["confidence"] == 0.77
    assert semantic_package["core_tensions"][0]["evidence"] == ["content studio"]

def test_prompt_context_preserves_llm_semantic_asset_scan():
    protocol = DemandReconstructionInsightProtocol()

    context = protocol._build_prompt_context(
        {
            "llm_semantic_scan": {
                "result": "strong_match",
                "matched_targets": ["media_production"],
                "asset_scan": {
                    "rule_fragments": [
                        {"group_id": "media_specialties", "fragment_id": "live_commerce_studio"}
                    ],
                    "approved_knowledge_assets": [
                        {"card_id": "approved_media_card", "evidence_level": "expert_review"}
                    ],
                },
            }
        }
    )

    asset_scan = context["llm_semantic_scan"]["asset_scan"]
    assert asset_scan["rule_fragments"][0]["group_id"] == "media_specialties"
    assert asset_scan["approved_knowledge_assets"][0]["card_id"] == "approved_media_card"
