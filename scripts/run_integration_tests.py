#!/usr/bin/env python
"""
集成测试运行器

支持运行不同级别的集成测试：
- --critical-only: 仅运行P0关键集成测试
- --full: 运行所有集成测试
- --regression: 运行回归测试

使用示例:
    python scripts/run_integration_tests.py --critical-only
    python scripts/run_integration_tests.py --full
    python scripts/run_integration_tests.py --regression

作者: Copilot AI Testing Assistant
创建日期: 2026-01-04
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import List


def run_pytest(markers: List[str], extra_args: List[str] = None) -> int:
    """
    运行pytest with指定的markers

    Args:
        markers: pytest marker列表
        extra_args: 额外的pytest参数

    Returns:
        pytest退出码
    """
    cmd = ["pytest"]

    # 添加markers
    for marker in markers:
        cmd.extend(["-m", marker])

    # 添加额外参数
    if extra_args:
        cmd.extend(extra_args)

    print(f"运行命令: {' '.join(cmd)}")
    print("=" * 80)

    result = subprocess.run(cmd, cwd=Path(__file__).parent.parent)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="集成测试运行器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
测试级别说明:
  --critical-only    仅运行P0关键集成测试（integration_critical标记）
                     包含：图片生成、WebSocket推送、数据库查询关键路径

  --full             运行所有集成测试（integration标记）
                     包含所有集成测试，耗时较长

  --regression       运行回归测试（regression标记）
                     防止历史BUG复现，覆盖前5个高频错误

  --all              运行集成测试 + 回归测试

示例:
  # 仅运行P0关键测试（CI快速验证）
  python scripts/run_integration_tests.py --critical-only

  # 运行所有集成测试（发布前全面验证）
  python scripts/run_integration_tests.py --full

  # 运行回归测试（防止BUG复现）
  python scripts/run_integration_tests.py --regression

  # 运行集成+回归测试
  python scripts/run_integration_tests.py --all
        """,
    )

    parser.add_argument("--critical-only", action="store_true", help="仅运行P0关键集成测试")

    parser.add_argument("--full", action="store_true", help="运行所有集成测试")

    parser.add_argument("--regression", action="store_true", help="运行回归测试")

    parser.add_argument("--all", action="store_true", help="运行集成测试 + 回归测试")

    parser.add_argument("-v", "--verbose", action="store_true", help="详细输出")

    parser.add_argument("--failfast", action="store_true", help="第一个失败后立即停止")

    parser.add_argument("--no-redis", action="store_true", help="跳过需要Redis的测试")

    args = parser.parse_args()

    # 构建pytest参数
    extra_args = []

    if args.verbose:
        extra_args.append("-vv")

    if args.failfast:
        extra_args.append("-x")

    if args.no_redis:
        extra_args.extend(["-k", "not redis"])

    # 确定要运行的测试
    exit_code = 0

    if args.critical_only:
        print("🔥 运行P0关键集成测试...")
        print("-" * 80)
        exit_code = run_pytest(["integration_critical"], extra_args)

    elif args.full:
        print("🔄 运行所有集成测试...")
        print("-" * 80)
        exit_code = run_pytest(["integration"], extra_args)

    elif args.regression:
        print("🐛 运行回归测试（防止历史BUG复现）...")
        print("-" * 80)
        exit_code = run_pytest(["regression"], extra_args)

    elif args.all:
        print("🎯 运行集成测试 + 回归测试...")
        print("-" * 80)
        exit_code = run_pytest(["integration or regression"], extra_args)

    else:
        # 默认运行P0测试
        print("🔥 默认运行P0关键集成测试 (使用 --help 查看更多选项)...")
        print("-" * 80)
        exit_code = run_pytest(["integration_critical"], extra_args)

    # 输出结果摘要
    print("\n" + "=" * 80)
    if exit_code == 0:
        print("✅ 测试通过")
    else:
        print(f"❌ 测试失败 (退出码: {exit_code})")
    print("=" * 80)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
