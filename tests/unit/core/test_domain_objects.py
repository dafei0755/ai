"""
tests/unit/core/test_domain_objects.py
领域对象层单元测试 — 双态架构核心产物

Copilot 生成（2026-03-22）
覆盖 intelligent_project_analyzer/core/domain_objects.py 中所有 Pydantic 模型。
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from intelligent_project_analyzer.core.domain_objects import (
    # 枚举
    InteractionState,
    GateStatus,
    DraftStatus,
    SystemMode,
    # 项目态主链
    RawBriefPacket,
    GapDiagnosis,
    ExtremeOption,
    GateDecision,
    StrategyZone,
    DesignTaskBook,
    DAGNode,
    ReviewGate,
    ExecutionBlueprint,
    DeliveryBundle,
    # 增量派生
    DeltaDelivery,
    DerivedProject,
    ImpactGraph,
    # 草稿对象
    DraftObjectMeta,
    IntentSeed,
    ProblemFrameDraft,
    DirectionCandidatePack,
    ConflictPack,
    BoundaryDraft,
    ConsensusPack,
    # 升级信号
    CognitionIndicators,
    UpgradeSignal,
    # 项目档案
    ProjectArchive,
)


# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------


class TestEnums:
    def test_gate_status_values(self):
        assert GateStatus.CONTINUE == "continue"
        assert GateStatus.CONVERSATION == "conversation"
        assert GateStatus.CONDITIONAL_CONTINUE == "conditional_continue"
        assert GateStatus.REJECT == "reject"
        assert GateStatus.NEED_MORE_PREREQUISITE == "need_more_prerequisite"

    def test_interaction_state_values(self):
        assert InteractionState.CONVERSATION == "conversation"
        assert InteractionState.PROJECT == "project"

    def test_draft_status_values(self):
        assert DraftStatus.DRAFT == "draft"
        assert DraftStatus.CONFIRMED == "confirmed"
        assert DraftStatus.UPGRADED == "upgraded"

    def test_system_mode_values(self):
        assert SystemMode.CONVERSATION == "conversation"
        assert SystemMode.PROJECT == "project"


# ---------------------------------------------------------------------------
# 项目态主链对象
# ---------------------------------------------------------------------------


class TestRawBriefPacket:
    def test_minimal_construction(self):
        pkt = RawBriefPacket(raw_user_prompt="设计一个住宅")
        assert pkt.raw_user_prompt == "设计一个住宅"
        assert pkt.attachments == []
        assert pkt.initial_context == {}
        assert pkt.session_or_project_stub is None
        assert pkt.prefill_from_drafts == {}

    def test_full_construction(self):
        pkt = RawBriefPacket(
            raw_user_prompt="改一下",
            attachments=[{"type": "image", "url": "s3://bucket/img.jpg"}],
            initial_context={"site": "北京"},
            session_or_project_stub="proj_001",
            prefill_from_drafts={"intent_seed": "content"},
        )
        assert len(pkt.attachments) == 1
        assert pkt.session_or_project_stub == "proj_001"

    def test_serializable_to_dict(self):
        pkt = RawBriefPacket(raw_user_prompt="test")
        d = pkt.model_dump()
        assert "raw_user_prompt" in d
        assert "attachments" in d


class TestGapDiagnosis:
    def test_defaults(self):
        g = GapDiagnosis(gap_index=0, description="预算缺口")
        assert g.severity == "major"

    def test_blocker_severity(self):
        g = GapDiagnosis(gap_index=1, description="无法推进", severity="blocker")
        assert g.severity == "blocker"


class TestGateDecision:
    def test_defaults(self):
        gd = GateDecision(status=GateStatus.CONTINUE, reason="条件满足")
        assert gd.interaction_state == InteractionState.CONVERSATION
        assert gd.gap_diagnosis == []
        assert gd.extreme_options == []

    def test_with_gap_and_options(self):
        gd = GateDecision(
            status=GateStatus.CONDITIONAL_CONTINUE,
            reason="有缺口",
            gap_diagnosis=[GapDiagnosis(gap_index=0, description="场地未确认")],
            extreme_options=[
                ExtremeOption(label="极省版", description="最低成本"),
                ExtremeOption(label="极优版", description="最高品质"),
            ],
        )
        assert len(gd.gap_diagnosis) == 1
        assert len(gd.extreme_options) == 2
        assert gd.extreme_options[0].label == "极省版"

    def test_boundary_notes_and_preconditions(self):
        gd = GateDecision(
            status=GateStatus.REJECT,
            reason="违规",
            boundary_notes=["超出限高"],
            required_preconditions=["取得规划许可"],
        )
        assert "超出限高" in gd.boundary_notes


class TestDesignTaskBook:
    def test_not_frozen_by_default(self):
        dtb = DesignTaskBook(
            project_intent="降成本公共校舍",
            core_proposition="成本优先",
        )
        assert dtb.frozen is False
        assert isinstance(dtb.strategy_zones, StrategyZone)

    def test_strategy_zones_populated(self):
        dtb = DesignTaskBook(
            project_intent="民宿",
            core_proposition="体验优先",
            strategy_zones=StrategyZone(
                frozen=["规划红线"],
                expanded=["立面风格"],
            ),
        )
        assert "规划红线" in dtb.strategy_zones.frozen
        assert "立面风格" in dtb.strategy_zones.expanded

    def test_can_set_frozen(self):
        dtb = DesignTaskBook(
            project_intent="审查通过后锁定",
            core_proposition="合规",
            frozen=True,
        )
        assert dtb.frozen is True


class TestExecutionBlueprint:
    def test_defaults(self):
        eb = ExecutionBlueprint()
        assert eb.frozen is False
        assert eb.deliverable_dag == []
        assert eb.review_gates == []

    def test_with_dag_and_gates(self):
        dag = [
            DAGNode(
                node_id="d1",
                name="方案图",
                owner_role="建筑师",
                success_criteria=["CAD 封图"],
            )
        ]
        gates = [
            ReviewGate(
                gate_id="g1",
                after_node_id="d1",
                gate_type="quality",
                description="首版方案评审",
            )
        ]
        eb = ExecutionBlueprint(deliverable_dag=dag, review_gates=gates)
        assert eb.deliverable_dag[0].node_id == "d1"
        assert eb.review_gates[0].gate_id == "g1"

    def test_budget_guard(self):
        eb = ExecutionBlueprint(budget_guard={"generate_image": 5})
        assert eb.budget_guard["generate_image"] == 5


class TestDeliveryBundle:
    def test_all_defaults(self):
        db = DeliveryBundle()
        assert db.final_deliverables == []
        assert db.stage_deliverables == []
        assert db.version_lineage == []
        assert db.risk_summary == {}

    def test_version_lineage(self):
        db = DeliveryBundle(version_lineage=["v1", "v1.1", "v1.2"])
        assert db.version_lineage == ["v1", "v1.1", "v1.2"]


# ---------------------------------------------------------------------------
# 增量派生对象
# ---------------------------------------------------------------------------


class TestDeltaDelivery:
    def test_construction(self):
        dd = DeltaDelivery(
            delta_target="修改外墙材质",
            original_ref="delivery_v1",
            modified_fields=["外墙材质"],
            impact_scope=["立面图", "效果图"],
            delta_result={"status": "ok"},
        )
        assert dd.delta_target == "修改外墙材质"
        assert "立面图" in dd.impact_scope

    def test_defaults(self):
        dd = DeltaDelivery(delta_target="小调整", original_ref="v0")
        assert dd.modified_fields == []
        assert dd.impact_scope == []
        assert dd.delta_result == {}


class TestDerivedProject:
    def test_partial_inheritance_default(self):
        dp = DerivedProject(
            parent_project_id="proj_001",
            diverge_point="S3 策略层",
        )
        assert dp.inheritance_mode == "partial"
        assert dp.new_brief_packet is None

    def test_full_mode(self):
        dp = DerivedProject(
            parent_project_id="p0",
            diverge_point="初始",
            inheritance_mode="full",
        )
        assert dp.inheritance_mode == "full"

    def test_with_new_brief(self):
        brief = RawBriefPacket(raw_user_prompt="全新方向")
        dp = DerivedProject(
            parent_project_id="p0",
            diverge_point="S3",
            new_brief_packet=brief,
            new_session_id="new_session_xyz",
        )
        assert dp.new_brief_packet.raw_user_prompt == "全新方向"
        assert dp.new_session_id == "new_session_xyz"


class TestImpactGraph:
    def test_defaults(self):
        ig = ImpactGraph(changed_field="外墙材质")
        assert ig.dependencies == []
        assert ig.affected_zones == []
        assert ig.redline_alerts == []
        assert ig.requires_derived_project is False

    def test_with_redline(self):
        ig = ImpactGraph(
            changed_field="容积率",
            redline_alerts=["触碰红线: 容积率上限"],
            requires_derived_project=True,
        )
        assert ig.requires_derived_project is True
        assert len(ig.redline_alerts) == 1

    def test_serializable(self):
        ig = ImpactGraph(
            changed_field="楼高",
            dependencies=["结构体系"],
            affected_zones=["frozen"],
        )
        d = ig.model_dump()
        assert d["changed_field"] == "楼高"
        assert "frozen" in d["affected_zones"]


# ---------------------------------------------------------------------------
# 对话态草稿对象
# ---------------------------------------------------------------------------


class TestDraftObjectMeta:
    def test_defaults(self):
        m = DraftObjectMeta(source="round_1")
        assert m.user_confirmed is False
        assert m.inferred is False
        assert m.open_questions == []
        assert m.upgrade_ready is False

    def test_confirmed_and_ready(self):
        m = DraftObjectMeta(
            source="round_3",
            user_confirmed=True,
            upgrade_ready=True,
        )
        assert m.user_confirmed is True
        assert m.upgrade_ready is True


class TestDraftObjects:
    def test_intent_seed(self):
        seed = IntentSeed(
            content="想做一个可以和社区互动的书店",
            keywords=["书店", "社区"],
        )
        assert seed.content.startswith("想做")
        assert "书店" in seed.keywords
        assert seed.meta.source == ""

    def test_problem_frame_draft(self):
        d = ProblemFrameDraft(
            problem_statement="如何在限高下最大化使用效率",
            sub_problems=["结构优化", "层高分配"],
        )
        assert len(d.sub_problems) == 2

    def test_direction_candidate_pack(self):
        pack = DirectionCandidatePack(
            candidates=[
                {"id": "A", "name": "极简风"},
                {"id": "B", "name": "工业风"},
            ]
        )
        assert len(pack.candidates) == 2

    def test_conflict_pack(self):
        cp = ConflictPack(conflicts=["成本 vs 品质", "效率 vs 体验"])
        assert len(cp.conflicts) == 2

    def test_boundary_draft(self):
        bd = BoundaryDraft(
            hard_constraints=["不超过 60m 限高"],
            soft_preferences=["尽量使用本地材料"],
        )
        assert "60m" in bd.hard_constraints[0]
        assert bd.soft_preferences[0].startswith("尽量")

    def test_consensus_pack(self):
        cp = ConsensusPack(
            agreed_items=["建筑面积 5000㎡"],
            pending_items=["立面材质待定"],
        )
        assert len(cp.agreed_items) == 1
        assert len(cp.pending_items) == 1


# ---------------------------------------------------------------------------
# 升级信号
# ---------------------------------------------------------------------------


class TestCognitionIndicators:
    def test_not_triggered_below_thresholds(self):
        ci = CognitionIndicators(
            freeze_readiness=0.5,
            cognitive_debt=0.5,
            diverge_fatigue=0.5,
        )
        assert ci.should_trigger_upgrade is False

    def test_not_triggered_partial_thresholds(self):
        # freeze_readiness 超过，其他两项未超过
        ci = CognitionIndicators(
            freeze_readiness=0.9,
            cognitive_debt=0.5,
            diverge_fatigue=0.8,
        )
        assert ci.should_trigger_upgrade is False

    def test_triggered_at_exact_thresholds(self):
        ci = CognitionIndicators(
            freeze_readiness=0.7,
            cognitive_debt=0.6,
            diverge_fatigue=0.6,
        )
        assert ci.should_trigger_upgrade is True

    def test_triggered_above_thresholds(self):
        ci = CognitionIndicators(
            freeze_readiness=0.95,
            cognitive_debt=0.85,
            diverge_fatigue=0.75,
        )
        assert ci.should_trigger_upgrade is True

    def test_defaults_not_triggered(self):
        ci = CognitionIndicators()
        assert ci.should_trigger_upgrade is False


class TestUpgradeSignal:
    def test_defaults(self):
        us = UpgradeSignal()
        assert us.triggered is False
        assert us.suggestion_text == ""
        assert isinstance(us.indicators, CognitionIndicators)

    def test_triggered_signal(self):
        indicators = CognitionIndicators(
            freeze_readiness=0.8,
            cognitive_debt=0.7,
            diverge_fatigue=0.7,
        )
        us = UpgradeSignal(
            indicators=indicators,
            suggestion_text="建议此刻进入项目态",
            triggered=True,
        )
        assert us.triggered is True
        assert us.indicators.should_trigger_upgrade is True


# ---------------------------------------------------------------------------
# 项目档案
# ---------------------------------------------------------------------------


class TestProjectArchive:
    def test_minimal_construction(self):
        pa = ProjectArchive(project_id="p123", session_id="s456")
        assert pa.project_id == "p123"
        assert pa.session_id == "s456"
        assert pa.delivery_bundle is None
        assert pa.design_task_book is None
        assert pa.execution_blueprint is None
        assert pa.version_lineage == []
        assert pa.decision_records == []
        assert pa.review_traces == []
        assert pa.risk_summary == {}

    def test_full_construction(self):
        bundle = DeliveryBundle(version_lineage=["v1", "v2"])
        dtb = DesignTaskBook(project_intent="民宿", core_proposition="体验", frozen=True)
        pa = ProjectArchive(
            project_id="proj_final",
            session_id="session_001",
            delivery_bundle=bundle,
            design_task_book=dtb,
            version_lineage=["v1", "v2"],
            decision_records=[{"decision": "确认限高 24m", "round": 3}],
        )
        assert pa.delivery_bundle.version_lineage == ["v1", "v2"]
        assert pa.design_task_book.frozen is True
        assert len(pa.decision_records) == 1

    def test_serializable_roundtrip(self):
        pa = ProjectArchive(project_id="test", session_id="sess")
        d = pa.model_dump()
        pa2 = ProjectArchive(**d)
        assert pa2.project_id == pa.project_id
