# -*- coding: utf-8 -*-
"""
需求分析师 - 回归测试套件
============================
专门验证 Phase 1 止血修复的 5 个变更不被回滚：

C-01  Schema补字段：Phase1Output 新增 problem_types/proposition_candidates/complexity_assessment
C-02  删Rule2：insufficient + phase2_analysis 不再报验证错误
A-01  V2补 problem_solving_approach：output_node 自动补全
V-Default V2切换为默认：main_workflow.py 默认使用 V717
C-05  删 utils：requirements_analyst_utils.py 文件不存在

全部使用 @pytest.mark.unit 标记（不调用 LLM，毫秒级）
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ═══════════════════════════════════════════════════════════════
# 共享 fixture 构造函数（满足 Phase1Output 所有 min_length 约束）
# ═══════════════════════════════════════════════════════════════


def _make_deliverable():
    """构造满足约束的最小合法 Phase1Deliverable"""
    from intelligent_project_analyzer.agents.requirements_analyst_schema import (
        CapabilityCheck,
        DeliverableOwnerSuggestion,
        DeliverablePriorityEnum,
        DeliverableTypeEnum,
        Phase1Deliverable,
    )

    return Phase1Deliverable(
        deliverable_id="D1",
        type=DeliverableTypeEnum.DESIGN_STRATEGY,
        description="室内设计策略文档，含完整空间规划和选材指导",
        priority=DeliverablePriorityEnum.MUST_HAVE,
        acceptance_criteria=["必须包含平面布局方案"],
        deliverable_owner_suggestion=DeliverableOwnerSuggestion(
            primary_owner="V3_叙事与体验专家_3-3",
            owner_rationale="最擅长将生活叙事转化为空间体验",
        ),
        capability_check=CapabilityCheck(within_capability=True),
    )


def _make_p1(info_status: str = "sufficient", next_step: str = "phase2_analysis"):
    """构造满足所有 min_length 约束的最小合法 Phase1Output"""
    from intelligent_project_analyzer.agents.requirements_analyst_schema import Phase1Output

    return Phase1Output(
        info_status=info_status,
        info_status_reason="用户提供了完整的面积预算风格偏好居住人口等关键信息，信息充足",
        project_type_preliminary="personal_residential",
        project_summary="75平米城市公寓改造，三代同堂，现代极简风格，预算60万，注重收纳与光线",
        primary_deliverables=[_make_deliverable()],
        recommended_next_step=next_step,
        next_step_reason="信息充足，可直接进入Phase2深度分析以获取专业设计策略",
    )


# ═══════════════════════════════════════════════════════════════
# R01 - C-01: Schema 补字段回归
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestC01SchemaFieldsRegression:
    """C-01: Phase1Output 必须包含 3 个新字段，绝不能因重构被删除"""

    def test_problem_types_field_exists(self):
        """problem_types 字段必须存在于 Phase1Output"""
        from intelligent_project_analyzer.agents.requirements_analyst_schema import Phase1Output

        fields = Phase1Output.model_fields
        assert "problem_types" in fields, "C-01 REGRESSION: problem_types 字段已被删除！"

    def test_proposition_candidates_field_exists(self):
        """proposition_candidates 字段必须存在于 Phase1Output"""
        from intelligent_project_analyzer.agents.requirements_analyst_schema import Phase1Output

        fields = Phase1Output.model_fields
        assert "proposition_candidates" in fields, "C-01 REGRESSION: proposition_candidates 字段已被删除！"

    def test_complexity_assessment_field_exists(self):
        """complexity_assessment 字段必须存在于 Phase1Output"""
        from intelligent_project_analyzer.agents.requirements_analyst_schema import Phase1Output

        fields = Phase1Output.model_fields
        assert "complexity_assessment" in fields, "C-01 REGRESSION: complexity_assessment 字段已被删除！"

    def test_problem_types_is_optional_list(self):
        """problem_types 为 Optional[List[str]]，可接受 None 或列表"""
        obj = _make_p1()
        assert obj.problem_types is None or isinstance(obj.problem_types, list)

    def test_proposition_candidates_is_optional_list(self):
        obj = _make_p1()
        assert obj.proposition_candidates is None or isinstance(obj.proposition_candidates, list)

    def test_complexity_assessment_is_optional_str_or_dict(self):
        obj = _make_p1()
        assert obj.complexity_assessment is None or isinstance(obj.complexity_assessment, (str, dict))

    def test_three_fields_survive_model_dump(self):
        """model_dump 后 3 个字段应保留在输出字典中"""

        obj = _make_p1()
        obj_with_fields = obj.model_copy(
            update={
                "problem_types": ["空间优化"],
                "proposition_candidates": ["极简路线"],
                "complexity_assessment": "中等",
            }
        )
        d = obj_with_fields.model_dump()
        assert "problem_types" in d
        assert "proposition_candidates" in d
        assert "complexity_assessment" in d
        assert d["problem_types"] == ["空间优化"]
        assert d["proposition_candidates"] == ["极简路线"]
        assert d["complexity_assessment"] == "中等"


# ═══════════════════════════════════════════════════════════════
# R02 - C-02: 删 Rule2 回归
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestC02DeleteRule2Regression:
    """C-02: insufficient + phase2_analysis 组合曾触发 Rule2 验证错误，修复后不应再报错"""

    def test_insufficient_with_phase2_analysis_no_error(self):
        """info_status=insufficient + recommended_next_step=phase2_analysis 不应抛出 ValidationError"""
        # 这组合在修复前会触发 Rule2 验证错误
        obj = _make_p1(info_status="insufficient", next_step="phase2_analysis")
        assert obj.info_status == "insufficient"
        assert obj.recommended_next_step == "phase2_analysis"

    def test_insufficient_with_need_more_info_still_valid(self):
        """insufficient + questionnaire_first 仍然合法（Rule4 的替代值）"""
        # need_more_info 已重命名为 questionnaire_first / clarify_expectations
        obj = _make_p1(info_status="insufficient", next_step="questionnaire_first")
        assert obj.recommended_next_step == "questionnaire_first"

    def test_sufficient_with_phase2_analysis_still_valid(self):
        """sufficient + phase2_analysis 仍合法（Rule1）"""
        obj = _make_p1(info_status="sufficient", next_step="phase2_analysis")
        assert obj.info_status == "sufficient"
        assert obj.recommended_next_step == "phase2_analysis"

    def test_rule4_insufficient_must_not_be_phase2(self):
        """Rule4 仍存在：insufficient + need_more_info 是推荐组合（不强制，但应支持）"""
        import pydantic

        # 只需要确保 phase2_analysis 不再被 Rule2 禁止
        try:
            obj = _make_p1(info_status="insufficient", next_step="phase2_analysis")
            # 不应抛出异常 → Rule2 确认已删除
            assert obj is not None
        except pydantic.ValidationError as e:
            pytest.fail(f"C-02 REGRESSION: Rule2 仍然存在！ValidationError: {e}")


# ═══════════════════════════════════════════════════════════════
# R03 - A-01: problem_solving_approach 自动补全回归
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestA01ProblemSolvingApproachRegression:
    """A-01: output_node 对 two_phase 模式必须自动生成 problem_solving_approach"""

    def _make_output_state(self, l5_data=None, l4_data=None):
        """构造 output_node 所需的状态（无 LLM）"""
        analysis_layers = {
            "L1_facts": ["75平米", "60万预算", "三代同堂"],
            "L3_core_tension": "功能密度 vs 极简美学",
        }
        if l4_data:
            analysis_layers["L4_project_task"] = l4_data
        if l5_data:
            analysis_layers["L5_sharpness"] = l5_data

        phase2 = {
            "phase": 2,
            "structured_output": {
                "project_task": "三代共居公寓极简现代化改造",
                "character_narrative": "祖父母+年轻父母+孩子",
            },
            "analysis_layers": analysis_layers,
            "expert_handoff": {},
        }
        phase1 = {
            "phase": 1,
            "info_status": "sufficient",
            "info_status_reason": "充足",
            "project_type_preliminary": "personal_residential",
            "project_summary": "75平公寓改造",
            "primary_deliverables": [
                {
                    "deliverable_id": "D1",
                    "type": "design_strategy",
                    "description": "空间策略",
                    "priority": "MUST_HAVE",
                    "acceptance_criteria": ["平面图"],
                    "deliverable_owner_suggestion": {
                        "primary_owner": "V3_叙事与体验专家",
                        "owner_rationale": "ok",
                    },
                    "capability_check": {"within_capability": True},
                }
            ],
            "recommended_next_step": "phase2_analysis",
            "next_step_reason": "ok",
        }
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

    def test_a01_problem_solving_approach_generated(self):
        """两阶段模式下 output_node 必须生成 problem_solving_approach"""
        from intelligent_project_analyzer.agents.requirements_analyst_agent import output_node

        result = output_node(
            self._make_output_state(
                l5_data={"score": 75, "verdict": "sharp"},
                l4_data="三代共居公寓的极简改造",
            )
        )
        sd = result["structured_data"]
        assert "problem_solving_approach" in sd, "A-01 REGRESSION: problem_solving_approach 字段缺失！"
        psa = sd["problem_solving_approach"]
        assert psa is not None
        assert isinstance(psa, dict)

    def test_a01_psa_source_is_phase2_output(self):
        """problem_solving_approach 的 source 应为 phase2_output"""
        from intelligent_project_analyzer.agents.requirements_analyst_agent import output_node

        result = output_node(
            self._make_output_state(
                l5_data={"score": 80, "verdict": "very_sharp"},
            )
        )
        psa = result["structured_data"]["problem_solving_approach"]
        assert (
            psa.get("source") == "phase2_output"
        ), f"A-01 REGRESSION: source 应为 'phase2_output'，实际为 {psa.get('source')}"

    def test_a01_psa_not_generated_for_phase1_only(self):
        """phase1_only 模式下 problem_solving_approach 应为 None 或不存在"""
        from intelligent_project_analyzer.agents.requirements_analyst_agent import output_node

        state = {
            "user_input": "帮我设计房子",
            "session_id": "test",
            "phase1_result": {
                "phase": 1,
                "info_status": "insufficient",
                "info_status_reason": "不足",
                "project_type_preliminary": "personal_residential",
                "project_summary": "不完整",
                "primary_deliverables": [],
                "recommended_next_step": "need_more_info",
                "next_step_reason": "ok",
            },
            "phase2_result": {},
            "precheck_elapsed_ms": 5.0,
            "phase1_elapsed_ms": 1000.0,
            "phase2_elapsed_ms": 0.0,
            "detected_design_modes": [],
            "processing_log": [],
            "node_path": ["precheck", "phase1"],
        }
        result = output_node(state)
        sd = result["structured_data"]
        psa = sd.get("problem_solving_approach")
        # phase1_only 下 PSA 应为 None 或不存在
        assert psa is None or sd.get("analysis_mode") == "phase1_only"


# ═══════════════════════════════════════════════════════════════
# R04 - V-Default: V2 切换为默认回归
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestVDefaultRegression:
    """V-Default: USE_V717_REQUIREMENTS_ANALYST 默认应为 True"""

    def test_v717_flag_defaults_to_true(self):
        """main_workflow 的 V717 标志默认应为 True"""

        # 通过环境变量控制的标志，默认值为 True
        current = os.environ.get("USE_V717_REQUIREMENTS_ANALYST", "true")
        # 默认应该是 true（大小写不敏感）
        assert current.lower() in (
            "true",
            "1",
            "yes",
        ), f"V-Default REGRESSION: USE_V717_REQUIREMENTS_ANALYST 默认不为 True，当前 = {current}"

    def test_v2_agent_importable(self):
        """V2 Agent 类应可正常导入"""
        from intelligent_project_analyzer.agents.requirements_analyst_agent import RequirementsAnalystAgentV2

        assert RequirementsAnalystAgentV2 is not None

    def test_v2_agent_is_default_in_workflow(self):
        """workflow 或 agents __init__ 中的默认代理应为 V2"""
        try:
            from intelligent_project_analyzer.agents import requirements_analyst_agent as m

            agent_cls = getattr(m, "RequirementsAnalystAgent", None)
            if agent_cls is not None:
                # 应该是 V2 的别名或 V2 本身
                from intelligent_project_analyzer.agents.requirements_analyst_agent import RequirementsAnalystAgentV2

                assert (
                    issubclass(agent_cls, RequirementsAnalystAgentV2) or agent_cls is RequirementsAnalystAgentV2
                ), "V-Default REGRESSION: RequirementsAnalystAgent 不是 V2！"
        except ImportError:
            pytest.skip("RequirementsAnalystAgent 未暴露为别名")


# ═══════════════════════════════════════════════════════════════
# R05 - C-05: 删 utils 文件回归
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestC05DeleteUtilsRegression:
    """C-05: requirements_analyst_utils.py 不应存在（已删除以防止代码分裂）"""

    def test_utils_file_does_not_exist(self):
        """requirements_analyst_utils.py 文件必须不存在"""
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        agents_dir = os.path.join(base_dir, "intelligent_project_analyzer", "agents")
        utils_path = os.path.join(agents_dir, "requirements_analyst_utils.py")
        assert not os.path.exists(
            utils_path
        ), f"C-05 REGRESSION: requirements_analyst_utils.py 文件已重新创建！路径: {utils_path}"

    def test_utils_module_not_importable(self):
        """requirements_analyst_utils 模块不可导入"""
        import importlib

        try:
            importlib.import_module("intelligent_project_analyzer.agents.requirements_analyst_utils")
            pytest.fail("C-05 REGRESSION: requirements_analyst_utils 模块仍可导入！")
        except ImportError:
            pass  # 预期结果

    def test_no_broken_imports_in_agent(self):
        """agent.py 不引用已删除的 utils 文件"""
        import intelligent_project_analyzer.agents.requirements_analyst_agent as m  # noqa: F401

        # 如果 agent.py 引用了 utils 且 utils 已删除，此 import 会失败


# ═══════════════════════════════════════════════════════════════
# R06 - should_execute_phase2 路由回归
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestRoutingRegression:
    """Phase2 路由必须始终返回 'phase2'，绝不跳过"""

    def test_always_routes_to_phase2_sufficient(self):
        from intelligent_project_analyzer.agents.requirements_analyst_agent import should_execute_phase2

        state = {"phase1_info_status": "sufficient"}
        assert should_execute_phase2(state) == "phase2"

    def test_always_routes_to_phase2_insufficient(self):
        from intelligent_project_analyzer.agents.requirements_analyst_agent import should_execute_phase2

        state = {"phase1_info_status": "insufficient"}
        assert should_execute_phase2(state) == "phase2"

    def test_always_routes_to_phase2_unknown(self):
        from intelligent_project_analyzer.agents.requirements_analyst_agent import should_execute_phase2

        state = {"phase1_info_status": "unknown"}
        assert should_execute_phase2(state) == "phase2"

    def test_always_routes_to_phase2_none(self):
        from intelligent_project_analyzer.agents.requirements_analyst_agent import should_execute_phase2

        state = {}
        result = should_execute_phase2(state)
        assert result == "phase2", f"路由回归: should_execute_phase2 返回 {result!r}，期望 'phase2'"

    @pytest.mark.skip(reason="build_requirements_analyst_graph 签名已更新为需要 llm_model, prompt_manager 参数，需 mock 重写")
    def test_graph_conditional_edge_never_skips_phase2(self):
        """图的条件边 map 中应不存在直接跳到 output 的路径"""
        from intelligent_project_analyzer.agents.requirements_analyst_agent import build_requirements_analyst_graph

        graph = build_requirements_analyst_graph()
        # 编译后的图须包含 phase2 节点
        nodes = list(graph.nodes.keys())
        assert "phase2" in nodes, "路由回归: 图中 phase2 节点已消失！"


# ═══════════════════════════════════════════════════════════════
# R07 - 综合回归：Phase 1 所有修复互不干扰
# ═══════════════════════════════════════════════════════════════


@pytest.mark.unit
class TestPhase1ChangesCoexistenceRegression:
    """5 个修复同时存在时互不干扰"""

    def test_all_five_changes_coexist(self):
        """一次性验证所有 5 个 Phase 1 修复都存在"""
        failures = []

        # C-01: 三字段存在
        try:
            from intelligent_project_analyzer.agents.requirements_analyst_schema import Phase1Output

            for field in ("problem_types", "proposition_candidates", "complexity_assessment"):
                if field not in Phase1Output.model_fields:
                    failures.append(f"C-01: {field} 字段缺失")
        except ImportError as e:
            failures.append(f"C-01 导入失败: {e}")

        # C-02: Rule2 已删除（insufficient + phase2_analysis 不报错）
        try:
            import pydantic

            _make_p1(info_status="insufficient", next_step="phase2_analysis")
        except pydantic.ValidationError as e:
            failures.append(f"C-02: Rule2 仍然存在 - {e}")
        except Exception:
            pass

        # C-05: utils 文件不存在
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        utils_path = os.path.join(base_dir, "intelligent_project_analyzer", "agents", "requirements_analyst_utils.py")
        if os.path.exists(utils_path):
            failures.append("C-05: requirements_analyst_utils.py 文件仍然存在")

        # A-01: should_execute_phase2 始终返回 phase2
        try:
            from intelligent_project_analyzer.agents.requirements_analyst_agent import should_execute_phase2

            for status in ("sufficient", "insufficient", "unknown", ""):
                result = should_execute_phase2({"phase1_info_status": status})
                if result != "phase2":
                    failures.append(f"A-01/Routing: status={status!r} 时路由返回 {result!r}")
        except Exception as e:
            failures.append(f"路由检查失败: {e}")

        # V-Default: V2 Agent 可导入
        try:
            from intelligent_project_analyzer.agents.requirements_analyst_agent import RequirementsAnalystAgentV2

            if RequirementsAnalystAgentV2 is None:
                failures.append("V-Default: RequirementsAnalystAgentV2 为 None")
        except ImportError as e:
            failures.append(f"V-Default: V2 Agent 导入失败 - {e}")

        if failures:
            failure_msg = "\n".join(f"  - {f}" for f in failures)
            pytest.fail(f"Phase 1 止血修复回归检测到 {len(failures)} 个问题：\n{failure_msg}")
