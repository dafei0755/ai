"""发布 Tag 命名与版本一致性校验。

规则：
1) 稳定版 Tag 必须为 vX.Y.Z（严格 SemVer，带 v 前缀）。
2) 稳定版 Tag 必须与根目录 VERSION 一致（默认启用）。
3) 备份 Tag 使用 backup/... 命名，不视为稳定发布 Tag。
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


STABLE_TAG_RE = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
BACKUP_TAG_RE = re.compile(r"^backup/.+")


def _read_version(root: Path) -> str:
    return (root / "VERSION").read_text(encoding="utf-8").strip()


def _detect_tag_from_env() -> str | None:
    if os.getenv("GITHUB_REF_TYPE") == "tag":
        return os.getenv("GITHUB_REF_NAME")
    return None


def _detect_exact_tag_from_git(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--exact-match"],
            cwd=str(root),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            tag = result.stdout.strip()
            return tag or None
    except Exception:
        pass
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="校验发布 Tag 命名规范")
    parser.add_argument("--tag", help="要校验的 Tag（不传则自动检测）")
    parser.add_argument(
        "--allow-skip",
        action="store_true",
        help="未检测到 tag 时返回成功（用于普通分支 CI）",
    )
    parser.add_argument(
        "--no-version-match",
        action="store_true",
        help="仅校验格式，不校验是否与 VERSION 一致",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    version = _read_version(root)
    expected_stable_tag = f"v{version}"

    tag = args.tag or _detect_tag_from_env() or _detect_exact_tag_from_git(root)

    if not tag:
        if args.allow_skip:
            print("ℹ️ 未检测到 Tag，跳过 Tag 命名校验。")
            return 0
        print("❌ 未检测到 Tag，请通过 --tag 指定。")
        return 1

    if BACKUP_TAG_RE.match(tag):
        print(f"ℹ️ 检测到备份 Tag: {tag}（非稳定发布 Tag）")
        return 0

    if not STABLE_TAG_RE.match(tag):
        print(f"❌ Tag 命名不合法: {tag}，稳定发布必须为 vX.Y.Z")
        return 1

    if not args.no_version_match and tag != expected_stable_tag:
        print(f"❌ Tag 与 VERSION 不一致: tag={tag}, VERSION={version}（期望 {expected_stable_tag}）")
        return 1

    print(f"✅ Tag 校验通过: {tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
