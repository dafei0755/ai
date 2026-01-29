"""
TikHub 完整集成测试脚本 (v3)
测试通过 BochaSearchTool 调用 TikHub 社交媒体搜索
"""

import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()


def main():
    print("=" * 60)
    print("TikHub Integration Test via BochaSearchTool")
    print("=" * 60)

    # 导入并初始化
    from intelligent_project_analyzer.agents.bocha_search_tool import BochaSearchTool
    from intelligent_project_analyzer.settings import settings

    print(f"\n📋 Configuration:")
    print(f"  - Bocha Enabled: {settings.bocha.enabled}")
    print(f"  - TikHub Enabled: {settings.bocha.tikhub_enabled}")
    print(f"  - TikHub Platforms: {settings.bocha.tikhub_platforms}")
    print(f"  - TikHub Count: {settings.bocha.tikhub_count}")
    print(f"  - TikHub Base URL: {settings.bocha.tikhub_base_url}")

    # 初始化 BochaSearchTool
    tool = BochaSearchTool(
        api_key=settings.bocha.api_key, base_url=settings.bocha.base_url, default_count=settings.bocha.default_count
    )

    print(f"\n🔧 BochaSearchTool initialized:")
    print(f"  - TikHub Enabled: {tool.tikhub_enabled}")
    print(f"  - TikHub Platforms: {tool.tikhub_platforms}")

    # 测试 TikHub 搜索
    print("\n" + "=" * 60)
    print("Testing _search_tikhub() method")
    print("=" * 60)

    query = "AI人工智能设计"
    results = tool._search_tikhub(query)

    print(f"\n✅ Got {len(results)} TikHub results for '{query}':")

    for i, result in enumerate(results[:6], 1):
        print(f"\n  {i}. [{result.get('platform', 'unknown')}] {result.get('title', 'N/A')[:50]}")
        print(f"     URL: {result.get('url', 'N/A')[:60]}")
        print(f"     作者: {result.get('author', 'N/A')}")

    # 统计
    platforms = {}
    for r in results:
        p = r.get("platform", "unknown")
        platforms[p] = platforms.get(p, 0) + 1

    print(f"\n📊 Platform Summary:")
    for p, count in platforms.items():
        print(f"  - {p}: {count} results")

    print("\n✅ Test completed!")


if __name__ == "__main__":
    main()
