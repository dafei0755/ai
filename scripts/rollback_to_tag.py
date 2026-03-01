"""按稳定 Tag 一键回滚。

默认行为（安全）：
1) 检查工作区是否干净。
2) 校验 tag 格式为 vX.Y.Z 且存在。
3) 创建当前快照分支 recovery/pre_rollback_<timestamp>。
4) 基于该 tag 创建 rollback 分支并切换到该分支。

可选危险模式：--mode hard-reset
会将当前分支 hard reset 到目标 tag。
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path


STABLE_TAG_RE = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def _run(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True, check=check)


def _git_ok(repo: Path) -> bool:
    try:
        r = _run(["git", "rev-parse", "--is-inside-work-tree"], repo, check=False)
        return r.returncode == 0 and r.stdout.strip() == "true"
    except Exception:
        return False


def _working_tree_clean(repo: Path) -> bool:
    r = _run(["git", "status", "--porcelain"], repo, check=False)
    return r.returncode == 0 and not r.stdout.strip()


def _tag_exists(repo: Path, tag: str) -> bool:
    r = _run(["git", "rev-parse", f"refs/tags/{tag}"], repo, check=False)
    return r.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="按稳定 Tag 回滚")
    parser.add_argument("tag", help="目标稳定 Tag（例如 v8.0.0）")
    parser.add_argument(
        "--mode",
        choices=["safe-branch", "hard-reset"],
        default="safe-branch",
        help="safe-branch: 创建回滚分支（默认）；hard-reset: 当前分支硬回滚",
    )
    parser.add_argument("--force", action="store_true", help="忽略未提交改动检查")
    args = parser.parse_args()

    repo = Path(__file__).resolve().parents[1]

    if not _git_ok(repo):
        print("❌ 当前目录不是 Git 仓库")
        return 1

    if not STABLE_TAG_RE.match(args.tag):
        print(f"❌ 非法稳定 Tag: {args.tag}（必须是 vX.Y.Z）")
        return 1

    if not _tag_exists(repo, args.tag):
        print(f"❌ Tag 不存在: {args.tag}")
        return 1

    if not args.force and not _working_tree_clean(repo):
        print("❌ 工作区有未提交改动，请先提交/暂存（或使用 --force）")
        return 1

    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_branch = f"recovery/pre_rollback_{ts}"
    rollback_branch = f"rollback/{args.tag}_{ts}"

    # 先保存当前快照分支
    _run(["git", "branch", backup_branch], repo)

    if args.mode == "safe-branch":
        _run(["git", "switch", "-c", rollback_branch, args.tag], repo)
        print("✅ 已创建回滚分支并切换")
        print(f"   backup:   {backup_branch}")
        print(f"   rollback: {rollback_branch} -> {args.tag}")
        return 0

    # hard-reset 模式
    _run(["git", "reset", "--hard", args.tag], repo)
    print("✅ 已执行 hard reset 回滚")
    print(f"   backup: {backup_branch}")
    print(f"   current branch -> {args.tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
