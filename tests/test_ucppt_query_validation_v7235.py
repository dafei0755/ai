"""
Unit Tests for Ucppt Query Validation - v7.235

Tests the Phase 1 emergency fixes:
1. Query validation helper
2. Fallback query generation
3. Retry loop validation
4. Semantic filtering threshold
5. Semantic relevance assessment
"""

import asyncio

import pytest

from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine


class TestQueryValidation:
    """测试查询验证功能 - Fix 1.1"""

    def setup_method(self):
        self.engine = UcpptSearchEngine()

    def test_validate_empty_query(self):
        """测试空查询验证"""
        assert not self.engine._validate_search_query("", "test")
        assert not self.engine._validate_search_query(None, "test")

    def test_validate_whitespace_query(self):
        """测试纯空格查询验证"""
        assert not self.engine._validate_search_query("   ", "test")
        assert not self.engine._validate_search_query("\t\n", "test")
        assert not self.engine._validate_search_query("  \t  \n  ", "test")

    def test_validate_short_query(self):
        """测试过短查询验证"""
        assert not self.engine._validate_search_query("a", "test")
        assert self.engine._validate_search_query("ab", "test")  # 2字符应该通过
        assert self.engine._validate_search_query("abc", "test")

    def test_validate_punctuation_only(self):
        """测试仅标点符号查询验证"""
        assert not self.engine._validate_search_query("...", "test")
        assert not self.engine._validate_search_query("？！", "test")
        assert not self.engine._validate_search_query(".,;:", "test")
        assert not self.engine._validate_search_query("   ...   ", "test")

    def test_validate_valid_query(self):
        """测试有效查询验证"""
        assert self.engine._validate_search_query("设计", "test")
        assert self.engine._validate_search_query("HAY 设计 元素", "test")
        assert self.engine._validate_search_query("design concept", "test")
        assert self.engine._validate_search_query("北欧风格", "test")

    def test_validate_mixed_content(self):
        """测试混合内容查询"""
        # 包含标点但也有有效字符
        assert self.engine._validate_search_query("设计？", "test")
        assert self.engine._validate_search_query("HAY, design", "test")


class TestFallbackQueryGeneration:
    """测试查询降级逻辑 - Fix 1.2"""

    def setup_method(self):
        self.engine = UcpptSearchEngine()

    def test_preset_keyword_fallback_with_target_name(self):
        """测试预设关键词降级（有目标名称）"""

        # Mock target with no preset keywords but has name
        class MockTarget:
            name = "设计理念"
            preset_keywords = []
            current_keyword_index = 0

            def get_next_preset_keyword(self):
                return None

        target = MockTarget()
        result = self.engine._get_search_query_with_preset(target, "")

        assert result  # 应该返回非空
        assert len(result) >= 2  # 应该是有效查询
        assert self.engine._validate_search_query(result, "test")  # 应该通过验证
        assert result == "设计理念"  # 应该使用目标名称

    def test_preset_keyword_fallback_without_target_name(self):
        """测试预设关键词降级（无目标名称）"""

        # Mock target without name
        class MockTarget:
            preset_keywords = []
            current_keyword_index = 0

            def get_next_preset_keyword(self):
                return None

        target = MockTarget()
        result = self.engine._get_search_query_with_preset(target, "")

        assert result  # 应该返回非空
        assert self.engine._validate_search_query(result, "test")  # 应该通过验证
        assert result == "设计研究案例"  # 应该使用默认降级

    def test_preset_keyword_with_valid_llm_query(self):
        """测试有效LLM查询时的行为"""

        class MockTarget:
            name = "设计理念"
            preset_keywords = []

            def get_next_preset_keyword(self):
                return None

        target = MockTarget()
        result = self.engine._get_search_query_with_preset(target, "HAY 设计 北欧风格")

        assert result == "HAY 设计 北欧风格"  # 应该使用LLM查询

    def test_preset_keyword_with_preset_available(self):
        """测试有预设关键词时的行为"""

        class MockTarget:
            name = "设计理念"
            preset_keywords = ["HAY 品牌设计"]
            current_keyword_index = 0

            def get_next_preset_keyword(self):
                return "HAY 品牌设计"

        target = MockTarget()
        result = self.engine._get_search_query_with_preset(target, "")

        assert result == "HAY 品牌设计"  # 应该使用预设关键词


class TestSemanticFiltering:
    """测试语义过滤 - Fix 1.4 & 1.5"""

    def setup_method(self):
        self.engine = UcpptSearchEngine()

    @pytest.mark.asyncio
    async def test_semantic_relevance_empty_query(self):
        """测试空查询的语义相关性评估"""
        score = await self.engine._assess_semantic_relevance("设计内容", "")
        assert score >= 0.5  # 应该返回默认分数，避免过滤

    @pytest.mark.asyncio
    async def test_semantic_relevance_whitespace_query(self):
        """测试空格查询的语义相关性评估"""
        score = await self.engine._assess_semantic_relevance("设计内容", "   ")
        assert score >= 0.5  # 应该返回默认分数

    @pytest.mark.asyncio
    async def test_semantic_relevance_valid_query(self):
        """测试有效查询的语义相关性评估"""
        score = await self.engine._assess_semantic_relevance("HAY 设计品牌以其简约的北欧风格著称", "HAY 设计 北欧")
        assert score > 0.5  # 应该有较高相关性

    @pytest.mark.asyncio
    async def test_semantic_relevance_no_overlap(self):
        """测试无重叠关键词的情况"""
        score = await self.engine._assess_semantic_relevance("这是关于汽车的内容", "设计 北欧")
        assert score >= 0.3  # 应该返回基础分数

    @pytest.mark.asyncio
    async def test_semantic_relevance_high_overlap(self):
        """测试高重叠度的情况"""
        score = await self.engine._assess_semantic_relevance("HAY 设计 北欧 风格 简约 家具", "HAY 设计 北欧 风格")
        assert score > 0.7  # 应该有很高相关性


class TestRetryLogicValidation:
    """测试重试逻辑验证 - Fix 1.3"""

    def setup_method(self):
        self.engine = UcpptSearchEngine()

    def test_supplement_query_with_invalid_input(self):
        """测试补充查询生成（无效输入）"""
        result = self.engine._generate_supplement_query("", 0, None, False)

        assert result  # 应该返回非空
        assert self.engine._validate_search_query(result, "test")  # 应该是有效查询

    def test_supplement_query_with_whitespace_input(self):
        """测试补充查询生成（空格输入）"""
        result = self.engine._generate_supplement_query("   ", 0, None, False)

        assert result  # 应该返回非空
        assert self.engine._validate_search_query(result, "test")  # 应该是有效查询

    def test_supplement_query_with_valid_input(self):
        """测试补充查询生成（有效输入）"""
        result = self.engine._generate_supplement_query("HAY 设计", 0, None, False)

        assert result  # 应该返回非空
        assert self.engine._validate_search_query(result, "test")  # 应该是有效查询
        assert "HAY 设计" in result  # 应该包含原始查询

    def test_supplement_query_empty_retry_mode(self):
        """测试空结果重试模式"""
        result = self.engine._generate_supplement_query("", 0, None, True)

        assert result  # 应该返回非空
        assert self.engine._validate_search_query(result, "test")  # 应该是有效查询


class TestIntegration:
    """集成测试 - 测试多个修复协同工作"""

    def setup_method(self):
        self.engine = UcpptSearchEngine()

    def test_query_validation_prevents_invalid_queries(self):
        """测试查询验证阻止无效查询"""
        invalid_queries = ["", "   ", "...", "a"]

        for query in invalid_queries:
            is_valid = self.engine._validate_search_query(query, "integration_test")
            assert not is_valid, f"Query '{query}' should be invalid"

    def test_fallback_chain_always_produces_valid_query(self):
        """测试降级链总是产生有效查询"""

        class MockTarget:
            name = "测试目标"

            def get_next_preset_keyword(self):
                return None

        target = MockTarget()

        # 测试各种无效输入
        invalid_inputs = ["", "   ", None, "a"]

        for invalid_input in invalid_inputs:
            result = self.engine._get_search_query_with_preset(target, invalid_input or "")
            assert result, f"Fallback should produce non-empty result for input: {invalid_input}"
            assert self.engine._validate_search_query(
                result, "test"
            ), f"Fallback result should be valid for input: {invalid_input}"

    @pytest.mark.asyncio
    async def test_semantic_filtering_with_empty_query_preserves_results(self):
        """测试空查询时语义过滤保留结果"""
        # 模拟搜索结果
        mock_results = [
            {"content": "HAY 设计内容" * 10, "title": "HAY 设计", "url": "http://example.com/1"},
            {"content": "北欧风格内容" * 10, "title": "北欧风格", "url": "http://example.com/2"},
            {"content": "设计理念内容" * 10, "title": "设计理念", "url": "http://example.com/3"},
        ]

        # 使用空查询进行质量评估
        result = await self.engine.enhanced_quality_assessment(mock_results, "", "test")  # 空查询

        # 应该保留一些结果（通过保底逻辑）
        assert len(result["filtered_results"]) > 0, "Empty query should not filter out all results"


class TestRegressionPrevention:
    """回归测试 - 确保修复不破坏现有功能"""

    def setup_method(self):
        self.engine = UcpptSearchEngine()

    def test_valid_queries_still_work(self):
        """测试有效查询仍然正常工作"""
        valid_queries = [
            "HAY 设计 北欧风格",
            "斯堪的纳维亚 设计 自然材质",
            "山居 民宿 室内设计",
            "design concept",
        ]

        for query in valid_queries:
            assert self.engine._validate_search_query(
                query, "regression_test"
            ), f"Valid query '{query}' should pass validation"

    @pytest.mark.asyncio
    async def test_semantic_relevance_still_scores_correctly(self):
        """测试语义相关性评分仍然正确"""
        # 高相关性
        high_score = await self.engine._assess_semantic_relevance("HAY 设计品牌以其简约的北欧风格著称", "HAY 设计 北欧风格")
        assert high_score > 0.6, "High relevance should score > 0.6"

        # 低相关性
        low_score = await self.engine._assess_semantic_relevance("这是关于汽车的内容", "设计 北欧")
        assert low_score < 0.5, "Low relevance should score < 0.5"

    def test_preset_keywords_still_prioritized(self):
        """测试预设关键词仍然被优先使用"""

        class MockTarget:
            name = "设计理念"
            preset_keywords = ["HAY 品牌设计"]

            def get_next_preset_keyword(self):
                return "HAY 品牌设计"

        target = MockTarget()

        # 即使LLM查询有效，也应该优先使用预设关键词（根据原有逻辑）
        result = self.engine._get_search_query_with_preset(target, "其他设计")

        # 根据原有逻辑，预设关键词应该被优先使用
        assert result == "HAY 品牌设计"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
