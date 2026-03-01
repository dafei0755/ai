"""
理念探索问题生成测试

验证基于V1战略洞察的理念、方案、概念探索问题生成能力。
"""

import pytest
from typing import Dict, Any

from intelligent_project_analyzer.interaction.nodes.calibration_questionnaire import CalibrationQuestionnaireNode
from intelligent_project_analyzer.interaction.questionnaire import (
    PhilosophyQuestionGenerator,
    ConflictQuestionGenerator,
)


# ==================== 测试数据 ====================

MOCK_V1_OUTPUT_WITH_DESIGN_CHALLENGE = {
    "design_challenge": "作为[追求高品质生活的业主]的[全进口材料需求]与[预算约束]的对立",
    "project_task": "为[追求高品质生活的业主]+打造[200㎡豪华别墅]+雇佣空间完成[高端材质展示]与[智能便捷体验]",
    "expert_handoff": {
        "design_challenge_spectrum": {
            "极端A": {"标签": "极致奢华：不计成本，追求顶级品质"},
            "极端B": {"标签": "实用理性：控制预算，满足基本需求"},
            "中间立场": [{"标签": "品质优先：选择性投入，核心区域用好材料"}, {"标签": "分期实施：一期保证基础，二期升级高端"}],
        },
        "critical_questions_for_experts": ["在预算有限的情况下，您是否愿意牺牲部分功能来保证材料品质？", "您更看重的是视觉效果还是触觉体验？"],
    },
}

MOCK_V1_OUTPUT_MINIMAL = {
    "design_challenge": "作为[现代家庭]的[便捷性]与[私密性]的对立",
    "project_task": "为[现代家庭]+打造[智能空间]+雇佣空间完成[自动化控制]与[安全保障]",
    "expert_handoff": {},
}

MOCK_V1_OUTPUT_NO_DATA = {"design_challenge": "", "project_task": "", "expert_handoff": {}}


# ==================== 测试类 ====================


class TestPhilosophyQuestions:
    """理念探索问题生成测试"""

    def test_build_philosophy_questions_from_design_challenge(self):
        """测试基于design_challenge生成理念问题"""
        # 🔧 v7.4.1: 使用 PhilosophyQuestionGenerator 替代已移除的方法
        questions = PhilosophyQuestionGenerator.generate(MOCK_V1_OUTPUT_WITH_DESIGN_CHALLENGE)

        # 验证生成了问题
        assert len(questions) >= 1

        # 查找design_philosophy问题
        design_q = next((q for q in questions if q["id"] == "v1_design_philosophy"), None)
        assert design_q is not None

        # 验证问题结构
        assert design_q["type"] == "single_choice"
        assert "全进口材料需求" in design_q["question"] or "预算约束" in design_q["question"]
        assert "追求高品质生活的业主" in design_q["context"]

        # 验证选项包含4个（2个极端 + 平衡 + 不确定）
        assert len(design_q["options"]) == 4
        assert any("优先" in opt for opt in design_q["options"])
        assert any("不确定" in opt for opt in design_q["options"])

        # 验证来源和维度
        assert design_q["source"] == "v1_strategic_insight"
        assert design_q["dimension"] == "philosophy"

    def test_build_philosophy_questions_from_spectrum(self):
        """测试基于design_challenge_spectrum生成方案倾向问题"""
        questions = PhilosophyQuestionGenerator.generate(MOCK_V1_OUTPUT_WITH_DESIGN_CHALLENGE)

        # 查找approach_spectrum问题
        spectrum_q = next((q for q in questions if q["id"] == "v1_approach_spectrum"), None)
        assert spectrum_q is not None

        # 验证问题结构
        assert spectrum_q["type"] == "single_choice"
        assert "光谱" in spectrum_q["question"] or "立场" in spectrum_q["question"]

        # 验证选项包含极端A、极端B和中间立场
        assert len(spectrum_q["options"]) >= 2
        assert any("极端A" in opt for opt in spectrum_q["options"])
        assert any("极端B" in opt for opt in spectrum_q["options"])
        assert any("中间立场" in opt for opt in spectrum_q["options"])

        # 验证维度
        assert spectrum_q["dimension"] == "approach"

    def test_build_philosophy_questions_from_project_task(self):
        """测试基于project_task生成目标理念问题"""
        questions = PhilosophyQuestionGenerator.generate(MOCK_V1_OUTPUT_WITH_DESIGN_CHALLENGE)

        # 查找goal_philosophy问题
        goal_q = next((q for q in questions if q["id"] == "v1_goal_philosophy"), None)
        assert goal_q is not None

        # 验证问题结构
        assert goal_q["type"] == "single_choice"
        assert "成功" in goal_q["question"] or "看重" in goal_q["question"]

        # 验证选项包含goal_x和goal_y
        assert any("高端材质展示" in opt for opt in goal_q["options"])
        assert any("智能便捷体验" in opt for opt in goal_q["options"])
        assert any("缺一不可" in opt for opt in goal_q["options"])

        # 验证维度
        assert goal_q["dimension"] == "goal"

    def test_build_philosophy_questions_from_critical_questions(self):
        """测试基于critical_questions_for_experts生成开放探索问题"""
        questions = PhilosophyQuestionGenerator.generate(MOCK_V1_OUTPUT_WITH_DESIGN_CHALLENGE)

        # 查找critical_exploration问题
        critical_q = next((q for q in questions if q["id"] == "v1_critical_exploration"), None)
        assert critical_q is not None

        # 验证问题结构
        assert critical_q["type"] == "open_ended"
        assert "牺牲部分功能" in critical_q["question"] or "材料品质" in critical_q["question"]

        # 验证有placeholder
        assert "placeholder" in critical_q
        assert len(critical_q["placeholder"]) > 0

        # 验证维度
        assert critical_q["dimension"] == "exploration"

    def test_build_philosophy_questions_all_types(self):
        """测试生成所有类型的理念问题"""
        questions = PhilosophyQuestionGenerator.generate(MOCK_V1_OUTPUT_WITH_DESIGN_CHALLENGE)

        # 验证生成了4个问题（design_challenge + spectrum + goal + critical）
        assert len(questions) == 4

        # 验证问题ID不重复
        question_ids = [q["id"] for q in questions]
        assert len(set(question_ids)) == 4

        # 验证包含所有维度
        dimensions = {q["dimension"] for q in questions}
        assert "philosophy" in dimensions
        assert "approach" in dimensions
        assert "goal" in dimensions
        assert "exploration" in dimensions

    def test_build_philosophy_questions_minimal_data(self):
        """测试最小数据集生成问题"""
        questions = PhilosophyQuestionGenerator.generate(MOCK_V1_OUTPUT_MINIMAL)

        # 验证至少生成了部分问题
        assert len(questions) >= 1

        # 验证design_philosophy问题存在
        design_q = next((q for q in questions if q["id"] == "v1_design_philosophy"), None)
        assert design_q is not None

    def test_build_philosophy_questions_no_data(self):
        """测试无数据时不生成问题"""
        questions = PhilosophyQuestionGenerator.generate(MOCK_V1_OUTPUT_NO_DATA)

        # 验证不生成任何问题
        assert len(questions) == 0

    def test_philosophy_questions_format_consistency(self):
        """测试理念问题格式一致性"""
        questions = PhilosophyQuestionGenerator.generate(MOCK_V1_OUTPUT_WITH_DESIGN_CHALLENGE)

        # 验证所有问题都遵循相同的格式
        for q in questions:
            # 验证必须字段存在
            assert "id" in q
            assert "question" in q
            assert "context" in q
            assert "type" in q
            assert "source" in q
            assert "dimension" in q

            # 验证来源都是v1_strategic_insight
            assert q["source"] == "v1_strategic_insight"

            # 验证问题以emoji开头
            assert q["question"][0] in ["💭", "🎯", "🌟", "💡"]

            # 验证context提到V1
            assert "V1" in q["context"] or "您" in q["context"]

    def test_philosophy_questions_focus_on_concepts(self):
        """测试理念问题关注方案、理念、概念（而非资源约束）"""
        questions = PhilosophyQuestionGenerator.generate(MOCK_V1_OUTPUT_WITH_DESIGN_CHALLENGE)

        # 验证问题不关注预算数字、工期天数等
        for q in questions:
            question_text = q["question"] + q["context"]
            # 不应包含具体数字（万元、天、㎡等）
            assert "万元" not in question_text
            assert "天" not in question_text or "每天" in question_text  # 允许"每天"这样的表达
            assert "㎡" not in question_text

            # 应包含理念、方案、价值等关键词（开放题除外，因为它直接引用critical_questions）
            if q["type"] != "open_ended":
                conceptual_keywords = ["理念", "方案", "价值", "认同", "倾向", "看重", "追求", "目标", "立场"]
                assert any(keyword in question_text for keyword in conceptual_keywords)


class TestIntegratedQuestionGeneration:
    """测试理念问题和冲突问题的集成生成"""

    def test_philosophy_questions_priority_over_conflict_questions(self):
        """测试理念问题优先于冲突问题注入"""
        # 模拟同时有V1和V1.5数据的场景
        v1_data = MOCK_V1_OUTPUT_WITH_DESIGN_CHALLENGE
        v15_data = {
            "conflict_detection": {
                "budget_conflicts": [
                    {
                        "detected": True,
                        "severity": "critical",
                        "description": "预算20万，但需求成本37万",
                        "details": {"gap": 170000, "gap_percentage": 85},
                    }
                ]
            }
        }

        # 生成两种问题
        # 🔧 v7.4.1: 使用新的生成器类
        philosophy_questions = PhilosophyQuestionGenerator.generate(v1_data)
        conflict_questions = ConflictQuestionGenerator.generate(
            v15_data, scenario_type="design_execution", user_mentioned_constraints=["budget"]  # 用户提及了预算约束
        )

        # 验证两种问题都生成了
        assert len(philosophy_questions) > 0
        assert len(conflict_questions) > 0

        # 验证理念问题和冲突问题可以区分
        philosophy_ids = {q["id"] for q in philosophy_questions}
        conflict_ids = {q["id"] for q in conflict_questions}
        assert philosophy_ids.isdisjoint(conflict_ids)  # ID不重复

        # 验证维度不同
        philosophy_dimensions = {q["dimension"] for q in philosophy_questions}
        assert "philosophy" in philosophy_dimensions or "approach" in philosophy_dimensions

        # 冲突问题没有dimension字段（或dimension不同）
        for cq in conflict_questions:
            assert cq.get("dimension") != "philosophy"


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
