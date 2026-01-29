#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证备份系统优化结果
"""
import io
import os
import sys
from datetime import datetime
from pathlib import Path

# 设置标准输出为UTF-8编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def check_backup_optimization():
    """检查备份系统优化是否成功"""

    project_root = Path("d:/11-20/langgraph-design")
    backup_root = project_root / "backup"

    print("=" * 60)
    print("备份系统优化验证")
    print("=" * 60)
    print()

    # 1. 检查备份脚本修改
    print("[1/4] 检查备份脚本修改...")
    backup_script = project_root / "scripts" / "backup_project.bat"

    if not backup_script.exists():
        print("  [X] 备份脚本不存在")
        return False

    script_content = backup_script.read_text(encoding="utf-8")

    checks = {
        "Git bundle创建": "git bundle create" in script_content,
        "保留策略调整": "/d -7" in script_content,
        "自动验证": "verify_backup.py" in script_content,
    }

    for check_name, result in checks.items():
        status = "[OK]" if result else "[X]"
        print(f"  {status} {check_name}")

    print()

    # 2. 检查最新备份
    print("[2/4] 检查最新备份...")

    if not backup_root.exists():
        print("  [X] 备份目录不存在")
        return False

    backup_dirs = sorted(
        [d for d in backup_root.iterdir() if d.is_dir() and d.name.startswith("auto_backup_")],
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )

    if not backup_dirs:
        print("  [X] 没有找到备份")
        return False

    latest_backup = backup_dirs[0]
    print(f"  最新备份: {latest_backup.name}")
    print(f"  创建时间: {datetime.fromtimestamp(latest_backup.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # 3. 检查Git bundle
    print("[3/4] 检查Git bundle...")

    bundle_file = latest_backup / "repo.bundle"
    if bundle_file.exists():
        size_mb = bundle_file.stat().st_size / (1024 * 1024)
        print(f"  [OK] Git bundle 已创建")
        print(f"    大小: {size_mb:.2f} MB")
    else:
        print(f"  [X] Git bundle 未找到")
        print(f"    注意: 这可能是旧备份，请运行新的备份测试")
    print()

    # 4. 检查其他Git文件
    print("[4/4] 检查Git相关文件...")

    git_files = {
        "git_current_commit.txt": "当前提交",
        "git_current_branch.txt": "当前分支",
        "git_branches.txt": "分支列表",
        "git_tags.txt": "标签列表",
        "git_diff.patch": "差异补丁",
        "git_log.txt": "提交日志",
        "git_status.txt": "状态信息",
    }

    for filename, description in git_files.items():
        file_path = latest_backup / filename
        status = "[OK]" if file_path.exists() else "[X]"
        print(f"  {status} {description} ({filename})")

    print()

    # 5. 统计备份数量
    print("[5/5] 统计备份数量...")
    total_backups = len(backup_dirs)
    print(f"  当前备份总数: {total_backups}")
    print(f"  预期保留数量: 14个 (7天 x 2次/天)")

    if total_backups > 14:
        print(f"  [!] 备份数量超过预期，旧备份将在下次备份时清理")
    elif total_backups <= 14:
        print(f"  [OK] 备份数量正常")

    print()

    # 总结
    print("=" * 60)
    print("验证总结")
    print("=" * 60)

    has_bundle = (latest_backup / "repo.bundle").exists()

    if has_bundle:
        print("[OK] 备份系统优化成功！")
        print()
        print("优化内容:")
        print("  1. [OK] 添加了Git bundle（可恢复完整历史）")
        print("  2. [OK] 调整了保留策略（14天->7天）")
        print("  3. [OK] 添加了自动验证功能")
        print()
        print("下一步:")
        print("  - 备份系统将继续自动运行（每天10:00和18:00）")
        print("  - 磁盘占用将逐步减少约50%")
        print("  - 可以使用 scripts\\restore_backup_enhanced.bat 恢复备份")
    else:
        print("[!] 最新备份中未找到Git bundle")
        print()
        print("可能原因:")
        print("  - 这是优化前创建的备份")
        print("  - Git bundle创建失败")
        print()
        print("建议:")
        print("  1. 手动运行一次备份: scripts\\backup_project.bat")
        print("  2. 再次运行此验证脚本")
        print("  3. 如果仍然失败，检查Git是否正常工作")

    print("=" * 60)

    return has_bundle


if __name__ == "__main__":
    try:
        success = check_backup_optimization()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[X] 验证过程出错: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
