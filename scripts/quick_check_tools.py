#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
快速工具连通性检查脚本
执行方案A步骤1：验证工具连通性
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from intelligent_project_analyzer.services.tool_factory import ToolFactory
from intelligent_project_analyzer.settings import settings


def main():
    print("=" * 50)
    print("工具连通性检查")
    print("=" * 50)
    print()

    # 步骤1: 检查配置
    print("[1/3] 配置状态检查")
    print("-" * 50)
    print(f"  Tavily API Key: {'已配置' if settings.tavily.api_key else '未配置'}")
    print(f"  Bocha Enabled: {settings.bocha.enabled}")
    bocha_configured = settings.bocha.api_key and settings.bocha.api_key != "your_bocha_api_key_here"
    print(f"  Bocha API Key: {'已配置' if bocha_configured else '未配置'}")
    print(f"  ArXiv Enabled: {settings.arxiv.enabled}")
    print(f"  RAGFlow API Key: {'已配置' if settings.ragflow.api_key else '未配置'}")
    print()

    # 步骤2: 创建工具实例
    print("[2/3] 创建工具实例")
    print("-" * 50)
    try:
        tools = ToolFactory.create_all_tools()
        print(f"成功创建 {len(tools)} 个工具")
        print()

        print("可用工具列表:")
        for name, tool in tools.items():
            tool_name = getattr(tool, "name", "unknown")
            print(f"  - {name}: {tool_name}")
        print()
    except Exception as e:
        print(f"工具创建失败: {e}")
        import traceback

        traceback.print_exc()
        return

    # 步骤3: 测试工具可用性
    print("[3/3] 测试工具可用性")
    print("-" * 50)

    # Tavily测试
    if "tavily" in tools:
        print("测试 Tavily...")
        from intelligent_project_analyzer.core.types import ToolConfig
        from intelligent_project_analyzer.tools.tavily_search import TavilySearchTool

        try:
            tavily_tool = TavilySearchTool(api_key=settings.tavily.api_key, config=ToolConfig(name="tavily_search"))
            # 简单测试：搜索"test"
            result = tavily_tool.search("test", max_results=1, search_depth="basic")
            if result.get("success"):
                print(f"  Tavily: 可用 (返回 {len(result.get('results', []))} 条结果)")
            else:
                print(f"  Tavily: 不可用 - {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"  Tavily: 测试失败 - {e}")
    else:
        print("  Tavily: 未创建")

    # ArXiv测试
    if "arxiv" in tools:
        print("测试 ArXiv...")
        from intelligent_project_analyzer.core.types import ToolConfig
        from intelligent_project_analyzer.tools.arxiv_search import ArxivSearchTool

        try:
            arxiv_tool = ArxivSearchTool(config=ToolConfig(name="arxiv_search"))
            result = arxiv_tool.search("machine learning", max_results=1)
            if result.get("success"):
                print(f"  ArXiv: 可用 (返回 {len(result.get('results', []))} 条结果)")
            else:
                print(f"  ArXiv: 不可用 - {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"  ArXiv: 测试失败 - {e}")
    else:
        print("  ArXiv: 未创建")

    # Bocha测试
    if "bocha" in tools:
        print("测试 Bocha...")
        from intelligent_project_analyzer.agents.bocha_search_tool import BochaSearchTool
        from intelligent_project_analyzer.core.types import ToolConfig

        try:
            bocha_tool = BochaSearchTool(
                api_key=settings.bocha.api_key,
                base_url=settings.bocha.base_url,
                default_count=5,
                timeout=30,
                config=ToolConfig(name="bocha_search"),
            )
            result = bocha_tool.search("测试", count=1)
            if result.get("success"):
                print(f"  Bocha: 可用 (返回 {len(result.get('results', []))} 条结果)")
            else:
                print(f"  Bocha: 不可用 - {result.get('message', 'Unknown error')}")
        except Exception as e:
            print(f"  Bocha: 测试失败 - {e}")
    else:
        print("  Bocha: 未创建（可能未启用或未配置API密钥）")

    print()
    print("=" * 50)
    print("检查完成")
    print("=" * 50)


if __name__ == "__main__":
    main()
