#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
server.py クリーンアップスクリプト
- 已迁移至 deps.py 的代码从 server.py 中删除
- 添加 from .deps import ... 导入
使用 ast 解析定位函数/类边界，不依赖 emoji 字符。
"""
import ast
import shutil
import sys
from pathlib import Path

SERVER_PATH = Path(__file__).parent / "intelligent_project_analyzer/api/server.py"
BACKUP_PATH = SERVER_PATH.with_suffix(".py.bak_deps")

# 读取
content = SERVER_PATH.read_text(encoding="utf-8-sig")  # utf-8-sig handles BOM
# 去除 coding cookie 行以避免 ast.parse 报错（parse 不需要 coding 声明）
parse_content = content
if parse_content.startswith("# -*- coding"):
    parse_content = parse_content[parse_content.index("\n") + 1 :]
lines = content.splitlines(keepends=True)
original_lines = len(lines)
print(f"[start] server.py: {original_lines} lines")

# ── 备份 ──────────────────────────────────────────────────────────────────
shutil.copy2(SERVER_PATH, BACKUP_PATH)
print(f"备份: {BACKUP_PATH.name}")

# ══════════════════════════════════════════════════════════════════════════
# 辅助：用 ast 找到顶层节点的行范围
# ══════════════════════════════════════════════════════════════════════════
tree = ast.parse(parse_content)


def find_toplevel_ranges(names):
    """返回 {name: (lineno_start_0based, lineno_end_exclusive_0based)}"""
    result = {}
    nodes = [
        n
        for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Assign)) and n.col_offset == 0
    ]
    for node in nodes:
        name = None
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            name = node.name
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id in names:
                    name = t.id
                    break
        if name and name in names:
            result[name] = (node.lineno - 1, node.end_lineno)  # 0-based start, 1-based end → exclusive
    return result


targets = {
    "sync_checkpoint_to_redis",
    "TTLCache",
    "sessions_cache",
    "DEV_MODE",
    "get_current_user",
    "get_user_identifier",
    "optional_auth",
    "get_current_user_optional",
    "_serialize_for_json",
}
ranges = find_toplevel_ranges(targets)
print(f"[AST] 找到 {len(ranges)} 个目标: {sorted(ranges.keys())}")

# 特殊处理：jwt_service = WordPressJWTService() 是个 ast.Assign
# 也要找到它 + 前面的注释行
jwt_assign = None
for node in ast.walk(tree):
    if isinstance(node, ast.Assign) and node.col_offset == 0:
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "jwt_service":
                jwt_assign = (node.lineno - 1, node.end_lineno)

if jwt_assign:
    ranges["jwt_service"] = jwt_assign
    print(f"[AST] jwt_service: lines {jwt_assign[0]+1}–{jwt_assign[1]}")

# 按起始行逆序排列，从后向前删除（不扰乱行号）
items_to_remove = sorted(ranges.items(), key=lambda x: x[1][0], reverse=True)


# 额外：删除每个块前的"纯注释行"（紧邻块上方的 # 注释）
def expand_preceding_comments(start_0: int, lines: list) -> int:
    """向上扩展，包含连续的空行和注释行"""
    i = start_0 - 1
    while i >= 0:
        stripped = lines[i].strip()
        if stripped == "" or stripped.startswith("#"):
            i -= 1
        else:
            break
    return i + 1  # 返回新的 start_0


new_lines = lines[:]
for name, (s, e) in items_to_remove:
    expanded_s = expand_preceding_comments(s, new_lines)
    print(f"  删除 {name}: 原行 {s+1}–{e}，扩展后 {expanded_s+1}–{e}")
    del new_lines[expanded_s:e]

content = "".join(new_lines)

# ══════════════════════════════════════════════════════════════════════════
# 添加 from .deps import ... 在 MainWorkflow import 之后
# ══════════════════════════════════════════════════════════════════════════
DEPS_IMPORT = (
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

ANCHOR = "from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow\n"
idx = content.find(ANCHOR)
if idx == -1:
    print("[WARN] anchor for deps import not found!")
else:
    content = content[: idx + len(ANCHOR)] + DEPS_IMPORT + content[idx + len(ANCHOR) :]
    print("[OK] added 'from .deps import ...'")


# ══════════════════════════════════════════════════════════════════════════
# 验证语法
# ══════════════════════════════════════════════════════════════════════════
def check_syntax(src: str, path: str) -> bool:
    try:
        compile(src, path, "exec")
        return True
    except SyntaxError as e:
        print(f"[SYNTAX ERROR] {e}")
        return False


final_lines = len(content.splitlines())
if check_syntax(content, str(SERVER_PATH)):
    SERVER_PATH.write_text(content, encoding="utf-8")
    print(f"\n[SUCCESS] server.py: {original_lines} → {final_lines} lines ({final_lines - original_lines:+d})")
    print(f"备份保留在: {BACKUP_PATH.name}")
else:
    print("[ABORTED] 语法错误，未写入文件")
    print(f"请对比备份: {BACKUP_PATH.name}")
    sys.exit(1)
