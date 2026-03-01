import re

with open(r"d:\11-20\langgraph-design\frontend-nextjs\components\PlanReviewPanel.tsx", "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
issues = []
for i, line in enumerate(lines, 1):
    s = line.rstrip()
    # Pattern 1: className="..." where quote is missing at end
    if "className=" in s and re.search(r'className="[^"]*$', s):
        # Check it's not a multi-line expression (next line would close)
        issues.append(f'  L{i} (className unterminated "): {s}')
    # Pattern 2: single-quote string unterminated in ternary or object literal
    if re.search(r"[?:=]\s*'[^']*$", s):
        if not s.strip().startswith("//"):
            issues.append(f"  L{i} (unterminated single-quote): {s}")

if issues:
    print(f"{len(issues)} potential issues:")
    for iss in issues:
        print(iss)
else:
    print("No unterminated string issues detected!")
