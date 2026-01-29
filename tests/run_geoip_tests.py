"""
运行 GeoIP 单元测试

使用方法:
  python tests/run_geoip_tests.py
  python tests/run_geoip_tests.py -v  # 详细输出
  python tests/run_geoip_tests.py --cov  # 包含覆盖率报告
"""

import sys
from pathlib import Path

import pytest

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    """运行测试"""
    args = [
        "tests/services/test_geoip_service.py",
        "tests/integration/test_geoip_integration.py",
        "-v",  # 详细输出
        "--tb=short",  # 简化回溯信息
        "--color=yes",  # 彩色输出
    ]

    # 检查是否请求覆盖率报告
    if "--cov" in sys.argv:
        args.extend(
            [
                "--cov=intelligent_project_analyzer.services.geoip_service",
                "--cov-report=term-missing",
                "--cov-report=html",
            ]
        )

    # 检查是否只运行快速测试
    if "--fast" in sys.argv:
        args.append('-m "not slow"')

    print("=" * 70)
    print(" 🧪 运行 GeoIP 单元测试")
    print("=" * 70)
    print()

    exit_code = pytest.main(args)

    print()
    print("=" * 70)
    if exit_code == 0:
        print(" ✅ 所有测试通过！")
    else:
        print(f" ❌ 测试失败 (退出码: {exit_code})")
    print("=" * 70)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
