from intelligent_project_analyzer.services.demand_reconstruction_context_adapter import (
    DemandReconstructionContextAdapter,
)
from intelligent_project_analyzer.services.latent_model_adapter import LatentModelAdapter


def test_latent_model_adapter_preserves_q16_high_value_signals() -> None:
    source = "50岁男性室内设计师，背井离乡多年，想在老家建一栋民居，给出建议"
    adapter_context = DemandReconstructionContextAdapter().build(source)

    latent_model = LatentModelAdapter().build(
        source_message=source,
        adapter_context=adapter_context,
    ).model_dump(mode="json")

    assert latent_model["mode"] == "project_reconstruction"
    assert latent_model["person_profile"][0]["professional_identity"] == "interior_designer"
    assert latent_model["person_profile"][0]["relationship_to_place"] == "returning_home"
    assert "故乡关系" in latent_model["existential_job"]["statement"]
    assert latent_model["forbidden_capture_paths"]
    assert len(latent_model["evidence_index"]) >= 3
