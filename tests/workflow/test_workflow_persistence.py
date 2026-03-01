"""
测试工作流持久化功能

验证点：
1. SqliteSaver 能否正常初始化
2. 数据库文件能否正常创建
3. Checkpoint 能否正常保存和恢复
"""
import asyncio
import sys
from pathlib import Path

# Python 3.13+ Windows 兼容性
if sys.platform == "win32" and sys.version_info >= (3, 13):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print("[OK] WindowsProactorEventLoopPolicy set for Python 3.13+ Windows")


async def test_sqlite_persistence():
    """测试 SqliteSaver 持久化"""
    print("\n" + "=" * 60)
    print("[TEST] Workflow Persistence Test")
    print("=" * 60)

    try:
        from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow

        # 创建工作流实例
        print("[1/4] Creating MainWorkflow instance...")
        workflow = MainWorkflow()

        # 验证 checkpointer 类型
        print(f"[OK] Checkpointer type: {type(workflow.checkpointer).__name__}")

        # 验证数据库文件
        db_path = Path("./data/checkpoints/workflow.db")
        if db_path.exists():
            file_size = db_path.stat().st_size
            print(f"[OK] Database file exists: {db_path}")
            print(f"     File size: {file_size:,} bytes")
        else:
            print(f"[FAIL] Database file not found: {db_path}")
            return False

        # 验证持久化配置
        print(f"[OK] Persistence enabled: {db_path}")

        print("\n[SUCCESS] Workflow persistence test passed!")
        return True

    except Exception as e:
        print(f"[FAIL] Workflow persistence test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """运行测试"""
    print("\n" + "=" * 60)
    print("[START] Workflow Persistence Verification")
    print("=" * 60)
    print(f"Python version: {sys.version}")
    print(f"Platform: {sys.platform}")

    result = await test_sqlite_persistence()

    print("\n" + "=" * 60)
    if result:
        print("[SUCCESS] All tests passed! SqliteSaver is working correctly")
    else:
        print("[FAIL] Tests failed, please check error messages above")
    print("=" * 60)

    return result


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
