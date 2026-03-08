# -*- coding: utf-8 -*-
"""
Fast Path 最小保障守卫单元测试

覆盖：
1) _can_apply_requirements_fast_path 通过分支
2) _can_apply_requirements_fast_path 失败分支（缺失字段）
3) _unified_input_validator_secondary_node 在 fast-path 启用且守卫通过时直达 project_director
4) _unified_input_validator_secondary_node 在 fast-path 启用但守卫失败时回退默认链路
"""

from unittest.mock import Mock

import pytest
from langgraph.types import Command

import intelligent_project_analyzer.workflow.nodes.security_nodes as security_nodes_module
from intelligent_project_analyzer.workflow.nodes.security_nodes import SecurityNodesMixin


class _DummySecurityNode(SecurityNodesMixin):
    """最小可测替身：仅提供 mixin 方法需要的属性。"""

    def __init__(self):
        self.store = None
        self.llm_model = Mock()


@pytest.mark.unit
class TestRequirementsFastPathGuard:
    def _make_valid_state(self):
        return {
            "requirements_quality_gate": {"severity": "pass"},
            "project_type": "personal_residential",
            "space_classification": {"primary_type": "personal_residential"},
            "task_framework": {"task_tree": []},
            "structured_requirements": {
                "project_motivation_detail": "项目以文化叙事重构为核心，强调在地材料与当代生活方式的平衡。",
                "design_motivation_detail": "需要挑战型设计策略以突破模板化民宿表达并建立独特辨识度。",
                "stance_spectrum": {
                    "rationale": "通过张力转化而非简单消解，建立新旧并置下的第三空间语义。"
                },
                "expert_handoff_questions": {
                    "universal_disruption_challenge": "若预算砍掉50%，必须优先保留哪一类空间价值才能维持项目核心主张？"
                },
                "disruption_authorization": {
                    "disruption_rationale": "在文化驱动场景中，适度颠覆既有模板是形成真实在地性的必要条件。"
                },
            },
        }

    def test_guard_passes_with_minimum_required_fields(self):
        node = _DummySecurityNode()
        ok, reasons = node._can_apply_requirements_fast_path(self._make_valid_state())

        assert ok is True
        assert reasons == []

    def test_guard_fails_and_returns_reasons_when_fields_missing(self):
        node = _DummySecurityNode()
        bad_state = {
            "requirements_quality_gate": {"severity": "warn"},
            "structured_requirements": {},
        }

        ok, reasons = node._can_apply_requirements_fast_path(bad_state)

        assert ok is False
        assert "quality_gate_not_pass:warn" in reasons
        assert "project_type_missing" in reasons
        assert "space_classification_missing" in reasons
        assert "task_framework_missing" in reasons
        assert "M18_missing_project_motivation_detail" in reasons
        assert "M19_missing_design_motivation_detail" in reasons
        assert "M22_missing_stance_rationale" in reasons
        assert "M23_missing_universal_disruption_challenge" in reasons
        assert "M24_missing_disruption_rationale" in reasons


@pytest.mark.unit
class TestSecondaryValidationFastPathRouting:
    def _patch_secondary_validation_to_return_dict(self, monkeypatch, payload=None):
        if payload is None:
            payload = {"secondary_validation": "ok"}

        monkeypatch.setattr(
            security_nodes_module.UnifiedInputValidatorNode,
            "execute_secondary_validation",
            staticmethod(lambda state, store=None, llm_model=None: dict(payload)),
        )

    def test_secondary_validation_short_circuits_to_project_director_when_guard_passes(self, monkeypatch):
        node = _DummySecurityNode()
        state = {
            "requirements_quality_gate": {"severity": "pass"},
            "project_type": "personal_residential",
            "space_classification": {"primary_type": "personal_residential"},
            "task_framework": {"task_tree": []},
            "structured_requirements": {
                "project_motivation_detail": "项目由文化复兴动机驱动，强调在地表达。",
                "design_motivation_detail": "设计需挑战常规模板并建立独特识别性。",
                "stance_spectrum": {"rationale": "通过转化张力建立第三空间语义。"},
                "expert_handoff_questions": {"universal_disruption_challenge": "若预算减半，必须保留什么？"},
                "disruption_authorization": {"disruption_rationale": "适度颠覆是达成项目主张的必要条件。"},
            },
        }

        self._patch_secondary_validation_to_return_dict(monkeypatch)
        monkeypatch.setattr(security_nodes_module, "ENABLE_REQUIREMENTS_FAST_PATH", True)

        result = node._unified_input_validator_secondary_node(state)

        assert isinstance(result, Command)
        assert result.goto == "project_director"
        assert result.update["requirements_fast_path"] is True
        assert result.update["questionnaire_summary_skipped"] is True
        assert result.update["progressive_step3_skipped"] is True
        assert result.update["progressive_step2_skipped"] is True
        assert result.update["requirements_fast_path_guard"]["passed"] is True

    def test_secondary_validation_falls_back_when_guard_fails(self, monkeypatch):
        node = _DummySecurityNode()
        state = {
            "requirements_quality_gate": {"severity": "warn"},
            "structured_requirements": {},
        }

        self._patch_secondary_validation_to_return_dict(monkeypatch)
        monkeypatch.setattr(security_nodes_module, "ENABLE_REQUIREMENTS_FAST_PATH", True)

        result = node._unified_input_validator_secondary_node(state)

        assert isinstance(result, dict)
        assert result["requirements_fast_path"] is False
        assert result["requirements_fast_path_guard"]["passed"] is False
        assert "quality_gate_not_pass:warn" in result["requirements_fast_path_guard"]["reasons"]
        assert result["detail"] == "二次验证领域适配性"

    def test_secondary_validation_uses_default_chain_when_flag_disabled(self, monkeypatch):
        node = _DummySecurityNode()
        state = {
            "requirements_quality_gate": {"severity": "pass"},
            "project_type": "personal_residential",
            "space_classification": {"primary_type": "personal_residential"},
            "task_framework": {"task_tree": []},
            "structured_requirements": {
                "project_motivation_detail": "项目由文化复兴动机驱动，强调在地表达。",
                "design_motivation_detail": "设计需挑战常规模板并建立独特识别性。",
                "stance_spectrum": {"rationale": "通过转化张力建立第三空间语义。"},
                "expert_handoff_questions": {"universal_disruption_challenge": "若预算减半，必须保留什么？"},
                "disruption_authorization": {"disruption_rationale": "适度颠覆是达成项目主张的必要条件。"},
            },
        }

        self._patch_secondary_validation_to_return_dict(monkeypatch, payload={"secondary_validation": "ok"})
        monkeypatch.setattr(security_nodes_module, "ENABLE_REQUIREMENTS_FAST_PATH", False)

        result = node._unified_input_validator_secondary_node(state)

        assert isinstance(result, dict)
        assert result.get("requirements_fast_path") is None
        assert result["detail"] == "二次验证领域适配性"

    def test_secondary_validation_command_passthrough_has_higher_priority_than_fast_path(self, monkeypatch):
        node = _DummySecurityNode()
        state = {
            "requirements_quality_gate": {"severity": "pass"},
            "project_type": "personal_residential",
            "space_classification": {"primary_type": "personal_residential"},
            "task_framework": {"task_tree": []},
            "structured_requirements": {
                "project_motivation_detail": "项目由文化复兴动机驱动，强调在地表达。",
                "design_motivation_detail": "设计需挑战常规模板并建立独特识别性。",
                "stance_spectrum": {"rationale": "通过转化张力建立第三空间语义。"},
                "expert_handoff_questions": {"universal_disruption_challenge": "若预算减半，必须保留什么？"},
                "disruption_authorization": {"disruption_rationale": "适度颠覆是达成项目主张的必要条件。"},
            },
        }

        expected_cmd = Command(update={"reason": "need_reanalysis"}, goto="requirements_analyst")
        monkeypatch.setattr(
            security_nodes_module.UnifiedInputValidatorNode,
            "execute_secondary_validation",
            staticmethod(lambda state, store=None, llm_model=None: expected_cmd),
        )
        monkeypatch.setattr(security_nodes_module, "ENABLE_REQUIREMENTS_FAST_PATH", True)

        result = node._unified_input_validator_secondary_node(state)

        assert isinstance(result, Command)
        assert result is expected_cmd
        assert result.goto == "requirements_analyst"
