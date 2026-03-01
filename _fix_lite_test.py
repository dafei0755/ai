"""Fix test_progressive_questionnaire_lite.py - wrap execution body in main()."""
from pathlib import Path

filepath = Path("tests/interaction/test_progressive_questionnaire_lite.py")
content = filepath.read_text(encoding="utf-8")
lines = content.splitlines()

# Find def main() line index
main_idx = next(i for i, l in enumerate(lines) if l.startswith("def main"))
# The main() body currently has 3 indented lines, then all the rest is module-level
# Find end of current main() body (last indented line)
body_end = main_idx + 1
while body_end < len(lines) and (lines[body_end].startswith("    ") or lines[body_end] == ""):
    body_end += 1

print(f"main_idx={main_idx}, body_end={body_end}")
print("Module-level code starts at:", body_end)
print("First few module-level lines:")
for i in range(body_end, min(body_end + 5, len(lines))):
    print(f"  {i}: {repr(lines[i])}")

# Build new content:
# 1. Header (docstring + imports up to def main():)
header_lines = lines[: main_idx + 1]  # includes "def main() -> None:"

# 2. The current body of main() (already indented)
current_body = [l for l in lines[main_idx + 1 : body_end] if l.strip() != "" or True]

# 3. All module-level execution lines (need to be indented with 4 spaces)
module_exec_lines = lines[body_end:]

# Indent module_exec_lines
indented_exec = []
for line in module_exec_lines:
    if line == "":
        indented_exec.append("")
    else:
        indented_exec.append("    " + line)

# 4. Remove the last blank lines and add __name__ guard
while indented_exec and indented_exec[-1].strip() == "":
    indented_exec.pop()

new_lines = header_lines + current_body + indented_exec + ["", "", 'if __name__ == "__main__":', "    main()"]

new_content = "\n".join(new_lines) + "\n"
filepath.write_text(new_content, encoding="utf-8")
print(f"\nDone! Wrote {len(new_lines)} lines.")
print("Last 5 lines:")
for l in new_lines[-5:]:
    print(f"  {repr(l)}")
