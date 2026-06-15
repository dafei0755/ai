import pytest
import os

os.environ["DEBUG"] = "false"
from intelligent_project_analyzer.api import admin_routes
from intelligent_project_analyzer.services.knowledge_asset_review_service import (
    KnowledgeAssetReviewService,
)


@pytest.fixture
def review_service(tmp_path):
    return KnowledgeAssetReviewService(root_dir=tmp_path)


@pytest.fixture(autouse=True)
def patch_review_service(monkeypatch, review_service):
    monkeypatch.setattr(
        admin_routes,
        "get_knowledge_asset_review_service",
        lambda: review_service,
        raising=False,
    )


@pytest.mark.asyncio
async def test_submit_and_approve_knowledge_asset_candidate_via_admin_routes(review_service):
    response = await admin_routes.submit_knowledge_asset_candidate(
        {
            "asset_id": "KA-ROUTE-I01",
            "source_type": "external_generation",
            "source_machine_id": "local-rd-node-01",
            "asset_type": "KnowledgeCard",
            "title": "水吧台高度分层判断卡",
            "payload": {"summary": "制作、湿区、交接层应分开判断。"},
            "package_ids": ["tea_bar_counter_dimension_pack"],
        },
        admin={"username": "reviewer"},
    )

    assert response["status"] == "success"
    assert response["item"]["lifecycle_status"] == "needs_review"

    approved = await admin_routes.approve_knowledge_asset_candidate(
        "KA-ROUTE-I01",
        {"reviewer_note": "允许条件级调用"},
        admin={"username": "reviewer"},
    )

    assert approved["status"] == "success"
    assert approved["item"]["lifecycle_status"] == "approved"
    assert review_service.find_approved_assets(package_ids=["tea_bar_counter_dimension_pack"])


@pytest.mark.asyncio
async def test_internal_settlement_route_creates_review_proposal_only(review_service):
    response = await admin_routes.submit_knowledge_asset_candidate(
        {
            "asset_id": "KA-ROUTE-SETTLEMENT",
            "source_type": "internal_settlement",
            "asset_type": "PromotionCandidate",
            "title": "设备开门包络规则强化提案",
            "related_consumption_id": "CL-001",
            "related_settlement_event_id": "SE-001",
            "payload": {"summary": "多次反馈显示设备开门阻断后场。"},
        },
        admin={"username": "system"},
    )

    assert response["item"]["lifecycle_status"] == "needs_review"
    assert response["item"]["source_type"] == "internal_settlement"
    assert review_service.find_approved_assets() == []


@pytest.mark.asyncio
async def test_list_knowledge_asset_candidates_filters_status(review_service):
    review_service.submit_candidate(
        {
            "asset_id": "KA-LIST-1",
            "source_type": "external_generation",
            "asset_type": "KnowledgeCard",
            "title": "待审核卡",
        }
    )
    review_service.submit_candidate(
        {
            "asset_id": "KA-LIST-2",
            "source_type": "external_generation",
            "asset_type": "KnowledgeCard",
            "title": "被拒绝卡",
        }
    )
    review_service.reject_candidate("KA-LIST-2", reviewer_id="reviewer", reason="重复")

    response = await admin_routes.list_knowledge_asset_candidates(
        status="needs_review",
        source_type=None,
        asset_type=None,
        admin={"username": "reviewer"},
    )

    assert response["total"] == 1
    assert response["items"][0]["asset_id"] == "KA-LIST-1"


@pytest.mark.asyncio
async def test_consumption_and_settlement_routes_create_internal_review_candidate(review_service):
    consumption = await admin_routes.record_knowledge_asset_consumption_event(
        {
            "project_id": "project-tea-route",
            "consumed_asset_ids": ["KA-ROUTE-CONSUMED"],
            "recalled_not_used_asset_ids": ["KA-ROUTE-NOT-USED"],
            "ceiling_level": "condition_level",
        },
        admin={"username": "runtime"},
    )

    assert consumption["status"] == "success"
    assert consumption["item"]["consumed_asset_ids"] == ["KA-ROUTE-CONSUMED"]
    assert consumption["item"]["recalled_not_used_asset_ids"] == ["KA-ROUTE-NOT-USED"]

    settlement = await admin_routes.submit_knowledge_asset_settlement_event(
        {
            "consumption_id": consumption["item"]["consumption_id"],
            "asset_id": "KA-ROUTE-CONSUMED",
            "outcome": "refute",
            "attribution": "card_wrong",
            "evidence_strength": "L1_measured_data",
            "observation": "Measured project data refutes the prior condition boundary.",
            "promotion_candidate": {
                "asset_type": "PromotionCandidate",
                "title": "Route-level promotion candidate",
                "payload": {"summary": "Promote only after human review."},
            },
        },
        admin={"username": "runtime"},
    )

    assert settlement["status"] == "success"
    assert settlement["item"]["settlement_event_id"].startswith("SE-")
    assert settlement["promotion_candidate"]["source_type"] == "internal_settlement"

    candidates = await admin_routes.list_knowledge_asset_candidates(
        status="needs_review",
        source_type="internal_settlement",
        asset_type=None,
        admin={"username": "reviewer"},
    )
    assert candidates["total"] == 1
    assert candidates["items"][0]["related_settlement_event_id"] == settlement["item"]["settlement_event_id"]


@pytest.mark.asyncio
async def test_settlement_route_keeps_recall_wrong_out_of_candidate_queue(review_service):
    settlement = await admin_routes.submit_knowledge_asset_settlement_event(
        {
            "consumption_id": "CL-ROUTE-UNKNOWN",
            "asset_id": "KA-ROUTE-NOT-FIT",
            "outcome": "inapplicable",
            "attribution": "recall_wrong",
            "evidence_strength": "L2_user_feedback",
            "observation": "The card was recalled too broadly.",
            "promotion_candidate": {
                "asset_type": "PromotionCandidate",
                "title": "Should not become candidate",
                "payload": {"summary": "Recall issue only."},
            },
        },
        admin={"username": "runtime"},
    )

    assert settlement["status"] == "success"
    assert settlement["promotion_candidate"] is None
    assert review_service.list_candidates(source_type="internal_settlement") == []


@pytest.mark.asyncio
async def test_scheme_advisor_golden_review_status_route_is_read_only_admin_queue():
    response = await admin_routes.get_scheme_advisor_golden_review_status(
        admin={"username": "reviewer"},
    )

    assert response["status"] == "success"
    assert response["review_status"] == "needs_human_review"
    assert response["next_action"] == "fill_required_gold_fields"
    assert response["completion"]["total_rows"] == 29
    assert response["quality_gate"]["gate_status"] == "fail"
    assert response["terminal_copy_guardrail"]["summary"]["violation_count"] == 0
    assert response["terminal_copy_guardrail"]["violation_policy"] == "fail_review"
    assert response["suggestions"]["summary"]["total"] == 29
    assert response["suggestions"]["summary"]["ready_for_fast_review"] == 3
    assert response["suggestions"]["summary"]["needs_human_decision"] == 26
    assert len(response["suggestions"]["items"]) == 29
    assert "gold_expected_project_type" not in response["suggestions"]["items"][0]
    assert response["systemic_remediation"]["summary"]["systemic_actions"] == 8
    assert response["systemic_remediation"]["summary"]["must_not_hardcode_cases"] is True
    modules = {item["module"] for item in response["systemic_remediation"]["items"]}
    assert "SpaceClassificationService" in modules
    assert "SchemeAdvisorEntryService" in modules
    assert "FrontendHumanLanguageMapping" in modules
