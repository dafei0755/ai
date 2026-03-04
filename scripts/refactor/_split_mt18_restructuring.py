"""
MT-18: requirements_restructuring.py 拆分脚本 (1739行 → 3 Mixin + 精简主文件)

拆分方案:
  _restructuring_synthesis_mixin.py - 综合/合成方法  L160-L609
  _restructuring_analysis_mixin.py  - 分析/提取方法  L610-L1395
  _restructuring_output_mixin.py    - 输出/摘要方法  L1356-end
  requirements_restructuring.py     - 保留 restructure + class 定义 (~200行)

用法:
    python scripts/refactor/_split_mt18_restructuring.py
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SRC  = ROOT / "intelligent_project_analyzer" / "interaction" / "nodes" / "requirements_restructuring.py"
DST  = SRC.parent

lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
total = len(lines)
print(f"原文件行数: {total}")


def find_method_extent(lines, name, cls_indent=4):
    """找方法完整范围，包含其前面的装饰器行"""
    def_idx = None
    for i, ln in enumerate(lines):
        s = ln.lstrip()
        if s.startswith((f"async def {name}(", f"def {name}(")):
            indent = len(ln) - len(s)
            if indent == cls_indent:
                def_idx = i
                break
    if def_idx is None:
        raise ValueError(f"方法未找到: {name}")

    # 向上追溯连续装饰器行
    start = def_idx
    for k in range(def_idx - 1, -1, -1):
        ln = lines[k]
        s = ln.lstrip()
        indent = len(ln) - len(s)
        if s == "" or s.startswith("#"):
            continue
        if indent == cls_indent and s.startswith("@"):
            start = k  # 包含装饰器
        else:
            break

    # 向下找下一个同级条目（def/class/装饰器/类级常量）
    for j in range(def_idx + 1, len(lines)):
        ln = lines[j]
        s  = ln.lstrip()
        if s == "":
            continue
        indent = len(ln) - len(s)
        if indent != cls_indent:
            continue
        if s.startswith(("def ", "async def ", "class ", "@")):
            return start, j
        if re.match(r'^[A-Z_][A-Z0-9_]*\s*[=:]', s):
            return start, j
    return start, len(lines)


SYNTHESIS_METHODS = [
    "_prepare_synthesis_context",
    "_build_synthesis_prompt",
    "_llm_synthesize_insight",
    "_validate_synthesis_result",
    "_format_synthesis_output",
    "_extract_insight_summary_from_context",
    "_rule_based_fallback",
]

ANALYSIS_METHODS = [
    "_rule_based_task_corrections",
    "_extract_objectives_with_jtbd",
    "_llm_enhance_goal",
    "_identify_constraints",
    "_build_priorities_with_insights",
    "_extract_key_requirements_for_dimension",
    "_extract_core_tension",
    "_llm_generate_tension_strategies",
    "_extract_special_requirements",
    "_identify_risks_with_tension",
]

OUTPUT_METHODS = [
    "_extract_insight_summary",
    "_generate_executive_summary",
    "_llm_generate_one_sentence",
    "_infer_flexibility",
    "_llm_comprehensive_analysis",
]


def collect(names):
    ranges, indices = [], set()
    for name in names:
        try:
            s, e = find_method_extent(lines, name)
            ranges.append((s, e))
            indices.update(range(s, e))
            print(f"  {name}: L{s+1}-{e} ({e-s}行)")
        except ValueError as ex:
            print(f"  ⚠️ {ex}")
    return ranges, indices


print("=== SYNTHESIS_MIXIN ===")
syn_r, syn_i = collect(SYNTHESIS_METHODS)
print("=== ANALYSIS_MIXIN ===")
ana_r, ana_i = collect(ANALYSIS_METHODS)
print("=== OUTPUT_MIXIN ===")
out_r, out_i = collect(OUTPUT_METHODS)

# ─── class 起始前的 imports ───
import re
class_start = next(i for i, ln in enumerate(lines) if re.match(r'^class RequirementsRestructuringEngine\b', ln))
raw_imports = "".join(lines[:class_start])

MIXIN_HDR = '''\
"""
{title}
由 scripts/refactor/_split_mt18_restructuring.py 自动生成 (MT-18)
"""
from __future__ import annotations

from typing import Any, Dict, List


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
write_mixin("_restructuring_synthesis_mixin.py", "需求重组 综合/合成 Mixin", "RestructuringSynthesisMixin", syn_r)
write_mixin("_restructuring_analysis_mixin.py",  "需求重组 分析/提取 Mixin",  "RestructuringAnalysisMixin",  ana_r)
write_mixin("_restructuring_output_mixin.py",    "需求重组 输出/摘要 Mixin",   "RestructuringOutputMixin",   out_r)

# ─── 更新主文件 ───
all_moved = syn_i | ana_i | out_i
new_lines = [ln for i, ln in enumerate(lines) if i not in all_moved]
new_text  = "".join(new_lines)

new_text = new_text.replace(
    "class RequirementsRestructuringEngine:",
    "class RequirementsRestructuringEngine(RestructuringSynthesisMixin, RestructuringAnalysisMixin, RestructuringOutputMixin):",
)

mixin_block = (
    "from ._restructuring_synthesis_mixin import RestructuringSynthesisMixin\n"
    "from ._restructuring_analysis_mixin import RestructuringAnalysisMixin\n"
    "from ._restructuring_output_mixin import RestructuringOutputMixin\n"
)
# 插入到第一个本地/相对 import 前
first_local = next(
    (ln for ln in new_text.splitlines(keepends=True) if ln.startswith("from .") or ln.startswith("from ..")),
    None
)
if first_local:
    new_text = new_text.replace(first_local, mixin_block + first_local, 1)
else:
    # 插入到 class 定义前
    new_text = new_text.replace(
        "from ._restructuring_synthesis_mixin",
        mixin_block + "from ._restructuring_synthesis_mixin",
        1,
    )

SRC.write_text(new_text, encoding="utf-8")
nl = len(new_text.splitlines())
print(f"✅ requirements_restructuring.py: {total} → {nl} 行 (−{total - nl}行)")

# ─── 语法验证 ───
errors = 0
for fname in [
    "_restructuring_synthesis_mixin.py",
    "_restructuring_analysis_mixin.py",
    "_restructuring_output_mixin.py",
    "requirements_restructuring.py",
]:
    p = DST / fname
    try:
        ast.parse(p.read_text(encoding="utf-8"))
        print(f"  OK  {fname}")
    except SyntaxError as e:
        print(f"  FAIL {fname}: {e}")
        errors += 1

print(f"\n{'⚠️ 有语法错误' if errors else '✅ 所有文件语法正确'}")
import sys; sys.exit(errors)
