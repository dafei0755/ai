"""
单元测试 - 需求洞察异常日志增强 (v7.149)

测试目标:
1. 验证异常被正确捕获并记录完整堆栈
2. 验证降级逻辑正常工作
3. 验证降级文档包含正确的 generation_method
"""

from unittest.mock import MagicMock, Mock, patch

import pytest

from intelligent_project_analyzer.core.state import ProjectAnalysisState
from intelligent_project_analyzer.interaction.nodes.questionnaire_summary import QuestionnaireSummaryNode


class TestQuestionnaireSummaryExceptionLogging:
    """测试需求洞察节点的异常日志增强"""

    def test_exception_logging_with_full_stacktrace(self, caplog):
        """测试异常被捕获并记录完整堆栈"""
        import logging

        caplog.set_level(logging.ERROR)

        # 准备测试数据
        state = {
            "confirmed_core_tasks": [
                {"title": "测试任务1", "description": "描述1"},
                {"title": "测试任务2", "description": "描述2"},
            ],
            "gap_filling_answers": {"project_scale": "100平米", "design_output_type": ["设计方案"]},
            "selected_dimensions": [{"id": "functionality", "name": "功能性"}, {"id": "aesthetics", "name": "美学"}],
            "radar_dimension_values": {"functionality": 80, "aesthetics": 70},
            "requirement_analysis": {},
            "user_input": "测试需求",
        }

        # Mock RequirementsRestructuringEngine.restructure 抛出异常
        with patch(
            "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.RequirementsRestructuringEngine"
        ) as mock_engine:
            mock_engine.restructure.side_effect = ValueError("测试异常：数据格式错误")

            # 执行节点（应该捕获异常并使用降级逻辑）
            with patch(
                "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.interrupt"
            ) as mock_interrupt:
                mock_interrupt.return_value = {"action": "confirm"}

                result = QuestionnaireSummaryNode.execute(state, store=None)

        # 验证日志记录
        assert "❌ 需求重构失败: 测试异常：数据格式错误" in caplog.text
        assert "异常堆栈:" in caplog.text
        assert "ValueError" in caplog.text
        assert "⚠️ [降级模式] 使用简化需求重构" in caplog.text

    def test_fallback_restructure_is_called_on_exception(self):
        """测试异常时调用降级逻辑"""
        state = {
            "confirmed_core_tasks": [{"title": "任务1"}],
            "gap_filling_answers": {},
            "selected_dimensions": [],
            "requirement_analysis": {},
            "user_input": "测试",
        }

        with patch(
            "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.RequirementsRestructuringEngine"
        ) as mock_engine:
            mock_engine.restructure.side_effect = Exception("测试异常")

            with patch(
                "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.interrupt"
            ) as mock_interrupt:
                mock_interrupt.return_value = {"action": "confirm"}

                result = QuestionnaireSummaryNode.execute(state, store=None)

        # 验证返回的 update_dict 包含 restructured_requirements
        assert "restructured_requirements" in result.update
        restructured = result.update["restructured_requirements"]

        # 验证使用了降级模式
        assert restructured["metadata"]["generation_method"] == "fallback_restructure"
        assert restructured["metadata"]["data_sources"] == ["user_questionnaire"]

    def test_fallback_document_structure(self):
        """测试降级文档的结构完整性"""
        questionnaire_data = {
            "core_tasks": [{"title": "核心任务1"}, {"title": "核心任务2"}],
            "gap_filling": {},
            "dimensions": {"selected": [], "weights": {}},
        }
        ai_analysis = {}
        user_input = "测试需求"

        fallback_doc = QuestionnaireSummaryNode._fallback_restructure(questionnaire_data, ai_analysis, user_input)

        # 验证必要字段存在
        assert "metadata" in fallback_doc
        assert "project_objectives" in fallback_doc
        assert "constraints" in fallback_doc
        assert "design_priorities" in fallback_doc
        assert "insight_summary" in fallback_doc
        assert "executive_summary" in fallback_doc

        # 验证 metadata
        assert fallback_doc["metadata"]["generation_method"] == "fallback_restructure"
        assert fallback_doc["metadata"]["document_version"] == "1.0"

        # 验证 project_objectives
        assert fallback_doc["project_objectives"]["primary_goal"] == "核心任务1"
        assert fallback_doc["project_objectives"]["primary_goal_source"] == "fallback"

    def test_normal_flow_without_exception(self):
        """测试正常流程（无异常）"""
        state = {
            "confirmed_core_tasks": [{"title": "任务1"}],
            "gap_filling_answers": {"field1": "value1"},
            "selected_dimensions": [{"id": "functionality", "name": "功能性"}],
            "radar_dimension_values": {"functionality": 80},
            "requirement_analysis": {},
            "user_input": "测试",
        }

        # Mock 正常的 restructure 返回
        mock_doc = {
            "metadata": {"generation_method": "normal_restructure", "generated_at": "2026-01-07T10:00:00"},
            "project_objectives": {"primary_goal": "测试目标"},
            "design_priorities": [{"dimension": "functionality", "label": "功能性", "weight": 0.8}],
            "constraints": {},
            "core_tension": {},
            "special_requirements": [],
            "identified_risks": [],
            "insight_summary": {
                "L1_key_facts": [],
                "L2_user_profile": {},
                "L3_core_tension": "",
                "L4_project_task_jtbd": "",
                "L5_sharpness_score": 0,
            },
            "deliverable_expectations": [],
            "executive_summary": {
                "one_sentence": "测试",
                "what": "测试",
                "why": "测试",
                "how": "测试",
                "constraints_summary": "测试",
            },
        }

        with patch(
            "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.RequirementsRestructuringEngine"
        ) as mock_engine:
            mock_engine.restructure.return_value = mock_doc

            with patch(
                "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.interrupt"
            ) as mock_interrupt:
                mock_interrupt.return_value = {"action": "confirm"}

                result = QuestionnaireSummaryNode.execute(state, store=None)

        # 验证使用了正常模式
        assert result.update["restructured_requirements"]["metadata"]["generation_method"] == "normal_restructure"

    def test_data_completeness_warnings(self, caplog):
        """测试数据不完整时的警告日志"""
        import logging

        caplog.set_level(logging.WARNING)

        # 准备不完整的数据
        state = {
            "confirmed_core_tasks": [],  # 空
            "gap_filling_answers": {},  # 空
            "selected_dimensions": [],  # 空
            "requirement_analysis": {},
            "user_input": "测试",
        }

        with patch(
            "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.RequirementsRestructuringEngine"
        ) as mock_engine:
            mock_engine.restructure.side_effect = Exception("数据不完整")

            with patch(
                "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.interrupt"
            ) as mock_interrupt:
                mock_interrupt.return_value = {"action": "confirm"}

                QuestionnaireSummaryNode.execute(state, store=None)

        # 验证警告日志
        assert "⚠️ [数据缺失] confirmed_core_tasks为空" in caplog.text
        assert "⚠️ [数据缺失] gap_filling_answers为空" in caplog.text
        assert "⚠️ [数据缺失] selected_dimensions为空" in caplog.text


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
