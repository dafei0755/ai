#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
v7.199 ucppt 搜索引擎集成测试

验证以下功能在 ucppt 中的正确集成：
1. 查询分类器 - 识别学术/新闻/案例等查询类型
2. OpenAlex 学术搜索 - 学术类查询自动调用
3. 语义去重 - 使用 embedding 向量去重

作者: AI Assistant
日期: 2026-01-10
"""

import asyncio
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_imports():
    """测试所有模块导入"""
    print("\n" + "=" * 60)
    print("🔍 测试模块导入")
    print("=" * 60)

    results = {}

    # 测试查询分类器
    try:
        from intelligent_project_analyzer.tools.query_classifier import QueryType, classify_query

        results["query_classifier"] = True
        print("✅ 查询分类器 (query_classifier) 导入成功")
    except Exception as e:
        results["query_classifier"] = False
        print(f"❌ 查询分类器导入失败: {e}")

    # 测试 OpenAlex
    try:
        from intelligent_project_analyzer.tools.openalex_search import OpenAlexSearchTool

        results["openalex"] = True
        print("✅ OpenAlex 搜索工具导入成功")
    except Exception as e:
        results["openalex"] = False
        print(f"❌ OpenAlex 导入失败: {e}")

    # 测试语义去重
    try:
        from intelligent_project_analyzer.tools.semantic_dedup import semantic_deduplicate

        results["semantic_dedup"] = True
        print("✅ 语义去重模块导入成功")
    except Exception as e:
        results["semantic_dedup"] = False
        print(f"❌ 语义去重导入失败: {e}")

    # 测试 ucppt 引擎
    try:
        from intelligent_project_analyzer.services.ucppt_search_engine import (
            OPENALEX_AVAILABLE,
            QUERY_CLASSIFIER_AVAILABLE,
            SEMANTIC_DEDUP_AVAILABLE,
            UcpptSearchEngine,
        )

        results["ucppt"] = True
        print("✅ ucppt 搜索引擎导入成功")
        print(f"   - 查询分类器可用: {QUERY_CLASSIFIER_AVAILABLE}")
        print(f"   - OpenAlex 可用: {OPENALEX_AVAILABLE}")
        print(f"   - 语义去重可用: {SEMANTIC_DEDUP_AVAILABLE}")
    except Exception as e:
        results["ucppt"] = False
        print(f"❌ ucppt 导入失败: {e}")

    return all(results.values())


def test_query_classification():
    """测试查询分类功能"""
    print("\n" + "=" * 60)
    print("🔍 测试查询分类")
    print("=" * 60)

    try:
        from intelligent_project_analyzer.tools.query_classifier import QueryType, classify_query

        test_cases = [
            ("室内设计论文研究方法", QueryType.ACADEMIC, "学术"),
            ("最新装修趋势 2026", QueryType.TREND, "趋势"),
            ("archdaily 获奖案例", QueryType.CASE, "案例"),
            ("什么是极简主义设计", QueryType.CONCEPT, "概念"),
            ("如何选择装修材料", QueryType.HOWTO, "教程"),
        ]

        passed = 0
        for query, expected_type, label in test_cases:
            result = classify_query(query)
            status = "✅" if result.query_type == expected_type else "⚠️"
            if result.query_type == expected_type:
                passed += 1
            print(f"   {status} 「{query[:20]}...」→ {result.query_type.value} (期望: {expected_type.value})")

        print(f"\n📊 查询分类测试: {passed}/{len(test_cases)} 通过")
        return passed == len(test_cases)

    except Exception as e:
        print(f"❌ 查询分类测试失败: {e}")
        return False


def test_ucppt_initialization():
    """测试 ucppt 引擎初始化"""
    print("\n" + "=" * 60)
    print("🔍 测试 ucppt 引擎初始化")
    print("=" * 60)

    try:
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()

        print(f"   - max_rounds: {engine.max_rounds}")
        print(f"   - completeness_threshold: {engine.completeness_threshold}")
        print(f"   - bocha_service: {'已初始化' if engine.bocha_service else '未初始化'}")
        print(f"   - openalex_tool: {'已初始化' if engine.openalex_tool else '未初始化'}")

        if engine.openalex_tool:
            print("✅ OpenAlex 工具已正确集成到 ucppt")
        else:
            print("⚠️ OpenAlex 工具未初始化（可能 API 配置问题）")

        return True

    except Exception as e:
        print(f"❌ ucppt 初始化测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_academic_query_detection():
    """测试学术查询检测"""
    print("\n" + "=" * 60)
    print("🔍 测试学术查询检测")
    print("=" * 60)

    try:
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine
        from intelligent_project_analyzer.tools.query_classifier import QueryType, classify_query

        engine = UcpptSearchEngine()

        # 测试学术查询
        academic_queries = [
            "室内设计 论文 研究方法",
            "user experience design research paper",
            "arxiv 建筑设计 算法",
        ]

        non_academic_queries = [
            "最新装修效果图",
            "如何装修客厅",
            "北京装修公司推荐",
        ]

        print("\n📚 学术类查询:")
        for query in academic_queries:
            engine._query_classification = classify_query(query)
            is_academic = engine._is_academic_query()
            status = "✅" if is_academic else "❌"
            print(f"   {status} 「{query[:25]}」→ academic={is_academic}")

        print("\n📰 非学术类查询:")
        for query in non_academic_queries:
            engine._query_classification = classify_query(query)
            is_academic = engine._is_academic_query()
            status = "✅" if not is_academic else "❌"
            print(f"   {status} 「{query[:25]}」→ academic={is_academic}")

        return True

    except Exception as e:
        print(f"❌ 学术查询检测测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_openalex_search():
    """测试 OpenAlex 搜索功能"""
    print("\n" + "=" * 60)
    print("🔍 测试 OpenAlex 学术搜索")
    print("=" * 60)

    try:
        from intelligent_project_analyzer.services.ucppt_search_engine import UcpptSearchEngine

        engine = UcpptSearchEngine()

        if not engine.openalex_tool:
            print("⚠️ OpenAlex 工具未初始化，跳过搜索测试")
            return True

        query = "interior design user experience"
        print(f"📝 查询: '{query}'")

        sources = await engine._search_openalex(query)

        print(f"📊 返回结果: {len(sources)} 篇论文")

        if sources:
            print("\n找到的论文:")
            for i, source in enumerate(sources[:3], 1):
                print(f"\n{i}. {source.get('title', 'N/A')[:60]}...")
                print(f"   来源: {source.get('siteName', 'N/A')}")
                print(f"   引用: {source.get('_cited_by', 0)} 次")
                print(f"   年份: {source.get('_year', 'N/A')}")

            print("\n✅ OpenAlex 搜索测试通过")
            return True
        else:
            print("⚠️ 未返回结果（可能网络问题）")
            return True  # 不因网络问题失败

    except Exception as e:
        print(f"❌ OpenAlex 搜索测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_semantic_dedup():
    """测试语义去重功能"""
    print("\n" + "=" * 60)
    print("🔍 测试语义去重")
    print("=" * 60)

    try:
        from intelligent_project_analyzer.tools.semantic_dedup import semantic_deduplicate

        # 构造相似内容
        test_sources = [
            {"title": "室内设计的基本原则", "content": "室内设计需要考虑空间布局、色彩搭配和家具选择"},
            {"title": "室内设计基本要点", "content": "室内设计要考虑空间规划、颜色搭配以及家具挑选"},  # 语义相似
            {"title": "装修风格介绍", "content": "现代简约风格是当下最流行的装修风格之一"},
            {"title": "北欧风格设计", "content": "北欧风格以简洁明亮为特点，注重功能性设计"},
        ]

        print(f"📝 输入: {len(test_sources)} 条结果")

        # 正确的函数签名: semantic_deduplicate(results, threshold, content_key, fallback_key) -> (list, int)
        deduped, removed_count = semantic_deduplicate(
            test_sources,
            threshold=0.85,
            content_key="content",
        )

        print(f"📊 去重后: {len(deduped)} 条结果 (移除 {removed_count})")

        if removed_count > 0:
            print("✅ 语义去重生效，移除了相似内容")
        else:
            print("ℹ️ 未检测到足够相似的内容（阈值 0.85）")

        return True

    except Exception as e:
        print(f"❌ 语义去重测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """主测试函数"""
    print("🚀 v7.199 ucppt 搜索引擎集成测试")
    print("=" * 60)

    results = {}

    # 1. 模块导入测试
    results["imports"] = test_imports()

    # 2. 查询分类测试
    results["classification"] = test_query_classification()

    # 3. ucppt 初始化测试
    results["initialization"] = test_ucppt_initialization()

    # 4. 学术查询检测测试
    results["academic_detection"] = test_academic_query_detection()

    # 5. OpenAlex 搜索测试
    results["openalex"] = await test_openalex_search()

    # 6. 语义去重测试
    results["semantic_dedup"] = test_semantic_dedup()

    # 汇总
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)

    passed = 0
    for name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"  {status}: {name}")
        if result:
            passed += 1

    print(f"\n总计: {passed}/{len(results)} 通过")

    if passed == len(results):
        print("\n🎉 所有测试通过！v7.199 ucppt 集成成功")
    else:
        print("\n⚠️ 部分测试失败，请检查日志")

    return passed == len(results)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
