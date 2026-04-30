import pytest

from intelligent_project_analyzer.core.domain_objects import (
    FloorPlanFactElement,
    FloorPlanFacts,
    SPGFlow,
    SPGZone,
    SpatialProgramGraph,
)
from intelligent_project_analyzer.services.floor_plan_layout_engine import (
    generate_layout_variants,
    list_supported_operations,
)
from intelligent_project_analyzer.api.routes.floor_plan_layout_routes import (
    LayoutVariantRequest,
    generate_floor_plan_variants,
)


def _sample_spg() -> SpatialProgramGraph:
    return SpatialProgramGraph(
        spg_id="spg-plan-sandbox-smoke",
        space_type="山地民宿",
        version="v1.2",
        zones=[
            SPGZone(
                zone_id="arrival",
                name="到达前厅",
                function="arrival",
                approx_area_m2=18,
                privacy_level="public",
                required_adjacencies=["public_lounge"],
            ),
            SPGZone(
                zone_id="public_lounge",
                name="景观公区",
                function="lounge",
                approx_area_m2=42,
                privacy_level="public",
                orientation_preference="best_view",
            ),
            SPGZone(
                zone_id="guest_room",
                name="客房组团",
                function="guestroom",
                approx_area_m2=80,
                privacy_level="private",
                forbidden_adjacencies=["service"],
            ),
            SPGZone(
                zone_id="service",
                name="后勤",
                function="service",
                approx_area_m2=20,
                privacy_level="service",
                required_adjacencies=["arrival"],
            ),
        ],
        flows=[
            SPGFlow(flow_id="guest_route", name="住客动线", flow_type="public", from_zone="arrival", to_zone="guest_room"),
            SPGFlow(flow_id="service_route", name="后勤动线", flow_type="service", from_zone="service", to_zone="arrival"),
        ],
    )


def test_generate_layout_variants_returns_strategy_distinct_candidates():
    facts = FloorPlanFacts(
        facts_id="facts-smoke",
        session_id="session-smoke",
        boundary=[[0, 0], [1, 0], [1, 1], [0, 1]],
        immutable_elements=[
            FloorPlanFactElement(
                element_id="core-1",
                element_type="core",
                geometry=[[0.45, 0.45], [0.55, 0.45], [0.55, 0.55], [0.45, 0.55]],
                locked=True,
                confidence=0.86,
            )
        ],
    )

    package = generate_layout_variants(_sample_spg(), facts=facts, session_id="session-smoke")

    assert len(package.variants) == 3
    assert {variant.intent.strategy for variant in package.variants} == {
        "conservative_low_change",
        "functional_efficiency",
        "experience_value",
    }
    assert package.constraint_graph.facts_id == "facts-smoke"
    assert package.constraint_graph.locked_zone_ids == ["core-1"]
    assert len(package.version_graph.nodes) == 3
    assert all(variant.layout.based_on_spg_version == "v1.2" for variant in package.variants)
    assert all(variant.layout.spaces for variant in package.variants)
    assert all(variant.layout.explanation for variant in package.variants)


def test_functional_efficiency_variant_keeps_spg_flows():
    package = generate_layout_variants(_sample_spg(), session_id="session-flow")
    efficiency = next(
        variant for variant in package.variants
        if variant.intent.strategy == "functional_efficiency"
    )

    assert efficiency.layout.circulation["guest_route"] == ["arrival", "guest_room"]
    assert efficiency.layout.circulation["service_route"] == ["service", "arrival"]
    assert efficiency.layout.score.functional_efficiency >= 80


def test_supported_operations_include_user_command_primitives():
    operations = set(list_supported_operations())

    assert "lock_space" in operations
    assert "merge_strategy" in operations
    assert "shorten_path" in operations
    assert "reduce_cost" in operations


@pytest.mark.asyncio
async def test_generate_floor_plan_variants_route_contract():
    request = LayoutVariantRequest(
        session_id="session-route",
        spg=_sample_spg(),
        variant_count=2,
    )

    package = await generate_floor_plan_variants(request)

    assert package.session_id == "session-route"
    assert len(package.variants) == 2
    assert package.variants[0].layout.session_id == "session-route"
