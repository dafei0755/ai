"""
测试脚本：验证BochaSearchTool的name属性修复

测试内容：
1. 验证BochaSearchTool实例有name属性
2. 验证name属性值正确
3. 模拟LangChain工具绑定场景
"""

import sys

sys.path.insert(0, "d:/11-20/langgraph-design")

from intelligent_project_analyzer.agents.bocha_search_tool import BochaSearchTool

print("=" * 80)
print("[TEST] BochaSearchTool P0修复验证")
print("=" * 80)

# 测试1：创建工具实例
print("\n[Test 1] 创建BochaSearchTool实例")
print("-" * 80)
try:
    tool = BochaSearchTool(api_key="test_key", base_url="https://api.bocha.cn", default_count=5, timeout=30)
    print(f"[OK] 工具实例创建成功: {tool}")
except Exception as e:
    print(f"[ERROR] 实例创建失败: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# 测试2：验证name属性
print("\n[Test 2] 验证name属性")
print("-" * 80)
if hasattr(tool, "name"):
    print("[OK] 工具有name属性")
    print(f"   属性值: '{tool.name}'")

    if tool.name == "bocha_search":
        print("[OK] 属性值正确: bocha_search")
    else:
        print(f"[FAIL] 属性值错误: 期望 'bocha_search', 实际 '{tool.name}'")
else:
    print("[FAIL] 工具缺少name属性")
    sys.exit(1)

# 测试3：模拟LangChain工具名称获取（base.py:485-496的逻辑）
print("\n[Test 3] 模拟LangChain工具名称获取")
print("-" * 80)
tools = [tool]
tool_names = []
for t in tools:
    if hasattr(t, "name"):
        tool_names.append(t.name)
        print(f"[OK] 通过name属性获取: {t.name}")
    elif hasattr(t, "__name__"):
        tool_names.append(t.__name__)
        print(f"[OK] 通过__name__属性获取: {t.__name__}")
    else:
        print("[FAIL] 无法获取工具名称")

if tool_names:
    print(f"[OK] 工具名称列表: {tool_names}")
else:
    print("[FAIL] 未能获取任何工具名称")
    sys.exit(1)

# 测试4：模拟bind_tools场景（task_oriented_expert_factory.py:254-256）
print("\n[Test 4] 模拟bind_tools工具名称提取")
print("-" * 80)
try:
    tool_names_for_binding = [getattr(t, "name", str(t)) for t in tools]
    print(f"[OK] getattr提取成功: {tool_names_for_binding}")

    if "bocha_search" in tool_names_for_binding:
        print("[OK] 工具名称正确包含在列表中")
    else:
        print(f"[FAIL] 工具名称不在列表中: {tool_names_for_binding}")
        sys.exit(1)
except Exception as e:
    print(f"[ERROR] getattr提取失败: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("[OK] 所有测试通过 - BochaSearchTool P0修复成功")
print("=" * 80)
print("\n修复效果：")
print("✅ 工具实例正确创建name属性")
print("✅ name属性值为'bocha_search'")
print("✅ 兼容base.py的工具查找逻辑")
print("✅ 兼容task_oriented_expert_factory.py的bind_tools逻辑")
print("\n预期结果：")
print("📊 专家执行成功率：60% → 100%（3/5失败 → 0/5失败）")
print("📊 工具调用失败：100% → 0%（BochaSearchTool）")
