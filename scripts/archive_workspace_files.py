"""Archive obvious root-level temporary files without deleting them.

Default mode is dry-run. Use --apply to move candidates into:
_archive/local-cleanup/YYYY-MM-DD/root-temp/
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
from pathlib import Path


TEMP_FILE_PATTERNS = [
    "_*.py",
    "_*.txt",
    "patch.py",
    "patch*.js",
    "update.py",
    "update_*.py",
    "check.py",
    "analyze_columns.py",
    "old.txt",
    "new_str.txt",
    "old_str.txt",
    "temp.txt",
    "test_replace.py",
    "fix_emoji_encoding.py",
    "verify_deployment_v7620.py",
    "test_step1.log",
]

PROTECTED_NAMES = {
    ".env",
    ".gitignore",
    "README.md",
    "QUICKSTART.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "Makefile",
    "requirements.txt",
}


def repo_root() -> Path:
    output = subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        encoding="utf-8",
    )
    return Path(output.strip()).resolve()


def is_tracked(root: Path, path: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", rel],
        cwd=root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    return result.returncode == 0


def unique_destination(destination_dir: Path, name: str) -> Path:
    destination = destination_dir / name
    if not destination.exists():
        return destination

    stem = destination.stem
    suffix = destination.suffix
    index = 1
    while True:
        candidate = destination_dir / f"{stem}.{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def collect_candidates(root: Path) -> list[Path]:
    candidates: list[Path] = []
    for pattern in TEMP_FILE_PATTERNS:
        candidates.extend(root.glob(pattern))

    result: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if not path.is_file():
            continue
        if path.name in PROTECTED_NAMES:
            continue
        if path.parent.resolve() != root:
            continue
        if is_tracked(root, path):
            continue
        result.append(path)
    return sorted(result, key=lambda item: item.name.lower())


def archive_candidates(root: Path, candidates: list[Path], apply: bool) -> Path:
    today = dt.date.today().isoformat()
    destination_dir = root / "_archive" / "local-cleanup" / today / "root-temp"
    manifest_path = destination_dir.parent / "archive-manifest.jsonl"

    if apply:
        destination_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows = []
    for source in candidates:
        destination = unique_destination(destination_dir, source.name)
        row = {
            "source": source.relative_to(root).as_posix(),
            "destination": destination.relative_to(root).as_posix(),
            "size": source.stat().st_size,
            "mtime": dt.datetime.fromtimestamp(source.stat().st_mtime).isoformat(),
            "action": "moved" if apply else "dry_run",
        }
        manifest_rows.append(row)
        if apply:
            shutil.move(str(source), str(destination))

    if apply:
        with manifest_path.open("a", encoding="utf-8", newline="\n") as handle:
            for row in manifest_rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Move files into the local archive. Omit for dry-run.",
    )
    args = parser.parse_args()

    root = repo_root()
    candidates = collect_candidates(root)
    manifest_path = archive_candidates(root, candidates, args.apply)

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"mode: {mode}")
    print(f"repo_root: {root}")
    print(f"candidate_count: {len(candidates)}")
    for path in candidates:
        print(path.relative_to(root).as_posix())
    print(f"manifest: {manifest_path.relative_to(root).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
