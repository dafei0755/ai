"""
MT-21: output_intent_detection.py 拆分脚本 (1636行 → 3个函数模块 + 聚合器)

拆分方案:
  _oid_constraint.py     - 约束相关函数  L46-L452
  _oid_signal.py         - 信号检测函数  L453-L694
  _oid_scoring.py        - 评分/框架函数 L695-end
  output_intent_detection.py - imports + re-exports

用法:
    python scripts/refactor/_split_mt21_output_intent.py
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SRC  = ROOT / "intelligent_project_analyzer" / "interaction" / "nodes" / "output_intent_detection.py"
DST  = SRC.parent

lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
total = len(lines)
print(f"原文件行数: {total}")


def find_top_func_start(name):
    """找到模块级函数（indent=0）"""
    for i, ln in enumerate(lines):
        s = ln.lstrip()
        if s.startswith((f"async def {name}(", f"def {name}(")):
            if len(ln) - len(s) == 0:
                return i
    raise ValueError(f"函数未找到: {name}")


# 找关键边界
constraint_start = find_top_func_start("_extract_spatial_zones")
signal_start     = find_top_func_start("_load_config")
scoring_start    = find_top_func_start("_score_delivery_types")

print(f"  约束组起始: 行 {constraint_start+1}")
print(f"  信号组起始: 行 {signal_start+1}")
print(f"  评分组起始: 行 {scoring_start+1}")

# ─── imports（L1 ~ constraint_start-1）───
raw_imports = "".join(lines[:constraint_start])

# ─── 子模块内容 ───
constraint_content = raw_imports + "".join(lines[constraint_start:signal_start])
signal_content     = raw_imports + "".join(lines[signal_start:scoring_start])
scoring_content    = raw_imports + "".join(lines[scoring_start:])

(DST / "_oid_constraint.py").write_text(constraint_content, encoding="utf-8")
(DST / "_oid_signal.py").write_text(signal_content,     encoding="utf-8")
(DST / "_oid_scoring.py").write_text(scoring_content,   encoding="utf-8")

print(f"✅ _oid_constraint.py: {len(constraint_content.splitlines())} 行")
print(f"✅ _oid_signal.py: {len(signal_content.splitlines())} 行")
print(f"✅ _oid_scoring.py: {len(scoring_content.splitlines())} 行")

# ─── 扫描每组的导出名 ───
def collect_func_names(start, end):
    names = []
    for ln in lines[start:end]:
        m = re.match(r'^(?:async )?def (\w+)\(', ln)
        if m:
            names.append(m.group(1))
    return names


constraint_exports = collect_func_names(constraint_start, signal_start)
signal_exports     = collect_func_names(signal_start, scoring_start)
scoring_exports    = collect_func_names(scoring_start, len(lines))

print(f"  约束组导出: {constraint_exports}")
print(f"  信号组导出: {signal_exports}")
print(f"  评分组导出: {scoring_exports}")

# ─── 聚合器 ───
def fmt_imports(module, names):
    return (
        f"from .{module} import (\n"
        + "".join(f"    {n},\n" for n in names)
        + ")  # noqa: F401\n"
    )

agg = (
    '"""output_intent_detection - 输出意图检测模块聚合器 (MT-21 拆分后)"""\n'
    + fmt_imports("_oid_constraint", constraint_exports)
    + fmt_imports("_oid_signal",     signal_exports)
    + fmt_imports("_oid_scoring",    scoring_exports)
    + "\n__all__ = [\n"
    + "".join(f'    "{n}",\n' for n in constraint_exports + signal_exports + scoring_exports)
    + "]\n"
)
SRC.write_text(agg, encoding="utf-8")
print(f"✅ output_intent_detection.py: {total} → {len(agg.splitlines())} 行 (聚合器)")

# ─── 语法验证 ───
errors = 0
for fname in ["_oid_constraint.py", "_oid_signal.py", "_oid_scoring.py", "output_intent_detection.py"]:
    p = DST / fname
    try:
        ast.parse(p.read_text(encoding="utf-8"))
        print(f"  OK  {fname}")
    except SyntaxError as e:
        print(f"  FAIL {fname}: {e}")
        errors += 1

print(f"\n{'⚠️ 有语法错误' if errors else '✅ 所有文件语法正确'}")
import sys; sys.exit(errors)
