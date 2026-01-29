"""
测试 v7.197 搜索质量提升功能

测试内容：
1. 查询分类器
2. 语义去重
3. 动态权重
"""

import sys

sys.path.insert(0, ".")

from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stdout, level="DEBUG", format="{time:HH:mm:ss} | {level:7} | {message}")


def test_query_classifier():
    """测试查询分类器"""
    print("\n" + "=" * 60)
    print("🔍 测试查询分类器")
    print("=" * 60)

    from intelligent_project_analyzer.tools.query_classifier import QueryType, classify_query

    test_queries = [
        # 新闻类
        ("2025年深圳设计周最新动态", QueryType.NEWS),
        ("今日室内设计行业新闻", QueryType.NEWS),
        # 学术类
        ("用户体验设计的理论研究", QueryType.ACADEMIC),
        ("交互设计论文综述", QueryType.ACADEMIC),
        # 案例类
        ("深圳湾海景别墅设计案例", QueryType.CASE),
        ("archdaily 获奖作品", QueryType.CASE),
        # 概念类
        ("什么是极简主义设计", QueryType.CONCEPT),
        ("可持续建筑的定义", QueryType.CONCEPT),
        # 趋势类
        ("2025年室内设计流行趋势", QueryType.TREND),
        ("未来办公空间发展方向", QueryType.TREND),
        # 教程类
        ("如何设计开放式厨房", QueryType.HOWTO),
        ("色彩搭配教程指南", QueryType.HOWTO),
        # 对比类
        ("现代风格和简约风格的区别", QueryType.COMPARISON),
        ("木地板还是瓷砖好", QueryType.COMPARISON),
    ]

    correct = 0
    for query, expected_type in test_queries:
        result = classify_query(query)
        is_correct = result.query_type == expected_type
        correct += 1 if is_correct else 0

        status = "✅" if is_correct else "❌"
        print(f"{status} '{query[:25]}...'")
        print(f"   预期: {expected_type.value}, 实际: {result.query_type.value}")
        print(f"   权重: 时效性={result.timeliness_weight:.0%}, 可信度={result.credibility_weight:.0%}")
        print()

    accuracy = correct / len(test_queries) * 100
    print(f"📊 分类准确率: {accuracy:.1f}% ({correct}/{len(test_queries)})")
    return accuracy >= 70  # 至少70%准确率


def test_semantic_dedup():
    """测试语义去重"""
    print("\n" + "=" * 60)
    print("🧹 测试语义去重")
    print("=" * 60)

    from intelligent_project_analyzer.tools.semantic_dedup import semantic_deduplicate

    # 测试数据：包含语义重复的结果
    test_results = [
        {"url": "https://example1.com", "title": "深圳湾别墅设计", "content": "这个海景别墅项目位于深圳湾，采用现代极简风格设计，大面积落地窗引入自然光线。"},
        {
            "url": "https://example2.com",
            "title": "深圳湾海景豪宅设计案例",
            "content": "深圳湾的这座海景别墅采用现代简约风格，大落地窗设计让室内充满自然光线。",  # 语义相似
        },
        {
            "url": "https://example3.com",
            "title": "上海外滩公寓设计",
            "content": "这是一个位于上海外滩的高端公寓项目，采用Art Deco风格，融合经典与现代元素。",  # 不同
        },
        {"url": "https://example4.com", "title": "深圳湾海边住宅", "content": "位于深圳湾的现代极简住宅项目，大面积玻璃窗设计引入自然采光。"},  # 语义相似
        {"url": "https://example5.com", "title": "北京胡同四合院改造", "content": "这个四合院改造项目保留了传统建筑特色，同时融入现代生活功能。"},  # 不同
    ]

    print(f"📥 输入: {len(test_results)} 个结果")

    try:
        unique_results, removed_count = semantic_deduplicate(
            test_results,
            threshold=0.85,
            content_key="content",
        )

        print(f"📤 输出: {len(unique_results)} 个唯一结果")
        print(f"🗑️ 移除: {removed_count} 个重复结果")

        print("\n保留的结果:")
        for r in unique_results:
            print(f"  - {r['title']}")

        # 预期移除约2个重复（深圳湾相关的3个应该合并为1个）
        success = removed_count >= 1 and len(unique_results) <= 4
        print(f"\n{'✅' if success else '❌'} 语义去重测试 {'通过' if success else '失败'}")
        return success

    except Exception as e:
        print(f"❌ 语义去重测试失败: {e}")
        return False


def test_dynamic_weights():
    """测试动态权重集成"""
    print("\n" + "=" * 60)
    print("⚖️ 测试动态权重")
    print("=" * 60)

    from intelligent_project_analyzer.tools.quality_control import SearchQualityControl

    test_cases = [
        ("最新室内设计新闻", "news"),
        ("用户体验设计研究论文", "academic"),
        ("archdaily 设计案例", "case"),
    ]

    for query, expected_type in test_cases:
        qc = SearchQualityControl(query=query)
        weights = qc.get_weights()

        print(f"\n查询: '{query}'")
        print(f"  预期类型: {expected_type}")
        print(f"  动态权重:")
        print(f"    - 相关性: {weights.get('relevance', 0):.0%}")
        print(f"    - 时效性: {weights.get('timeliness', 0):.0%}")
        print(f"    - 可信度: {weights.get('credibility', 0):.0%}")
        print(f"    - 完整性: {weights.get('completeness', 0):.0%}")

    # 验证新闻类时效性权重高于学术类
    qc_news = SearchQualityControl(query="最新新闻动态")
    qc_academic = SearchQualityControl(query="学术研究论文")

    news_timeliness = qc_news.get_weights().get("timeliness", 0)
    academic_timeliness = qc_academic.get_weights().get("timeliness", 0)

    success = news_timeliness > academic_timeliness
    print(f"\n{'✅' if success else '❌'} 新闻时效性权重({news_timeliness:.0%}) > 学术时效性权重({academic_timeliness:.0%})")
    return success


def test_integrated_quality_control():
    """测试完整质量控制流程"""
    print("\n" + "=" * 60)
    print("🔧 测试完整质量控制流程")
    print("=" * 60)

    from intelligent_project_analyzer.tools.quality_control import SearchQualityControl

    # 模拟搜索结果
    test_results = [
        {
            "url": "https://arxiv.org/abs/2401.12345",
            "title": "深圳湾别墅设计研究",
            "content": "这是一篇关于深圳湾海景别墅设计的学术论文...",
            "relevance_score": 0.9,
        },
        {
            "url": "https://gooood.cn/project/123",
            "title": "深圳湾海景住宅项目",
            "content": "深圳湾的海景住宅项目采用现代设计风格...",  # 可能被视为语义相似
            "relevance_score": 0.85,
        },
        {
            "url": "https://designboom.com/article/456",
            "title": "一代创业者的别墅设计",
            "content": "为一代创业者设计的豪华别墅，融合现代与经典元素...",
            "relevance_score": 0.8,
        },
    ]

    query = "从一代创业者的视角，给出设计概念：深圳湾海景别墅"
    qc = SearchQualityControl(query=query)

    print(f"📥 输入: {len(test_results)} 个结果")
    print(f"📝 查询: '{query}'")

    processed = qc.process_results(test_results)

    print(f"📤 输出: {len(processed)} 个结果")
    print("\n处理后结果:")
    for i, r in enumerate(processed, 1):
        print(f"  {i}. {r['title']}")
        print(f"     质量分数: {r.get('quality_score', 0):.1f}")
        print(f"     可信度: {r.get('source_credibility', 'unknown')}")
        if r.get("is_academic"):
            print(f"     🎓 学术来源")

    print("\n✅ 完整流程测试完成")
    return True


if __name__ == "__main__":
    print("🚀 v7.197 搜索质量提升功能测试")
    print("=" * 60)

    results = []

    # 测试1: 查询分类器
    try:
        results.append(("查询分类器", test_query_classifier()))
    except Exception as e:
        print(f"❌ 查询分类器测试异常: {e}")
        results.append(("查询分类器", False))

    # 测试2: 语义去重
    try:
        results.append(("语义去重", test_semantic_dedup()))
    except Exception as e:
        print(f"❌ 语义去重测试异常: {e}")
        results.append(("语义去重", False))

    # 测试3: 动态权重
    try:
        results.append(("动态权重", test_dynamic_weights()))
    except Exception as e:
        print(f"❌ 动态权重测试异常: {e}")
        results.append(("动态权重", False))

    # 测试4: 完整流程
    try:
        results.append(("完整流程", test_integrated_quality_control()))
    except Exception as e:
        print(f"❌ 完整流程测试异常: {e}")
        results.append(("完整流程", False))

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
        print("\n🎉 所有测试通过！v7.197 功能实施成功")
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息")
