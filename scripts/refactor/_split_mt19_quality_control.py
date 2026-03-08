"""
MT-19: quality_control.py 拆分脚本 (1661行 → 5个类文件 + 聚合器)

结构:
  L1  -L69  : imports + 3个懒加载函数
  L70 -L950 : SearchQualityControl + quick_quality_control
  L951-L1196: ContentDepthEvaluator
  L1197-L1312: EnhancedSearchQualityControl
  L1313-L1503: HumanDimensionEvaluator
  L1504-end : InsightAwareQualityControl

用法:
    python scripts/refactor/_split_mt19_quality_control.py
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SRC  = ROOT / "intelligent_project_analyzer" / "tools" / "quality_control.py"
DST  = SRC.parent

lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
total = len(lines)
print(f"原文件行数: {total}")


def find_class_start(name):
    for i, ln in enumerate(lines):
        if re.match(rf'^class {name}\b', ln):
            return i
    raise ValueError(f"class {name} not found")


sqc_start    = find_class_start("SearchQualityControl")
cde_start    = find_class_start("ContentDepthEvaluator")
esqc_start   = find_class_start("EnhancedSearchQualityControl")
hde_start    = find_class_start("HumanDimensionEvaluator")
iaqc_start   = find_class_start("InsightAwareQualityControl")

for name, idx in [
    ("SearchQualityControl", sqc_start),
    ("ContentDepthEvaluator", cde_start),
    ("EnhancedSearchQualityControl", esqc_start),
    ("HumanDimensionEvaluator", hde_start),
    ("InsightAwareQualityControl", iaqc_start),
]:
    print(f"  {name}: 行 {idx+1}")

raw_imports = "".join(lines[:sqc_start])


def write_class_file(fname, class_lines, extra_imports=""):
    content = raw_imports + extra_imports + "".join(class_lines)
    (DST / fname).write_text(content, encoding="utf-8")
    lc = len(content.splitlines())
    print(f"✅ {fname}: {lc} 行")


print("\n=== 写出类文件 ===")
write_class_file("_search_quality_control.py",    lines[sqc_start:cde_start])
write_class_file("_content_depth_evaluator.py",   lines[cde_start:esqc_start],
                 "from ._search_quality_control import SearchQualityControl\n\n")
write_class_file("_enhanced_quality_control.py",  lines[esqc_start:hde_start],
                 "from ._search_quality_control import SearchQualityControl\nfrom ._content_depth_evaluator import ContentDepthEvaluator\n\n")
write_class_file("_human_dimension_evaluator.py", lines[hde_start:iaqc_start])
write_class_file("_insight_quality_control.py",   lines[iaqc_start:],
                 "from ._enhanced_quality_control import EnhancedSearchQualityControl\nfrom ._human_dimension_evaluator import HumanDimensionEvaluator\n\n")

# ─── 薄聚合器 ───
AGGREGATOR = '''\
"""quality_control - 搜索质量控制模块聚合器 (MT-19 拆分后)"""
from ._search_quality_control import SearchQualityControl, quick_quality_control  # noqa: F401
from ._content_depth_evaluator import ContentDepthEvaluator  # noqa: F401
from ._enhanced_quality_control import EnhancedSearchQualityControl, enhanced_quality_control, evaluate_content_depth  # noqa: F401
from ._human_dimension_evaluator import HumanDimensionEvaluator  # noqa: F401
from ._insight_quality_control import InsightAwareQualityControl  # noqa: F401

__all__ = [
    "SearchQualityControl",
    "quick_quality_control",
    "ContentDepthEvaluator",
    "EnhancedSearchQualityControl",
    "enhanced_quality_control",
    "evaluate_content_depth",
    "HumanDimensionEvaluator",
    "InsightAwareQualityControl",
]
'''
SRC.write_text(AGGREGATOR, encoding="utf-8")
print(f"✅ quality_control.py: {total} → {len(AGGREGATOR.splitlines())} 行 (聚合器)")

# ─── 语法验证 ───
errors = 0
for fname in [
    "_search_quality_control.py",
    "_content_depth_evaluator.py",
    "_enhanced_quality_control.py",
    "_human_dimension_evaluator.py",
    "_insight_quality_control.py",
    "quality_control.py",
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
