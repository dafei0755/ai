"""
MT-16: review_agents.py 拆分脚本 (1779行 → 5个独立类文件 + 聚合器)

结构:
  ReviewerRole (base)  L21-L116
  RedTeamReviewer      L117-L693
  BlueTeamReviewer     L694-L1318
  JudgeReviewer        L1319-L1612
  ClientReviewer       L1613-end

拆分方案:
  _reviewer_base.py       - ReviewerRole (base class)
  _red_team_reviewer.py   - RedTeamReviewer
  _blue_team_reviewer.py  - BlueTeamReviewer
  _judge_reviewer.py      - JudgeReviewer
  _client_reviewer.py     - ClientReviewer
  review_agents.py        - 薄聚合器 (re-export all)

用法:
    python scripts/refactor/_split_mt16_review_agents.py
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SRC  = ROOT / "intelligent_project_analyzer" / "review" / "review_agents.py"
DST  = SRC.parent

lines = SRC.read_text(encoding="utf-8").splitlines(keepends=True)
total = len(lines)
print(f"原文件行数: {total}")


def find_class_start(name):
    for i, ln in enumerate(lines):
        if re.match(rf'^class {name}\b', ln):
            return i
    raise ValueError(f"class {name} not found")


# ─── 找各类起始行 ───
base_start    = find_class_start("ReviewerRole")
red_start     = find_class_start("RedTeamReviewer")
blue_start    = find_class_start("BlueTeamReviewer")
judge_start   = find_class_start("JudgeReviewer")
client_start  = find_class_start("ClientReviewer")

for name, idx in [("ReviewerRole", base_start), ("RedTeamReviewer", red_start),
                   ("BlueTeamReviewer", blue_start), ("JudgeReviewer", judge_start),
                   ("ClientReviewer", client_start)]:
    print(f"  {name}: 行 {idx+1}")

# ─── 原始 imports 区（L1 ~ before ReviewerRole）───
raw_imports = "".join(lines[:base_start])


def write_class_file(fname, title, class_range_lines, extra_imports=""):
    content = raw_imports + extra_imports + "".join(class_range_lines)
    (DST / fname).write_text(content, encoding="utf-8")
    lc = len(content.splitlines())
    print(f"✅ {fname}: {lc} 行")
    return lc


print("\n=== 写出独立类文件 ===")
write_class_file("_reviewer_base.py",      "ReviewerRole",     lines[base_start:red_start])
write_class_file("_red_team_reviewer.py",  "RedTeamReviewer",  lines[red_start:blue_start],
                 "from ._reviewer_base import ReviewerRole\n\n")
write_class_file("_blue_team_reviewer.py", "BlueTeamReviewer", lines[blue_start:judge_start],
                 "from ._reviewer_base import ReviewerRole\n\n")
write_class_file("_judge_reviewer.py",     "JudgeReviewer",    lines[judge_start:client_start],
                 "from ._reviewer_base import ReviewerRole\n\n")
write_class_file("_client_reviewer.py",    "ClientReviewer",   lines[client_start:],
                 "from ._reviewer_base import ReviewerRole\n\n")


# ─── 薄聚合器 ───
AGGREGATOR = '''\
"""
review_agents - 评审智能体模块聚合器 (MT-16 拆分后)

子文件:
  _reviewer_base.py       ReviewerRole (base)
  _red_team_reviewer.py   RedTeamReviewer
  _blue_team_reviewer.py  BlueTeamReviewer
  _judge_reviewer.py      JudgeReviewer
  _client_reviewer.py     ClientReviewer
"""
from ._reviewer_base import ReviewerRole  # noqa: F401
from ._red_team_reviewer import RedTeamReviewer  # noqa: F401
from ._blue_team_reviewer import BlueTeamReviewer  # noqa: F401
from ._judge_reviewer import JudgeReviewer  # noqa: F401
from ._client_reviewer import ClientReviewer  # noqa: F401

__all__ = [
    "ReviewerRole",
    "RedTeamReviewer",
    "BlueTeamReviewer",
    "JudgeReviewer",
    "ClientReviewer",
]
'''
SRC.write_text(AGGREGATOR, encoding="utf-8")
print(f"✅ review_agents.py: {total} → {len(AGGREGATOR.splitlines())} 行 (聚合器)")

# ─── 语法验证 ───
errors = 0
for fname in [
    "_reviewer_base.py",
    "_red_team_reviewer.py",
    "_blue_team_reviewer.py",
    "_judge_reviewer.py",
    "_client_reviewer.py",
    "review_agents.py",
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
