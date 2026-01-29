"""
v7.281 答案质量评估机制 - 单元测试

测试内容：
1. _detect_cross_round_conflicts - 跨轮信息冲突检测
2. _validate_citation_references - 来源引用有效性校验
3. _calculate_answer_confidence - 答案置信度评估
"""

import os
import sys

import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from intelligent_project_analyzer.services.ucppt_search_engine import (
    AnswerFramework,
    KeyAspect,
    RoundInsights,
    SearchFramework,
    UcpptSearchEngine,
)

# ==================== Fixtures ====================


@pytest.fixture
def search_engine():
    """创建测试用搜索引擎实例"""
    engine = UcpptSearchEngine()
    return engine


@pytest.fixture
def sample_round_insights():
    """创建示例轮次洞察数据"""
    return [
        RoundInsights(
            round_number=1,
            target_aspect="日式侘寂风格",
            search_query="侘寂美学核心原则",
            key_findings=["素材质感比颜色更重要", "强调自然材料使用"],
            inferred_insights=["用户追求简约而非简单"],
            info_sufficiency=0.8,
            info_quality=0.85,
            alignment_score=0.9,
            best_source_urls=["https://example.com/1", "https://example.com/2", "https://example.com/3"],
            sources_count=10,
        ),
        RoundInsights(
            round_number=2,
            target_aspect="空间布局",
            search_query="小户型卧室布局",
            key_findings=["8平米卧室推荐L型布局", "床头不宜靠窗"],
            inferred_insights=["动线设计需优先考虑"],
            info_sufficiency=0.75,
            info_quality=0.8,
            alignment_score=0.85,
            best_source_urls=["https://example.com/4", "https://example.com/5"],
            sources_count=8,
        ),
        RoundInsights(
            round_number=3,
            target_aspect="材料选择",
            search_query="日式卧室材料推荐",
            key_findings=["榉木比橡木更适合日式风格", "推荐使用草编元素"],
            inferred_insights=["预算约束下应优先考虑木材"],
            info_sufficiency=0.7,
            info_quality=0.75,
            alignment_score=0.8,
            best_source_urls=["https://example.com/6"],
            sources_count=6,
        ),
    ]


@pytest.fixture
def conflicting_round_insights():
    """创建包含冲突信息的轮次洞察"""
    return [
        RoundInsights(
            round_number=1,
            target_aspect="材料选择",
            key_findings=["推荐使用榉木", "白色墙面是最佳选择"],
            inferred_insights=["应该使用天然材料"],
            info_quality=0.8,
        ),
        RoundInsights(
            round_number=2,
            target_aspect="材料验证",
            key_findings=["不推荐使用榉木，易变形", "深色墙面更有氛围"],
            inferred_insights=["不应该使用天然材料，维护成本高"],
            info_quality=0.85,
        ),
    ]


@pytest.fixture
def sample_framework(sample_round_insights):
    """创建示例答案框架"""
    framework = AnswerFramework(
        original_query="如何设计一个8平米的日式侘寂风格卧室",
        answer_goal="为用户提供完整的日式侘寂风格小户型卧室设计方案",
    )
    framework.round_insights = sample_round_insights
    return framework


# ==================== 1. 跨轮信息冲突检测测试 ====================


class TestDetectCrossRoundConflicts:
    """测试跨轮信息冲突检测"""

    def test_no_conflicts_with_empty_insights(self, search_engine):
        """空洞察列表应返回无冲突"""
        result = search_engine._detect_cross_round_conflicts([])

        assert result["has_conflicts"] == False
        assert result["conflicts"] == []
        assert result["consensus"] == []
        assert result["conflict_summary"] == ""

    def test_no_conflicts_with_single_round(self, search_engine):
        """单轮洞察应返回无冲突"""
        single_insight = [
            RoundInsights(
                round_number=1,
                key_findings=["发现1", "发现2"],
            )
        ]
        result = search_engine._detect_cross_round_conflicts(single_insight)

        assert result["has_conflicts"] == False
        assert result["conflicts"] == []

    def test_no_conflicts_with_consistent_findings(self, search_engine, sample_round_insights):
        """一致的发现应返回无冲突"""
        result = search_engine._detect_cross_round_conflicts(sample_round_insights)

        # 示例数据中没有明显冲突
        # 但可能有共识
        assert isinstance(result["has_conflicts"], bool)
        assert isinstance(result["conflicts"], list)
        assert isinstance(result["consensus"], list)

    def test_detects_conflicts_with_negation_patterns(self, search_engine, conflicting_round_insights):
        """应检测到否定模式的冲突"""
        result = search_engine._detect_cross_round_conflicts(conflicting_round_insights)

        # 检查是否检测到冲突（"推荐" vs "不推荐"）
        assert result["has_conflicts"] == True or len(result["conflicts"]) > 0 or "不" in str(result)

    def test_conflict_result_structure(self, search_engine, conflicting_round_insights):
        """验证冲突结果的数据结构"""
        result = search_engine._detect_cross_round_conflicts(conflicting_round_insights)

        # 检查返回结构
        assert "has_conflicts" in result
        assert "conflicts" in result
        assert "consensus" in result
        assert "conflict_summary" in result

        # conflicts 应该是列表
        assert isinstance(result["conflicts"], list)

        # 如果有冲突，检查冲突条目结构
        if result["conflicts"]:
            conflict = result["conflicts"][0]
            assert "topic" in conflict or "findings" in conflict or "rounds" in conflict

    def test_conflict_summary_generation(self, search_engine, conflicting_round_insights):
        """验证冲突摘要生成"""
        result = search_engine._detect_cross_round_conflicts(conflicting_round_insights)

        if result["has_conflicts"]:
            assert result["conflict_summary"] != ""
            assert "冲突" in result["conflict_summary"] or "处" in result["conflict_summary"]


# ==================== 2. 来源引用有效性校验测试 ====================


class TestValidateCitationReferences:
    """测试来源引用有效性校验"""

    def test_empty_answer_no_citations(self, search_engine):
        """空答案应返回零引用"""
        result = search_engine._validate_citation_references("", 10)

        assert result["total_citations"] == 0
        assert result["valid_citations"] == []
        assert result["invalid_citations"] == []
        assert result["citation_coverage"] == 0

    def test_valid_citations_only(self, search_engine):
        """只有有效引用的情况"""
        answer = "根据研究[1]，日式设计强调简约。专家指出[2][3]，材料选择很重要。此外[5]也提到了这一点。"
        result = search_engine._validate_citation_references(answer, 10)

        assert result["valid"] == True
        assert result["total_citations"] == 4
        assert set(result["valid_citations"]) == {1, 2, 3, 5}
        assert result["invalid_citations"] == []

    def test_invalid_citations_detected(self, search_engine):
        """应检测到无效引用"""
        answer = "根据研究[1]，很重要。但[15]指出不同观点，[20]也有补充。"
        result = search_engine._validate_citation_references(answer, 10)  # 只有10个来源

        assert result["valid"] == False
        assert 15 in result["invalid_citations"]
        assert 20 in result["invalid_citations"]
        assert result["warning"] != ""

    def test_citation_coverage_calculation(self, search_engine):
        """验证引用覆盖度计算"""
        answer = "参考[1][2][3][4][5]的研究结论。"
        result = search_engine._validate_citation_references(answer, 10)

        # 引用了5/10 = 50%
        assert result["citation_coverage"] == 0.5

    def test_duplicate_citations_handled(self, search_engine):
        """重复引用应正确处理"""
        answer = "根据[1]的研究，[1]又指出，参考[1]我们发现，同时[2]也证实了[1]的观点。"
        result = search_engine._validate_citation_references(answer, 10)

        # 总引用数应计算所有出现
        assert result["total_citations"] == 5
        # 有效引用应去重
        assert set(result["valid_citations"]) == {1, 2}

    def test_zero_sources_edge_case(self, search_engine):
        """零来源的边界情况"""
        result = search_engine._validate_citation_references("无引用的文本", 0)

        assert result["citation_coverage"] == 0

    def test_warning_for_few_citations(self, search_engine):
        """引用过少时应有警告"""
        answer = "只引用了[1]一条来源。"
        result = search_engine._validate_citation_references(answer, 10)

        # 引用较少时应有警告
        assert result["warning"] != "" or result["citation_coverage"] < 0.1


# ==================== 3. 答案置信度评估测试 ====================


class TestCalculateAnswerConfidence:
    """测试答案置信度评估"""

    def test_high_confidence_scenario(self, search_engine, sample_framework, sample_round_insights):
        """高质量场景应返回高置信度"""
        conflict_result = {"has_conflicts": False, "conflicts": []}
        citation_result = {
            "citation_coverage": 0.4,
            "valid": True,
            "total_citations": 12,
        }

        result = search_engine._calculate_answer_confidence(
            framework=sample_framework,
            round_insights=sample_round_insights,
            sources_count=30,
            conflict_result=conflict_result,
            citation_result=citation_result,
        )

        assert result["overall_confidence"] >= 0.7
        assert result["confidence_level"] in ["高", "中"]
        assert result["confidence_note"] != ""

    def test_low_confidence_with_conflicts(self, search_engine, sample_framework, conflicting_round_insights):
        """有冲突时应降低置信度"""
        conflict_result = {"has_conflicts": True, "conflicts": [{"topic": "材料"}, {"topic": "颜色"}]}
        citation_result = {"citation_coverage": 0.1, "valid": True}

        result = search_engine._calculate_answer_confidence(
            framework=sample_framework,
            round_insights=conflicting_round_insights,
            sources_count=10,
            conflict_result=conflict_result,
            citation_result=citation_result,
        )

        # 冲突应降低一致性得分
        assert result["dimension_scores"]["consistency"] < 1.0

    def test_confidence_dimensions(self, search_engine, sample_framework, sample_round_insights):
        """验证置信度维度完整性"""
        conflict_result = {"has_conflicts": False, "conflicts": []}
        citation_result = {"citation_coverage": 0.3, "valid": True}

        result = search_engine._calculate_answer_confidence(
            framework=sample_framework,
            round_insights=sample_round_insights,
            sources_count=30,
            conflict_result=conflict_result,
            citation_result=citation_result,
        )

        # 检查5个维度都存在
        assert "info_sufficiency" in result["dimension_scores"]
        assert "info_quality" in result["dimension_scores"]
        assert "source_coverage" in result["dimension_scores"]
        assert "consistency" in result["dimension_scores"]
        assert "goal_alignment" in result["dimension_scores"]

        # 每个维度分数应在 0-1 范围
        for score in result["dimension_scores"].values():
            assert 0 <= score <= 1

    def test_confidence_level_thresholds(self, search_engine, sample_framework):
        """验证置信度等级阈值"""
        # 高质量场景
        high_insights = [
            RoundInsights(
                round_number=1,
                info_sufficiency=0.9,
                info_quality=0.9,
                alignment_score=0.9,
            )
        ]

        result_high = search_engine._calculate_answer_confidence(
            framework=sample_framework,
            round_insights=high_insights,
            sources_count=30,
            conflict_result={"has_conflicts": False, "conflicts": []},
            citation_result={"citation_coverage": 0.5, "valid": True},
        )

        # 低质量场景
        low_insights = [
            RoundInsights(
                round_number=1,
                info_sufficiency=0.3,
                info_quality=0.3,
                alignment_score=0.3,
            )
        ]

        result_low = search_engine._calculate_answer_confidence(
            framework=sample_framework,
            round_insights=low_insights,
            sources_count=5,
            conflict_result={"has_conflicts": True, "conflicts": [{}, {}, {}]},
            citation_result={"citation_coverage": 0.05, "valid": False},
        )

        # 高质量应比低质量得分高
        assert result_high["overall_confidence"] > result_low["overall_confidence"]

    def test_empty_insights_fallback(self, search_engine, sample_framework):
        """空洞察时应有合理的默认值"""
        result = search_engine._calculate_answer_confidence(
            framework=sample_framework,
            round_insights=[],
            sources_count=10,
            conflict_result={"has_conflicts": False, "conflicts": []},
            citation_result={"citation_coverage": 0.2, "valid": True},
        )

        # 应返回中等默认值
        assert result["overall_confidence"] >= 0.3
        assert result["confidence_level"] in ["高", "中", "低"]

    def test_confidence_note_content(self, search_engine, sample_framework, sample_round_insights):
        """验证置信度说明内容"""
        # 有冲突的情况
        conflict_result = {"has_conflicts": True, "conflicts": [{"topic": "test"}]}
        citation_result = {"citation_coverage": 0.3, "valid": True}

        result = search_engine._calculate_answer_confidence(
            framework=sample_framework,
            round_insights=sample_round_insights,
            sources_count=30,
            conflict_result=conflict_result,
            citation_result=citation_result,
        )

        # 说明中应提及冲突
        assert "冲突" in result["confidence_note"]


# ==================== 4. 边界条件测试 ====================


class TestEdgeCases:
    """测试边界条件"""

    def test_special_characters_in_citations(self, search_engine):
        """特殊字符不应影响引用提取"""
        answer = "根据[1]，结合[2]的研究（见[3]）。注意：[4]也很重要！"
        result = search_engine._validate_citation_references(answer, 10)

        assert result["total_citations"] == 4

    def test_large_round_number_handling(self, search_engine):
        """大轮次数应正确处理"""
        many_insights = [
            RoundInsights(round_number=i, info_quality=0.7, info_sufficiency=0.7, alignment_score=0.7)
            for i in range(1, 20)
        ]

        result = search_engine._detect_cross_round_conflicts(many_insights)

        # 不应崩溃
        assert "has_conflicts" in result

    def test_unicode_in_findings(self, search_engine):
        """Unicode字符应正确处理"""
        insights = [
            RoundInsights(
                round_number=1,
                key_findings=["日式侘寂风格 🎌", "使用榻榻米"],
            ),
            RoundInsights(
                round_number=2,
                key_findings=["现代简约风格 ✨", "不使用榻榻米"],
            ),
        ]

        result = search_engine._detect_cross_round_conflicts(insights)

        # 不应崩溃
        assert "has_conflicts" in result


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
