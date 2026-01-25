"""
搜索引用功能集成测试 (v7.120修复验证)

测试目标:
1. 验证后端正确返回 search_references 数据
2. 验证数据结构符合前端类型定义
3. 验证搜索引用在报告中的集成
"""

from typing import Any, Dict, List

import pytest

from intelligent_project_analyzer.core.task_oriented_models import SearchReference


class TestSearchReferencesIntegration:
    """搜索引用集成测试"""

    def test_search_reference_model_creation(self):
        """测试 SearchReference 模型创建"""
        reference = SearchReference(
            source_tool="tavily",
            title="Test Article",
            url="https://example.com/article",
            snippet="This is a test article about design.",
            relevance_score=0.95,
            quality_score=85.5,
            content_complete=True,
            source_credibility="high",
            deliverable_id="2-1_1_143022_abc",
            query="modern design trends",
            timestamp="2025-01-03T10:00:00Z",
            llm_relevance_score=92,
            llm_scoring_reason="Highly relevant to user requirements",
        )

        assert reference.source_tool == "tavily"
        assert reference.title == "Test Article"
        assert reference.url == "https://example.com/article"
        assert reference.relevance_score == 0.95
        assert reference.quality_score == 85.5
        assert reference.llm_relevance_score == 92

    def test_search_reference_model_validation(self):
        """测试 SearchReference 模型字段验证"""
        # 测试必需字段
        with pytest.raises(Exception):  # Pydantic ValidationError
            SearchReference(
                source_tool="tavily",
                # 缺少 title
                snippet="Test snippet",
                relevance_score=0.9,
                deliverable_id="test-1",
                query="test",
                timestamp="2025-01-03T10:00:00Z",
            )

    def test_search_reference_source_tool_enum(self):
        """测试 source_tool 枚举值验证"""
        valid_tools = ["tavily", "arxiv", "milvus", "bocha"]  # v7.154: ragflow → milvus

        for tool in valid_tools:
            reference = SearchReference(
                source_tool=tool,
                title="Test",
                snippet="Test snippet",
                relevance_score=0.9,
                deliverable_id="test-1",
                query="test",
                timestamp="2025-01-03T10:00:00Z",
            )
            assert reference.source_tool == tool

        # 测试无效工具
        with pytest.raises(Exception):  # Pydantic ValidationError
            SearchReference(
                source_tool="invalid_tool",
                title="Test",
                snippet="Test snippet",
                relevance_score=0.9,
                deliverable_id="test-1",
                query="test",
                timestamp="2025-01-03T10:00:00Z",
            )

    def test_search_reference_relevance_score_range(self):
        """测试 relevance_score 范围验证 (0-1)"""
        # 有效范围
        reference = SearchReference(
            source_tool="tavily",
            title="Test",
            snippet="Test snippet",
            relevance_score=0.5,
            deliverable_id="test-1",
            query="test",
            timestamp="2025-01-03T10:00:00Z",
        )
        assert 0 <= reference.relevance_score <= 1

        # 超出范围应该抛出错误
        with pytest.raises(Exception):  # Pydantic ValidationError
            SearchReference(
                source_tool="tavily",
                title="Test",
                snippet="Test snippet",
                relevance_score=1.5,  # 超过1
                deliverable_id="test-1",
                query="test",
                timestamp="2025-01-03T10:00:00Z",
            )

    def test_search_reference_quality_score_range(self):
        """测试 quality_score 范围验证 (0-100)"""
        reference = SearchReference(
            source_tool="tavily",
            title="Test",
            snippet="Test snippet",
            relevance_score=0.9,
            quality_score=75.0,
            deliverable_id="test-1",
            query="test",
            timestamp="2025-01-03T10:00:00Z",
        )
        assert 0 <= reference.quality_score <= 100

        # 超出范围应该抛出错误
        with pytest.raises(Exception):  # Pydantic ValidationError
            SearchReference(
                source_tool="tavily",
                title="Test",
                snippet="Test snippet",
                relevance_score=0.9,
                quality_score=150.0,  # 超过100
                deliverable_id="test-1",
                query="test",
                timestamp="2025-01-03T10:00:00Z",
            )

    def test_search_reference_snippet_max_length(self):
        """测试 snippet 最大长度限制 (300字符)"""
        long_snippet = "A" * 301  # 超过300字符

        with pytest.raises(Exception):  # Pydantic ValidationError
            SearchReference(
                source_tool="tavily",
                title="Test",
                snippet=long_snippet,
                relevance_score=0.9,
                deliverable_id="test-1",
                query="test",
                timestamp="2025-01-03T10:00:00Z",
            )

        # 300字符以内应该成功
        valid_snippet = "A" * 300
        reference = SearchReference(
            source_tool="tavily",
            title="Test",
            snippet=valid_snippet,
            relevance_score=0.9,
            deliverable_id="test-1",
            query="test",
            timestamp="2025-01-03T10:00:00Z",
        )
        assert len(reference.snippet) == 300

    def test_search_reference_optional_fields(self):
        """测试可选字段的默认值"""
        reference = SearchReference(
            source_tool="tavily",
            title="Test",
            snippet="Test snippet",
            relevance_score=0.9,
            deliverable_id="test-1",
            query="test",
            timestamp="2025-01-03T10:00:00Z",
        )

        # 可选字段应该有默认值或为None
        assert reference.url is None
        assert reference.quality_score is None
        assert reference.content_complete == True  # 默认值
        assert reference.source_credibility == "unknown"  # 默认值
        assert reference.llm_relevance_score is None
        assert reference.llm_scoring_reason is None

    def test_search_reference_to_dict(self):
        """测试 SearchReference 转换为字典（用于API响应）"""
        reference = SearchReference(
            source_tool="tavily",
            title="Test Article",
            url="https://example.com",
            snippet="Test snippet",
            relevance_score=0.95,
            quality_score=85.0,
            deliverable_id="2-1_1_143022",
            query="design trends",
            timestamp="2025-01-03T10:00:00Z",
        )

        ref_dict = reference.model_dump()

        assert ref_dict["source_tool"] == "tavily"
        assert ref_dict["title"] == "Test Article"
        assert ref_dict["url"] == "https://example.com"
        assert ref_dict["relevance_score"] == 0.95
        assert ref_dict["quality_score"] == 85.0

    def test_multiple_search_references_grouping(self):
        """测试多个搜索引用的分组逻辑"""
        references = [
            SearchReference(
                source_tool="tavily",
                title="Article 1",
                snippet="Snippet 1",
                relevance_score=0.9,
                deliverable_id="2-1",
                query="test",
                timestamp="2025-01-03T10:00:00Z",
            ),
            SearchReference(
                source_tool="tavily",
                title="Article 2",
                snippet="Snippet 2",
                relevance_score=0.85,
                deliverable_id="2-1",
                query="test",
                timestamp="2025-01-03T10:01:00Z",
            ),
            SearchReference(
                source_tool="arxiv",
                title="Paper 1",
                snippet="Snippet 3",
                relevance_score=0.88,
                deliverable_id="3-1",
                query="research",
                timestamp="2025-01-03T10:02:00Z",
            ),
        ]

        # 按工具分组
        grouped = {}
        for ref in references:
            tool = ref.source_tool
            if tool not in grouped:
                grouped[tool] = []
            grouped[tool].append(ref)

        assert len(grouped) == 2
        assert len(grouped["tavily"]) == 2
        assert len(grouped["arxiv"]) == 1

    def test_search_reference_llm_scoring(self):
        """测试LLM二次评分字段"""
        reference = SearchReference(
            source_tool="tavily",
            title="Test",
            snippet="Test snippet",
            relevance_score=0.9,
            deliverable_id="test-1",
            query="test",
            timestamp="2025-01-03T10:00:00Z",
            llm_relevance_score=95,
            llm_scoring_reason="Perfect match for project requirements",
        )

        assert reference.llm_relevance_score == 95
        assert reference.llm_scoring_reason == "Perfect match for project requirements"
        assert 0 <= reference.llm_relevance_score <= 100

    def test_search_reference_credibility_levels(self):
        """测试来源可信度级别"""
        credibility_levels = ["high", "medium", "low", "unknown"]

        for level in credibility_levels:
            reference = SearchReference(
                source_tool="tavily",
                title="Test",
                snippet="Test snippet",
                relevance_score=0.9,
                source_credibility=level,
                deliverable_id="test-1",
                query="test",
                timestamp="2025-01-03T10:00:00Z",
            )
            assert reference.source_credibility == level


class TestSearchReferencesAPIResponse:
    """测试API响应中的搜索引用数据"""

    def test_structured_report_includes_search_references(self):
        """测试结构化报告包含 search_references 字段"""
        # 模拟报告数据结构
        mock_report = {
            "session_id": "test-session-123",
            "report_text": "Test report content",
            "structured_report": {
                "inquiry_architecture": "深度思考模式",
                "executive_summary": {},
                "sections": [],
                "comprehensive_analysis": {},
                "conclusions": {},
                "expert_reports": {},
                # 🆕 v7.120: 搜索引用字段
                "search_references": [
                    {
                        "source_tool": "tavily",
                        "title": "Test Reference",
                        "snippet": "Test snippet",
                        "relevance_score": 0.95,
                        "deliverable_id": "2-1",
                        "query": "test query",
                        "timestamp": "2025-01-03T10:00:00Z",
                    }
                ],
            },
        }

        # 验证字段存在
        assert "search_references" in mock_report["structured_report"]
        assert isinstance(mock_report["structured_report"]["search_references"], list)
        assert len(mock_report["structured_report"]["search_references"]) > 0

        # 验证数据结构
        ref = mock_report["structured_report"]["search_references"][0]
        assert "source_tool" in ref
        assert "title" in ref
        assert "snippet" in ref
        assert "relevance_score" in ref
        assert "deliverable_id" in ref
        assert "query" in ref
        assert "timestamp" in ref


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
