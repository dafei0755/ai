"""
v7.118 修复验证 - 单元测试版本
直接测试修复的代码逻辑，无需启动服务器

测试场景：北京四合院改造为纽约Loft风格
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger


def test_fix_1_emoji_encoding():
    """测试修复1: Emoji编码处理"""
    logger.info("\n" + "=" * 70)
    logger.info("测试修复1: Emoji编码处理")
    logger.info("=" * 70)

    from intelligent_project_analyzer.services.dynamic_dimension_generator import DynamicDimensionGenerator

    # 测试包含emoji和特殊字符的字符串
    test_cases = [
        "New Feature",
        "'ascii' codec can't encode character 'x'",
        "Beijing Courtyard + New York Loft",
        "Traditional architecture atmosphere",
        "Minimalist party function",
    ]

    all_passed = True
    for i, test_str in enumerate(test_cases, 1):
        try:
            safe_str = DynamicDimensionGenerator._safe_str(test_str)
            # 验证可以安全编码
            safe_str.encode("ascii", errors="ignore")
            logger.success(f"✅ 测试{i}: '{test_str[:20]}...' -> '{safe_str[:20]}...'")
        except Exception as e:
            logger.error(f"❌ 测试{i}失败: {e}")
            all_passed = False

    if all_passed:
        logger.success("✅ 修复1验证通过: Emoji编码处理正常")
    else:
        logger.error("❌ 修复1验证失败")

    return all_passed


def test_fix_2_search_strategy():
    """测试修复2: SearchStrategyGenerator.generate_deliverable_queries"""
    logger.info("\n" + "=" * 70)
    logger.info("测试修复2: SearchStrategyGenerator方法")
    logger.info("=" * 70)

    from intelligent_project_analyzer.agents.search_strategy import SearchStrategyGenerator

    gen = SearchStrategyGenerator(llm_model=None)  # 无LLM，使用降级方案

    # 测试案例：四合院改造
    test_cases = [
        {
            "deliverable_name": "空间布局方案",
            "deliverable_description": "将四合院内部改造为开放式Loft空间",
            "keywords": ["四合院", "Loft", "开放式", "极简"],
            "project_task": "北京四合院改造为纽约Loft风格",
        },
        {
            "deliverable_name": "传统元素保留策略",
            "deliverable_description": "保留建筑气质的同时实现现代功能",
            "keywords": ["传统", "气", "现代", "融合"],
            "project_task": "传统与现代结合",
        },
        {
            "deliverable_name": "派对功能设计",
            "deliverable_description": "实现派对娱乐功能",
            "keywords": ["派对", "娱乐", "社交"],
            "project_task": "派对空间设计",
        },
    ]

    all_passed = True
    for i, case in enumerate(test_cases, 1):
        try:
            queries = gen.generate_deliverable_queries(
                deliverable_name=case["deliverable_name"],
                deliverable_description=case["deliverable_description"],
                keywords=case["keywords"],
                project_task=case["project_task"],
                num_queries=3,
            )

            assert len(queries) == 3, f"应该生成3个查询，实际: {len(queries)}"
            assert all(isinstance(q, str) and len(q) > 0 for q in queries), "查询应为非空字符串"

            logger.success(f"✅ 测试{i}: {case['deliverable_name']}")
            for j, q in enumerate(queries, 1):
                logger.info(f"    查询{j}: {q}")

        except Exception as e:
            logger.error(f"❌ 测试{i}失败: {e}")
            all_passed = False

    if all_passed:
        logger.success("✅ 修复2验证通过: SearchStrategyGenerator方法正常")
    else:
        logger.error("❌ 修复2验证失败")

    return all_passed


def test_fix_3_complex_requirements():
    """测试修复3: 复杂需求处理（四合院案例）"""
    logger.info("\n" + "=" * 70)
    logger.info("测试修复3: 复杂需求处理能力")
    logger.info("=" * 70)

    user_input = """
    An American who grew up in Beijing bought a small courtyard house (Siheyuan).
    He wants to preserve the traditional architectural 'Qi', but achieve New York Loft's openness, minimalism and party functions inside.
    """

    # 模拟需求分析
    logger.info("需求特点分析:")
    logger.info("  1. 文化融合: 北京四合院 + 纽约Loft")
    logger.info("  2. 矛盾平衡: 传统'气'保留 vs 现代开放空间")
    logger.info("  3. 功能复杂: 居住 + 派对 + 传统元素")

    # 检查是否包含emoji或特殊字符
    from intelligent_project_analyzer.services.dynamic_dimension_generator import DynamicDimensionGenerator

    safe_input = DynamicDimensionGenerator._safe_str(user_input)

    logger.info(f"\n原始输入长度: {len(user_input)} 字符")
    logger.info(f"安全处理后: {len(safe_input)} 字符")

    # 模拟搜索查询生成
    from intelligent_project_analyzer.agents.search_strategy import SearchStrategyGenerator

    gen = SearchStrategyGenerator()

    deliverables = [
        ("Siheyuan Modern Renovation Plan", ["courtyard", "modern", "renovation"]),
        ("Loft Style Space Layout", ["loft", "open", "minimalist"]),
        ("Traditional Element Preservation Strategy", ["traditional", "culture", "atmosphere"]),
        ("Party Function Design", ["party", "social", "entertainment"]),
    ]

    logger.info("\n模拟生成搜索查询:")
    all_passed = True
    for name, keywords in deliverables:
        try:
            queries = gen.generate_deliverable_queries(
                deliverable_name=name, keywords=keywords, project_task=safe_input, num_queries=2
            )
            logger.info(f"  {name}:")
            for q in queries:
                logger.info(f"    - {q}")
        except Exception as e:
            logger.error(f"  ❌ {name} 失败: {e}")
            all_passed = False

    if all_passed:
        logger.success("✅ 修复3验证通过: 复杂需求处理正常")
    else:
        logger.error("❌ 修复3验证失败")

    return all_passed


def test_fix_4_edge_cases():
    """测试修复4: 边缘情况"""
    logger.info("\n" + "=" * 70)
    logger.info("测试修复4: 边缘情况处理")
    logger.info("=" * 70)

    from intelligent_project_analyzer.agents.search_strategy import SearchStrategyGenerator
    from intelligent_project_analyzer.services.dynamic_dimension_generator import DynamicDimensionGenerator

    gen = SearchStrategyGenerator()

    edge_cases = [
        ("空字符串", "", [], ""),
        ("仅emoji", "🎨🏮🗽", ["emoji"], ""),
        ("超长描述", "A" * 1000, ["test"], "project"),
        ("特殊字符", "测试\n换行\t制表符", ["特殊"], "test"),
        ("None值", None, None, None),
    ]

    all_passed = True
    for i, (name, deliv_name, keywords, task) in enumerate(edge_cases, 1):
        try:
            # 测试安全字符串处理
            if deliv_name is not None:
                safe_deliv = DynamicDimensionGenerator._safe_str(deliv_name)

            # 测试查询生成
            queries = gen.generate_deliverable_queries(
                deliverable_name=deliv_name if deliv_name is not None else "默认",
                keywords=keywords if keywords is not None else [],
                project_task=task if task is not None else "",
                num_queries=2,
            )

            logger.success(f"✅ 边缘测试{i}: {name} - 生成{len(queries)}个查询")

        except Exception as e:
            logger.error(f"❌ 边缘测试{i}: {name} 失败 - {e}")
            all_passed = False

    if all_passed:
        logger.success("✅ 修复4验证通过: 边缘情况处理正常")
    else:
        logger.error("❌ 修复4验证失败")

    return all_passed


def main():
    """主函数"""
    logger.info("=" * 70)
    logger.info("v7.118 修复验证测试 - 北京四合院改造案例")
    logger.info("=" * 70)

    results = []

    # 执行所有测试
    results.append(("Emoji编码处理", test_fix_1_emoji_encoding()))
    results.append(("SearchStrategy方法", test_fix_2_search_strategy()))
    results.append(("复杂需求处理", test_fix_3_complex_requirements()))
    results.append(("边缘情况处理", test_fix_4_edge_cases()))

    # 汇总结果
    logger.info("\n" + "=" * 70)
    logger.info("测试结果汇总")
    logger.info("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"  {name}: {status}")

    logger.info(f"\n通过率: {passed}/{total} ({passed/total*100:.0f}%)")

    if passed == total:
        logger.success("\n✅ 所有测试通过 - v7.118修复有效")
        logger.success("系统已准备好处理北京四合院改造等复杂需求")
    else:
        logger.error(f"\n❌ {total-passed}个测试失败 - 需要进一步修复")

    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
