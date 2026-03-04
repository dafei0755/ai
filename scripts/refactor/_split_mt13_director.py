"""
MT-13: dynamic_project_director.py 拆分脚本

结构:
  L1-~362 : models — format_for_log, TaskDetail, RoleObject, RoleSelection
  L~363-~1524: DynamicProjectDirector class
  L~1525-end:  ChallengeDetector class + helpers

目标:
  _director_models.py    - models 区块
  _challenge_detector.py - ChallengeDetector + helpers
  dynamic_project_director.py - 仅保留 DynamicProjectDirector + 必要 imports
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SRC  = ROOT / "intelligent_project_analyzer" / "agents" / "dynamic_project_director.py"
DST  = SRC.parent

orig_text = SRC.read_text(encoding="utf-8")
lines = orig_text.splitlines(keepends=True)
total = len(lines)
print(f"原文件行数: {total}")

# ─── 找关键行号 (0-based) ───
def find_class_start(name: str) -> int:
    for i, ln in enumerate(lines):
        if re.match(rf'^class {name}\b', ln):
            return i
    raise ValueError(f"class {name} not found")

def find_top_func(name: str) -> int:
    for i, ln in enumerate(lines):
        if re.match(rf'^(?:async )?def {name}\b', ln):
            return i
    return -1

dir_start  = find_class_start("DynamicProjectDirector")
chal_start = find_class_start("ChallengeDetector")

print(f"DynamicProjectDirector: 行 {dir_start+1}")
print(f"ChallengeDetector:      行 {chal_start+1}")

# ─── 分区 ───
# header_lines: 原始 imports（直到 DynamicProjectDirector class 前）
header_lines   = lines[:dir_start]
director_lines = lines[dir_start:chal_start]
detector_lines = lines[chal_start:]

# ─── _director_models.py ───
# model_lines = header (containing imports) + content before DynamicProjectDirector
# This already IS the models file (format_for_log + 3 classes)
models_content = "".join(header_lines)
(DST / "_director_models.py").write_text(models_content, encoding="utf-8")
ml = len(models_content.splitlines())
print(f"✅ _director_models.py: {ml} 行")

# ─── _challenge_detector.py ───
# 从 header_lines 中截取 "纯 import 区"：从开头到第一个 def/class 前（连续的）
pure_import_end = 0
for i, ln in enumerate(header_lines):
    stripped = ln.lstrip()
    if stripped.startswith(("def ", "class ", "async def ")):
        pure_import_end = i
        break
else:
    pure_import_end = len(header_lines)

pure_imports = "".join(header_lines[:pure_import_end])

det_local = (
    "from ._director_models import (\n"
    "    format_for_log, TaskDetail, RoleObject, RoleSelection\n"
    ")\n\n"
)
det_content = pure_imports + det_local + "".join(detector_lines)
(DST / "_challenge_detector.py").write_text(det_content, encoding="utf-8")
dl = len(det_content.splitlines())
print(f"✅ _challenge_detector.py: {dl} 行")

# ─── dynamic_project_director.py (仅 DynamicProjectDirector) ───
# 使用纯 import 区（不含 models 代码），然后加子模块 imports，再加主 class
sub_imports = (
    "\nfrom ._director_models import (\n"
    "    format_for_log, TaskDetail, RoleObject, RoleSelection\n"
    ")  # noqa: F401\n"
    "from ._challenge_detector import (\n"
    "    ChallengeDetector, detect_and_handle_challenges_node\n"
    ")  # noqa: F401\n\n"
)
new_main = pure_imports + sub_imports + "".join(director_lines)
SRC.write_text(new_main, encoding="utf-8")
nl = len(new_main.splitlines())
print(f"✅ dynamic_project_director.py: {total} → {nl} 行 (减少 {total - nl} 行)")

# ─── 语法验证 ───
errors = 0
for p in [DST / "_director_models.py", DST / "_challenge_detector.py", SRC]:
    try:
        ast.parse(p.read_text(encoding="utf-8"))
        print(f"  OK  {p.name}")
    except SyntaxError as e:
        print(f"  FAIL {p.name}: {e}")
        errors += 1

print(f"\n{'⚠️ 有语法错误' if errors else '✅ 所有文件语法正确'}")
import sys; sys.exit(errors)
