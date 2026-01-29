"""
测试需求洞察节点 questionnaire_responses 空值修复

v7.143: 修复 AttributeError: 'NoneType' object has no attribute 'get'
"""

from datetime import datetime

import pytest

from intelligent_project_analyzer.core.state import ProjectAnalysisState
from intelligent_project_analyzer.interaction.nodes.questionnaire_summary import QuestionnaireSummaryNode


class TestQuestionnaireResponsesFix:
    """测试 questionnaire_responses 空值防御性代码"""

    def test_extract_questionnaire_data_with_none_responses(self):
        """测试 questionnaire_responses 为 None 时不崩溃"""
        # 构建一个 questionnaire_responses 为 None 的 state
        state = ProjectAnalysisState(
            session_id="test-session",
            user_id="test-user",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user_input="测试输入",
            questionnaire_responses=None,  # ❌ 模拟旧流程中该字段为 None
            confirmed_core_tasks=[],
            gap_filling_answers={},
        )

        # 调用 _extract_questionnaire_data，应该不崩溃
        result = QuestionnaireSummaryNode._extract_questionnaire_data(state)

        # 验证返回结构
        assert "core_tasks" in result
        assert "gap_filling" in result
        assert isinstance(result["gap_filling"], dict)

    def test_extract_questionnaire_data_with_valid_responses(self):
        """测试 questionnaire_responses 有效数据时正常工作"""
        state = ProjectAnalysisState(
            session_id="test-session",
            user_id="test-user",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user_input="测试输入",
            questionnaire_responses={
                "gap_filling": {"budget": "10万", "timeline": "3个月"},
                "radar_dimensions": [],
                "timestamp": datetime.now().isoformat(),
            },
            confirmed_core_tasks=["任务1", "任务2"],
            gap_filling_answers={},
        )

        result = QuestionnaireSummaryNode._extract_questionnaire_data(state)

        # 验证 gap_filling 数据正确提取
        assert result["gap_filling"] == {"budget": "10万", "timeline": "3个月"}
        assert len(result["core_tasks"]) == 2

    def test_extract_questionnaire_data_with_gap_filling_answers(self):
        """测试优先使用 gap_filling_answers 字段"""
        state = ProjectAnalysisState(
            session_id="test-session",
            user_id="test-user",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user_input="测试输入",
            questionnaire_responses={
                "gap_filling": {"budget": "旧数据"},
            },
            gap_filling_answers={"budget": "新数据", "timeline": "3个月"},  # 优先使用
            confirmed_core_tasks=[],
        )

        result = QuestionnaireSummaryNode._extract_questionnaire_data(state)

        # 验证优先使用 gap_filling_answers
        assert result["gap_filling"] == {"budget": "新数据", "timeline": "3个月"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
