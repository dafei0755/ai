#!/usr/bin/env python3
"""
根目录清洁度检查脚本
用于CI/CD和pre-commit检查，防止根目录堆积文件
"""
import os
import sys
from pathlib import Path
from typing import Dict, List

# 允许的根目录文件（白名单）
ALLOWED_ROOT_FILES = {
    # 核心文档（必须保留）
    "README.md",
    "QUICKSTART.md",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    "EMERGENCY_RECOVERY.md",
    "BACKUP_GUIDE.md",
    "README_TESTING.md",
    "NEXT_STEPS.md",
    "LICENSE",
    # 配置文件
    ".env",
    ".env.example",
    ".gitignore",
    ".gitattributes",
    ".pre-commit-config.yaml",
    "pytest.ini",
    "requirements.txt",
    "Makefile",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    # Git相关
    ".git",
    ".github",
}

# 文件类型限制
MAX_MD_FILES = 10  # 根目录最多10个.md文件
MAX_TOTAL_FILES = 20  # 根目录最多20个文件/文件夹（不含隐藏文件）


def get_root_files() -> List[str]:
    """获取根目录所有文件（不递归，不包括文件夹）"""
    root_path = Path(__file__).parent.parent
    return [item.name for item in root_path.iterdir() if item.is_file()]


def categorize_files(files: List[str]) -> Dict[str, List[str]]:
    """文件分类"""
    categories = {
        "allowed": [],  # 白名单内的文件
        "md_files": [],  # Markdown文件
        "scripts": [],  # 脚本文件
        "tests": [],  # 测试文件
        "temp": [],  # 临时文件
        "other": [],  # 其他文件
    }

    for file in files:
        # 跳过隐藏文件/文件夹（.开头）
        if file.startswith("."):
            if file in ALLOWED_ROOT_FILES:
                categories["allowed"].append(file)
            continue

        # 白名单检查
        if file in ALLOWED_ROOT_FILES:
            categories["allowed"].append(file)
            continue

        # Markdown文件
        if file.endswith(".md"):
            categories["md_files"].append(file)
        # 脚本文件
        elif file.endswith((".py", ".sh", ".bat", ".ps1")):
            categories["scripts"].append(file)
        # 测试文件
        elif file.startswith("test_") or file.endswith("_test.py"):
            categories["tests"].append(file)
        # 临时文件
        elif file in ("nul", "__pycache__") or file.endswith((".log", ".tmp", ".bak", ".swp")):
            categories["temp"].append(file)
        # 其他
        else:
            categories["other"].append(file)

    return categories


def check_violations(categories: Dict[str, List[str]]) -> List[str]:
    """检查违规项"""
    violations = []

    # 检查Markdown文件数
    md_count = len(categories["md_files"])
    if md_count > 0:
        violations.append(
            f"❌ 根目录发现 {md_count} 个未归类的 .md 文件（应为0）：\n   "
            + "\n   ".join(f"→ {f}" for f in categories["md_files"])
            + "\n   💡 应移动到: docs/ 下的对应模块目录"
        )

    # 检查脚本文件
    if categories["scripts"]:
        violations.append(
            f"❌ 根目录发现 {len(categories['scripts'])} 个脚本文件：\n   "
            + "\n   ".join(f"→ {f}" for f in categories["scripts"])
            + "\n   💡 应移动到: scripts/ 目录"
        )

    # 检查测试文件
    if categories["tests"]:
        violations.append(
            f"❌ 根目录发现 {len(categories['tests'])} 个测试文件：\n   "
            + "\n   ".join(f"→ {f}" for f in categories["tests"])
            + "\n   💡 应移动到: tests/ 目录"
        )

    # 检查临时文件
    if categories["temp"]:
        violations.append(
            f"⚠️  根目录发现 {len(categories['temp'])} 个临时文件：\n   "
            + "\n   ".join(f"→ {f}" for f in categories["temp"])
            + "\n   💡 建议删除或添加到 .gitignore"
        )

    # 检查其他未归类文件
    if categories["other"]:
        violations.append(
            f"⚠️  根目录发现 {len(categories['other'])} 个未归类文件：\n   "
            + "\n   ".join(f"→ {f}" for f in categories["other"])
            + "\n   💡 请评估是否需要移动到其他目录"
        )

    # 检查总文件数（排除隐藏文件）
    visible_files = [f for f in categories["allowed"] if not f.startswith(".")]
    total_visible = (
        len(visible_files)
        + len(categories["md_files"])
        + len(categories["scripts"])
        + len(categories["tests"])
        + len(categories["temp"])
        + len(categories["other"])
    )

    if total_visible > MAX_TOTAL_FILES:
        violations.append(f"❌ 根目录文件总数 {total_visible} 超出限制（最多 {MAX_TOTAL_FILES}）")

    return violations


def print_summary(categories: Dict[str, List[str]]):
    """打印汇总信息"""
    print("\n" + "=" * 70)
    print("🔍 根目录清洁度检查报告")
    print("=" * 70)

    # 统计
    print(f"\n✅ 白名单文件: {len(categories['allowed'])} 个")
    print(f"❗ 未归类 .md 文件: {len(categories['md_files'])} 个")
    print(f"❗ 脚本文件: {len(categories['scripts'])} 个")
    print(f"❗ 测试文件: {len(categories['tests'])} 个")
    print(f"⚠️  临时文件: {len(categories['temp'])} 个")
    print(f"⚠️  其他文件: {len(categories['other'])} 个")


def main():
    """主函数"""
    try:
        # 获取根目录文件
        files = get_root_files()

        # 分类
        categories = categorize_files(files)

        # 检查违规
        violations = check_violations(categories)

        # 打印汇总
        print_summary(categories)

        # 输出违规信息
        if violations:
            print("\n" + "=" * 70)
            print("⚠️  发现以下问题：")
            print("=" * 70)
            for violation in violations:
                print(f"\n{violation}")

            print("\n" + "=" * 70)
            print("📋 解决方案：")
            print("=" * 70)
            print("1. 运行清理脚本:")
            print("   python scripts/organize_root_files.py")
            print("\n2. 手动移动文件:")
            print("   - Markdown文档 → docs/")
            print("   - 脚本文件 → scripts/")
            print("   - 测试文件 → tests/")
            print("\n3. 查看文档规范:")
            print("   .github/DOCUMENTATION_RULES.md")
            print("=" * 70 + "\n")

            sys.exit(1)
        else:
            print("\n" + "=" * 70)
            print("✅ 根目录清洁度检查通过！")
            print("=" * 70 + "\n")
            sys.exit(0)

    except Exception as e:
        print(f"\n❌ 检查失败: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
