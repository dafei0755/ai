from intelligent_project_analyzer.core.latent_model import (
    EvidenceItem,
    LatentModel,
    LatentVariableItem,
)


def test_latent_model_requires_evidence_for_inferred_variables() -> None:
    model = LatentModel(
        mode="project_reconstruction",
        input_frame={"raw_text": "50岁男性室内设计师，背井离乡，想在老家建一栋民居"},
        latent_variables={
            "identity_drivers": [
                LatentVariableItem(
                    id="professional_identity",
                    label="职业身份",
                    value="interior_designer",
                    confidence=0.88,
                    evidence_refs=["e2"],
                    source="inferred",
                )
            ]
        },
        tensions=[{"id": "return_vs_daily_life", "statement": "返乡象征与日常居住之间的张力"}],
        hypotheses=[{"id": "h1", "statement": "这栋民居可能承载职业后半场的自我安放"}],
        uncertainty_ledger=[{"id": "u1", "question": "长期居住还是阶段性返乡"}],
        decision_frontier={"next_question": "这栋房子一年会住多久"},
        evidence_index=[
            EvidenceItem(
                evidence_id="e1",
                excerpt="50岁",
                source_span={"start": 0, "end": 3},
                evidence_type="explicit",
                reliability="high",
            ),
            EvidenceItem(
                evidence_id="e2",
                excerpt="室内设计师",
                source_span={"start": 5, "end": 10},
                evidence_type="explicit",
                reliability="high",
            ),
        ],
        quality_gate={"evidence_bound": True},
        provenance={"source": "unit_test"},
    )

    assert model.schema_version == "latent_model.v1"
    assert model.latent_variables["identity_drivers"][0].evidence_refs == ["e2"]
