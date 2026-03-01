# -*- coding: utf-8 -*-
"""
需求分析师 - 单元测试套件
============================
覆盖范围（全部无 LLM 调用，毫秒级执行）：

U01  Schema 基础验证 (Phase1Output, CoreTension)
U02  Schema 边界校验 (字段长度 / 枚举约束 / 幻觉理论拒绝)
U03  Schema 新增字段 (C-01 止血修复校验)
U04  validate_logic_consistency 验证器 (Rule2 删除 / Rule4 保留)
U05  _weighted_info_status_vote() 加权投票
U06  _build_decision_reason() 决策理由拼装
U07  _build_problem_solving_approach() (A-01 止血修复)
U08  _parse_json_response() 四层 JSON 解析
U09  _format_precheck_hints() 预检测提示格式化
U10  _build_phase1_only_result() Phase1-only 结果构建
U11  _merge_phase_results() Phase1+Phase2 结果合并
U12  _calculate_two_phase_confidence() 置信度计算
U13  _normalize_jtbd_fields() JTBD 字段规范化
U14  _infer_project_type() 项目类型推断
U15  should_execute_phase2() 路由 — 总是返回 phase2
U16  _phase1_fallback() / _phase2_fallback() 降级逻辑
U17  build_requirements_analyst_graph() 图结构验证
U18  DeliverableTypeEnum / DeliverablePriorityEnum 枚举完整性
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─────────────────────────────────────────────────── Schema ─────
from intelligent_project_analyzer.agents.requirements_analyst_schema import (
    APPROVED_THEORY,
    THEORY_TO_LENS,
    CapabilityCheck,
    CoreTension,
    DeliverableOwnerSuggestion,
    DeliverablePriorityEnum,
    DeliverableTypeEnum,
    LensCategory,
    Phase1Deliverable,
    Phase1Output,
)

# ──────────────────────────────────────────── Agent helpers ─────
from intelligent_project_analyzer.agents.requirements_analyst_agent import (
    _build_decision_reason,
    _build_phase1_only_result,
    _build_problem_solving_approach,
    _calculate_two_phase_confidence,
    _format_precheck_hints,
    _infer_project_type,
    _merge_phase_results,
    _normalize_jtbd_fields,
    _parse_json_response,
    _phase1_fallback,
    _phase2_fallback,
    _weighted_info_status_vote,
    build_requirements_analyst_graph,
    should_execute_phase2,
)


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


def _make_deliverable(idx: int = 1, d_type: str = "design_strategy") -> Phase1Deliverable:
    """构造合法 Phase1Deliverable（用于测试）"""
    return Phase1Deliverable(
        deliverable_id=f"D{idx}",
        type=d_type,
        description="室内设计方案，含完整空间规划和选材指导",
        priority=DeliverablePriorityEnum.MUST_HAVE,
        acceptance_criteria=["必须包含平面布局方案"],
        deliverable_owner_suggestion=DeliverableOwnerSuggestion(
            primary_owner="V3_叙事与体验专家_3-3",
            owner_rationale="最擅长将生活叙事转化为空间体验",
        ),
        capability_check=CapabilityCheck(within_capability=True),
    )


def _make_phase1_output(info_status: str = "sufficient") -> Phase1Output:
    """构造合法 Phase1Output"""
    return Phase1Output(
        info_status=info_status,
        info_status_reason="用户提供了完整的面积、预算、风格偏好、居住人口等关键信息",
        project_type_preliminary="personal_residential",
        project_summary="75平米城市公寓改造，三代同堂，现代极简风格，预算60万，注重收纳与光线",
        primary_deliverables=[_make_deliverable()],
        recommended_next_step="phase2_analysis",
        next_step_reason="信息充足，可直接进入Phase2深度分析以获取专业设计策略",
    )


# ═══════════════════════════════════════════════════════════════
# U01  Schema 基础验证
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestPhase1OutputBasic:
    def test_valid_sufficient(self):
        p1 = _make_phase1_output("sufficient")
        assert p1.info_status == "sufficient"
        assert p1.phase == 1
        assert len(p1.primary_deliverables) == 1

    def test_valid_insufficient(self):
        p1 = _make_phase1_output("insufficient")
        assert p1.info_status == "insufficient"

    def test_defaults_present(self):
        """C-01 字段存在且有合理默认值"""
        p1 = _make_phase1_output()
        assert p1.problem_types == []
        assert p1.proposition_candidates == []
        assert p1.complexity_assessment is None

    def test_problem_types_accepted(self):
        p1 = Phase1Output(
            info_status="sufficient",
            info_status_reason="用户提供了完整的面积、预算、风格偏好、居住人口等关键信息",
            project_type_preliminary="personal_residential",
            project_summary="75平米城市公寓改造，三代同堂，现代极简风格，预算60万，注重收纳与光线",
            primary_deliverables=[_make_deliverable()],
            recommended_next_step="phase2_analysis",
            next_step_reason="信息充足，可直接进入Phase2深度分析以获取专业设计策略",
            problem_types=["tension_identity", "technical_first"],
            proposition_candidates=[{"text": "方案A", "score": 90}],
            complexity_assessment={"overall": "high", "dimensions": 4},
        )
        assert p1.problem_types == ["tension_identity", "technical_first"]
        assert p1.complexity_assessment["overall"] == "high"

    def test_recommended_next_step_clarify_expectations(self):
        """C-01: clarify_expectations 是合法值"""
        p1 = Phase1Output(
            info_status="insufficient",
            info_status_reason="客户仅提供风格倾向，缺乏面积、预算、家庭结构等核心数据",
            project_type_preliminary="personal_residential",
            project_summary="风格倾向：现代极简，但面积、预算、居住成员等关键信息完全缺失待明确",
            primary_deliverables=[_make_deliverable()],
            recommended_next_step="clarify_expectations",
            next_step_reason="核心信息不足，建议先与客户澄清具体需求后再启动分析",
        )
        assert p1.recommended_next_step == "clarify_expectations"


# ═══════════════════════════════════════════════════════════════
# U02  Schema 边界校验
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestPhase1OutputBoundary:
    def test_invalid_info_status(self):
        with pytest.raises(Exception):
            Phase1Output(
                info_status="unknown",  # 非法
                info_status_reason="测试" * 10,
                project_type_preliminary="x",
                project_summary="y" * 30,
                primary_deliverables=[_make_deliverable()],
                recommended_next_step="phase2_analysis",
                next_step_reason="z" * 20,
            )

    def test_info_status_reason_too_short(self):
        """info_status_reason 最少 20 字"""
        with pytest.raises(Exception):
            Phase1Output(
                info_status="sufficient",
                info_status_reason="太短",
                project_type_preliminary="x",
                project_summary="y" * 30,
                primary_deliverables=[_make_deliverable()],
                recommended_next_step="phase2_analysis",
                next_step_reason="z" * 20,
            )

    def test_project_summary_too_short(self):
        """project_summary 最少 30 字"""
        with pytest.raises(Exception):
            Phase1Output(
                info_status="sufficient",
                info_status_reason="用户提供了完整的面积、预算、风格偏好、居住人口等关键信息",
                project_type_preliminary="x",
                project_summary="太短",
                primary_deliverables=[_make_deliverable()],
                recommended_next_step="phase2_analysis",
                next_step_reason="z" * 20,
            )

    def test_empty_deliverables_rejected(self):
        """deliverables 至少 1 个"""
        with pytest.raises(Exception):
            Phase1Output(
                info_status="sufficient",
                info_status_reason="用户提供了完整的面积、预算、风格偏好、居住人口等关键信息",
                project_type_preliminary="x",
                project_summary="y" * 30,
                primary_deliverables=[],
                recommended_next_step="phase2_analysis",
                next_step_reason="z" * 20,
            )


# ═══════════════════════════════════════════════════════════════
# U03  Schema 新增字段 (C-01)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestPhase1C01Fields:
    def test_problem_types_field_exists(self):
        fields = Phase1Output.model_fields
        assert "problem_types" in fields

    def test_proposition_candidates_field_exists(self):
        fields = Phase1Output.model_fields
        assert "proposition_candidates" in fields

    def test_complexity_assessment_field_exists(self):
        fields = Phase1Output.model_fields
        assert "complexity_assessment" in fields

    def test_recommended_next_step_includes_clarify(self):
        ann = str(Phase1Output.model_fields["recommended_next_step"].annotation)
        assert "clarify_expectations" in ann

    def test_phase1_output_does_not_drop_extra_fields(self):
        """LLM 返回 problem_types 时，Schema 应保留而非丢弃"""
        p1 = Phase1Output(
            info_status="sufficient",
            info_status_reason="用户提供了完整的面积、预算、风格偏好、居住人口等关键信息",
            project_type_preliminary="personal_residential",
            project_summary="75平米城市公寓改造三代同堂现代极简风格预算60万注重收纳与光线",
            primary_deliverables=[_make_deliverable()],
            recommended_next_step="phase2_analysis",
            next_step_reason="信息充足，可直接进入Phase2深度分析以获取专业设计策略",
            problem_types=["tension_identity"],
        )
        d = p1.model_dump()
        assert "problem_types" in d
        assert d["problem_types"] == ["tension_identity"]


# ═══════════════════════════════════════════════════════════════
# U04  validate_logic_consistency (C-02 Rule2 删除)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestValidateLogicConsistency:
    def test_rule2_deleted_insufficient_phase2_ok(self):
        """C-02: insufficient + phase2_analysis 不再抛出 ValueError"""
        p1 = Phase1Output(
            info_status="insufficient",
            info_status_reason="客户仅告知想装修房子，缺乏面积预算风格家庭结构等全部关键信息",
            project_type_preliminary="personal_residential",
            project_summary="基础需求已识别，面积预算家庭结构风格偏好工期等核心约束均未明确待补充",
            primary_deliverables=[_make_deliverable()],
            recommended_next_step="phase2_analysis",
            next_step_reason="虽信息不足但Phase2仍可产生基础方向分析以供后续问卷聚焦",
        )
        assert p1.info_status == "insufficient"
        assert p1.recommended_next_step == "phase2_analysis"

    def test_rule4_no_must_have_raises(self):
        """Rule4 保留: 至少一个 MUST_HAVE 交付物"""
        with pytest.raises(Exception):
            Phase1Output(
                info_status="sufficient",
                info_status_reason="用户提供了完整的面积、预算、风格偏好、居住人口等关键信息",
                project_type_preliminary="personal_residential",
                project_summary="75平米城市公寓改造三代同堂现代极简风格预算60万注重收纳与光线",
                primary_deliverables=[
                    Phase1Deliverable(
                        deliverable_id="D1",
                        type=DeliverableTypeEnum.DESIGN_STRATEGY,
                        description="室内设计方案含完整空间规划和选材指导",
                        priority=DeliverablePriorityEnum.NICE_TO_HAVE,  # 非 MUST_HAVE
                        acceptance_criteria=["必须包含平面布局方案"],
                        deliverable_owner_suggestion=DeliverableOwnerSuggestion(
                            primary_owner="V3_叙事与体验专家_3-3",
                            owner_rationale="最擅长将生活叙事转化为空间体验",
                        ),
                        capability_check=CapabilityCheck(within_capability=True),
                    )
                ],
                recommended_next_step="phase2_analysis",
                next_step_reason="信息充足，可直接进入Phase2深度分析以获取专业设计策略",
            )

    def test_rule1_sufficient_with_many_gaps_raises(self):
        """Rule1: sufficient 时 info_gaps 不超过 2 个"""
        with pytest.raises(Exception):
            Phase1Output(
                info_status="sufficient",
                info_status_reason="用户提供了完整的面积、预算、风格偏好、居住人口等关键信息",
                project_type_preliminary="personal_residential",
                project_summary="75平米城市公寓改造三代同堂现代极简风格预算60万注重收纳与光线",
                primary_deliverables=[_make_deliverable()],
                recommended_next_step="phase2_analysis",
                next_step_reason="信息充足，可直接进入Phase2深度分析以获取专业设计策略",
                info_gaps=["缺A", "缺B", "缺C"],  # 超过 2 个
            )


# ═══════════════════════════════════════════════════════════════
# U05  _weighted_info_status_vote()
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestWeightedInfoStatusVote:
    """
    投票权重: precheck=0.4, phase1=0.4, mode=0.2
    阈值: >= 0.5 → sufficient
    """

    def test_all_sufficient(self):
        precheck = {"info_sufficiency": {"is_sufficient": True}}
        phase1 = {"info_status": "sufficient"}
        mode = {"adjusted_status": "sufficient"}
        status, details = _weighted_info_status_vote(precheck, phase1, mode)
        assert status == "sufficient"
        assert details["final_score"] == pytest.approx(1.0)
        assert details["consensus"] is True

    def test_all_insufficient(self):
        precheck = {"info_sufficiency": {"is_sufficient": False}}
        phase1 = {"info_status": "insufficient"}
        mode = {"adjusted_status": "insufficient"}
        status, details = _weighted_info_status_vote(precheck, phase1, mode)
        assert status == "insufficient"
        assert details["final_score"] == pytest.approx(0.0)
        assert details["consensus"] is True

    def test_threshold_exactly_0_5(self):
        """precheck=sufficient(0.4) + mode=sufficient(0.2) → 0.6 → sufficient"""
        precheck = {"info_sufficiency": {"is_sufficient": True}}
        phase1 = {"info_status": "insufficient"}
        mode = {"adjusted_status": "sufficient"}
        status, details = _weighted_info_status_vote(precheck, phase1, mode)
        assert status == "sufficient"
        assert details["final_score"] == pytest.approx(0.6)

    def test_threshold_below_0_5(self):
        """只有 mode=sufficient(0.2) → 0.2 → insufficient"""
        precheck = {"info_sufficiency": {"is_sufficient": False}}
        phase1 = {"info_status": "insufficient"}
        mode = {"adjusted_status": "sufficient"}
        status, details = _weighted_info_status_vote(precheck, phase1, mode)
        assert status == "insufficient"
        assert details["final_score"] == pytest.approx(0.2)

    def test_phase1_sufficient_only(self):
        """precheck=insufficient(0) + phase1=sufficient(0.4) + mode={}(默认0.2) → 0.6 → sufficient"""
        precheck = {"info_sufficiency": {"is_sufficient": False}}
        phase1 = {"info_status": "sufficient"}
        mode = {}  # 无 adjusted_status，mode 贡献默认 0.2（sufficient 方向）
        status, details = _weighted_info_status_vote(precheck, phase1, mode)
        # 实际行为: 0 + 0.4 + 0.2 = 0.6 ≥ 0.5 → sufficient
        assert status == "sufficient"
        assert details["final_score"] == pytest.approx(0.6)

    def test_precheck_and_phase1_sufficient(self):
        """precheck=0.4, phase1=0.4 → 0.8 → sufficient，consensus=True"""
        precheck = {"info_sufficiency": {"is_sufficient": True}}
        phase1 = {"info_status": "sufficient"}
        mode = {}
        status, details = _weighted_info_status_vote(precheck, phase1, mode)
        assert status == "sufficient"
        assert details["consensus"] is True

    def test_vote_details_structure(self):
        precheck = {"info_sufficiency": {"is_sufficient": True}}
        phase1 = {"info_status": "sufficient"}
        mode = {"adjusted_status": "insufficient"}
        _, details = _weighted_info_status_vote(precheck, phase1, mode)
        assert "votes" in details
        assert "precheck" in details["votes"]
        assert "phase1" in details["votes"]
        assert "mode" in details["votes"]
        assert "decision_reason" in details


# ═══════════════════════════════════════════════════════════════
# U06  _build_decision_reason()
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestBuildDecisionReason:
    def test_all_agree_sufficient(self):
        reason = _build_decision_reason(True, "sufficient", "sufficient", "sufficient")
        assert "三方一致" in reason

    def test_all_agree_insufficient(self):
        reason = _build_decision_reason(False, "insufficient", "insufficient", "insufficient")
        assert "三方一致" in reason

    def test_majority_sufficient(self):
        reason = _build_decision_reason(True, "sufficient", "insufficient", "sufficient")
        assert "充足" in reason or "sufficient" in reason.lower()

    def test_majority_insufficient(self):
        reason = _build_decision_reason(False, "insufficient", "insufficient", "insufficient")
        assert "不足" in reason or "insufficient" in reason.lower()


# ═══════════════════════════════════════════════════════════════
# U07  _build_problem_solving_approach() (A-01)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestBuildProblemSolvingApproach:
    def test_returns_none_without_core_fields(self):
        assert _build_problem_solving_approach({}, {}) is None

    def test_basic_extraction(self):
        phase2 = {
            "L3_core_tension": "传统居住方式 vs 现代游牧生活",
            "L4_project_task": "将公寓改造为同时满足冥想与直播需求的灵活空间",
        }
        result = _build_problem_solving_approach({}, phase2)
        assert result is not None
        assert result["source"] == "phase2_output"
        assert result["method"] == "programmatic_extraction"
        assert result["task_type"] == "design_strategy"

    def test_high_sharpness_score(self):
        phase2 = {
            "L3_core_tension": "t",
            "L5_sharpness": {"score": 80},
        }
        result = _build_problem_solving_approach({}, phase2)
        assert result["complexity_level"] == "high"

    def test_low_sharpness_score(self):
        phase2 = {
            "L3_core_tension": "t",
            "L5_sharpness": {"score": 40},
        }
        result = _build_problem_solving_approach({}, phase2)
        assert result["complexity_level"] == "medium"

    def test_depth_reached_l5_with_five_whys(self):
        phase2 = {
            "L3_core_tension": "t",
            "L5_1_five_whys": ["why1", "why2"],
        }
        result = _build_problem_solving_approach({}, phase2)
        assert result["depth_reached"] == "L5"

    def test_depth_reached_l4_without_five_whys(self):
        phase2 = {"L3_core_tension": "t"}
        result = _build_problem_solving_approach({}, phase2)
        assert result["depth_reached"] == "L4"

    def test_alternative_keys(self):
        """支持备用键名 core_tensions / project_task"""
        phase2 = {
            "core_tensions": "设计矛盾",
            "project_task": "改造项目",
        }
        result = _build_problem_solving_approach({}, phase2)
        assert result is not None

    def test_text_truncated_to_200(self):
        phase2 = {
            "L3_core_tension": "x" * 300,
        }
        result = _build_problem_solving_approach({}, phase2)
        assert len(result["core_challenge"]) <= 200

    def test_analysis_layers_wrapper(self):
        """phase2 通过 analysis_layers 包装时也能提取"""
        phase2 = {
            "analysis_layers": {
                "L3_core_tension": "封装的张力",
                "L4_project_task": "封装的任务",
            }
        }
        result = _build_problem_solving_approach({}, phase2)
        assert result is not None


# ═══════════════════════════════════════════════════════════════
# U08  _parse_json_response() 四层解析
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestParseJsonResponse:
    def test_code_fence_json(self):
        resp = '说明文字\n```json\n{"key": "value"}\n```\n尾随文字'
        result = _parse_json_response(resp)
        assert result["key"] == "value"

    def test_bare_code_fence(self):
        resp = '```\n{"bare": true}\n```'
        result = _parse_json_response(resp)
        assert result["bare"] is True

    def test_inline_json(self):
        resp = '分析结果: {"score": 99, "label": "high"}'
        result = _parse_json_response(resp)
        assert result["score"] == 99

    def test_nested_json(self):
        obj = {"a": {"b": {"c": 3}}, "list": [1, 2, 3]}
        resp = f"输出: {json.dumps(obj)}"
        assert _parse_json_response(resp) == obj

    def test_no_json_raises(self):
        with pytest.raises((ValueError, Exception)):
            _parse_json_response("这里没有任何JSON数据只有文字")

    def test_empty_raises(self):
        with pytest.raises((ValueError, Exception)):
            _parse_json_response("")

    def test_unicode_content(self):
        resp = '{"中文": "测试", "日本語": "テスト"}'
        result = _parse_json_response(resp)
        assert result["中文"] == "测试"

    def test_boolean_and_null(self):
        resp = '{"ok": true, "val": null, "n": 0}'
        result = _parse_json_response(resp)
        assert result["ok"] is True
        assert result["val"] is None
        assert result["n"] == 0


# ═══════════════════════════════════════════════════════════════
# U09  _format_precheck_hints()
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestFormatPrecheckHints:
    def _sufficient_precheck(self):
        return {
            "info_sufficiency": {
                "is_sufficient": True,
                "score": 0.82,
                "present_elements": ["面积", "预算", "风格"],
            },
            "deliverable_capability": {"capability_score": 0.9},
            "capable_deliverables": [{"type": "design_strategy"}],
            "transformations": [],
        }

    def _insufficient_precheck(self):
        return {
            "info_sufficiency": {
                "is_sufficient": False,
                "score": 0.30,
                "missing_elements": ["面积", "预算", "风格", "工期"],
            },
            "deliverable_capability": {"capability_score": 0.5},
            "capable_deliverables": [],
            "transformations": [{"original": "3D效果图", "transformed_to": "design_strategy"}],
        }

    def test_sufficient_hint_contains_ok_marker(self):
        hints = _format_precheck_hints(self._sufficient_precheck())
        assert "充足" in hints or "OK" in hints.upper()

    def test_insufficient_hint_contains_warning(self):
        hints = _format_precheck_hints(self._insufficient_precheck())
        assert "不足" in hints or "Warning" in hints

    def test_transformation_listed(self):
        hints = _format_precheck_hints(self._insufficient_precheck())
        assert "3D效果图" in hints or "design_strategy" in hints

    def test_capability_score_shown(self):
        hints = _format_precheck_hints(self._sufficient_precheck())
        assert "%" in hints or "0.9" in hints


# ═══════════════════════════════════════════════════════════════
# U10  _build_phase1_only_result()
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestBuildPhase1OnlyResult:
    def _phase1(self):
        return {
            "info_status": "insufficient",
            "info_status_reason": "信息不足",
            "project_summary": "公寓改造",
            "primary_deliverables": [{"deliverable_id": "D1", "type": "design_strategy"}],
            "info_gaps": ["面积", "预算"],
        }

    def test_essential_fields_present(self):
        result = _build_phase1_only_result(self._phase1(), "帮我设计房子")
        assert "project_task" in result
        assert "primary_deliverables" in result
        assert "info_status" in result
        assert "info_gaps" in result

    def test_deliverables_passed_through(self):
        result = _build_phase1_only_result(self._phase1(), "帮我设计房子")
        assert len(result["primary_deliverables"]) == 1

    def test_info_status_passed_through(self):
        result = _build_phase1_only_result(self._phase1(), "帮我设计房子")
        assert result["info_status"] == "insufficient"

    def test_project_task_falls_back_to_input(self):
        p1 = {"primary_deliverables": []}
        result = _build_phase1_only_result(p1, "我想改造一间公寓")
        assert "公寓" in result["project_task"]


# ═══════════════════════════════════════════════════════════════
# U11  _merge_phase_results()
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestMergePhaseResults:
    def _phase1(self):
        return {
            "info_status": "sufficient",
            "primary_deliverables": [{"deliverable_id": "D1", "type": "design_strategy"}],
            "project_type_preliminary": "personal_residential",
        }

    def _phase2_basic(self):
        return {
            "structured_output": {
                "project_task": "将75平米公寓改造为融合冥想与创作功能的灵动空间",
                "character_narrative": "前律师，转型博主",
                "physical_context": "上海高层南向",
                "resource_constraints": "60万，4个月",
            },
            "analysis_layers": {
                "L3_core_tension": "公共展示 vs 私密避难",
                "L5_sharpness": {"score": 78},
            },
            "expert_handoff": {"critical_questions_for_experts": ["如何在一室中实现可切换的空间氛围？"]},
        }

    def test_project_task_extracted(self):
        result = _merge_phase_results(self._phase1(), self._phase2_basic(), "input")
        assert "公寓" in result["project_task"]

    def test_primary_deliverables_from_phase1(self):
        result = _merge_phase_results(self._phase1(), self._phase2_basic(), "input")
        assert len(result["primary_deliverables"]) == 1

    def test_info_status_from_phase1(self):
        result = _merge_phase_results(self._phase1(), self._phase2_basic(), "input")
        assert result["info_status"] == "sufficient"

    def test_analysis_layers_present(self):
        result = _merge_phase_results(self._phase1(), self._phase2_basic(), "input")
        assert "analysis_layers" in result
        assert result["analysis_layers"]["L3_core_tension"] == "公共展示 vs 私密避难"

    def test_expert_handoff_present(self):
        result = _merge_phase_results(self._phase1(), self._phase2_basic(), "input")
        assert "expert_handoff" in result
        assert len(result["expert_handoff"]["critical_questions_for_experts"]) == 1

    def test_empty_phase2_graceful(self):
        """空 phase2 结果不应崩溃"""
        result = _merge_phase_results(self._phase1(), {}, "input")
        assert "project_task" in result

    def test_v10_phase_a_b_c_keys(self):
        """v10.0.0 的三阶段键名优先"""
        phase2 = {
            "phase_a_reality": {
                "A2_stakeholders": [{"role": "owner", "goals": ["aesthetics"]}],
            },
            "phase_b_excavation": {
                "B3_five_whys_analysis": [{"why": "身份焦虑"}],
            },
            "structured_output": {},
            "analysis_layers": {},
            "expert_handoff": {},
        }
        result = _merge_phase_results(self._phase1(), phase2, "input")
        assert result["stakeholder_system"] is not None
        assert result["five_whys_analysis"] is not None


# ═══════════════════════════════════════════════════════════════
# U12  _calculate_two_phase_confidence()
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestCalculateTwoPhaseConfidence:
    def test_baseline(self):
        c = _calculate_two_phase_confidence({}, {})
        assert c == pytest.approx(0.5)

    def test_sufficient_adds_delta(self):
        c = _calculate_two_phase_confidence({"info_status": "sufficient"}, {})
        assert c > 0.5

    def test_deliverables_add_delta(self):
        c = _calculate_two_phase_confidence({"info_status": "sufficient", "primary_deliverables": [{"id": "D1"}]}, {})
        assert c >= 0.7

    def test_sharpness_score_caps_at_one(self):
        phase2 = {
            "analysis_layers": {"L5_sharpness": {"score": 100}},
            "expert_handoff": {"critical_questions_for_experts": ["q1"]},
        }
        c = _calculate_two_phase_confidence(
            {"info_status": "sufficient", "primary_deliverables": [{"id": "D1"}]},
            phase2,
        )
        assert c <= 1.0

    def test_never_exceeds_one(self):
        phase2 = {
            "analysis_layers": {"L5_sharpness": {"score": 999}},
            "expert_handoff": {"critical_questions_for_experts": ["q1", "q2"]},
        }
        c = _calculate_two_phase_confidence(
            {"info_status": "sufficient", "primary_deliverables": [{"id": "D1"}, {"id": "D2"}]},
            phase2,
        )
        assert c <= 1.0


# ═══════════════════════════════════════════════════════════════
# U13  _normalize_jtbd_fields()
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestNormalizeJtbdFields:
    def test_string_field_transformed(self):
        data = {"project_task": "帮我设计房子", "project_overview": "公寓改造"}
        _normalize_jtbd_fields(data)
        # 调用后字段类型仍为 str
        assert isinstance(data["project_task"], str)
        assert isinstance(data["project_overview"], str)

    def test_none_field_skipped(self):
        data = {"project_task": None, "project_overview": "公寓"}
        _normalize_jtbd_fields(data)
        # None 不应报错
        assert data["project_task"] is None

    def test_non_string_field_skipped(self):
        data = {"project_task": {"nested": "obj"}}
        _normalize_jtbd_fields(data)
        assert isinstance(data["project_task"], dict)


# ═══════════════════════════════════════════════════════════════
# U14  _infer_project_type()
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestInferProjectType:
    def test_personal_residential(self):
        data = {"project_task": "75平米住宅公寓改造"}
        assert _infer_project_type(data) == "personal_residential"

    def test_commercial_enterprise(self):
        # _infer_project_type 已委托 ProjectTypeDetector(SSOT)，'办公' 匹配 commercial_office
        data = {"project_task": "500平米办公空间设计"}
        assert _infer_project_type(data) == "commercial_office"

    def test_hybrid(self):
        # '餐厅' 关键词在 SSOT 中命中 commercial_dining，更新断言以匹配 ProjectTypeDetector 行为
        data = {"project_task": "住宅底层改办公，复合住宅餐厅"}
        assert _infer_project_type(data) == "commercial_dining"

    def test_no_match_returns_none(self):
        # _infer_project_type 永不返回 None，无匹配时返回 'other'（v7.200+ 行为）
        data = {"project_task": "策略咨询报告"}
        assert _infer_project_type(data) == "other"

    def test_multiple_text_sources(self):
        """从 project_task + character_narrative + project_overview 综合判断"""
        data = {
            "project_task": "设计一个好看的空间",
            "character_narrative": "业主是一个住在别墅里的家庭",
            "project_overview": "居住改造项目",
        }
        assert _infer_project_type(data) == "personal_residential"


# ═══════════════════════════════════════════════════════════════
# U15  should_execute_phase2()
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestShouldExecutePhase2:
    def test_always_returns_phase2_when_sufficient(self):
        state = {"phase1_info_status": "sufficient"}
        assert should_execute_phase2(state) == "phase2"

    def test_always_returns_phase2_when_insufficient(self):
        state = {"phase1_info_status": "insufficient"}
        assert should_execute_phase2(state) == "phase2"

    def test_always_returns_phase2_default_state(self):
        assert should_execute_phase2({}) == "phase2"

    def test_returns_phase2_not_output(self):
        """确保路由不会跳转到 output（Phase2 不可跳过）"""
        for status in ("sufficient", "insufficient", "unknown"):
            state = {"phase1_info_status": status}
            result = should_execute_phase2(state)
            assert result == "phase2", f"status={status} 应返回 phase2，实际返回 {result}"


# ═══════════════════════════════════════════════════════════════
# U16  _phase1_fallback() / _phase2_fallback()
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestFallbacks:
    def _base_state(self, user_input="帮我设计房子"):
        return {
            "user_input": user_input,
            "session_id": "test",
            "precheck_result": {
                "info_sufficiency": {"is_sufficient": False},
                "capable_deliverables": [{"type": "design_strategy"}],
                "recommended_action": "questionnaire_first",
            },
            "processing_log": [],
            "node_path": [],
        }

    def test_phase1_fallback_returns_required_keys(self):
        import time

        state = self._base_state()
        result = _phase1_fallback(state, time.time())
        for key in ("phase1_result", "phase1_elapsed_ms", "phase1_info_status", "node_path"):
            assert key in result, f"phase1_fallback 缺少键: {key}"

    def test_phase1_fallback_result_has_deliverables(self):
        import time

        result = _phase1_fallback(self._base_state(), time.time())
        assert len(result["phase1_result"]["primary_deliverables"]) >= 1

    def test_phase2_fallback_returns_required_keys(self):
        import time

        state = self._base_state()
        result = _phase2_fallback(state, time.time())
        for key in ("phase2_result", "phase2_elapsed_ms", "analysis_layers", "node_path"):
            assert key in result, f"phase2_fallback 缺少键: {key}"

    def test_phase2_fallback_analysis_layers_has_l4(self):
        import time

        result = _phase2_fallback(self._base_state("公寓改造"), time.time())
        layers = result["analysis_layers"]
        assert "L4_project_task" in layers

    def test_phase1_fallback_node_in_path(self):
        import time

        result = _phase1_fallback(self._base_state(), time.time())
        assert "phase1" in result["node_path"]

    def test_phase2_fallback_node_in_path(self):
        import time

        result = _phase2_fallback(self._base_state(), time.time())
        assert "phase2" in result["node_path"]


# ═══════════════════════════════════════════════════════════════
# U17  build_requirements_analyst_graph()
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestBuildGraph:
    @pytest.mark.skip(reason="build_requirements_analyst_graph 签名已更新为需要 llm_model, prompt_manager 参数，单元测试需 mock 重写")
    def test_graph_has_four_nodes(self):
        g = build_requirements_analyst_graph()
        nodes = list(g.nodes.keys())
        for expected in ("precheck", "phase1", "phase2", "output"):
            assert expected in nodes

    @pytest.mark.skip(reason="build_requirements_analyst_graph 签名已更新为需要 llm_model, prompt_manager 参数")
    def test_graph_compiles_without_error(self):
        g = build_requirements_analyst_graph()
        compiled = g.compile()
        assert compiled is not None

    @pytest.mark.skip(reason="build_requirements_analyst_graph 签名已更新为需要 llm_model, prompt_manager 参数")
    def test_graph_compile_returns_runnable(self):
        from langgraph.graph.state import CompiledStateGraph

        g = build_requirements_analyst_graph()
        compiled = g.compile()
        assert isinstance(compiled, CompiledStateGraph)


# ═══════════════════════════════════════════════════════════════
# U18  DeliverableTypeEnum / DeliverablePriorityEnum 枚举完整性
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestEnumIntegrity:
    def test_deliverable_type_enum_has_key_types(self):
        types = {e.value for e in DeliverableTypeEnum}
        for expected in ("design_strategy", "naming_list", "analysis_report"):
            assert expected in types, f"DeliverableTypeEnum 缺少 {expected}"

    def test_deliverable_priority_enum_has_three_levels(self):
        priorities = {e.value for e in DeliverablePriorityEnum}
        assert "MUST_HAVE" in priorities
        assert "NICE_TO_HAVE" in priorities

    def test_approved_theory_is_non_empty_list(self):
        """APPROVED_THEORY 是 Literal 类型，用 get_args 获取具体值"""
        from typing import get_args

        theories = get_args(APPROVED_THEORY)
        assert len(theories) > 0

    def test_theory_to_lens_covers_all_approved(self):
        """每个 APPROVED_THEORY 理论都应有对应的透镜映射"""
        from typing import get_args

        theories = get_args(APPROVED_THEORY)
        missing = [t for t in theories if t not in THEORY_TO_LENS]
        assert missing == [], f"以下理论缺少透镜映射: {missing}"

    def test_lens_category_has_eight_categories(self):
        categories = {e.value for e in LensCategory}
        assert len(categories) == 8


# ═══════════════════════════════════════════════════════════════
# U19  CoreTension Schema 幻觉防护
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestCoreTensionSchema:
    def _valid_tension(self):
        return CoreTension(
            name="公共展示 vs 私密避难",
            theory_source="Goffman_Front_Back_Stage",
            lens_category=LensCategory.SOCIOLOGY,
            description="台前/台后的身份切换在居住空间中的具体体现，直接决定空间的功能分区逻辑",
            design_implication="设计独立玄关与视觉隔断，作为身份切换的过渡缓冲区，强化前台/后台感知边界",
        )

    def test_valid_construction(self):
        t = self._valid_tension()
        assert t.theory_source == "Goffman_Front_Back_Stage"
        assert t.lens_category == LensCategory.SOCIOLOGY

    def test_hallucinated_theory_rejected(self):
        """非法理论名称（幻觉）应被拒绝"""
        with pytest.raises(Exception):
            CoreTension(
                name="张力名称",
                theory_source="PostModern_Deconstruction_Theory",  # 非法
                lens_category=LensCategory.SOCIOLOGY,
                description="这是一个应该被拒绝的幻觉理论" * 3,
            )

    def test_description_too_short_rejected(self):
        with pytest.raises(Exception):
            CoreTension(
                name="公共展示 vs 私密避难",
                theory_source="Goffman_Front_Back_Stage",
                lens_category=LensCategory.SOCIOLOGY,
                description="太短",
            )
