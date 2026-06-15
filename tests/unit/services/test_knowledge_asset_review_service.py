import json

import pytest

from intelligent_project_analyzer.services.knowledge_asset_review_service import (
    KnowledgeAssetReviewService,
)


def _candidate_payload(**overrides):
    payload = {
        "source_type": "external_generation",
        "source_machine_id": "local-rd-node-01",
        "batch_id": "batch-i01",
        "asset_type": "KnowledgeCard",
        "title": "水吧台高度分层判断卡",
        "payload": {
            "summary": "水吧台不应按单一高度处理，应拆分制作、湿区和交接层。",
            "decision_point": "吧台高度是否可以统一锁定",
        },
        "package_ids": ["tea_bar_counter_dimension_pack"],
        "ontology_dimension_ids": ["FunctionProgram", "MaterialMEP"],
        "source_evidence_level": "E2_research",
        "provenance": {
            "source_path": "I01_BarCounterDimension_水吧台尺度_v2.2_202606.md"
        },
    }
    payload.update(overrides)
    return payload


def test_submit_external_candidate_creates_reviewable_asset(tmp_path):
    service = KnowledgeAssetReviewService(root_dir=tmp_path)

    candidate = service.submit_candidate(_candidate_payload())

    assert candidate["lifecycle_status"] == "needs_review"
    assert candidate["source_type"] == "external_generation"
    assert candidate["asset_type"] == "KnowledgeCard"
    assert candidate["asset_id"].startswith("KA-")
    assert candidate["checksum"]
    assert (tmp_path / "candidates" / f"{candidate['asset_id']}.json").exists()

    listed = service.list_candidates(status="needs_review")
    assert [item["asset_id"] for item in listed] == [candidate["asset_id"]]


def test_approve_candidate_writes_approved_asset_and_runtime_reads_only_approved(tmp_path):
    service = KnowledgeAssetReviewService(root_dir=tmp_path)
    candidate = service.submit_candidate(_candidate_payload(asset_id="KA-I01-HEIGHT"))

    assert service.find_approved_assets(package_ids=["tea_bar_counter_dimension_pack"]) == []

    approved = service.approve_candidate(
        candidate["asset_id"],
        reviewer_id="admin",
        reviewer_note="证据链完整，允许条件级调用。",
    )

    assert approved["lifecycle_status"] == "approved"
    assert approved["reviewer_id"] == "admin"
    assert (tmp_path / "approved" / "KA-I01-HEIGHT.json").exists()

    runtime_assets = service.find_approved_assets(
        package_ids=["tea_bar_counter_dimension_pack"]
    )
    assert [asset["asset_id"] for asset in runtime_assets] == ["KA-I01-HEIGHT"]

    with (tmp_path / "indexes" / "approved_index.json").open(
        "r", encoding="utf-8"
    ) as f:
        index = json.load(f)
    assert index["assets"][0]["asset_id"] == "KA-I01-HEIGHT"


def test_filtered_runtime_lookup_returns_empty_on_miss(tmp_path):
    service = KnowledgeAssetReviewService(root_dir=tmp_path)
    candidate = service.submit_candidate(_candidate_payload(asset_id="KA-I01-DEPTH"))
    service.approve_candidate(candidate["asset_id"], reviewer_id="admin")

    assert service.find_approved_assets(package_ids=["unknown_pack"]) == []
    assert service.find_approved_assets(asset_type="ValidationRule") == []


def test_reject_candidate_keeps_asset_out_of_approved_runtime_store(tmp_path):
    service = KnowledgeAssetReviewService(root_dir=tmp_path)
    candidate = service.submit_candidate(_candidate_payload(asset_id="KA-I01-REJECT"))

    rejected = service.reject_candidate(
        candidate["asset_id"], reviewer_id="admin", reason="证据不足"
    )

    assert rejected["lifecycle_status"] == "rejected"
    assert not (tmp_path / "approved" / "KA-I01-REJECT.json").exists()
    assert service.find_approved_assets() == []


def test_internal_settlement_submission_is_proposal_not_approved_asset(tmp_path):
    service = KnowledgeAssetReviewService(root_dir=tmp_path)

    proposal = service.submit_candidate(
        _candidate_payload(
            asset_id="KA-SETTLEMENT-001",
            source_type="internal_settlement",
            asset_type="PromotionCandidate",
            related_consumption_id="CL-001",
            related_settlement_event_id="SE-001",
            payload={
                "summary": "台下设备开门包络多次造成后场拥堵，建议强化规则。",
                "attribution": "card_validated",
            },
        )
    )

    assert proposal["source_type"] == "internal_settlement"
    assert proposal["asset_type"] == "PromotionCandidate"
    assert proposal["lifecycle_status"] == "needs_review"
    assert service.find_approved_assets() == []


def test_record_consumption_event_separates_used_cards_from_recalled_not_used(tmp_path):
    service = KnowledgeAssetReviewService(root_dir=tmp_path)

    consumption = service.record_consumption_event(
        {
            "project_id": "project-tea-001",
            "session_id": "session-001",
            "consumed_asset_ids": ["KA-USED-001"],
            "recalled_not_used_asset_ids": ["KA-NOT-USED-001"],
            "missing_slots": ["floor_plan"],
            "ceiling_level": "condition_level",
            "answer_trace": {"reason": "used for first-round advisory answer"},
        }
    )

    assert consumption["consumption_id"].startswith("CL-")
    assert consumption["consumed_asset_ids"] == ["KA-USED-001"]
    assert consumption["recalled_not_used_asset_ids"] == ["KA-NOT-USED-001"]
    assert (tmp_path / "consumption_ledger" / f"{consumption['consumption_id']}.json").exists()


def test_settlement_event_with_card_wrong_attribution_creates_internal_review_candidate(tmp_path):
    service = KnowledgeAssetReviewService(root_dir=tmp_path)
    consumption = service.record_consumption_event(
        {
            "project_id": "project-tea-001",
            "consumed_asset_ids": ["KA-BAR-COUNTER-001"],
        }
    )

    event = service.submit_settlement_event(
        {
            "consumption_id": consumption["consumption_id"],
            "asset_id": "KA-BAR-COUNTER-001",
            "outcome": "refute",
            "attribution": "card_wrong",
            "evidence_strength": "L1_measured_data",
            "observation": "Actual peak workflow repeatedly blocked at the back counter.",
            "promotion_candidate": {
                "asset_type": "PromotionCandidate",
                "title": "Back counter clearance rule needs revision",
                "payload": {
                    "summary": "Observed projects show the previous clearance rule is too loose.",
                },
                "package_ids": ["tea_bar_counter_dimension_pack"],
                "ontology_dimension_ids": ["FunctionProgram", "OperationFlow"],
            },
        }
    )

    assert event["settlement_event_id"].startswith("SE-")
    assert event["attribution"] == "card_wrong"
    assert (tmp_path / "settlement_events" / f"{event['settlement_event_id']}.json").exists()

    proposals = service.list_candidates(source_type="internal_settlement")
    assert len(proposals) == 1
    assert proposals[0]["lifecycle_status"] == "needs_review"
    assert proposals[0]["related_settlement_event_id"] == event["settlement_event_id"]
    assert proposals[0]["related_consumption_id"] == consumption["consumption_id"]


def test_settlement_event_with_recall_wrong_attribution_does_not_create_candidate(tmp_path):
    service = KnowledgeAssetReviewService(root_dir=tmp_path)

    event = service.submit_settlement_event(
        {
            "consumption_id": "CL-UNKNOWN",
            "asset_id": "KA-RECALL-MISS",
            "outcome": "inapplicable",
            "attribution": "recall_wrong",
            "evidence_strength": "L2_user_feedback",
            "observation": "The card was recalled for a scenario it did not fit.",
            "promotion_candidate": {
                "asset_type": "PromotionCandidate",
                "title": "This should not be promoted",
                "payload": {"summary": "Recall issue, not card knowledge."},
            },
        }
    )

    assert event["attribution"] == "recall_wrong"
    assert service.list_settlement_events(attribution="recall_wrong")[0]["settlement_event_id"] == event["settlement_event_id"]
    assert service.list_candidates(source_type="internal_settlement") == []


def test_submit_candidate_requires_review_source_and_asset_type(tmp_path):
    service = KnowledgeAssetReviewService(root_dir=tmp_path)

    with pytest.raises(ValueError, match="source_type"):
        service.submit_candidate({"asset_type": "KnowledgeCard"})

    with pytest.raises(ValueError, match="asset_type"):
        service.submit_candidate({"source_type": "external_generation"})
