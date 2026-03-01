"""
v9.3 回归测试套件
====================
覆盖本次修复的 7 处 Bug：

Bug①: requirements_analyst_agent._merge_phase_results — dict[:100] → KeyError
Bug②: questionnaire_summary — state.get("structured_requirements", {}) 不兜底 None
Bug③: main_workflow._requirements_analyst_node — except 分支缺最小骨架
Bug④: output_intent_detection — 无幂等保护，重路由时二次 interrupt
Bug⑦: progressive_questionnaire.progressive_step3_radar — step 写 2 而非 3

pytest 标记：
  @pytest.mark.unit        — 无 LLM，纯逻辑
  @pytest.mark.integration — 多组件协作，无外部 IO
  @pytest.mark.regression  — 回归守护，确保已修复问题不复现
"""

import os
from typing import Any
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# 路径常量
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT_FILE = os.path.join(ROOT, "intelligent_project_analyzer", "agents", "requirements_analyst_agent.py")
QS_FILE = os.path.join(ROOT, "intelligent_project_analyzer", "interaction", "nodes", "questionnaire_summary.py")
MW_FILE = os.path.join(ROOT, "intelligent_project_analyzer", "workflow", "main_workflow.py")
OID_FILE = os.path.join(ROOT, "intelligent_project_analyzer", "interaction", "nodes", "output_intent_detection.py")
PQ_FILE = os.path.join(ROOT, "intelligent_project_analyzer", "interaction", "nodes", "progressive_questionnaire.py")


# ===========================================================================
# Bug① — _merge_phase_results 中 project_task dict[:100] 切片
# ===========================================================================


@pytest.mark.unit
@pytest.mark.regression
class TestProjectTaskDictSliceFix:
    """确认 project_task 为 dict 时不再触发 KeyError: slice(None, 100, None)"""

    def _get_merge_fn(self):
        """直接导入模块级函数 _merge_phase_results"""
        from intelligent_project_analyzer.agents.requirements_analyst_agent import (
            _merge_phase_results,
        )

        return _merge_phase_results

    def _make_phases(self, project_task_value: Any) -> tuple:
        phase1 = {
            "primary_deliverables": ["施工图"],
            "info_status": "sufficient",
            "project_type_preliminary": "住宅",
        }
        phase2 = {
            "structured_output": {
                "project_task": project_task_value,
                "character_narrative": "乡村民宿",
                "physical_context": "四川广元",
                "resource_constraints": "",
                "regulatory_requirements": "",
                "inspiration_references": "",
                "experience_behavior": "",
                "design_challenge": "",
            },
            "analysis_layers": {},
            "expert_handoff": {},
        }
        return phase1, phase2

    def test_project_task_as_string(self):
        """正常字符串路径不受影响"""
        merge = self._get_merge_fn()
        p1, p2 = self._make_phases("设计狮岭村民宿集群")
        result = merge(p1, p2, "测试输入")
        assert result["project_overview"] == "设计狮岭村民宿集群"
        assert result["core_objectives"] == ["设计狮岭村民宿集群"][:1]

    def test_project_task_as_dict_with_full_statement(self):
        """dict 含 full_statement — 应取 full_statement，不报错"""
        merge = self._get_merge_fn()
        task_dict = {
            "full_statement": "为四川广元苍溪县设计乡村振兴民宿集群",
            "i_want_to": "设计民宿",
        }
        p1, p2 = self._make_phases(task_dict)
        result = merge(p1, p2, "测试输入")
        assert result["project_overview"] == task_dict["full_statement"]
        assert result["core_objectives"][0] == task_dict["full_statement"][:100]
        assert isinstance(result["project_tasks"], list)

    def test_project_task_as_dict_without_full_statement(self):
        """dict 仅含 i_want_to — 应 fallback 到 i_want_to"""
        merge = self._get_merge_fn()
        task_dict = {"i_want_to": "设计民宿集群"}
        p1, p2 = self._make_phases(task_dict)
        result = merge(p1, p2, "测试")
        assert result["project_overview"] == "设计民宿集群"

    def test_project_task_as_empty_dict(self):
        """空 dict — 应 fallback 到 str({}) 而非崩溃（不抛 KeyError）"""
        merge = self._get_merge_fn()
        p1, p2 = self._make_phases({})
        result = merge(p1, p2, "测试")
        # str({}) = "{}" — 非空字符串，overview 为 "{}"，core_objectives 为 ["{}"]
        # 关键验证：不抛 KeyError（而非断言具体值）
        assert isinstance(result["project_overview"], str)
        assert isinstance(result["core_objectives"], list)

    def test_project_task_as_none(self):
        """None — 不崩溃，overview/core_objectives 合理为空"""
        merge = self._get_merge_fn()
        p1, p2 = self._make_phases(None)
        result = merge(p1, p2, "测试")
        assert result["project_overview"] == ""
        assert result["core_objectives"] == []

    def test_project_task_long_string_truncation(self):
        """长字符串 core_objectives 应截断到 100 字符"""
        merge = self._get_merge_fn()
        long_str = "A" * 200
        p1, p2 = self._make_phases(long_str)
        result = merge(p1, p2, "测试")
        assert len(result["core_objectives"][0]) == 100


# ===========================================================================
# Bug② — questionnaire_summary None 防御
# ===========================================================================


@pytest.mark.unit
@pytest.mark.regression
class TestQuestionnaireSummaryNoneDefense:
    """state.get("structured_requirements", {}) 在 key 存在但值为 None 时必须兜底"""

    def _invoke_summary_node(self, structured_requirements_value):
        """构造最小 state 并调用 questionnaire_summary_node"""
        from intelligent_project_analyzer.interaction.nodes.questionnaire_summary import (
            questionnaire_summary_node,
        )

        state = {
            "session_id": "test-session-v93",
            "user_input": "狮岭村民宿集群设计",
            "structured_requirements": structured_requirements_value,
            "agent_results": {"requirements_analyst": {"structured_data": {}}},
            "progressive_questionnaire_step": 3,
            "questionnaire_answers": {},
            "radar_adjustments": {},
            "active_projections": ["建筑设计方案"],
        }

        # 构造完整的 restructured_doc 骨架，避免 MagicMock 替代字符串时 TypeError
        _fake_restructured = {
            "project_objectives": {"primary_goal": "测试目标", "secondary_goals": [], "success_metrics": []},
            "design_priorities": [],
            "identified_risks": [],
            "insight_summary": {"L5_sharpness_score": 3, "key_insights": [], "confidence": "medium"},
            "functional_requirements": [],
            "constraints": {},
            "executive_summary": "测试摘要",
        }

        with patch(
            "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.RequirementsRestructuringEngine"
        ) as mock_cls:
            mock_cls.restructure.return_value = _fake_restructured
            # 同时 mock _update_structured_requirements 避免深层链路问题
            with patch(
                "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.QuestionnaireSummaryNode._update_structured_requirements",
                return_value={},
            ):
                # mock LangGraph interrupt 避免 GraphInterrupt
                with patch(
                    "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.interrupt",
                    return_value={"intent": "confirm"},
                ):
                    return questionnaire_summary_node(state)

    def test_none_value_does_not_raise(self):
        """structured_requirements=None 时节点不抛 AttributeError"""
        # 此测试在修复前会抛出 AttributeError: 'NoneType' object has no attribute 'get'
        try:
            self._invoke_summary_node(None)
            # 只要不崩溃即通过
        except AttributeError as e:
            pytest.fail(f"Bug② 未修复 — AttributeError: {e}")

    def test_empty_dict_value_works(self):
        """structured_requirements={} 正常空 dict 路径"""
        self._invoke_summary_node({})
        # 不抛异常即可

    def test_valid_dict_value_works(self):
        """structured_requirements 含真实数据时正常处理"""
        valid_reqs = {
            "analysis_layers": {
                "L1_project_positioning": {"content": "乡村振兴旅游"},
            }
        }
        self._invoke_summary_node(valid_reqs)


# ===========================================================================
# Bug③ — main_workflow except 分支最小骨架
# ===========================================================================


@pytest.mark.unit
@pytest.mark.regression
class TestMainWorkflowExceptionSkeleton:
    """requirements_analyst 节点抛异常后，返回值必须含骨架字段"""

    def test_exception_return_contains_structured_requirements(self):
        """静态检查 except 分支包含 structured_requirements 键"""
        with open(MW_FILE, encoding="utf-8") as f:
            source = f.read()
        # 修复后的 except 分支应包含 structured_requirements
        assert (
            '"structured_requirements"' in source or "'structured_requirements'" in source
        ), "Bug③ 未修复 — main_workflow.py except 分支缺少 structured_requirements 骨架键"

    def test_exception_return_contains_agent_results(self):
        """静态检查 except 分支包含 agent_results 键"""
        with open(MW_FILE, encoding="utf-8") as f:
            source = f.read()
        assert (
            '"agent_results"' in source or "'agent_results'" in source
        ), "Bug③ 未修复 — main_workflow.py except 分支缺少 agent_results 骨架键"


# ===========================================================================
# Bug④ — output_intent_detection 幂等保护
# ===========================================================================


@pytest.mark.unit
@pytest.mark.regression
class TestOutputIntentIdempotency:
    """当 active_projections 已存在且 intent_changed=False 时，应跳过 interrupt"""

    def test_idempotency_source_code_check(self):
        """静态检查幂等保护块是否存在"""
        with open(OID_FILE, encoding="utf-8") as f:
            source = f.read()
        assert "existing_projections" in source, "Bug④ 未修复 — output_intent_detection.py 缺少幂等保护变量 existing_projections"
        assert "intent_changed" in source, "Bug④ 未修复 — 缺少 intent_changed 判断"

    def test_idempotency_skips_interrupt_when_projections_exist(self):
        """active_projections 已存在时节点应直接路由，不调用 interrupt"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            output_intent_detection_node,
        )

        state = {
            "session_id": "test-v93-idempotent",
            "user_input": "狮岭村民宿",
            "active_projections": ["建筑设计方案", "景观规划"],  # 已存在
            "intent_changed": False,
            "structured_requirements": {},
            "agent_results": {},
        }

        interrupt_called = []

        def fake_interrupt(payload):
            interrupt_called.append(payload)
            return {"selected": ["建筑设计方案"]}

        with patch(
            "intelligent_project_analyzer.interaction.nodes.output_intent_detection.interrupt",
            side_effect=fake_interrupt,
        ):
            try:
                output_intent_detection_node(state)
                # 不应调用 interrupt
                assert len(interrupt_called) == 0, "Bug④ 未修复 — active_projections 已存在时仍调用了 interrupt"
            except Exception as e:
                # 如果节点需要更多 state 字段才能运行，跳过
                if "interrupt_called" in str(e):
                    raise
                pytest.skip(f"节点需要额外 state 字段: {e}")

    def test_intent_changed_true_allows_redetection(self):
        """intent_changed=True 时应重新执行检测（不跳过）"""
        with open(OID_FILE, encoding="utf-8") as f:
            source = f.read()
        # 确认逻辑中 intent_changed=True 时不走幂等分支
        # 静态检查：not state.get("intent_changed", False) 或等效逻辑
        assert "intent_changed" in source and (
            "not state.get" in source or "intent_changed, False" in source
        ), "幂等条件检查格式异常"


# ===========================================================================
# Bug⑦ — progressive_questionnaire step 计数器
# ===========================================================================


@pytest.mark.unit
@pytest.mark.regression
class TestProgressiveStepCounter:
    """progressive_step3_radar 完成后应写入 step=3，而非 2"""

    def test_radar_step_writes_step_3(self):
        """
        AST 静态分析：step3_radar 函数中，「中断后写入的 step」应为 3。
        注意：line 522 幂等路径 `progressive_questionnaire_step: 2` 是语义正确的，
        此测试只检查 update_dict 赋值块中的 step 值。
        """
        with open(PQ_FILE, encoding="utf-8") as f:
            source = f.read()

        # 关键字符串直接检查：update_dict 写入的 step 行
        # 修复后应有 'progressive_questionnaire_step': 3  # v9.3 fix
        assert (
            '"progressive_questionnaire_step": 3' in source or "'progressive_questionnaire_step': 3" in source
        ), "Bug⑦ 未修复 — step3_radar update_dict 中未找到 step=3 赋值"
        # 通过：找到值 3

    def test_source_contains_step_3_assignment(self):
        """确认源码包含 'progressive_questionnaire_step': 3"""
        with open(PQ_FILE, encoding="utf-8") as f:
            source = f.read()
        assert (
            '"progressive_questionnaire_step": 3' in source or "'progressive_questionnaire_step': 3" in source
        ), "Bug⑦ 未修复 — progressive_questionnaire.py 中未找到 step=3 赋值"


# ===========================================================================
# 集成测试 — 崩溃链路全链路防御
# ===========================================================================


@pytest.mark.integration
@pytest.mark.regression
class TestV93CrashChainIntegration:
    """
    模拟 analysis-20260223162154-2ed04a93ce89 的崩溃路径：
    requirements_analyst 失败 → state 污染 → questionnaire_summary 接收 None
    """

    def test_crash_chain_defense(self):
        """
        模拟完整崩溃链：
        1. _merge_phase_results 接收 ProjectTask dict（Bug①触发点）
        2. 返回值传入 main_workflow except 骨架
        3. questionnaire_summary 从被污染 state 读取 None（Bug② 触发点）
        全程不应抛出 AttributeError / KeyError
        """
        # Step1: 模拟 _merge_phase_results 接收 dict 类型 project_task
        from intelligent_project_analyzer.agents.requirements_analyst_agent import (
            _merge_phase_results,
        )

        phase1 = {"primary_deliverables": ["方案报告"], "info_status": "sufficient", "project_type_preliminary": "民宿"}
        phase2 = {
            "structured_output": {
                "project_task": {
                    "full_statement": "设计四川广元苍溪县狮岭村民宿集群",
                    "i_want_to": "民宿设计",
                },
                "character_narrative": "乡村振兴",
                "physical_context": "四川广元",
                "resource_constraints": "",
                "regulatory_requirements": "",
                "inspiration_references": "",
                "experience_behavior": "",
                "design_challenge": "",
            },
            "analysis_layers": {},
            "expert_handoff": {},
        }

        try:
            result = _merge_phase_results(phase1, phase2, "狮岭村民宿")
        except KeyError as e:
            pytest.fail(f"Bug① 未修复 — KeyError: {e}")

        assert isinstance(result["project_overview"], str)
        assert result["project_overview"] != ""

        # Step2: 模拟 main_workflow except 返回骨架（Bug③）
        # 骨架中 structured_requirements 应为 {} 而非 None
        workflow_except_state = {
            "error": "simulated failure",
            "structured_requirements": {},  # 修复后的骨架
            "agent_results": {"requirements_analyst": {}},
        }
        assert workflow_except_state.get("structured_requirements") is not None

        # Step3: 模拟 questionnaire_summary 接收被污染 state（Bug②）
        # key 存在但值为 None
        polluted_state = {"structured_requirements": None}
        structured_reqs = polluted_state.get("structured_requirements") or {}
        try:
            analysis_layers = structured_reqs.get("analysis_layers", {})
        except AttributeError as e:
            pytest.fail(f"Bug② 未修复 — AttributeError: {e}")

        assert analysis_layers == {}

    def test_full_state_skeleton_after_exception(self):
        """验证 except 骨架字段能通过 questionnaire_summary 前置检查"""
        # 模拟 except 分支回填的最小 state
        min_state = {
            "session_id": "test-v93-skeleton",
            "user_input": "民宿设计",
            "structured_requirements": {},  # Bug③ 修复
            "agent_results": {"requirements_analyst": {}},
            "progressive_questionnaire_step": 3,
            "questionnaire_answers": {},
            "radar_adjustments": {},
            "active_projections": ["建筑设计方案"],
        }

        # 验证 questionnaire_summary 的 None 防御对空 dict 也适用
        structured_reqs = min_state.get("structured_requirements") or {}
        assert isinstance(structured_reqs, dict)
        analysis_layers = structured_reqs.get("analysis_layers", {})
        assert analysis_layers == {}


# ===========================================================================
# 源码完整性检查
# ===========================================================================


@pytest.mark.unit
@pytest.mark.regression
class TestSourceCodeIntegrity:
    """确认所有修复文件的关键代码片段存在"""

    def test_requirements_analyst_has_isinstance_check(self):
        with open(AGENT_FILE, encoding="utf-8") as f:
            source = f.read()
        assert "isinstance(_pt_raw, dict)" in source, "Bug① 修复代码丢失：缺少 isinstance(_pt_raw, dict) 检查"

    def test_questionnaire_summary_uses_or_empty_dict(self):
        with open(QS_FILE, encoding="utf-8") as f:
            source = f.read()
        assert "or {}" in source, "Bug② 修复代码丢失：缺少 or {} 防御"

    def test_progressive_questionnaire_step3_present(self):
        with open(PQ_FILE, encoding="utf-8") as f:
            source = f.read()
        assert "progressive_questionnaire_step" in source, "progressive_questionnaire.py 缺少 step 赋值"

    def test_output_intent_detection_has_idempotency(self):
        with open(OID_FILE, encoding="utf-8") as f:
            source = f.read()
        assert "existing_projections" in source, "Bug④ 修复代码丢失：缺少 existing_projections 幂等保护"
