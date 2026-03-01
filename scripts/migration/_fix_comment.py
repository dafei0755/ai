p = r"d:\11-20\langgraph-design\frontend-nextjs\app\admin\crawler-monitor\page.tsx"
c = open(p, encoding="utf-8").read()
idx = c.find("\u5206\u7c7b\u8fdb\u5ea6\u5217\u8868")
print(repr(c[idx - 10 : idx + 35]))
# fix: {/* ... */ followed by newline → {/* ... */} followed by newline
import re

fixed = re.sub(r"(\{/\*[^*]*\*/)(\n)", lambda m: m.group(1) + "}" + m.group(2), c)
diffs = [(i, a, b) for i, (a, b) in enumerate(zip(c.splitlines(), fixed.splitlines())) if a != b]
print(f"changed {len(diffs)} lines:")
for i, a, b in diffs:
    print(f"  line {i+1}: {repr(a)} -> {repr(b)}")
if diffs:
    open(p, "w", encoding="utf-8").write(fixed)
    print("saved")
