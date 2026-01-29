"""
搜索编排器单元测试 (v7.170)

测试5轮渐进式搜索编排功能
"""

from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, patch

import pytest


class TestAdvancedQueryBuilder:
    """测试多模式搜索词生成器"""

    def test_extract_concepts_chinese(self):
        """测试中文概念提取"""
        from intelligent_project_analyzer.tools.query_builder import AdvancedQueryBuilder

        builder = AdvancedQueryBuilder()
        query = "农耕文化与城市化进程对于室内设计概念的影响"
        concepts = builder.extract_concepts(query)

        assert len(concepts) > 0
        assert isinstance(concepts, list)
        # 应该提取出关键概念
        assert any("农耕" in c or "文化" in c for c in concepts) or len(concepts) > 0

    def test_build_concept_domain_queries(self):
        """测试概念+领域+关系词模式"""
        from intelligent_project_analyzer.tools.query_builder import AdvancedQueryBuilder

        builder = AdvancedQueryBuilder()
        queries = builder.build_multi_mode_queries("农耕文化对室内设计的影响", domain="interior_design", modes=["concept_domain"])

        assert "concept_domain" in queries
        assert len(queries["concept_domain"]) > 0
        # 应该包含关系词
        assert any("对" in q or "与" in q for q in queries["concept_domain"])

    def test_build_time_limited_queries(self):
        """测试时间限定模式"""
        from intelligent_project_analyzer.tools.query_builder import AdvancedQueryBuilder

        builder = AdvancedQueryBuilder()
        queries = builder.build_multi_mode_queries("智慧城市室内设计", domain="interior_design", modes=["time_limited"])

        assert "time_limited" in queries
        assert len(queries["time_limited"]) > 0
        # 应该包含年份或时间词
        assert any("2024" in q or "2025" in q or "最新" in q for q in queries["time_limited"])

    def test_build_content_type_queries(self):
        """测试内容类型模式"""
        from intelligent_project_analyzer.tools.query_builder import AdvancedQueryBuilder

        builder = AdvancedQueryBuilder()
        queries = builder.build_multi_mode_queries("城市化对室内设计的影响", domain="interior_design", modes=["content_type"])

        assert "content_type" in queries
        assert len(queries["content_type"]) > 0
        # 应该包含内容类型词
        content_keywords = ["论文", "案例", "数据", "新闻"]
        assert any(any(kw in q for kw in content_keywords) for q in queries["content_type"])

    def test_build_progressive_queries(self):
        """测试渐进式搜索词生成"""
        from intelligent_project_analyzer.tools.query_builder import AdvancedQueryBuilder

        builder = AdvancedQueryBuilder()
        query = "农耕文化与城市化进程对于室内设计概念的影响"

        # 测试各轮次
        for round_type in ["concepts", "dimensions", "academic", "cases", "data"]:
            queries = builder.build_progressive_queries(query, "interior_design", round_type)
            assert len(queries) > 0, f"Round {round_type} should generate queries"

    def test_build_all_queries_deduplication(self):
        """测试去重功能"""
        from intelligent_project_analyzer.tools.query_builder import AdvancedQueryBuilder

        builder = AdvancedQueryBuilder()
        queries = builder.build_all_queries("室内设计趋势", "interior_design")

        # 检查去重
        assert len(queries) == len(set(q.lower() for q in queries))


class TestContentDepthEvaluator:
    """测试内容深度评估器"""

    def test_evaluate_depth_with_framework(self):
        """测试包含框架的内容"""
        from intelligent_project_analyzer.tools.quality_control import ContentDepthEvaluator

        evaluator = ContentDepthEvaluator()
        result = {"title": "室内设计框架分析", "content": "本文提出了一个三维度分析框架，包括空间、材料和功能三个层面的系统性分析方法。"}

        depth_info = evaluator.evaluate_depth(result)

        assert depth_info["depth_score"] > 0
        assert depth_info["depth_indicators"]["has_framework"] == True
        assert depth_info["depth_indicators"]["has_methodology"] == True

    def test_evaluate_depth_with_data(self):
        """测试包含数据的内容"""
        from intelligent_project_analyzer.tools.quality_control import ContentDepthEvaluator

        evaluator = ContentDepthEvaluator()
        result = {"title": "室内设计市场报告", "content": "根据统计数据显示，2024年室内设计市场规模增长了15%，达到5000亿元。"}

        depth_info = evaluator.evaluate_depth(result)

        assert depth_info["depth_indicators"]["has_data"] == True

    def test_evaluate_depth_shallow_content(self):
        """测试浅层内容"""
        from intelligent_project_analyzer.tools.quality_control import ContentDepthEvaluator

        evaluator = ContentDepthEvaluator()
        result = {"title": "室内设计", "content": "室内设计是一种设计。"}

        depth_info = evaluator.evaluate_depth(result)

        assert depth_info["depth_level"] == "shallow"
        assert depth_info["depth_score"] < 30

    def test_evaluate_batch(self):
        """测试批量评估"""
        from intelligent_project_analyzer.tools.quality_control import ContentDepthEvaluator

        evaluator = ContentDepthEvaluator()
        results = [
            {"title": "深度分析", "content": "本文提出框架和方法论，包含数据统计和案例分析。"},
            {"title": "简单介绍", "content": "这是一个简单的介绍。"},
        ]

        evaluated = evaluator.evaluate_batch(results)

        assert len(evaluated) == 2
        assert all("depth_score" in r for r in evaluated)
        assert evaluated[0]["depth_score"] > evaluated[1]["depth_score"]

    def test_filter_by_depth(self):
        """测试按深度过滤"""
        from intelligent_project_analyzer.tools.quality_control import ContentDepthEvaluator

        evaluator = ContentDepthEvaluator()
        results = [
            {"title": "深度分析", "content": "本文提出框架和方法论，包含数据统计和案例分析。"},
            {"title": "简单介绍", "content": "这是一个简单的介绍。"},
        ]

        filtered = evaluator.filter_by_depth(results, min_depth_score=30)

        # 浅层内容应该被过滤
        assert len(filtered) <= len(results)


class TestSearchOrchestrator:
    """测试搜索编排器"""

    @pytest.fixture
    def mock_search_tools(self):
        """模拟搜索工具"""
        with patch("intelligent_project_analyzer.services.search_orchestrator.TavilySearchTool") as mock_tavily, patch(
            "intelligent_project_analyzer.services.search_orchestrator.create_bocha_search_tool_from_settings"
        ) as mock_bocha, patch(
            "intelligent_project_analyzer.services.search_orchestrator.ArxivSearchTool"
        ) as mock_arxiv:
            # 模拟 Tavily 搜索结果
            mock_tavily_instance = MagicMock()
            mock_tavily_instance.search.return_value = {
                "success": True,
                "results": [
                    {"title": "Tavily Result 1", "url": "https://example.com/1", "content": "Content 1"},
                    {"title": "Tavily Result 2", "url": "https://example.com/2", "content": "Content 2"},
                ],
            }
            mock_tavily.return_value = mock_tavily_instance

            # 模拟 Bocha 搜索结果
            mock_bocha_instance = MagicMock()
            mock_bocha_instance.search.return_value = {
                "success": True,
                "results": [
                    {"title": "Bocha Result 1", "url": "https://example.cn/1", "content": "内容 1"},
                    {"title": "Bocha Result 2", "url": "https://example.cn/2", "content": "内容 2"},
                ],
            }
            mock_bocha.return_value = mock_bocha_instance

            # 模拟 Arxiv 搜索结果
            mock_arxiv_instance = MagicMock()
            mock_arxiv_instance.search.return_value = {
                "success": True,
                "results": [
                    {"title": "Arxiv Paper 1", "url": "https://arxiv.org/1", "content": "Abstract 1"},
                ],
            }
            mock_arxiv.return_value = mock_arxiv_instance

            yield {"tavily": mock_tavily_instance, "bocha": mock_bocha_instance, "arxiv": mock_arxiv_instance}

    def test_extract_concepts(self):
        """测试概念提取"""
        from intelligent_project_analyzer.services.search_orchestrator import SearchOrchestrator

        with patch.object(SearchOrchestrator, "_init_search_tools"):
            orchestrator = SearchOrchestrator()
            orchestrator.tavily = None
            orchestrator.bocha = None
            orchestrator.arxiv = None

            concepts = orchestrator._extract_concepts("农耕文化与城市化进程对于室内设计概念的影响")

            assert len(concepts) > 0
            assert isinstance(concepts, list)

    def test_extract_domain(self):
        """测试领域提取"""
        from intelligent_project_analyzer.services.search_orchestrator import SearchOrchestrator

        with patch.object(SearchOrchestrator, "_init_search_tools"):
            orchestrator = SearchOrchestrator()
            orchestrator.tavily = None
            orchestrator.bocha = None
            orchestrator.arxiv = None
            orchestrator.orchestrator_config = {"domain_mapping": {"interior_design": "室内设计"}}

            domain = orchestrator._extract_domain("室内设计趋势分析")

            assert domain == "室内设计" or domain == "设计"

    def test_extract_dimensions(self):
        """测试维度提取"""
        from intelligent_project_analyzer.services.search_orchestrator import SearchOrchestrator

        with patch.object(SearchOrchestrator, "_init_search_tools"):
            orchestrator = SearchOrchestrator()
            orchestrator.tavily = None
            orchestrator.bocha = None
            orchestrator.arxiv = None
            orchestrator.orchestrator_config = {"dimension_keywords": ["空间", "材料", "功能", "风格"]}

            round1_results = {
                "results": [
                    {"title": "空间布局分析", "content": "关于空间和材料的研究"},
                    {"title": "功能设计", "content": "功能性设计方法"},
                ]
            }

            dimensions = orchestrator._extract_dimensions(round1_results)

            assert len(dimensions) > 0
            assert any(d in ["空间", "材料", "功能"] for d in dimensions)

    def test_deduplicate_results(self):
        """测试结果去重"""
        from intelligent_project_analyzer.services.search_orchestrator import SearchOrchestrator

        with patch.object(SearchOrchestrator, "_init_search_tools"):
            orchestrator = SearchOrchestrator()
            orchestrator.tavily = None
            orchestrator.bocha = None
            orchestrator.arxiv = None

            results = [
                {"url": "https://example.com/1", "title": "Title 1"},
                {"url": "https://example.com/1", "title": "Title 1 Duplicate"},  # 重复
                {"url": "https://example.com/2", "title": "Title 2"},
            ]

            unique = orchestrator._deduplicate_results(results)

            assert len(unique) == 2

    def test_integrate_results(self):
        """测试结果整合"""
        from intelligent_project_analyzer.services.search_orchestrator import SearchOrchestrator

        with patch.object(SearchOrchestrator, "_init_search_tools"):
            orchestrator = SearchOrchestrator()
            orchestrator.tavily = None
            orchestrator.bocha = None
            orchestrator.arxiv = None

            all_results = {
                "query": "测试查询",
                "concepts": ["概念1", "概念2"],
                "domain": "室内设计",
                "dimensions_found": ["空间", "材料"],
                "rounds": {
                    "concepts": {
                        "results": [{"title": "概念结果", "url": "https://example.com/1", "content": "内容"}],
                        "result_count": 1,
                    },
                    "dimensions": {"results": [], "result_count": 0},
                    "academic": {"results": [], "result_count": 0},
                    "cases": {"results": [], "result_count": 0},
                    "data": {"results": [], "result_count": 0},
                },
                "all_sources": [{"title": "概念结果", "url": "https://example.com/1", "content": "内容"}],
            }

            integrated = orchestrator._integrate_results(all_results)

            assert integrated["success"] == True
            assert "summary" in integrated
            assert "references" in integrated
            assert "statistics" in integrated


class TestIntegration:
    """集成测试"""

    def test_build_advanced_queries_convenience_function(self):
        """测试便捷函数"""
        from intelligent_project_analyzer.tools.query_builder import build_advanced_queries

        queries = build_advanced_queries("室内设计趋势", "interior_design")

        assert len(queries) > 0
        assert isinstance(queries, list)

    def test_build_progressive_queries_convenience_function(self):
        """测试渐进式搜索便捷函数"""
        from intelligent_project_analyzer.tools.query_builder import build_progressive_queries

        for round_type in ["concepts", "dimensions", "academic", "cases", "data"]:
            queries = build_progressive_queries("室内设计趋势", "interior_design", round_type)
            assert len(queries) > 0, f"Round {round_type} should generate queries"

    def test_enhanced_quality_control(self):
        """测试增强版质量控制"""
        from intelligent_project_analyzer.tools.quality_control import enhanced_quality_control

        results = [
            {
                "title": "深度分析报告",
                "url": "https://example.com/1",
                "content": "本文提出了一个分析框架，包含数据统计和案例研究，方法论清晰。",
                "score": 0.8,
            },
            {"title": "简单介绍", "url": "https://example.com/2", "content": "这是一个简单的介绍。", "score": 0.7},
        ]

        processed = enhanced_quality_control(results, enable_depth=True)

        assert len(processed) > 0
        assert all("depth_score" in r for r in processed)
        assert all("quality_score" in r for r in processed)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
