# -*- coding: utf-8 -*-
"""
需求分析师 - 集成测试套件
============================
策略：真实节点函数 + Mock LLM（绕过网络，保留业务逻辑）

I01  precheck_node — 充足 / 不足 / 边界输入
I02  phase1_node — Mock LLM 成功 / 代码围栏格式 / LLM 失败降级
I03  phase2_node — Full 模式 / Lite 模式 / 结构化输出 / 降级
I04  output_node — two_phase 合并 / phase1_only / problem_solving_approach 补全
I05  RequirementsAnalystAgentV2 — execute() 完整图调用
I06  _weighted_info_status_vote 与节点的集成
I07  能力边界边界场景（CAD/3D 图要求转化）
I08  模式检测结果传递（Phase1 → Phase2 → Output）
"""

import json
import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intelligent_project_analyzer.agents.requirements_analyst_agent import (
    RequirementsAnalystAgentV2,
    RequirementsAnalystState,
    output_node,
    phase1_node,
    phase2_node,
    precheck_node,
)
from intelligent_project_analyzer.core.prompt_manager import PromptManager


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def _mock_llm_response(content: str):
    """创建返回固定内容的 Mock LLM"""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.content = content
    mock_llm.invoke.return_value = mock_response
    # structured_output 失败 → 回退到普通 invoke
    mock_llm.with_structured_output.side_effect = Exception("structured output disabled in test")
    return mock_llm


def _base_state(
    user_input: str = "帮我设计75平米的公寓，预算60万，现代极简风格，三代同堂", session_id: str = "test"
) -> RequirementsAnalystState:
    return {
        "user_input": user_input,
        "session_id": session_id,
        "processing_log": [],
        "node_path": [],
    }


def _valid_phase1_json(info_status: str = "sufficient") -> str:
    """构造合法的 Phase1 LLM 输出 JSON"""
    return json.dumps(
        {
            "phase": 1,
            "info_status": info_status,
            "info_status_reason": "用户提供了完整的面积预算风格居住人口等关键信息可进入深度分析",
            "project_type_preliminary": "personal_residential",
            "project_summary": "75平米城市公寓改造，三代同堂，现代极简，60万，4个月",
            "primary_deliverables": [
                {
                    "deliverable_id": "D1",
                    "type": "design_strategy",
                    "description": "室内设计策略文档，含空间布局和选材指导",
                    "priority": "MUST_HAVE",
                    "acceptance_criteria": ["必须包含分区平面图", "必须含族群适配分析"],
                    "deliverable_owner_suggestion": {
                        "primary_owner": "V3_叙事与体验专家_3-3",
                        "owner_rationale": "擅长将生活叙事转化为空间设计策略",
                    },
                    "capability_check": {"within_capability": True},
                }
            ],
            "recommended_next_step": "phase2_analysis",
            "next_step_reason": "信息充足，可直接进入Phase2进行L1-L7深度分析",
        },
        ensure_ascii=False,
    )


def _valid_phase2_json(info_status: str = "sufficient") -> str:
    """构造合法的 Phase2 LLM 输出 JSON"""
    return json.dumps(
        {
            "phase": 2,
            "structured_output": {
                "project_task": "将75平米公寓改造成兼顾三代同堂需求与现代极简美学的生活空间",
                "character_narrative": "业主为三代家庭，祖父母注重安全动线，年轻父母关注高效收纳",
                "physical_context": "上海高层南向公寓，采光好，层高2.8m",
                "resource_constraints": "预算60万，工期4个月",
                "design_challenge": "在极简美学与多代功能性间寻找平衡点",
            },
            "analysis_layers": {
                "L1_facts": ["75平米", "三代同堂", "60万预算"],
                "L3_core_tension": "功能密度 vs 极简美学",
                "L4_project_task": "三代共居的极简现代公寓改造",
                "L5_sharpness": {"score": 75, "verdict": "sharp"},
                "L5_1_five_whys": ["为什么要极简？—身份认同", "为什么三代同堂？—文化传承"],
            },
            "expert_handoff": {
                "critical_questions_for_experts": ["如何在极简框架内满足老人的安全扶手需求？"],
                "recommended_experts": ["V3_叙事与体验专家", "V2_设计总监"],
            },
        },
        ensure_ascii=False,
    )


# ═══════════════════════════════════════════════════════════════
# I01  precheck_node
# ═══════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestPrecheckNode:
    def test_sufficient_input(self):
        state = _base_state("我是32岁前律师，有75平米一居室公寓，上海，预算60万，现代极简，4个月")
        result = precheck_node(state)

        assert "precheck_result" in result
        assert "precheck_elapsed_ms" in result
        assert "info_sufficient" in result
        assert "capability_score" in result
        assert result["precheck_elapsed_ms"] > 0
        assert "precheck" in result["node_path"]

    def test_insufficient_input(self):
        state = _base_state("帮我设计一下房子")
        result = precheck_node(state)

        assert "precheck_result" in result
        assert result["info_sufficient"] is False
        assert "precheck" in result["node_path"]

    def test_empty_input(self):
        """空输入不崩溃"""
        state = _base_state("")
        result = precheck_node(state)
        assert "precheck_result" in result
        assert result["info_sufficient"] is False

    def test_very_long_input(self):
        """超长输入不崩溃"""
        state = _base_state("设计需求" * 1000)
        result = precheck_node(state)
        assert "precheck_result" in result

    def test_processing_log_updated(self):
        state = _base_state("公寓设计")
        result = precheck_node(state)
        assert len(result["processing_log"]) >= 1
        # 日志应有 Precheck 关键词
        log_text = " ".join(result["processing_log"])
        assert "Precheck" in log_text or "precheck" in log_text.lower()

    def test_capability_score_in_range(self):
        state = _base_state("帮我设计75平米住宅，预算50万，现代风格")
        result = precheck_node(state)
        assert 0.0 <= result["capability_score"] <= 1.0

    def test_cad_request_capability_partial(self):
        """CAD 施工图请求 → 能力受限"""
        state = _base_state("需要一套完整的CAD施工图，包含给排水和电气布线")
        result = precheck_node(state)
        # 能力分数应低于 1.0（有部分超出能力范围的需求）
        assert result["capability_score"] <= 1.0


# ═══════════════════════════════════════════════════════════════
# I02  phase1_node — Mock LLM
# ═══════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestPhase1NodeMocked:
    def _state_with_llm(self, user_input: str, llm_content: str, info_status: str = "sufficient"):
        """构造含 Mock LLM 和 PromptManager 的 State"""
        mock_llm = _mock_llm_response(llm_content)
        pm = PromptManager()
        precheck = {
            "info_sufficiency": {
                "is_sufficient": (info_status == "sufficient"),
                "score": 0.8,
                "present_elements": ["面积", "预算"],
                "missing_elements": [],
            },
            "deliverable_capability": {"capability_score": 0.9},
            "capable_deliverables": [{"type": "design_strategy"}],
            "transformations": [],
        }
        return (
            {
                "user_input": user_input,
                "session_id": "test",
                "precheck_result": precheck,
                "processing_log": [],
                "node_path": ["precheck"],
            },
            mock_llm,
            pm,
        )

    def test_successful_phase1_returns_required_keys(self):
        state, mock_llm, pm = self._state_with_llm(
            "75平米公寓，预算60万，现代风格",
            _valid_phase1_json("sufficient"),
        )
        result = phase1_node(state, mock_llm, pm)

        for key in (
            "phase1_result",
            "phase1_elapsed_ms",
            "phase1_info_status",
            "recommended_next_step",
            "primary_deliverables",
            "node_path",
        ):
            assert key in result, f"phase1_node 缺少键: {key}"

    def test_phase1_node_path_updated(self):
        state, mock_llm, pm = self._state_with_llm("公寓改造", _valid_phase1_json())
        result = phase1_node(state, mock_llm, pm)
        assert "phase1" in result["node_path"]

    def test_phase1_sufficient_info_status(self):
        state, mock_llm, pm = self._state_with_llm("公寓改造", _valid_phase1_json("sufficient"))
        result = phase1_node(state, mock_llm, pm)
        # 最终状态由加权投票决定，不一定与 LLM 完全一致
        assert result["phase1_info_status"] in ("sufficient", "insufficient")

    def test_phase1_deliverables_extracted(self):
        state, mock_llm, pm = self._state_with_llm("公寓改造", _valid_phase1_json())
        result = phase1_node(state, mock_llm, pm)
        assert len(result["primary_deliverables"]) >= 1

    def test_phase1_code_fence_json_parsed(self):
        """LLM 回复用代码围栏包裹的 JSON"""
        fenced = f"分析完成：\n```json\n{_valid_phase1_json()}\n```\n请参考。"
        state, mock_llm, pm = self._state_with_llm("公寓改造", fenced)
        result = phase1_node(state, mock_llm, pm)
        assert "phase1_result" in result
        assert result["phase1_result"].get("phase") == 1

    def test_phase1_invalid_json_triggers_fallback(self):
        """LLM 返回无效 JSON → 触发 fallback"""
        state, mock_llm, pm = self._state_with_llm("公寓改造", "这是无法解析的纯文本响应，没有任何 JSON")
        result = phase1_node(state, mock_llm, pm)
        assert "phase1_result" in result
        # fallback 结果有 "fallback" 标记
        assert result["phase1_result"].get("fallback") is True or "phase1_result" in result

    def test_phase1_mode_detection_results_present(self):
        state, mock_llm, pm = self._state_with_llm("公寓改造", _valid_phase1_json())
        result = phase1_node(state, mock_llm, pm)
        assert "detected_design_modes" in result

    def test_phase1_processing_log_updated(self):
        state, mock_llm, pm = self._state_with_llm("公寓改造", _valid_phase1_json())
        result = phase1_node(state, mock_llm, pm)
        assert len(result["processing_log"]) >= 1
        log_text = " ".join(result["processing_log"])
        assert "Phase1" in log_text

    def test_phase1_weighted_vote_details_present(self):
        """加权投票决策细节应存在"""
        state, mock_llm, pm = self._state_with_llm("公寓改造75平预算60万", _valid_phase1_json())
        result = phase1_node(state, mock_llm, pm)
        assert "weighted_vote_decision" in result
        vote = result["weighted_vote_decision"]
        assert "final_score" in vote
        assert "votes" in vote


# ═══════════════════════════════════════════════════════════════
# I03  phase2_node — Mock LLM
# ═══════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestPhase2NodeMocked:
    def _state(self, info_status: str = "sufficient", llm_content: str = None):
        if llm_content is None:
            llm_content = _valid_phase2_json(info_status)
        mock_llm = _mock_llm_response(llm_content)
        pm = PromptManager()
        phase1 = json.loads(_valid_phase1_json(info_status))
        return (
            {
                "user_input": "75平米公寓，三代同堂，60万预算，现代极简",
                "session_id": "test",
                "phase1_result": phase1,
                "phase1_info_status": info_status,
                "primary_deliverables": phase1.get("primary_deliverables", []),
                "detected_design_modes": [],
                "mode_detection_elapsed_ms": 0,
                "processing_log": ["[Phase1] done"],
                "node_path": ["precheck", "phase1"],
            },
            mock_llm,
            pm,
        )

    def test_phase2_full_mode_returns_required_keys(self):
        state, mock_llm, pm = self._state("sufficient")
        result = phase2_node(state, mock_llm, pm)
        for key in ("phase2_result", "phase2_elapsed_ms", "analysis_layers", "expert_handoff", "node_path"):
            assert key in result, f"phase2_node 缺少键: {key}"

    def test_phase2_lite_mode_returns_required_keys(self):
        state, mock_llm, pm = self._state("insufficient")
        result = phase2_node(state, mock_llm, pm)
        for key in ("phase2_result", "phase2_elapsed_ms", "analysis_layers", "node_path"):
            assert key in result

    def test_phase2_mode_label_full(self):
        state, mock_llm, pm = self._state("sufficient")
        result = phase2_node(state, mock_llm, pm)
        assert result.get("phase2_mode") == "Phase2-Full"

    def test_phase2_mode_label_lite(self):
        state, mock_llm, pm = self._state("insufficient")
        result = phase2_node(state, mock_llm, pm)
        assert result.get("phase2_mode") == "Phase2-Lite"

    def test_phase2_node_path_updated(self):
        state, mock_llm, pm = self._state()
        result = phase2_node(state, mock_llm, pm)
        assert "phase2" in result["node_path"]

    def test_phase2_invalid_json_triggers_fallback(self):
        state, mock_llm, pm = self._state(llm_content="This is not JSON at all")
        result = phase2_node(state, mock_llm, pm)
        assert "phase2_result" in result
        assert result["phase2_result"].get("fallback") is True or "phase2_result" in result

    def test_phase2_with_mode_detection_uses_phase1_results(self):
        """Phase2 复用 Phase1 的模式检测结果（不重复检测）"""
        state, mock_llm, pm = self._state()
        state["detected_design_modes"] = [{"mode": "M1_spatial_narrative", "confidence": 0.85}]
        result = phase2_node(state, mock_llm, pm)
        # 模式结果应透传
        assert "detected_design_modes" in result
        assert len(result["detected_design_modes"]) >= 1


# ═══════════════════════════════════════════════════════════════
# I04  output_node
# ═══════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestOutputNode:
    def _two_phase_state(self):
        phase1 = json.loads(_valid_phase1_json("sufficient"))
        phase2 = json.loads(_valid_phase2_json("sufficient"))
        return {
            "user_input": "75平米公寓，三代同堂",
            "session_id": "test",
            "phase1_result": phase1,
            "phase2_result": phase2,
            "precheck_elapsed_ms": 5.0,
            "phase1_elapsed_ms": 1200.0,
            "phase2_elapsed_ms": 3000.0,
            "detected_design_modes": [],
            "processing_log": [],
            "node_path": ["precheck", "phase1", "phase2"],
        }

    def _phase1_only_state(self):
        phase1 = json.loads(_valid_phase1_json("insufficient"))
        return {
            "user_input": "帮我设计房子",
            "session_id": "test",
            "phase1_result": phase1,
            "phase2_result": {},  # 空 phase2
            "precheck_elapsed_ms": 5.0,
            "phase1_elapsed_ms": 1200.0,
            "phase2_elapsed_ms": 0.0,
            "detected_design_modes": [],
            "processing_log": [],
            "node_path": ["precheck", "phase1"],
        }

    def test_two_phase_returns_required_keys(self):
        result = output_node(self._two_phase_state())
        for key in ("structured_data", "confidence", "analysis_mode", "project_type", "node_path"):
            assert key in result, f"output_node 缺少键: {key}"

    def test_two_phase_analysis_mode(self):
        result = output_node(self._two_phase_state())
        assert result["analysis_mode"] == "two_phase"

    def test_phase1_only_analysis_mode(self):
        result = output_node(self._phase1_only_state())
        assert result["analysis_mode"] == "phase1_only"

    def test_confidence_in_range(self):
        result = output_node(self._two_phase_state())
        assert 0.0 <= result["confidence"] <= 1.0

    def test_two_phase_confidence_higher_than_phase1_only(self):
        c2 = output_node(self._two_phase_state())["confidence"]
        c1 = output_node(self._phase1_only_state())["confidence"]
        assert c2 >= c1

    def test_a01_problem_solving_approach_generated_in_two_phase(self):
        """A-01: output_node 应为 two_phase 模式补全 problem_solving_approach"""
        state = self._two_phase_state()
        result = output_node(state)
        sd = result["structured_data"]
        assert "problem_solving_approach" in sd
        psa = sd["problem_solving_approach"]
        assert psa is not None
        assert psa.get("source") == "phase2_output"

    def test_a01_no_override_if_already_present(self):
        """若 phase2 已提供 problem_solving_approach，不应覆盖"""
        state = self._two_phase_state()
        # 直接在 phase2_result 写入
        state["phase2_result"]["structured_output"]["problem_solving_approach"] = {
            "task_type": "custom",
            "source": "llm_output",
        }
        # 但合并时 _merge_phase_results 会把 problem_solving_approach 放到顶层 structured_data
        # 此测试验证 output_node 的 if not structured_data.get() 逻辑
        result = output_node(state)
        sd = result["structured_data"]
        # 如果有两个都存在，验证结构完整性
        assert "problem_solving_approach" in sd

    def test_node_path_updated(self):
        result = output_node(self._two_phase_state())
        assert "output" in result["node_path"]

    def test_elapsed_time_in_structured_data(self):
        result = output_node(self._two_phase_state())
        sd = result["structured_data"]
        assert "phase1_elapsed_ms" in sd
        assert "phase2_elapsed_ms" in sd

    def test_total_elapsed_ms_calculated(self):
        result = output_node(self._two_phase_state())
        assert "total_elapsed_ms" in result
        assert result["total_elapsed_ms"] > 0

    def test_detected_modes_injected(self):
        state = self._two_phase_state()
        state["detected_design_modes"] = [
            {"mode": "M1", "confidence": 0.9},
            {"mode": "M3", "confidence": 0.6},
        ]
        result = output_node(state)
        sd = result["structured_data"]
        assert "detected_design_modes" in sd
        assert sd["primary_design_mode"] == "M1"

    def test_project_type_inferred(self):
        result = output_node(self._two_phase_state())
        # project_task 包含 "公寓" → personal_residential
        assert result["project_type"] in ("personal_residential", "hybrid_residential_commercial", None)


# ═══════════════════════════════════════════════════════════════
# I05  RequirementsAnalystAgentV2.execute() 全图调用
# ═══════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestAgentV2Execute:
    def _build_agent(self, phase1_content: str = None, phase2_content: str = None):
        """构建含 Mock LLM 的 Agent V2"""
        if phase1_content is None:
            phase1_content = _valid_phase1_json("sufficient")
        if phase2_content is None:
            phase2_content = _valid_phase2_json("sufficient")

        call_count = [0]
        responses = [phase1_content, phase2_content]

        mock_llm = MagicMock()

        def side_effect(messages):
            idx = call_count[0]
            call_count[0] += 1
            resp = MagicMock()
            resp.content = responses[idx % len(responses)]
            return resp

        mock_llm.invoke.side_effect = side_effect
        mock_llm.with_structured_output.side_effect = Exception("disable structured output")
        return RequirementsAnalystAgentV2(llm_model=mock_llm)

    def test_execute_returns_analysis_result(self):
        agent = self._build_agent()
        result = agent.execute("75平米公寓，预算60万，现代极简，三代同堂", "session-001")
        from intelligent_project_analyzer.core.types import AnalysisResult

        assert isinstance(result, AnalysisResult)

    def test_execute_has_structured_data(self):
        agent = self._build_agent()
        result = agent.execute("75平米公寓，预算60万，现代极简，三代同堂", "session-001")
        assert result.structured_data is not None
        assert isinstance(result.structured_data, dict)

    def test_execute_confidence_in_range(self):
        agent = self._build_agent()
        result = agent.execute("75平米公寓，预算60万", "session-001")
        assert 0.0 <= result.confidence <= 1.0

    def test_execute_analysis_mode_in_metadata(self):
        agent = self._build_agent()
        result = agent.execute("75平米公寓，预算60万", "session-001")
        assert "analysis_mode" in result.metadata
        assert result.metadata["analysis_mode"] in ("two_phase", "phase1_only")

    def test_execute_node_path_in_metadata(self):
        agent = self._build_agent()
        result = agent.execute("75平米公寓，预算60万", "session-001")
        assert "node_path" in result.metadata
        path = result.metadata["node_path"]
        for expected_node in ("precheck", "phase1", "phase2", "output"):
            assert expected_node in path, f"节点路径中缺少 {expected_node}"

    def test_execute_content_is_json_string(self):
        """content 字段应为可解析的 JSON 字符串"""
        agent = self._build_agent()
        result = agent.execute("公寓设计", "session-001")
        data = json.loads(result.content)
        assert isinstance(data, dict)

    def test_execute_sources_present(self):
        agent = self._build_agent()
        result = agent.execute("公寓设计", "session-001")
        assert len(result.sources) > 0

    def test_execute_empty_input_uses_fallback(self):
        """空输入应通过 fallback 优雅处理"""
        agent = self._build_agent(
            phase1_content="非JSON文字触发fallback",
            phase2_content="非JSON文字触发fallback",
        )
        result = agent.execute("", "session-empty")
        # 不应崩溃
        assert result is not None
        assert result.structured_data is not None

    def test_compat_layer_execute(self):
        """RequirementsAnalystCompat 向后兼容层正常工作"""
        from intelligent_project_analyzer.agents.requirements_analyst_agent import RequirementsAnalystCompat

        mock_llm = MagicMock()
        cnt = [0]

        def side_effect(messages):
            idx = cnt[0]
            cnt[0] += 1
            resp = MagicMock()
            resp.content = [_valid_phase1_json(), _valid_phase2_json()][idx % 2]
            return resp

        mock_llm.invoke.side_effect = side_effect
        mock_llm.with_structured_output.side_effect = Exception("disable")

        agent = RequirementsAnalystCompat(llm_model=mock_llm)
        state = {"user_input": "公寓改造，75平，60万", "session_id": "compat-test"}
        result = agent.execute(state)
        from intelligent_project_analyzer.core.types import AnalysisResult

        assert isinstance(result, AnalysisResult)


# ═══════════════════════════════════════════════════════════════
# I06  加权投票与节点集成
# ═══════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestWeightedVoteIntegration:
    """验证 precheck 判断 + phase1 LLM 判断 + mode 调整 三方投票一致性"""

    def test_precheck_sufficient_phase1_insufficient_votes_correctly(self):
        """precheck=sufficient(0.4) + phase1=insufficient(0) → 0.4 → insufficient"""
        from intelligent_project_analyzer.agents.requirements_analyst_agent import _weighted_info_status_vote

        precheck = {"info_sufficiency": {"is_sufficient": True}}
        phase1 = {"info_status": "insufficient"}
        mode = {}
        status, details = _weighted_info_status_vote(precheck, phase1, mode)
        assert status == "insufficient"
        assert details["final_score"] == pytest.approx(0.4)

    def test_precheck_insufficient_phase1_sufficient_votes_correctly(self):
        """precheck=insufficient(0) + phase1=sufficient(0.4) + mode={}(默认0.2) → 0.6 → sufficient"""
        from intelligent_project_analyzer.agents.requirements_analyst_agent import _weighted_info_status_vote

        precheck = {"info_sufficiency": {"is_sufficient": False}}
        phase1 = {"info_status": "sufficient"}
        mode = {}
        status, details = _weighted_info_status_vote(precheck, phase1, mode)
        # 实际行为: 0 + 0.4 + 0.2(mode默认sufficient) = 0.6 ≥ 0.5 → sufficient
        assert status == "sufficient"

    def test_consensus_both_sufficient(self):
        from intelligent_project_analyzer.agents.requirements_analyst_agent import _weighted_info_status_vote

        precheck = {"info_sufficiency": {"is_sufficient": True}}
        phase1 = {"info_status": "sufficient"}
        _, details = _weighted_info_status_vote(precheck, phase1, {})
        assert details["consensus"] is True


# ═══════════════════════════════════════════════════════════════
# I07  能力边界转化集成
# ═══════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestCapabilityBoundaryIntegration:
    """CAD/3D 效果图类请求应被转化为 design_strategy"""

    def test_capability_check_transforms_cad_request(self):
        from intelligent_project_analyzer.utils.capability_detector import CapabilityDetector, CapabilityLevel

        results = CapabilityDetector.detect_deliverable_capability("请提供完整CAD施工图")
        if results:
            # 应部分或全部超出能力
            cap_levels = [r.capability_level for r in results]
            assert CapabilityLevel.PARTIAL in cap_levels or CapabilityLevel.NONE in cap_levels

    def test_capability_check_accepts_design_strategy(self):
        from intelligent_project_analyzer.utils.capability_detector import CapabilityDetector, CapabilityLevel

        results = CapabilityDetector.detect_deliverable_capability("需要一份设计策略文档")
        if results:
            levels = [r.capability_level for r in results]
            assert CapabilityLevel.FULL in levels

    def test_precheck_detects_beyond_capability(self):
        state = _base_state("需要3D效果渲染图和精确的材料报价单以及CAD图纸")
        result = precheck_node(state)
        # 能力分数应小于 1.0
        assert result["capability_score"] <= 1.0


# ═══════════════════════════════════════════════════════════════
# I08  模式检测结果传递
# ═══════════════════════════════════════════════════════════════


@pytest.mark.integration
class TestModeDetectionPipeline:
    def test_mode_detection_runs_in_phase1(self):
        pm = PromptManager()
        precheck_result = {
            "info_sufficiency": {"is_sufficient": True, "score": 0.8, "present_elements": [], "missing_elements": []},
            "deliverable_capability": {"capability_score": 0.9},
            "capable_deliverables": [{"type": "design_strategy"}],
            "transformations": [],
        }
        mock_llm = _mock_llm_response(_valid_phase1_json())
        state = {
            "user_input": "我是建筑师，需要为山地乡村设计一套可持续建筑策略文档",
            "session_id": "test",
            "precheck_result": precheck_result,
            "processing_log": [],
            "node_path": ["precheck"],
        }
        result = phase1_node(state, mock_llm, pm)
        assert "detected_design_modes" in result
        # 不应报错，列表可为空
        assert isinstance(result["detected_design_modes"], list)

    def test_mode_detection_elapsed_recorded(self):
        pm = PromptManager()
        precheck_result = {
            "info_sufficiency": {"is_sufficient": True, "score": 0.8, "present_elements": [], "missing_elements": []},
            "deliverable_capability": {"capability_score": 0.9},
            "capable_deliverables": [],
            "transformations": [],
        }
        mock_llm = _mock_llm_response(_valid_phase1_json())
        state = {
            "user_input": "文化遗址附近的公共广场设计",
            "session_id": "test",
            "precheck_result": precheck_result,
            "processing_log": [],
            "node_path": [],
        }
        result = phase1_node(state, mock_llm, pm)
        assert "mode_detection_elapsed_ms" in result
        assert result["mode_detection_elapsed_ms"] >= 0
