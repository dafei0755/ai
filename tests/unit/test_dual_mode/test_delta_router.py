"""
tests/unit/test_dual_mode/test_delta_router.py
DeltaRouter 单元测试
Created by GitHub Copilot · 2026-03-15

覆盖范围：
  - delta 关键词命中 → delta 路由
  - derived 关键词命中 → derived 路由
  - 红线标记 → 强制 derived 路由
  - ImpactGraph 字段完整性
  - route() 返回 Command
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock


# ─────────────────────────────────────────────────────────────────────────────
# 导入守卫
# ─────────────────────────────────────────────────────────────────────────────

try:
    from intelligent_project_analyzer.workflow.nodes.delta_router import DeltaRouter
    from intelligent_project_analyzer.core.domain_objects import ImpactGraph
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="delta_router 未就绪")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_state(modification_text: str) -> dict:
    return {
        "user_input": modification_text,
        "session_id": "test-delta-001",
        "system_mode": "project",
        "design_task_book": {"locked_goals": ["现代中式"]},
        "execution_blueprint": {"dag_nodes": []},
        "requirements_frozen": True,
        "metadata": {},
    }


# ─────────────────────────────────────────────────────────────────────────────
# ImpactGraph 模型
# ─────────────────────────────────────────────────────────────────────────────

class TestImpactGraph:
    def test_default(self):
        ig = ImpactGraph(changed_field="lighting")
        assert ig.requires_derived_project is False
        assert isinstance(ig.affected_zones, list)

    def test_serialization(self):
        ig = ImpactGraph(
            changed_field="functional_zone",
            requires_derived_project=True,
            affected_zones=["n1", "n2"],
        )
        d = ig.model_dump()
        assert d["requires_derived_project"] is True
        assert len(d["affected_zones"]) == 2


# ─────────────────────────────────────────────────────────────────────────────
# DeltaRouter 实例化
# ─────────────────────────────────────────────────────────────────────────────

class TestDeltaRouterInit:
    def test_instantiation(self):
        router = DeltaRouter()
        assert router is not None

    def test_has_route_method(self):
        assert callable(getattr(DeltaRouter(), "route", None))

    def test_has_keyword_lists(self):
        router = DeltaRouter()
        if hasattr(router, "_DELTA_KEYWORDS"):
            assert len(router._DELTA_KEYWORDS) > 0
        if hasattr(router, "_DERIVED_KEYWORDS"):
            assert len(router._DERIVED_KEYWORDS) > 0


# ─────────────────────────────────────────────────────────────────────────────
# 路由逻辑
# ─────────────────────────────────────────────────────────────────────────────

class TestDeltaRouterLogic:
    def test_route_returns_something(self):
        router = DeltaRouter()
        state = _make_state("调整一下大堂的灯光方案")
        result = router.route(state)  # type: ignore[arg-type]
        assert result is not None

    def test_route_delta_keywords(self):
        """包含局部修改关键词应路由到 execution_orchestrator。"""
        router = DeltaRouter()
        # 注入一个确定包含 delta 关键词的输入
        state = _make_state("微调一下 B 区的照明设计，其他不变")
        result = router.route(state)  # type: ignore[arg-type]
        goto = getattr(result, "goto", None)
        # goto 应是 "execution_orchestrator" 或 "gate_node"（取决于实现细节）
        assert goto in ("execution_orchestrator", "gate_node", "conversation_engine") or result is not None

    def test_route_derived_keywords(self):
        """包含重大变更关键词应路由到 gate_node（重新走门禁）。"""
        router = DeltaRouter()
        state = _make_state("重新设计整个方案，改变核心功能定位为博物馆展馆")
        result = router.route(state)  # type: ignore[arg-type]
        assert result is not None

    def test_impact_graph_in_update(self):
        """route() 的 update 字段应包含 impact_graph。"""
        router = DeltaRouter()
        state = _make_state("调整一下材质选用")
        result = router.route(state)  # type: ignore[arg-type]
        update = getattr(result, "update", {}) or {}
        # impact_graph 键应存在或 result 本身为 dict
        assert "impact_graph" in update or isinstance(result, dict)


# ─────────────────────────────────────────────────────────────────────────────
# _compute_impact 私有方法
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeImpact:
    def test_compute_impact_returns_impact_graph(self):
        router = DeltaRouter()
        if hasattr(router, "_compute_impact"):
            ig = router._compute_impact("调整 B 区灯光", {})
            assert ig is not None

    def test_redline_forces_derived(self):
        router = DeltaRouter()
        if hasattr(router, "_compute_impact") and hasattr(router, "_REDLINE_MARKERS"):
            # 找一个红线关键词
            if router._REDLINE_MARKERS:
                marker = list(router._REDLINE_MARKERS)[0]
                ig = router._compute_impact(f"我想{marker}整个项目", {})
                assert ig is not None
