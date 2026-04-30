"""
tests/integration/test_delta_delivery.py

DeltaRouter → DeltaDeliveryNode 端到端集成测试

Copilot 生成（2026-03-15）
覆盖：
  - DeltaRouter 路由到 delta_delivery（含 delta 关键词 + 无红线）
  - DeltaDeliveryNode 完成版本树追加后状态字段正确
  - delta_router_state 流转并被清除
  - project_archive 同步刷新
  - 连续两次增量版本号递增正确（v1.0 → v1.1 → v1.2）
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from intelligent_project_analyzer.workflow.nodes.delta_delivery_node import (
    DeltaDeliveryNode,
)
from intelligent_project_analyzer.workflow.nodes.delta_router import DeltaRouter


# ─────────────────────────────────────────────────────────────────────────────
# 辅助
# ─────────────────────────────────────────────────────────────────────────────


def _pre_routing_state(
    user_input: str = "把立面材质改成穿孔金属板",
    version_lineage=("v1.0",),
) -> Dict[str, Any]:
    """
    DeltaRouter 路由前的 state — 包含已交付项目档案 + 用户修改指令。
    使用含 delta 关键词（"材质"/"改成"）的输入，触发 _is_clear_delta。
    """
    return {
        "session_id": "integ-delta-001",
        "user_input": user_input,
        "is_delta_modification": False,
        "design_task_book": {
            "strategy_zones": {"flexible": ["facade_material", "color_scheme"]},
            "boundaries_and_redlines": [],
        },
        "delivery_bundle": {
            "final_deliverables": [{"type": "main_report"}],
            "stage_deliverables": [{"type": "initial", "content": "初始交付"}],
            "insight_records": [],
            "risk_summary": {},
            "version_lineage": list(version_lineage),
            "explanation_materials": {},
        },
        "project_archive": {
            "project_id": "proj-integ-001",
            "session_id": "integ-delta-001",
            "delivery_bundle": None,
            "design_task_book": None,
            "execution_blueprint": None,
            "version_lineage": list(version_lineage),
            "decision_records": [],
            "review_traces": [],
            "risk_summary": {},
        },
    }


def _state_with_router_output(
    user_input: str = "把立面改成穿孔金属板",
    affected_zones=("facade_detail",),
    redline_alerts=(),
    version_lineage=("v1.0",),
) -> Dict[str, Any]:
    """
    已由 DeltaRouter 写入 delta_router_state 后的 state 快照。
    供 DeltaDeliveryNode 直接调用。
    """
    return {
        "session_id": "integ-delta-001",
        "user_input": user_input,
        "is_delta_modification": True,
        "delta_router_state": {
            "delta": {
                "delta_target": user_input,
                "original_ref": "integ-delta-001",
                "modified_fields": ["facade_material"],
                "impact_scope": list(affected_zones),
            },
            "impact": {
                "changed_field": "facade_material",
                "affected_zones": list(affected_zones),
                "redline_alerts": list(redline_alerts),
                "dependencies": [],
                "requires_derived_project": False,
            },
        },
        "delivery_bundle": {
            "final_deliverables": [{"type": "main_report"}],
            "stage_deliverables": [{"type": "initial", "content": "初始交付"}],
            "insight_records": [],
            "risk_summary": {},
            "version_lineage": list(version_lineage),
            "explanation_materials": {},
        },
        "project_archive": {
            "project_id": "proj-integ-001",
            "session_id": "integ-delta-001",
            "delivery_bundle": None,
            "design_task_book": None,
            "execution_blueprint": None,
            "version_lineage": list(version_lineage),
            "decision_records": [],
            "review_traces": [],
            "risk_summary": {},
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# DeltaRouter 路由方向验证
# ─────────────────────────────────────────────────────────────────────────────


class TestDeltaRouterRoutesToDeltaDelivery:
    """验证 DeltaRouter 对局部修改意图（含 delta 关键词）正确路由到 delta_delivery。"""

    def test_delta_keywords_trigger_delta_path(self):
        """含"改成"/"材质"等 delta 关键词 → 应路由到 delta_delivery。"""
        # "材质" 是 _DELTA_KEYWORDS 之一
        state = _pre_routing_state(user_input="把立面材质改成穿孔金属板")
        router = DeltaRouter()
        command = router.route(state)
        assert hasattr(command, "goto")
        assert command.goto == "delta_delivery"

    def test_delta_router_state_set_in_command_update(self):
        """DeltaRouter 路由后 delta_router_state 应在 command.update 中。"""
        state = _pre_routing_state()
        router = DeltaRouter()
        command = router.route(state)
        update = command.update or {}
        assert "delta_router_state" in update
        assert update["delta_router_state"] is not None

    def test_is_delta_modification_set_true(self):
        """DeltaRouter 路由后 is_delta_modification 应为 True。"""
        state = _pre_routing_state()
        router = DeltaRouter()
        command = router.route(state)
        update = command.update or {}
        assert update.get("is_delta_modification") is True


# ─────────────────────────────────────────────────────────────────────────────
# DeltaDeliveryNode 执行结果
# ─────────────────────────────────────────────────────────────────────────────


class TestDeltaDeliveryNodeExecution:
    """DeltaDeliveryNode 执行逻辑的端到端验证。"""

    def test_full_v1_0_to_v1_1_flow(self):
        """完整流：state 含 v1.0 → DeltaDelivery → 版本树变为 [v1.0, v1.1]。"""
        state = _state_with_router_output(version_lineage=["v1.0"])
        result = DeltaDeliveryNode().execute(state)

        bundle = result["delivery_bundle"]
        assert bundle["version_lineage"] == ["v1.0", "v1.1"]

    def test_system_mode_reverts_to_conversation(self):
        state = _state_with_router_output()
        result = DeltaDeliveryNode().execute(state)
        assert result["system_mode"] == "conversation"

    def test_delta_flag_cleared(self):
        state = _state_with_router_output()
        result = DeltaDeliveryNode().execute(state)
        assert result["is_delta_modification"] is False

    def test_delta_router_state_cleared_after_execution(self):
        state = _state_with_router_output()
        result = DeltaDeliveryNode().execute(state)
        assert result["delta_router_state"] is None

    def test_stage_deliverables_has_delta_entry(self):
        state = _state_with_router_output()
        result = DeltaDeliveryNode().execute(state)
        bundle = result["delivery_bundle"]
        delta_entries = [s for s in bundle["stage_deliverables"] if s.get("type") == "delta_delivery"]
        assert len(delta_entries) == 1

    def test_delta_result_contains_affected_zones(self):
        state = _state_with_router_output(affected_zones=["facade_detail", "material_list"])
        result = DeltaDeliveryNode().execute(state)
        bundle = result["delivery_bundle"]
        last_stage = bundle["stage_deliverables"][-1]
        zones = last_stage["delta_result"].get("affected_zones", [])
        assert "facade_detail" in zones
        assert "material_list" in zones


# ─────────────────────────────────────────────────────────────────────────────
# 连续两次增量
# ─────────────────────────────────────────────────────────────────────────────


class TestConsecutiveDeltaDeliveries:
    """两次增量操作版本号递增正确。"""

    def test_v1_0_to_v1_1_then_v1_2(self):
        # 第一次增量：v1.0 → v1.1
        state1 = _state_with_router_output(
            user_input="改立面材料",
            version_lineage=["v1.0"],
        )
        result1 = DeltaDeliveryNode().execute(state1)
        bundle1 = result1["delivery_bundle"]
        assert "v1.1" in bundle1["version_lineage"]

        # 第二次增量：用第一次的 bundle 继续，v1.1 → v1.2
        state2 = _state_with_router_output(
            user_input="调整室内照明方案",
            version_lineage=bundle1["version_lineage"],
        )
        result2 = DeltaDeliveryNode().execute(state2)
        bundle2 = result2["delivery_bundle"]
        assert "v1.2" in bundle2["version_lineage"]
        assert len(bundle2["version_lineage"]) == 3  # v1.0, v1.1, v1.2

    def test_version_lineage_is_cumulative(self):
        state1 = _state_with_router_output(version_lineage=["v1.0"])
        r1 = DeltaDeliveryNode().execute(state1)

        state2 = _state_with_router_output(
            version_lineage=r1["delivery_bundle"]["version_lineage"]
        )
        r2 = DeltaDeliveryNode().execute(state2)

        # 保留全历史
        assert "v1.0" in r2["delivery_bundle"]["version_lineage"]
        assert "v1.1" in r2["delivery_bundle"]["version_lineage"]
        assert "v1.2" in r2["delivery_bundle"]["version_lineage"]


# ─────────────────────────────────────────────────────────────────────────────
# project_archive 同步
# ─────────────────────────────────────────────────────────────────────────────


class TestArchiveSync:
    def test_archive_decision_records_updated(self):
        state = _state_with_router_output()
        result = DeltaDeliveryNode().execute(state)
        archive = result.get("project_archive")
        assert archive is not None
        assert len(archive["decision_records"]) == 1
        assert archive["decision_records"][0]["type"] == "delta_modification"

    def test_archive_version_matches_bundle(self):
        state = _state_with_router_output()
        result = DeltaDeliveryNode().execute(state)
        bundle_ver = result["delivery_bundle"]["version_lineage"][-1]
        archive_record_ver = result["project_archive"]["decision_records"][0]["version"]
        assert archive_record_ver == bundle_ver
