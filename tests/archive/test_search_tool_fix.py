"""
测试脚本：验证搜索工具传递和重搜机制

测试内容：
1. 验证ToolFactory能创建工具
2. 验证_filter_tools_for_role正确筛选工具
3. 验证工具的重搜方法存在且可调用
"""

import os
import sys

# 设置UTF-8编码
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

sys.path.insert(0, "d:/11-20/langgraph-design")

from intelligent_project_analyzer.services.tool_factory import ToolFactory
from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow

print("=" * 80)
print("[TEST] Search Tool Fix Verification")
print("=" * 80)

# 测试1：验证ToolFactory能创建工具
print("\n[Test 1] Verify ToolFactory can create tools")
print("-" * 80)
try:
    all_tools = ToolFactory.create_all_tools()
    print(f"[OK] Tools created: {len(all_tools)} tools")
    for tool_name, tool in all_tools.items():
        print(f"   - {tool_name}: {tool.__class__.__name__}")

        # 检查是否有重搜方法
        has_retry = hasattr(tool, "search_for_deliverable_with_retry")
        retry_status = "[OK] Has retry" if has_retry else "[WARN] No retry"
        print(f"     {retry_status}")
except Exception as e:
    print(f"[ERROR] Tool creation failed: {e}")
    import traceback

    traceback.print_exc()

# 测试2：验证角色工具筛选
print("\n[Test 2] Verify role-based tool filtering")
print("-" * 80)
try:
    workflow = MainWorkflow()

    test_roles = [
        ("V2_设计总监_2-1", "V2", []),  # 应该无工具
        ("V3_叙事专家_3-1", "V3", ["bocha", "tavily", "ragflow"]),
        ("V4_设计研究员_4-1", "V4", ["bocha", "tavily", "arxiv", "ragflow"]),
        ("V5_场景专家_5-1", "V5", ["bocha", "tavily", "ragflow"]),
        ("V6_总工程师_6-1", "V6", ["bocha", "tavily", "arxiv", "ragflow"]),
    ]

    for role_id, role_type, expected_tools in test_roles:
        role_tools = workflow._filter_tools_for_role(role_id, all_tools, {})
        actual_tool_names = list(role_tools.keys())

        # 过滤掉未配置的工具
        expected_available = [t for t in expected_tools if t in all_tools]

        match = set(actual_tool_names) == set(expected_available)
        status = "[OK]" if match else "[FAIL]"

        print(f"{status} {role_type}: Expected {len(expected_available)} tools, Got {len(actual_tool_names)}")
        print(f"   Expected: {expected_available}")
        print(f"   Actual: {actual_tool_names}")

except Exception as e:
    print(f"[ERROR] Tool filtering test failed: {e}")
    import traceback

    traceback.print_exc()

# 测试3：验证重搜方法签名
print("\n[Test 3] Verify retry method signatures")
print("-" * 80)
for tool_name, tool in all_tools.items():
    if hasattr(tool, "search_for_deliverable_with_retry"):
        import inspect

        sig = inspect.signature(tool.search_for_deliverable_with_retry)
        params = list(sig.parameters.keys())
        print(f"[OK] {tool_name}.search_for_deliverable_with_retry:")
        print(f"   Parameters: {', '.join(params)}")
    else:
        print(f"[WARN] {tool_name}: No retry method implemented")

print("\n" + "=" * 80)
print("[OK] All tests completed")
print("=" * 80)
