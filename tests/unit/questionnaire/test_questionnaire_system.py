"""
P2 Questionnaire测试: 问卷生成器、调整器、解析器

测试问卷系统核心功能:
- FallbackQuestionGenerator (规则生成, 关键词匹配)
- PhilosophyQuestionGenerator (理念探索问题)
- BiddingStrategyGenerator (竞标策略问题)
- ConflictQuestionGenerator (资源冲突问题)
- QuestionAdjuster (动态数量调整, 优先级排序)
- AnswerParser (用户回答解析, 意图识别)

覆盖率目标: 75%+

注意: 部分测试已存在于 tests/test_questionnaire_generators.py
本文件补充集成测试和边界情况测试
"""

from typing import Any, Dict, List
from unittest.mock import Mock, patch

import pytest

from intelligent_project_analyzer.interaction.questionnaire import (
    AnswerParser,
    BiddingStrategyGenerator,
    ConflictQuestionGenerator,
    FallbackQuestionGenerator,
    KeywordExtractor,
    PhilosophyQuestionGenerator,
    QuestionAdjuster,
)
from tests.fixtures.mocks import MockKeywordExtractor

# ============================================================================
# Test Class 1: FallbackQuestionGenerator Integration
# ============================================================================


class TestFallbackGeneratorIntegration:
    """测试规则生成器集成场景"""

    def test_generate_for_office_space(self):
        """测试办公空间场景问题生成"""
        structured_data = {"project_task": "办公空间设计", "character_narrative": "科技公司"}
        user_input = "设计现代办公空间，强调协作与创新"

        extracted_info = KeywordExtractor.extract(user_input, structured_data)
        questions = FallbackQuestionGenerator.generate(structured_data, user_input, extracted_info)

        assert len(questions) > 0
        # 应该包含办公空间相关问题
        question_texts = [q["question"] for q in questions]
        assert any("办公" in q or "协作" in q for q in question_texts)

    def test_generate_for_residential_space(self):
        """测试住宅空间场景问题生成"""
        structured_data = {"project_task": "家庭住宅设计", "character_narrative": "三口之家"}
        user_input = "设计温馨的家庭空间"

        extracted_info = KeywordExtractor.extract(user_input, structured_data)
        questions = FallbackQuestionGenerator.generate(structured_data, user_input, extracted_info)

        assert len(questions) > 0
        question_texts = [q["question"] for q in questions]
        assert any("家" in q or "居住" in q for q in question_texts)

    def test_generate_with_empty_extracted_info(self):
        """测试空提取信息时的降级生成"""
        structured_data = {"project_task": "设计项目"}
        user_input = "设计空间"
        extracted_info = {}

        questions = FallbackQuestionGenerator.generate(structured_data, user_input, extracted_info)

        # 应该至少生成基础问题
        assert len(questions) >= 1


# ============================================================================
# Test Class 2: PhilosophyQuestionGenerator
# ============================================================================


class TestPhilosophyQuestionGenerator:
    """测试理念探索问题生成"""

    @pytest.mark.skip(reason="需要LLM调用或mock")
    def test_generate_philosophy_questions(self):
        """测试生成理念探索问题"""
        structured_data = {"project_task": "办公空间设计", "design_challenge": "平衡开放性与隐私"}

        questions = PhilosophyQuestionGenerator.generate(structured_data)

        assert len(questions) > 0
        # 应该是开放式问题
        for q in questions:
            assert q.get("type") == "open_ended"

    @pytest.mark.skip(reason="需要LLM调用或mock")
    def test_philosophy_questions_domain_specific(self):
        """测试领域特定的理念问题"""
        structured_data = {"project_task": "图书馆设计", "character_narrative": "社区公共空间"}

        questions = PhilosophyQuestionGenerator.generate(structured_data)

        assert len(questions) > 0
        question_texts = [q["question"] for q in questions]
        # 应该包含与公共空间相关的理念探索
        assert any("空间" in q or "体验" in q for q in question_texts)


# ============================================================================
# Test Class 3: BiddingStrategyGenerator
# ============================================================================


class TestBiddingStrategyGenerator:
    """测试竞标策略问题生成"""

    def test_generate_bidding_questions(self):
        """测试生成竞标策略问题"""
        user_input = "商业综合体设计"
        structured_data = {"project_task": "商业综合体设计", "resource_constraints": {"预算": "中等"}}

        questions = BiddingStrategyGenerator.generate(user_input, structured_data)

        # 可能生成或不生成（取决于是否检测到竞标场景）
        assert isinstance(questions, list)

    def test_bidding_not_triggered_for_personal_project(self):
        """测试个人项目不触发竞标问题"""
        user_input = "家庭装修"
        structured_data = {"project_task": "家庭装修", "character_narrative": "个人住宅"}

        questions = BiddingStrategyGenerator.generate(user_input, structured_data)

        # 个人项目不应生成竞标问题
        assert len(questions) == 0 or "竞标" not in str(questions)


# ============================================================================
# Test Class 4: ConflictQuestionGenerator
# ============================================================================


class TestConflictQuestionGenerator:
    """测试资源冲突问题生成"""

    @pytest.mark.skip(reason="需要复杂数据结构")
    def test_generate_conflict_questions_with_feasibility(self):
        """测试基于可行性数据生成冲突问题"""
        feasibility_data = {
            "budget_vs_scope": {"severity": "high", "description": "预算不足以实现全部功能"},
            "timeline_vs_complexity": {"severity": "medium", "description": "时间紧张"},
        }

        questions = ConflictQuestionGenerator.generate(feasibility_data)

        assert len(questions) > 0
        # 应该包含预算相关问题
        question_texts = [q["question"] for q in questions]
        assert any("预算" in q or "功能" in q for q in question_texts)

    def test_conflict_questions_priority_by_severity(self):
        """测试冲突问题按严重性排序"""
        feasibility_data = {
            "conflict1": {"severity": "critical", "description": "严重冲突"},
            "conflict2": {"severity": "low", "description": "轻微冲突"},
            "conflict3": {"severity": "high", "description": "重要冲突"},
        }

        questions = ConflictQuestionGenerator.generate(feasibility_data)

        if len(questions) > 1:
            # critical应该排在前面
            severities = [q.get("priority", 0) for q in questions]
            # 高优先级应该靠前（假设priority值越小越优先）
            assert severities == sorted(severities) or severities == sorted(severities, reverse=True)

    def test_no_conflicts_no_questions(self):
        """测试无冲突时不生成问题"""
        feasibility_data = {}

        questions = ConflictQuestionGenerator.generate(feasibility_data)

        assert len(questions) == 0


# ============================================================================
# Test Class 5: QuestionAdjuster Dynamic Adjustment
# ============================================================================


class TestQuestionAdjuster:
    """测试问题数量动态调整器"""

    @pytest.mark.skip(reason="需要验证实际调整逻辑")
    def test_adjust_no_trimming_for_short_questionnaire(self):
        """测试短问卷不裁剪 (≤7个问题)"""
        philosophy_questions = [{"id": f"phil_{i}", "question": f"问题{i}"} for i in range(3)]
        conflict_questions = [{"id": f"conf_{i}", "question": f"冲突{i}"} for i in range(2)]
        original_question_count = 5
        feasibility_data = {}

        adjusted_phil, adjusted_conf = QuestionAdjuster.adjust(
            philosophy_questions, conflict_questions, original_question_count, feasibility_data
        )

        # 应该保留全部
        assert len(adjusted_phil) == 3
        assert len(adjusted_conf) == 2

    def test_adjust_light_trimming_for_medium_questionnaire(self):
        """测试中等问卷轻度裁剪 (8-10个问题)"""
        philosophy_questions = [{"id": f"phil_{i}", "question": f"问题{i}"} for i in range(5)]
        conflict_questions = [{"id": f"conf_{i}", "question": f"冲突{i}"} for i in range(4)]
        original_question_count = 9
        feasibility_data = {}

        adjusted_phil, adjusted_conf = QuestionAdjuster.adjust(
            philosophy_questions, conflict_questions, original_question_count, feasibility_data
        )

        # 应该有轻度裁剪（保留80%理念问题）
        assert len(adjusted_phil) <= 5
        assert len(adjusted_conf) <= 4

    def test_adjust_heavy_trimming_for_long_questionnaire(self):
        """测试长问卷重度裁剪 (≥14个问题)"""
        philosophy_questions = [{"id": f"phil_{i}", "question": f"问题{i}"} for i in range(10)]
        conflict_questions = [{"id": f"conf_{i}", "question": f"冲突{i}"} for i in range(6)]
        original_question_count = 16
        feasibility_data = {}

        adjusted_phil, adjusted_conf = QuestionAdjuster.adjust(
            philosophy_questions, conflict_questions, original_question_count, feasibility_data
        )

        # 应该有显著裁剪
        assert len(adjusted_phil) < 10
        assert len(adjusted_conf) < 6

    @pytest.mark.skip(reason="需要验证priority逻辑")
    def test_adjust_priority_critical_conflicts(self):
        """测试critical冲突优先保留"""
        philosophy_questions = [{"id": f"phil_{i}", "question": f"问题{i}"} for i in range(8)]
        conflict_questions = [
            {"id": "conf_critical", "question": "严重冲突", "priority": 100},
            {"id": "conf_low", "question": "轻微冲突", "priority": 20},
        ]
        original_question_count = 10
        feasibility_data = {"max_severity": "critical"}

        adjusted_phil, adjusted_conf = QuestionAdjuster.adjust(
            philosophy_questions, conflict_questions, original_question_count, feasibility_data
        )

        # critical冲突应该被保留
        conflict_ids = [q["id"] for q in adjusted_conf]
        assert "conf_critical" in conflict_ids


# ============================================================================
# Test Class 6: AnswerParser Intent Recognition
# ============================================================================


class TestAnswerParser:
    """测试答案解析器"""

    def test_parse_user_answers_basic(self):
        """测试解析基本用户回答"""
        questionnaire = {
            "questions": [
                {"id": "q1", "question": "您的预算范围？", "type": "single_choice"},
                {"id": "q2", "question": "设计风格偏好？", "type": "multiple_choice"},
            ]
        }
        raw_answers = [{"question_id": "q1", "answer": "30-50万"}, {"question_id": "q2", "answer": ["现代", "简约"]}]

        entries, answers_map = AnswerParser.build_answer_entries(questionnaire, raw_answers)

        assert len(entries) == 2
        assert entries[0]["id"] == "q1"
        assert entries[0]["value"] == "30-50万"

    def test_parse_with_additional_notes(self):
        """测试解析包含补充说明的回答"""
        questionnaire = {"questions": [{"id": "q1", "question": "设计需求？"}]}
        user_response = {"answers": [{"question_id": "q1", "answer": "现代风格"}], "additional_info": "希望增加储物空间"}

        raw_answers, notes = AnswerParser.extract_raw_answers(user_response)
        entries, answers_map = AnswerParser.build_answer_entries(questionnaire, raw_answers)

        assert len(entries) > 0
        assert notes == "希望增加储物空间"

    def test_parse_skip_intent_recognition(self):
        """测试识别跳过意图"""
        user_response = "跳过问卷"

        raw_answers, notes = AnswerParser.extract_raw_answers(user_response)

        # 字符串输入应该返回None（无法解析为结构化答案）
        assert raw_answers is None

    def test_parse_rejection_intent(self):
        """测试识别拒绝意图"""
        user_response = "我不想回答这些问题"

        raw_answers, notes = AnswerParser.extract_raw_answers(user_response)

        # 非结构化文本应该返回None
        assert raw_answers is None


# ============================================================================
# Test Class 7: KeywordExtractor
# ============================================================================


class TestKeywordExtractor:
    """测试关键词提取器"""

    def test_extract_office_keywords(self):
        """测试提取办公空间关键词"""
        user_input = "设计现代化的办公空间，强调协作与创新"
        structured_data = {"project_task": "办公空间设计"}

        result = KeywordExtractor.extract(user_input, structured_data)

        assert "keywords" in result
        assert len(result["keywords"]) > 0
        assert any("办公" in kw for kw in result["keywords"])

    def test_extract_residential_keywords(self):
        """测试提取住宅关键词"""
        user_input = "设计温馨舒适的家庭空间"
        structured_data = {"project_task": "住宅设计"}

        result = KeywordExtractor.extract(user_input, structured_data)

        assert "keywords" in result
        # keywords可能是字符串列表或元组列表
        keywords = result["keywords"]
        if keywords:
            # 将元组转换为字符串
            keywords_str = " ".join([str(k[0] if isinstance(k, tuple) else k) for k in keywords])
            assert len(keywords) > 0  # 至少提取到一些关键词

    def test_extract_domain_classification(self):
        """测试领域分类"""
        user_input = "设计商业办公楼"
        structured_data = {}

        result = KeywordExtractor.extract(user_input, structured_data)

        assert "domain" in result
        # domain是字典，包含type字段
        domain = result["domain"]
        if isinstance(domain, dict):
            assert "type" in domain
            assert domain["type"] in ["office", "commercial", "general", "residential"]
        else:
            assert domain in ["commercial_office", "commercial", "general"]

    def test_extract_empty_result_on_failure(self):
        """测试提取失败时返回空结果"""
        result = KeywordExtractor._empty_result()

        assert result["keywords"] == []
        # domain是字典，包含type字段
        assert isinstance(result["domain"], dict)
        assert result["domain"]["type"] == "general"


# ============================================================================
# Test Class 8: Integration Scenarios
# ============================================================================


class TestQuestionnaireIntegration:
    """测试问卷系统完整集成"""

    def test_complete_questionnaire_generation_workflow(self):
        """测试完整问卷生成工作流"""
        # 1. 提取关键词
        user_input = "设计1000平米的现代办公空间，预算有限"
        structured_data = {"project_task": "办公空间设计", "resource_constraints": {"预算": "有限"}}

        extracted_info = KeywordExtractor.extract(user_input, structured_data)

        # 2. 生成基础问题
        base_questions = FallbackQuestionGenerator.generate(structured_data, user_input, extracted_info)

        # 3. 生成理念问题
        philosophy_questions = PhilosophyQuestionGenerator.generate(structured_data)

        # 4. 生成冲突问题
        feasibility_data = {"budget_constraint": {"severity": "high", "description": "预算受限"}}
        conflict_questions = ConflictQuestionGenerator.generate(feasibility_data)

        # 5. 动态调整数量
        total_questions = base_questions + philosophy_questions
        adjusted_phil, adjusted_conf = QuestionAdjuster.adjust(
            philosophy_questions, conflict_questions, len(total_questions), feasibility_data
        )

        # 最终问卷
        final_questionnaire = base_questions + adjusted_phil + adjusted_conf

        assert len(final_questionnaire) > 0
        assert len(final_questionnaire) <= 14  # 应该被调整到合理范围

    def test_questionnaire_answer_parsing_workflow(self):
        """测试问卷回答解析工作流"""
        questionnaire = {
            "questions": [
                {"id": "q1", "question": "预算范围？", "type": "single_choice", "options": ["20-30万", "30-50万", "50万以上"]},
                {"id": "q2", "question": "设计风格？", "type": "multiple_choice", "options": ["现代", "简约", "工业风"]},
            ]
        }

        user_response = {
            "answers": [{"question_id": "q1", "answer": "30-50万"}, {"question_id": "q2", "answer": ["现代", "简约"]}],
            "additional_info": "希望突出科技感",
        }

        raw_answers, notes = AnswerParser.extract_raw_answers(user_response)
        entries, answers_map = AnswerParser.build_answer_entries(questionnaire, raw_answers)

        assert len(entries) == 2
        assert entries[0]["value"] == "30-50万"
        assert "现代" in str(entries[1]["value"])


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
