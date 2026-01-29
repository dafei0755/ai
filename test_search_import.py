"""测试 search_routes 导入"""
import sys

sys.path.insert(0, ".")

try:
    from intelligent_project_analyzer.api.search_routes import router

    print(f"✅ search_routes 导入成功: {router}")
except Exception as e:
    print(f"❌ 导入失败: {e}")
    import traceback

    traceback.print_exc()
