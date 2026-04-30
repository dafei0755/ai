"""
tests/unit/test_dual_mode/test_risk_gates.py

四级动作门禁 RiskGateEngine 单元测试

Copilot 生成（2026-03-15）
覆盖：A / B / C / D 四级门控逻辑、audit_trail 记录、Budget Guard、
      create_gate_engine_from_blueprint 工厂函数。
"""

from __future__ import annotations

import pytest

from intelligent_project_analyzer.workflow.execution.risk_gates import (
    ActionRequest,
    GateOutcome,
    RiskGateEngine,
    RiskLevel,
    _ACTION_GATE_MAP,
    _DEFAULT_C_BUDGET,
    create_gate_engine_from_blueprint,
)


# ─────────────────────────────────────────────────────────────────────────────
# 辅助工厂
# ─────────────────────────────────────────────────────────────────────────────


def _req(action: str, desc: str = "") -> ActionRequest:
    return ActionRequest(action_name=action, description=desc, context={"from": "test"})


def _engine(**kwargs) -> RiskGateEngine:
    return RiskGateEngine(session_id="test-session", **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# ActionRequest
# ─────────────────────────────────────────────────────────────────────────────


class TestActionRequest:
    def test_known_action_level_a(self):
        req = _req("query_knowledge_base")
        assert req.risk_level() == RiskLevel.A

    def test_known_action_level_b(self):
        req = _req("search_web")
        assert req.risk_level() == RiskLevel.B

    def test_known_action_level_c(self):
        req = _req("generate_image")
        assert req.risk_level() == RiskLevel.C

    def test_known_action_level_d(self):
        req = _req("modify_frozen_zone")
        assert req.risk_level() == RiskLevel.D

    def test_unknown_action_defaults_to_b(self):
        req = _req("some_unknown_action_xyz")
        assert req.risk_level() == RiskLevel.B

    def test_request_has_unique_id(self):
        r1 = _req("search_web")
        r2 = _req("search_web")
        assert r1.request_id != r2.request_id

    def test_request_stores_context(self):
        req = ActionRequest("search_web", context={"query": "hotel"})
        assert req.context["query"] == "hotel"


# ─────────────────────────────────────────────────────────────────────────────
# GateOutcome
# ─────────────────────────────────────────────────────────────────────────────


class TestGateOutcome:
    def test_can_proceed_happy(self):
        outcome = GateOutcome("id", "search_web", RiskLevel.B, allowed=True)
        assert outcome.can_proceed is True

    def test_can_proceed_blocked(self):
        outcome = GateOutcome("id", "generate_image", RiskLevel.C,
                              allowed=False, blocked=True)
        assert outcome.can_proceed is False

    def test_can_proceed_needs_confirm(self):
        outcome = GateOutcome("id", "modify_frozen_zone", RiskLevel.D,
                              allowed=False, needs_confirm=True)
        assert outcome.can_proceed is False

    def test_to_dict_keys(self):
        outcome = GateOutcome("id", "search_web", RiskLevel.B, allowed=True)
        d = outcome.to_dict()
        for key in ("request_id", "action_name", "level", "allowed", "blocked",
                    "needs_confirm", "block_reason", "checked_at"):
            assert key in d


# ─────────────────────────────────────────────────────────────────────────────
# Level-A 门控
# ─────────────────────────────────────────────────────────────────────────────


class TestLevelA:
    def test_a_passes(self):
        engine = _engine()
        outcome = engine.check(_req("query_knowledge_base"))
        assert outcome.can_proceed is True
        assert outcome.blocked is False
        assert outcome.needs_confirm is False

    def test_a_level_recorded(self):
        engine = _engine()
        outcome = engine.check(_req("draft_compile"))
        assert outcome.level == RiskLevel.A

    def test_a_adds_to_audit_trail(self):
        engine = _engine()
        engine.check(_req("baseline_compare"))
        assert len(engine.audit_trail) == 1
        assert engine.audit_trail[0]["action_name"] == "baseline_compare"

    def test_a_all_registered_actions(self):
        engine = _engine()
        a_actions = [k for k, v in _ACTION_GATE_MAP.items() if v == RiskLevel.A]
        for action in a_actions:
            outcome = engine.check(_req(action))
            assert outcome.can_proceed, f"A 类动作 '{action}' 应能放行"


# ─────────────────────────────────────────────────────────────────────────────
# Level-B 门控
# ─────────────────────────────────────────────────────────────────────────────


class TestLevelB:
    def test_b_passes_auto(self):
        engine = _engine()
        outcome = engine.check(_req("search_web", "搜索亚洲酒店案例"))
        assert outcome.can_proceed is True
        assert outcome.blocked is False

    def test_b_records_audit_record(self):
        engine = _engine()
        outcome = engine.check(_req("fetch_external_case", "抓取 archdaily 案例"))
        # B 类应当在 outcome 上留下 audit_record
        assert outcome.audit_record.get("type") == "B"
        assert outcome.audit_record.get("action") == "fetch_external_case"

    def test_b_audit_trail_grows(self):
        engine = _engine()
        engine.check(_req("search_web"))
        engine.check(_req("crawl_reference"))
        assert len(engine.audit_trail) == 2

    def test_b_unknown_action_treated_as_b(self):
        engine = _engine()
        outcome = engine.check(_req("some_novel_external_action"))
        assert outcome.level == RiskLevel.B
        assert outcome.can_proceed is True


# ─────────────────────────────────────────────────────────────────────────────
# Level-C 门控（Budget Guard）
# ─────────────────────────────────────────────────────────────────────────────


class TestLevelC:
    def test_c_passes_when_under_budget(self):
        engine = _engine()
        outcome = engine.check(_req("generate_image"),
                               call_counts={"generate_image": 3})
        assert outcome.can_proceed is True
        assert outcome.blocked is False

    def test_c_blocked_when_at_default_limit(self):
        engine = _engine()
        outcome = engine.check(
            _req("generate_image"),
            call_counts={"generate_image": _DEFAULT_C_BUDGET},
        )
        assert outcome.blocked is True
        assert outcome.can_proceed is False
        assert "配额" in outcome.block_reason

    def test_c_blocked_when_over_limit(self):
        engine = _engine()
        outcome = engine.check(
            _req("generate_image"),
            call_counts={"generate_image": _DEFAULT_C_BUDGET + 5},
        )
        assert outcome.blocked is True

    def test_c_custom_budget_override(self):
        engine = _engine(budget_override={"generate_image": 3})
        # 已用 2 次，未超
        outcome = engine.check(_req("generate_image"),
                               call_counts={"generate_image": 2})
        assert outcome.can_proceed is True
        # 已用 3 次，恰好超
        outcome = engine.check(_req("generate_image"),
                               call_counts={"generate_image": 3})
        assert outcome.blocked is True

    def test_c_zero_count_passes(self):
        engine = _engine()
        outcome = engine.check(_req("generate_render"), call_counts={})
        assert outcome.can_proceed is True

    def test_c_different_actions_independent_budgets(self):
        engine = _engine(budget_override={"generate_image": 1, "generate_render": 5})
        # generate_image 已用完
        outcome_img = engine.check(_req("generate_image"),
                                   call_counts={"generate_image": 1})
        # generate_render 未用完
        outcome_rdr = engine.check(_req("generate_render"),
                                   call_counts={"generate_render": 4})
        assert outcome_img.blocked is True
        assert outcome_rdr.can_proceed is True

    def test_c_block_reason_contains_limit(self):
        engine = _engine(budget_override={"generate_image": 5})
        outcome = engine.check(_req("generate_image"),
                               call_counts={"generate_image": 5})
        assert "5" in outcome.block_reason


# ─────────────────────────────────────────────────────────────────────────────
# Level-D 门控（阻断级，强制人工确认）
# ─────────────────────────────────────────────────────────────────────────────


class TestLevelD:
    def test_d_needs_confirm(self):
        engine = _engine()
        outcome = engine.check(_req("modify_frozen_zone"))
        assert outcome.needs_confirm is True
        assert outcome.can_proceed is False

    def test_d_not_blocked_just_needs_confirm(self):
        engine = _engine()
        outcome = engine.check(_req("send_external_api"))
        # D 类不是"blocked"，而是"needs_confirm"（由调用方触发 Interrupt）
        assert outcome.blocked is False
        assert outcome.needs_confirm is True

    def test_d_audit_trail_recorded(self):
        engine = _engine()
        engine.check(_req("auto_submit_order"))
        assert len(engine.audit_trail) >= 1
        entry = engine.audit_trail[-1]
        assert entry["level"] == "D"

    def test_d_all_registered_actions(self):
        engine = _engine()
        d_actions = [k for k, v in _ACTION_GATE_MAP.items() if v == RiskLevel.D]
        for action in d_actions:
            outcome = engine.check(_req(action))
            assert outcome.needs_confirm, f"D 类动作 '{action}' 应需要人工确认"


# ─────────────────────────────────────────────────────────────────────────────
# audit_trail 全局行为
# ─────────────────────────────────────────────────────────────────────────────


class TestAuditTrail:
    def test_trail_starts_empty(self):
        engine = _engine()
        assert engine.audit_trail == []

    def test_trail_grows_per_check(self):
        engine = _engine()
        for action in ("query_knowledge_base", "search_web", "generate_image",
                       "modify_frozen_zone"):
            engine.check(_req(action), call_counts={})
        assert len(engine.audit_trail) == 4

    def test_trail_is_copy_not_reference(self):
        engine = _engine()
        engine.check(_req("search_web"))
        trail = engine.audit_trail
        trail.append({"injected": True})
        # 原始 trail 不应被修改
        assert "injected" not in str(engine.audit_trail)

    def test_trail_entry_has_required_keys(self):
        engine = _engine()
        engine.check(_req("search_web"))
        entry = engine.audit_trail[0]
        for key in ("action_name", "level", "allowed", "recorded_at"):
            assert key in entry


# ─────────────────────────────────────────────────────────────────────────────
# create_gate_engine_from_blueprint 工厂
# ─────────────────────────────────────────────────────────────────────────────


class TestCreateGateEngineFactory:
    def test_basic_construction(self):
        blueprint_raw = {
            "budget_guard": {"generate_image": 5, "generate_render": 3}
        }
        engine = create_gate_engine_from_blueprint(blueprint_raw, session_id="sess-001")
        assert isinstance(engine, RiskGateEngine)

    def test_budget_propagated(self):
        blueprint_raw = {"budget_guard": {"generate_image": 2}}
        engine = create_gate_engine_from_blueprint(blueprint_raw, session_id="sess-002")
        # 已用 2 次 → 应被阻断
        outcome = engine.check(_req("generate_image"),
                               call_counts={"generate_image": 2})
        assert outcome.blocked is True

    def test_empty_blueprint(self):
        engine = create_gate_engine_from_blueprint({}, session_id="sess-003")
        assert isinstance(engine, RiskGateEngine)
        # 使用默认配额
        outcome = engine.check(_req("generate_image"),
                               call_counts={"generate_image": 0})
        assert outcome.can_proceed is True

    def test_none_budget_guard(self):
        engine = create_gate_engine_from_blueprint(
            {"budget_guard": None}, session_id="sess-004"
        )
        assert isinstance(engine, RiskGateEngine)

    def test_session_id_stored(self):
        engine = create_gate_engine_from_blueprint({}, session_id="sess-xyz")
        assert engine._session_id == "sess-xyz"
