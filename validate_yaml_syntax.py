"""验证YAML文件语法"""
import yaml
import sys

files = [
    'intelligent_project_analyzer/config/roles/v3_narrative_expert.yaml',
    'intelligent_project_analyzer/config/roles/v5_scenario_expert.yaml',
    'intelligent_project_analyzer/config/roles/v2_design_director.yaml',
    'intelligent_project_analyzer/config/roles/v6_chief_engineer.yaml',
    'intelligent_project_analyzer/config/roles/v4_design_researcher.yaml'
]

print("=" * 80)
print("🔧 v7.63.1: YAML语法验证")
print("=" * 80)
print()

errors = []
for f in files:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            yaml.safe_load(file)
        print(f"✅ {f.split('/')[-1]}")
    except Exception as e:
        errors.append((f, str(e)))
        print(f"❌ {f.split('/')[-1]}: {e}")

print()
if errors:
    print("=" * 80)
    print(f"❌ 发现 {len(errors)} 个错误")
    print("=" * 80)
    sys.exit(1)
else:
    print("=" * 80)
    print("🎉 所有5个YAML文件语法验证通过！")
    print("=" * 80)
    sys.exit(0)
