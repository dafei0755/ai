#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试自动化脚本
提供多种测试模式、前置条件检查、覆盖率报告生成等功能
"""
import argparse
import io
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 修复Windows控制台编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


class TestAutomation:
    """测试自动化主类"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.tests_dir = self.project_root / "tests"
        self.coverage_dir = self.project_root / "htmlcov"
        self.reports_dir = self.project_root / "test_reports"

    def check_preconditions(self):
        """检查测试前置条件"""
        print("🔍 检查测试环境前置条件...\n")

        all_passed = True

        # 1. 检查Python版本
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        if sys.version_info >= (3, 8):
            print(f"✅ Python >= 3.8: {python_version}")
        else:
            print(f"❌ Python版本过低: {python_version} (需要 >= 3.8)")
            all_passed = False

        # 2. 检查必需的包
        required_packages = [
            "pytest",
            "pytest-cov",
            "pytest-asyncio",
            "pytest-mock",
        ]

        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
                print(f"✅ Package: {package}: 已安装")
            except ImportError:
                print(f"❌ Package: {package}: 未安装")
                all_passed = False

        # 3. 检查环境变量
        env_vars = [
            "ANTHROPIC_API_KEY",
            "OPENAI_API_KEY",
        ]

        print("\n📌 环境变量检查:")
        for var in env_vars:
            if os.getenv(var):
                print(f"✅ {var}: 已设置")
            else:
                print(f"⚠️  {var}: 未设置 (某些测试可能需要)")

        # 4. 检查测试目录
        print("\n📁 目录检查:")
        if self.tests_dir.exists():
            print(f"✅ 测试目录存在: {self.tests_dir}")
            test_files = list(self.tests_dir.rglob("test_*.py"))
            print(f"   发现 {len(test_files)} 个测试文件")
        else:
            print(f"❌ 测试目录不存在: {self.tests_dir}")
            all_passed = False

        print("\n" + "=" * 60)
        if all_passed:
            print("✅ All preconditions passed!")
        else:
            print("❌ Some preconditions failed. Please fix them before running tests.")
        print("=" * 60 + "\n")

        return all_passed

    def run_tests(self, mode="all", verbose=True):
        """
        运行测试

        Args:
            mode: 测试模式 (all, unit, integration, fast, coverage, agents, workflow, interaction, security)
            verbose: 是否显示详细输出
        """
        print(f"🚀 运行测试模式: {mode}\n")

        # 定义不同测试模式的命令
        commands = {
            "all": ["python", "-m", "pytest", "tests/", "-v"],
            "unit": ["python", "-m", "pytest", "tests/", "-m", "unit", "-v"],
            "integration": ["python", "-m", "pytest", "tests/", "-m", "integration", "-v"],
            "fast": ["python", "-m", "pytest", "tests/", "-m", "not slow", "-v"],
            "coverage": [
                "python",
                "-m",
                "pytest",
                "tests/",
                "--cov=intelligent_project_analyzer",
                "--cov-report=html",
                "--cov-report=term",
                "--cov-report=json",
                "-v",
            ],
            "agents": ["python", "-m", "pytest", "tests/agents/", "-v"],
            "workflow": ["python", "-m", "pytest", "tests/workflow/", "-v"],
            "interaction": ["python", "-m", "pytest", "tests/interaction/", "-v"],
            "security": ["python", "-m", "pytest", "tests/security/", "-v"],
        }

        if mode not in commands:
            print(f"❌ 未知的测试模式: {mode}")
            print(f"可用模式: {', '.join(commands.keys())}")
            return False

        cmd = commands[mode]

        try:
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=not verbose, text=True)

            if result.returncode == 0:
                print(f"\n✅ 测试通过 (模式: {mode})")
                return True
            else:
                print(f"\n❌ 测试失败 (模式: {mode})")
                if not verbose and result.stdout:
                    print(result.stdout)
                return False

        except Exception as e:
            print(f"❌ 执行测试时出错: {e}")
            return False

    def generate_coverage_report(self):
        """生成覆盖率报告"""
        print("📊 生成覆盖率报告...\n")

        # 确保报告目录存在
        self.reports_dir.mkdir(exist_ok=True)

        # 检查是否有coverage数据
        coverage_json = self.project_root / "coverage.json"
        if not coverage_json.exists():
            print("⚠️  没有找到coverage数据，请先运行: python scripts/test_automation.py --mode coverage")
            return False

        try:
            # 读取coverage数据
            with open(coverage_json, "r", encoding="utf-8") as f:
                coverage_data = json.load(f)

            # 生成Markdown报告
            report_file = self.reports_dir / f"coverage_report_{datetime.now().strftime('%Y%m%d')}.md"

            with open(report_file, "w", encoding="utf-8") as f:
                f.write("# 测试覆盖率报告\n\n")
                f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

                # 总体覆盖率
                totals = coverage_data.get("totals", {})
                percent_covered = totals.get("percent_covered", 0)
                f.write(f"## 总体覆盖率: {percent_covered:.2f}%\n\n")

                f.write(f"- **总行数**: {totals.get('num_statements', 0)}\n")
                f.write(f"- **已覆盖**: {totals.get('covered_lines', 0)}\n")
                f.write(f"- **未覆盖**: {totals.get('missing_lines', 0)}\n")
                f.write(f"- **分支覆盖**: {totals.get('percent_covered_display', 'N/A')}\n\n")

                # 文件详情
                f.write("## 文件覆盖率详情\n\n")
                f.write("| 文件 | 覆盖率 | 语句数 | 已覆盖 | 未覆盖 |\n")
                f.write("|------|--------|--------|--------|--------|\n")

                files = coverage_data.get("files", {})
                for file_path, file_data in sorted(files.items()):
                    summary = file_data.get("summary", {})
                    f.write(
                        f"| {file_path} | {summary.get('percent_covered', 0):.1f}% | "
                        f"{summary.get('num_statements', 0)} | "
                        f"{summary.get('covered_lines', 0)} | "
                        f"{summary.get('missing_lines', 0)} |\n"
                    )

                f.write("\n---\n")
                f.write(f"\n**HTML报告**: `htmlcov/index.html`\n")
                f.write(f"**JSON报告**: `coverage.json`\n")

            print(f"✅ 报告已生成: {report_file}")
            print(f"✅ HTML报告: {self.coverage_dir / 'index.html'}")
            return True

        except Exception as e:
            print(f"❌ 生成报告时出错: {e}")
            return False

    def clean_test_artifacts(self):
        """清理测试生成的文件"""
        print("🧹 清理测试文件...\n")

        import shutil

        artifacts = [
            self.coverage_dir,
            self.project_root / ".coverage",
            self.project_root / "coverage.json",
            self.project_root / ".pytest_cache",
        ]

        for artifact in artifacts:
            if artifact.exists():
                if artifact.is_dir():
                    shutil.rmtree(artifact)
                    print(f"✅ 已删除目录: {artifact.name}")
                else:
                    artifact.unlink()
                    print(f"✅ 已删除文件: {artifact.name}")

        # 清理__pycache__
        for pycache in self.project_root.rglob("__pycache__"):
            shutil.rmtree(pycache)
        print("✅ 已清理所有 __pycache__ 目录")

        print("\n✅ 清理完成")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="测试自动化脚本")
    parser.add_argument("--check", action="store_true", help="检查测试前置条件")
    parser.add_argument(
        "--mode",
        type=str,
        default="all",
        choices=["all", "unit", "integration", "fast", "coverage", "agents", "workflow", "interaction", "security"],
        help="测试模式",
    )
    parser.add_argument("--report", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--clean", action="store_true", help="清理测试文件")
    parser.add_argument("--quiet", action="store_true", help="静默模式")

    args = parser.parse_args()

    automation = TestAutomation()

    # 执行操作
    if args.check:
        automation.check_preconditions()

    elif args.report:
        automation.generate_coverage_report()

    elif args.clean:
        automation.clean_test_artifacts()

    else:
        # 默认运行测试
        if not args.quiet:
            automation.check_preconditions()
        automation.run_tests(mode=args.mode, verbose=not args.quiet)


if __name__ == "__main__":
    main()
