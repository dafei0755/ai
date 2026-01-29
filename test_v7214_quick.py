"""
快速单元测试运行脚本 - v7.214
简化版本，专注于核心功能测试
"""

import os
import sys
from pathlib import Path

import pytest


def main():
    """运行v7.214核心单元测试"""
    print("🧪 v7.214 深度搜索优化 - 快速单元测试")
    print("=" * 50)

    # 设置项目路径
    project_root = Path(__file__).parent
    test_file = project_root / "tests" / "unit" / "services" / "test_ucppt_search_engine_v7214.py"

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

    print(f"📂 测试文件: {test_file}")
    print(f"🔧 pytest参数: {' '.join(pytest_args)}")
    print("=" * 50)

    # 运行测试
    try:
        exit_code = pytest.main(pytest_args)

        if exit_code == 0:
            print("\n🎉 所有单元测试通过!")
        else:
            print(f"\n❌ 测试失败，退出代码: {exit_code}")

        return exit_code

    except Exception as e:
        print(f"❌ 测试运行异常: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
