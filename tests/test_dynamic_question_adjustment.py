"""
动态问题数量调整测试（P2功能）

验证基于问卷长度、冲突严重性、V1输出丰富度的智能裁剪功能。
"""

import pytest
from typing import Dict, Any, List

from intelligent_project_analyzer.interaction.nodes.calibration_questionnaire import CalibrationQuestionnaireNode
from intelligent_project_analyzer.interaction.questionnaire import QuestionAdjuster


# ==================== 测试数据 ====================

# 4个理念问题（完整）
FULL_PHILOSOPHY_QUESTIONS = [
    {"id": "v1_design_philosophy", "dimension": "philosophy", "type": "single_choice"},
    {"id": "v1_approach_spectrum", "dimension": "approach", "type": "single_choice"},
    {"id": "v1_goal_philosophy", "dimension": "goal", "type": "single_choice"},
    {"id": "v1_critical_exploration", "dimension": "exploration", "type": "open_ended"}
]

# 3个冲突问题（完整）
FULL_CONFLICT_QUESTIONS = [
    {"id": "v15_budget_conflict", "severity": "critical", "type": "single_choice"},
    {"id": "v15_timeline_conflict", "severity": "high", "type": "single_choice"},
    {"id": "v15_space_conflict", "severity": "medium", "type": "single_choice"}
]

# critical冲突数据
CRITICAL_FEASIBILITY = {
    "conflict_detection": {
        "budget_conflicts": [{"detected": True, "severity": "critical"}],
        "timeline_conflicts": [],
        "space_conflicts": []
    }
}

# high冲突数据
HIGH_FEASIBILITY = {
    "conflict_detection": {
        "budget_conflicts": [],
        "timeline_conflicts": [{"detected": True, "severity": "high"}],
        "space_conflicts": []
    }
}

# 无冲突数据
NO_CONFLICT_FEASIBILITY = {
    "conflict_detection": {
        "budget_conflicts": [],
        "timeline_conflicts": [],
        "space_conflicts": []
    }
}


# ==================== 测试类 ====================

class TestDynamicQuestionAdjustment:
    """动态问题数量调整测试"""

    def test_short_questionnaire_keeps_all_questions(self):
        """测试短问卷（≤7题）保留所有问题"""
        # 原始问卷3个问题 + 注入4个理念问题 = 7个问题
        original_count = 3
        philosophy_q = FULL_PHILOSOPHY_QUESTIONS.copy()
        conflict_q = []

        adjusted_phil, adjusted_conf = QuestionAdjuster.adjust(
            philosophy_questions=philosophy_q,
            conflict_questions=conflict_q,
            original_question_count=original_count,
            feasibility_data=NO_CONFLICT_FEASIBILITY
        )

        # 验证保留所有问题
        assert len(adjusted_phil) == 4
        assert len(adjusted_conf) == 0

    def test_medium_questionnaire_applies_light_trim(self):
        """测试中等问卷（8-10题）轻度裁剪（保留80%）"""
        # 原始问卷5个问题 + 注入7个问题（4理念+3冲突）= 12个问题
        # 但注入的7个会触发轻度裁剪（8-10范围）
        original_count = 3  # 3+7=10, 触发轻度裁剪
        philosophy_q = FULL_PHILOSOPHY_QUESTIONS.copy()
        conflict_q = FULL_CONFLICT_QUESTIONS.copy()

        adjusted_phil, adjusted_conf = QuestionAdjuster.adjust(
            philosophy_questions=philosophy_q,
            conflict_questions=conflict_q,
            original_question_count=original_count,
            feasibility_data=HIGH_FEASIBILITY
        )

        total_adjusted = len(adjusted_phil) + len(adjusted_conf)
        # 7个问题 * 80% ≈ 5-6个问题
        assert total_adjusted >= 5
        assert total_adjusted <= 6

    def test_long_questionnaire_applies_medium_trim(self):
        """测试较长问卷（11-13题）中度裁剪（保留60%）"""
        # 原始问卷7个问题 + 注入7个问题 = 14个问题，触发中度裁剪
        original_count = 6  # 6+7=13, 触发中度裁剪
        philosophy_q = FULL_PHILOSOPHY_QUESTIONS.copy()
        conflict_q = FULL_CONFLICT_QUESTIONS.copy()

        adjusted_phil, adjusted_conf = QuestionAdjuster.adjust(
            philosophy_questions=philosophy_q,
            conflict_questions=conflict_q,
            original_question_count=original_count,
            feasibility_data=HIGH_FEASIBILITY
        )

        total_adjusted = len(adjusted_phil) + len(adjusted_conf)
        # 7个问题 * 60% ≈ 4-5个问题
        assert total_adjusted >= 4
        assert total_adjusted <= 5

    def test_very_long_questionnaire_applies_heavy_trim(self):
        """测试超长问卷（≥14题）重度裁剪（保留40%）"""
        # 原始问卷10个问题 + 注入7个问题 = 17个问题，触发重度裁剪
        original_count = 10  # 10+7=17, 触发重度裁剪
        philosophy_q = FULL_PHILOSOPHY_QUESTIONS.copy()
        conflict_q = FULL_CONFLICT_QUESTIONS.copy()

        adjusted_phil, adjusted_conf = QuestionAdjuster.adjust(
            philosophy_questions=philosophy_q,
            conflict_questions=conflict_q,
            original_question_count=original_count,
            feasibility_data=HIGH_FEASIBILITY
        )

        total_adjusted = len(adjusted_phil) + len(adjusted_conf)
        # 7个问题 * 40% ≈ 2-3个问题
        assert total_adjusted >= 2
        assert total_adjusted <= 3

    def test_critical_conflict_prioritizes_conflict_questions(self):
        """测试critical冲突时优先保留冲突问题"""
        original_count = 10  # 触发重度裁剪（保留40%，约3个问题）
        philosophy_q = FULL_PHILOSOPHY_QUESTIONS.copy()
        conflict_q = [
            {"id": "v15_budget_conflict", "severity": "critical", "type": "single_choice"}
        ]

        adjusted_phil, adjusted_conf = QuestionAdjuster.adjust(
            philosophy_questions=philosophy_q,
            conflict_questions=conflict_q,
            original_question_count=original_count,
            feasibility_data=CRITICAL_FEASIBILITY
        )

        # critical冲突问题应该被保留
        assert len(adjusted_conf) == 1
        assert adjusted_conf[0]["id"] == "v15_budget_conflict"

        # 理念问题可能被部分裁剪
        total_adjusted = len(adjusted_phil) + len(adjusted_conf)
        # 5个问题 * 40% = 2个问题
        assert total_adjusted >= 2

    def test_philosophy_priority_order(self):
        """测试理念问题的优先级排序"""
        original_count = 10  # 触发重度裁剪
        philosophy_q = FULL_PHILOSOPHY_QUESTIONS.copy()
        conflict_q = []

        adjusted_phil, adjusted_conf = QuestionAdjuster.adjust(
            philosophy_questions=philosophy_q,
            conflict_questions=conflict_q,
            original_question_count=original_count,
            feasibility_data=NO_CONFLICT_FEASIBILITY
        )

        # 应该保留1-2个高优先级理念问题
        # 优先级: philosophy(90) > approach(75) > goal(65) > exploration(50)
        assert len(adjusted_phil) >= 1

        # 验证保留的是高优先级问题
        adjusted_dimensions = {q["dimension"] for q in adjusted_phil}
        # philosophy和approach应该优先保留
        if len(adjusted_phil) >= 1:
            assert "philosophy" in adjusted_dimensions or "approach" in adjusted_dimensions

    def test_get_max_conflict_severity_critical(self):
        """测试获取最高冲突严重性：critical"""
        severity = QuestionAdjuster._get_max_conflict_severity(CRITICAL_FEASIBILITY)
        assert severity == "critical"

    def test_get_max_conflict_severity_high(self):
        """测试获取最高冲突严重性：high"""
        severity = QuestionAdjuster._get_max_conflict_severity(HIGH_FEASIBILITY)
        assert severity == "high"

    def test_get_max_conflict_severity_none(self):
        """测试获取最高冲突严重性：无冲突"""
        severity = QuestionAdjuster._get_max_conflict_severity(NO_CONFLICT_FEASIBILITY)
        assert severity == "none"

    def test_get_max_conflict_severity_multiple_conflicts(self):
        """测试多个冲突时返回最高严重性"""
        mixed_feasibility = {
            "conflict_detection": {
                "budget_conflicts": [{"detected": True, "severity": "high"}],
                "timeline_conflicts": [{"detected": True, "severity": "critical"}],
                "space_conflicts": [{"detected": True, "severity": "medium"}]
            }
        }

        severity = QuestionAdjuster._get_max_conflict_severity(mixed_feasibility)
        assert severity == "critical"

    def test_empty_questions_returns_empty(self):
        """测试无问题时返回空列表"""
        adjusted_phil, adjusted_conf = QuestionAdjuster.adjust(
            philosophy_questions=[],
            conflict_questions=[],
            original_question_count=5,
            feasibility_data=NO_CONFLICT_FEASIBILITY
        )

        assert len(adjusted_phil) == 0
        assert len(adjusted_conf) == 0

    def test_preserves_at_least_one_question(self):
        """测试即使重度裁剪也至少保留1个问题"""
        original_count = 20  # 超长问卷
        philosophy_q = FULL_PHILOSOPHY_QUESTIONS[:1]  # 只有1个理念问题
        conflict_q = []

        adjusted_phil, adjusted_conf = QuestionAdjuster.adjust(
            philosophy_questions=philosophy_q,
            conflict_questions=conflict_q,
            original_question_count=original_count,
            feasibility_data=NO_CONFLICT_FEASIBILITY
        )

        # 即使触发重度裁剪，也应该保留至少1个问题
        total_adjusted = len(adjusted_phil) + len(adjusted_conf)
        assert total_adjusted >= 1


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
