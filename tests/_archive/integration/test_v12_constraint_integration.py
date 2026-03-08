"""
v12.0 智能约束识别系统 — 集成测试

测试范围：
I1: 约束管线 + Mock Vision → 约束信封生成完整闭环
I2: project_director.get_task_description 注入约束信封
I3: task_oriented_expert_factory base_system_prompt 包含约束信封
I4: image_generator._generate_structured_prompt 接收 visual_constraints
I5: output_intent_detection_node → interrupt payload 包含 spatial_zones + auto_detected_constraints
I6: output_intent_detection_node → Command.update 包含 visual_constraints + extracted_spatial_zones
"""

import asyncio
import os
import sys
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from typing import Any, Dict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

pytestmark = [pytest.mark.integration]


# ==============================================================================
# 公共工具
# ==============================================================================


def _minimal_state(**kwargs) -> Dict[str, Any]:
    """最小可用 state 字典"""
    from intelligent_project_analyzer.core.state import StateManager

    sm = StateManager()
    state = sm.create_initial_state("150平米三层别墅设计，1楼客厅餐厅，2楼卧室书房", "test-v12-int")
    state.update(
        {
            "agent_results": {
                "requirements_analyst": {
                    "structured_data": {
                        "project_task": "三层别墅设计",
                        "project_overview": "150平米三层别墅",
                        "core_objectives": ["现代简约风格"],
                        "functional_requirements": ["客厅", "餐厅", "卧室"],
                        "constraints": {"budget": "100万"},
                        "confidence_score": 0.85,
                    }
                }
            },
            "structured_requirements": {
                "project_overview": "150平米三层别墅",
                "core_objectives": ["现代简约风格"],
                "functional_requirements": ["客厅", "餐厅", "卧室"],
                "constraints": {"budget": "100万"},
            },
            "detected_design_modes": [],
            "project_type": "personal_residential",
        }
    )
    state.update(kwargs)
    return state


def _state_with_constraints(**kwargs) -> Dict[str, Any]:
    """带已填充 visual_constraints 的 state"""
    state = _minimal_state()
    state["visual_constraints"] = {
        "constraints_by_zone": {
            "overall": [
                {"level": "immutable", "description": "承重墙位于客厅与餐厅之间", "source": "floor_plan"},
                {"level": "baseline", "description": "标准层高2.8m", "source": "floor_plan"},
            ],
            "1f": [
                {"level": "opportunity", "description": "南向采光极佳", "source": "site_photo"},
            ],
        },
        "spatial_topologies": {"overall": {"rooms": 8, "total_area": "150㎡"}},
        "existing_conditions": {"1f": {"doors": 2, "windows": 4}},
        "style_tendencies": {"prefer": ["现代简约"], "avoid": ["欧式古典"]},
        "constraint_envelope": (
            "=== 设计参照系（系统自动识别）===\n"
            "## 整体\n### 🔒 L1 不可变\n- 承重墙位于客厅与餐厅之间\n"
            "### 📐 L2 基准\n- 标准层高2.8m\n"
            "## 1F\n### ✨ L3 机会\n- 南向采光极佳\n"
            "### 风格偏好: 现代简约\n### 倾向避免: 欧式古典\n"
            "=== END ==="
        ),
    }
    state["extracted_spatial_zones"] = [
        {"id": "overall", "label": "整体", "source": "preset"},
        {"id": "1f", "label": "1F", "source": "extracted"},
    ]
    state.update(kwargs)
    return state


# ==============================================================================
# I1: 约束管线完整闭环（mock Vision）
# ==============================================================================


class TestI1ConstraintPipelineWithMockVision:
    """约束管线从图片分类到信封生成的完整闭环"""

    def test_pipeline_with_constraint_source_images(self):
        """I1.1: 有约束源图片时应产出非空 visual_constraints"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            _run_constraint_pipeline,
        )

        # 构造含约束源图片的 state
        state = _minimal_state()
        state["uploaded_visual_references"] = [
            {
                "file_path": "/tmp/floor_plan.png",
                "structured_features": {
                    "image_type": "constraint_source",
                    "image_subtype": "floor_plan",
                    "spatial_zone_guess": "1F",
                    "style_keywords": [],
                },
            },
        ]
        state["extracted_spatial_zones"] = [
            {"id": "overall", "label": "整体", "source": "preset"},
            {"id": "1f", "label": "1F", "source": "extracted"},
        ]

        # Mock ConstraintSourceExtractor 使其不真正调 Vision API
        mock_result = {
            "spatial_zone": "1F",
            "constraints": [
                {"level": "immutable", "description": "承重墙在中部", "source": "floor_plan"},
                {"level": "baseline", "description": "层高2.8m", "source": "floor_plan"},
            ],
            "spatial_topology": {"rooms": 5},
            "existing_conditions": None,
        }

        with patch("intelligent_project_analyzer.services.file_processor.ConstraintSourceExtractor") as MockCls:
            mock_extractor = MagicMock()
            mock_extractor.extract_constraint_source_details = AsyncMock(return_value=mock_result)
            MockCls.return_value = mock_extractor

            result = asyncio.run(_run_constraint_pipeline(state))

        assert result is not None
        assert "constraints_by_zone" in result
        assert "constraint_envelope" in result
        assert len(result["constraints_by_zone"].get("1F", [])) == 2
        assert "承重墙" in result["constraint_envelope"]

    def test_pipeline_with_style_reference_only(self):
        """I1.2: 仅有风格参考图时应产出 style_tendencies"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            _run_constraint_pipeline,
        )

        state = _minimal_state()
        state["uploaded_visual_references"] = [
            {
                "file_path": "/tmp/style_ref.jpg",
                "structured_features": {
                    "image_type": "style_reference",
                    "image_subtype": "style_reference",
                    "spatial_zone_guess": "整体",
                    "style_keywords": ["侘寂风", "木质纹理", "暖色调"],
                },
            },
        ]
        state["extracted_spatial_zones"] = [{"id": "overall", "label": "整体", "source": "preset"}]

        # style_reference 不触发 ConstraintSourceExtractor，直接汇总 style_keywords
        with patch("intelligent_project_analyzer.services.file_processor.ConstraintSourceExtractor") as MockCls:
            mock_extractor = MagicMock()
            mock_extractor.extract_constraint_source_details = AsyncMock(
                return_value={
                    "spatial_zone": "整体",
                    "constraints": [],
                    "spatial_topology": None,
                    "existing_conditions": None,
                }
            )
            MockCls.return_value = mock_extractor

            result = asyncio.run(_run_constraint_pipeline(state))

        assert result is not None
        assert "style_tendencies" in result
        assert "侘寂风" in result["style_tendencies"]["prefer"]


# ==============================================================================
# I2: project_director 约束信封注入
# ==============================================================================


class TestI2ProjectDirectorConstraintInjection:
    """project_director.get_task_description 是否正确注入约束信封"""

    def test_constraint_envelope_appears_in_task_description(self):
        """I2.1: 有约束信封时，task_description 应包含信封内容"""
        from intelligent_project_analyzer.agents.project_director import ProjectDirectorAgent

        state = _state_with_constraints()
        pd = ProjectDirectorAgent.__new__(ProjectDirectorAgent)
        pd._build_feasibility_context = MagicMock(return_value="")

        desc = pd.get_task_description(state)
        assert "设计参照系" in desc
        assert "承重墙" in desc
        assert "L1 不可变" in desc

    def test_no_constraint_envelope_no_injection(self):
        """I2.2: 无约束信封时，task_description 不包含设计参照系"""
        from intelligent_project_analyzer.agents.project_director import ProjectDirectorAgent

        state = _minimal_state()  # visual_constraints = None
        pd = ProjectDirectorAgent.__new__(ProjectDirectorAgent)
        pd._build_feasibility_context = MagicMock(return_value="")

        desc = pd.get_task_description(state)
        assert "设计参照系" not in desc


# ==============================================================================
# I3: image_generator 约束注入
# ==============================================================================


class TestI3ImageGeneratorConstraintInjection:
    """image_generator._generate_structured_prompt 是否接收 visual_constraints"""

    def test_generate_structured_prompt_signature_has_visual_constraints(self):
        """I3.1: _generate_structured_prompt 签名包含 visual_constraints 参数"""
        from intelligent_project_analyzer.services.image_generator import ImageGeneratorService
        import inspect

        sig = inspect.signature(ImageGeneratorService._generate_structured_prompt)
        param_names = list(sig.parameters.keys())
        assert "visual_constraints" in param_names

    def test_generate_deliverable_image_signature_has_visual_constraints(self):
        """I3.2: generate_deliverable_image 签名包含 visual_constraints 参数"""
        from intelligent_project_analyzer.services.image_generator import ImageGeneratorService
        import inspect

        sig = inspect.signature(ImageGeneratorService.generate_deliverable_image)
        param_names = list(sig.parameters.keys())
        assert "visual_constraints" in param_names


# ==============================================================================
# I4: output_intent_detection_node 空间区域提取 + 信封传播
# ==============================================================================


class TestI4OutputIntentDetectionZoneExtraction:
    """output_intent_detection_node 中空间区域提取和约束传播集成测试"""

    def test_spatial_zones_extracted_from_user_input(self):
        """I4.1: 节点应从 user_input 中提取空间区域"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            _extract_spatial_zones,
        )

        sr = {
            "project_task": "三层别墅设计",
            "spatial_description": {"zones": ["影音室"]},
        }
        zones = _extract_spatial_zones(sr, "三层别墅，1楼客厅，2楼主卧，地下室车库")
        ids = {z["id"] for z in zones}
        assert "1f" in ids
        assert "2f" in ids
        assert "basement" in ids
        assert "living_room" in ids or "garage" in ids

    def test_constraint_envelope_flows_to_command_update(self):
        """I4.2: 约束应最终出现在 Command.update 中（mock interrupt）"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            output_intent_detection_node,
        )

        state = _state_with_constraints()
        state["active_projections"] = None
        state["intent_changed"] = False

        # Mock interrupt 返回用户选择
        with patch(
            "intelligent_project_analyzer.interaction.nodes.output_intent_detection.interrupt",
            return_value={"selected_deliveries": ["design_professional"], "selected_modes": []},
        ):
            # Mock 约束管线（已在 state 中预设约束数据）
            with patch(
                "intelligent_project_analyzer.interaction.nodes.output_intent_detection._run_constraint_pipeline",
                new=AsyncMock(return_value=state["visual_constraints"]),
            ):
                cmd = output_intent_detection_node(state)

        from langgraph.types import Command

        assert isinstance(cmd, Command)
        assert cmd.update.get("visual_constraints") is not None
        assert cmd.update.get("extracted_spatial_zones") is not None
        assert "constraint_envelope" in (cmd.update.get("visual_constraints") or {})
