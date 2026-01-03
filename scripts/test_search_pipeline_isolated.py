"""
v7.118 搜索管道隔离测试
测试场景：北京四合院改造为纽约Loft风格

不需要启动服务器，直接测试搜索相关组件:
1. SearchStrategyGenerator - 搜索查询生成
2. 搜索工具配置 - Tavily, Arxiv, RAGFlow
3. 查询去重和优化逻辑
"""

import sys
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from intelligent_project_analyzer.agents.search_strategy import SearchStrategyGenerator


class SearchPipelineTester:
    """搜索管道隔离测试器"""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.test_results = []

    def run_all_tests(self):
        """运行所有测试"""
        logger.info("=" * 80)
        logger.info("🔍 v7.118 搜索管道隔离测试 - 北京四合院Loft改造场景")
        logger.info("=" * 80)

        # 测试1: SearchStrategyGenerator查询生成
        self.test_query_generation()

        # 测试2: 多个deliverable的查询生成
        self.test_multiple_deliverables()

        # 测试3: 搜索工具配置验证
        self.test_search_tool_configuration()

        # 生成报告
        self.generate_report()

        return len(self.errors) == 0

    def test_query_generation(self):
        """测试1: 查询生成功能"""
        logger.info("\n" + "=" * 70)
        logger.info("📋 测试1: SearchStrategyGenerator查询生成")
        logger.info("=" * 70)

        try:
            gen = SearchStrategyGenerator(llm_model=None)  # 无LLM，使用降级方案

            # 四合院改造项目的关键deliverable
            test_deliverable = {
                "name": "空间布局方案",
                "description": "将四合院内部改造为开放式Loft空间，保留传统建筑气质",
                "keywords": ["四合院", "Loft", "开放式", "传统气质"],
                "project_task": "An American who grew up in Beijing bought a small courtyard house (Siheyuan). He wants to preserve the traditional architectural 'Qi', but achieve New York Loft's openness, minimalism and party functions inside.",
            }

            queries = gen.generate_deliverable_queries(
                deliverable_name=test_deliverable["name"],
                deliverable_description=test_deliverable["description"],
                keywords=test_deliverable["keywords"],
                project_task=test_deliverable["project_task"],
                num_queries=3,
            )

            # 验证查询生成
            assert len(queries) == 3, f"应生成3个查询，实际: {len(queries)}"
            assert all(isinstance(q, str) and len(q) > 0 for q in queries), "所有查询应为非空字符串"

            logger.success(f"✅ 成功生成{len(queries)}个搜索查询")
            for i, q in enumerate(queries, 1):
                logger.info(f"   查询{i}: {q}")

            # 验证查询质量
            quality_checks = []

            # 检查1: 查询是否包含关键词
            has_keywords = any(any(kw in q for kw in ["Siheyuan", "四合院", "Loft", "courtyard"]) for q in queries)
            quality_checks.append(("包含关键词", has_keywords))

            # 检查2: 查询是否有多样性（不完全重复）
            unique_queries = len(set(queries))
            has_diversity = unique_queries >= 2
            quality_checks.append(("查询多样性", has_diversity))

            # 检查3: 查询长度合理（不要太短或太长）
            reasonable_length = all(5 <= len(q) <= 100 for q in queries)
            quality_checks.append(("长度合理", reasonable_length))

            logger.info("\n   质量检查:")
            for check_name, passed in quality_checks:
                status = "✅" if passed else "⚠️"
                logger.info(f"   {status} {check_name}: {'通过' if passed else '未通过'}")

            all_checks_passed = all(passed for _, passed in quality_checks)
            if all_checks_passed:
                logger.success("✅ 测试1通过: 查询生成功能正常")
                self.test_results.append(("查询生成", True))
            else:
                warning = "查询质量检查未完全通过"
                logger.warning(f"⚠️ {warning}")
                self.warnings.append(warning)
                self.test_results.append(("查询生成", False))

        except Exception as e:
            error = f"测试1失败: {e}"
            logger.error(f"❌ {error}")
            self.errors.append(error)
            self.test_results.append(("查询生成", False))
            import traceback

            traceback.print_exc()

    def test_multiple_deliverables(self):
        """测试2: 多个deliverable的查询生成"""
        logger.info("\n" + "=" * 70)
        logger.info("📦 测试2: 多deliverable查询生成")
        logger.info("=" * 70)

        try:
            gen = SearchStrategyGenerator(llm_model=None)

            # 四合院改造项目的多个deliverable
            deliverables = [
                {"name": "Siheyuan Modern Renovation", "keywords": ["courtyard", "modern", "renovation"]},
                {"name": "Loft Style Space Layout", "keywords": ["loft", "open", "minimalist"]},
                {"name": "Traditional Element Preservation", "keywords": ["traditional", "Qi", "culture"]},
                {"name": "Party Function Integration", "keywords": ["party", "social", "entertainment"]},
            ]

            all_queries = {}
            for deliv in deliverables:
                queries = gen.generate_deliverable_queries(
                    deliverable_name=deliv["name"], keywords=deliv["keywords"], num_queries=2
                )
                all_queries[deliv["name"]] = queries

            logger.info(f"   为{len(deliverables)}个deliverable生成查询:")
            for name, queries in all_queries.items():
                logger.info(f"\n   📌 {name}:")
                for q in queries:
                    logger.info(f"      - {q}")

            # 验证
            total_queries = sum(len(queries) for queries in all_queries.values())
            expected_total = len(deliverables) * 2

            if total_queries == expected_total:
                logger.success(f"✅ 测试2通过: 生成{total_queries}个查询（符合预期）")
                self.test_results.append(("多deliverable", True))
            else:
                warning = f"查询数量异常: 预期{expected_total}，实际{total_queries}"
                logger.warning(f"⚠️ {warning}")
                self.warnings.append(warning)
                self.test_results.append(("多deliverable", False))

        except Exception as e:
            error = f"测试2失败: {e}"
            logger.error(f"❌ {error}")
            self.errors.append(error)
            self.test_results.append(("多deliverable", False))
            import traceback

            traceback.print_exc()

    def test_search_tool_configuration(self):
        """测试3: 搜索工具配置验证"""
        logger.info("\n" + "=" * 70)
        logger.info("🔧 测试3: 搜索工具配置验证")
        logger.info("=" * 70)

        try:
            # 检查搜索工具配置是否可导入
            tool_checks = []

            # Tavily Search
            try:
                from intelligent_project_analyzer.tools.tavily_search import TavilySearchTool

                tool_checks.append(("Tavily", True, "可导入 (TavilySearchTool)"))
            except Exception as e:
                tool_checks.append(("Tavily", False, str(e)))

            # Arxiv Search
            try:
                from intelligent_project_analyzer.tools.arxiv_search import ArxivSearchTool

                tool_checks.append(("Arxiv", True, "可导入 (ArxivSearchTool)"))
            except Exception as e:
                tool_checks.append(("Arxiv", False, str(e)))

            # RAGFlow KB
            try:
                from intelligent_project_analyzer.tools.ragflow_kb import RagflowKBTool

                tool_checks.append(("RAGFlow", True, "可导入 (RagflowKBTool)"))
            except Exception as e:
                tool_checks.append(("RAGFlow", False, str(e)))

            logger.info("   搜索工具状态:")
            for tool_name, available, detail in tool_checks:
                status = "✅" if available else "❌"
                logger.info(f"   {status} {tool_name}: {detail}")

            available_count = sum(1 for _, available, _ in tool_checks if available)
            total_count = len(tool_checks)

            if available_count == total_count:
                logger.success(f"✅ 测试3通过: {available_count}/{total_count}个搜索工具可用")
                self.test_results.append(("工具配置", True))
            elif available_count > 0:
                warning = f"部分工具不可用: {available_count}/{total_count}"
                logger.warning(f"⚠️ {warning}")
                self.warnings.append(warning)
                self.test_results.append(("工具配置", False))
            else:
                error = "所有搜索工具不可用"
                logger.error(f"❌ {error}")
                self.errors.append(error)
                self.test_results.append(("工具配置", False))

        except Exception as e:
            error = f"测试3失败: {e}"
            logger.error(f"❌ {error}")
            self.errors.append(error)
            self.test_results.append(("工具配置", False))
            import traceback

            traceback.print_exc()

    def generate_report(self):
        """生成测试报告"""
        logger.info("\n" + "=" * 80)
        logger.info("📊 搜索管道测试报告")
        logger.info("=" * 80)

        # 测试结果
        logger.info("\n测试结果:")
        passed_count = sum(1 for _, passed in self.test_results if passed)
        total_count = len(self.test_results)

        for name, passed in self.test_results:
            status = "✅ 通过" if passed else "❌ 失败"
            logger.info(f"  {name}: {status}")

        logger.info(f"\n通过率: {passed_count}/{total_count} ({passed_count/total_count*100:.0f}%)")

        # 错误统计
        logger.info(f"\n错误数量: {len(self.errors)}")
        if self.errors:
            for i, error in enumerate(self.errors, 1):
                logger.error(f"  {i}. {error}")

        # 警告统计
        logger.info(f"\n警告数量: {len(self.warnings)}")
        if self.warnings:
            for i, warning in enumerate(self.warnings, 1):
                logger.warning(f"  {i}. {warning}")

        # 总体评估
        logger.info("\n" + "=" * 80)
        if passed_count == total_count and len(self.errors) == 0:
            logger.success("✅ 搜索管道测试全部通过")
            logger.success("   系统可以处理复杂的文化融合设计需求")
        elif passed_count > 0:
            logger.warning(f"⚠️ 部分测试通过 ({passed_count}/{total_count})")
        else:
            logger.error("❌ 所有测试失败")
        logger.info("=" * 80)


def main():
    """主函数"""
    tester = SearchPipelineTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
