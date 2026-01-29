"""
Milvus 知识库工具测试脚本

功能:
1. 测试 Milvus 连接
2. 测试 6-Stage Pipeline
3. 性能基准测试
4. 质量评估

用法:
    python scripts/test_milvus_kb.py
"""

import sys
import time
from pathlib import Path

from loguru import logger

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from intelligent_project_analyzer.core.types import ToolConfig
from intelligent_project_analyzer.settings import settings
from intelligent_project_analyzer.tools.milvus_kb import MilvusKBTool


def test_connection():
    """测试 Milvus 连接"""
    logger.info("=" * 50)
    logger.info("测试 1: Milvus 连接")
    logger.info("=" * 50)

    tool = MilvusKBTool(
        host=settings.milvus.host,
        port=settings.milvus.port,
        collection_name=settings.milvus.collection_name,
        embedding_model_name=settings.milvus.embedding_model,
        reranker_model_name=settings.milvus.reranker_model,
        config=ToolConfig(name="milvus_kb_test"),
    )

    # 健康检查
    health = tool.health_check()
    logger.info(f"健康状态: {health}")

    if health.get("status") == "healthy":
        logger.info(f"✅ Milvus 连接成功")
        logger.info(f"Collection: {health.get('collection')}")
        logger.info(f"实体数量: {health.get('num_entities')}")
        return tool
    else:
        logger.error(f"❌ Milvus 连接失败: {health.get('message')}")
        return None


def test_basic_search(tool: MilvusKBTool):
    """测试基础搜索功能"""
    logger.info("=" * 50)
    logger.info("测试 2: 基础搜索")
    logger.info("=" * 50)

    test_queries = [
        "现代简约风格的客厅设计要点",
        "住宅照明设计标准",
        "环保材料选择建议",
    ]

    for i, query in enumerate(test_queries, 1):
        logger.info(f"\n查询 {i}: {query}")
        start_time = time.time()

        result = tool.search_knowledge(query, max_results=5)

        elapsed = time.time() - start_time

        if result.get("success"):
            logger.info(f"✅ 搜索成功 (耗时: {elapsed:.3f}s)")
            logger.info(f"返回结果数: {result['total_results']}")

            for j, item in enumerate(result.get("results", []), 1):
                logger.info(f"  [{j}] {item.get('title')}")
                logger.info(f"      相似度: {item.get('relevance_score', 0):.3f}")
                logger.info(f"      可信度: {item.get('credibility_score', 0):.3f}")
                logger.info(f"      类型: {item['metadata'].get('document_type')}")

            # Pipeline 指标
            metrics = result.get("pipeline_metrics", {})
            logger.info(f"\nPipeline 性能:")
            logger.info(f"  查询处理: {metrics.get('query_processing_time', 0):.3f}s")
            logger.info(f"  检索: {metrics.get('retrieval_time', 0):.3f}s")
            logger.info(f"  重排序: {metrics.get('reranking_time', 0):.3f}s")
            logger.info(f"  候选文档数: {metrics.get('candidates_count', 0)}")
            logger.info(f"  最终文档数: {metrics.get('filtered_count', 0)}")
        else:
            logger.error(f"❌ 搜索失败: {result.get('error')}")


def test_deliverable_search(tool: MilvusKBTool):
    """测试交付物搜索功能"""
    logger.info("=" * 50)
    logger.info("测试 3: 交付物搜索")
    logger.info("=" * 50)

    deliverable = {
        "name": "室内设计方案",
        "description": "包含空间规划、材料选择、照明设计等内容",
        "dimensions": ["空间布局", "材料方案", "照明设计"],
    }

    project_type = "residential"

    logger.info(f"交付物: {deliverable['name']}")
    logger.info(f"项目类型: {project_type}")

    start_time = time.time()
    result = tool.search_for_deliverable(deliverable, project_type, max_results=5)
    elapsed = time.time() - start_time

    if result.get("success"):
        logger.info(f"✅ 搜索成功 (耗时: {elapsed:.3f}s)")
        logger.info(f"返回结果数: {result['total_results']}")

        for i, item in enumerate(result.get("results", []), 1):
            logger.info(f"  [{i}] {item.get('title')}")
            logger.info(f"      相似度: {item.get('relevance_score', 0):.3f}")
    else:
        logger.error(f"❌ 搜索失败: {result.get('error')}")


def test_performance_benchmark(tool: MilvusKBTool):
    """性能基准测试"""
    logger.info("=" * 50)
    logger.info("测试 4: 性能基准测试")
    logger.info("=" * 50)

    queries = [
        "室内设计要点",
        "照明标准",
        "材料选择",
        "空间规划",
        "色彩搭配",
    ] * 2  # 10 次查询

    logger.info(f"执行 {len(queries)} 次搜索...")

    times = []
    for i, query in enumerate(queries, 1):
        start = time.time()
        result = tool.search_knowledge(query, max_results=5)
        elapsed = time.time() - start
        times.append(elapsed)

        if result.get("success"):
            logger.info(f"  查询 {i}: {elapsed:.3f}s ✅")
        else:
            logger.info(f"  查询 {i}: 失败 ❌")

    # 统计
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    p95_time = sorted(times)[int(len(times) * 0.95)]

    logger.info(f"\n性能统计:")
    logger.info(f"  平均延迟: {avg_time:.3f}s")
    logger.info(f"  最小延迟: {min_time:.3f}s")
    logger.info(f"  最大延迟: {max_time:.3f}s")
    logger.info(f"  P95 延迟: {p95_time:.3f}s")
    logger.info(f"  QPS: {1/avg_time:.2f}")


def test_langchain_integration(tool: MilvusKBTool):
    """测试 LangChain 集成"""
    logger.info("=" * 50)
    logger.info("测试 5: LangChain 工具包装")
    logger.info("=" * 50)

    langchain_tool = tool.to_langchain_tool()

    logger.info(f"工具名称: {langchain_tool.name}")
    logger.info(f"工具描述: {langchain_tool.description[:100]}...")

    # 测试调用
    test_query = "室内设计要点"
    logger.info(f"\n测试查询: {test_query}")

    result = langchain_tool.func(test_query)

    logger.info(f"✅ LangChain 调用成功")
    logger.info(f"返回结果:\n{result[:500]}...")


def main():
    logger.info("=" * 80)
    logger.info("Milvus 知识库工具测试")
    logger.info("=" * 80)

    # 测试 1: 连接
    tool = test_connection()
    if not tool:
        logger.error("Milvus 连接失败，退出测试")
        return

    # 测试 2: 基础搜索
    test_basic_search(tool)

    # 测试 3: 交付物搜索
    test_deliverable_search(tool)

    # 测试 4: 性能基准
    test_performance_benchmark(tool)

    # 测试 5: LangChain 集成
    test_langchain_integration(tool)

    logger.info("=" * 80)
    logger.info("所有测试完成！")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
