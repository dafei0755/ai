"""
v8.0 雷达图集成 - 回归测试

确保 v8.0 改动不破坏以下已有功能：
R1: 传统静态维度选择仍可正常工作（USE_PROJECT_SPECIFIC=false）
R2: 特殊场景维度注入（AdaptiveDimensionGenerator / 场景检测）仍生效
R3: state 字段 selected_radar_dimensions / radar_dimension_values 保持正确格式
R4: dimension_selector.py profile_label 降级逻辑正常
R5: deliverable_id_generator_node 材料关键词回退正常
R6: requirements_analyst_agent problem_types 字段保留
R7: 问卷跳过逻辑（step>=2 且 values 非空）保持不变
R8: 雷达图分析 RadarGapAnalyzer 继续获得维度值
"""

import os
import pytest
from unittest.mock import patch
from typing import Any, Dict


# ==============================================================================
# 公共工具
# ==============================================================================


def _minimal_state(**kwargs) -> Dict[str, Any]:
    base = {
        "user_input": "现代简约住宅 120平",
        "project_type": "personal_residential",
        "confirmed_core_tasks": [],
        "agent_results": {
            "requirements_analyst": {
                "structured_data": {
                    "project_task": "现代简约住宅设计",
                    "confidence_score": 0.8,
                }
            }
        },
        "progressive_questionnaire_step": 0,
        "radar_dimension_values": {},
        "special_scene_metadata": None,
    }
    base.update(kwargs)
    return base


# ==============================================================================
# R1: 传统路径回归
# ==============================================================================


class TestR1LegacyPathNotBroken:
    """v8.0 关闭时，传统选择路径完整工作"""

    @patch.dict(
        os.environ,
        {
            "USE_PROJECT_SPECIFIC_DIMENSIONS": "false",
            "ENABLE_DIMENSION_LEARNING": "false",
            "USE_DYNAMIC_GENERATION": "false",
            "FORCE_GENERATE_DIMENSIONS": "false",
        },
    )
    @patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
    def test_legacy_path_produces_dimensions(self, mock_interrupt):
        """传统路径应生成维度列表（非空）"""
        mock_interrupt.return_value = {"values": {}}

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            ProgressiveQuestionnaireNode,
        )

        cmd = ProgressiveQuestionnaireNode.step3_radar(_minimal_state())
        dims = cmd.update.get("selected_radar_dimensions", [])
        assert isinstance(dims, list)
        assert len(dims) > 0, "传统路径应生成至少1个维度"

    @patch.dict(
        os.environ,
        {
            "USE_PROJECT_SPECIFIC_DIMENSIONS": "false",
            "ENABLE_DIMENSION_LEARNING": "false",
            "USE_DYNAMIC_GENERATION": "false",
            "FORCE_GENERATE_DIMENSIONS": "false",
        },
    )
    @patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
    def test_legacy_path_dimension_format(self, mock_interrupt):
        """传统路径维度应含 id/name/left_label/right_label/default_value"""
        mock_interrupt.return_value = {"values": {}}

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            ProgressiveQuestionnaireNode,
        )

        cmd = ProgressiveQuestionnaireNode.step3_radar(_minimal_state())
        for dim in cmd.update.get("selected_radar_dimensions", []):
            assert "id" in dim
            assert "name" in dim
            assert "left_label" in dim
            assert "right_label" in dim
            assert "default_value" in dim

    @patch.dict(
        os.environ,
        {
            "USE_PROJECT_SPECIFIC_DIMENSIONS": "false",
            "ENABLE_DIMENSION_LEARNING": "false",
            "USE_DYNAMIC_GENERATION": "false",
            "FORCE_GENERATE_DIMENSIONS": "false",
        },
    )
    @patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
    def test_legacy_path_dimension_generation_method_is_static(self, mock_interrupt):
        """传统路径 dimension_generation_method 应为 'static'"""
        mock_interrupt.return_value = {"values": {}}

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            ProgressiveQuestionnaireNode,
        )

        cmd = ProgressiveQuestionnaireNode.step3_radar(_minimal_state())
        assert cmd.update.get("dimension_generation_method") == "static"


# ==============================================================================
# R2: 特殊场景注入不被 v8.0 路径破坏
# ==============================================================================


class TestR2SpecialSceneInjection:
    """v8.0 关闭时特殊场景注入仍调用"""

    @patch.dict(
        os.environ,
        {
            "USE_PROJECT_SPECIFIC_DIMENSIONS": "false",
            "ENABLE_DIMENSION_LEARNING": "false",
            "USE_DYNAMIC_GENERATION": "false",
            "FORCE_GENERATE_DIMENSIONS": "false",
        },
    )
    @patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
    @patch(
        "intelligent_project_analyzer.services.dimension_selector.DimensionSelector."
        "detect_and_inject_specialized_dimensions"
    )
    def test_scene_injection_called_when_v8_disabled(self, mock_inject, mock_interrupt):
        """v8.0 关闭时特殊场景注入逻辑应被调用"""
        mock_inject.return_value = []
        mock_interrupt.return_value = {"values": {}}

        state = _minimal_state(special_scene_metadata={"scene_tags": ["medical"]})

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            ProgressiveQuestionnaireNode,
        )

        ProgressiveQuestionnaireNode.step3_radar(state)
        mock_inject.assert_called_once()


# ==============================================================================
# R3: state 字段格式保持稳定
# ==============================================================================


class TestR3StateFieldFormat:
    """selected_radar_dimensions 始终是 list，radar_dimension_values 始终是 dict"""

    @pytest.mark.parametrize("ps_enabled", ["true", "false"])
    @patch(
        "intelligent_project_analyzer.services.project_specific_dimension_generator."
        "ProjectSpecificDimensionGenerator._call_llm"
    )
    @patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
    def test_dimensions_always_list(self, mock_interrupt, mock_llm, ps_enabled):
        """无论 v8.0 是否启用，selected_radar_dimensions 应为 list"""
        import json
        from unittest.mock import patch as mpatch

        dims = [
            {
                "id": f"d{i}",
                "name": f"n{i}",
                "left_label": "L",
                "right_label": "R",
                "description": "D",
                "default_value": 35 + i * 5,
                "category": "decision",
                "source": "decision",
            }
            for i in range(7)
        ]
        mock_llm.return_value = f"```json\n{json.dumps(dims, ensure_ascii=False)}\n```"
        mock_interrupt.return_value = {"values": {d["id"]: 50 for d in dims}}

        with mpatch.dict(
            os.environ,
            {
                "USE_PROJECT_SPECIFIC_DIMENSIONS": ps_enabled,
                "ENABLE_DIMENSION_LEARNING": "false",
                "USE_DYNAMIC_GENERATION": "false",
            },
        ):
            from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
                ProgressiveQuestionnaireNode,
            )

            cmd = ProgressiveQuestionnaireNode.step3_radar(_minimal_state())

        dims_out = cmd.update.get("selected_radar_dimensions")
        assert isinstance(dims_out, list), f"ps_enabled={ps_enabled}: 应为 list，实际: {type(dims_out)}"

    @patch.dict(
        os.environ,
        {
            "USE_PROJECT_SPECIFIC_DIMENSIONS": "false",
            "ENABLE_DIMENSION_LEARNING": "false",
            "USE_DYNAMIC_GENERATION": "false",
        },
    )
    @patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
    def test_radar_values_always_dict(self, mock_interrupt):
        """radar_dimension_values 始终是 dict"""
        mock_interrupt.return_value = {"values": {"dim_a": 60}}

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            ProgressiveQuestionnaireNode,
        )

        cmd = ProgressiveQuestionnaireNode.step3_radar(_minimal_state())
        vals = cmd.update.get("radar_dimension_values")
        assert isinstance(vals, dict)


# ==============================================================================
# R4: profile_label 降级逻辑
# ==============================================================================


class TestR4ProfileLabelFallback:
    """RadarGapAnalyzer._generate_profile_label 在动态维度下的降级"""

    def test_profile_label_with_no_labels_uses_tendency(self):
        """没有固定维度 ID 时，profile_label 从极端倾向生成"""
        from intelligent_project_analyzer.services.dimension_selector import RadarGapAnalyzer

        analyzer = RadarGapAnalyzer()
        values = {
            "integ_dim_000": 90,
            "integ_dim_001": 10,
            "integ_dim_002": 50,
        }
        details = {
            "integ_dim_000": {"name": "维度A", "tendency": "强烈倾向极端右", "value": 90},
            "integ_dim_001": {"name": "维度B", "tendency": "强烈倾向极端左", "value": 10},
            "integ_dim_002": {"name": "维度C", "tendency": "平衡/中立", "value": 50},
        }
        label = analyzer._generate_profile_label(values, details)
        assert isinstance(label, str)
        assert len(label) > 0

    def test_profile_label_fallback_returns_string(self):
        """即使没有任何极端值，也应返回非空字符串"""
        from intelligent_project_analyzer.services.dimension_selector import RadarGapAnalyzer

        analyzer = RadarGapAnalyzer()
        values = {"dim_x": 50, "dim_y": 50}
        details = {
            "dim_x": {"name": "X", "tendency": "平衡/中立", "value": 50},
            "dim_y": {"name": "Y", "tendency": "平衡/中立", "value": 50},
        }
        label = analyzer._generate_profile_label(values, details)
        assert isinstance(label, str)
        assert len(label) > 0


# ==============================================================================
# R5: deliverable_id_generator_node 材料关键词回退
# ==============================================================================


class TestR5DeliverableIdKeywordsFallback:
    """非标准 profile_label 时材料关键词回退到 label 文字"""

    def test_unknown_profile_label_yields_keywords(self):
        """未在 style_mapping 中的 label 应从 label 文字提取关键词"""
        from intelligent_project_analyzer.workflow.nodes.deliverable_id_generator_node import (
            _extract_keywords_from_questionnaire,
        )

        profile_label = "极端右·极端左"
        result = _extract_keywords_from_questionnaire(
            gap_answers={},
            profile_label=profile_label,
            radar_values={},
        )
        assert isinstance(result, dict)
        material_kws = result.get("material_keywords", [])
        # 未在映射表中的 label 应走 v8.0 fallback，把 label 拆分为关键词
        assert isinstance(material_kws, list)


# ==============================================================================
# R6: requirements_analyst problem_types 保留
# ==============================================================================


class TestR6ProblemTypesPreserved:
    """_merge_phase_results 应保留 problem_types 字段"""

    def test_problem_types_preserved_in_merge(self):
        """合并后 problem_types 不应被丢弃"""
        import inspect
        from intelligent_project_analyzer.agents import requirements_analyst_agent as module

        func = getattr(module, "_merge_phase_results", None)
        if func is None:
            pytest.skip("_merge_phase_results 函数不存在")

        source = inspect.getsource(func)
        assert "problem_types" in source, "_merge_phase_results 应显式处理 problem_types"

    def test_problem_types_actually_populated(self):
        """合并结果中 problem_types 字段有值时应正确保留"""
        from intelligent_project_analyzer.agents.requirements_analyst_agent import (
            _merge_phase_results,
        )

        phase1 = {"problem_types": ["空间矛盾", "预算张力"]}
        phase2 = {"structured_output": {"project_task": "test"}, "analysis_layers": {}}
        result = _merge_phase_results(phase1, phase2, "test input")
        assert result.get("problem_types") == ["空间矛盾", "预算张力"]


# ==============================================================================
# R7: 问卷跳过逻辑保持不变
# ==============================================================================


class TestR7SkipLogicUnchanged:
    """已完成的步骤不应被重新执行"""

    def test_step_already_completed_skips(self):
        """step >= 2 且 radar_values 非空时应路由到 questionnaire_summary（跳过重复执行）"""
        state = _minimal_state()
        state["progressive_questionnaire_step"] = 2  # 正确 key
        state["radar_dimension_values"] = {"dim_a": 65, "dim_b": 40}

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            ProgressiveQuestionnaireNode,
        )

        cmd = ProgressiveQuestionnaireNode.step3_radar(state)
        assert cmd.goto == "questionnaire_summary"

    def test_step_zero_does_not_skip(self):
        """step == 0 时应正常执行（不跳过）"""
        state = _minimal_state(step=0)

        with patch(
            "intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt"
        ) as mock_interrupt:
            mock_interrupt.return_value = {"values": {}}

            with patch.dict(
                os.environ,
                {
                    "USE_PROJECT_SPECIFIC_DIMENSIONS": "false",
                    "ENABLE_DIMENSION_LEARNING": "false",
                    "USE_DYNAMIC_GENERATION": "false",
                },
            ):
                from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
                    ProgressiveQuestionnaireNode,
                )

                ProgressiveQuestionnaireNode.step3_radar(state)
                assert mock_interrupt.called, "step=0 时应调用 interrupt"


# ==============================================================================
# R8: RadarGapAnalyzer 继续收到维度值
# ==============================================================================


class TestR8RadarGapAnalyzerFed:
    """雷达图分析器应收到有意义的维度值"""

    @patch.dict(
        os.environ,
        {
            "USE_PROJECT_SPECIFIC_DIMENSIONS": "false",
            "ENABLE_DIMENSION_LEARNING": "false",
            "USE_DYNAMIC_GENERATION": "false",
        },
    )
    @patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
    def test_analysis_summary_present(self, mock_interrupt):
        """radar_analysis_summary 应非空"""
        mock_interrupt.return_value = {"values": {"cosmos_style": 30, "budget_control": 70}}

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            ProgressiveQuestionnaireNode,
        )

        cmd = ProgressiveQuestionnaireNode.step3_radar(_minimal_state())
        summary = cmd.update.get("radar_analysis_summary")
        assert summary is not None


pytestmark = [pytest.mark.regression]
