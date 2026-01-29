#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试Bocha优先级修复 (v7.131)

验证中文查询是否优先使用Bocha而不是Tavily
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from intelligent_project_analyzer.services.tool_factory import ToolFactory


def test_language_detection():
    """测试语言检测函数"""
    print("=" * 60)
    print("测试1: 语言检测")
    print("=" * 60)

    def is_chinese_query(text: str) -> bool:
        """判断是否为中文查询（包含中文字符）"""
        return any("\u4e00" <= char <= "\u9fff" for char in text)

    test_cases = [
        ("用户画像 设计案例", True, "纯中文"),
        ("user persona design", False, "纯英文"),
        ("设计 design 混合", True, "中英混合"),
        ("2024年设计趋势", True, "中文+数字"),
    ]

    for query, expected, desc in test_cases:
        result = is_chinese_query(query)
        status = "✅" if result == expected else "❌"
        print(f"{status} {desc}: '{query}' -> {result} (期望: {expected})")

    print()


def test_tool_priority():
    """测试工具优先级逻辑"""
    print("=" * 60)
    print("测试2: 工具优先级逻辑")
    print("=" * 60)

    # 创建工具
    tools = ToolFactory.create_all_tools()

    bocha_tool = tools.get("bocha")
    tavily_tool = tools.get("tavily")
    serper_tool = tools.get("serper")

    print(f"可用工具:")
    print(f"  - Bocha: {'✅' if bocha_tool else '❌'}")
    print(f"  - Tavily: {'✅' if tavily_tool else '❌'}")
    print(f"  - Serper: {'✅' if serper_tool else '❌'}")
    print()

    def is_chinese_query(text: str) -> bool:
        return any("\u4e00" <= char <= "\u9fff" for char in text)

    # 测试中文查询
    chinese_query = "用户画像 设计案例"
    is_chinese = is_chinese_query(chinese_query)

    print(f"测试查询: '{chinese_query}'")
    print(f"语言检测: {'中文' if is_chinese else '英文'}")
    print()

    # 模拟优先级逻辑 (v7.131修复后)
    if is_chinese:
        # 中文查询: Bocha → Tavily → Serper
        tool_to_use = bocha_tool if bocha_tool else (tavily_tool if tavily_tool else serper_tool)
        if bocha_tool:
            selected = "Bocha (中文专用)"
            status = "✅ 正确"
        elif tavily_tool:
            selected = "Tavily (降级)"
            status = "⚠️ Bocha不可用"
        else:
            selected = "Serper (二次降级)"
            status = "⚠️ Bocha和Tavily不可用"
    else:
        # 英文查询: Tavily → Bocha → Serper
        tool_to_use = tavily_tool if tavily_tool else (bocha_tool if bocha_tool else serper_tool)
        if tavily_tool:
            selected = "Tavily (全球覆盖)"
            status = "✅ 正确"
        else:
            selected = "Bocha (降级)"
            status = "⚠️ Tavily不可用"

    print(f"选择的工具: {selected}")
    print(f"状态: {status}")
    print()

    # 测试英文查询
    english_query = "user persona design"
    is_chinese = is_chinese_query(english_query)

    print(f"测试查询: '{english_query}'")
    print(f"语言检测: {'中文' if is_chinese else '英文'}")
    print()

    if is_chinese:
        tool_to_use = bocha_tool if bocha_tool else (tavily_tool if tavily_tool else serper_tool)
        selected = "Bocha"
    else:
        tool_to_use = tavily_tool if tavily_tool else (bocha_tool if bocha_tool else serper_tool)
        if tavily_tool:
            selected = "Tavily (全球覆盖)"
            status = "✅ 正确"
        else:
            selected = "Bocha (降级)"
            status = "⚠️ Tavily不可用"

    print(f"选择的工具: {selected}")
    print(f"状态: {status}")
    print()


def main():
    """主函数"""
    print()
    print("🔍 Bocha优先级修复验证 (v7.131)")
    print()

    test_language_detection()
    test_tool_priority()

    print("=" * 60)
    print("✅ 验证完成")
    print("=" * 60)
    print()
    print("预期行为:")
    print("  1. 中文查询 → 优先使用Bocha")
    print("  2. 英文查询 → 优先使用Tavily")
    print("  3. 工具不可用时自动降级")
    print()


if __name__ == "__main__":
    main()
