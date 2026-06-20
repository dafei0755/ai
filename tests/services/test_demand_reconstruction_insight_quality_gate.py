from intelligent_project_analyzer.services.demand_reconstruction_service import (
    DemandReconstructionService,
)


RURAL_HOME_PROMPT = "50岁男性室内设计师，背井离乡，想在老家建一栋民居，给出建议"


def test_service_attaches_latent_model_and_insight_quality_watch() -> None:
    result = DemandReconstructionService(require_llm=False).handle_message(
        session={},
        user_message=RURAL_HOME_PROMPT,
        in_response_to_card_id=None,
        selected_option_id=None,
    )

    assert result is not None
    context = result["demand_reconstruction_context"]
    blueprint = context["blueprint"]

    latent_model = context["adapter_context"]["latent_model"]
    assert latent_model["schema_version"] == "latent_model.v1"
    assert latent_model["person_profile"][0]["relationship_to_place"] == "returning_home"

    assert "insight_quality" in blueprint
    assert blueprint["insight_quality"]["level"] in {"semantic_pass", "insight_pass", "trust_pass"}
    assert any(
        signal.get("type") == "insight_quality_watch"
        for signal in blueprint.get("governance_signals", [])
    )
