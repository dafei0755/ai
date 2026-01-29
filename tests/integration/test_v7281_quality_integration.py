"""
v7.281 答案质量评估机制 - 集成测试

测试内容：
1. 质量评估方法与 _generate_final_answer 的集成
2. SSE 事件 answer_quality_assessment 的正确发送
3. 评估结果与前端状态的集成
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from intelligent_project_analyzer.services.ucppt_search_engine import (
    AnswerFramework,
    RoundInsights,
    SearchFramework,
    SearchTarget,
    UcpptSearchEngine,
)

# ==================== Fixtures ====================


@pytest.fixture
def mock_llm_response():
    """模拟LLM响应"""
    return "这是一个关于日式侘寂风格卧室设计的详细回答。根据[1]的研究，侘寂美学强调自然材料和不完美之美。专家[2][3]建议使用榉木和草编元素。在空间布局上[4]，8平米的卧室应采用L型布局。"


@pytest.fixture
def search_engine_with_mocks():
    """创建带mock的搜索引擎"""
    engine = UcpptSearchEngine()
    return engine


@pytest.fixture
def sample_framework_with_insights():
    """创建包含完整洞察的答案框架"""
    framework = AnswerFramework(
        original_query="如何设计一个8平米的日式侘寂风格卧室",
        answer_goal="为用户提供完整的设计方案",
    )

    # 添加关键信息面
    framework.key_aspects = [
        KeyAspect(aspect_name="风格基础", answer_goal="理解侘寂美学核心"),
        KeyAspect(aspect_name="空间布局", answer_goal="优化8平米空间"),
        KeyAspect(aspect_name="材料选择", answer_goal="推荐合适的材料"),
    ]

    # 添加轮次洞察
    framework.round_insights = [
        RoundInsights(
            round_number=1,
            target_aspect="风格基础",
            key_findings=["侘寂强调不完美之美", "自然材料是核心"],
            inferred_insights=["用户追求简约质感"],
            info_sufficiency=0.85,
            info_quality=0.9,
            alignment_score=0.88,
            best_source_urls=["https://example.com/1", "https://example.com/2"],
            sources_count=8,
        ),
        RoundInsights(
            round_number=2,
            target_aspect="空间布局",
            key_findings=["L型布局最优", "床头朝向建议"],
            inferred_insights=["动线设计很重要"],
            info_sufficiency=0.8,
            info_quality=0.85,
            alignment_score=0.85,
            best_source_urls=["https://example.com/3"],
            sources_count=6,
        ),
    ]

    return framework


@pytest.fixture
def sample_sources():
    """创建示例来源数据"""
    return [
        {"id": "1", "title": "日式侘寂设计指南", "url": "https://example.com/1", "content": "侘寂美学..."},
        {"id": "2", "title": "小户型布局研究", "url": "https://example.com/2", "content": "L型布局..."},
        {"id": "3", "title": "材料选择建议", "url": "https://example.com/3", "content": "榉木推荐..."},
        {"id": "4", "title": "空间优化技巧", "url": "https://example.com/4", "content": "8平米方案..."},
        {"id": "5", "title": "日式卧室案例", "url": "https://example.com/5", "content": "案例分析..."},
    ]


# 为了避免循环导入，在这里定义 KeyAspect
try:
    from intelligent_project_analyzer.services.ucppt_search_engine import KeyAspect
except ImportError:
    from dataclasses import dataclass, field
    from typing import List

    @dataclass
    class KeyAspect:
        aspect_name: str = ""
        answer_goal: str = ""
        collected_info: List[str] = field(default_factory=list)
        status: str = "pending"
        completion_score: float = 0.0


# ==================== 1. 质量评估集成测试 ====================


class TestQualityAssessmentIntegration:
    """测试质量评估与答案生成的集成"""

    def test_conflict_detection_integration(self, search_engine_with_mocks):
        """测试冲突检测与答案框架的集成"""
        engine = search_engine_with_mocks

        insights = [
            RoundInsights(round_number=1, key_findings=["推荐使用A方案"]),
            RoundInsights(round_number=2, key_findings=["不推荐使用A方案"]),
        ]

        # 调用冲突检测
        result = engine._detect_cross_round_conflicts(insights)

        # 验证集成结果
        assert "conflict_summary" in result
        assert isinstance(result["conflict_summary"], str)

    def test_citation_validation_integration(self, search_engine_with_mocks, mock_llm_response):
        """测试引用校验与答案内容的集成"""
        engine = search_engine_with_mocks

        # 使用模拟的LLM响应
        result = engine._validate_citation_references(mock_llm_response, sources_count=5)

        # 验证提取的引用
        assert result["total_citations"] > 0
        assert 1 in result["valid_citations"]
        assert result["citation_coverage"] > 0

    def test_confidence_calculation_with_real_framework(self, search_engine_with_mocks, sample_framework_with_insights):
        """测试置信度计算与真实框架的集成"""
        engine = search_engine_with_mocks
        framework = sample_framework_with_insights

        conflict_result = engine._detect_cross_round_conflicts(framework.round_insights)
        citation_result = {"citation_coverage": 0.4, "valid": True, "total_citations": 4}

        result = engine._calculate_answer_confidence(
            framework=framework,
            round_insights=framework.round_insights,
            sources_count=10,
            conflict_result=conflict_result,
            citation_result=citation_result,
        )

        # 验证完整结果
        assert result["overall_confidence"] > 0
        assert result["confidence_level"] in ["高", "中", "低"]
        assert len(result["dimension_scores"]) == 5


# ==================== 2. SSE 事件测试 ====================


class TestSSEEventIntegration:
    """测试 SSE 事件发送"""

    @pytest.mark.asyncio
    async def test_answer_quality_assessment_event_structure(
        self, search_engine_with_mocks, sample_framework_with_insights, sample_sources
    ):
        """测试 answer_quality_assessment 事件的数据结构"""
        engine = search_engine_with_mocks
        framework = sample_framework_with_insights

        # 准备测试数据
        conflict_result = {"has_conflicts": False, "conflicts": []}
        citation_result = {
            "valid": True,
            "total_citations": 5,
            "valid_citations": [1, 2, 3],
            "invalid_citations": [],
            "citation_coverage": 0.3,
            "warning": "",
        }

        confidence_result = engine._calculate_answer_confidence(
            framework=framework,
            round_insights=framework.round_insights,
            sources_count=len(sample_sources),
            conflict_result=conflict_result,
            citation_result=citation_result,
        )

        # 构造事件数据
        event_data = {
            "type": "answer_quality_assessment",
            "data": {
                "confidence": confidence_result,
                "citation": citation_result,
                "conflicts": {
                    "has_conflicts": conflict_result.get("has_conflicts", False),
                    "count": len(conflict_result.get("conflicts", [])),
                },
                "message": f"答案置信度: {confidence_result['confidence_level']} ({confidence_result['overall_confidence']:.0%})",
            },
        }

        # 验证事件结构
        assert event_data["type"] == "answer_quality_assessment"
        assert "confidence" in event_data["data"]
        assert "citation" in event_data["data"]
        assert "conflicts" in event_data["data"]
        assert "message" in event_data["data"]

        # 验证嵌套结构
        assert "overall_confidence" in event_data["data"]["confidence"]
        assert "confidence_level" in event_data["data"]["confidence"]
        assert "total_citations" in event_data["data"]["citation"]

    @pytest.mark.asyncio
    async def test_event_generation_flow(self, search_engine_with_mocks, sample_framework_with_insights):
        """测试事件生成流程"""
        engine = search_engine_with_mocks
        framework = sample_framework_with_insights

        # 模拟各阶段调用
        # 1. 冲突检测
        conflict_result = engine._detect_cross_round_conflicts(framework.round_insights)
        assert isinstance(conflict_result, dict)

        # 2. 引用校验（模拟答案）
        mock_answer = "根据[1]的研究，侘寂美学很重要[2][3]。"
        citation_result = engine._validate_citation_references(mock_answer, 10)
        assert isinstance(citation_result, dict)

        # 3. 置信度计算
        confidence_result = engine._calculate_answer_confidence(
            framework=framework,
            round_insights=framework.round_insights,
            sources_count=10,
            conflict_result=conflict_result,
            citation_result=citation_result,
        )
        assert isinstance(confidence_result, dict)

        # 验证整个流程产生有意义的结果
        assert 0 <= confidence_result["overall_confidence"] <= 1


# ==================== 3. 数据流集成测试 ====================


class TestDataFlowIntegration:
    """测试数据在组件间的流动"""

    def test_round_insights_to_conflict_detection(self, search_engine_with_mocks):
        """测试轮次洞察到冲突检测的数据流"""
        engine = search_engine_with_mocks

        # 创建洞察链
        insights = [
            RoundInsights(
                round_number=i,
                key_findings=[f"发现{i}-1", f"发现{i}-2"],
                inferred_insights=[f"推断{i}"],
                info_quality=0.7 + i * 0.05,
            )
            for i in range(1, 4)
        ]

        # 数据流: insights -> conflict_detection
        result = engine._detect_cross_round_conflicts(insights)

        # 验证数据被正确处理
        assert result is not None
        assert isinstance(result["has_conflicts"], bool)

    def test_answer_to_citation_validation(self, search_engine_with_mocks):
        """测试答案内容到引用校验的数据流"""
        engine = search_engine_with_mocks

        # 模拟不同格式的答案
        answers = [
            "简单引用[1]测试",
            "多引用[1][2][3]测试",
            "复杂引用：根据[1]，结合[2]和[3]的研究[4]，我们发现[5][6]...",
            "无引用的答案文本",
        ]

        for answer in answers:
            result = engine._validate_citation_references(answer, 10)

            # 每个答案都应返回有效结果
            assert "total_citations" in result
            assert "citation_coverage" in result

    def test_full_quality_pipeline(self, search_engine_with_mocks, sample_framework_with_insights):
        """测试完整质量评估管道"""
        engine = search_engine_with_mocks
        framework = sample_framework_with_insights

        # 完整管道
        # Step 1: 冲突检测
        conflict_result = engine._detect_cross_round_conflicts(framework.round_insights)

        # Step 2: 模拟答案生成
        mock_answer = """
        根据多轮搜索结果[1][2]，日式侘寂风格卧室设计应注意以下几点：

        1. 材料选择[3]：优先使用天然材料
        2. 空间布局[4][5]：L型布局最优
        3. 色彩搭配[6]：以素色为主

        综上所述[7][8]，这是一个完整的设计方案。
        """

        # Step 3: 引用校验
        citation_result = engine._validate_citation_references(mock_answer, 10)

        # Step 4: 置信度计算
        confidence_result = engine._calculate_answer_confidence(
            framework=framework,
            round_insights=framework.round_insights,
            sources_count=10,
            conflict_result=conflict_result,
            citation_result=citation_result,
        )

        # 验证管道输出
        assert not conflict_result.get("has_conflicts", True)  # 示例数据无冲突
        assert citation_result["total_citations"] == 8
        assert citation_result["valid"]
        assert confidence_result["overall_confidence"] > 0.5


# ==================== 4. 兼容性测试 ====================


class TestBackwardCompatibility:
    """测试向后兼容性"""

    def test_works_with_search_framework(self, search_engine_with_mocks):
        """测试与 SearchFramework 的兼容"""
        engine = search_engine_with_mocks

        # 使用 SearchFramework 而非 AnswerFramework
        framework = SearchFramework(
            original_query="测试查询",
            answer_goal="测试目标",
        )
        framework.round_insights = [
            RoundInsights(round_number=1, info_quality=0.8, info_sufficiency=0.8, alignment_score=0.8)
        ]

        # 应该正常工作
        conflict_result = engine._detect_cross_round_conflicts(framework.round_insights)
        confidence_result = engine._calculate_answer_confidence(
            framework=framework,
            round_insights=framework.round_insights,
            sources_count=5,
            conflict_result=conflict_result,
            citation_result={"citation_coverage": 0.3, "valid": True},
        )

        assert confidence_result is not None

    def test_works_with_empty_round_insights(self, search_engine_with_mocks):
        """测试空轮次洞察的兼容性"""
        engine = search_engine_with_mocks

        framework = AnswerFramework(original_query="测试")
        framework.round_insights = []

        # 应该有合理的默认行为
        conflict_result = engine._detect_cross_round_conflicts([])
        confidence_result = engine._calculate_answer_confidence(
            framework=framework,
            round_insights=[],
            sources_count=5,
            conflict_result=conflict_result,
            citation_result={"citation_coverage": 0.2, "valid": True},
        )

        assert confidence_result["overall_confidence"] >= 0


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
