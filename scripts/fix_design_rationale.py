"""
批量为所有角色配置添加 design_rationale 字段
"""
import re

files_to_fix = [
    ("intelligent_project_analyzer/config/roles/v5_scenario_expert.yaml", "场景策略选择的行为学依据"),
    ("intelligent_project_analyzer/config/roles/v6_chief_engineer.yaml", "工程实施策略选择的技术依据"),
]

pattern = re.compile(
    r'(            confidence: float = Field\(description="分析置信度 \(0\.0-1\.0\)", ge=0, le=1\)\n'
    r'            \n'
    r'            # 🆕 v3\.5 Expert Autonomy Protocol 扩展字段\n'
    r'            expert_handoff_response)',
    re.MULTILINE
)

replacement_template = '''            confidence: float = Field(description="分析置信度 (0.0-1.0)", ge=0, le=1)
            
            # 🆕 v3.5 Expert Autonomy Protocol 扩展字段
            design_rationale: str = Field(
                description="【v3.5 必填】清晰阐述{reason}"
            )
            expert_handoff_response'''

for filepath, reason in files_to_fix:
    print(f"\n处理: {filepath}")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 计算匹配次数
        matches = pattern.findall(content)
        print(f"  找到 {len(matches)} 处需要修复")
        
        if matches:
            # 替换
            new_content = pattern.sub(
                replacement_template.format(reason=reason),
                content
            )
            
            # 写回
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"  ✅ 已修复 {len(matches)} 处")
        else:
            print(f"  ⚠️ 未找到匹配项")
            
    except Exception as e:
        print(f"  ❌ 错误: {e}")

print("\n✅ 批量修复完成！")
