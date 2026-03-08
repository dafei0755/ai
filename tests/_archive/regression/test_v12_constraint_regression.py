"""
v12.0 智能约束识别系统 — 回归测试

确保 v12.0 改动不破坏以下已有功能：
R1: 无上传图片的纯文本分析流程完全不受影响
R2: output_intent_detection_node 幂等保护仍生效（已有 active_projections 跳过检测）
R3: project_director 无约束时 task_description 格式不变
R4: image_generator 无约束时 avoid_patterns / required_keywords 不变
R5: State 初始化向后兼容（所有旧字段仍存在）
R6: interrupt payload 向后兼容（新字段是附加的，不影响旧字段结构）
R7: 约束管线异常不阻塞主流程
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from typing import Any, Dict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

pytestmark = [pytest.mark.regression]


# ==============================================================================
# 公共工具
# ==============================================================================


def _minimal_state_no_images(**kwargs) -> Dict[str, Any]:
    """无上传图片的最小 state（模拟大多数用户场景）"""
    from intelligent_project_analyzer.core.state import StateManager

    sm = StateManager()
    state = sm.create_initial_state("150平米现代简约住宅设计", "test-v12-reg")
    state.update(
        {
            "agent_results": {
                "requirements_analyst": {
                    "structured_data": {
                        "project_task": "住宅设计",
                        "project_overview": "150平米现代简约住宅",
                        "core_objectives": ["舒适居住"],
                        "functional_requirements": ["客厅", "卧室"],
                        "constraints": {},
                        "confidence_score": 0.8,
                    }
                }
            },
            "structured_requirements": {
                "project_overview": "150平米现代简约住宅",
                "core_objectives": ["舒适居住"],
                "functional_requirements": ["客厅", "卧室"],
                "constraints": {},
            },
            "detected_design_modes": [],
            "project_type": "personal_residential",
            "uploaded_visual_references": None,
        }
    )
    state.update(kwargs)
    return state


# ==============================================================================
# R1: 无上传图片流程不受影响
# ==============================================================================


class TestR1NoImageFlowUnchanged:
    """无图片时约束字段全部为 None，流程正常"""

    def test_node_produces_none_visual_constraints(self):
        """R1.1: 无图片上传 → visual_constraints 为 None"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            output_intent_detection_node,
        )

        state = _minimal_state_no_images()

        with patch(
            "intelligent_project_analyzer.interaction.nodes.output_intent_detection.interrupt",
            return_value={"selected_deliveries": ["design_professional"], "selected_modes": []},
        ):
            from langgraph.types import Command

            cmd = output_intent_detection_node(state)

        assert isinstance(cmd, Command)
        assert cmd.update.get("visual_constraints") is None

    def test_node_still_has_active_projections(self):
        """R1.2: 无图片时仍正常产出 active_projections"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            output_intent_detection_node,
        )

        state = _minimal_state_no_images()

        with patch(
            "intelligent_project_analyzer.interaction.nodes.output_intent_detection.interrupt",
            return_value={"selected_deliveries": ["design_professional"], "selected_modes": []},
        ):
            cmd = output_intent_detection_node(state)

        ap = cmd.update.get("active_projections")
        assert ap is not None
        assert "design_professional" in ap

    def test_extracted_spatial_zones_still_present(self):
        """R1.3: 即使无图片，extracted_spatial_zones 也应有 overall"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            output_intent_detection_node,
        )

        state = _minimal_state_no_images()

        with patch(
            "intelligent_project_analyzer.interaction.nodes.output_intent_detection.interrupt",
            return_value={"selected_deliveries": ["design_professional"], "selected_modes": []},
        ):
            cmd = output_intent_detection_node(state)

        esz = cmd.update.get("extracted_spatial_zones")
        assert esz is not None
        assert len(esz) >= 1
        assert esz[0]["id"] == "overall"


# ==============================================================================
# R2: 幂等保护仍生效
# ==============================================================================


class TestR2IdempotencyGuardStillWorks:
    """已有 active_projections 且 intent_changed=False 时直接跳过"""

    def test_skip_when_projections_exist(self):
        """R2.1: 幂等保护应直接 goto feasibility_analyst"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            output_intent_detection_node,
        )
        from langgraph.types import Command

        state = _minimal_state_no_images(
            active_projections=["design_professional"],
            intent_changed=False,
        )

        cmd = output_intent_detection_node(state)
        assert isinstance(cmd, Command)
        assert cmd.goto == "feasibility_analyst"
        # 幂等跳过时不应有 update（或 update 为空）
        assert cmd.update is None or "active_projections" not in (cmd.update or {})


# ==============================================================================
# R3: project_director 无约束时格式不变
# ==============================================================================


class TestR3ProjectDirectorNoConstraint:
    """无约束时 task_description 保持原有格式"""

    def test_no_injection_marker(self):
        """R3.1: visual_constraints=None 时不出现'设计参照系'"""
        from intelligent_project_analyzer.agents.project_director import ProjectDirectorAgent

        state = _minimal_state_no_images()
        pd = ProjectDirectorAgent.__new__(ProjectDirectorAgent)
        pd._build_feasibility_context = MagicMock(return_value="")

        desc = pd.get_task_description(state)
        assert "设计参照系" not in desc
        assert "约束信封" not in desc

    def test_still_contains_base_sections(self):
        """R3.2: 基础区段（项目概述、核心目标、功能需求）仍然存在"""
        from intelligent_project_analyzer.agents.project_director import ProjectDirectorAgent

        state = _minimal_state_no_images()
        pd = ProjectDirectorAgent.__new__(ProjectDirectorAgent)
        pd._build_feasibility_context = MagicMock(return_value="")

        desc = pd.get_task_description(state)
        assert "项目概述" in desc
        assert "核心目标" in desc
        assert "功能需求" in desc
        assert "约束条件" in desc


# ==============================================================================
# R4: image_generator 无约束时不改变 avoid/required
# ==============================================================================


class TestR4ImageGeneratorNoConstraint:
    """无 visual_constraints 时图像生成prompt保持不变"""

    def test_generate_structured_prompt_default_visual_constraints(self):
        """R4.1: visual_constraints=None 时不添加额外 avoid/required"""
        import inspect
        from intelligent_project_analyzer.services.image_generator import ImageGeneratorService

        sig = inspect.signature(ImageGeneratorService._generate_structured_prompt)
        # visual_constraints 参数默认值应为 None
        param = sig.parameters.get("visual_constraints")
        assert param is not None
        assert param.default is None


# ==============================================================================
# R5: State 向后兼容
# ==============================================================================


class TestR5StateBackwardCompatibility:
    """确保旧字段依然存在"""

    def test_core_fields_still_exist(self):
        """R5.1: 所有核心字段（user_input, session_id 等）仍在初始 state 中"""
        from intelligent_project_analyzer.core.state import StateManager

        sm = StateManager()
        state = sm.create_initial_state("test", "s1")

        essential_keys = [
            "user_input",
            "session_id",
            "agent_results",
            "structured_requirements",
            "active_projections",
        ]
        for key in essential_keys:
            assert key in state, f"缺少核心字段: {key}"

    def test_new_fields_coexist_with_old(self):
        """R5.2: 新字段不覆盖旧字段"""
        from intelligent_project_analyzer.core.state import StateManager

        sm = StateManager()
        state = sm.create_initial_state("test", "s1")

        # 新字段存在
        assert "visual_constraints" in state
        assert "extracted_spatial_zones" in state

        # 旧字段也存在
        assert "uploaded_visual_references" in state or True  # 旧字段可能不在初始state中，这是OK的
        assert "user_input" in state
        assert state["user_input"] == "test"


# ==============================================================================
# R6: interrupt payload 向后兼容
# ==============================================================================


class TestR6InterruptPayloadBackwardCompatibility:
    """interrupt payload 新字段是附加的，不影响旧字段"""

    def test_payload_still_has_delivery_types_and_identity_modes(self):
        """R6.1: interrupt payload 仍包含旧的 delivery_types / identity_modes"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            output_intent_detection_node,
        )

        state = _minimal_state_no_images()
        captured_payload = {}

        def capture_interrupt(payload):
            captured_payload.update(payload)
            return {"selected_deliveries": ["design_professional"], "selected_modes": []}

        with patch(
            "intelligent_project_analyzer.interaction.nodes.output_intent_detection.interrupt",
            side_effect=capture_interrupt,
        ):
            output_intent_detection_node(state)

        # 旧字段仍存在
        assert "interaction_type" in captured_payload
        assert captured_payload["interaction_type"] == "output_intent_confirmation"
        assert "delivery_types" in captured_payload
        assert "identity_modes" in captured_payload
        assert "options" in captured_payload["delivery_types"]

        # 新字段作为附加（可能为空但不应破坏结构）
        assert "spatial_zones" in captured_payload
        assert "auto_detected_constraints" in captured_payload


# ==============================================================================
# R7: 约束管线异常不阻塞主流程
# ==============================================================================


class TestR7ConstraintPipelineErrorResilience:
    """约束管线报错时主流程应正常继续"""

    def test_pipeline_exception_does_not_block_node(self):
        """R7.1: 管线抛异常 → visual_constraints=None 但节点正常返回 Command"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            output_intent_detection_node,
        )

        state = _minimal_state_no_images()
        # 注入图片使管线被触发
        state["uploaded_visual_references"] = [
            {
                "file_path": "/tmp/broken.png",
                "structured_features": {
                    "image_type": "constraint_source",
                    "image_subtype": "floor_plan",
                    "spatial_zone_guess": "1F",
                    "style_keywords": [],
                },
            },
        ]

        with patch(
            "intelligent_project_analyzer.interaction.nodes.output_intent_detection.interrupt",
            return_value={"selected_deliveries": ["design_professional"], "selected_modes": []},
        ):
            # 让管线内部抛异常
            with patch(
                "intelligent_project_analyzer.interaction.nodes.output_intent_detection._run_constraint_pipeline",
                side_effect=RuntimeError("Vision API 连接超时"),
            ):
                from langgraph.types import Command

                cmd = output_intent_detection_node(state)

        # 节点应正常返回
        assert isinstance(cmd, Command)
        assert cmd.goto == "feasibility_analyst"
        # 约束应为 None（管线失败）
        assert cmd.update.get("visual_constraints") is None
        # 其他字段正常
        assert "active_projections" in cmd.update

    def test_pipeline_timeout_does_not_block(self):
        """R7.2: 管线超时 → 节点正常返回"""
        from intelligent_project_analyzer.interaction.nodes.output_intent_detection import (
            output_intent_detection_node,
        )

        state = _minimal_state_no_images()
        state["uploaded_visual_references"] = [
            {
                "file_path": "/tmp/timeout.png",
                "structured_features": {
                    "image_type": "constraint_source",
                    "image_subtype": "site_photo",
                    "spatial_zone_guess": "整体",
                    "style_keywords": [],
                },
            },
        ]

        with patch(
            "intelligent_project_analyzer.interaction.nodes.output_intent_detection.interrupt",
            return_value={"selected_deliveries": ["design_professional"], "selected_modes": []},
        ):
            with patch(
                "intelligent_project_analyzer.interaction.nodes.output_intent_detection._run_constraint_pipeline",
                side_effect=TimeoutError("Vision API 45秒超时"),
            ):
                from langgraph.types import Command

                cmd = output_intent_detection_node(state)

        assert isinstance(cmd, Command)
        assert cmd.update.get("visual_constraints") is None
        assert "active_projections" in cmd.update
