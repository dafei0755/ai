#!/usr/bin/env python3
# coding: utf-8
import re, shutil, sys
from pathlib import Path

SERVER_PATH = Path(__file__).parent / "intelligent_project_analyzer/api/server.py"
BACKUP_PATH = SERVER_PATH.with_suffix(".py.bak_deps2")

content = SERVER_PATH.read_text(encoding="utf-8-sig")
original_lines = len(content.splitlines())
print(f"[start] server.py: {original_lines} lines")
shutil.copy2(SERVER_PATH, BACKUP_PATH)


def find_block(src, name):
    lines_list = src.splitlines(keepends=True)
    header = re.compile(
        r"^(async\s+def\s+"
        + re.escape(name)
        + r"\b|def\s+"
        + re.escape(name)
        + r"\b|class\s+"
        + re.escape(name)
        + r"\b|"
        + re.escape(name)
        + r"\s*=)"
    )
    start = None
    for i, ln in enumerate(lines_list):
        if header.match(ln):
            start = i
            break
    if start is None:
        return None

    # Track paren/bracket/brace depth to handle multi-line expressions
    depth = 0
    for i in range(start, len(lines_list)):
        for ch in lines_list[i]:
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                depth -= 1
        if i > start and depth <= 0:
            end = i + 1  # inclusive end
            break
    else:
        # function body: find next toplevel item
        end = len(lines_list)

    # For func/class: end is determined by next col-0 non-blank non-comment line
    # but for simple assignments (no depth=0 mid-body), the loop above handles it
    # For def/class, the depth tracking won't find end; use indentation approach
    if (
        lines_list[start].startswith("def ")
        or lines_list[start].startswith("async def ")
        or lines_list[start].startswith("class ")
    ):
        depth = 0
        end_func = len(lines_list)
        for i in range(start + 1, len(lines_list)):
            ln = lines_list[i]
            if ln.strip() and not ln[0].isspace() and not ln.startswith("#"):
                end_func = i
                break
        end = end_func

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
    removed_lines = "".join(ll[es:e]).strip()[:80]
    ll = ll[:es] + ll[e:]
    content = "".join(ll)
    print(f"[OK] removed {name}: rows {es+1}-{e} | preview: {removed_lines!r}")

ANCHOR = "from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow\n"
DEPS = (
    "from .deps import (\n    _parse_aspect_ratio,\n    sessions_cache,\n"
    "    DEV_MODE,\n    jwt_service,\n    get_current_user,\n"
    "    get_user_identifier,\n    optional_auth,\n"
    "    get_current_user_optional,\n    sync_checkpoint_to_redis,\n"
    "    _serialize_for_json,\n)\n"
)
idx = content.find(ANCHOR)
if idx != -1:
    content = content[: idx + len(ANCHOR)] + DEPS + content[idx + len(ANCHOR) :]
    print("[OK] added deps import")
else:
    print("[WARN] anchor not found")

try:
    compile(content, str(SERVER_PATH), "exec")
    print("[OK] syntax check passed")
except SyntaxError as ex:
    print(f"[SYNTAX ERROR] {ex}")
    # Show context
    lines_ctx = content.splitlines()
    err_line = ex.lineno or 0
    for i in range(max(0, err_line - 3), min(len(lines_ctx), err_line + 3)):
        print(f"  {i+1:4d}: {lines_ctx[i]}")
    sys.exit(1)

final_lines = len(content.splitlines())
SERVER_PATH.write_text(content, encoding="utf-8")
print(f"\n[SUCCESS] {original_lines} -> {final_lines} lines ({final_lines - original_lines:+d})")
