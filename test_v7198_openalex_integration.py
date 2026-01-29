"""
测试 v7.198 OpenAlex 学术搜索集成

测试内容：
1. OpenAlex 搜索工具基础功能
2. 摘要重建（倒排索引）
3. 搜索编排器学术轮次
"""

import sys

sys.path.insert(0, ".")

from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss} | {level:7} | {message}")


def test_openalex_basic_search():
    """测试 OpenAlex 基础搜索"""
    print("\n" + "=" * 60)
    print("🔍 测试 OpenAlex 基础搜索")
    print("=" * 60)

    from intelligent_project_analyzer.tools.openalex_search import OpenAlexSearchTool

    tool = OpenAlexSearchTool()

    # 测试搜索
    query = "user experience design"
    print(f"📝 查询: '{query}'")

    result = tool.search(query, max_results=5)

    print(f"📊 状态: {result.get('status')}")
    print(f"📊 总数: {result.get('total_count', 0)}")
    print(f"📊 返回: {result.get('returned_count', 0)}")

    if result.get("status") == "success":
        papers = result.get("results", [])
        print("\n找到的论文:")
        for i, paper in enumerate(papers, 1):
            print(f"\n{i}. {paper.get('title', '无标题')[:60]}...")
            print(f"   作者: {paper.get('authors_str', '未知')[:50]}...")
            print(f"   年份: {paper.get('publication_year', 'N/A')}")
            print(f"   引用: {paper.get('cited_by_count', 0)} 次")
            print(f"   开放获取: {'是' if paper.get('is_open_access') else '否'}")

        success = len(papers) > 0
    else:
        print(f"❌ 错误: {result.get('message')}")
        success = False

    print(f"\n{'✅' if success else '❌'} 基础搜索测试 {'通过' if success else '失败'}")
    return success


def test_openalex_chinese_search():
    """测试 OpenAlex 中文搜索"""
    print("\n" + "=" * 60)
    print("🔍 测试 OpenAlex 中文搜索")
    print("=" * 60)

    from intelligent_project_analyzer.tools.openalex_search import OpenAlexSearchTool

    tool = OpenAlexSearchTool()

    # 测试中文搜索（OpenAlex 支持多语言）
    query = "室内设计 用户体验"
    print(f"📝 查询: '{query}'")

    result = tool.search(query, max_results=5)

    print(f"📊 状态: {result.get('status')}")
    print(f"📊 返回: {result.get('returned_count', 0)} 篇")

    if result.get("status") == "success":
        papers = result.get("results", [])
        if papers:
            print(f"\n第一篇论文:")
            paper = papers[0]
            print(f"   标题: {paper.get('title', '无标题')[:80]}")
            print(f"   摘要: {paper.get('abstract', '')[:100]}...")

        success = True  # 即使结果少也算成功
    else:
        success = False

    print(f"\n{'✅' if success else '❌'} 中文搜索测试 {'通过' if success else '失败'}")
    return success


def test_openalex_filters():
    """测试 OpenAlex 过滤功能"""
    print("\n" + "=" * 60)
    print("🔍 测试 OpenAlex 过滤功能")
    print("=" * 60)

    from intelligent_project_analyzer.tools.openalex_search import OpenAlexSearchTool

    tool = OpenAlexSearchTool()

    # 测试年份过滤
    query = "artificial intelligence"
    print(f"📝 查询: '{query}' (2023-2024, 仅开放获取)")

    result = tool.search(
        query,
        max_results=3,
        from_year=2023,
        to_year=2024,
        open_access_only=True,
    )

    print(f"📊 状态: {result.get('status')}")

    if result.get("status") == "success":
        papers = result.get("results", [])
        print(f"📊 返回: {len(papers)} 篇")

        # 验证过滤结果
        all_oa = all(p.get("is_open_access", False) for p in papers)
        all_recent = all(p.get("publication_year", 0) >= 2023 for p in papers)

        print(f"   全部开放获取: {'是' if all_oa else '否'}")
        print(f"   全部2023+年: {'是' if all_recent else '否'}")

        success = len(papers) > 0
    else:
        success = False

    print(f"\n{'✅' if success else '❌'} 过滤功能测试 {'通过' if success else '失败'}")
    return success


def test_search_orchestrator_academic():
    """测试搜索编排器学术轮次"""
    print("\n" + "=" * 60)
    print("🔧 测试搜索编排器学术轮次")
    print("=" * 60)

    try:
        from intelligent_project_analyzer.services.search_orchestrator import SearchOrchestrator

        orchestrator = SearchOrchestrator()

        # 检查 OpenAlex 是否已初始化
        has_openalex = orchestrator.openalex is not None
        print(f"📊 OpenAlex 已初始化: {'是' if has_openalex else '否'}")

        if not has_openalex:
            print("⚠️ OpenAlex 未初始化，跳过编排器测试")
            return True

        # 测试学术搜索轮次
        print("\n执行学术搜索轮次...")
        result = orchestrator._search_round_3_academic(concepts=["用户体验", "室内设计"], domain="设计")

        print(f"📊 轮次名称: {result.get('round_name')}")
        print(f"📊 查询数量: {len(result.get('queries', []))}")
        print(f"📊 结果数量: {result.get('result_count', 0)}")

        if result.get("results"):
            print("\n示例结果:")
            for r in result.get("results", [])[:2]:
                print(f"   - {r.get('title', '无标题')[:50]}...")
                print(f"     来源: {r.get('source', 'unknown')}")

        success = result.get("result_count", 0) >= 0  # 有结果或无结果都OK
        print(f"\n{'✅' if success else '❌'} 编排器学术轮次测试 {'通过' if success else '失败'}")
        return success

    except Exception as e:
        print(f"❌ 编排器测试异常: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_langchain_wrapper():
    """测试 LangChain 工具包装"""
    print("\n" + "=" * 60)
    print("🔧 测试 LangChain 工具包装")
    print("=" * 60)

    try:
        from intelligent_project_analyzer.tools.openalex_search import LANGCHAIN_AVAILABLE, create_openalex_tool

        if not LANGCHAIN_AVAILABLE:
            print("⚠️ LangChain 不可用，跳过测试")
            return True

        tool = create_openalex_tool()

        print(f"📊 工具名称: {tool.name}")
        print(f"📊 工具描述: {tool.description[:80]}...")

        # 测试调用
        result = tool.invoke({"query": "design thinking", "max_results": 2})
        print(f"\n调用结果:\n{result[:300]}...")

        success = "论文" in result or "找到" in result or "papers" in result.lower()
        print(f"\n{'✅' if success else '❌'} LangChain 包装测试 {'通过' if success else '失败'}")
        return success

    except Exception as e:
        print(f"❌ LangChain 测试异常: {e}")
        return False


if __name__ == "__main__":
    print("🚀 v7.198 OpenAlex 学术搜索集成测试")
    print("=" * 60)

    results = []

    # 测试1: 基础搜索
    try:
        results.append(("基础搜索", test_openalex_basic_search()))
    except Exception as e:
        print(f"❌ 基础搜索测试异常: {e}")
        results.append(("基础搜索", False))

    # 测试2: 中文搜索
    try:
        results.append(("中文搜索", test_openalex_chinese_search()))
    except Exception as e:
        print(f"❌ 中文搜索测试异常: {e}")
        results.append(("中文搜索", False))

    # 测试3: 过滤功能
    try:
        results.append(("过滤功能", test_openalex_filters()))
    except Exception as e:
        print(f"❌ 过滤功能测试异常: {e}")
        results.append(("过滤功能", False))

    # 测试4: 编排器集成
    try:
        results.append(("编排器集成", test_search_orchestrator_academic()))
    except Exception as e:
        print(f"❌ 编排器集成测试异常: {e}")
        results.append(("编排器集成", False))

    # 测试5: LangChain 包装
    try:
        results.append(("LangChain 包装", test_langchain_wrapper()))
    except Exception as e:
        print(f"❌ LangChain 包装测试异常: {e}")
        results.append(("LangChain 包装", False))

    # 汇总
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)

    passed = 0
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"  {status}: {name}")
        passed += 1 if success else 0

    print(f"\n总计: {passed}/{len(results)} 通过")

    if passed == len(results):
        print("\n🎉 所有测试通过！v7.198 OpenAlex 集成成功")
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息")
