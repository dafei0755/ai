"""在问卷末尾添加文字输入题"""
import re

file_path = r"d:\11-20\langgraph-design\intelligent_project_analyzer\config\prompts\requirements_analyst.yaml"

# 读取文件
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 定义要插入的内容
insert_text = """
      # ---- 第三部分：开放式文字输入 (Open-Ended Text Input) ----
      - question: "请分享3-5个您喜欢的设计案例、作品或场所，并简要说明为何被吸引"
        context: "这些参考将帮助我们理解您的审美倾向和设计期待"
        type: "open_ended"
      - question: "请描述您在这个空间中的典型一天（从早到晚的使用场景）"
        context: "具体的行为场景将帮助我们设计更贴合实际的空间"
        type: "open_ended"
      - question: "5年后，您希望这个空间成为怎样的存在？"
        context: "帮助我们理解您对未来状态的期望与理想转变"
        type: "open_ended"
"""

# 查找插入位置（在"能激发新灵感的、意想不到的角落"之后，"# 任务描述模板"之前）
pattern = r'(- "能激发新灵感的、意想不到的角落"\s*\n)(\n# -{60,}\n# 任务描述模板)'
replacement = r'\1' + insert_text + r'\2'

# 执行替换
new_content = re.sub(pattern, replacement, content)

# 检查是否成功替换
if new_content != content:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("✅ 成功添加文字输入题到问卷末尾")
    print(f"📍 插入位置: 在第427行附近")
else:
    print("❌ 未找到匹配的插入位置")
    print("尝试查找目标文本...")
    if '能激发新灵感的、意想不到的角落' in content:
        print("✅ 找到了目标文本")
        # 尝试更简单的匹配
        pattern2 = r'("能激发新灵感的、意想不到的角落")\n\n(# -{50,})'
        if re.search(pattern2, content):
            print("✅ 找到了简化的匹配模式")
            new_content = re.sub(pattern2, r'\1' + insert_text + r'\n\2', content)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print("✅ 使用简化模式成功添加")
        else:
            print("❌ 简化模式也未匹配")
    else:
        print("❌ 未找到目标文本")
