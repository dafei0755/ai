"""
MT-12: result_aggregator.py 拆分脚本 (2302行 → 3个 Mixin + 精简主文件)

拆分方案:
  _aggregator_format_mixin.py      - 格式化/兜底报告方法 (约L724-L1230)
  _aggregator_extraction_mixin.py  - 提取各类数据方法   (约L1231-L2085)
  _aggregator_deliverable_mixin.py - 交付物答案方法     (约L2085-end)
  result_aggregator.py             - 保留 core执行逻辑 + 3个 Mixin 继承

用法:
    python scripts/refactor/_split_mt12_result_aggregator.py
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SRC = ROOT / "intelligent_project_analyzer" / "report" / "result_aggregator.py"
DST_DIR = SRC.parent

assert SRC.exists(), f"源文件不存在: {SRC}"

text = SRC.read_text(encoding="utf-8")
lines = text.splitlines(keepends=True)
total = len(lines)
print(f"原文件行数: {total}")


# ──────────────── 精确定位方法边界 ────────────────
def find_method_extent(lines: list[str], start_name: str) -> tuple[int, int]:
    """返回 (start_0idx, end_exclusive_0idx)，含所有内部行直到下一个同级方法"""
    start_idx = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith(("async def " + start_name + "(", "def " + start_name + "(")):
            indent = len(line) - len(stripped)
            if indent == 4:  # 类成员方法（缩进4）
                start_idx = i
                break
    if start_idx is None:
        raise ValueError(f"找不到方法: {start_name}")
    # 找下一个同级（缩进4）方法或类定义
    for j in range(start_idx + 1, len(lines)):
        line = lines[j]
        stripped = line.lstrip()
        if stripped == "" or stripped.startswith("#"):
            continue
        indent = len(line) - len(stripped)
        if indent <= 4 and stripped.startswith(("def ", "async def ", "class ")):
            return start_idx, j
    return start_idx, len(lines)


# ──────────────── 定义三个 Mixin 的方法集 ────────────────
FORMAT_METHODS = [
    "_update_progress",
    "_format_agent_results",
    "_format_task_oriented_output",
    "_format_legacy_output",
    "_parse_final_report",
    "_create_fallback_report",
]

EXTRACTION_METHODS = [
    "_has_placeholder_content",
    "_extract_expert_reports",
    "_manually_populate_sections",
    "_extract_challenge_resolutions",
    "_calculate_overall_confidence",
    "_get_expert_distribution",
    "_estimate_report_pages",
    "_extract_review_feedback",
    "_extract_questionnaire_data",
    "_stringify_answer",
    "_extract_visualization_data",
    "_format_key_improvements",
    "_analyze_questionnaire_insights",
    "_extract_generated_images_by_expert",
]

DELIVERABLE_METHODS = [
    "_extract_deliverable_answers",
    "_find_owner_result",
    "_extract_owner_deliverable_output",
    "_clean_nested_json_content",
    "_format_dict_as_readable",
    "_extract_quality_score",
    "_generate_answer_summary",
    "_generate_combined_summary",
    "_extract_supporter_contribution",
    "_consolidate_search_references",
]


def collect_methods(lines: list[str], method_names: list[str]) -> tuple[list[tuple[int, int]], set[int]]:
    """收集所有方法的行范围，返回 (ranges, line_indices_set)"""
    ranges = []
    all_indices: set[int] = set()
    for name in method_names:
        try:
            s, e = find_method_extent(lines, name)
            ranges.append((s, e))
            all_indices.update(range(s, e))
            print(f"  方法 {name}: 行 {s+1}-{e} ({e-s} 行)")
        except ValueError as err:
            print(f"  ⚠️  {err}")
    return ranges, all_indices


print("\n=== FORMAT MIXIN ===")
fmt_ranges, fmt_indices = collect_methods(lines, FORMAT_METHODS)
print("\n=== EXTRACTION MIXIN ===")
ext_ranges, ext_indices = collect_methods(lines, EXTRACTION_METHODS)
print("\n=== DELIVERABLE MIXIN ===")
dlv_ranges, dlv_indices = collect_methods(lines, DELIVERABLE_METHODS)


# ──────────────── 原文件 imports 区 ────────────────
# 取 L1~L55 作为共享 imports（去掉 class 定义）
header_end = next(i for i, l in enumerate(lines) if l.startswith("class ResultAggregatorAgent"))
raw_imports = "".join(lines[:header_end])


# ──────────────── 生成 Mixin 文件 ────────────────
MIXIN_HEADER_TMPL = '''\
"""
{title}
由 scripts/refactor/_split_mt12_result_aggregator.py 自动生成 (MT-12)
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from ..workflow.state import ProjectAnalysisState


class {classname}:
    """Mixin — {title}"""
'''


def extract_method_text(lines: list[str], ranges: list[tuple[int, int]]) -> str:
    """按行范围提取方法体，去掉首尾多余空行"""
    parts = []
    for s, e in ranges:
        block = "".join(lines[s:e])
        parts.append(block)
    return "\n".join(parts)


def write_mixin(path: Path, title: str, classname: str, method_ranges: list[tuple[int, int]]) -> int:
    body = extract_method_text(lines, method_ranges)
    content = MIXIN_HEADER_TMPL.format(title=title, classname=classname) + body
    path.write_text(content, encoding="utf-8")
    lc = len(content.splitlines())
    print(f"  ✅ 写出 {path.name} ({lc} 行)")
    return lc


print("\n=== 写出 Mixin 文件 ===")
write_mixin(
    DST_DIR / "_aggregator_format_mixin.py",
    "ResultAggregator 格式化 & 兜底报告 Mixin",
    "AggregatorFormatMixin",
    fmt_ranges,
)
write_mixin(
    DST_DIR / "_aggregator_extraction_mixin.py",
    "ResultAggregator 数据提取 Mixin",
    "AggregatorExtractionMixin",
    ext_ranges,
)
write_mixin(
    DST_DIR / "_aggregator_deliverable_mixin.py",
    "ResultAggregator 交付物答案 Mixin",
    "AggregatorDeliverableMixin",
    dlv_ranges,
)


# ──────────────── 修改主文件：删除已迁移方法 + 修改继承 ────────────────
all_moved: set[int] = fmt_indices | ext_indices | dlv_indices
new_lines: list[str] = []
i = 0
while i < len(lines):
    if i in all_moved:
        i += 1
        continue
    new_lines.append(lines[i])
    i += 1

new_text = "".join(new_lines)

# 修改 class 定义行：加入 Mixin 继承
new_text = new_text.replace(
    "class ResultAggregatorAgent(LLMAgent):",
    "class ResultAggregatorAgent(AggregatorFormatMixin, AggregatorExtractionMixin, AggregatorDeliverableMixin, LLMAgent):",
)

# 在 from ._result_models import 前插入 Mixin imports
mixin_imports = (
    "from ._aggregator_format_mixin import AggregatorFormatMixin\n"
    "from ._aggregator_extraction_mixin import AggregatorExtractionMixin\n"
    "from ._aggregator_deliverable_mixin import AggregatorDeliverableMixin\n"
)
# 找合适插入点：from . import 或其他本地 import
insert_marker = "from ._result_models import"
new_text = new_text.replace(insert_marker, mixin_imports + insert_marker, 1)

SRC.write_text(new_text, encoding="utf-8")
new_lc = len(new_text.splitlines())
print(f"\n  ✅ 更新 result_aggregator.py: {total} → {new_lc} 行 (减少 {total - new_lc} 行)")


# ──────────────── 语法验证 ────────────────
print("\n=== 语法验证 ===")
errors = 0
for p in [
    DST_DIR / "_aggregator_format_mixin.py",
    DST_DIR / "_aggregator_extraction_mixin.py",
    DST_DIR / "_aggregator_deliverable_mixin.py",
    SRC,
]:
    try:
        ast.parse(p.read_text(encoding="utf-8"))
        print(f"  OK  {p.name}")
    except SyntaxError as e:
        print(f"  FAIL  {p.name}: {e}")
        errors += 1

print(f"\n{'⚠️ 有语法错误' if errors else '✅ 所有文件语法正确'}")
import sys; sys.exit(errors)
