"""测试导入"""
import sys

print(f"Python: {sys.executable}")

try:
    from intelligent_project_analyzer.services.session_archive_manager import ArchivedSearchSession

    print("ArchivedSearchSession import OK")
    print(f"Columns: is_deep_mode={hasattr(ArchivedSearchSession, 'is_deep_mode')}")

    from intelligent_project_analyzer.api.app import app

    print("API app import OK")
except Exception as e:
    print(f"Import error: {e}")
    import traceback

    traceback.print_exc()
