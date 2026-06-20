from intelligent_project_analyzer.services.demand_reconstruction_output_planner import DemandReconstructionOutputPlanner


def test_public_cultural_default_blueprint_uses_primary_registry_fragment():
    planner = DemandReconstructionOutputPlanner()
    context = {
        "source_message": "??????????????????????????????????????",
        "space_label": "??????",
        "project_type_name": "??????",
        "archetype": {"primary": "public_cultural_experience", "secondary": [], "downweighted": []},
        "semantic_candidate_set": [
            {
                "id": "public_cultural_experience",
                "score": 120,
                "role": "primary",
                "evidence": ["??????"],
                "counter_evidence": [],
            }
        ],
        "classification": {},
        "semantic_axes": [],
        "main_tensions": [],
        "missing_slots": [],
        "context_source": {},
    }

    plan = planner.build_plan(context)

    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:primary_archetypes.public_cultural_experience"
    assert "????" in plan["task_reframe"]
    assert plan["project_viability_judgment"]
    assert plan["primary_risk"]

def test_life_identity_default_blueprint_uses_primary_registry_fragment():
    planner = DemandReconstructionOutputPlanner()
    context = {
        "source_message": "neutral private residence demand reconstruction",
        "space_label": "private residence",
        "project_type_name": "residential project",
        "archetype": {"primary": "life_identity", "secondary": [], "downweighted": []},
        "semantic_candidate_set": [
            {
                "id": "life_identity",
                "score": 120,
                "role": "primary",
                "evidence": ["private residence"],
                "counter_evidence": [],
            }
        ],
        "classification": {},
        "semantic_axes": [],
        "main_tensions": [],
        "missing_slots": [],
        "context_source": {},
    }

    plan = planner.build_plan(context)

    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:primary_archetypes.life_identity"
    assert plan["task_reframe"]
    assert plan["project_viability_judgment"]
    assert plan["primary_risk"]

def test_media_production_default_blueprint_uses_primary_registry_fragment():
    planner = DemandReconstructionOutputPlanner()
    context = {
        "source_message": "neutral content production demand reconstruction",
        "space_label": "content studio",
        "project_type_name": "media project",
        "archetype": {"primary": "media_production", "secondary": [], "downweighted": []},
        "semantic_candidate_set": [
            {
                "id": "media_production",
                "score": 120,
                "role": "primary",
                "evidence": ["content production"],
                "counter_evidence": [],
            }
        ],
        "classification": {},
        "semantic_axes": [],
        "main_tensions": [],
        "missing_slots": [],
        "context_source": {},
    }

    plan = planner.build_plan(context)

    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:primary_archetypes.media_production"
    assert plan["task_reframe"]
    assert plan["project_viability_judgment"]
    assert plan["primary_risk"]

def test_hard_constraint_default_blueprint_uses_primary_registry_fragment():
    planner = DemandReconstructionOutputPlanner()
    context = {
        "source_message": "neutral technical constraint demand reconstruction",
        "space_label": "technical project",
        "project_type_name": "constraint project",
        "archetype": {"primary": "hard_constraint", "secondary": [], "downweighted": []},
        "semantic_candidate_set": [
            {
                "id": "hard_constraint",
                "score": 120,
                "role": "primary",
                "evidence": ["technical constraint"],
                "counter_evidence": [],
            }
        ],
        "classification": {},
        "semantic_axes": [],
        "main_tensions": [],
        "missing_slots": [],
        "context_source": {},
    }

    plan = planner.build_plan(context)

    assert plan["brief_handoff_slots"]["fragment_source"] == "registry:primary_archetypes.hard_constraint"
    assert plan["task_reframe"]
    assert plan["project_viability_judgment"]
    assert plan["primary_risk"]

def test_partial_specialist_coverage_softens_blueprint_commitment():
    planner = DemandReconstructionOutputPlanner()
    context = {
        "source_message": "medium confidence content studio demand reconstruction",
        "space_label": "content studio",
        "project_type_name": "media project",
        "archetype": {"primary": "media_production", "secondary": [], "downweighted": []},
        "semantic_candidate_set": [
            {
                "id": "media_production",
                "score": 120,
                "role": "primary",
                "evidence": ["content studio"],
                "counter_evidence": [],
            }
        ],
        "classification": {},
        "semantic_axes": [],
        "main_tensions": [],
        "missing_slots": [],
        "knowledge_coverage_ceiling": {
            "level": "partial_specialist",
            "user_visible_note": "partial specialist coverage only",
        },
        "context_source": {},
    }

    plan = planner.build_plan(context)

    assert plan["coverage_level"] == "partial_specialist"
    assert "\u90bb\u8fd1\u8fc1\u79fb" in plan["project_viability_judgment"]
    assert "\u5b8c\u6574\u4e13\u79d1\u7ed3\u8bba" in plan["primary_risk"]
