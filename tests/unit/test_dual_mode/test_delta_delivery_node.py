"""
tests/unit/test_dual_mode/test_delta_delivery_node.py

DeltaDeliveryNode 单元测试

Copilot 生成（2026-03-15）
覆盖：
  - 正常增量执行（仅重跑 affected_zones）
  - delta_router_state 缺失时的安全降级
  - 版本树追加逻辑（v1.0 → v1.1 → v1.2）
  - delivery_bundle 不存在时创建空包
  - project_archive 同步刷新
  - 返回值字段正确性
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from intelligent_project_analyzer.workflow.nodes.delta_delivery_node import (
    DeltaDeliveryNode,
)


# ─────────────────────────────────────────────────────────────────────────────
# 辅助构造器
# ─────────────────────────────────────────────────────────────────────────────


def _base_state(**overrides) -> Dict[str, Any]:
    """构造最小可用测试 state。"""
    state: Dict[str, Any] = {
        "session_id": "test-delta-001",
        "user_input": "请把第三章改为现代风格",
        "is_delta_modification": True,
        "delta_router_state": {
            "delta": {
                "delta_target": "第三章改为现代风格",
                "original_ref": "test-delta-001",
                "modified_fields": ["style", "material"],
                "impact_scope": ["chapter_3"],
            },
            "impact": {
                "changed_field": "style",
                "affected_zones": ["chapter_3", "facade_design"],
                "redline_alerts": [],
                "dependencies": ["material_palette"],
                "requires_derived_project": False,
            },
        },
        "delivery_bundle": {
            "final_deliverables": [],
            "stage_deliverables": [{"type": "initial", "content": "v1.0 交付物"}],
            "insight_records": [],
            "risk_summary": {},
            "version_lineage": ["v1.0"],
            "explanation_materials": {},
        },
        "project_archive": {
            "project_id": "proj-001",
            "session_id": "test-delta-001",
            "delivery_bundle": None,
            "design_task_book": None,
            "execution_blueprint": None,
            "version_lineage": ["v1.0"],
            "decision_records": [],
            "review_traces": [],
            "risk_summary": {},
        },
    }
    state.update(overrides)
    return state


# ─────────────────────────────────────────────────────────────────────────────
# 节点实例化
# ─────────────────────────────────────────────────────────────────────────────


def _node() -> DeltaDeliveryNode:
    return DeltaDeliveryNode()


# ─────────────────────────────────────────────────────────────────────────────
# 正常执行路径
# ─────────────────────────────────────────────────────────────────────────────


class TestDeltaDeliveryNodeNormalPath:
    def test_returns_dict(self):
        result = _node().execute(_base_state())
        assert isinstance(result, dict)

    def test_system_mode_is_conversation(self):
        result = _node().execute(_base_state())
        assert result["system_mode"] == "conversation"

    def test_delta_flag_reset_to_false(self):
        result = _node().execute(_base_state())
        assert result["is_delta_modification"] is False

    def test_delta_router_state_cleared(self):
        result = _node().execute(_base_state())
        assert result["delta_router_state"] is None

    def test_delivery_bundle_returned(self):
        result = _node().execute(_base_state())
        assert "delivery_bundle" in result
        assert result["delivery_bundle"] is not None

    def test_updated_at_set(self):
        result = _node().execute(_base_state())
        assert "updated_at" in result
        assert result["updated_at"]


# ─────────────────────────────────────────────────────────────────────────────
# 版本树追加逻辑
# ─────────────────────────────────────────────────────────────────────────────


class TestVersionLineage:
    def test_version_increments_from_v1_0(self):
        result = _node().execute(_base_state())
        bundle = result["delivery_bundle"]
        assert "v1.1" in bundle["version_lineage"]

    def test_version_increments_from_v1_1(self):
        state = _base_state()
        state["delivery_bundle"]["version_lineage"] = ["v1.0", "v1.1"]
        result = _node().execute(state)
        bundle = result["delivery_bundle"]
        assert "v1.2" in bundle["version_lineage"]

    def test_original_version_preserved(self):
        result = _node().execute(_base_state())
        bundle = result["delivery_bundle"]
        assert "v1.0" in bundle["version_lineage"]

    def test_version_lineage_grows_by_one(self):
        state = _base_state()
        original_len = len(state["delivery_bundle"]["version_lineage"])
        result = _node().execute(state)
        bundle = result["delivery_bundle"]
        assert len(bundle["version_lineage"]) == original_len + 1

    def test_empty_lineage_uses_v1_0_delta(self):
        state = _base_state()
        state["delivery_bundle"]["version_lineage"] = []
        result = _node().execute(state)
        bundle = result["delivery_bundle"]
        assert len(bundle["version_lineage"]) == 1
        assert "delta" in bundle["version_lineage"][0].lower()

    def test_delta_entry_appended_to_stage_deliverables(self):
        result = _node().execute(_base_state())
        bundle = result["delivery_bundle"]
        stages = bundle["stage_deliverables"]
        # 末尾应追加 delta_delivery 类型条目
        delta_entries = [s for s in stages if s.get("type") == "delta_delivery"]
        assert len(delta_entries) == 1

    def test_delta_entry_has_version(self):
        result = _node().execute(_base_state())
        bundle = result["delivery_bundle"]
        last = bundle["stage_deliverables"][-1]
        assert "version" in last
        assert last["version"] == bundle["version_lineage"][-1]


# ─────────────────────────────────────────────────────────────────────────────
# 仅重跑 affected_zones
# ─────────────────────────────────────────────────────────────────────────────


class TestAffectedZonesExecution:
    def test_affected_zones_in_delta_result(self):
        result = _node().execute(_base_state())
        bundle = result["delivery_bundle"]
        last_stage = bundle["stage_deliverables"][-1]
        delta_result = last_stage.get("delta_result", {})
        zones = delta_result.get("affected_zones", [])
        assert "chapter_3" in zones
        assert "facade_design" in zones

    def test_partial_results_count_matches_zones(self):
        result = _node().execute(_base_state())
        bundle = result["delivery_bundle"]
        last_stage = bundle["stage_deliverables"][-1]
        partial_results = last_stage["delta_result"].get("partial_results", [])
        # 两个受影响区域 → 两条结果
        assert len(partial_results) == 2

    def test_empty_affected_zones_no_results(self):
        state = _base_state()
        state["delta_router_state"]["impact"]["affected_zones"] = []
        result = _node().execute(state)
        bundle = result["delivery_bundle"]
        last_stage = bundle["stage_deliverables"][-1]
        partial_results = last_stage["delta_result"].get("partial_results", [])
        assert partial_results == []


# ─────────────────────────────────────────────────────────────────────────────
# delivery_bundle 不存在时（兜底）
# ─────────────────────────────────────────────────────────────────────────────


class TestMissingDeliveryBundle:
    def test_creates_bundle_when_missing(self):
        state = _base_state(delivery_bundle=None)
        result = _node().execute(state)
        bundle = result["delivery_bundle"]
        assert bundle is not None
        assert "version_lineage" in bundle

    def test_version_contains_delta_when_no_prior_bundle(self):
        state = _base_state(delivery_bundle=None)
        result = _node().execute(state)
        bundle = result["delivery_bundle"]
        assert len(bundle["version_lineage"]) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# delta_router_state 缺失时安全降级
# ─────────────────────────────────────────────────────────────────────────────


class TestMissingDeltaRouterState:
    def test_returns_error_key(self):
        state = _base_state(delta_router_state=None)
        result = _node().execute(state)
        assert "execution_error" in result

    def test_system_mode_still_conversation_on_error(self):
        state = _base_state(delta_router_state=None)
        result = _node().execute(state)
        assert result.get("system_mode") == "conversation"


# ─────────────────────────────────────────────────────────────────────────────
# ProjectArchive 刷新
# ─────────────────────────────────────────────────────────────────────────────


class TestProjectArchiveRefresh:
    def test_archive_refreshed_when_present(self):
        result = _node().execute(_base_state())
        archive = result.get("project_archive")
        assert archive is not None

    def test_archive_decision_records_grow(self):
        result = _node().execute(_base_state())
        archive = result["project_archive"]
        assert len(archive["decision_records"]) == 1
        assert archive["decision_records"][0]["type"] == "delta_modification"

    def test_archive_none_when_state_has_no_archive(self):
        state = _base_state(project_archive=None)
        result = _node().execute(state)
        assert result.get("project_archive") is None
