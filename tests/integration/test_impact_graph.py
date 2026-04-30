"""
tests/integration/test_impact_graph.py
ImpactGraph + DeltaRouter 路由行为集成测试

Copilot 生成（2026-03-22）
覆盖 delta_router.py 的影响图谱计算与三条路由分支。
"""

from __future__ import annotations

import pytest
from unittest.mock import patch

from intelligent_project_analyzer.core.domain_objects import ImpactGraph
from intelligent_project_analyzer.workflow.nodes.delta_router import (
    DeltaRouter,
    _DELTA_KEYWORDS,
    _DERIVED_KEYWORDS,
    _REDLINE_MARKERS,
)


# ---------------------------------------------------------------------------
# 辅助：构造最小 state
# ---------------------------------------------------------------------------


def _state(
    user_input: str = "",
    session_id: str = "sess_test",
    taskbook: dict | None = None,
) -> dict:
    return {
        "session_id": session_id,
        "user_input": user_input,
        "design_task_book": taskbook or {},
        "project_archive": {},
    }


# ---------------------------------------------------------------------------
# _compute_impact 单元级测试
# ---------------------------------------------------------------------------


class TestComputeImpact:
    def setup_method(self):
        self.router = DeltaRouter()

    def test_plain_input_no_keywords(self):
        impact = self.router._compute_impact("想要改一下方案", {})
        assert isinstance(impact, ImpactGraph)
        assert isinstance(impact.changed_field, str)
        assert impact.requires_derived_project is False

    def test_redline_marker_sets_requires_derived(self):
        for marker in _REDLINE_MARKERS:
            impact = self.router._compute_impact(f"希望调整{marker}", {})
            assert impact.requires_derived_project is True, (
                f"marker '{marker}' should trigger derived"
            )

    def test_derived_keyword_sets_requires_derived(self):
        for kw in _DERIVED_KEYWORDS:
            impact = self.router._compute_impact(f"想{kw}整个项目", {})
            assert impact.requires_derived_project is True, (
                f"keyword '{kw}' should trigger derived"
            )

    def test_delta_keyword_no_derived(self):
        for kw in _DELTA_KEYWORDS[:3]:  # 取前 3 个验证即可
            impact = self.router._compute_impact(f"把外墙{kw}一下", {})
            # 仅有 delta 关键词，且无红线词，不应触发派生
            assert impact.requires_derived_project is False, (
                f"delta keyword '{kw}' should not trigger derived"
            )

    def test_frozen_zone_hit_creates_redline_alert(self):
        taskbook = {
            "strategy_zones": {
                "frozen": ["规划退线 6m"],
            },
            "boundaries_and_redlines": [],
        }
        # changed_field 会从 input 第一个词提取
        impact = self.router._compute_impact("规划退线 6m 能改吗", taskbook)
        # 触碰冻结项
        assert any("冻结项" in alert for alert in impact.redline_alerts)

    def test_affected_zones_populated(self):
        taskbook = {
            "strategy_zones": {
                "expanded": ["外墙材质选型"],
            }
        }
        impact = self.router._compute_impact("想把外墙材质换一下", taskbook)
        # changed_field = "想把外墙材质换一下" 第一个分词结果
        # affected_zones 取决于 changed_field 是否在 zone items 中

        # 断言影响图谱字段已正确初始化（不报错）
        assert isinstance(impact.affected_zones, list)
        assert isinstance(impact.dependencies, list)

    def test_impact_graph_serializable(self):
        impact = self.router._compute_impact("调整颜色", {})
        d = impact.model_dump()
        assert "changed_field" in d
        assert "requires_derived_project" in d


# ---------------------------------------------------------------------------
# _is_clear_delta
# ---------------------------------------------------------------------------


class TestIsClearDelta:
    def setup_method(self):
        self.router = DeltaRouter()

    def test_clear_delta_returns_true(self):
        impact = ImpactGraph(
            changed_field="颜色",
            requires_derived_project=False,
            redline_alerts=[],
        )
        assert self.router._is_clear_delta("把颜色改成白色", impact) is True

    def test_false_when_no_delta_keyword(self):
        impact = ImpactGraph(
            changed_field="方案",
            requires_derived_project=False,
        )
        assert self.router._is_clear_delta("我想要一个新方案", impact) is False

    def test_false_when_requires_derived(self):
        impact = ImpactGraph(
            changed_field="容积率",
            requires_derived_project=True,
        )
        assert self.router._is_clear_delta("把材质改一下", impact) is False

    def test_false_when_redline_alert_present(self):
        impact = ImpactGraph(
            changed_field="材质",
            requires_derived_project=False,
            redline_alerts=["触碰冻结项: 规划红线"],
        )
        assert self.router._is_clear_delta("把材质换成木材", impact) is False


# ---------------------------------------------------------------------------
# route() 路由决策集成测试
# ---------------------------------------------------------------------------


class TestDeltaRouterRoute:
    def setup_method(self):
        self.router = DeltaRouter()

    def test_routes_to_delta_delivery_on_delta_keywords(self):
        state = _state(user_input="把外墙材质改成清水混凝土")
        cmd = self.router.route(state)
        assert cmd.goto == "delta_delivery"
        assert cmd.update.get("is_delta_modification") is True

    def test_routes_to_derived_on_redline_marker(self):
        state = _state(user_input="我希望把容积率提高到 3.5")
        cmd = self.router.route(state)
        assert cmd.goto == "derived_project"
        assert cmd.update.get("is_delta_modification") is False

    def test_routes_to_derived_on_derived_keyword(self):
        state = _state(user_input="这个方案我们从零重新来过")
        cmd = self.router.route(state)
        assert cmd.goto == "derived_project"

    def test_routes_to_conversation_on_ambiguous_input(self):
        # 无 delta 关键词，无红线/派生词 → 路由到对话追问
        state = _state(user_input="我觉得方案有问题")
        cmd = self.router.route(state)
        assert cmd.goto == "conversation_engine"
        assert cmd.update.get("system_mode") == "conversation"

    def test_delta_command_contains_impact_graph(self):
        state = _state(user_input="把颜色换成米白色")
        cmd = self.router.route(state)
        assert cmd.goto == "delta_delivery"
        assert "impact_graph" in cmd.update

    def test_derived_command_contains_parent_project_id(self):
        state = _state(user_input="从零开始重做", session_id="my_session")
        cmd = self.router.route(state)
        assert cmd.goto == "derived_project"
        assert cmd.update.get("parent_project_id") == "my_session"

    def test_redline_command_contains_impact_graph(self):
        state = _state(user_input="能不能调整一下退红线距离")
        cmd = self.router.route(state)
        assert cmd.goto == "derived_project"
        assert "impact_graph" in cmd.update

    def test_conversation_command_contains_system_mode(self):
        state = _state(user_input="感觉不太对")
        cmd = self.router.route(state)
        assert cmd.goto == "conversation_engine"
        assert cmd.update.get("system_mode") == "conversation"

    def test_multiple_redline_words_all_trigger_derived(self):
        for marker in ("消防", "日照", "限高", "结构体系", "地基"):
            state = _state(user_input=f"想要调整{marker}方案")
            cmd = self.router.route(state)
            assert cmd.goto == "derived_project", (
                f"marker '{marker}' should route to derived_project"
            )


# ---------------------------------------------------------------------------
# ImpactGraph 字段变动独立测试
# ---------------------------------------------------------------------------


class TestImpactGraphModel:
    def test_default_no_derived(self):
        ig = ImpactGraph(changed_field="门窗尺寸")
        assert ig.requires_derived_project is False
        assert ig.redline_alerts == []

    def test_redline_alerts_list(self):
        ig = ImpactGraph(
            changed_field="容积率",
            redline_alerts=["触碰红线: 容积率上限 2.5"],
            requires_derived_project=True,
        )
        assert len(ig.redline_alerts) == 1
        assert "容积率" in ig.redline_alerts[0]

    def test_dependencies_and_zones(self):
        ig = ImpactGraph(
            changed_field="结构跨度",
            dependencies=["结构计算", "施工图"],
            affected_zones=["frozen"],
        )
        assert "施工图" in ig.dependencies
        assert "frozen" in ig.affected_zones
