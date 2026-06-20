from intelligent_project_analyzer.services.demand_reconstruction_insight_quality import (
    DemandReconstructionInsightQualityEvaluator,
)


SOURCE = "50岁男性室内设计师，背井离乡多年，想在老家建一栋民居，给出建议"


def test_insight_quality_flags_style_capture_and_missing_identity_signals() -> None:
    result = DemandReconstructionInsightQualityEvaluator().evaluate(
        source_message=SOURCE,
        semantic_package={},
        latent_model={},
        blueprint={"task_reframe": "为乡村民居给出风格标签与施工建议"},
        visible_reply="这个问题主要是风格标签和施工条件匹配。",
    )

    assert result["level"] == "semantic_pass"
    assert "life_stage" in result["missing_high_value_signals"]
    assert "professional_identity" in result["missing_high_value_signals"]
    assert "returning_home" in result["missing_high_value_signals"]
    assert result["anti_capture_checks"]["style_over_capture"]["status"] == "fail"


def test_insight_quality_rewards_evidence_bound_affect() -> None:
    result = DemandReconstructionInsightQualityEvaluator().evaluate(
        source_message=SOURCE,
        semantic_package={},
        latent_model={
            "person_profile": [
                {
                    "life_stage": "mid_life",
                    "professional_identity": "interior_designer",
                    "relationship_to_place": "returning_home",
                    "evidence_refs": ["e1", "e2", "e3"],
                }
            ],
            "evidence_bound_affect": [
                {"claim": "身心安放", "allowed_terms": ["返乡", "身心安放"], "evidence_refs": ["e3"]}
            ],
        },
        blueprint={"task_reframe": "这不是普通乡村民居，而是返乡设计师的身心安放容器。"},
        visible_reply="这不是简单建房，而是返乡设计师在职业后半场处理故乡关系与身心安放。",
    )

    assert result["level"] == "trust_pass"
    assert result["missing_high_value_signals"] == []
    assert result["evidence_bound_affect"]["status"] == "pass"
