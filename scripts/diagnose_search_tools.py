#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
搜索工具诊断脚本 (v7.120)

按照4个层级诊断搜索工具的执行情况：
1. 工具能否连通
2. 搜索任务及指令是否正常
3. 搜索是否执行
4. 结果是否呈现

作者: Claude Code
创建: 2025-01-03
"""

import sys
import time
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from intelligent_project_analyzer.agents.search_strategy import SearchStrategyGenerator
from intelligent_project_analyzer.services.llm_factory import LLMFactory
from intelligent_project_analyzer.services.tool_factory import ToolFactory
from intelligent_project_analyzer.settings import settings


class SearchToolsDiagnostic:
    """搜索工具诊断类"""

    def __init__(self):
        self.results = {
            "connectivity": {},
            "query_generation": {},
            "search_execution": {},
            "result_collection": {},
            "frontend_data_flow": {},
        }
        self.start_time = datetime.now()

    def print_header(self, title):
        """打印章节标题"""
        print()
        print("=" * 60)
        print(f" {title}")
        print("=" * 60)

    def print_section(self, title):
        """打印小节标题"""
        print()
        print(f"[{title}]")
        print("-" * 60)

    # ========== 检查1: 工具连通性 ==========
    def check_1_connectivity(self):
        """检查工具连通性和配置"""
        self.print_section("1/5 工具连通性检查")

        results = {}

        # 检查配置
        print("配置状态:")
        configs = {
            "Tavily": bool(settings.tavily.api_key),
            "Bocha": settings.bocha.enabled and settings.bocha.api_key != "your_bocha_api_key_here",
            "ArXiv": settings.arxiv.enabled,
            "RAGFlow": bool(settings.ragflow.api_key),
        }

        for name, configured in configs.items():
            status = "已配置" if configured else "未配置"
            symbol = "✅" if configured else "❌"
            print(f"  {symbol} {name}: {status}")
            results[name.lower()] = {"configured": configured}

        # 创建工具实例
        print()
        print("创建工具实例...")
        try:
            tools = ToolFactory.create_all_tools()
            print(f"成功创建 {len(tools)} 个工具")

            # 测试工具可用性
            print()
            print("测试工具可用性:")

            for tool_name in ["tavily", "arxiv", "bocha"]:
                if tool_name in tools:
                    try:
                        if tool_name == "tavily":
                            from intelligent_project_analyzer.core.types import ToolConfig
                            from intelligent_project_analyzer.tools.tavily_search import TavilySearchTool

                            tool = TavilySearchTool(
                                api_key=settings.tavily.api_key, config=ToolConfig(name="tavily_search")
                            )
                            result = tool.search("test", max_results=1, search_depth="basic")
                            available = result.get("success", False)
                        elif tool_name == "arxiv":
                            from intelligent_project_analyzer.core.types import ToolConfig
                            from intelligent_project_analyzer.tools.arxiv_search import ArxivSearchTool

                            tool = ArxivSearchTool(config=ToolConfig(name="arxiv_search"))
                            result = tool.search("test", max_results=1)
                            available = result.get("success", False)
                        elif tool_name == "bocha":
                            from intelligent_project_analyzer.agents.bocha_search_tool import BochaSearchTool
                            from intelligent_project_analyzer.core.types import ToolConfig

                            tool = BochaSearchTool(
                                api_key=settings.bocha.api_key,
                                base_url=settings.bocha.base_url,
                                default_count=5,
                                timeout=30,
                                config=ToolConfig(name="bocha_search"),
                            )
                            result = tool.search("测试", count=1)
                            available = result.get("success", False)

                        status = "可用" if available else "不可用"
                        symbol = "✅" if available else "❌"
                        print(f"  {symbol} {tool_name.capitalize()}: {status}")
                        results[tool_name]["available"] = available
                    except Exception as e:
                        print(f"  ❌ {tool_name.capitalize()}: 测试失败 - {str(e)[:50]}")
                        results[tool_name]["available"] = False
                        results[tool_name]["error"] = str(e)
        except Exception as e:
            print(f"❌ 工具创建失败: {e}")
            self.results["connectivity"] = {"error": str(e)}
            return False

        self.results["connectivity"] = results
        return True

    # ========== 检查2: 角色工具映射 ==========
    def check_2_role_tool_mapping(self):
        """检查角色工具映射策略"""
        self.print_section("2/5 角色工具映射检查")

        # 硬编码的角色工具映射（来自main_workflow.py:2574-2580）
        role_tool_mapping = {
            "V2": [],  # 设计总监：禁止外部搜索
            "V3": ["bocha", "tavily", "ragflow"],
            "V4": ["bocha", "tavily", "arxiv", "ragflow"],
            "V5": ["bocha", "tavily", "ragflow"],
            "V6": ["bocha", "tavily", "arxiv", "ragflow"],
        }

        print("角色工具映射规则:")
        for role_type, tools in role_tool_mapping.items():
            tools_str = ", ".join(tools) if tools else "无（禁用搜索）"
            print(f"  - {role_type}: {tools_str}")

        print()
        print("关键发现:")
        print("  ⚠️  V2角色（设计总监）默认禁用所有搜索工具")
        print("  ✅ V3/V4/V5/V6角色启用搜索工具")
        print("  💡 测试时建议使用V4角色（拥有全部工具）")

        self.results["role_tool_mapping"] = role_tool_mapping
        return True

    # ========== 检查3: 搜索查询生成 ==========
    def check_3_query_generation(self):
        """检查搜索查询生成"""
        self.print_section("3/5 搜索查询生成检查")

        try:
            # 初始化搜索策略生成器
            print("初始化SearchStrategyGenerator...")
            try:
                llm_factory = LLMFactory()
                llm = llm_factory.create_llm(provider="openrouter", model_name="gpt-4o-mini", temperature=0.5)
                generator = SearchStrategyGenerator(llm_model=llm)
                print("  ✅ 使用LLM模式")
            except Exception as e:
                print(f"  ⚠️  LLM初始化失败，使用降级模式: {str(e)[:50]}")
                generator = SearchStrategyGenerator(llm_model=None)

            # 测试交付物
            test_deliverable = {
                "name": "用户画像",
                "description": "构建目标用户的详细画像，包括需求、行为、痛点",
                "keywords": ["独立女性", "现代简约"],
                "constraints": {},
            }

            print()
            print("测试交付物:")
            print(f"  名称: {test_deliverable['name']}")
            print(f"  描述: {test_deliverable['description']}")
            print(f"  关键词: {', '.join(test_deliverable['keywords'])}")

            # 生成查询
            print()
            print("生成搜索查询...")
            queries = generator.generate_deliverable_queries(
                deliverable_name=test_deliverable["name"],
                deliverable_description=test_deliverable["description"],
                keywords=test_deliverable["keywords"],
                constraints=test_deliverable["constraints"],
                project_task="为年轻白领设计现代公寓",
                num_queries=3,
            )

            print(f"  ✅ 成功生成 {len(queries)} 个查询:")
            for i, query in enumerate(queries, 1):
                print(f"    {i}. {query}")

            self.results["query_generation"] = {
                "success": True,
                "queries_generated": len(queries),
                "example_queries": queries,
            }
            return True
        except Exception as e:
            print(f"  ❌ 查询生成失败: {e}")
            self.results["query_generation"] = {"success": False, "error": str(e)}
            return False

    # ========== 检查4: 搜索执行 ==========
    def check_4_search_execution(self):
        """检查搜索实际执行"""
        self.print_section("4/5 搜索执行检查")

        test_query = "用户画像 设计案例 2024"
        results = {}

        print(f"测试查询: {test_query}")
        print()

        # 测试Tavily
        if self.results["connectivity"].get("tavily", {}).get("available"):
            print("测试Tavily搜索...")
            try:
                from intelligent_project_analyzer.core.types import ToolConfig
                from intelligent_project_analyzer.tools.tavily_search import TavilySearchTool

                tool = TavilySearchTool(api_key=settings.tavily.api_key, config=ToolConfig(name="tavily_search"))
                result = tool.search(test_query, max_results=3)

                if result.get("success"):
                    count = len(result.get("results", []))
                    print(f"  ✅ 成功返回 {count} 条结果")
                    if count > 0:
                        print(f"    示例: {result['results'][0].get('title', 'N/A')}")
                    results["tavily"] = {"success": True, "count": count}
                else:
                    print(f"  ❌ 搜索失败: {result.get('error', 'Unknown')}")
                    results["tavily"] = {"success": False, "error": result.get("error")}
            except Exception as e:
                print(f"  ❌ 执行失败: {str(e)[:50]}")
                results["tavily"] = {"success": False, "error": str(e)}
        else:
            print("  ⏭️  Tavily: 跳过（不可用）")

        # 测试ArXiv
        print()
        if self.results["connectivity"].get("arxiv", {}).get("available"):
            print("测试ArXiv搜索...")
            try:
                from intelligent_project_analyzer.core.types import ToolConfig
                from intelligent_project_analyzer.tools.arxiv_search import ArxivSearchTool

                tool = ArxivSearchTool(config=ToolConfig(name="arxiv_search"))
                result = tool.search("user persona design", max_results=3)

                if result.get("success"):
                    count = len(result.get("results", []))
                    print(f"  ✅ 成功返回 {count} 条结果")
                    if count > 0:
                        print(f"    示例: {result['results'][0].get('title', 'N/A')}")
                    results["arxiv"] = {"success": True, "count": count}
                else:
                    print(f"  ❌ 搜索失败: {result.get('error', 'Unknown')}")
                    results["arxiv"] = {"success": False, "error": result.get("error")}
            except Exception as e:
                print(f"  ❌ 执行失败: {str(e)[:50]}")
                results["arxiv"] = {"success": False, "error": str(e)}
        else:
            print("  ⏭️  ArXiv: 跳过（不可用）")

        self.results["search_execution"] = results
        return True

    # ========== 检查5: 前端数据流 ==========
    def check_5_frontend_data_flow(self):
        """检查前端数据流"""
        self.print_section("5/5 前端数据传递检查")

        results = {}

        # 检查类型定义
        print("检查前端类型定义...")
        types_file = project_root / "frontend-nextjs" / "types" / "index.ts"
        if types_file.exists():
            content = types_file.read_text(encoding="utf-8")
            has_search_reference = "SearchReference" in content
            if has_search_reference:
                print("  ✅ SearchReference类型已定义")
                results["type_defined"] = True
            else:
                print("  ❌ SearchReference类型未定义")
                results["type_defined"] = False
        else:
            print("  ❌ 类型文件不存在")
            results["type_defined"] = False

        # 检查WebSocket推送
        print()
        print("检查WebSocket推送逻辑...")
        server_file = project_root / "intelligent_project_analyzer" / "api" / "server.py"
        if server_file.exists():
            content = server_file.read_text(encoding="utf-8")
            has_search_references = "search_references" in content
            if has_search_references:
                print("  ✅ server.py包含search_references字段")
                results["websocket_push"] = True
            else:
                print("  ⚠️  server.py未找到search_references字段")
                print("     建议: 检查WebSocket推送逻辑是否包含此字段")
                results["websocket_push"] = False

        self.results["frontend_data_flow"] = results
        return True

    # ========== 生成报告 ==========
    def generate_report(self):
        """生成诊断报告"""
        self.print_header("诊断总结")

        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        print(f"运行时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"总耗时: {duration:.2f}秒")
        print()

        # 统计可用工具
        conn = self.results.get("connectivity", {})
        available_tools = [name for name, data in conn.items() if data.get("available")]
        total_tools = len([k for k in conn.keys() if k != "error"])

        print(f"可用工具: {len(available_tools)}/{total_tools}")
        if available_tools:
            print(f"  - {', '.join([t.capitalize() for t in available_tools])}")

        # 关键发现
        print()
        print("关键发现:")
        findings = []

        # 检查工具连通性
        if not available_tools:
            findings.append("❌ 所有搜索工具不可用（配置或网络问题）")

        # 检查角色映射
        role_mapping = self.results.get("role_tool_mapping", {})
        if role_mapping.get("V2") == []:
            findings.append("⚠️  V2角色（设计总监）默认禁用搜索工具")
            findings.append("💡 建议：测试时使用V3/V4/V5/V6角色")

        # 检查查询生成
        query_gen = self.results.get("query_generation", {})
        if query_gen.get("success"):
            findings.append(f"✅ 搜索查询生成正常（生成{query_gen.get('queries_generated', 0)}个查询）")
        else:
            findings.append("❌ 搜索查询生成失败")

        # 检查搜索执行
        exec_results = self.results.get("search_execution", {})
        successful_searches = [k for k, v in exec_results.items() if v.get("success")]
        if successful_searches:
            findings.append(f"✅ 搜索执行正常（{', '.join([s.capitalize() for s in successful_searches])}）")

        # 检查前端数据流
        frontend = self.results.get("frontend_data_flow", {})
        if not frontend.get("type_defined"):
            findings.append("⚠️  前端SearchReference类型定义缺失")
        if not frontend.get("websocket_push"):
            findings.append("⚠️  WebSocket推送可能未包含search_references字段")

        for finding in findings:
            print(f"  {finding}")

        # 建议修复步骤
        print()
        print("建议修复步骤:")
        steps = []

        if "tavily" not in available_tools and conn.get("tavily", {}).get("configured"):
            steps.append("1. 检查Tavily API密钥是否有效")
        if "bocha" not in available_tools and not conn.get("bocha", {}).get("configured"):
            steps.append("1. 配置BOCHA_API_KEY在.env文件")
        if not frontend.get("type_defined"):
            steps.append("2. 添加SearchReference类型定义到frontend-nextjs/types/index.ts")
        if not frontend.get("websocket_push"):
            steps.append("3. 修复server.py中的search_references WebSocket推送逻辑")
        steps.append("4. 确保使用V3/V4/V5/V6角色进行测试（V2禁用搜索）")

        for step in steps:
            print(f"  {step}")

        print()
        print("=" * 60)
        print(" 诊断完成")
        print("=" * 60)

    # ========== 主函数 ==========
    def run(self):
        """运行完整诊断"""
        self.print_header("搜索工具诊断报告")
        print(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("环境: development")

        # 依次执行检查
        checks = [
            ("工具连通性", self.check_1_connectivity),
            ("角色工具映射", self.check_2_role_tool_mapping),
            ("搜索查询生成", self.check_3_query_generation),
            ("搜索执行", self.check_4_search_execution),
            ("前端数据流", self.check_5_frontend_data_flow),
        ]

        for name, check_func in checks:
            try:
                check_func()
            except Exception as e:
                print(f"❌ {name}检查失败: {e}")
                import traceback

                traceback.print_exc()

        # 生成总结报告
        self.generate_report()


def main():
    """主函数"""
    diagnostic = SearchToolsDiagnostic()
    diagnostic.run()


if __name__ == "__main__":
    main()
