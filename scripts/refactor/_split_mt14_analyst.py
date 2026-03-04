"""
MT-14: requirements_analyst.py 拆分脚本 (1857行 → 3 Mixin + 精简主文件)

拆分方案:
  _analyst_parse_mixin.py  - 解析/结构化方法  L225-L708
  _analyst_phase_mixin.py  - 两阶段执行方法   L709-L1494
  _analyst_fix_mixin.py    - 修复/补全方法    L1495-end
  requirements_analyst.py  - 保留 core + 继承 3 Mixin (~225行)

用法:
    python scripts/refactor/_split_mt14_analyst.py
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SRC  = ROOT / "intelligent_project_analyzer" / "agents" / "requirements_analyst.py"
DST  = SRC.parent

lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
total = len(lines)
print(f"原文件行数: {total}")


def find_method_extent(lines, name):
    """返回 (start_0idx, end_exclusive) 包括 async def"""
    for i, ln in enumerate(lines):
        stripped = ln.lstrip()
        if stripped.startswith((f"async def {name}(", f"def {name}(")):
            indent = len(ln) - len(stripped)
            if indent == 4:
                start = i
                break
    else:
        raise ValueError(f"方法未找到: {name}")
    for j in range(start + 1, len(lines)):
        ln = lines[j]
        s  = ln.lstrip()
        if s == "" or s.startswith("#"):
            continue
        if len(ln) - len(s) <= 4 and s.startswith(("def ", "async def ", "class ")):
            return start, j
    return start, len(lines)


PARSE_METHODS = [
    "_parse_requirements",
    "_extract_balanced_json",
    "_create_fallback_structure",
    "_normalize_jtbd_fields",
    "_infer_project_type",
    "_calculate_confidence",
    "_retrieve_user_preferences",
    "_save_user_preferences",
]

PHASE_METHODS = [
    "_execute_two_phase",
    "_execute_precheck_async",
    "_execute_phase1_async",
    "_execute_phase1",
    "_execute_phase2",
    "_parse_phase_response",
    "_fallback_phase1",
    "_format_precheck_hints",
    "_build_visual_reference_context",
    "_fallback_phase2",
    "_build_phase1_only_result",
    "_merge_phase_results",
    "_extract_l2_extended_perspectives",
    "_calculate_two_phase_confidence",
]

FIX_METHODS = [
    "_fix_validation_issues",
    "_generate_missing_l6",
    "_generate_missing_l7",
]


def collect(names):
    ranges = []
    indices = set()
    for name in names:
        try:
            s, e = find_method_extent(lines, name)
            ranges.append((s, e))
            indices.update(range(s, e))
            print(f"  {name}: L{s+1}-{e} ({e-s}行)")
        except ValueError as ex:
            print(f"  ⚠️ {ex}")
    return ranges, indices


print("\n=== PARSE_MIXIN ===")
parse_r, parse_i = collect(PARSE_METHODS)
print("\n=== PHASE_MIXIN ===")
phase_r, phase_i = collect(PHASE_METHODS)
print("\n=== FIX_MIXIN ===")
fix_r, fix_i = collect(FIX_METHODS)


# ─── 原始 imports 区（直到 class RequirementsAnalystAgent）───
class_start = next(i for i, ln in enumerate(lines) if ln.startswith("class RequirementsAnalystAgent"))
pure_imports = "".join(lines[:class_start])

MIXIN_HDR = '''\
"""
{title}
由 scripts/refactor/_split_mt14_analyst.py 自动生成 (MT-14)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from langchain_core.runnables import RunnableConfig
    from langgraph.store.base import BaseStore
    from ..workflow.state import ProjectAnalysisState


class {cls}:
    """Mixin — {title}"""
'''


def write_mixin(fname, title, cls, ranges):
    body = "".join("".join(lines[s:e]) for s, e in ranges)
    content = MIXIN_HDR.format(title=title, cls=cls) + body
    (DST / fname).write_text(content, encoding="utf-8")
    lc = len(content.splitlines())
    print(f"✅ {fname}: {lc} 行")


print("\n=== 写出 Mixin 文件 ===")
write_mixin("_analyst_parse_mixin.py",  "需求分析师 解析/结构化 Mixin",  "AnalystParseMixin",  parse_r)
write_mixin("_analyst_phase_mixin.py",  "需求分析师 两阶段执行 Mixin",   "AnalystPhaseMixin",  phase_r)
write_mixin("_analyst_fix_mixin.py",    "需求分析师 修复/补全 Mixin",    "AnalystFixMixin",    fix_r)


# ─── 更新主文件：删除迁移的方法行 ───
all_moved = parse_i | phase_i | fix_i
new_lines = [ln for i, ln in enumerate(lines) if i not in all_moved]
new_text  = "".join(new_lines)

# 修改继承
new_text = new_text.replace(
    "class RequirementsAnalystAgent(LLMAgent):",
    "class RequirementsAnalystAgent(AnalystParseMixin, AnalystPhaseMixin, AnalystFixMixin, LLMAgent):",
)

# 插入 Mixin imports（在 from . 或本地 import 之前）
mixin_block = (
    "from ._analyst_parse_mixin import AnalystParseMixin\n"
    "from ._analyst_phase_mixin import AnalystPhaseMixin\n"
    "from ._analyst_fix_mixin import AnalystFixMixin\n"
)
# 找第一个 from .. 或 from . 本地导入
import_target = "from ..core."
new_text = new_text.replace(import_target, mixin_block + import_target, 1)

SRC.write_text(new_text, encoding="utf-8")
nl = len(new_text.splitlines())
print(f"✅ requirements_analyst.py: {total} → {nl} 行 (−{total - nl}行)")

# ─── 语法验证 ───
errors = 0
for p in [
    DST / "_analyst_parse_mixin.py",
    DST / "_analyst_phase_mixin.py",
    DST / "_analyst_fix_mixin.py",
    SRC,
]:
    try:
        ast.parse(p.read_text(encoding="utf-8"))
        print(f"  OK  {p.name}")
    except SyntaxError as e:
        print(f"  FAIL {p.name}: {e}")
        errors += 1

print(f"\n{'⚠️ 有语法错误' if errors else '✅ 所有文件语法正确'}")
import sys; sys.exit(errors)
