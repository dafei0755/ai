"""
MT-17: project_type_detector.py 拆分脚本 (1741行)

结构:
  L1-1457  : 注册表数据+工具函数 (_load_extension_registry + helpers)
  L1458-end: ProjectTypeDetector class

拆分方案:
  _type_registry.py        - 注册表函数+工具函数
  project_type_detector.py - 仅保留 ProjectTypeDetector class + imports

用法:
    python scripts/refactor/_split_mt17_type_detector.py
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SRC  = ROOT / "intelligent_project_analyzer" / "services" / "project_type_detector.py"
DST  = SRC.parent

lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
total = len(lines)
print(f"原文件行数: {total}")


def find_class_start(name):
    for i, ln in enumerate(lines):
        if re.match(rf'^class {name}\b', ln):
            return i
    raise ValueError(f"class {name} not found")


detector_start = find_class_start("ProjectTypeDetector")
print(f"ProjectTypeDetector: 行 {detector_start+1}")

# ─── imports 区（最初的 import/from 语句区块）───
# 找第一个 def 之前的区域
first_def = next(i for i, ln in enumerate(lines) if re.match(r'^def |^async def |^class ', ln))
raw_imports = "".join(lines[:first_def])

# ─── _type_registry.py: imports + L(first_def)..L(detector_start-1) ───
registry_content = raw_imports + "".join(lines[first_def:detector_start])
(DST / "_type_registry.py").write_text(registry_content, encoding="utf-8")
print(f"✅ _type_registry.py: {len(registry_content.splitlines())} 行")

# ─── project_type_detector.py: imports + sub-import + ProjectTypeDetector ───
# 确定要从 _type_registry 导入的顶级名称
# 扫描 first_def ~ detector_start 之间的顶级 def / 变量
exported_names = []
for ln in lines[first_def:detector_start]:
    m = re.match(r'^(def |async def )(\w+)', ln)
    if m:
        exported_names.append(m.group(2))
    # top-level assignments (e.g. REGISTRY = ...)
    m2 = re.match(r'^([A-Z_][A-Z0-9_]+)\s*=', ln)
    if m2:
        exported_names.append(m2.group(1))

if not exported_names:
    exported_names = ["_load_extension_registry"]

print(f"  导出名称: {exported_names[:8]}{'...' if len(exported_names)>8 else ''}")

sub_import_block = (
    "from ._type_registry import (\n"
    + "".join(f"    {n},\n" for n in exported_names)
    + ")  # noqa: F401\n\n"
)

new_main = raw_imports + sub_import_block + "".join(lines[detector_start:])
SRC.write_text(new_main, encoding="utf-8")
nl = len(new_main.splitlines())
print(f"✅ project_type_detector.py: {total} → {nl} 行 (−{total - nl}行)")

# ─── 语法验证 ───
errors = 0
for p in [DST / "_type_registry.py", SRC]:
    try:
        ast.parse(p.read_text(encoding="utf-8"))
        print(f"  OK  {p.name}")
    except SyntaxError as e:
        print(f"  FAIL {p.name}: {e}")
        errors += 1

print(f"\n{'⚠️ 有语法错误' if errors else '✅ 所有文件语法正确'}")
import sys; sys.exit(errors)
