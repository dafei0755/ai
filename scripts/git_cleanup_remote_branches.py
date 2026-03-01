"""远程分支清理工具（支持 dry-run）。

目标：
1) 识别 origin 下的远程分支。
2) 根据“是否已合并到 origin/main + 天龄阈值”给出候选清单。
3) 可选执行远程删除（默认仅预览，不做任何删除）。

示例：
- 仅预览（默认）：
  python scripts/git_cleanup_remote_branches.py

- 预览并显示可删除分支：
  python scripts/git_cleanup_remote_branches.py --min-age-days 14

- 真正执行删除（仅删除已合并且超过阈值的分支）：
  python scripts/git_cleanup_remote_branches.py --apply --min-age-days 14
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import subprocess
import sys
from typing import List, Set


@dataclasses.dataclass
class BranchInfo:
    name: str
    commit_dt: dt.datetime
    age_days: int
    merged_into_main: bool


def _run_git(args: List[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False)


def _require_git_ok(result: subprocess.CompletedProcess[str], action: str) -> str:
    if result.returncode != 0:
        raise RuntimeError(f"{action} 失败: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout


def _parse_ref_line(line: str) -> BranchInfo | None:
    # format: origin/branch|2026-01-03 16:14:20 +0800
    parts = line.strip().split("|", 1)
    if len(parts) != 2:
        return None

    name, dts = parts[0].strip(), parts[1].strip()
    if not name or name in {"origin", "origin/HEAD"}:
        return None

    commit_dt = dt.datetime.fromisoformat(dts)
    age_days = (dt.datetime.now(commit_dt.tzinfo) - commit_dt).days

    return BranchInfo(name=name, commit_dt=commit_dt, age_days=age_days, merged_into_main=False)


def _fetch_prune() -> None:
    res = _run_git(["fetch", "--prune"])
    if res.returncode != 0:
        # 网络不稳定时不直接中断，给出提示并继续使用本地远程跟踪信息。
        print(f"⚠️ fetch --prune 失败，将基于本地远程跟踪信息继续: {res.stderr.strip() or res.stdout.strip()}")
    else:
        print("✅ 已执行 git fetch --prune")


def _list_remote_refs() -> List[BranchInfo]:
    res = _run_git(["for-each-ref", "refs/remotes/origin", "--format=%(refname:short)|%(committerdate:iso8601)"])
    out = _require_git_ok(res, "列出远程引用")

    refs: List[BranchInfo] = []
    for line in out.splitlines():
        info = _parse_ref_line(line)
        if info:
            refs.append(info)

    refs.sort(key=lambda x: x.commit_dt, reverse=True)
    return refs


def _list_merged_into_origin_main() -> Set[str]:
    res = _run_git(["branch", "-r", "--merged", "origin/main"])
    out = _require_git_ok(res, "获取已合并分支")

    merged: Set[str] = set()
    for line in out.splitlines():
        item = line.strip()
        if item:
            merged.add(item)
    return merged


def _delete_remote_branch(remote_branch: str) -> tuple[bool, str]:
    # origin/foo -> foo
    short_name = remote_branch.replace("origin/", "", 1)
    res = _run_git(["push", "origin", "--delete", short_name])
    if res.returncode == 0:
        return True, res.stdout.strip() or "deleted"
    return False, res.stderr.strip() or res.stdout.strip() or "unknown error"


def main() -> int:
    parser = argparse.ArgumentParser(description="远程分支清理工具（默认 dry-run）")
    parser.add_argument("--min-age-days", type=int, default=14, help="最小天龄阈值（默认14）")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="执行删除（默认不删除，仅预览）",
    )
    parser.add_argument(
        "--protect",
        nargs="*",
        default=["origin/main", "origin/master", "origin/HEAD"],
        help="保护分支列表（不会删除）",
    )

    args = parser.parse_args()

    try:
        _fetch_prune()
        refs = _list_remote_refs()
        merged = _list_merged_into_origin_main()

        for r in refs:
            r.merged_into_main = r.name in merged

        print("\n=== 远程分支盘点 ===")
        print("branch|age_days|merged_into_origin_main")
        for r in refs:
            print(f"{r.name}|{r.age_days}|{'yes' if r.merged_into_main else 'no'}")

        candidates = [
            r
            for r in refs
            if r.merged_into_main and r.age_days >= args.min_age_days and r.name not in set(args.protect)
        ]

        print("\n=== 可删除候选（已合并 + 超过阈值）===")
        if not candidates:
            print("(无)")
        else:
            for c in candidates:
                print(f"- {c.name} (age={c.age_days}d)")

        if not args.apply:
            print("\n🔍 当前为 dry-run（未执行删除）。如需执行删除，添加 --apply")
            return 0

        if not candidates:
            print("\n✅ 无需删除")
            return 0

        print("\n⚙️ 开始执行删除...")
        failed = 0
        for c in candidates:
            ok, msg = _delete_remote_branch(c.name)
            if ok:
                print(f"✅ 删除成功: {c.name}")
            else:
                failed += 1
                print(f"❌ 删除失败: {c.name} -> {msg}")

        if failed:
            print(f"\n⚠️ 清理完成，但有 {failed} 个分支删除失败")
            return 1

        print("\n✅ 清理完成")
        return 0

    except Exception as exc:
        print(f"❌ 执行失败: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
