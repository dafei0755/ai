#!/usr/bin/env python3
# coding: utf-8
import re, shutil, sys
from pathlib import Path

SERVER_PATH = Path(__file__).parent / "intelligent_project_analyzer/api/server.py"
BACKUP_PATH = SERVER_PATH.with_suffix(".py.bak_deps3")

content = SERVER_PATH.read_text(encoding="utf-8-sig")
original_lines = len(content.splitlines())
print(f"[start] server.py: {original_lines} lines")
shutil.copy2(SERVER_PATH, BACKUP_PATH)


def find_block(src, name):
    lines_list = src.splitlines(keepends=True)
    header = re.compile(
        r"^(async\s+def\s+" + re.escape(name) + r"\b"
        r"|def\s+" + re.escape(name) + r"\b"
        r"|class\s+" + re.escape(name) + r"\b"
        r"|" + re.escape(name) + r"\s*=)"
    )
    start = None
    for i, ln in enumerate(lines_list):
        if header.match(ln):
            start = i
            break
    if start is None:
        return None

    is_def_or_class = (
        lines_list[start].startswith("def ")
        or lines_list[start].startswith("async def ")
        or lines_list[start].startswith("class ")
    )

    if is_def_or_class:
        end = len(lines_list)
        for i in range(start + 1, len(lines_list)):
            ln = lines_list[i]
            if ln.strip() and not ln[0].isspace() and not ln.startswith("#"):
                end = i
                break
        return (start, end)
    else:
        # Assignment: track paren depth; end when depth returns to 0
        depth = 0
        for i in range(start, len(lines_list)):
            for ch in lines_list[i]:
                if ch in "([{":
                    depth += 1
                elif ch in ")]}":
                    depth -= 1
            if depth <= 0:
                end = i + 1
                break
        else:
            end = len(lines_list)
        return (start, end)


def expand_up(lines_list, start):
    i = start - 1
    while i >= 0 and (lines_list[i].strip() == "" or lines_list[i].strip().startswith("#")):
        i -= 1
    return i + 1


targets = [
    "_serialize_for_json",
    "get_current_user_optional",
    "optional_auth",
    "get_user_identifier",
    "get_current_user",
    "DEV_MODE",
    "sessions_cache",
    "TTLCache",
    "sync_checkpoint_to_redis",
    "jwt_service",
]
for name in targets:
    r = find_block(content, name)
    if r is None:
        print(f"[SKIP] {name}: not found")
        continue
    s, e = r
    ll = content.splitlines(keepends=True)
    es = expand_up(ll, s)
    preview = "".join(ll[es:e]).strip()[:80]
    ll = ll[:es] + ll[e:]
    content = "".join(ll)
    print(f"[OK] removed {name}: rows {es+1}-{e} | {preview!r}")

ANCHOR = "from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow\n"
DEPS = (
    "from .deps import (\n"
    "    _parse_aspect_ratio,\n"
    "    sessions_cache,\n"
    "    DEV_MODE,\n"
    "    jwt_service,\n"
    "    get_current_user,\n"
    "    get_user_identifier,\n"
    "    optional_auth,\n"
    "    get_current_user_optional,\n"
    "    sync_checkpoint_to_redis,\n"
    "    _serialize_for_json,\n"
    ")\n"
)
idx = content.find(ANCHOR)
if idx != -1:
    content = content[: idx + len(ANCHOR)] + DEPS + content[idx + len(ANCHOR) :]
    print("[OK] added deps import")

try:
    compile(content, str(SERVER_PATH), "exec")
    print("[OK] syntax check passed")
except SyntaxError as ex:
    print(f"[SYNTAX ERROR] {ex}")
    lines_ctx = content.splitlines()
    err_line = ex.lineno or 0
    for i in range(max(0, err_line - 3), min(len(lines_ctx), err_line + 3)):
        print(f"  {i+1:4d}: {lines_ctx[i]}")
    sys.exit(1)

final_lines = len(content.splitlines())
SERVER_PATH.write_text(content, encoding="utf-8")
print(f"\n[SUCCESS] {original_lines} -> {final_lines} lines ({final_lines - original_lines:+d})")
