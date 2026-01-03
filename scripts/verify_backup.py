#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
备份验证脚本
验证备份的完整性和可用性
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# 设置标准输出为UTF-8编码（解决Windows控制台中文显示问题）
if sys.platform == "win32":
    import io

    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
BACKUP_ROOT = PROJECT_ROOT / "backup"


class BackupVerifier:
    """备份验证器"""

    def __init__(self, backup_dir: Path):
        self.backup_dir = Path(backup_dir)
        self.errors = []
        self.warnings = []
        self.passed_checks = []

    def verify(self) -> bool:
        """执行完整验证"""
        print("=" * 60)
        print(f"验证备份: {self.backup_dir.name}")
        print("=" * 60)
        print()

        # 1. 检查备份目录结构
        self._check_directory_structure()

        # 2. 验证Git bundle完整性
        self._verify_git_bundle()

        # 3. 检查关键文件存在性
        self._check_critical_files()

        # 4. 验证版本元数据
        self._verify_metadata()

        # 5. 检查代码文件数量
        self._check_code_files()

        # 6. 生成报告
        return self._generate_report()

    def _check_directory_structure(self):
        """检查备份目录结构"""
        print("[1/6] 检查目录结构...")

        required_dirs = ["config", "docs", "python", "frontend"]

        for dir_name in required_dirs:
            dir_path = self.backup_dir / dir_name
            if dir_path.exists():
                self.passed_checks.append(f"目录存在: {dir_name}/")
            else:
                self.errors.append(f"缺失关键目录: {dir_name}/")

        print(f"  ✓ 检查完成\n")

    def _verify_git_bundle(self):
        """验证Git bundle完整性"""
        print("[2/6] 验证Git bundle...")

        bundle_file = self.backup_dir / "repo.bundle"

        if not bundle_file.exists():
            self.warnings.append("未找到Git bundle文件（repo.bundle）")
            print(f"  ⚠ 未找到Git bundle\n")
            return

        # 使用git bundle verify验证
        try:
            result = subprocess.run(
                ["git", "bundle", "verify", str(bundle_file)], capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                self.passed_checks.append("Git bundle验证通过")
                print(f"  ✓ Git bundle完整性验证通过")

                # 统计bundle大小
                size_mb = bundle_file.stat().st_size / (1024 * 1024)
                print(f"  → Bundle大小: {size_mb:.2f} MB")
            else:
                self.errors.append(f"Git bundle验证失败: {result.stderr}")
                print(f"  ✗ Git bundle验证失败")

        except subprocess.TimeoutExpired:
            self.errors.append("Git bundle验证超时")
            print(f"  ✗ 验证超时")
        except FileNotFoundError:
            self.warnings.append("未安装Git，跳过bundle验证")
            print(f"  ⚠ 未安装Git")
        except Exception as e:
            self.errors.append(f"Git bundle验证异常: {str(e)}")
            print(f"  ✗ 验证异常: {e}")

        print()

    def _check_critical_files(self):
        """检查关键文件存在性"""
        print("[3/6] 检查关键文件...")

        critical_files = [
            "BACKUP_INFO.txt",
            "version_metadata.json",
            "git_log.txt",
            "git_current_commit.txt",
            "config/requirements.txt",
            "config/package.json",
        ]

        for file_path in critical_files:
            full_path = self.backup_dir / file_path
            if full_path.exists():
                self.passed_checks.append(f"文件存在: {file_path}")
            else:
                self.warnings.append(f"缺失文件: {file_path}")

        print(f"  ✓ 检查完成\n")

    def _verify_metadata(self):
        """验证版本元数据"""
        print("[4/6] 验证版本元数据...")

        metadata_file = self.backup_dir / "version_metadata.json"

        if not metadata_file.exists():
            self.warnings.append("缺失版本元数据文件")
            print(f"  ⚠ 未找到元数据文件\n")
            return

        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)

            required_fields = ["backup_time", "git_commit", "git_branch"]
            missing_fields = [field for field in required_fields if field not in metadata]

            if missing_fields:
                self.warnings.append(f"元数据缺失字段: {', '.join(missing_fields)}")
            else:
                self.passed_checks.append("版本元数据完整")
                print(f"  → 备份时间: {metadata.get('backup_time', 'N/A')}")
                print(f"  → 备份目录: {metadata.get('backup_dirname', metadata.get('backup_dir', 'N/A'))}")
                print(f"  → Git提交: {metadata.get('git_commit', 'N/A')[:8]}")
                print(f"  → Git分支: {metadata.get('git_branch', 'N/A')}")
                if "backup_version" in metadata:
                    print(f"  → 备份版本: {metadata.get('backup_version')}")

        except json.JSONDecodeError as e:
            self.errors.append(f"元数据JSON格式错误: {str(e)}")
            print(f"  ✗ JSON解析失败")
        except Exception as e:
            self.errors.append(f"元数据读取异常: {str(e)}")
            print(f"  ✗ 读取异常: {e}")

        print()

    def _check_code_files(self):
        """检查代码文件数量"""
        print("[5/6] 统计代码文件...")

        # 统计Python文件
        python_dir = self.backup_dir / "python"
        if python_dir.exists():
            python_files = list(python_dir.rglob("*.py"))
            print(f"  → Python文件: {len(python_files)} 个")
            if len(python_files) < 50:
                self.warnings.append(f"Python文件数量异常少: {len(python_files)}")
            else:
                self.passed_checks.append(f"Python文件数量正常: {len(python_files)}")
        else:
            self.errors.append("Python代码目录不存在")

        # 统计前端文件
        frontend_dir = self.backup_dir / "frontend"
        if frontend_dir.exists():
            ts_files = list(frontend_dir.rglob("*.ts")) + list(frontend_dir.rglob("*.tsx"))
            print(f"  → TypeScript文件: {len(ts_files)} 个")
            if len(ts_files) < 30:
                self.warnings.append(f"TypeScript文件数量异常少: {len(ts_files)}")
            else:
                self.passed_checks.append(f"TypeScript文件数量正常: {len(ts_files)}")
        else:
            self.errors.append("前端代码目录不存在")

        print()

    def _generate_report(self) -> bool:
        """生成验证报告"""
        print("[6/6] 生成验证报告...")
        print()
        print("=" * 60)
        print("验证结果汇总")
        print("=" * 60)

        # 通过的检查
        if self.passed_checks:
            print(f"\n✓ 通过检查 ({len(self.passed_checks)} 项):")
            for check in self.passed_checks[:5]:  # 只显示前5项
                print(f"  • {check}")
            if len(self.passed_checks) > 5:
                print(f"  ... 共 {len(self.passed_checks)} 项")

        # 警告
        if self.warnings:
            print(f"\n⚠ 警告 ({len(self.warnings)} 项):")
            for warning in self.warnings:
                print(f"  • {warning}")

        # 错误
        if self.errors:
            print(f"\n✗ 错误 ({len(self.errors)} 项):")
            for error in self.errors:
                print(f"  • {error}")

        # 最终结果
        print("\n" + "=" * 60)
        if self.errors:
            print("❌ 验证失败：发现严重错误")
            print("=" * 60)
            return False
        elif self.warnings:
            print("⚠️  验证通过（有警告）：备份可用但可能不完整")
            print("=" * 60)
            return True
        else:
            print("✅ 验证通过：备份完整且可用")
            print("=" * 60)
            return True


def verify_latest_backup():
    """验证最新的备份"""
    if not BACKUP_ROOT.exists():
        print(f"错误: 备份目录不存在: {BACKUP_ROOT}")
        return False

    # 查找最新的备份
    backups = sorted(
        [d for d in BACKUP_ROOT.iterdir() if d.is_dir() and d.name.startswith("auto_backup_")],
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )

    if not backups:
        print("错误: 未找到任何备份")
        return False

    latest_backup = backups[0]
    verifier = BackupVerifier(latest_backup)
    return verifier.verify()


def verify_all_backups():
    """验证所有备份"""
    if not BACKUP_ROOT.exists():
        print(f"错误: 备份目录不存在: {BACKUP_ROOT}")
        return

    backups = sorted(
        [d for d in BACKUP_ROOT.iterdir() if d.is_dir() and d.name.startswith("auto_backup_")],
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )

    if not backups:
        print("错误: 未找到任何备份")
        return

    print(f"找到 {len(backups)} 个备份，开始验证...\n")

    results = []
    for i, backup in enumerate(backups, 1):
        print(f"\n{'='*60}")
        print(f"验证 [{i}/{len(backups)}]: {backup.name}")
        print(f"{'='*60}\n")

        verifier = BackupVerifier(backup)
        success = verifier.verify()
        results.append((backup.name, success, len(verifier.errors), len(verifier.warnings)))

        print()

    # 汇总报告
    print("\n" + "=" * 60)
    print("所有备份验证汇总")
    print("=" * 60)
    for name, success, errors, warnings in results:
        status = "✓" if success else "✗"
        print(f"{status} {name:40s} | 错误: {errors} | 警告: {warnings}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--all":
        verify_all_backups()
    else:
        success = verify_latest_backup()
        sys.exit(0 if success else 1)
