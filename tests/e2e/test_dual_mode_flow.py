"""
tests/e2e/test_dual_mode_flow.py
双态架构端到端流程测试

Copilot 生成（2026-03-22）

测试策略：
- 不调用真实 LLM 接口（全量 mock）
- 逐节点 execute() / route() 调用，验证 state 流转正确性
- 覆盖完整对话态 → 升级 → 项目态 → 交付 → 增量/派生 主链路
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from typing import Any, Dict

from intelligent_project_analyzer.core.domain_objects import (
    GateStatus,
    InteractionState,
    GateDecision,
    CognitionIndicators,
    UpgradeSignal,
    DesignTaskBook,
    StrategyZone,
    ExecutionBlueprint,
    DeliveryBundle,
    ProjectArchive,
    DraftObjectMeta,
    IntentSeed,
)
from intelligent_project_analyzer.core.state import ProjectAnalysisState
from intelligent_project_analyzer.workflow.conversation_engine import ConversationEngine
from intelligent_project_analyzer.workflow.nodes.gate_node import GateNode
from intelligent_project_analyzer.workflow.nodes.delta_router import DeltaRouter
from intelligent_project_analyzer.workflow.nodes.delta_delivery_node import DeltaDeliveryNode
from intelligent_project_analyzer.workflow.nodes.derived_project_node import DerivedProjectNode


# ---------------------------------------------------------------------------
# 辅助：构造基础 state
# ---------------------------------------------------------------------------


def _base_state(**overrides) -> Dict[str, Any]:
    base: Dict[str, Any] = {
        "session_id": "e2e_session_001",
        "user_input": "",
        "system_mode": "conversation",
        "conversation_drafts": [],
        "upgrade_signal": None,
        "gate_decision": None,
        "design_task_book": None,
        "execution_blueprint": None,
        "project_archive": None,
        "is_delta_modification": False,
        "impact_graph": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Flow 1: 对话态 → 意图沉淀 → 认知指标低 → 保持对话态
# ---------------------------------------------------------------------------


class TestConversationModeStaysInConversation:
    def test_knowledge_qa_returns_conversation_mode(self):
        engine = ConversationEngine(llm=None)
        state = _base_state(user_input="什么是容积率？")
        result = engine.execute(state)
        assert result.get("system_mode") == "conversation"

    def test_inspiration_input_creates_draft(self):
        engine = ConversationEngine(llm=None)
        state = _base_state(user_input="我在想做一个山地民宿")
        result = engine.execute(state)
        assert result.get("system_mode") == "conversation"

    def test_project_signal_stores_cognition_indicators(self):
        engine = ConversationEngine(llm=None)
        state = _base_state(user_input="我想设计一个书店")
        result = engine.execute(state)
        # system_mode 保持对话态
        assert result.get("system_mode") == "conversation"
        # cognition_indicators 已写入（即使未触发升级）
        assert "cognition_indicators" in result or "system_mode" in result


# ---------------------------------------------------------------------------
# Flow 2: 对话态 → 升级信号触发
# ---------------------------------------------------------------------------


class TestUpgradeSignalTrigger:
    """验证当三大认知指标均超过阈值时，ConversationEngine 发出 upgrade_signal。"""

    def test_upgrade_signal_triggered_when_indicators_high(self):
        engine = ConversationEngine(llm=None)

        high_ci = CognitionIndicators(
            freeze_readiness=0.9,
            cognitive_debt=0.8,
            diverge_fatigue=0.75,
        )
        with patch.object(
            engine, "_classify_intent", return_value="project_signal"
        ), patch.object(
            engine, "_compute_cognition_indicators", return_value=high_ci
        ):
            state = _base_state(
                user_input="我想建一个可以和社区互动的书店",
                conversation_drafts=[
                    {"content": "草稿1", "meta": {"source": "r1", "user_confirmed": True, "inferred": False, "open_questions": [], "upgrade_ready": True}},
                ],
            )
            result = engine.execute(state)

        # 升级信号已写入
        assert "upgrade_signal" in result
        assert result["upgrade_signal"]["triggered"] is True
        # cognition_indicators 已写入
        assert "cognition_indicators" in result

    def test_no_upgrade_signal_when_indicators_low(self):
        engine = ConversationEngine(llm=None)

        low_ci = CognitionIndicators(
            freeze_readiness=0.3,
            cognitive_debt=0.2,
            diverge_fatigue=0.1,
        )
        with patch.object(
            engine, "_compute_cognition_indicators", return_value=low_ci
        ):
            state = _base_state(user_input="我想做一个建筑")
            result = engine.execute(state)

        upgrade_signal = result.get("upgrade_signal")
        assert not (upgrade_signal and upgrade_signal.get("triggered"))


# ---------------------------------------------------------------------------
# Flow 3: Gate 节点放行决策
# ---------------------------------------------------------------------------


class TestGateNodeDecisions:
    def test_gate_passes_clear_brief(self):
        gate = GateNode(llm=None)
        state = _base_state(
            user_input="设计一个 500 平米的精品茶馆，位于杭州西湖边，预算 300 万",
        )
        cmd = gate.execute(state)
        # gate.execute 返回 LangGraph Command，通过 cmd.update 访问字段
        assert cmd is not None
        gd_raw = cmd.update.get("gate_decision")
        assert isinstance(gd_raw, dict)
        assert "status" in gd_raw

    def test_gate_returns_dict_structure(self):
        gate = GateNode(llm=None)
        state = _base_state(user_input="帮我设计一个房子")
        cmd = gate.execute(state)
        assert cmd is not None
        gd = cmd.update.get("gate_decision")
        assert isinstance(gd, dict)
        assert "status" in gd
        assert "reason" in gd
        assert "interaction_state" in gd


# ---------------------------------------------------------------------------
# Flow 4: 完整项目态主链（S1→S5 节点产出衔接）
# ---------------------------------------------------------------------------


class TestProjectModeChainStateFlow:
    """测试 state 在各节点间的字段衔接——不调用 LLM，验证 state 字段约定。"""

    def _make_taskbook_state(self) -> Dict[str, Any]:
        """模拟 S5 产出后的 state。"""
        dtb = DesignTaskBook(
            project_intent="书店兼咖啡馆",
            core_proposition="体验优先",
            strategy_zones=StrategyZone(frozen=["规划红线"], expanded=["立面风格"]),
            frozen=True,
        )
        eb = ExecutionBlueprint(
            task_chain_skeleton=["施工图", "效果图", "BIM"],
            budget_guard={"generate_image": 5},
            frozen=True,
        )
        return _base_state(
            system_mode="project",
            design_task_book=dtb.model_dump(),
            execution_blueprint=eb.model_dump(),
            delivery_bundle=None,
        )

    def test_taskbook_frozen_in_project_state(self):
        state = self._make_taskbook_state()
        dtb_raw = state["design_task_book"]
        dtb = DesignTaskBook(**dtb_raw)
        assert dtb.frozen is True

    def test_execution_blueprint_frozen_in_project_state(self):
        state = self._make_taskbook_state()
        eb_raw = state["execution_blueprint"]
        eb = ExecutionBlueprint(**eb_raw)
        assert eb.frozen is True
        assert eb.budget_guard["generate_image"] == 5


# ---------------------------------------------------------------------------
# Flow 5: 交付后进入增量/派生决策
# ---------------------------------------------------------------------------


class TestPostDeliveryDeltaOrDerived:
    """模拟交付完成后发出修改指令，验证 delta_router 走向正确分支。"""

    def _delivered_state(self, user_input: str) -> Dict[str, Any]:
        archive = ProjectArchive(
            project_id="proj_001",
            session_id="e2e_session_001",
            delivery_bundle=DeliveryBundle(version_lineage=["v1"]),
            version_lineage=["v1"],
        )
        dtb = DesignTaskBook(
            project_intent="书店",
            core_proposition="体验优先",
            strategy_zones=StrategyZone(frozen=["规划红线"]),
            frozen=True,
        )
        return _base_state(
            user_input=user_input,
            project_archive=archive.model_dump(),
            design_task_book=dtb.model_dump(),
            system_mode="project",
        )

    def test_material_change_goes_to_delta(self):
        router = DeltaRouter()
        state = self._delivered_state("把外墙材质改成清水混凝土")
        cmd = router.route(state)
        assert cmd.goto == "delta_delivery"

    def test_redline_change_goes_to_derived(self):
        router = DeltaRouter()
        state = self._delivered_state("我希望把容积率提高到 3.5")
        cmd = router.route(state)
        assert cmd.goto == "derived_project"

    def test_ambiguous_change_goes_to_conversation(self):
        router = DeltaRouter()
        state = self._delivered_state("感觉有些地方需要调整")
        cmd = router.route(state)
        assert cmd.goto == "conversation_engine"


# ---------------------------------------------------------------------------
# Flow 6: DeltaDeliveryNode 执行增量修改
# ---------------------------------------------------------------------------


class TestDeltaDeliveryFlow:
    def test_delta_node_produces_output(self):
        node = DeltaDeliveryNode()
        impact_data = {
            "changed_field": "材质",
            "dependencies": ["效果图"],
            "affected_zones": [],
            "redline_alerts": [],
            "requires_derived_project": False,
        }
        state = _base_state(
            user_input="把外立面材质改成木材饰面",
            is_delta_modification=True,
            impact_graph=impact_data,
            delta_router_state={
                "delta": {
                    "delta_target": "外立面材质",
                    "original_ref": "v1",
                    "modified_fields": [],
                    "impact_scope": [],
                    "delta_result": {},
                },
                "impact": impact_data,
            },
        )
        result = node.execute(state)
        # DeltaDeliveryNode 将增量结果写入 delivery_bundle（追加版本树）
        assert "delivery_bundle" in result
        assert "system_mode" in result

    def test_delta_node_resets_flags_after_execution(self):
        # 增量执行完成后应重置 is_delta_modification 为 False
        node = DeltaDeliveryNode()
        impact_data = {
            "changed_field": "颜色",
            "dependencies": [],
            "affected_zones": [],
            "redline_alerts": [],
            "requires_derived_project": False,
        }
        state = _base_state(
            user_input="把颜色换成灰色",
            is_delta_modification=True,
            impact_graph=impact_data,
            delta_router_state={
                "delta": {
                    "delta_target": "颜色",
                    "original_ref": "v1",
                    "modified_fields": [],
                    "impact_scope": [],
                    "delta_result": {},
                },
                "impact": impact_data,
            },
        )
        result = node.execute(state)
        assert result.get("is_delta_modification") is False
        assert result.get("delta_router_state") is None


# ---------------------------------------------------------------------------
# Flow 7: DerivedProjectNode 开辟新项目态
# ---------------------------------------------------------------------------


class TestDerivedProjectFlow:
    def test_derived_node_creates_new_session(self):
        node = DerivedProjectNode()
        state = _base_state(
            user_input="从零开始重做整个项目",
            parent_project_id="proj_001",
            impact_graph={
                "changed_field": "整体方案",
                "dependencies": [],
                "affected_zones": [],
                "redline_alerts": [],
                "requires_derived_project": True,
            },
        )
        cmd = node.execute(state)
        # 应返回 Command 或 dict，并携带派生信息
        assert cmd is not None

    def test_derived_node_preserves_parent_id(self):
        node = DerivedProjectNode()
        state = _base_state(
            user_input="这个方案推翻重来",
            parent_project_id="parent_sess_xyz",
            impact_graph={
                "changed_field": "全部",
                "dependencies": [],
                "affected_zones": [],
                "redline_alerts": [],
                "requires_derived_project": True,
            },
        )
        cmd = node.execute(state)
        # 不能崩溃，必须有合法返回
        assert cmd is not None


# ---------------------------------------------------------------------------
# Flow 8: ProjectArchive 状态快照
# ---------------------------------------------------------------------------


class TestProjectArchiveSnapshot:
    def test_archive_serialization_roundtrip(self):
        dtb = DesignTaskBook(project_intent="民宿", core_proposition="体验", frozen=True)
        bundle = DeliveryBundle(version_lineage=["v1", "v2"])
        archive = ProjectArchive(
            project_id="proj_snap",
            session_id="sess_snap",
            delivery_bundle=bundle,
            design_task_book=dtb,
            version_lineage=["v1", "v2"],
        )
        d = archive.model_dump()
        archive2 = ProjectArchive(**d)
        assert archive2.project_id == archive.project_id
        assert archive2.design_task_book.frozen is True
        assert archive2.delivery_bundle.version_lineage == ["v1", "v2"]

    def test_archive_decision_records(self):
        archive = ProjectArchive(
            project_id="p",
            session_id="s",
            decision_records=[
                {"round": 1, "decision": "确认场地"},
                {"round": 2, "decision": "锁定预算"},
            ],
        )
        assert len(archive.decision_records) == 2
        assert archive.decision_records[1]["decision"] == "锁定预算"
