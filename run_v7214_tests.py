#!/usr/bin/env python3
"""
v7.214 深度搜索优化单元测试运行脚本
支持多种测试模式和详细的结果输出
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description=""):
    """运行命令并处理输出"""
    print(f"\n🔍 {description}")
    print(f"命令: {' '.join(cmd)}")
    print("=" * 60)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)  # 项目根目录

        # 输出结果
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print("错误输出:")
            print(result.stderr)

        print(f"\n退出代码: {result.returncode}")
        return result.returncode == 0

    except Exception as e:
        print(f"❌ 命令执行失败: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="v7.214 深度搜索优化单元测试")
    parser.add_argument("--mode", choices=["unit", "integration", "performance", "all"], default="unit", help="测试模式")
    parser.add_argument("--coverage", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--fast", action="store_true", help="快速模式（跳过慢速测试）")

    args = parser.parse_args()

    print("🧪 v7.214 深度搜索优化单元测试")
    print("=" * 60)

    # 基础pytest命令
    base_cmd = [sys.executable, "-m", "pytest"]

    # 添加测试文件路径
    test_file = "tests/unit/services/test_ucppt_search_engine_v7214.py"
    base_cmd.append(test_file)

    # 根据模式添加标记过滤
    if args.mode == "unit":
        base_cmd.extend(["-m", "unit"])
    elif args.mode == "integration":
        base_cmd.extend(["-m", "integration"])
    elif args.mode == "performance":
        base_cmd.extend(["-m", "performance"])
    elif args.mode == "all":
        pass  # 运行所有测试

    # 快速模式
    if args.fast:
        base_cmd.extend(["-m", "not slow"])

    # 详细输出
    if args.verbose:
        base_cmd.extend(["-v", "-s"])
    else:
        base_cmd.append("--tb=short")

    # 覆盖率选项
    if args.coverage:
        base_cmd.extend(
            [
                "--cov=intelligent_project_analyzer.services.ucppt_search_engine",
                "--cov-report=term-missing",
                "--cov-report=html:htmlcov/v7214_coverage",
            ]
        )

    # 其他有用的选项
    base_cmd.extend(["--strict-markers", "--maxfail=5", "-x"])  # 严格标记检查  # 最多5个失败后停止  # 遇到第一个失败就停止

    # 运行测试
    success = run_command(base_cmd, f"运行 v7.214 深度搜索优化{args.mode}测试")

    if success:
        print("\n🎉 测试运行成功!")

        if args.coverage:
            print("\n📊 覆盖率报告已生成:")
            print("  - 控制台报告: 见上方输出")
            print("  - HTML报告: htmlcov/v7214_coverage/index.html")
    else:
        print("\n❌ 测试运行失败!")
        sys.exit(1)

    # 运行代码质量检查
    if args.mode == "all":
        print("\n" + "=" * 60)
        print("🔍 运行代码质量检查...")

        # 检查代码风格（如果安装了flake8）
        try:
            flake8_cmd = [
                sys.executable,
                "-m",
                "flake8",
                "intelligent_project_analyzer/services/ucppt_search_engine.py",
                "--max-line-length=120",
                "--ignore=E501,W503",  # 忽略一些常见的风格问题
            ]
            run_command(flake8_cmd, "代码风格检查 (flake8)")
        except:
            print("⚠️  flake8 未安装，跳过代码风格检查")


if __name__ == "__main__":
    main()
