"""
v8.0 雷达图维度生成 - 集成测试

覆盖：
- ProjectSpecificDimensionGenerator 与 step3_radar 的集成
- _skip_legacy 旗标正确控制传统流程跳过
- 降级路径（LLM 失败 → 传统选择）
- state 更新字段含 dimension_generation_method
- interrupt payload 含 dimension_layers / generation_summary
- 环境变量开关（USE_PROJECT_SPECIFIC_DIMENSIONS=false 时走传统路径）
"""

import json
import os
from typing import Any, Dict, List
from unittest.mock import patch

import pytest

# ==============================================================================
# 公共工具
# ==============================================================================


def _make_state(
    user_input: str = "测试项目",
    project_type: str = "personal_residential",
    confirmed_tasks: List[str] = None,
    step: int = 0,
    radar_values: dict = None,
) -> Dict[str, Any]:
    """构造最小可用 ProjectAnalysisState 字典"""
    return {
        "user_input": user_input,
        "project_type": project_type,
        "confirmed_core_tasks": confirmed_tasks or [],
        "agent_results": {
            "requirements_analyst": {
                "structured_data": {
                    "project_task": user_input,
                    "confidence_score": 0.65,
                    "character_narrative": "测试用户",
                    "core_tensions": "",
                    "stakeholder_system": "",
                    "uncertainty_map": {},
                }
            }
        },
        "progressive_questionnaire_step": step,
        "radar_dimension_values": radar_values or {},
        "special_scene_metadata": None,
    }


def _make_valid_dims(count: int = 7) -> List[Dict]:
    """生成 count 个能通过验证的维度"""
    categories = ["calibration", "decision", "insight"]
    dims = []
    for i in range(count):
        cat = categories[i % 3]
        val = 35 if cat == "calibration" else 50
        dims.append(
            {
                "id": f"integ_dim_{i:03d}",
                "name": f"集成维度{i}",
                "left_label": f"左{i}",
                "right_label": f"右{i}",
                "description": f"集成测试维度{i}",
                "default_value": val,
                "category": cat,
                "source": cat,
                "rationale": f"理由{i}",
                "impact_hint": f"影响{i}",
                "global_impact": True,
            }
        )
    return dims


# ==============================================================================
# [1] v8.0 路径 - ProjectSpecificDimensionGenerator 成功
# ==============================================================================


class TestV8PathSuccess:
    """USE_PROJECT_SPECIFIC=true 且 LLM 返回足够维度时的集成行为"""

    @patch.dict(os.environ, {"USE_PROJECT_SPECIFIC_DIMENSIONS": "true"})
    @patch(
        "intelligent_project_analyzer.services.project_specific_dimension_generator."
        "ProjectSpecificDimensionGenerator._call_llm"
    )
    @patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
    def test_skip_legacy_when_ps_succeeds(self, mock_interrupt, mock_llm):
        """v8.0 成功时应调用 interrupt，生成方法应为 project_specific"""
        dims = _make_valid_dims(7)
        mock_llm.return_value = f"```json\n{json.dumps(dims, ensure_ascii=False)}\n```"

        # interrupt 返回模拟用户输入
        mock_interrupt.return_value = {"values": {d["id"]: d["default_value"] for d in dims}}

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            ProgressiveQuestionnaireNode,
        )

        state = _make_state()
        cmd = ProgressiveQuestionnaireNode.step2_radar(state)

        # 验证 v8.0 路径成功执行
        assert mock_interrupt.called
        payload = mock_interrupt.call_args[0][0]
        assert "dimensions" in payload
        assert len(payload["dimensions"]) >= 5
        # 生成方法应标识为 project_specific
        assert payload.get("dimension_generation_method") == "project_specific"
        # Command update 也应含此字段
        assert cmd.update.get("dimension_generation_method") == "project_specific"

    @patch.dict(os.environ, {"USE_PROJECT_SPECIFIC_DIMENSIONS": "true"})
    @patch(
        "intelligent_project_analyzer.services.project_specific_dimension_generator."
        "ProjectSpecificDimensionGenerator._call_llm"
    )
    @patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
    def test_payload_contains_v8_metadata(self, mock_interrupt, mock_llm):
        """interrupt payload 应含 dimension_generation_method / dimension_layers / generation_summary"""
        dims = _make_valid_dims(7)
        mock_llm.return_value = f"```json\n{json.dumps(dims, ensure_ascii=False)}\n```"
        mock_interrupt.return_value = {"values": {d["id"]: d["default_value"] for d in dims}}

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            ProgressiveQuestionnaireNode,
        )

        ProgressiveQuestionnaireNode.step2_radar(_make_state())

        payload = mock_interrupt.call_args[0][0]
        assert "dimension_generation_method" in payload
        assert payload["dimension_generation_method"] == "project_specific"
        assert "dimension_layers" in payload
        assert isinstance(payload["dimension_layers"], dict)
        assert "generation_summary" in payload

    @patch.dict(os.environ, {"USE_PROJECT_SPECIFIC_DIMENSIONS": "true"})
    @patch(
        "intelligent_project_analyzer.services.project_specific_dimension_generator."
        "ProjectSpecificDimensionGenerator._call_llm"
    )
    @patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
    def test_state_update_contains_dimension_generation_method(self, mock_interrupt, mock_llm):
        """返回的 Command update 应含 dimension_generation_method = 'project_specific'"""
        dims = _make_valid_dims(7)
        mock_llm.return_value = f"```json\n{json.dumps(dims, ensure_ascii=False)}\n```"
        mock_interrupt.return_value = {"values": {d["id"]: d["default_value"] for d in dims}}

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            ProgressiveQuestionnaireNode,
        )

        cmd = ProgressiveQuestionnaireNode.step2_radar(_make_state())

        update = cmd.update
        assert "dimension_generation_method" in update
        assert update["dimension_generation_method"] == "project_specific"
        assert "selected_radar_dimensions" in update
        assert "radar_dimension_values" in update

    @patch.dict(os.environ, {"USE_PROJECT_SPECIFIC_DIMENSIONS": "true"})
    @patch(
        "intelligent_project_analyzer.services.project_specific_dimension_generator."
        "ProjectSpecificDimensionGenerator._call_llm"
    )
    @patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
    def test_dimension_layers_grouped_by_category(self, mock_interrupt, mock_llm):
        """dimension_layers 应按类别分组，每组至少有1个维度"""
        dims = _make_valid_dims(7)
        mock_llm.return_value = f"```json\n{json.dumps(dims, ensure_ascii=False)}\n```"
        mock_interrupt.return_value = {"values": {d["id"]: d["default_value"] for d in dims}}

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            ProgressiveQuestionnaireNode,
        )

        ProgressiveQuestionnaireNode.step2_radar(_make_state())

        payload = mock_interrupt.call_args[0][0]
        layers = payload["dimension_layers"]
        # 7个维度分3类：应有 calibration/decision/insight
        for cat in ("calibration", "decision", "insight"):
            assert cat in layers, f"缺少类别 '{cat}'"
            assert len(layers[cat]) >= 1


# ==============================================================================
# [2] 降级路径 - LLM 失败
# ==============================================================================


class TestV8FallbackPath:
    """LLM 失败时应自动降级到传统维度选择"""

    @patch.dict(
        os.environ,
        {
            "USE_PROJECT_SPECIFIC_DIMENSIONS": "true",
            "ENABLE_DIMENSION_LEARNING": "false",
            "USE_DYNAMIC_GENERATION": "false",
            "FORCE_GENERATE_DIMENSIONS": "false",
        },
    )
    @patch(
        "intelligent_project_analyzer.services.project_specific_dimension_generator."
        "ProjectSpecificDimensionGenerator._call_llm"
    )
    @patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
    def test_fallback_on_llm_exception(self, mock_interrupt, mock_llm):
        """LLM 抛出异常时流程应完成（降级到静态）"""
        mock_llm.side_effect = RuntimeError("API 超时")
        mock_interrupt.return_value = {"values": {}}

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            ProgressiveQuestionnaireNode,
        )

        # 不应抛出异常
        cmd = ProgressiveQuestionnaireNode.step2_radar(_make_state())
        assert cmd is not None
        assert mock_interrupt.called

    @patch.dict(
        os.environ,
        {
            "USE_PROJECT_SPECIFIC_DIMENSIONS": "true",
            "ENABLE_DIMENSION_LEARNING": "false",
            "USE_DYNAMIC_GENERATION": "false",
            "FORCE_GENERATE_DIMENSIONS": "false",
        },
    )
    @patch(
        "intelligent_project_analyzer.services.project_specific_dimension_generator."
        "ProjectSpecificDimensionGenerator._call_llm"
    )
    @patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
    def test_fallback_on_too_few_dims(self, mock_interrupt, mock_llm):
        """LLM 返回维度不足5个时应降级，状态更新 dimension_generation_method='static'"""
        few_dims = _make_valid_dims(3)  # < 5
        mock_llm.return_value = f"```json\n{json.dumps(few_dims, ensure_ascii=False)}\n```"
        mock_interrupt.return_value = {"values": {}}

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            ProgressiveQuestionnaireNode,
        )

        cmd = ProgressiveQuestionnaireNode.step2_radar(_make_state())
        update = cmd.update
        assert update.get("dimension_generation_method") == "static"


# ==============================================================================
# [3] 环境变量开关
# ==============================================================================


class TestEnvVarSwitch:
    """USE_PROJECT_SPECIFIC_DIMENSIONS=false 时应完全走传统路径"""

    @patch.dict(
        os.environ,
        {
            "USE_PROJECT_SPECIFIC_DIMENSIONS": "false",
            "ENABLE_DIMENSION_LEARNING": "false",
            "USE_DYNAMIC_GENERATION": "false",
            "FORCE_GENERATE_DIMENSIONS": "false",
        },
    )
    @patch(
        "intelligent_project_analyzer.services.project_specific_dimension_generator."
        "ProjectSpecificDimensionGenerator.generate_dimensions"
    )
    @patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
    def test_ps_generator_not_called_when_disabled(self, mock_interrupt, mock_ps_gen):
        """关闭开关后 ProjectSpecificDimensionGenerator 不应被调用"""
        mock_interrupt.return_value = {"values": {}}

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            ProgressiveQuestionnaireNode,
        )

        ProgressiveQuestionnaireNode.step2_radar(_make_state())
        mock_ps_gen.assert_not_called()

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
    def test_static_method_used_as_default(self, mock_interrupt):
        """关闭后 dimension_generation_method 应为 'static'"""
        mock_interrupt.return_value = {"values": {}}

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            ProgressiveQuestionnaireNode,
        )

        cmd = ProgressiveQuestionnaireNode.step2_radar(_make_state())
        assert cmd.update.get("dimension_generation_method") == "static"


# ==============================================================================
# [4] 路由目标验证
# ==============================================================================


class TestRouting:
    """step3_radar 完成后路由目标应为 progressive_step2_info_gather"""

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
    def test_routes_to_gap_filling(self, mock_interrupt):
        """完成后应路由到 questionnaire_summary（step3_radar 是最后一步）"""
        mock_interrupt.return_value = {"values": {}}

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            ProgressiveQuestionnaireNode,
        )

        cmd = ProgressiveQuestionnaireNode.step2_radar(_make_state())
        assert cmd.goto == "questionnaire_summary"

    @patch.dict(
        os.environ,
        {
            "USE_PROJECT_SPECIFIC_DIMENSIONS": "true",
            "ENABLE_DIMENSION_LEARNING": "false",
            "USE_DYNAMIC_GENERATION": "false",
        },
    )
    @patch(
        "intelligent_project_analyzer.services.project_specific_dimension_generator."
        "ProjectSpecificDimensionGenerator._call_llm"
    )
    @patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
    def test_routes_to_gap_filling_v8_path(self, mock_interrupt, mock_llm):
        """v8.0 路径也应路由到 questionnaire_summary（step3_radar 是最后一步）"""
        dims = _make_valid_dims(7)
        mock_llm.return_value = f"```json\n{json.dumps(dims, ensure_ascii=False)}\n```"
        mock_interrupt.return_value = {"values": {d["id"]: d["default_value"] for d in dims}}

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            ProgressiveQuestionnaireNode,
        )

        cmd = ProgressiveQuestionnaireNode.step2_radar(_make_state())
        assert cmd.goto == "questionnaire_summary"

    @patch.dict(os.environ, {"USE_PROJECT_SPECIFIC_DIMENSIONS": "false"})
    def test_skip_if_already_completed(self):
        """step 已 >= 2 且已有值时应路由到 questionnaire_summary（跳过重复执行）"""
        state = _make_state(step=2, radar_values={"dim_a": 50})

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            ProgressiveQuestionnaireNode,
        )

        cmd = ProgressiveQuestionnaireNode.step2_radar(state)
        assert cmd.goto == "questionnaire_summary"


# ==============================================================================
# [5] dimension_generation_method 持久化到 state
# ==============================================================================


class TestStatePersistence:
    """确保 dimension_generation_method 正确写入 state update dict"""

    @patch.dict(
        os.environ,
        {
            "USE_PROJECT_SPECIFIC_DIMENSIONS": "true",
            "USE_DYNAMIC_GENERATION": "false",
            "ENABLE_DIMENSION_LEARNING": "false",
        },
    )
    @patch(
        "intelligent_project_analyzer.services.project_specific_dimension_generator."
        "ProjectSpecificDimensionGenerator._call_llm"
    )
    @patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
    def test_update_dict_fields_complete(self, mock_interrupt, mock_llm):
        """state update 应含所有必要字段"""
        dims = _make_valid_dims(7)
        mock_llm.return_value = f"```json\n{json.dumps(dims, ensure_ascii=False)}\n```"
        mock_interrupt.return_value = {"values": {d["id"]: d["default_value"] for d in dims}}

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            ProgressiveQuestionnaireNode,
        )

        cmd = ProgressiveQuestionnaireNode.step2_radar(_make_state())
        update = cmd.update

        required_fields = [
            "selected_radar_dimensions",
            "selected_dimensions",
            "radar_dimension_values",
            "radar_analysis_summary",
            "progressive_questionnaire_step",
            "dimension_generation_method",
        ]
        for field in required_fields:
            assert field in update, f"update dict 缺少字段: {field}"


pytestmark = [pytest.mark.integration]
