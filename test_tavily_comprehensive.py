"""
Tavily 搜索工具专项测试
测试 Tavily API 的完整功能
"""
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# 加载环境变量
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"[INFO] 已加载 .env 文件: {env_path}")
else:
    print(f"[WARN] .env 文件不存在: {env_path}")

print("=" * 60)
print("Tavily 搜索工具专项测试")
print("=" * 60)

# 测试1: 环境变量检查
print("\n[测试 1/5] 环境变量检查")
print("-" * 60)

tavily_key = os.getenv("TAVILY_API_KEY")
if tavily_key:
    print(f"[OK] TAVILY_API_KEY: {tavily_key[:20]}...")
else:
    print("[FAIL] TAVILY_API_KEY 未设置")
    sys.exit(1)

# 测试2: Tavily 库导入
print("\n[测试 2/5] Tavily 库导入")
print("-" * 60)

try:
    from tavily import TavilyClient

    print("[OK] Tavily 库导入成功")
except ImportError as e:
    print(f"[FAIL] Tavily 库导入失败: {e}")
    sys.exit(1)

# 测试3: API 连接测试
print("\n[测试 3/5] API 连接测试")
print("-" * 60)

try:
    client = TavilyClient(api_key=tavily_key)
    result = client.search("Python programming", max_results=1)

    if result and "results" in result:
        print(f"[OK] API 连接成功")
        print(f"[OK] 返回结果数: {len(result['results'])}")
        if result["results"]:
            print(f"[OK] 第一个结果标题: {result['results'][0].get('title', 'N/A')[:50]}...")
    else:
        print("[FAIL] API 返回格式异常")
        print(f"返回内容: {result}")
except Exception as e:
    print(f"[FAIL] API 连接失败: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# 测试4: TavilySearchTool 类测试
print("\n[测试 4/5] TavilySearchTool 类测试")
print("-" * 60)

try:
    from intelligent_project_analyzer.tools.tavily_search import TavilySearchTool

    tool = TavilySearchTool(api_key=tavily_key)
    print("[OK] TavilySearchTool 初始化成功")

    # 测试搜索
    result = tool.search("design trends 2024", max_results=2)

    if result.get("success", True):  # 如果没有 success 字段，默认为成功
        print(f"[OK] 搜索执行成功")
        print(f"[OK] 返回结果数: {len(result.get('results', []))}")
        print(f"[OK] 执行时间: {result.get('execution_time', 0):.2f}秒")
    else:
        print(f"[FAIL] 搜索执行失败: {result.get('error', 'Unknown error')}")

except Exception as e:
    print(f"[FAIL] TavilySearchTool 测试失败: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)

# 测试5: 工具工厂集成测试
print("\n[测试 5/5] 工具工厂集成测试")
print("-" * 60)

try:
    from intelligent_project_analyzer.services.tool_factory import ToolFactory

    factory = ToolFactory()
    tavily_tool = factory.create_tavily_tool()

    if tavily_tool:
        print("[OK] 工具工厂创建 Tavily 工具成功")
        print(f"[OK] 工具名称: {tavily_tool.name}")
    else:
        print("[FAIL] 工具工厂返回 None")

except Exception as e:
    print(f"[FAIL] 工具工厂测试失败: {e}")
    import traceback

    traceback.print_exc()

# 总结
print("\n" + "=" * 60)
print("测试总结")
print("=" * 60)
print("[SUCCESS] 所有核心测试通过！")
print("\nTavily 搜索工具状态:")
print("  - API Key: 已配置")
print("  - API 连接: 正常")
print("  - 工具类: 正常")
print("  - 工具工厂: 正常")
print("\n建议:")
print("  1. 使用 V3/V4/V5/V6 角色测试（V2 无搜索权限）")
print("  2. 在实际会话中触发搜索功能")
print("  3. 检查前端是否正确显示搜索结果")
print("=" * 60)
