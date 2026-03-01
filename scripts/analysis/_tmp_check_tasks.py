import json, re

with open(".vscode/tasks.json", encoding="utf-8") as f:
    content = f.read()

# Find all lines with _*.py references
lines = content.split("\n")
for i, line in enumerate(lines, 1):
    if re.search(r"_\w+\.py", line):
        print(f"L{i}: {line.strip()}")
