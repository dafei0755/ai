"""修复 progressive_questionnaire.py 的缩进问题"""

import re

file_path = r"d:\11-20\langgraph-design\intelligent_project_analyzer\interaction\nodes\progressive_questionnaire.py"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 找到需要修复的范围：从第857行到第1218行（0-based index: 856-1217）
# 这些行需要增加4个空格的缩进

start_line = 856  # user_input = state.get("user_input", "")
end_line = 1217  # return Command(update=update_dict, goto="progressive_step2_radar")

print(f"修复第 {start_line+1} 行到第 {end_line+1} 行的缩进...")

for i in range(start_line, end_line + 1):
    if i < len(lines):
        # 添加4个空格缩进
        lines[i] = "    " + lines[i]

# 写回文件
with open(file_path, "w", encoding="utf-8") as f:
    f.writelines(lines)

print(f"✅ 缩进修复完成！")
