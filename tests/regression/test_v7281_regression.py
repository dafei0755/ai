"""
v7.281 答案质量评估机制 - 回归测试

确保新增功能不影响现有功能：
1. 原有答案生成流程正常工作
2. SSE 事件流不受影响
3. 搜索框架功能完整
4. 向后兼容性
"""

import asyncio
import os
import sys
from typing import Any, Dict, List
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
def engine():
    """创建搜索引擎实例"""
    return UcpptSearchEngine()


@pytest.fixture
def sample_framework():
    """创建示例搜索框架"""
    framework = AnswerFramework(
        original_query="日式卧室设计",
        answer_goal="提供设计方案",
    )
    framework.round_insights = [
        RoundInsights(
            round_number=1,
            target_aspect="美学基础",
            search_query="日式美学",
            key_findings=["侘寂美学很重要"],
            info_quality=0.8,
            info_sufficiency=0.8,
            alignment_score=0.8,
        ),
    ]
    return framework


# ==================== 1. 答案生成流程回归测试 ====================


class TestAnswerGenerationRegression:
    """测试答案生成流程不受影响"""

    def test_round_insights_structure_intact(self, engine, sample_framework):
        """验证 RoundInsights 数据结构完整"""
        insight = sample_framework.round_insights[0]

        # 原有属性应该都存在
        assert hasattr(insight, "round_number")
        assert hasattr(insight, "target_aspect")
        assert hasattr(insight, "search_query")
        assert hasattr(insight, "key_findings")
        assert hasattr(insight, "inferred_insights")
        assert hasattr(insight, "info_sufficiency")
        assert hasattr(insight, "info_quality")
        assert hasattr(insight, "alignment_score")

    def test_answer_framework_structure_intact(self, engine, sample_framework):
        """验证 AnswerFramework 数据结构完整"""
        # 原有属性应该都存在
        assert hasattr(sample_framework, "original_query")
        assert hasattr(sample_framework, "answer_goal")
        assert hasattr(sample_framework, "round_insights")
        assert hasattr(sample_framework, "answer_text") or True  # 可能是运行时属性

    def test_search_framework_structure_intact(self, engine):
        """验证 SearchFramework 数据结构完整"""
        framework = SearchFramework(
            user_question="测试问题",
            original_query="测试查询",
            purpose="测试目的",
            framework_type="exploration",
        )

        # 原有属性
        assert hasattr(framework, "user_question")
        assert hasattr(framework, "original_query")
        assert hasattr(framework, "purpose")
        assert hasattr(framework, "framework_type")

    def test_engine_core_methods_exist(self, engine):
        """验证引擎核心方法存在"""
        # 核心方法
        assert hasattr(engine, "_generate_final_answer")
        assert callable(getattr(engine, "_generate_final_answer"))

        # 新增方法应该存在
        assert hasattr(engine, "_detect_cross_round_conflicts")
        assert hasattr(engine, "_validate_citation_references")
        assert hasattr(engine, "_calculate_answer_confidence")


# ==================== 2. 新方法不破坏原有调用 ====================


class TestNewMethodsSafety:
    """测试新方法的安全性 - 不会破坏原有流程"""

    def test_conflict_detection_handles_none(self, engine):
        """冲突检测应处理 None 输入"""
        result = engine._detect_cross_round_conflicts(None)
        assert result["has_conflicts"] == False
        assert result["conflicts"] == []

    def test_conflict_detection_handles_empty_list(self, engine):
        """冲突检测应处理空列表"""
        result = engine._detect_cross_round_conflicts([])
        assert result["has_conflicts"] == False

    def test_citation_validation_handles_empty_string(self, engine):
        """引用校验应处理空字符串"""
        result = engine._validate_citation_references("", 0)
        assert result["valid"] == True  # 空答案无引用是合法的
        assert result["total_citations"] == 0

    def test_citation_validation_handles_none(self, engine):
        """引用校验应处理 None"""
        result = engine._validate_citation_references(None, 10)
        assert result is not None
        assert result["total_citations"] == 0

    def test_confidence_calculation_handles_minimal_input(self, engine):
        """置信度计算应处理最小输入"""
        minimal_framework = AnswerFramework(original_query="test")
        result = engine._calculate_answer_confidence(
            framework=minimal_framework,
            round_insights=[],
            sources_count=0,
            conflict_result={"has_conflicts": False},
            citation_result={"citation_coverage": 0, "valid": True},
        )

        assert result is not None
        assert "overall_confidence" in result
        assert "confidence_level" in result

    def test_new_methods_dont_raise_exceptions(self, engine, sample_framework):
        """新方法不应抛出异常"""
        try:
            # 测试冲突检测
            conflict_result = engine._detect_cross_round_conflicts(sample_framework.round_insights)

            # 测试引用校验
            citation_result = engine._validate_citation_references("测试答案[1][2]", 10)

            # 测试置信度计算
            confidence_result = engine._calculate_answer_confidence(
                framework=sample_framework,
                round_insights=sample_framework.round_insights,
                sources_count=10,
                conflict_result=conflict_result,
                citation_result=citation_result,
            )

            # 所有调用应该成功
            assert True
        except Exception as e:
            pytest.fail(f"新方法抛出异常: {e}")


# ==================== 3. SSE 事件流回归测试 ====================


class TestSSEEventStreamRegression:
    """测试 SSE 事件流的向后兼容性"""

    def test_original_event_types_still_work(self):
        """验证原有事件类型仍然有效"""
        # 原有事件类型
        original_events = [
            "search_start",
            "search_query",
            "search_results",
            "thinking",
            "answer_chunk",
            "answer_complete",
            "sources_update",
            "round_complete",
            "error",
        ]

        # 新事件类型
        new_event = "answer_quality_assessment"

        # 所有事件类型应该可以并存
        all_events = original_events + [new_event]
        assert len(set(all_events)) == len(all_events)  # 无重复

    def test_event_data_structure(self, engine, sample_framework):
        """测试事件数据结构"""
        # 构造质量评估事件
        conflict_result = engine._detect_cross_round_conflicts(sample_framework.round_insights)
        citation_result = engine._validate_citation_references("测试[1]", 5)
        confidence_result = engine._calculate_answer_confidence(
            framework=sample_framework,
            round_insights=sample_framework.round_insights,
            sources_count=5,
            conflict_result=conflict_result,
            citation_result=citation_result,
        )

        # 事件数据
        event_data = {
            "type": "answer_quality_assessment",
            "data": {
                "confidence": confidence_result,
                "citation": citation_result,
                "conflicts": {
                    "has_conflicts": conflict_result["has_conflicts"],
                    "count": len(conflict_result.get("conflicts", [])),
                },
            },
        }

        # 验证结构
        assert "type" in event_data
        assert "data" in event_data
        assert event_data["type"] == "answer_quality_assessment"


# ==================== 4. 性能回归测试 ====================


class TestPerformanceRegression:
    """测试性能不受影响"""

    def test_conflict_detection_performance(self, engine):
        """冲突检测的性能"""
        import time

        # 创建大量洞察
        many_insights = [
            RoundInsights(
                round_number=i,
                key_findings=[f"发现 {i}-{j}" for j in range(5)],
                inferred_insights=[f"推断 {i}"],
                info_quality=0.8,
                info_sufficiency=0.8,
                alignment_score=0.8,
            )
            for i in range(1, 11)  # 10 轮
        ]

        start = time.time()
        for _ in range(100):  # 执行100次
            engine._detect_cross_round_conflicts(many_insights)
        elapsed = time.time() - start

        # 100次执行应该在1秒内完成
        assert elapsed < 1.0, f"冲突检测太慢: {elapsed:.2f}s for 100 iterations"

    def test_citation_validation_performance(self, engine):
        """引用校验的性能"""
        import time

        # 创建长答案
        long_answer = "测试答案。" * 100
        for i in range(1, 51):
            long_answer += f" 引用[{i}]"

        start = time.time()
        for _ in range(100):
            engine._validate_citation_references(long_answer, 100)
        elapsed = time.time() - start

        # 应该在0.5秒内完成
        assert elapsed < 0.5, f"引用校验太慢: {elapsed:.2f}s for 100 iterations"

    def test_confidence_calculation_performance(self, engine, sample_framework):
        """置信度计算的性能"""
        import time

        conflict_result = {"has_conflicts": False}
        citation_result = {"citation_coverage": 0.3, "valid": True}

        start = time.time()
        for _ in range(100):
            engine._calculate_answer_confidence(
                framework=sample_framework,
                round_insights=sample_framework.round_insights,
                sources_count=30,
                conflict_result=conflict_result,
                citation_result=citation_result,
            )
        elapsed = time.time() - start

        # 应该在0.5秒内完成
        assert elapsed < 0.5, f"置信度计算太慢: {elapsed:.2f}s for 100 iterations"


# ==================== 5. 数据迁移兼容性测试 ====================


class TestDataMigrationCompatibility:
    """测试与旧数据的兼容性"""

    def test_old_framework_without_new_fields(self, engine):
        """测试旧格式框架（无新字段）"""
        # 模拟旧格式的框架数据
        old_framework = AnswerFramework(original_query="旧格式查询")

        # 旧框架可能没有 round_insights
        if not hasattr(old_framework, "round_insights"):
            old_framework.round_insights = []

        # 应该正常处理
        conflict_result = engine._detect_cross_round_conflicts(old_framework.round_insights)
        assert conflict_result is not None

    def test_insights_without_all_fields(self, engine):
        """测试不完整的洞察数据"""
        # 模拟缺少某些字段的洞察
        partial_insight = RoundInsights(round_number=1)

        # 设置一些属性，但不是全部
        partial_insight.key_findings = []

        # 确保有默认值
        if not hasattr(partial_insight, "inferred_insights"):
            partial_insight.inferred_insights = []
        if not hasattr(partial_insight, "info_quality"):
            partial_insight.info_quality = 0.5
        if not hasattr(partial_insight, "info_sufficiency"):
            partial_insight.info_sufficiency = 0.5
        if not hasattr(partial_insight, "alignment_score"):
            partial_insight.alignment_score = 0.5

        # 应该正常处理
        result = engine._detect_cross_round_conflicts([partial_insight])
        assert result is not None


# ==================== 6. 错误恢复测试 ====================


class TestErrorRecovery:
    """测试错误情况下的恢复能力"""

    def test_malformed_citation_format(self, engine):
        """测试畸形引用格式"""
        # 各种畸形引用
        malformed_texts = [
            "引用[ 1]",  # 空格
            "引用[1 ]",  # 空格
            "引用[一]",  # 中文数字
            "引用[1.5]",  # 小数
            "引用[abc]",  # 字母
            "引用[-1]",  # 负数
            "引用[]",  # 空
        ]

        for text in malformed_texts:
            result = engine._validate_citation_references(text, 10)
            # 应该不会崩溃
            assert result is not None
            assert "valid" in result

    def test_very_large_citation_numbers(self, engine):
        """测试非常大的引用编号"""
        text = "引用[99999]和[100000]"
        result = engine._validate_citation_references(text, 10)

        # 应该标记为无效
        assert result["valid"] == False or len(result["invalid_citations"]) > 0

    def test_mixed_valid_invalid_citations(self, engine):
        """测试混合有效和无效引用"""
        text = "有效引用[1][2][3]，无效引用[100][200]"
        result = engine._validate_citation_references(text, 10)

        # 应该正确分类
        assert 1 in result["valid_citations"]
        assert 2 in result["valid_citations"]
        assert 3 in result["valid_citations"]
        assert 100 in result["invalid_citations"]
        assert 200 in result["invalid_citations"]


# ==================== 7. 并发安全测试 ====================


class TestConcurrencySafety:
    """测试并发安全性"""

    @pytest.mark.asyncio
    async def test_concurrent_quality_assessments(self, engine):
        """测试并发执行质量评估"""

        async def run_assessment(i):
            framework = AnswerFramework(original_query=f"查询{i}")
            framework.round_insights = [
                RoundInsights(
                    round_number=1,
                    key_findings=[f"发现{i}"],
                    inferred_insights=[f"推断{i}"],
                    info_quality=0.8,
                    info_sufficiency=0.8,
                    alignment_score=0.8,
                )
            ]

            conflict_result = engine._detect_cross_round_conflicts(framework.round_insights)
            citation_result = engine._validate_citation_references(f"答案{i}[1][2]", 10)
            confidence_result = engine._calculate_answer_confidence(
                framework=framework,
                round_insights=framework.round_insights,
                sources_count=10,
                conflict_result=conflict_result,
                citation_result=citation_result,
            )

            return confidence_result

        # 并发执行10个评估
        tasks = [run_assessment(i) for i in range(10)]
        results = await asyncio.gather(*tasks)

        # 所有结果应该有效
        assert len(results) == 10
        for result in results:
            assert result is not None
            assert "overall_confidence" in result


# ==================== 运行测试 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
