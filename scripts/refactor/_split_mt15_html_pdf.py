"""
MT-15: html_pdf_generator.py 拆分脚本 (1933行)

结构:
  L1 -L175 : PlaywrightBrowserPool class + get_browser_pool()
  L176-L741 : HTMLPDFGenerator.__init__ + heavy imports
  L742-L1096: text/translate helpers (HTMLPDFGenerator methods)
  L1097-L1647: parsing helpers (HTMLPDFGenerator methods)
  L1648-end : render_html, generate_pdf_*, generate_expert_report_pdf

拆分方案:
  _browser_pool.py       - PlaywrightBrowserPool + get_browser_pool (独立文件)
  _pdf_text_mixin.py     - 文本处理/翻译 Mixin   L758-L1096
  _pdf_parse_mixin.py    - 解析/格式化 Mixin     L1097-L1647
  html_pdf_generator.py  - 仅保留 __init__ + render/generate (~500行)

用法:
    python scripts/refactor/_split_mt15_html_pdf.py
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SRC  = ROOT / "intelligent_project_analyzer" / "api" / "html_pdf_generator.py"
DST  = SRC.parent

lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
total = len(lines)
print(f"原文件行数: {total}")


def find_class_start(name):
    for i, ln in enumerate(lines):
        if re.match(rf'^class {name}\b', ln):
            return i
    raise ValueError(f"class {name} not found")


def find_method_extent(lines, name, cls_indent=4):
    """类方法（缩进4）边界提取"""
    for i, ln in enumerate(lines):
        s = ln.lstrip()
        if s.startswith((f"async def {name}(", f"def {name}(")):
            indent = len(ln) - len(s)
            if indent == cls_indent:
                start = i
                break
    else:
        raise ValueError(f"方法未找到: {name}")
    for j in range(start + 1, len(lines)):
        ln = lines[j]
        s  = ln.lstrip()
        if s == "" or s.startswith("#"):
            continue
        if len(ln) - len(s) <= cls_indent and s.startswith(("def ", "async def ", "class ")):
            return start, j
    return start, len(lines)


# ─── 找关键位置 ───
browser_pool_start = find_class_start("PlaywrightBrowserPool")   # ~L27
html_gen_start     = find_class_start("HTMLPDFGenerator")         # ~L176

print(f"PlaywrightBrowserPool: 行 {browser_pool_start+1}")
print(f"HTMLPDFGenerator:      行 {html_gen_start+1}")

# ─── 原始 imports（浏览器池之前）───
browser_pool_imports = "".join(lines[:browser_pool_start])
# HTMLPDFGenerator 之前（包括 browser_pool，但该区块做到 _browser_pool.py 里）
html_gen_preamble = "".join(lines[html_gen_start - 1:html_gen_start])  # blank line before

# ─── TEXT_MIXIN 方法列表 ───
TEXT_METHODS = [
    "_nl2br",
    "_normalize_newlines",
    "_simple_markdown",
    "_translate_all_english",
    "_unify_list_format",
    "translate_label",
    "translate_content",
]

PARSE_METHODS = [
    "_try_parse_dict_string",
    "_clean_json_artifacts",
    "_clean_and_format_value",
    "_format_object_list",
    "_format_numbered_text",
    "format_numbered_list",
    "_parse_deliverable_outputs",
    "_format_single_deliverable",
    "parse_expert_content",
    "_parse_field",
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


print("\n=== TEXT_MIXIN ===")
text_r, text_i = collect(TEXT_METHODS)
print("\n=== PARSE_MIXIN ===")
parse_r, parse_i = collect(PARSE_METHODS)

# ─── 写出 _browser_pool.py ───
# 包含：原始 imports + PlaywrightBrowserPool class + get_browser_pool 函数
# PlaywrightBrowserPool: browser_pool_start → html_gen_start
pool_content = browser_pool_imports + "".join(lines[browser_pool_start:html_gen_start])
(DST / "_browser_pool.py").write_text(pool_content, encoding="utf-8")
print(f"\n✅ _browser_pool.py: {len(pool_content.splitlines())} 行")

# ─── Mixin header ───
MIXIN_HDR = '''\
"""
{title}
由 scripts/refactor/_split_mt15_html_pdf.py 自动生成 (MT-15)
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


write_mixin("_pdf_text_mixin.py",  "PDF生成器 文本处理/翻译 Mixin", "PDFTextMixin",  text_r)
write_mixin("_pdf_parse_mixin.py", "PDF生成器 解析/格式化 Mixin",   "PDFParseMixin", parse_r)

# ─── 更新主文件：删除已迁移方法 + 修改 class 声明 ───
all_moved = text_i | parse_i
# 同时移除 PlaywrightBrowserPool 到独立文件（html_gen_start 以前的 class 定义）
# 即只保留 html_gen_start 之后的内容，加上原始 imports
orig_imports = browser_pool_imports  # 原始 imports 区 (L1~L26)

# 从 html_gen_start 开始的行，过滤掉已迁移的方法
gen_section = [ln for i, ln in enumerate(lines) if i >= html_gen_start and i not in all_moved]

# 修改 class 声明（在第0行）
new_class_decl = "class HTMLPDFGenerator(PDFTextMixin, PDFParseMixin):\n"
gen_section[0] = new_class_decl

# 加 Mixin imports
mixin_imports = (
    "from ._browser_pool import PlaywrightBrowserPool, get_browser_pool\n"
    "from ._pdf_text_mixin import PDFTextMixin\n"
    "from ._pdf_parse_mixin import PDFParseMixin\n"
)
# 插入到 orig_imports 末尾（最后一个 import 语句后）
new_text = orig_imports + mixin_imports + "\n\n" + "".join(gen_section)
SRC.write_text(new_text, encoding="utf-8")
nl = len(new_text.splitlines())
print(f"\n✅ html_pdf_generator.py: {total} → {nl} 行 (−{total - nl}行)")

# ─── 语法验证 ───
errors = 0
for p in [DST / "_browser_pool.py", DST / "_pdf_text_mixin.py", DST / "_pdf_parse_mixin.py", SRC]:
    try:
        ast.parse(p.read_text(encoding="utf-8"))
        print(f"  OK  {p.name}")
    except SyntaxError as e:
        print(f"  FAIL {p.name}: {e}")
        errors += 1

print(f"\n{'⚠️ 有语法错误' if errors else '✅ 所有文件语法正确'}")
import sys; sys.exit(errors)
