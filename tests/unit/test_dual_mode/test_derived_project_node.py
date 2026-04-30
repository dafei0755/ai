"""
tests/unit/test_dual_mode/test_derived_project_node.py

DerivedProjectNode 单元测试

Copilot 生成（2026-03-15）
覆盖：
  - execute() 返回 Command(goto="gatekeeper_v2")
  - 状态重置字段（requirements_frozen / design_task_book / execution_blueprint / …）
  - 派生项目 session_id 生成（格式 derived_{parent}_xxx）
  - RawBriefPacket 携带父项目上下文
  - inheritance_mode 决策逻辑（redline → soft，否则 partial）
  - prefill 内容不随 soft 模式泄露 inherited_boundaries
  - parent_project_id 传递
"""

from __future__ import annotations

from typing import Any, Dict

import pytest
from langgraph.types import Command

from intelligent_project_analyzer.workflow.nodes.derived_project_node import (
    DerivedProjectNode,
)


# ─────────────────────────────────────────────────────────────────────────────
# 辅助构造器
# ─────────────────────────────────────────────────────────────────────────────


def _base_state(**overrides) -> Dict[str, Any]:
    state: Dict[str, Any] = {
        "session_id": "sess-parent-001",
        "user_input": "把建筑改成波浪造型，整体规模也扩大一倍",
        "parent_project_id": "proj-parent-001",
        "impact_graph": {
            "changed_field": "building_form",
            "affected_zones": ["facade", "structure", "mep"],
            "redline_alerts": [],
            "dependencies": ["space_program"],
            "requires_derived_project": True,
        },
        "project_archive": {
            "project_id": "proj-parent-001",
            "session_id": "sess-parent-001",
            "delivery_bundle": None,
            "design_task_book_snapshot": {
                "core_proposition": "精品酒店，现代简约",
                "boundaries_and_redlines": ["场地红线不可越", "层高≤22m"],
            },
            "execution_blueprint_snapshot": {
                "expert_responsibility": {
                    "architect": "主创方案",
                    "structure_engineer": "结构设计",
                },
            },
            "version_lineage": ["v1.0"],
            "decision_records": [],
            "review_traces": [],
            "risk_summary": {},
        },
        # 存量项目态字段（期望被重置）
        "requirements_frozen": True,
        "design_task_book": {"frozen": True},
        "execution_blueprint": {"frozen": True},
        "gate_decision": {"status": "approved"},
        "stage_deliverables_v2": [{"stage": "S1"}],
        "execution_review_log": ["review_entry"],
        "execution_halted": False,
        "is_delta_modification": True,
        "delta_router_state": {"some": "data"},
    }
    state.update(overrides)
    return state


def _node() -> DerivedProjectNode:
    return DerivedProjectNode()


# ─────────────────────────────────────────────────────────────────────────────
# 返回类型 & 路由目标
# ─────────────────────────────────────────────────────────────────────────────


class TestDerivedProjectNodeReturnType:
    def test_returns_command(self):
        result = _node().execute(_base_state())
        assert isinstance(result, Command)

    def test_routes_to_gatekeeper_v2(self):
        result = _node().execute(_base_state())
        assert result.goto == "gatekeeper_v2"

    def test_update_is_dict(self):
        result = _node().execute(_base_state())
        assert isinstance(result.update, dict)


# ─────────────────────────────────────────────────────────────────────────────
# 状态重置字段
# ─────────────────────────────────────────────────────────────────────────────


class TestStateReset:
    def _update(self, **overrides) -> Dict[str, Any]:
        return _node().execute(_base_state(**overrides)).update  # type: ignore[attr-defined]

    def test_requirements_frozen_reset_to_false(self):
        u = self._update()
        assert u["requirements_frozen"] is False

    def test_design_task_book_cleared(self):
        u = self._update()
        assert u["design_task_book"] is None

    def test_execution_blueprint_cleared(self):
        u = self._update()
        assert u["execution_blueprint"] is None

    def test_gate_decision_cleared(self):
        u = self._update()
        assert u["gate_decision"] is None

    def test_stage_deliverables_v2_cleared(self):
        u = self._update()
        assert u["stage_deliverables_v2"] is None

    def test_execution_review_log_cleared(self):
        u = self._update()
        assert u["execution_review_log"] is None

    def test_execution_halted_reset_to_false(self):
        u = self._update()
        assert u["execution_halted"] is False

    def test_is_delta_modification_reset_to_false(self):
        u = self._update()
        assert u["is_delta_modification"] is False

    def test_delta_router_state_cleared(self):
        u = self._update()
        assert u["delta_router_state"] is None

    def test_system_mode_is_project(self):
        u = self._update()
        assert u["system_mode"] == "project"

    def test_current_stage_is_requirement_collection(self):
        u = self._update()
        assert u["current_stage"] == "requirement_collection"


# ─────────────────────────────────────────────────────────────────────────────
# session_id 生成格式
# ─────────────────────────────────────────────────────────────────────────────


class TestSessionIdGeneration:
    def test_new_session_id_starts_with_derived(self):
        result = _node().execute(_base_state())
        new_id = result.update["session_id"]  # type: ignore[index]
        assert new_id.startswith("derived_")

    def test_new_session_id_contains_parent_id(self):
        result = _node().execute(_base_state())
        new_id = result.update["session_id"]  # type: ignore[index]
        assert "sess-parent-001" in new_id

    def test_each_call_generates_different_id(self):
        state = _base_state()
        id1 = _node().execute(state).update["session_id"]  # type: ignore[index]
        id2 = _node().execute(state).update["session_id"]  # type: ignore[index]
        assert id1 != id2

    def test_parent_project_id_preserved(self):
        result = _node().execute(_base_state())
        assert result.update["parent_project_id"] == "proj-parent-001"  # type: ignore[index]


# ─────────────────────────────────────────────────────────────────────────────
# RawBriefPacket 内容
# ─────────────────────────────────────────────────────────────────────────────


class TestRawBriefPacket:
    def _brief(self, **overrides) -> Dict[str, Any]:
        result = _node().execute(_base_state(**overrides))
        return result.update["raw_brief_packet"] or {}  # type: ignore[index]

    def test_brief_contains_user_input(self):
        brief = self._brief()
        assert "波浪造型" in brief.get("raw_user_prompt", "")

    def test_brief_initial_context_has_derived_from(self):
        brief = self._brief()
        ctx = brief.get("initial_context", {})
        assert ctx.get("derived_from") == "proj-parent-001"

    def test_brief_initial_context_has_diverge_point(self):
        brief = self._brief()
        ctx = brief.get("initial_context", {})
        assert ctx.get("diverge_point") == "building_form"

    def test_brief_session_or_project_stub(self):
        brief = self._brief()
        stub = brief.get("session_or_project_stub", "")
        assert "derived:proj-parent-001" in stub


# ─────────────────────────────────────────────────────────────────────────────
# inheritance_mode 决策逻辑
# ─────────────────────────────────────────────────────────────────────────────


class TestInheritanceMode:
    def _get_prefill(self, impact_override: Dict | None = None) -> Dict[str, Any]:
        state = _base_state()
        if impact_override:
            state["impact_graph"].update(impact_override)
        result = _node().execute(state)
        # prefill 挂在 raw_brief_packet.prefill_from_drafts
        brief = result.update["raw_brief_packet"]  # type: ignore[index]
        return brief.get("prefill_from_drafts") or {}

    def test_no_redline_partial_mode(self):
        prefill = self._get_prefill({"redline_alerts": [], "affected_zones": ["a"]})
        assert "inheritance_mode" in prefill
        assert prefill["inheritance_mode"] == "partial"

    def test_redline_triggers_soft_mode(self):
        prefill = self._get_prefill({"redline_alerts": ["层高超限"]})
        assert prefill["inheritance_mode"] == "soft"

    def test_many_zones_partial_mode(self):
        prefill = self._get_prefill({"redline_alerts": [], "affected_zones": ["a", "b", "c"]})
        assert prefill["inheritance_mode"] == "partial"


# ─────────────────────────────────────────────────────────────────────────────
# prefill 内容 & soft 模式隔离
# ─────────────────────────────────────────────────────────────────────────────


class TestPrefillContent:
    def test_prefill_has_parent_project_id(self):
        state = _base_state()
        result = _node().execute(state)
        brief = result.update["raw_brief_packet"]  # type: ignore[index]
        prefill = brief.get("prefill_from_drafts") or {}
        assert prefill.get("parent_project_id") == "proj-parent-001"

    def test_prefill_has_affected_zones(self):
        state = _base_state()
        result = _node().execute(state)
        brief = result.update["raw_brief_packet"]  # type: ignore[index]
        prefill = brief.get("prefill_from_drafts") or {}
        assert "facade" in prefill.get("affected_zones", [])

    def test_soft_mode_no_inherited_boundaries(self):
        """soft 继承模式不应传递父项目边界（避免污染新项目态）"""
        state = _base_state()
        state["impact_graph"]["redline_alerts"] = ["层高超限"]  # 触发 soft
        result = _node().execute(state)
        brief = result.update["raw_brief_packet"]  # type: ignore[index]
        prefill = brief.get("prefill_from_drafts") or {}
        assert "inherited_boundaries" not in prefill

    def test_partial_mode_inherits_boundaries(self):
        """partial 继承模式应传递父项目边界"""
        state = _base_state()
        state["impact_graph"]["redline_alerts"] = []  # 无红线
        result = _node().execute(state)
        brief = result.update["raw_brief_packet"]  # type: ignore[index]
        prefill = brief.get("prefill_from_drafts") or {}
        # archive 中有边界数据，partial 模式应继承
        assert "inherited_boundaries" in prefill
        assert "场地红线不可越" in prefill["inherited_boundaries"]


# ─────────────────────────────────────────────────────────────────────────────
# 无父档案时的降级处理
# ─────────────────────────────────────────────────────────────────────────────


class TestNoParentArchive:
    def test_works_without_archive(self):
        state = _base_state(project_archive=None)
        result = _node().execute(state)
        assert isinstance(result, Command)
        assert result.goto == "gatekeeper_v2"

    def test_brief_still_created_without_archive(self):
        state = _base_state(project_archive=None)
        result = _node().execute(state)
        brief = result.update["raw_brief_packet"]  # type: ignore[index]
        assert brief is not None

    def test_no_parent_project_id_uses_session_id(self):
        """parent_project_id 缺失时应回落到 session_id"""
        state = _base_state(parent_project_id=None)
        result = _node().execute(state)
        parent_id = result.update["parent_project_id"]  # type: ignore[index]
        assert parent_id == "sess-parent-001"
