#!/usr/bin/env python3
"""分析当前description长度"""

import json
from pathlib import Path

# 读取已保存的数据
data_file = Path(__file__).parent.parent / "data" / "gooood_type" / "landscape_data.json"
with open(data_file, "r", encoding="utf-8") as f:
    projects = json.load(f)

print("当前description长度分析:")
print("=" * 80)

for idx, project in enumerate(projects, 1):
    desc = project.get("description", "")
    paragraphs = desc.split("\n\n")

    print(f"\n项目 {idx}: {project['title'][:50]}...")
    print(f"  总字符数: {len(desc)}")
    print(f"  段落数: {len(paragraphs)}")
    print(f"  平均每段: {len(desc) // len(paragraphs) if paragraphs else 0} 字符")

    if len(paragraphs) >= 10:
        print(f"  ⚠️  可能被截断（正好10段或更多）")

print("\n" + "=" * 80)
print("结论：如果段落数正好是10，说明被限制了")
