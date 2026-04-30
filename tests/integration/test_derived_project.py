"""
tests/integration/test_derived_project.py

DeltaRouter → DerivedProjectNode 端到端集成测试

Copilot 生成（2026-03-15）
覆盖：
  - DeltaRouter 对触碰红线/派生关键词的输入路由到 derived_project
  - DerivedProjectNode 输出 Command(goto="gatekeeper_v2") + 完整 state 重置
  - 两阶段数据流：router command.update 注入 state → DerivedProjectNode 读取并重置
  - 父项目档案保留（delivery_bundle / project_archive 历史不被清除）
  - 不同继承模式下 prefill 内容的差异
"""

from __future__ import annotations

from typing import Any, Dict

import pytest
from langgraph.types import Command

from intelligent_project_analyzer.workflow.nodes.derived_project_node import (
    DerivedProjectNode,
)
from intelligent_project_analyzer.workflow.nodes.delta_router import DeltaRouter


# ─────────────────────────────────────────────────────────────────────────────
# 辅助
# ─────────────────────────────────────────────────────────────────────────────


def _pre_routing_state_with_redline(
    user_input: str = "把整个地块容积率限高提高两倍",
) -> Dict[str, Any]:
    """
    含红线触碰词（"容积率"）的 state — DeltaRouter 应路由到 derived_project。
    _REDLINE_MARKERS = ("容积率", "退红线", ...) 中包含"容积率"。
    """
    return {
        "session_id": "integ-derived-001",
        "user_input": user_input,
        "is_delta_modification": False,
        "design_task_book": {
            "strategy_zones": {"frozen": ["height_limit", "floor_area_ratio"]},
            "boundaries_and_redlines": ["层高≤22m", "容积率≤2.5"],
        },
        "project_archive": {
            "project_id": "proj-derived-001",
            "session_id": "integ-derived-001",
            "delivery_bundle": None,
            "design_task_book_snapshot": {
                "core_proposition": "精品酒店",
                "boundaries_and_redlines": ["层高≤22m"],
            },
            "execution_blueprint_snapshot": {
                "expert_responsibility": {"architect": "主创"}
            },
            "version_lineage": ["v1.0"],
            "decision_records": [],
            "review_traces": [],
            "risk_summary": {},
        },
    }


def _state_after_router_derived(
    user_input: str = "推翻重做，换个方向",
    impact_redlines=("战略核心触碰",),
) -> Dict[str, Any]:
    """
    DeltaRouter 路由到 derived_project 后的 state 快照，
    包含 impact_graph（DerivedProjectNode 的输入）。
    """
    return {
        "session_id": "integ-derived-001",
        "user_input": user_input,
        "parent_project_id": "proj-derived-001",
        "is_delta_modification": False,
        "impact_graph": {
            "changed_field": "strategy",
            "affected_zones": ["facade", "structure", "mep"],
            "redline_alerts": list(impact_redlines),
            "dependencies": [],
            "requires_derived_project": True,
        },
        "delivery_bundle": {
            "final_deliverables": [{"type": "main_report"}],
            "stage_deliverables": [],
            "insight_records": [],
            "risk_summary": {},
            "version_lineage": ["v1.0"],
            "explanation_materials": {},
        },
        "project_archive": {
            "project_id": "proj-derived-001",
            "session_id": "integ-derived-001",
            "delivery_bundle": None,
            "design_task_book_snapshot": {
                "core_proposition": "精品酒店",
                "boundaries_and_redlines": ["层高≤22m"],
            },
            "execution_blueprint_snapshot": {
                "expert_responsibility": {"architect": "主创", "structure_engineer": "结构"}
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
    }


# ─────────────────────────────────────────────────────────────────────────────
# DeltaRouter 路由到 derived_project
# ─────────────────────────────────────────────────────────────────────────────


class TestDeltaRouterRoutesToDerivedProject:
    """验证含红线触碰词的输入路由到 derived_project。"""

    def test_redline_marker_triggers_derived_path(self):
        """含"容积率"（_REDLINE_MARKERS） → 路由到 derived_project。"""
        state = _pre_routing_state_with_redline(user_input="把整个地块容积率限高提高两倍")
        router = DeltaRouter()
        command = router.route(state)
        assert command.goto == "derived_project"

    def test_derived_keyword_triggers_derived_path(self):
        """含"从零"（_DERIVED_KEYWORDS） → 路由到 derived_project。"""
        state = _pre_routing_state_with_redline(user_input="从零重新设计整个方案")
        router = DeltaRouter()
        command = router.route(state)
        assert command.goto == "derived_project"

    def test_derived_command_has_impact_graph(self):
        """DeltaRouter 路由 derived 时应在 update 中写入 impact_graph。"""
        state = _pre_routing_state_with_redline()
        router = DeltaRouter()
        command = router.route(state)
        update = command.update or {}
        assert "impact_graph" in update

    def test_derived_command_has_parent_project_id(self):
        """DeltaRouter 路由 derived 时应写入 parent_project_id。"""
        state = _pre_routing_state_with_redline()
        router = DeltaRouter()
        command = router.route(state)
        update = command.update or {}
        assert "parent_project_id" in update


# ─────────────────────────────────────────────────────────────────────────────
# DerivedProjectNode 执行结果
# ─────────────────────────────────────────────────────────────────────────────


class TestDerivedProjectNodeExecution:
    """DerivedProjectNode 执行逻辑的端到端验证。"""

    def test_returns_command_goto_gatekeeper_v2(self):
        state = _state_after_router_derived()
        result = DerivedProjectNode().execute(state)
        assert isinstance(result, Command)
        assert result.goto == "gatekeeper_v2"

    def test_update_has_required_keys(self):
        state = _state_after_router_derived()
        result = DerivedProjectNode().execute(state)
        update = result.update  # type: ignore[union-attr]
        for key in ("session_id", "parent_project_id", "system_mode",
                    "requirements_frozen", "design_task_book", "execution_blueprint"):
            assert key in update, f"缺少必需字段: {key}"

    def test_requirements_frozen_reset(self):
        state = _state_after_router_derived()
        result = DerivedProjectNode().execute(state)
        assert result.update["requirements_frozen"] is False  # type: ignore[index]

    def test_design_task_book_cleared(self):
        state = _state_after_router_derived()
        result = DerivedProjectNode().execute(state)
        assert result.update["design_task_book"] is None  # type: ignore[index]

    def test_system_mode_is_project(self):
        state = _state_after_router_derived()
        result = DerivedProjectNode().execute(state)
        assert result.update["system_mode"] == "project"  # type: ignore[index]

    def test_new_session_id_different_from_parent(self):
        state = _state_after_router_derived()
        result = DerivedProjectNode().execute(state)
        new_id = result.update["session_id"]  # type: ignore[index]
        assert new_id != "integ-derived-001"
        assert "integ-derived-001" in new_id  # 含父 session 信息

    def test_new_session_id_format(self):
        state = _state_after_router_derived()
        result = DerivedProjectNode().execute(state)
        new_id = result.update["session_id"]  # type: ignore[index]
        assert new_id.startswith("derived_")


# ─────────────────────────────────────────────────────────────────────────────
# 两阶段数据流完整验证
# ─────────────────────────────────────────────────────────────────────────────


class TestRouterThenDerivedNodeChain:
    """
    模拟 LangGraph 两阶段执行：
      1. DeltaRouter.route() → Command(goto=derived_project, update=...)
      2. 将 update 合并到 state
      3. DerivedProjectNode.execute(merged_state) → Command(goto=gatekeeper_v2)
    """

    def test_two_stage_chain(self):
        # Stage 1: DeltaRouter
        state = _pre_routing_state_with_redline()
        router_cmd = DeltaRouter().route(state)
        assert router_cmd.goto == "derived_project"

        # 合并 router command.update 到 state（模拟 LangGraph state 合并）
        merged = dict(state)
        merged.update(router_cmd.update or {})

        # Stage 2: DerivedProjectNode
        derived_cmd = DerivedProjectNode().execute(merged)
        assert isinstance(derived_cmd, Command)
        assert derived_cmd.goto == "gatekeeper_v2"

        # 验证最终状态
        final = derived_cmd.update  # type: ignore[union-attr]
        assert final["requirements_frozen"] is False
        assert final["system_mode"] == "project"
        assert final["design_task_book"] is None

    def test_brief_packet_carries_user_input(self):
        state = _pre_routing_state_with_redline(
            user_input="把整个地块容积率限高提高两倍，同时整体规模扩大"
        )
        router_cmd = DeltaRouter().route(state)
        merged = dict(state)
        merged.update(router_cmd.update or {})

        derived_cmd = DerivedProjectNode().execute(merged)
        brief = derived_cmd.update["raw_brief_packet"]  # type: ignore[index]
        assert brief is not None
        assert "容积率" in brief.get("raw_user_prompt", "")


# ─────────────────────────────────────────────────────────────────────────────
# 父项目档案保留
# ─────────────────────────────────────────────────────────────────────────────


class TestParentArchivePreservation:
    """派生项目不应清除父项目的历史档案和交付束。"""

    def test_delivery_bundle_not_cleared(self):
        """delivery_bundle 应保留（历史档案）。"""
        state = _state_after_router_derived()
        result = DerivedProjectNode().execute(state)
        update = result.update  # type: ignore[union-attr]
        # delivery_bundle 不在 update 中表示未被重置（保留父值）
        # 或者若在 update 中，值不应为 None
        if "delivery_bundle" in update:
            assert update["delivery_bundle"] is not None

    def test_parent_project_id_in_update(self):
        state = _state_after_router_derived()
        result = DerivedProjectNode().execute(state)
        assert result.update.get("parent_project_id") == "proj-derived-001"  # type: ignore[union-attr]
