import json

import yaml

from sqlalchemy import create_engine, select

from intelligent_project_analyzer.services import knowledge_governance_store as kg_store
from intelligent_project_analyzer.services.knowledge_governance_store import (
    KnowledgeAssetDraftRecord,
    KnowledgeGovernanceStore,
)


def _sqlite_store() -> KnowledgeGovernanceStore:
    engine = create_engine("sqlite:///:memory:")
    store = KnowledgeGovernanceStore(engine=engine)
    store.create_all()
    return store


def test_enqueue_review_item_persists_pending_governance_queue_record():
    store = _sqlite_store()

    item = store.enqueue_review_item(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        user_id="user-1",
        module="demand_reconstruction",
        object_type="governance_signal",
        object_id="signal-001",
        title="知识缺口线索",
        source="llm_semantic_router",
        risk="P2",
        target_admin_path="/admin/review-queue?queue=knowledge_asset_review",
        metadata={"code": "knowledge_gap_ticket", "review_queue": "knowledge_asset_review"},
        created_by="runtime",
    )

    assert item["id"] == "demand_reconstruction:signal-001"
    assert item["review_status"] == "pending"
    listed = store.list_review_items(tenant_id="tenant-1", workspace_id="workspace-1")
    assert len(listed) == 1
    assert listed[0]["object_id"] == "signal-001"
    assert listed[0]["metadata"]["code"] == "knowledge_gap_ticket"


def test_enqueue_review_item_returns_updated_record_not_last_queue_item():
    store = _sqlite_store()

    common = {
        "tenant_id": "tenant-1",
        "workspace_id": "workspace-1",
        "user_id": "user-1",
        "module": "demand_reconstruction",
        "object_type": "governance_signal",
        "source": "llm_semantic_router",
        "risk": "P2",
        "target_admin_path": "/admin/review-queue?queue=knowledge_asset_review",
        "created_by": "runtime",
    }
    store.enqueue_review_item(
        **common,
        object_id="signal-001",
        title="first title",
        metadata={"code": "first"},
    )
    store.enqueue_review_item(
        **common,
        object_id="signal-002",
        title="second title",
        metadata={"code": "second"},
    )

    updated = store.enqueue_review_item(
        **common,
        object_id="signal-001",
        title="updated first title",
        metadata={"code": "updated"},
    )

    assert updated["id"] == "demand_reconstruction:signal-001"
    assert updated["title"] == "updated first title"
    assert updated["metadata"]["code"] == "updated"


def test_update_review_item_status_moves_item_out_of_pending_queue_and_audits():
    store = _sqlite_store()
    store.enqueue_review_item(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        user_id="user-1",
        module="demand_reconstruction",
        object_type="governance_signal",
        object_id="signal-001",
        title="知识缺口线索",
        source="llm_semantic_router",
        risk="P2",
        target_admin_path="/admin/review-queue?queue=knowledge_asset_review",
        metadata={"code": "knowledge_gap_ticket", "review_queue": "knowledge_asset_review"},
        created_by="runtime",
    )

    updated = store.update_review_item_status(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        item_id="demand_reconstruction:signal-001",
        review_status="approved",
        reviewer_id="reviewer-1",
        note="转入知识资产候选建设",
    )

    assert updated["review_status"] == "approved"
    assert updated["reviewer_note"] == "转入知识资产候选建设"
    assert store.list_review_items(tenant_id="tenant-1", workspace_id="workspace-1") == []
    approved = store.list_review_items(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        review_status="approved",
    )
    assert [item["id"] for item in approved] == ["demand_reconstruction:signal-001"]
    audit_actions = [event["action"] for event in store.list_audit_events(tenant_id="tenant-1")]
    assert "update_governance_review_item_status" in audit_actions


def test_approving_new_fragment_candidate_creates_blueprint_fragment_followup_draft():
    store = _sqlite_store()
    store.enqueue_review_item(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        user_id="user-1",
        module="demand_reconstruction",
        object_type="governance_signal",
        object_id="new_fragment_candidate:signal-001",
        title="评估是否需要为电竞直播训练间沉淀新的需求重构规则碎片。",
        source="llm_semantic_router",
        risk="P2",
        target_admin_path="/admin/review-queue?queue=blueprint_fragment_review",
        metadata={
            "code": "new_fragment_candidate",
            "review_queue": "blueprint_fragment_review",
            "signal": {
                "code": "new_fragment_candidate",
                "fragment_id": "esports_live_training_room",
                "project_object": "电竞直播训练间",
                "summary": "评估是否需要为电竞直播训练间沉淀新的需求重构规则碎片。",
                "evidence": ["电竞直播训练间", "隔音、灯光、散热"],
            },
        },
        created_by="runtime",
    )

    updated = store.update_review_item_status(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        item_id="demand_reconstruction:new_fragment_candidate:signal-001",
        review_status="approved",
        reviewer_id="reviewer-1",
        note="同意进入碎片草案",
    )

    followup = updated["metadata"]["governance_followup"]
    assert followup["type"] == "blueprint_fragment_candidate_draft"
    assert followup["status"] == "draft"
    assert followup["blueprint_fragment_draft_id"].startswith("blueprint_fragment_")
    assert followup["draft"]["fragment_id"] == "esports_live_training_room"
    assert followup["draft"]["project_object"] == "电竞直播训练间"
    assert followup["draft"]["evidence"] == ["电竞直播训练间", "隔音、灯光、散热"]
    assert followup["next_admin_action"] == "review_blueprint_fragment_draft"

    assert hasattr(kg_store, "BlueprintFragmentDraftRecord")
    with store.SessionLocal() as session:
        draft = session.execute(
            select(kg_store.BlueprintFragmentDraftRecord).where(
                kg_store.BlueprintFragmentDraftRecord.draft_id == followup["blueprint_fragment_draft_id"],
                kg_store.BlueprintFragmentDraftRecord.tenant_id == "tenant-1",
                kg_store.BlueprintFragmentDraftRecord.workspace_id == "workspace-1",
            )
        ).scalars().one()
    payload = json.loads(draft.payload_json)
    source_ref = json.loads(draft.source_ref_json)
    assert draft.review_status == "pending"
    assert payload["fragment_id"] == "esports_live_training_room"
    assert payload["project_object"] == "电竞直播训练间"
    assert payload["evidence"] == ["电竞直播训练间", "隔音、灯光、散热"]
    assert source_ref["review_item_id"] == "demand_reconstruction:new_fragment_candidate:signal-001"

    approved = store.approve_blueprint_fragment_draft(
        draft_id=followup["blueprint_fragment_draft_id"],
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        reviewer_id="reviewer-2",
    )

    assert approved["review_status"] == "approved"
    assert approved["registry_patch"]["registry_file"].endswith("demand_reconstruction_blueprints.yaml")
    assert approved["registry_patch"]["operation"] == "manual_merge_required"
    assert approved["registry_patch"]["fragment"]["fragment_id"] == "esports_live_training_room"
    with store.SessionLocal() as session:
        approved_draft = session.execute(
            select(kg_store.BlueprintFragmentDraftRecord).where(
                kg_store.BlueprintFragmentDraftRecord.draft_id == followup["blueprint_fragment_draft_id"],
                kg_store.BlueprintFragmentDraftRecord.tenant_id == "tenant-1",
                kg_store.BlueprintFragmentDraftRecord.workspace_id == "workspace-1",
            )
        ).scalars().one()
    approved_payload = json.loads(approved_draft.payload_json)
    assert approved_draft.review_status == "approved"
    assert approved_payload["registry_patch"]["fragment"]["fragment_id"] == "esports_live_training_room"

def test_export_blueprint_fragment_registry_patch_includes_parseable_yaml():
    store = _sqlite_store()
    store.enqueue_review_item(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        user_id="user-1",
        module="demand_reconstruction",
        object_type="governance_signal",
        object_id="new_fragment_candidate:signal-yaml",
        title="评估是否需要为社区文化中心沉淀新的需求重构规则碎片。",
        source="llm_semantic_router",
        risk="P2",
        target_admin_path="/admin/review-queue?queue=blueprint_fragment_review",
        metadata={
            "code": "new_fragment_candidate",
            "review_queue": "blueprint_fragment_review",
            "signal": {
                "code": "new_fragment_candidate",
                "fragment_id": "community_culture_center",
                "project_object": "社区文化中心",
                "summary": "评估是否需要为社区文化中心沉淀新的需求重构规则碎片。",
                "evidence": ["社区文化中心", "亲子厨房", "科普教育"],
            },
        },
        created_by="runtime",
    )
    updated = store.update_review_item_status(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        item_id="demand_reconstruction:new_fragment_candidate:signal-yaml",
        review_status="approved",
        reviewer_id="reviewer-1",
        note="同意进入碎片草案",
    )
    draft_id = updated["metadata"]["governance_followup"]["blueprint_fragment_draft_id"]
    store.approve_blueprint_fragment_draft(
        draft_id=draft_id,
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        reviewer_id="reviewer-2",
    )

    exported = store.get_blueprint_fragment_registry_patch(
        draft_id=draft_id,
        tenant_id="tenant-1",
        workspace_id="workspace-1",
    )

    assert exported["registry_patch"]["fragment"]["fragment_id"] == "community_culture_center"
    assert exported["registry_patch_yaml"]
    assert yaml.safe_load(exported["registry_patch_yaml"]) == exported["registry_patch"]



def test_apply_blueprint_fragment_registry_patch_writes_fragment_to_registry_file(tmp_path):
    store = _sqlite_store()
    store.enqueue_review_item(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        user_id="user-1",
        module="demand_reconstruction",
        object_type="governance_signal",
        object_id="new_fragment_candidate:signal-apply",
        title="评估是否需要为电竞直播训练间沉淀新的需求重构规则碎片。",
        source="llm_semantic_router",
        risk="P2",
        target_admin_path="/admin/review-queue?queue=blueprint_fragment_review",
        metadata={
            "code": "new_fragment_candidate",
            "review_queue": "blueprint_fragment_review",
            "signal": {
                "code": "new_fragment_candidate",
                "fragment_id": "esports_live_training_room",
                "project_object": "电竞直播训练间",
                "summary": "评估是否需要为电竞直播训练间沉淀新的需求重构规则碎片。",
                "evidence": ["电竞直播训练间", "隔音、灯光、散热"],
            },
        },
        created_by="runtime",
    )
    updated = store.update_review_item_status(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        item_id="demand_reconstruction:new_fragment_candidate:signal-apply",
        review_status="approved",
        reviewer_id="reviewer-1",
        note="同意进入碎片草案",
    )
    draft_id = updated["metadata"]["governance_followup"]["blueprint_fragment_draft_id"]
    store.approve_blueprint_fragment_draft(
        draft_id=draft_id,
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        reviewer_id="reviewer-2",
    )
    registry_path = tmp_path / "demand_reconstruction_blueprints.yaml"
    registry_path.write_text(
        yaml.safe_dump(
            {"demand_reconstruction_blueprint_fragments": {"primary_archetypes": {}}},
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    applied = store.apply_blueprint_fragment_registry_patch(
        draft_id=draft_id,
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        reviewer_id="reviewer-3",
        registry_path=registry_path,
    )

    assert applied["registry_patch"]["operation"] == "applied"
    assert applied["registry_patch"]["applied_to"] == str(registry_path)
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    governed = registry["demand_reconstruction_blueprint_fragments"]["governed_candidates"]
    assert governed["esports_live_training_room"]["project_object"] == "电竞直播训练间"
    assert governed["esports_live_training_room"]["evidence"] == ["电竞直播训练间", "隔音、灯光、散热"]

    with store.SessionLocal() as session:
        draft = session.execute(
            select(kg_store.BlueprintFragmentDraftRecord).where(
                kg_store.BlueprintFragmentDraftRecord.draft_id == draft_id,
                kg_store.BlueprintFragmentDraftRecord.tenant_id == "tenant-1",
                kg_store.BlueprintFragmentDraftRecord.workspace_id == "workspace-1",
            )
        ).scalars().one()
    payload = json.loads(draft.payload_json)
    assert payload["registry_patch"]["operation"] == "applied"
    assert payload["registry_patch"]["fragment"]["fragment_id"] == "esports_live_training_room"

def test_approving_knowledge_gap_ticket_creates_knowledge_asset_followup_draft():
    store = _sqlite_store()
    store.enqueue_review_item(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        user_id="user-1",
        module="demand_reconstruction",
        object_type="governance_signal",
        object_id="knowledge_gap_ticket:signal-001",
        title="LLM Semantic Router 判断特殊儿童康复教室缺少稳定专科规则/知识覆盖。",
        source="llm_semantic_router",
        risk="P2",
        target_admin_path="/admin/review-queue?queue=knowledge_asset_review",
        metadata={
            "code": "knowledge_gap_ticket",
            "review_queue": "knowledge_asset_review",
            "signal": {
                "code": "knowledge_gap_ticket",
                "gap_type": "llm_semantic_no_match",
                "project_type": "特殊儿童康复教室",
                "summary": "LLM Semantic Router 判断特殊儿童康复教室缺少稳定专科规则/知识覆盖。",
                "evidence": ["特殊儿童康复教室", "感统、安静区、家长等待"],
                "package_ids": ["special_children_rehab_classroom"],
                "ontology_dimension_ids": ["sensory_recovery_boundary"],
            },
        },
        created_by="runtime",
    )

    updated = store.update_review_item_status(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        item_id="demand_reconstruction:knowledge_gap_ticket:signal-001",
        review_status="approved",
        reviewer_id="reviewer-1",
        note="进入知识资产补齐",
    )

    followup = updated["metadata"]["governance_followup"]
    assert followup["type"] == "knowledge_asset_candidate_draft"
    assert followup["status"] == "draft"
    assert followup["asset_draft_id"].startswith("demand_gap_")
    assert followup["draft"]["project_type"] == "特殊儿童康复教室"
    assert followup["draft"]["gap_type"] == "llm_semantic_no_match"
    assert followup["draft"]["evidence"] == ["特殊儿童康复教室", "感统、安静区、家长等待"]
    assert followup["next_admin_action"] == "review_knowledge_asset_draft"

    with store.SessionLocal() as session:
        draft = session.execute(
            select(KnowledgeAssetDraftRecord).where(
                KnowledgeAssetDraftRecord.draft_id == followup["asset_draft_id"],
                KnowledgeAssetDraftRecord.tenant_id == "tenant-1",
                KnowledgeAssetDraftRecord.workspace_id == "workspace-1",
            )
        ).scalars().one()
    payload = json.loads(draft.payload_json)
    source_ref = json.loads(draft.source_ref_json)
    assert draft.review_status == "pending"
    assert payload["title"] == "特殊儿童康复教室 知识缺口候选"
    assert payload["knowledge_status"] == "candidate"
    assert payload["source_gap_type"] == "llm_semantic_no_match"
    assert payload["evidence"] == ["特殊儿童康复教室", "感统、安静区、家长等待"]
    assert payload["package_ids"] == ["special_children_rehab_classroom"]
    assert payload["ontology_dimension_ids"] == ["sensory_recovery_boundary"]

    approved = store.approve_asset_draft(
        draft_id=followup["asset_draft_id"],
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        reviewer_id="reviewer-2",
    )
    assert approved["review_status"] == "approved"
    cards = store.find_approved_cards(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        user_id="user-1",
    )
    assert cards[0]["package_ids"] == ["special_children_rehab_classroom"]
    assert cards[0]["ontology_dimension_ids"] == ["sensory_recovery_boundary"]
    assert source_ref["review_item_id"] == "demand_reconstruction:knowledge_gap_ticket:signal-001"

