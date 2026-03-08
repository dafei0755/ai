"""
MT-20: image_generator.py 拆分脚本 (1655行 → 2 Mixin + 精简主文件)

拆分方案:
  _image_extract_mixin.py  - 视觉提取/提示词方法  L151-L823
  _image_generate_mixin.py - 图片生成方法         L824-L1644
  image_generator.py       - models + class def + 模块函数 (~200行)

用法:
    python scripts/refactor/_split_mt20_image_generator.py
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SRC  = ROOT / "intelligent_project_analyzer" / "services" / "image_generator.py"
DST  = SRC.parent

lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
total = len(lines)
print(f"原文件行数: {total}")


def find_method_extent(lines, name, cls_indent=4):
    """含装饰器的方法范围检测"""
    def_idx = None
    for i, ln in enumerate(lines):
        s = ln.lstrip()
        if s.startswith((f"async def {name}(", f"def {name}(")):
            if len(ln) - len(s) == cls_indent:
                def_idx = i
                break
    if def_idx is None:
        raise ValueError(f"方法未找到: {name}")
    start = def_idx
    for k in range(def_idx - 1, -1, -1):
        ln = lines[k]; s = ln.lstrip()
        if s == "" or s.startswith("#"): continue
        if len(ln) - len(s) == cls_indent and s.startswith("@"):
            start = k
        else:
            break
    for j in range(def_idx + 1, len(lines)):
        ln = lines[j]; s = ln.lstrip()
        if s == "": continue
        indent = len(ln) - len(s)
        if indent != cls_indent: continue
        if s.startswith(("def ", "async def ", "class ", "@")): return start, j
        if re.match(r'^[A-Z_][A-Z0-9_]*\s*[=:]', s): return start, j
    return start, len(lines)


EXTRACT_METHODS = [
    "_extract_visual_brief",
    "_fallback_visual_brief",
    "_extract_style_anchor_fallback",
    "_build_visual_reference_context",
    "_generate_structured_prompt",
    "_fallback_structured_prompt",
    "_validate_and_enhance_prompt",
    "_llm_extract_visual_prompt",
    "_enhance_prompt_with_user_input",
    "_build_headers",
    "_enhance_prompt",
]

GENERATE_METHODS = [
    "generate_image",
    "generate_with_vision_reference",
    "_parse_response",
    "generate_concept_images",
    "_extract_visual_concepts",
    "generate_deliverable_image",
    "edit_image_with_mask",
]


def collect(names):
    ranges, indices = [], set()
    for name in names:
        try:
            s, e = find_method_extent(lines, name)
            ranges.append((s, e)); indices.update(range(s, e))
            print(f"  {name}: L{s+1}-{e} ({e-s}行)")
        except ValueError as ex:
            print(f"  ⚠️ {ex}")
    return ranges, indices


print("=== EXTRACT_MIXIN ===")
ext_r, ext_i = collect(EXTRACT_METHODS)
print("=== GENERATE_MIXIN ===")
gen_r, gen_i = collect(GENERATE_METHODS)

# ─── class 起始前 imports ───
class_start = next(i for i, ln in enumerate(lines) if re.match(r'^class ImageGeneratorService\b', ln))
raw_imports = "".join(lines[:class_start])

MIXIN_HDR = '''\
"""
{title}
由 scripts/refactor/_split_mt20_image_generator.py 自动生成 (MT-20)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple


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
write_mixin("_image_extract_mixin.py",   "图片生成器 视觉提取/提示词 Mixin", "ImageExtractMixin",  ext_r)
write_mixin("_image_generate_mixin.py",  "图片生成器 图片生成 Mixin",        "ImageGenerateMixin", gen_r)

# ─── 更新主文件 ───
all_moved = ext_i | gen_i
new_lines  = [ln for i, ln in enumerate(lines) if i not in all_moved]
new_text   = "".join(new_lines)
new_text   = new_text.replace(
    "class ImageGeneratorService:",
    "class ImageGeneratorService(ImageExtractMixin, ImageGenerateMixin):",
)
mixin_block = (
    "from ._image_extract_mixin import ImageExtractMixin\n"
    "from ._image_generate_mixin import ImageGenerateMixin\n"
)
first_local = next(
    (ln for ln in new_text.splitlines(keepends=True) if ln.startswith("from .") or ln.startswith("from ..")),
    None,
)
if first_local:
    new_text = new_text.replace(first_local, mixin_block + first_local, 1)

SRC.write_text(new_text, encoding="utf-8")
nl = len(new_text.splitlines())
print(f"✅ image_generator.py: {total} → {nl} 行 (−{total - nl}行)")

# ─── 语法验证 ───
errors = 0
for p in [DST / "_image_extract_mixin.py", DST / "_image_generate_mixin.py", SRC]:
    try:
        ast.parse(p.read_text(encoding="utf-8"))
        print(f"  OK  {p.name}")
    except SyntaxError as e:
        print(f"  FAIL {p.name}: {e}")
        errors += 1

print(f"\n{'⚠️ 有语法错误' if errors else '✅ 所有文件语法正确'}")
import sys; sys.exit(errors)
