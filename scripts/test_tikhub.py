"""
TikHub 集成测试脚本
"""
import os
import sys

from dotenv import load_dotenv

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 加载环境变量
load_dotenv()

print("=== TikHub Configuration Test ===")
print("BOCHA_TIKHUB_ENABLED:", os.getenv("BOCHA_TIKHUB_ENABLED"))
print("BOCHA_TIKHUB_API_KEY:", (os.getenv("BOCHA_TIKHUB_API_KEY") or "")[:30] + "...")
print("BOCHA_TIKHUB_PLATFORMS:", os.getenv("BOCHA_TIKHUB_PLATFORMS"))
print("BOCHA_TIKHUB_BASE_URL:", os.getenv("BOCHA_TIKHUB_BASE_URL"))
print("BOCHA_ENABLED:", os.getenv("BOCHA_ENABLED"))

print("\n=== Testing TikHub SDK Import ===")
try:
    from tikhub import Client as TikHubClient

    print("TikHub SDK imported successfully")
except ImportError as e:
    print("TikHub SDK import failed:", e)

print("\n=== Testing Settings ===")
from intelligent_project_analyzer.settings import settings

print("settings.bocha.tikhub_enabled:", settings.bocha.tikhub_enabled)
print(
    "settings.bocha.tikhub_api_key:",
    (settings.bocha.tikhub_api_key[:30] if settings.bocha.tikhub_api_key else "NOT SET") + "...",
)
print("settings.bocha.tikhub_platforms:", settings.bocha.tikhub_platforms)

print("\n=== Testing BochaSearchTool ===")
from intelligent_project_analyzer.agents.bocha_search_tool import create_bocha_search_tool_from_settings

tool = create_bocha_search_tool_from_settings()
if tool:
    print("BochaSearchTool created")
    print("   tikhub_enabled:", tool.tikhub_enabled)
    print("   tikhub_platforms:", tool.tikhub_platforms)
    print("   tikhub_client:", tool.tikhub_client is not None)

    # 执行实际搜索测试
    print("\n=== Testing TikHub Search ===")
    test_query = "咖啡店设计"
    print("Query:", test_query)

    # 测试单个平台搜索
    if tool.tikhub_enabled and tool.tikhub_client:
        print("\nSearching TikHub platforms...")
        tikhub_results = tool._search_tikhub(test_query)
        print("TikHub results count:", len(tikhub_results))
        if tikhub_results:
            for i, r in enumerate(tikhub_results[:3]):
                print("  ", i + 1, r.get("title", "无标题")[:50])
                print("      URL:", r.get("url", "无链接")[:60])
                print("      Platform:", r.get("platform", "unknown"))
else:
    print("Failed to create BochaSearchTool")

print("\n=== Testing TikHub SDK Import ===")
try:
    from tikhub import Client as TikHubClient

    print("✅ TikHub SDK imported successfully")
except ImportError as e:
    print(f"❌ TikHub SDK import failed: {e}")

print("\n=== Testing Settings ===")
from intelligent_project_analyzer.settings import settings

print(f"settings.bocha.tikhub_enabled: {settings.bocha.tikhub_enabled}")
print(
    f"settings.bocha.tikhub_api_key: {settings.bocha.tikhub_api_key[:30] if settings.bocha.tikhub_api_key else 'NOT SET'}..."
)
print(f"settings.bocha.tikhub_platforms: {settings.bocha.tikhub_platforms}")

print("\n=== Testing BochaSearchTool ===")
from intelligent_project_analyzer.agents.bocha_search_tool import create_bocha_search_tool_from_settings

tool = create_bocha_search_tool_from_settings()
if tool:
    print(f"✅ BochaSearchTool created")
    print(f"   tikhub_enabled: {tool.tikhub_enabled}")
    print(f"   tikhub_platforms: {tool.tikhub_platforms}")
    print(f"   tikhub_client: {tool.tikhub_client is not None}")
else:
    print("❌ Failed to create BochaSearchTool")
