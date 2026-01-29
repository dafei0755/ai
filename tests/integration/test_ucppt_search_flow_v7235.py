"""
Integration Tests for Ucppt Search Flow - v7.235

Tests the complete search flow with Phase 1 fixes:
1. No 400 API errors with invalid queries
2. Retry loop terminates early with invalid queries
3. Semantic filtering preserves results
4. End-to-end search flow works correctly
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from intelligent_project_analyzer.core.task_oriented_models import SearchTarget
from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine


class TestSearchFlowIntegration:
    """测试完整搜索流程"""

    @pytest.mark.asyncio
    async def test_search_with_valid_query_no_errors(self):
        """测试有效查询的完整搜索流程（无错误）"""
        engine = UcpptSearchEngine()

        # Mock Bocha service to avoid real API calls
        mock_result = Mock()
        mock_result.sources = [
            Mock(title="HAY 设计", url="http://example.com/1", snippet="HAY 设计内容" * 10, site_name="example.com")
        ]

        with patch.object(engine.bocha_service, "search", new_callable=AsyncMock, return_value=mock_result):
            results = await engine._execute_basic_search("HAY 设计 北欧风格", retry_count=1)

            # 验证结果
            assert isinstance(results, list)
            assert len(results) > 0  # 应该有结果
            assert all("url" in r for r in results)  # 每个结果都应该有URL

    @pytest.mark.asyncio
    async def test_search_with_empty_query_no_crash(self):
        """测试空查询不会导致崩溃"""
        engine = UcpptSearchEngine()

        # 执行搜索（应该优雅地处理）
        results = await engine._execute_basic_search("", retry_count=1)

        # 验证结果
        assert isinstance(results, list)
        assert len(results) == 0  # 空查询应该返回空结果，不应该崩溃

    @pytest.mark.asyncio
    async def test_retry_loop_terminates_with_invalid_query(self):
        """测试重试循环在无效查询时提前终止"""
        engine = UcpptSearchEngine()

        # Mock _generate_supplement_query to return invalid queries
        original_method = engine._generate_supplement_query

        def mock_supplement_query(query, attempt, target_aspect, is_empty_retry):
            # 返回无效查询
            return ""

        engine._generate_supplement_query = mock_supplement_query

        # Mock _execute_search to track calls
        execute_search_calls = []

        async def mock_execute_search(query):
            execute_search_calls.append(query)
            return []

        engine._execute_search = mock_execute_search

        # 执行带重试的搜索
        try:
            results = await engine._execute_search_with_quality_filter("", None)

            # 验证重试循环提前终止
            # 应该在第一次无效查询时就停止，而不是重试5次
            assert len(execute_search_calls) == 0, "Should not call _execute_search with invalid queries"
        finally:
            # 恢复原始方法
            engine._generate_supplement_query = original_method

    @pytest.mark.asyncio
    async def test_semantic_filtering_fallback_preserves_results(self):
        """测试语义过滤保底逻辑保留结果"""
        engine = UcpptSearchEngine()

        # 创建模拟结果
        mock_results = [
            {
                "content": "HAY 设计品牌以其简约的北欧风格著称" * 5,
                "title": "HAY 设计介绍",
                "url": "http://example.com/1",
                "publish_time": "2024-01-01",
            },
            {
                "content": "斯堪的纳维亚设计风格的特点" * 5,
                "title": "北欧设计风格",
                "url": "http://example.com/2",
                "publish_time": "2024-01-01",
            },
            {
                "content": "室内设计中的自然元素运用" * 5,
                "title": "室内设计元素",
                "url": "http://example.com/3",
                "publish_time": "2024-01-01",
            },
        ]

        # 使用空查询（会触发保底逻辑）
        result = await engine.enhanced_quality_assessment(mock_results, "", "test")  # 空查询

        # 验证保底逻辑生效
        assert len(result["filtered_results"]) > 0, "Fallback logic should preserve some results"
        assert len(result["filtered_results"]) <= 5, "Should preserve at most 5 results"

    @pytest.mark.asyncio
    async def test_parallel_search_filters_invalid_queries(self):
        """测试并行搜索过滤无效查询"""
        engine = UcpptSearchEngine()

        # Mock _execute_basic_search to track calls
        basic_search_calls = []

        async def mock_basic_search(query, retry_count=2):
            basic_search_calls.append(query)
            return []

        engine._execute_basic_search = mock_basic_search

        # 执行并行搜索，包含无效查询
        queries = ["HAY 设计", "", "   ", "北欧风格"]
        results = await engine._execute_parallel_search(queries)

        # 验证只有有效查询被执行
        assert len(basic_search_calls) == 2, "Should only execute valid queries"
        assert "HAY 设计" in basic_search_calls
        assert "北欧风格" in basic_search_calls
        assert "" not in basic_search_calls
        assert "   " not in basic_search_calls


class TestEndToEndSearchSession:
    """端到端测试 - 模拟完整搜索会话"""

    @pytest.mark.asyncio
    async def test_complete_search_session_with_mixed_queries(self):
        """测试包含有效和无效查询的完整搜索会话"""
        engine = UcpptSearchEngine()

        # Mock Bocha service
        mock_result = Mock()
        mock_result.sources = [
            Mock(
                title="HAY 设计", url="http://example.com/1", snippet="HAY 设计品牌以其简约的北欧风格著称" * 10, site_name="example.com"
            )
        ]

        test_queries = [
            ("HAY 设计 北欧风格", True, "valid query"),
            ("", False, "empty query"),
            ("   ", False, "whitespace query"),
            ("斯堪的纳维亚设计", True, "valid query 2"),
        ]

        with patch.object(engine.bocha_service, "search", new_callable=AsyncMock, return_value=mock_result):
            for query, should_succeed, desc in test_queries:
                results = await engine._execute_basic_search(query, retry_count=1)

                if should_succeed:
                    assert len(results) > 0, f"{desc} should return results"
                else:
                    assert len(results) == 0, f"{desc} should return empty results"

    @pytest.mark.asyncio
    async def test_no_400_errors_in_search_flow(self):
        """测试搜索流程中没有400错误"""
        engine = UcpptSearchEngine()

        # Mock Bocha service to simulate 400 error for invalid queries
        async def mock_search(query, count, freshness):
            if not query or not query.strip():
                # 模拟Bocha API的400错误
                from httpx import HTTPStatusError, Request, Response

                request = Request("POST", "https://api.bochaai.com/v1/web-search")
                response = Response(400, request=request)
                raise HTTPStatusError("400 Bad Request", request=request, response=response)

            # 返回正常结果
            mock_result = Mock()
            mock_result.sources = [
                Mock(title="Test", url="http://example.com", snippet="Test content" * 10, site_name="example.com")
            ]
            return mock_result

        with patch.object(engine.bocha_service, "search", new_callable=AsyncMock, side_effect=mock_search):
            # 测试空查询不会触发400错误
            results = await engine._execute_basic_search("", retry_count=1)
            assert len(results) == 0, "Empty query should return empty results without 400 error"

            # 测试有效查询正常工作
            results = await engine._execute_basic_search("HAY 设计", retry_count=1)
            assert len(results) > 0, "Valid query should return results"


class TestRegressionTests:
    """回归测试 - 确保修复不破坏现有功能"""

    @pytest.mark.asyncio
    async def test_round_3_success_pattern_still_works(self):
        """测试Round 3成功模式仍然有效"""
        engine = UcpptSearchEngine()

        # Round 3的成功查询
        success_query = "HAY 设计 元素 色彩 材质 运用；斯堪的纳维亚 设计 自然 材质 融合"

        # 验证查询有效
        assert engine._validate_search_query(success_query, "regression_test")

        # Mock Bocha service
        mock_result = Mock()
        mock_result.sources = [
            Mock(
                title=f"设计文章 {i}",
                url=f"http://example.com/{i}",
                snippet="HAY 设计品牌以其简约的北欧风格著称，注重色彩和材质的运用" * 10,
                site_name="example.com",
            )
            for i in range(10)
        ]

        with patch.object(engine.bocha_service, "search", new_callable=AsyncMock, return_value=mock_result):
            results = await engine._execute_basic_search(success_query, retry_count=1)

            # 验证结果
            assert len(results) > 0, "Success query should return results"
            assert len(results) >= 5, "Should return multiple results"

    @pytest.mark.asyncio
    async def test_quality_filtering_not_too_permissive(self):
        """测试质量过滤不会变得过于宽松"""
        engine = UcpptSearchEngine()

        # 创建低质量结果
        low_quality_results = [
            {
                "content": "短内容",  # 太短
                "title": "短",  # 标题太短
                "url": "http://example.com/1",
            },
            {
                "content": "a" * 100,  # 内容长度够，但质量低
                "title": "低质量标题",
                "url": "http://example.com/2",
            },
        ]

        # 使用有效查询
        result = await engine.enhanced_quality_assessment(low_quality_results, "HAY 设计", "test")

        # 验证低质量结果被过滤
        # 注意：由于保底逻辑，可能会保留一些结果，但不应该全部保留
        assert len(result["filtered_results"]) < len(low_quality_results), "Low quality results should be filtered"

    def test_query_variants_generation_still_works(self):
        """测试查询变体生成仍然正常工作"""
        engine = UcpptSearchEngine()

        # 测试有效查询的变体生成
        variants = engine._generate_query_variants("HAY 设计 北欧风格", None)

        assert len(variants) > 0, "Should generate variants for valid query"
        assert all(engine._validate_search_query(v, "test") for v in variants), "All variants should be valid"

        # 测试无效查询返回空列表
        empty_variants = engine._generate_query_variants("", None)
        assert len(empty_variants) == 0, "Should return empty list for invalid query"


class TestPerformanceRegression:
    """性能回归测试 - 确保修复不影响性能"""

    @pytest.mark.asyncio
    async def test_validation_overhead_is_minimal(self):
        """测试验证开销最小"""
        import time

        engine = UcpptSearchEngine()

        # 测试大量查询验证的性能
        queries = ["HAY 设计" + str(i) for i in range(1000)]

        start_time = time.time()
        for query in queries:
            engine._validate_search_query(query, "perf_test")
        elapsed = time.time() - start_time

        # 1000次验证应该在1秒内完成
        assert elapsed < 1.0, f"Validation overhead too high: {elapsed:.3f}s for 1000 queries"

    @pytest.mark.asyncio
    async def test_semantic_assessment_performance(self):
        """测试语义评估性能"""
        import time

        engine = UcpptSearchEngine()

        content = "HAY 设计品牌以其简约的北欧风格著称" * 100
        query = "HAY 设计 北欧风格"

        start_time = time.time()
        for _ in range(100):
            await engine._assess_semantic_relevance(content, query)
        elapsed = time.time() - start_time

        # 100次评估应该在2秒内完成
        assert elapsed < 2.0, f"Semantic assessment too slow: {elapsed:.3f}s for 100 assessments"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
