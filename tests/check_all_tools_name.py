"""
检查所有工具类是否有 name 属性

根据用户反馈，验证系统中的所有工具类是否正确实现了 name 属性
"""

import os
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def check_all_tools():
    """检查所有工具类的 name 属性"""
    from intelligent_project_analyzer.agents.bocha_search_tool import BochaSearchTool
    from intelligent_project_analyzer.tools.arxiv_search import ArxivSearchTool
    from intelligent_project_analyzer.tools.ragflow_kb import RagflowKBTool
    from intelligent_project_analyzer.tools.tavily_search import TavilySearchTool

    print("=" * 70)
    print("检查所有工具类的 name 属性实现")
    print("=" * 70)

    results = []

    # 1. Tavily
    print("\n1️⃣ TavilySearchTool")
    try:
        tool = TavilySearchTool(api_key="test_key")
        has_name = hasattr(tool, "name")
        has_config = hasattr(tool, "config")
        config_name = tool.config.name if has_config else "N/A"
        direct_name = tool.name if has_name else "N/A"

        print(f"   - hasattr(tool, 'name'): {has_name}")
        print(f"   - hasattr(tool, 'config'): {has_config}")
        print(f"   - tool.name: {direct_name}")
        print(f"   - tool.config.name: {config_name}")

        if has_name:
            results.append(("TavilySearchTool", "✅ PASS", f"name='{direct_name}'"))
        else:
            results.append(("TavilySearchTool", "⚠️ WARNING", "缺少 tool.name (仅有 config.name)"))
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        results.append(("TavilySearchTool", "❌ FAIL", str(e)))

    # 2. Arxiv
    print("\n2️⃣ ArxivSearchTool")
    try:
        tool = ArxivSearchTool()
        has_name = hasattr(tool, "name")
        has_config = hasattr(tool, "config")
        config_name = tool.config.name if has_config else "N/A"
        direct_name = tool.name if has_name else "N/A"

        print(f"   - hasattr(tool, 'name'): {has_name}")
        print(f"   - hasattr(tool, 'config'): {has_config}")
        print(f"   - tool.name: {direct_name}")
        print(f"   - tool.config.name: {config_name}")

        if has_name:
            results.append(("ArxivSearchTool", "✅ PASS", f"name='{direct_name}'"))
        else:
            results.append(("ArxivSearchTool", "⚠️ WARNING", "缺少 tool.name (仅有 config.name)"))
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        results.append(("ArxivSearchTool", "❌ FAIL", str(e)))

    # 3. Ragflow
    print("\n3️⃣ RagflowKBTool")
    try:
        tool = RagflowKBTool(api_endpoint="test", api_key="test", dataset_id="test")
        has_name = hasattr(tool, "name")
        has_config = hasattr(tool, "config")
        config_name = tool.config.name if has_config else "N/A"
        direct_name = tool.name if has_name else "N/A"

        print(f"   - hasattr(tool, 'name'): {has_name}")
        print(f"   - hasattr(tool, 'config'): {has_config}")
        print(f"   - tool.name: {direct_name}")
        print(f"   - tool.config.name: {config_name}")

        if has_name:
            results.append(("RagflowKBTool", "✅ PASS", f"name='{direct_name}'"))
        else:
            results.append(("RagflowKBTool", "⚠️ WARNING", "缺少 tool.name (仅有 config.name)"))
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        results.append(("RagflowKBTool", "❌ FAIL", str(e)))

    # 4. Bocha
    print("\n4️⃣ BochaSearchTool (刚修复的)")
    try:
        tool = BochaSearchTool(api_key="test_key")
        has_name = hasattr(tool, "name")
        has_config = hasattr(tool, "config")
        config_name = tool.config.name if has_config else "N/A"
        direct_name = tool.name if has_name else "N/A"

        print(f"   - hasattr(tool, 'name'): {has_name}")
        print(f"   - hasattr(tool, 'config'): {has_config}")
        print(f"   - tool.name: {direct_name}")
        print(f"   - tool.config.name: {config_name}")

        if has_name:
            results.append(("BochaSearchTool", "✅ PASS", f"name='{direct_name}'"))
        else:
            results.append(("BochaSearchTool", "❌ FAIL", "修复失败"))
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        results.append(("BochaSearchTool", "❌ FAIL", str(e)))

    # Summary
    print("\n" + "=" * 70)
    print("📊 检查结果汇总")
    print("=" * 70)
    print(f"\n{'工具类':<20} {'状态':<15} {'详情'}")
    print("-" * 70)
    for tool_name, status, details in results:
        print(f"{tool_name:<20} {status:<15} {details}")

    # Recommendations
    print("\n" + "=" * 70)
    print("💡 建议")
    print("=" * 70)

    warnings = [r for r in results if "WARNING" in r[1]]
    if warnings:
        print(f"\n⚠️ 发现 {len(warnings)} 个工具缺少 tool.name 属性:")
        for tool_name, _, _ in warnings:
            print(f"   - {tool_name}: 建议添加 self.name = self.config.name")
        print("\n   这些工具目前可能依赖 LangChain 的回退机制或间接访问 config.name")
        print("   建议统一添加 self.name 属性以确保兼容性")
    else:
        print("\n✅ 所有工具都正确实现了 name 属性")


if __name__ == "__main__":
    try:
        check_all_tools()
    except Exception as e:
        print(f"\n❌ 检查失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
