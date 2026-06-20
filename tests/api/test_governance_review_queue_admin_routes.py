import pytest
from sqlalchemy import create_engine

from intelligent_project_analyzer.api import admin_routes
from intelligent_project_analyzer.services.knowledge_governance_store import KnowledgeGovernanceStore


@pytest.fixture
def governance_store():
    engine = create_engine("sqlite:///:memory:")
    store = KnowledgeGovernanceStore(engine=engine)
    store.create_all()
    return store


@pytest.fixture(autouse=True)
def patch_governance_store(monkeypatch, governance_store):
    monkeypatch.setattr(
        admin_routes,
        "get_knowledge_governance_store",
        lambda: governance_store,
        raising=False,
    )


def _enqueue_signal(store: KnowledgeGovernanceStore, *, object_id: str, review_queue: str) -> None:
    store.enqueue_review_item(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        user_id="user-1",
        module="demand_reconstruction",
        object_type="governance_signal",
        object_id=object_id,
        title=f"治理信号 {object_id}",
        source="llm_semantic_router",
        risk="P2",
        target_admin_path=f"/admin/review-queue?queue={review_queue}",
        metadata={"code": object_id, "review_queue": review_queue},
        created_by="runtime",
    )


def _create_blueprint_fragment_draft(store: KnowledgeGovernanceStore) -> str:
    item = store.enqueue_review_item(
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
                "evidence": ["电竞直播训练间"],
            },
        },
        created_by="runtime",
    )
    updated = store.update_review_item_status(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        item_id=str(item["id"]),
        review_status="approved",
        reviewer_id="reviewer",
    )
    return str(updated["metadata"]["governance_followup"]["blueprint_fragment_draft_id"])


def _create_knowledge_asset_draft(store: KnowledgeGovernanceStore) -> str:
    item = store.enqueue_review_item(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        user_id="user-1",
        module="demand_reconstruction",
        object_type="governance_signal",
        object_id="knowledge_gap_ticket:signal-001",
        title="特殊儿童康复教室知识缺口",
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
                "evidence": ["特殊儿童康复教室"],
            },
        },
        created_by="runtime",
    )
    updated = store.update_review_item_status(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        item_id=str(item["id"]),
        review_status="approved",
        reviewer_id="reviewer",
    )
    return str(updated["metadata"]["governance_followup"]["asset_draft_id"])


@pytest.mark.asyncio
async def test_list_governance_review_queue_filters_review_queue(governance_store):
    _enqueue_signal(governance_store, object_id="knowledge_gap_ticket", review_queue="knowledge_asset_review")
    _enqueue_signal(governance_store, object_id="new_fragment_candidate", review_queue="blueprint_fragment_review")

    response = await admin_routes.list_governance_review_queue(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        review_status="pending",
        review_queue="blueprint_fragment_review",
        admin={"username": "reviewer"},
    )

    assert response["status"] == "success"
    assert response["total"] == 1
    assert response["items"][0]["object_id"] == "new_fragment_candidate"
    assert response["items"][0]["metadata"]["review_queue"] == "blueprint_fragment_review"


@pytest.mark.asyncio
async def test_update_governance_review_queue_item_status_via_admin_route(governance_store):
    _enqueue_signal(governance_store, object_id="knowledge_gap_ticket", review_queue="knowledge_asset_review")

    response = await admin_routes.update_governance_review_queue_item_status(
        item_id="demand_reconstruction:knowledge_gap_ticket",
        payload={
            "tenant_id": "tenant-1",
            "workspace_id": "workspace-1",
            "review_status": "approved",
            "note": "转入知识资产候选建设",
        },
        admin={"username": "reviewer"},
    )

    assert response["status"] == "success"
    assert response["item"]["review_status"] == "approved"
    assert response["item"]["reviewer_note"] == "转入知识资产候选建设"
    assert governance_store.list_review_items(tenant_id="tenant-1", workspace_id="workspace-1") == []


@pytest.mark.asyncio
async def test_approve_blueprint_fragment_draft_via_admin_route(governance_store):
    draft_id = _create_blueprint_fragment_draft(governance_store)

    response = await admin_routes.approve_blueprint_fragment_draft(
        draft_id=draft_id,
        payload={
            "tenant_id": "tenant-1",
            "workspace_id": "workspace-1",
        },
        admin={"username": "reviewer"},
    )

    assert response["status"] == "success"
    assert response["draft"]["review_status"] == "approved"
    assert response["draft"]["registry_patch"]["operation"] == "manual_merge_required"
    assert response["draft"]["registry_patch"]["fragment"]["fragment_id"] == "esports_live_training_room"


@pytest.mark.asyncio
async def test_export_blueprint_fragment_registry_patch_via_admin_route(governance_store):
    draft_id = _create_blueprint_fragment_draft(governance_store)
    await admin_routes.approve_blueprint_fragment_draft(
        draft_id=draft_id,
        payload={
            "tenant_id": "tenant-1",
            "workspace_id": "workspace-1",
        },
        admin={"username": "reviewer"},
    )

    response = await admin_routes.export_blueprint_fragment_registry_patch(
        draft_id=draft_id,
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        admin={"username": "reviewer"},
    )

    assert response["status"] == "success"
    assert response["draft_id"] == draft_id
    assert response["registry_patch"]["operation"] == "manual_merge_required"
    assert response["registry_patch"]["fragment"]["fragment_id"] == "esports_live_training_room"
    assert "demand_reconstruction_blueprints.yaml" in response["registry_patch_yaml"]
    assert "esports_live_training_room" in response["registry_patch_yaml"]


@pytest.mark.asyncio
async def test_apply_blueprint_fragment_registry_patch_via_admin_route(governance_store, tmp_path):
    draft_id = _create_blueprint_fragment_draft(governance_store)
    await admin_routes.approve_blueprint_fragment_draft(
        draft_id=draft_id,
        payload={
            "tenant_id": "tenant-1",
            "workspace_id": "workspace-1",
        },
        admin={"username": "reviewer"},
    )
    registry_path = tmp_path / "demand_reconstruction_blueprints.yaml"
    registry_path.write_text(
        "demand_reconstruction_blueprint_fragments:\n  primary_archetypes: {}\n",
        encoding="utf-8",
    )

    response = await admin_routes.apply_blueprint_fragment_registry_patch(
        draft_id=draft_id,
        payload={
            "tenant_id": "tenant-1",
            "workspace_id": "workspace-1",
            "registry_path": str(registry_path),
        },
        admin={"username": "reviewer"},
    )

    assert response["status"] == "success"
    assert response["draft"]["registry_patch"]["operation"] == "applied"
    assert response["draft"]["registry_patch"]["fragment"]["fragment_id"] == "esports_live_training_room"
    assert "esports_live_training_room" in registry_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_approve_knowledge_asset_draft_via_admin_route(governance_store):
    draft_id = _create_knowledge_asset_draft(governance_store)

    response = await admin_routes.approve_knowledge_asset_draft(
        draft_id=draft_id,
        payload={
            "tenant_id": "tenant-1",
            "workspace_id": "workspace-1",
        },
        admin={"username": "reviewer"},
    )

    assert response["status"] == "success"
    assert response["draft"]["review_status"] == "approved"
    assert response["draft"]["draft_id"] == draft_id
    assert response["draft"]["card_id"] == draft_id
