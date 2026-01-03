#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""安装Git Hooks脚本"""

import os
import shutil
import stat
from pathlib import Path


def install_hooks():
    """安装Git Commit-msg Hook"""

    # 路径配置
    project_root = Path(__file__).parent.parent.parent
    hooks_dir = project_root / ".git" / "hooks"
    source_hook = project_root / ".git" / "hooks" / "commit-msg-record-fix"
    target_hook = project_root / ".git" / "hooks" / "post-commit"

    # 确保hooks目录存在
    hooks_dir.mkdir(parents=True, exist_ok=True)

    # 检查源文件是否存在
    if not source_hook.exists():
        print(f"❌ 源Hook文件不存在: {source_hook}")
        print("   请确保 .git/hooks/commit-msg-record-fix 文件已创建")
        return False

    # 创建post-commit hook（在提交后执行，不阻塞提交）
    hook_content = f'''#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Auto-generated post-commit hook for fix recording"""
import sys
import subprocess

# 运行修复记录检查
sys.exit(subprocess.call([sys.executable, r"{source_hook.as_posix()}", ".git/COMMIT_EDITMSG"]))
'''

    # 写入hook文件
    with open(target_hook, "w", encoding="utf-8") as f:
        f.write(hook_content)

    # 设置权限
    if os.name != "nt":
        os.chmod(target_hook, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)

    print(f"✅ Git Hook 已配置: {target_hook}")
    print("\n" + "=" * 60)
    print("🎉 自动记录系统配置完成！")
    print("=" * 60)
    print("\n📋 工作原理：")
    print("  1. 每次 git commit 提交后自动触发")
    print("  2. 检测提交消息是否包含'修复'、'fix'等关键词")
    print("  3. 如果是修复提交，会提示是否记录到知识库")
    print("\n💡 使用建议：")
    print("  - 修复完成后正常提交代码即可")
    print("  - 看到提示时选择'y'立即记录（推荐）")
    print("  - 也可以选择'n'稍后手动记录")
    print("\n🔍 手动记录命令：")
    print("  python .github\\scripts\\record_fix.py --interactive")
    print("\n📊 查看历史修复：")
    print("  python .github\\scripts\\search_fix.py --stats")
    print("=" * 60)

    return True


if __name__ == "__main__":
    install_hooks()
