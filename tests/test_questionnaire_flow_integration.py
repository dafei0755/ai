"""
集成测试 - 完整问卷流程 (v7.149)

测试目标:
1. 测试完整的问卷流程（Step 1-4）
2. 验证需求洞察正常生成
3. 验证降级逻辑在异常时正常工作
4. 验证诊断脚本能正确识别问题
"""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from intelligent_project_analyzer.core.state import ProjectAnalysisState
from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import ProgressiveQuestionnaireNode
from intelligent_project_analyzer.interaction.nodes.questionnaire_summary import QuestionnaireSummaryNode


class TestQuestionnaireFlowIntegration:
    """测试完整问卷流程的集成"""

    @pytest.fixture
    def initial_state(self):
        """初始状态"""
        return {
            "user_input": "以丹麦家居品牌HAY气质为基础的民宿室内设计概念，四川峨眉山七里坪",
            "session_id": "test-session-001",
            "user_id": "test-user",
            "mode": "dynamic",
            "requirement_analysis": {
                "analysis_layers": {
                    "L1_key_facts": ["HAY品牌", "民宿", "峨眉山"],
                    "L2_user_model": {"aesthetic": "北欧极简"},
                    "L3_core_tension": "品牌美学与自然环境的融合",
                    "L4_project_task": "打造HAY风格民宿",
                    "L5_sharpness_score": 8,
                }
            },
        }

    def test_step1_core_tasks_generation(self, initial_state):
        """测试 Step 1: 核心任务生成"""
        with patch(
            "intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt"
        ) as mock_interrupt:
            # 模拟用户确认任务
            mock_interrupt.return_value = {
                "action": "confirm",
                "confirmed_tasks": [
                    {"title": "打造HAY品牌空间设计概念", "description": "核心任务1"},
                    {"title": "融合北欧美学与自然环境", "description": "核心任务2"},
                ],
            }

            result = ProgressiveQuestionnaireNode.step1_core_task(initial_state, store=None)

        # 验证返回的 Command
        assert result.update is not None
        assert "confirmed_core_tasks" in result.update
        assert len(result.update["confirmed_core_tasks"]) == 2
        assert result.goto == "progressive_step3_gap_filling"

    def test_step2_gap_filling(self):
        """测试 Step 2: 信息补充"""
        state = {
            "user_input": "测试需求",
            "confirmed_core_tasks": [{"title": "任务1", "description": "描述1"}, {"title": "任务2", "description": "描述2"}],
        }

        with patch(
            "intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt"
        ) as mock_interrupt:
            # 模拟用户提交答案
            mock_interrupt.return_value = {
                "action": "submit",
                "responses": {"project_scale": "700平米，12间客房", "design_output_type": ["设计策略文档", "空间概念描述"]},
            }

            result = ProgressiveQuestionnaireNode.step3_gap_filling(state, store=None)

        # 验证返回的 Command
        assert result.update is not None
        assert "gap_filling_answers" in result.update
        assert result.update["gap_filling_answers"]["project_scale"] == "700平米，12间客房"
        assert result.goto == "progressive_step2_radar"

    def test_step3_radar_dimensions(self):
        """测试 Step 3: 雷达图维度"""
        state = {
            "user_input": "测试需求",
            "confirmed_core_tasks": [{"title": "任务1"}],
            "gap_filling_answers": {"field1": "value1"},
        }

        with patch(
            "intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt"
        ) as mock_interrupt:
            # 模拟用户设置维度值
            mock_interrupt.return_value = {
                "action": "submit",
                "dimension_values": {"material_temperature": 60, "cultural_axis": 70, "space_density": 50},
            }

            result = ProgressiveQuestionnaireNode.step2_radar(state, store=None)

        # 验证返回的 Command
        assert result.update is not None
        assert "radar_dimension_values" in result.update
        assert "selected_dimensions" in result.update
        assert result.goto == "questionnaire_summary"

    def test_step4_questionnaire_summary_success(self):
        """测试 Step 4: 需求洞察（成功场景）"""
        state = {
            "user_input": "测试需求",
            "confirmed_core_tasks": [{"title": "任务1", "description": "描述1"}],
            "gap_filling_answers": {"project_scale": "100平米", "design_output_type": ["设计方案"]},
            "selected_dimensions": [{"id": "functionality", "name": "功能性"}, {"id": "aesthetics", "name": "美学"}],
            "radar_dimension_values": {"functionality": 80, "aesthetics": 70},
            "requirement_analysis": {
                "analysis_layers": {
                    "L1_key_facts": ["测试"],
                    "L2_user_model": {},
                    "L3_core_tension": "测试张力",
                    "L4_project_task": "测试任务",
                    "L5_sharpness_score": 7,
                }
            },
        }

        # Mock 正常的 restructure
        mock_doc = {
            "metadata": {"generation_method": "normal_restructure", "generated_at": "2026-01-07T10:00:00"},
            "project_objectives": {"primary_goal": "测试目标"},
            "design_priorities": [
                {"dimension": "functionality", "label": "功能性", "weight": 0.5},
                {"dimension": "aesthetics", "label": "美学", "weight": 0.5},
            ],
            "constraints": {},
            "core_tension": {},
            "special_requirements": [],
            "identified_risks": [],
            "insight_summary": {
                "L1_key_facts": ["测试"],
                "L2_user_profile": {},
                "L3_core_tension": "测试张力",
                "L4_project_task_jtbd": "测试任务",
                "L5_sharpness_score": 7,
            },
            "deliverable_expectations": ["设计方案"],
            "executive_summary": {
                "one_sentence": "测试",
                "what": "测试",
                "why": "测试",
                "how": "测试",
                "constraints_summary": "测试",
            },
            # 🆕 v7.151: 新增必要字段
            "insight_summary": {"L5_sharpness_score": 85},
            "project_essence": "",
            "implicit_requirements": [],
            "key_conflicts": [],
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

        # 验证结果
        assert result.update is not None
        assert "restructured_requirements" in result.update
        assert result.update["restructured_requirements"]["metadata"]["generation_method"] == "normal_restructure"
        assert len(result.update["restructured_requirements"]["design_priorities"]) == 2
        # 🆕 v7.151: 现在直接路由到 project_director（合并了 requirements_confirmation）
        assert result.goto == "project_director"
        assert result.update["requirements_confirmed"] is True

    def test_step4_questionnaire_summary_fallback(self):
        """测试 Step 4: 需求洞察（降级场景）"""
        state = {
            "user_input": "测试需求",
            "confirmed_core_tasks": [{"title": "任务1"}],
            "gap_filling_answers": {},
            "selected_dimensions": [],
            "requirement_analysis": {},
        }

        with patch(
            "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.RequirementsRestructuringEngine"
        ) as mock_engine:
            # 模拟异常
            mock_engine.restructure.side_effect = ValueError("数据格式错误")

            with patch(
                "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.interrupt"
            ) as mock_interrupt:
                mock_interrupt.return_value = {"action": "confirm"}

                result = QuestionnaireSummaryNode.execute(state, store=None)

        # 验证降级逻辑生效
        assert result.update is not None
        assert "restructured_requirements" in result.update
        assert result.update["restructured_requirements"]["metadata"]["generation_method"] == "fallback_restructure"
        assert result.update["restructured_requirements"]["project_objectives"]["primary_goal_source"] == "fallback"

    @pytest.mark.asyncio
    async def test_diagnostic_script_integration(self):
        """测试诊断脚本的集成"""
        # 这个测试需要 Redis 运行
        from intelligent_project_analyzer.services.redis_session_manager import RedisSessionManager

        session_manager = RedisSessionManager()

        try:
            await session_manager.connect()

            # 创建测试会话
            test_session_id = "test-diagnostic-001"
            test_data = {
                "session_id": test_session_id,
                "user_input": "测试",
                "status": "waiting_for_input",
                "progress": 0.9,
                "current_node": "interrupt",
                "confirmed_core_tasks": [],
                "gap_filling_answers": {},
                "selected_dimensions": [],
                "radar_dimension_values": {},
                "restructured_requirements": {"metadata": {"generation_method": "fallback_restructure"}},
            }

            await session_manager.create(test_session_id, test_data)

            # 获取会话数据
            retrieved = await session_manager.get(test_session_id)

            # 验证数据
            assert retrieved is not None
            assert retrieved["session_id"] == test_session_id
            assert retrieved["restructured_requirements"]["metadata"]["generation_method"] == "fallback_restructure"

            # 清理
            await session_manager.redis_client.delete(f"session:{test_session_id}")

        finally:
            await session_manager.disconnect()


class TestDimensionTypeHandling:
    """测试维度类型处理（v7.148 修复验证）"""

    def test_dict_dimension_format(self):
        """测试 dict 格式的维度"""
        state = {
            "user_input": "测试",
            "confirmed_core_tasks": [{"title": "任务1"}],
            "gap_filling_answers": {"field1": "value1"},
            "selected_dimensions": [{"id": "functionality", "name": "功能性"}, {"id": "aesthetics", "name": "美学"}],
            "radar_dimension_values": {"functionality": 80, "aesthetics": 70},
            "requirement_analysis": {"analysis_layers": {}},
        }

        with patch(
            "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.RequirementsRestructuringEngine"
        ) as mock_engine:
            mock_engine.restructure.return_value = {
                "metadata": {"generation_method": "test"},
                "project_objectives": {"primary_goal": "测试"},
                "design_priorities": [],
                "constraints": {},
                "core_tension": {},
                "special_requirements": [],
                "identified_risks": [],
                # 🆕 v7.151: 必须包含完整的 insight_summary
                "insight_summary": {"L5_sharpness_score": 75},
                "deliverable_expectations": [],
                "executive_summary": {},
                "project_essence": "",
                "implicit_requirements": [],
                "key_conflicts": [],
            }

            with patch(
                "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.interrupt"
            ) as mock_interrupt:
                mock_interrupt.return_value = {"action": "confirm"}

                result = QuestionnaireSummaryNode.execute(state, store=None)

        # 验证没有抛出 TypeError
        assert result.update is not None

    def test_string_dimension_format(self):
        """测试 string 格式的维度"""
        state = {
            "user_input": "测试",
            "confirmed_core_tasks": [{"title": "任务1"}],
            "gap_filling_answers": {"field1": "value1"},
            "selected_dimensions": ["functionality", "aesthetics"],  # 字符串格式
            "radar_dimension_values": {"functionality": 80, "aesthetics": 70},
            "requirement_analysis": {"analysis_layers": {}},
        }

        with patch(
            "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.RequirementsRestructuringEngine"
        ) as mock_engine:
            mock_engine.restructure.return_value = {
                "metadata": {"generation_method": "test"},
                "project_objectives": {"primary_goal": "测试"},
                "design_priorities": [],
                "constraints": {},
                "core_tension": {},
                "special_requirements": [],
                "identified_risks": [],
                # 🆕 v7.151: 必须包含完整的 insight_summary
                "insight_summary": {"L5_sharpness_score": 75},
                "deliverable_expectations": [],
                "executive_summary": {},
                "project_essence": "",
                "implicit_requirements": [],
                "key_conflicts": [],
            }

            with patch(
                "intelligent_project_analyzer.interaction.nodes.questionnaire_summary.interrupt"
            ) as mock_interrupt:
                mock_interrupt.return_value = {"action": "confirm"}

                result = QuestionnaireSummaryNode.execute(state, store=None)

        # 验证没有抛出 TypeError
        assert result.update is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
