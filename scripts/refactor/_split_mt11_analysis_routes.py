"""
MT-11: analysis_routes.py 拆分脚本 (2200行 → 3个子路由文件 + 薄聚合器)

拆分方案:
  _start_routes.py      - L96-L604   start, start-with-files, visual-reference
  _lifecycle_routes.py  - L605-L1294 status, resume, followup
  _report_routes.py     - L1295-L2199 result, report, pdf-download, event-replay
  analysis_routes.py    - 仅保留 imports + 聚合 include_router (~50行)

用法:
    python scripts/refactor/_split_mt11_analysis_routes.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ──────────────── 路径 ────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "intelligent_project_analyzer" / "api" / "analysis_routes.py"
DST_DIR = ROOT / "intelligent_project_analyzer" / "api"

assert SRC.exists(), f"源文件不存在: {SRC}"

lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
total = len(lines)
print(f"原文件行数: {total}")

# ──────────────── 行范围 (1-based → 0-based slice) ────────────────
HEADER_END    = 95   # imports + _get_session_manager + router
START_END     = 604  # start + start-with-files + visual-reference
LIFECYCLE_END = 1294 # status + resume + followup
# report block: 1295~total

header_lines    = lines[0:HEADER_END]         # [0, 94]
start_lines     = lines[HEADER_END:START_END]  # [95, 603]
lifecycle_lines = lines[START_END:LIFECYCLE_END]  # [604, 1293]
report_lines    = lines[LIFECYCLE_END:]           # [1294, ...]

# ──────────────── 共享 imports header ────────────────
SHARED_HEADER = "".join(header_lines)

# ──────────────── 子文件 router 声明（替换原 analysis_routes 中的那行）────────────────
SUBFILE_ROUTER_DECL = 'router = APIRouter(tags=["analysis"])\n'
# 原 header 中已有 router = APIRouter(...), 子文件直接复用

# ──────────────── 写出三个子文件 ────────────────
def write_sub_file(path: Path, body_lines: list[str]) -> int:
    content = SHARED_HEADER + "".join(body_lines)
    path.write_text(content, encoding="utf-8")
    lc = len(content.splitlines())
    print(f"  ✅ 写出 {path.name} ({lc} 行)")
    return lc


write_sub_file(DST_DIR / "_start_routes.py",     start_lines)
write_sub_file(DST_DIR / "_lifecycle_routes.py", lifecycle_lines)
write_sub_file(DST_DIR / "_report_routes.py",    report_lines)

# ──────────────── 写出新的 analysis_routes.py（薄聚合器）────────────────
AGGREGATOR = '''\
"""
分析路由模块 - 聚合器 (MT-11 拆分后)

子路由文件:
  _start_routes.py      POST /api/analysis/start
                        POST /api/analysis/start-with-files
                        POST /api/analysis/{id}/visual-reference/describe
  _lifecycle_routes.py  GET  /api/analysis/status/{session_id}
                        POST /api/analysis/resume
                        POST /api/analysis/followup
  _report_routes.py     GET  /api/analysis/result/{session_id}
                        GET  /api/analysis/report/{session_id}
                        GET  /api/analysis/report/{session_id}/download-pdf
                        GET  /api/analysis/report/{session_id}/download-all-experts-pdf
"""
from __future__ import annotations

from fastapi import APIRouter

from ._start_routes import router as _router_start
from ._lifecycle_routes import router as _router_lifecycle
from ._report_routes import router as _router_report

router = APIRouter(tags=["analysis"])
router.include_router(_router_start)
router.include_router(_router_lifecycle)
router.include_router(_router_report)
'''

agg_path = DST_DIR / "analysis_routes.py"
agg_path.write_text(AGGREGATOR, encoding="utf-8")
print(f"  ✅ 更新 analysis_routes.py → 薄聚合器 ({len(AGGREGATOR.splitlines())} 行)")

# ──────────────── 语法验证 ────────────────
import ast

errors = 0
for name in ["_start_routes.py", "_lifecycle_routes.py", "_report_routes.py", "analysis_routes.py"]:
    p = DST_DIR / name
    try:
        ast.parse(p.read_text(encoding="utf-8"))
        print(f"  OK  syntax: {name}")
    except SyntaxError as e:
        print(f"  FAIL syntax: {name}: {e}")
        errors += 1

print(f"\n完成！{'⚠️ 有语法错误，请检查' if errors else '✅ 所有文件语法正确'}")
print(f"原文件 {total} 行 → 拆分为 4 个文件")
sys.exit(errors)
