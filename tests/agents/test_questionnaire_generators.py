"""
问卷生成器单元测试

测试从 calibration_questionnaire.py 提取的问卷生成器模块。
"""

import pytest
from typing import Dict, Any

from intelligent_project_analyzer.interaction.questionnaire import (
    QuestionContext,
    FallbackQuestionGenerator,
    PhilosophyQuestionGenerator,
    BiddingStrategyGenerator,
    ConflictQuestionGenerator,
    QuestionAdjuster,
    AnswerParser,
)


class TestFallbackQuestionGenerator:
    """测试兜底问题生成器"""

    def test_generate_basic(self):
        """测试基本问题生成"""
        structured_data = {
            "project_task": "设计一个咖啡馆",
            "design_challenge": "功能性与艺术性的平衡",
            "project_type": "commercial_enterprise",
            "resource_constraints": "预算有限",
        }

        questions = FallbackQuestionGenerator.generate(structured_data)

        # 验证问题数量（7-10个）
        assert 7 <= len(questions) <= 10, f"Expected 7-10 questions, got {len(questions)}"

        # 验证问题类型分布
        single_choice = [q for q in questions if q["type"] == "single_choice"]
        multiple_choice = [q for q in questions if q["type"] == "multiple_choice"]
        open_ended = [q for q in questions if q["type"] == "open_ended"]

        assert len(single_choice) >= 2, "Should have at least 2 single choice questions"
        assert len(multiple_choice) >= 2, "Should have at least 2 multiple choice questions"
        assert len(open_ended) == 2, "Should have exactly 2 open-ended questions"

    def test_generate_with_tension_extraction(self):
        """测试核心矛盾提取"""
        structured_data = {"design_challenge": '"快速迭代需求"与"品牌稳定性"的对立', "project_type": "commercial_enterprise"}

        questions = FallbackQuestionGenerator.generate(structured_data)

        # 验证第一个问题包含提取的矛盾（检查问题ID而不是文本内容，避免编码问题）
        first_question = questions[0]
        assert first_question["id"] in ["core_tension_priority", "orientation_preference"]
        assert first_question["type"] == "single_choice"

    def test_generate_residential_vs_commercial(self):
        """测试住宅与商业项目的问题差异"""
        residential_data = {"project_type": "personal_residential"}
        commercial_data = {"project_type": "commercial_enterprise"}

        residential_questions = FallbackQuestionGenerator.generate(residential_data)
        commercial_questions = FallbackQuestionGenerator.generate(commercial_data)

        # 验证住宅项目包含感官体验问题
        residential_ids = [q["id"] for q in residential_questions]
        assert "sensory_experience" in residential_ids

        # 验证商业项目包含商业体验问题
        commercial_ids = [q["id"] for q in commercial_questions]
        assert "commercial_experience" in commercial_ids


class TestPhilosophyQuestionGenerator:
    """测试理念探索问题生成器"""

    def test_generate_with_design_challenge(self):
        """测试基于设计挑战生成理念问题"""
        structured_data = {
            "design_challenge": "作为[创业者]的[快速迭代需求]与[品牌稳定性]",
            "project_task": "雇佣空间完成[功能性]与[情感化]",
            "expert_handoff": {
                "design_challenge_spectrum": {"极端A": {"标签": "极简主义"}, "极端B": {"标签": "奢华主义"}, "中间立场": [{"标签": "现代简约"}]}
            },
        }

        questions = PhilosophyQuestionGenerator.generate(structured_data)

        assert len(questions) > 0, "Should generate at least one philosophy question"

        # 验证问题包含理念相关内容
        question_texts = [q["question"] for q in questions]
        assert any("理念" in text or "认同" in text for text in question_texts)

    def test_generate_empty_data(self):
        """测试空数据情况"""
        structured_data = {}

        questions = PhilosophyQuestionGenerator.generate(structured_data)

        # 空数据应该返回空列表或不崩溃
        assert isinstance(questions, list)


class TestBiddingStrategyGenerator:
    """测试竞标策略问题生成器"""

    def test_generate_with_competitors(self):
        """测试包含竞争对手的场景"""
        user_input = "我们要参加成都某酒店项目的竞标，对手有HBA、CCD等重量级设计公司"
        structured_data = {"project_type": "commercial_enterprise"}

        questions = BiddingStrategyGenerator.generate(user_input, structured_data)

        assert len(questions) > 0, "Should generate bidding strategy questions"

        # 验证问题包含竞争对手信息
        question_texts = " ".join([q["question"] for q in questions])
        assert "HBA" in question_texts or "CCD" in question_texts or "重量级" in question_texts

    def test_generate_basic_bidding(self):
        """测试基本竞标场景"""
        user_input = "竞标项目"
        structured_data = {}

        questions = BiddingStrategyGenerator.generate(user_input, structured_data)

        # 应该生成至少3个问题（差异化、对手弱点、评委打动点等）
        assert len(questions) >= 3


class TestConflictQuestionGenerator:
    """测试资源冲突问题生成器"""

    def test_generate_budget_conflict(self):
        """测试预算冲突问题生成"""
        feasibility = {
            "conflict_detection": {
                "budget_conflicts": [
                    {
                        "detected": True,
                        "severity": "critical",
                        "description": "预算不足",
                        "details": {"gap": 500000, "gap_percentage": 30},
                    }
                ]
            }
        }

        # 🔧 v7.4.1: 必须传入 user_mentioned_constraints 参数
        questions = ConflictQuestionGenerator.generate(
            feasibility, "design_execution", user_mentioned_constraints=["budget"]  # 用户提及了预算约束
        )

        assert len(questions) > 0, "Should generate conflict questions"

        # 验证问题包含预算相关内容
        first_question = questions[0]
        assert "预算" in first_question["question"]
        assert first_question["type"] == "single_choice"

    def test_skip_conflicts_for_bidding_scenario(self):
        """测试竞标场景跳过施工冲突"""
        feasibility = {
            "conflict_detection": {
                "budget_conflicts": [{"detected": True, "severity": "critical", "description": "预算不足"}]
            }
        }

        questions = ConflictQuestionGenerator.generate(feasibility, "bidding_strategy")

        # 竞标场景应该跳过施工相关冲突
        assert len(questions) == 0, "Bidding strategy should skip construction conflicts"

    def test_no_conflicts(self):
        """测试无冲突情况"""
        feasibility = {"conflict_detection": {}}

        questions = ConflictQuestionGenerator.generate(feasibility, "design_execution")

        assert len(questions) == 0, "Should return empty list when no conflicts"


class TestQuestionAdjuster:
    """测试问题数量调整器"""

    def test_adjust_no_trimming_needed(self):
        """测试不需要裁剪的情况"""
        philosophy_questions = [{"id": "q1", "type": "single_choice"}]
        conflict_questions = [{"id": "q2", "type": "single_choice"}]

        adjusted_phil, adjusted_conf = QuestionAdjuster.adjust(
            philosophy_questions=philosophy_questions,
            conflict_questions=conflict_questions,
            original_question_count=5,
            feasibility_data={},
        )

        # 总长度 <= 7，不应该裁剪
        assert len(adjusted_phil) == 1
        assert len(adjusted_conf) == 1

    def test_adjust_with_trimming(self):
        """测试需要裁剪的情况"""
        philosophy_questions = [
            {"id": f"phil_{i}", "type": "single_choice", "dimension": "philosophy"} for i in range(5)
        ]
        conflict_questions = [{"id": f"conf_{i}", "type": "single_choice", "severity": "medium"} for i in range(5)]

        adjusted_phil, adjusted_conf = QuestionAdjuster.adjust(
            philosophy_questions=philosophy_questions,
            conflict_questions=conflict_questions,
            original_question_count=10,  # Total: 20, should trigger heavy trimming
            feasibility_data={},
        )

        # 总长度 >= 14，应该重度裁剪（保留40%）
        total_adjusted = len(adjusted_phil) + len(adjusted_conf)
        assert total_adjusted < 10, f"Expected trimming, got {total_adjusted} questions"


class TestAnswerParser:
    """测试答案解析器"""

    def test_extract_raw_answers_from_dict(self):
        """测试从字典提取答案"""
        user_response = {"answers": {"q1": "答案1", "q2": "答案2"}, "additional_info": "补充说明"}

        raw_answers, notes = AnswerParser.extract_raw_answers(user_response)

        assert raw_answers == {"q1": "答案1", "q2": "答案2"}
        assert notes == "补充说明"

    def test_extract_raw_answers_from_list(self):
        """测试从列表提取答案"""
        user_response = [{"question_id": "q1", "answer": "答案1"}, {"question_id": "q2", "answer": "答案2"}]

        raw_answers, notes = AnswerParser.extract_raw_answers(user_response)

        assert isinstance(raw_answers, list)
        assert len(raw_answers) == 2

    def test_build_answer_entries(self):
        """测试构建答案条目"""
        questionnaire = {
            "questions": [
                {"id": "q1", "question": "问题1", "type": "single_choice"},
                {"id": "q2", "question": "问题2", "type": "multiple_choice"},
            ]
        }
        raw_answers = {"q1": "选项A", "q2": ["选项B", "选项C"]}

        entries, answers_map = AnswerParser.build_answer_entries(questionnaire, raw_answers)

        assert len(entries) == 2
        assert entries[0]["id"] == "q1"
        assert entries[0]["value"] == "选项A"
        assert entries[1]["id"] == "q2"
        assert entries[1]["value"] == ["选项B", "选项C"]

        assert answers_map["q1"] == "选项A"
        assert answers_map["q2"] == ["选项B", "选项C"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
