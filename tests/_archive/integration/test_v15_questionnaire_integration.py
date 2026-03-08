"""
V1.5 问卷集成测试（价值体现点1）

验证V1.5可行性分析结果影响战略校准问卷生成：
1. 检测到critical/high级别冲突时，自动生成针对性问题
2. 针对预算/时间/空间三类冲突，生成不同的单选题
3. 冲突问题插入到问卷中正确位置
"""

import pytest
from typing import Dict, Any

from intelligent_project_analyzer.interaction.nodes.calibration_questionnaire import CalibrationQuestionnaireNode
from intelligent_project_analyzer.interaction.questionnaire import ConflictQuestionGenerator


# ==================== 测试数据 ====================

MOCK_FEASIBILITY_WITH_BUDGET_CONFLICT = {
    "feasibility_assessment": {"overall_feasibility": "low", "critical_issues": ["预算缺口17万（超预算85%）"]},
    "conflict_detection": {
        "budget_conflicts": [
            {
                "type": "预算vs功能冲突",
                "severity": "critical",
                "detected": True,
                "details": {"available_budget": 200000, "estimated_cost": 370000, "gap": 170000, "gap_percentage": 85},
                "description": "预算20万，但需求成本37万，缺口17万（超预算85%）",
            }
        ],
        "timeline_conflicts": [],
        "space_conflicts": [],
    },
}

MOCK_FEASIBILITY_WITH_TIMELINE_CONFLICT = {
    "feasibility_assessment": {"overall_feasibility": "medium", "critical_issues": ["工期紧张（标准工期需90天）"]},
    "conflict_detection": {
        "budget_conflicts": [],
        "timeline_conflicts": [
            {
                "type": "时间vs质量冲突",
                "severity": "high",
                "detected": True,
                "details": {"available_days": 60, "required_days": 90, "gap": 30},
                "description": "2个月（60天）完成精装修，标准工期需90天，缺口30天",
            }
        ],
        "space_conflicts": [],
    },
}

MOCK_FEASIBILITY_WITH_SPACE_CONFLICT = {
    "feasibility_assessment": {"overall_feasibility": "low", "critical_issues": ["空间不足26㎡"]},
    "conflict_detection": {
        "budget_conflicts": [],
        "timeline_conflicts": [],
        "space_conflicts": [
            {
                "type": "空间vs功能冲突",
                "severity": "high",
                "detected": True,
                "details": {"available_area": 60, "required_area": 86, "gap": 26},
                "description": "60㎡小户型要4房2厅4独立卫，需要至少86㎡，缺口26㎡",
            }
        ],
    },
}

MOCK_FEASIBILITY_WITH_ALL_CONFLICTS = {
    "feasibility_assessment": {
        "overall_feasibility": "low",
        "critical_issues": ["预算缺口17万（超预算85%）", "工期紧张（标准工期需90天）", "空间不足26㎡"],
    },
    "conflict_detection": {
        "budget_conflicts": MOCK_FEASIBILITY_WITH_BUDGET_CONFLICT["conflict_detection"]["budget_conflicts"],
        "timeline_conflicts": MOCK_FEASIBILITY_WITH_TIMELINE_CONFLICT["conflict_detection"]["timeline_conflicts"],
        "space_conflicts": MOCK_FEASIBILITY_WITH_SPACE_CONFLICT["conflict_detection"]["space_conflicts"],
    },
}

MOCK_FEASIBILITY_NO_CONFLICT = {
    "feasibility_assessment": {"overall_feasibility": "high", "critical_issues": []},
    "conflict_detection": {"budget_conflicts": [], "timeline_conflicts": [], "space_conflicts": []},
}


# ==================== 测试类 ====================


class TestV15QuestionnaireIntegration:
    """V1.5问卷集成测试（价值体现点1）"""

    def test_build_conflict_questions_budget_conflict(self):
        """测试预算冲突问题生成"""
        # 🔧 v7.4.1: 必须传入 user_mentioned_constraints
        questions = ConflictQuestionGenerator.generate(
            MOCK_FEASIBILITY_WITH_BUDGET_CONFLICT,
            scenario_type="design_execution",
            user_mentioned_constraints=["budget"],
        )

        # 验证生成了1个问题
        assert len(questions) == 1

        # 验证问题结构
        question = questions[0]
        assert question["id"] == "v15_budget_conflict"
        assert question["type"] == "single_choice"
        assert "⚠️ 可行性分析发现" in question["question"]
        assert "预算20万，但需求成本37万" in question["question"]

        # 验证context包含V1.5标识
        assert "V1.5检测到预算缺口约85%" in question["context"]

        # 验证选项包含三种策略
        assert len(question["options"]) == 3
        assert any("增加预算" in opt for opt in question["options"])
        assert any("削减部分需求" in opt for opt in question["options"])
        assert any("寻求替代方案" in opt for opt in question["options"])

        # 验证来源和严重性
        assert question["source"] == "v15_feasibility_conflict"
        assert question["severity"] == "critical"

    def test_build_conflict_questions_timeline_conflict(self):
        """测试时间冲突问题生成"""
        questions = ConflictQuestionGenerator.generate(
            MOCK_FEASIBILITY_WITH_TIMELINE_CONFLICT,
            scenario_type="design_execution",
            user_mentioned_constraints=["timeline"],
        )

        # 验证生成了1个问题
        assert len(questions) == 1

        # 验证问题结构
        question = questions[0]
        assert question["id"] == "v15_timeline_conflict"
        assert question["type"] == "single_choice"
        assert "工期约束" in question["question"] or "质量标准" in question["context"]

        # 验证选项包含时间/质量权衡
        assert len(question["options"]) == 3
        assert any("延长工期" in opt for opt in question["options"])
        assert any("维持工期" in opt for opt in question["options"])
        assert any("优化施工方案" in opt for opt in question["options"])

    def test_build_conflict_questions_space_conflict(self):
        """测试空间冲突问题生成"""
        questions = ConflictQuestionGenerator.generate(
            MOCK_FEASIBILITY_WITH_SPACE_CONFLICT, scenario_type="design_execution", user_mentioned_constraints=["space"]
        )

        # 验证生成了1个问题
        assert len(questions) == 1

        # 验证问题结构
        question = questions[0]
        assert question["id"] == "v15_space_conflict"
        assert question["type"] == "single_choice"
        assert "空间约束" in question["question"] or "空间缺口" in question["context"]

        # 验证选项包含空间调整策略
        assert len(question["options"]) == 3
        assert any("调整户型配置" in opt for opt in question["options"])
        assert any("多功能房" in opt for opt in question["options"])
        assert any("优化空间布局" in opt for opt in question["options"])

    def test_build_conflict_questions_all_conflicts(self):
        """测试多个冲突同时存在时生成所有问题"""
        questions = ConflictQuestionGenerator.generate(
            MOCK_FEASIBILITY_WITH_ALL_CONFLICTS,
            scenario_type="design_execution",
            user_mentioned_constraints=["budget", "timeline", "space"],
        )

        # 验证生成了3个问题（预算+时间+空间）
        assert len(questions) == 3

        # 验证问题ID不重复
        question_ids = [q["id"] for q in questions]
        assert len(set(question_ids)) == 3

        # 验证包含所有三类冲突
        assert "v15_budget_conflict" in question_ids
        assert "v15_timeline_conflict" in question_ids
        assert "v15_space_conflict" in question_ids

        # 验证所有问题都是单选题
        assert all(q["type"] == "single_choice" for q in questions)

    def test_build_conflict_questions_no_conflict(self):
        """测试无冲突时不生成问题"""
        questions = ConflictQuestionGenerator.generate(
            MOCK_FEASIBILITY_NO_CONFLICT, scenario_type="design_execution", user_mentioned_constraints=[]
        )

        # 验证不生成任何问题
        assert len(questions) == 0

    def test_build_conflict_questions_low_severity_ignored(self):
        """测试低严重性冲突不生成问题"""
        feasibility_low_severity = {
            "conflict_detection": {
                "budget_conflicts": [
                    {
                        "type": "预算vs功能冲突",
                        "severity": "low",  # 低严重性，应该被忽略
                        "detected": True,
                        "details": {"gap": 5000, "gap_percentage": 5},
                        "description": "预算略有不足",
                    }
                ],
                "timeline_conflicts": [],
                "space_conflicts": [],
            }
        }

        questions = ConflictQuestionGenerator.generate(
            feasibility_low_severity, scenario_type="design_execution", user_mentioned_constraints=["budget"]
        )

        # 验证不生成问题（因为severity=low不符合阈值）
        assert len(questions) == 0

    def test_conflict_questions_contain_quantitative_info(self):
        """测试冲突问题包含量化信息"""
        questions = ConflictQuestionGenerator.generate(
            MOCK_FEASIBILITY_WITH_BUDGET_CONFLICT,
            scenario_type="design_execution",
            user_mentioned_constraints=["budget"],
        )

        question = questions[0]

        # 验证问题中包含具体数字
        assert "17万" in question["options"][0] or "170000" in str(question)

        # 验证context包含百分比
        assert "85%" in question["context"]

    def test_conflict_questions_format_consistency(self):
        """测试冲突问题格式一致性"""
        questions_budget = ConflictQuestionGenerator.generate(MOCK_FEASIBILITY_WITH_BUDGET_CONFLICT)
        questions_timeline = ConflictQuestionGenerator.generate(MOCK_FEASIBILITY_WITH_TIMELINE_CONFLICT)

        # 验证所有问题都遵循相同的格式
        for questions in [questions_budget, questions_timeline]:
            if questions:
                q = questions[0]
                # 验证必须字段存在
                assert "id" in q
                assert "question" in q
                assert "context" in q
                assert "type" in q
                assert "options" in q
                assert "source" in q
                assert "severity" in q

                # 验证问题以emoji警告开头
                assert q["question"].startswith("⚠️")

                # 验证context提到V1.5
                assert "V1.5" in q["context"]


class TestQuestionnaireInjection:
    """测试冲突问题注入到问卷的逻辑"""

    def test_conflict_questions_injected_after_single_choice(self):
        """测试冲突问题插入到单选题之后"""
        # 构造一个模拟的问卷
        original_questions = [
            {"id": "q1", "type": "single_choice", "question": "原始单选题1"},
            {"id": "q2", "type": "single_choice", "question": "原始单选题2"},
            {"id": "q3", "type": "multiple_choice", "question": "原始多选题1"},
            {"id": "q4", "type": "open_ended", "question": "原始开放题1"},
        ]

        # 生成冲突问题
        # 🔧 v7.4.1: 必须传入 user_mentioned_constraints
        conflict_questions = ConflictQuestionGenerator.generate(
            MOCK_FEASIBILITY_WITH_BUDGET_CONFLICT,
            scenario_type="design_execution",
            user_mentioned_constraints=["budget"],
        )

        # 模拟注入逻辑（与实际代码一致）
        insert_position = 0
        for i, q in enumerate(original_questions):
            if q.get("type") != "single_choice":
                insert_position = i
                break

        updated_questions = (
            original_questions[:insert_position] + conflict_questions + original_questions[insert_position:]
        )

        # 验证注入位置正确（在第2个单选题之后，第1个多选题之前）
        assert len(updated_questions) == 5
        assert updated_questions[0]["id"] == "q1"
        assert updated_questions[1]["id"] == "q2"
        assert updated_questions[2]["id"] == "v15_budget_conflict"  # 冲突问题在这里
        assert updated_questions[3]["id"] == "q3"
        assert updated_questions[4]["id"] == "q4"

        # 验证题型顺序正确：单选→单选→单选(V1.5冲突)→多选→开放
        types = [q["type"] for q in updated_questions]
        assert types == ["single_choice", "single_choice", "single_choice", "multiple_choice", "open_ended"]


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
