"""
v7.228 并行搜索测试脚本
"""
import asyncio
import sys

sys.path.insert(0, ".")


async def test_parallel_search():
    from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

    print("=" * 60)
    print("🧪 v7.228 并行搜索测试")
    print("=" * 60)

    engine = UcpptSearchEngine()

    # 测试查询变体生成
    query = "现代简约风格室内设计"
    print(f"\n📝 原始查询: {query}")

    variants = engine._generate_query_variants(query)
    print(f"🔄 生成变体: {variants}")

    # 测试并行搜索
    print(f"\n🚀 开始并行搜索...")
    results = await engine._execute_parallel_search(variants)

    print(f"\n✅ 并行搜索完成! 共 {len(results)} 条结果")
    print("-" * 60)

    for i, r in enumerate(results[:8]):
        title = r.get("title", "无标题")[:50]
        url = r.get("url", "")[:60]
        print(f"{i+1}. {title}")
        print(f"   URL: {url}")

    # 测试完整的质量筛选流程
    print(f"\n" + "=" * 60)
    print("🔍 测试完整质量筛选流程...")
    quality_results = await engine._execute_search_with_quality_filter(query)

    print(f"\n✅ 质量筛选后: {len(quality_results)} 条高质量结果")
    for i, r in enumerate(quality_results[:5]):
        title = r.get("title", "无标题")[:50]
        score = r.get("_quality_score", 0)
        print(f"{i+1}. [{score:.2f}] {title}")


if __name__ == "__main__":
    asyncio.run(test_parallel_search())
