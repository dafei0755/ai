"""
快速单元测试运行脚本 - v7.218
测试覆盖：搜索体验优化（进度提示、Phase 分离、事件流）
"""

import os
import sys
from pathlib import Path

import pytest


def main():
    """运行v7.218搜索体验优化单元测试"""
    print("🧪 v7.218 搜索体验优化 - 单元测试")
    print("=" * 60)
    print("测试覆盖：")
    print("  1. analysis_progress 事件发送 (Bug 1: 164s 延迟)")
    print("  2. thinking_chunk phase 字段区分 (Bug 2: 顺序异常)")
    print("  3. round_sources 事件结构 (Bug 3: 搜索结果缺失)")
    print("  4. Phase 0/Phase 2 状态分离 (Bug 4: 多轮解题思考)")
    print("=" * 60)

    # 设置项目路径
    project_root = Path(__file__).parent
    test_file = project_root / "tests" / "unit" / "services" / "test_ucppt_search_engine_v7218.py"

    if not test_file.exists():
        print(f"❌ 测试文件不存在: {test_file}")
        return 1

    # 配置pytest参数
    pytest_args = [
        str(test_file),
        "-v",  # 详细输出
        "--tb=short",  # 简短的traceback
        "-x",  # 遇到失败就停止
        "--maxfail=3",  # 最多3个失败
        "-m",
        "unit",  # 只运行单元测试
        "--disable-warnings",  # 禁用警告以保持输出清洁
    ]

    print(f"\n📂 测试文件: {test_file}")
    print(f"🔧 pytest参数: {' '.join(pytest_args)}")
    print("=" * 60 + "\n")

    # 运行测试
    try:
        exit_code = pytest.main(pytest_args)

        print("\n" + "=" * 60)
        if exit_code == 0:
            print("🎉 所有 v7.218 单元测试通过!")
            print("\n✅ Bug 修复验证:")
            print("   • Bug 1 (164s延迟): analysis_progress 事件正确发送")
            print("   • Bug 2 (顺序异常): Phase 0/Phase 2 事件正确分离")
            print("   • Bug 3 (结果缺失): round_sources 结构正确")
            print("   • Bug 4 (多轮思考): thinking_chunk 包含 phase 字段")
        else:
            print(f"❌ 测试失败，退出代码: {exit_code}")

        return exit_code

    except Exception as e:
        print(f"❌ 测试运行异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
