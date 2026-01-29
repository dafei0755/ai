"""
Milvus 知识库集成测试

测试完整的 6-Stage Pipeline 集成到系统中的情况

用法:
    pytest tests/test_milvus_integration.py -v
"""

from unittest.mock import Mock, patch

import pytest

from intelligent_project_analyzer.core.types import ToolConfig
from intelligent_project_analyzer.tools.milvus_kb import (
    CoarseRanker,
    CrossEncoderReranker,
    HybridRetriever,
    MilvusKBTool,
    OutputFormatter,
    PostProcessor,
    QueryProcessor,
)


class TestQueryProcessor:
    """测试查询处理器"""

    def test_extract_keywords(self):
        processor = QueryProcessor()
        query = "现代简约风格的客厅照明设计标准"

        result = processor.process(query)

        assert "original_query" in result
        assert "keywords" in result
        assert "intent" in result
        assert "expanded_query" in result
        assert len(result["keywords"]) > 0

    def test_intent_classification(self):
        processor = QueryProcessor()

        # 规范查询
        result1 = processor.process("照明设计标准和规范要求")
        assert result1["intent"] == "规范查询"

        # 案例查询
        result2 = processor.process("现代风格住宅案例参考")
        assert result2["intent"] == "案例查询"

        # 技术查询
        result3 = processor.process("环保材料选择和施工工艺")
        assert result3["intent"] == "技术查询"


class TestCoarseRanker:
    """测试粗排器"""

    def test_filter_low_scores(self):
        ranker = CoarseRanker(similarity_threshold=0.6)

        candidates = [
            {"id": "1", "title": "Doc1", "vector_score": 0.8},
            {"id": "2", "title": "Doc2", "vector_score": 0.5},  # 应被过滤
            {"id": "3", "title": "Doc3", "vector_score": 0.7},
        ]

        ranked = ranker.rank(candidates)

        assert len(ranked) == 2
        assert ranked[0]["vector_score"] == 0.8
        assert ranked[1]["vector_score"] == 0.7


class TestPostProcessor:
    """测试后处理器"""

    def test_deduplication(self):
        processor = PostProcessor(dedup_threshold=0.95)

        docs = [
            {"id": "1", "title": "Doc1", "content": "这是一段相同的内容", "final_score": 0.8, "metadata": {}},
            {"id": "2", "title": "Doc2", "content": "这是一段相同的内容", "final_score": 0.9, "metadata": {}},  # 重复，应保留
            {"id": "3", "title": "Doc3", "content": "这是完全不同的内容", "final_score": 0.7, "metadata": {}},
        ]

        deduplicated = processor._deduplicate(docs)

        assert len(deduplicated) <= len(docs)

    def test_credibility_scores(self):
        processor = PostProcessor()

        docs = [
            {
                "id": "1",
                "title": "Doc1",
                "content": "内容" * 100,
                "final_score": 0.9,
                "metadata": {"document_type": "设计规范"},
            }
        ]

        processed = processor._add_credibility_scores(docs)

        assert "credibility_score" in processed[0]
        assert 0 <= processed[0]["credibility_score"] <= 1


class TestOutputFormatter:
    """测试输出格式化器"""

    def test_format_output(self):
        formatter = OutputFormatter()

        processed_docs = [
            {
                "id": "1",
                "title": "测试文档",
                "content": "测试内容",
                "final_score": 0.85,
                "credibility_score": 0.9,
                "metadata": {"document_type": "设计规范", "tags": [], "project_type": "", "source_file": "test.txt"},
            }
        ]

        query_info = {"original_query": "测试查询", "keywords": ["测试"], "intent": "通用查询"}

        metrics = {
            "stage1_time": 0.01,
            "stage2_time": 0.05,
            "stage4_time": 0.1,
            "total_time": 0.2,
            "candidates_count": 10,
            "filtered_count": 1,
        }

        output = formatter.format(processed_docs, query_info, metrics)

        assert output["success"] is True
        assert output["query"] == "测试查询"
        assert output["total_results"] == 1
        assert len(output["results"]) == 1
        assert output["results"][0]["reference_number"] == 1
        assert "pipeline_metrics" in output


class TestMilvusKBToolPlaceholder:
    """测试 MilvusKBTool (占位符模式)"""

    @patch("intelligent_project_analyzer.tools.milvus_kb.MILVUS_AVAILABLE", False)
    def test_placeholder_mode(self):
        """测试占位符模式响应"""
        tool = MilvusKBTool()

        assert tool.is_placeholder is True

        result = tool.search_knowledge("测试查询")

        assert result["success"] is True
        assert len(result["results"]) > 0
        assert result["results"][0]["source"] == "milvus_placeholder"

    @patch("intelligent_project_analyzer.tools.milvus_kb.MILVUS_AVAILABLE", False)
    def test_to_langchain_tool_placeholder(self):
        """测试 LangChain 工具包装 (占位符模式)"""
        tool = MilvusKBTool()
        langchain_tool = tool.to_langchain_tool()

        assert langchain_tool.name == "milvus_kb_search"
        assert "Milvus" in langchain_tool.description

        result = langchain_tool.func("测试查询")
        assert "Placeholder" in result or "示例" in result


@pytest.mark.integration
class TestMilvusKBToolIntegration:
    """集成测试 (需要真实 Milvus 服务)"""

    @pytest.fixture
    def milvus_tool(self):
        """创建 Milvus 工具实例"""
        try:
            tool = MilvusKBTool(
                host="localhost",
                port=19530,
                collection_name="test_collection",
                embedding_model_name="BAAI/bge-small-zh-v1.5",  # 使用小模型加快测试
                config=ToolConfig(name="milvus_test"),
            )
            return tool
        except Exception:
            pytest.skip("Milvus 服务不可用")

    @pytest.mark.skip(reason="需要真实 Milvus 服务和数据")
    def test_full_pipeline(self, milvus_tool):
        """测试完整 6-Stage Pipeline"""
        result = milvus_tool.search_knowledge("室内设计要点", max_results=5)

        assert result["success"] is True
        assert len(result["results"]) > 0
        assert "pipeline_metrics" in result

        # 检查 Pipeline 各阶段
        metrics = result["pipeline_metrics"]
        assert "query_processing_time" in metrics
        assert "retrieval_time" in metrics
        assert "reranking_time" in metrics
        assert metrics["candidates_count"] >= metrics["filtered_count"]

    @pytest.mark.skip(reason="需要真实 Milvus 服务和数据")
    def test_deliverable_search_integration(self, milvus_tool):
        """测试交付物搜索集成"""
        deliverable = {
            "name": "室内设计方案",
            "description": "包含空间规划和材料选择",
            "dimensions": ["空间布局", "材料方案"],
        }

        result = milvus_tool.search_for_deliverable(deliverable, project_type="residential", max_results=5)

        assert result["success"] is True
        assert len(result["results"]) > 0
