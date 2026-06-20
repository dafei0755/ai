from intelligent_project_analyzer.services.demand_reconstruction_insight_protocol import (
    DemandReconstructionInsightProtocol,
)


def test_insight_protocol_prompt_carries_latent_model_and_evidence_bound_affect() -> None:
    prompt = DemandReconstructionInsightProtocol().build_prompt(
        adapter_context={
            "source_message": "50岁男性室内设计师，背井离乡，想在老家建一栋民居",
            "project_type": "personal_residential",
            "latent_model": {
                "person_profile": [
                    {
                        "life_stage": "mid_late_career",
                        "professional_identity": "interior_designer",
                        "relationship_to_place": "returning_home",
                        "evidence_refs": ["e1", "e2", "e3"],
                    }
                ],
                "evidence_bound_affect": [
                    {"claim": "身心安放", "allowed_terms": ["返乡", "身心安放"], "evidence_refs": ["e3"]}
                ],
                "forbidden_capture_paths": [
                    {"id": "style_over_capture", "rule": "不得把返乡民居压缩成风格标签"}
                ],
            },
        },
        rule_plan={"task_reframe": "规则蓝图", "key_forks": [], "unknowns": [], "sections": []},
    )

    assert "latent_model" in prompt
    assert "person_profile" in prompt
    assert "evidence_bound_affect" in prompt
    assert "forbidden_capture_paths" in prompt
    assert "有证据的情感" in prompt
    assert "空洞套话" in prompt


def test_quality_gate_allows_evidence_bound_affect_but_rejects_empty_cliche() -> None:
    protocol = DemandReconstructionInsightProtocol()

    assert protocol.passes_quality_gate(
        {
            "task_reframe": "这不是普通民居风格问题，而是返乡设计师把职业后半场与身心安放重新放进故乡关系。",
            "project_viability_judgment": "先判断长期生活方式，再判断形式表达。",
            "primary_risk": "如果只做风格表达，会让作品化住宅压过真实居住。",
            "sections": [{"title": "读人", "body": "基于50岁、设计师、背井离乡这些证据判断。", "items": ["返乡", "设计师"]}],
            "key_forks": ["长期自住还是阶段性返乡"],
            "unknowns": ["家庭成员结构"],
            "next_question": "这栋房子一年住多久",
        }
    )

    assert not protocol.passes_quality_gate(
        {
            "task_reframe": "这里要打造温馨舒适并有归属感的品质生活空间，让用户放松身心。",
            "project_viability_judgment": "判断生活品质。",
            "primary_risk": "表达太泛。",
            "sections": [{"title": "建议", "body": "温馨舒适", "items": ["功能齐全"]}],
            "key_forks": ["风格"],
            "unknowns": ["预算"],
            "next_question": "喜欢什么风格",
        }
    )
