"""
v7.130 问卷状态管理统一测试

测试 interaction_type 与 step 数字一致性
- step1 = 任务梳理 → interaction_type: progressive_questionnaire_step1
- step2 = 信息补全 → interaction_type: progressive_questionnaire_step2
- step3 = 雷达图 → interaction_type: progressive_questionnaire_step3
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import MagicMock, patch

import pytest


class TestInteractionTypeConsistency:
    """测试 interaction_type 与 step 数字的一致性"""

    def test_step1_interaction_type_matches_step_number(self):
        """测试 Step 1 的 interaction_type 与 step 数字一致"""
        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            progressive_step1_core_task_node,
        )

        mock_state = {
            "session_id": "test_session",
            "user_input": "设计一个现代简约风格的客厅",
            "agent_results": {
                "requirements_analyst": {
                    "structured_data": {
                        "project_type": "室内设计",
                        "project_overview": "客厅设计",
                    }
                }
            },
        }
        mock_store = MagicMock()
        captured_payload = None

        def capture_interrupt(payload):
            nonlocal captured_payload
            captured_payload = payload
            return {"confirmed_tasks": [{"title": "测试任务", "description": "测试描述"}]}

        with patch(
            "intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt",
            side_effect=capture_interrupt,
        ):
            progressive_step1_core_task_node(mock_state, mock_store)

        assert captured_payload is not None, "应该捕获到 interrupt payload"
        assert (
            captured_payload.get("interaction_type") == "progressive_questionnaire_step1"
        ), f"Step 1 的 interaction_type 应该是 'progressive_questionnaire_step1'，实际是 '{captured_payload.get('interaction_type')}'"
        assert captured_payload.get("step") == 1, f"Step 1 的 step 数字应该是 1，实际是 {captured_payload.get('step')}"

    def test_step2_info_completion_interaction_type(self):
        """测试 Step 2 (信息补全) 的 interaction_type 与 step 数字一致

        v7.130: step2 = 信息补全，interaction_type = progressive_questionnaire_step2
        """
        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            progressive_step3_gap_filling_node,  # 函数名是 step3，但它发送的是 step2
        )

        mock_state = {
            "session_id": "test_session",
            "user_input": "设计一个现代简约风格的客厅",
            "confirmed_core_tasks": [{"title": "客厅设计", "description": "设计现代简约风格的客厅"}],
            "confirmed_core_task": "设计现代简约风格的客厅",
            "agent_results": {"requirements_analyst": {"structured_data": {"project_type": "室内设计"}}},
        }
        mock_store = MagicMock()
        captured_payload = None

        def capture_interrupt(payload):
            nonlocal captured_payload
            captured_payload = payload
            return {"answers": {"budget": "50万"}}

        with patch(
            "intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt",
            side_effect=capture_interrupt,
        ):
            progressive_step3_gap_filling_node(mock_state, mock_store)

        assert captured_payload is not None, "应该捕获到 interrupt payload"

        # v7.130 关键验证：interaction_type 应该与 step 数字一致
        assert (
            captured_payload.get("interaction_type") == "progressive_questionnaire_step2"
        ), f"信息补全的 interaction_type 应该是 'progressive_questionnaire_step2'，实际是 '{captured_payload.get('interaction_type')}'"
        assert captured_payload.get("step") == 2, f"信息补全的 step 数字应该是 2，实际是 {captured_payload.get('step')}"

    def test_step3_radar_interaction_type(self):
        """测试 Step 3 (雷达图) 的 interaction_type 与 step 数字一致

        v7.130: step3 = 雷达图，interaction_type = progressive_questionnaire_step3
        """
        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            progressive_step2_radar_node,  # 函数名是 step2，但它发送的是 step3
        )

        mock_state = {
            "session_id": "test_session",
            "user_input": "设计一个现代简约风格的客厅",
            "confirmed_core_tasks": [{"title": "客厅设计", "description": "设计现代简约风格的客厅"}],
            "confirmed_core_task": "设计现代简约风格的客厅",
            "gap_filling_answers": {"budget": "50万"},
            "agent_results": {"requirements_analyst": {"structured_data": {"project_type": "室内设计"}}},
        }
        mock_store = MagicMock()
        captured_payload = None

        def capture_interrupt(payload):
            nonlocal captured_payload
            captured_payload = payload
            return {"dimension_values": {"modern_feel": 85}}

        # Mock 掉 DimensionSelector 的依赖问题
        with patch(
            "intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt",
            side_effect=capture_interrupt,
        ), patch(
            "intelligent_project_analyzer.services.dimension_selector.DimensionSelector.detect_and_inject_specialized_dimensions",
            return_value=[],
        ):
            progressive_step2_radar_node(mock_state, mock_store)

        assert captured_payload is not None, "应该捕获到 interrupt payload"

        # v7.130 关键验证：interaction_type 应该与 step 数字一致
        assert (
            captured_payload.get("interaction_type") == "progressive_questionnaire_step3"
        ), f"雷达图的 interaction_type 应该是 'progressive_questionnaire_step3'，实际是 '{captured_payload.get('interaction_type')}'"
        assert captured_payload.get("step") == 3, f"雷达图的 step 数字应该是 3，实际是 {captured_payload.get('step')}"


class TestExecutionOrder:
    """测试执行顺序正确性：step1 → step3函数(发step2) → step2函数(发step3)"""

    def test_step1_routes_to_step3_function(self):
        """测试 Step 1 路由到 progressive_step3_gap_filling"""
        from langgraph.types import Command

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            progressive_step1_core_task_node,
        )

        mock_state = {
            "session_id": "test_session",
            "user_input": "设计一个现代简约风格的客厅",
            "agent_results": {
                "requirements_analyst": {
                    "structured_data": {
                        "project_type": "室内设计",
                        "project_overview": "客厅设计",
                    }
                }
            },
        }
        mock_store = MagicMock()

        with patch(
            "intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt"
        ) as mock_interrupt:
            mock_interrupt.return_value = {"confirmed_tasks": [{"title": "测试", "description": "测试"}]}
            result = progressive_step1_core_task_node(mock_state, mock_store)

        assert isinstance(result, Command), "返回类型应该是 Command"
        assert (
            result.goto == "progressive_step3_gap_filling"
        ), f"Step 1 应该路由到 progressive_step3_gap_filling，实际是 {result.goto}"

    def test_step3_function_routes_to_step2_function(self):
        """测试 step3 函数路由到 progressive_step2_radar"""
        from langgraph.types import Command

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            progressive_step3_gap_filling_node,
        )

        mock_state = {
            "session_id": "test_session",
            "user_input": "设计一个现代简约风格的客厅",
            "confirmed_core_tasks": [{"title": "客厅设计", "description": "设计现代简约风格的客厅"}],
            "confirmed_core_task": "设计现代简约风格的客厅",
            "agent_results": {"requirements_analyst": {"structured_data": {"project_type": "室内设计"}}},
        }
        mock_store = MagicMock()

        with patch(
            "intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt"
        ) as mock_interrupt:
            mock_interrupt.return_value = {"answers": {"budget": "50万"}}
            result = progressive_step3_gap_filling_node(mock_state, mock_store)

        assert isinstance(result, Command), "返回类型应该是 Command"
        assert result.goto == "progressive_step2_radar", f"Step 3 函数应该路由到 progressive_step2_radar，实际是 {result.goto}"

    def test_step2_function_routes_to_project_director(self):
        """测试 step2 函数路由到 project_director（问卷结束）"""
        from langgraph.types import Command

        from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
            progressive_step2_radar_node,
        )

        mock_state = {
            "session_id": "test_session",
            "user_input": "设计一个现代简约风格的客厅",
            "confirmed_core_tasks": [{"title": "客厅设计", "description": "设计现代简约风格的客厅"}],
            "confirmed_core_task": "设计现代简约风格的客厅",
            "gap_filling_answers": {"budget": "50万"},
            "agent_results": {"requirements_analyst": {"structured_data": {"project_type": "室内设计"}}},
        }
        mock_store = MagicMock()

        # Mock 掉 DimensionSelector 的依赖问题
        with patch(
            "intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt"
        ) as mock_interrupt, patch(
            "intelligent_project_analyzer.services.dimension_selector.DimensionSelector.detect_and_inject_specialized_dimensions",
            return_value=[],
        ):
            mock_interrupt.return_value = {"dimension_values": {"modern_feel": 85}}
            result = progressive_step2_radar_node(mock_state, mock_store)

        assert isinstance(result, Command), "返回类型应该是 Command"
        assert result.goto == "project_director", f"Step 2 函数应该路由到 project_director，实际是 {result.goto}"
        assert result.update.get("progressive_questionnaire_completed") == True, "问卷应该标记为已完成"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
