"""
v7.128 核心路由验证

直接检查源代码中的关键字符串
"""

import os

print("=" * 80)
print("v7.128 问卷步骤互换验证")
print("=" * 80)
print()

# 读取 progressive_questionnaire.py
file_path = os.path.join("..", "intelligent_project_analyzer", "interaction", "nodes", "progressive_questionnaire.py")

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

print("[后端] progressive_questionnaire.py 检查:")
print()

# 测试1: Step 1 路由
if 'return Command(update=update_dict, goto="progressive_step3_gap_filling")' in content:
    # 确认这是在 step1 函数中
    if content.find("def step1_core_task") < content.find('goto="progressive_step3_gap_filling"'):
        print("✅ Step 1 正确路由到 progressive_step3_gap_filling")
    else:
        print("⚠️  找到 progressive_step3_gap_filling 但不在 step1 中")
else:
    print("❌ Step 1 未找到正确的路由")

# 测试2: Step 2 路由和编号
if 'return Command(update=update_dict, goto="project_director")' in content:
    # 检查是否在 step2 中
    step2_start = content.find("def step2_radar")
    step3_start = content.find("def step3_gap_filling")

    project_director_pos = content.find('goto="project_director"')

    if step2_start < project_director_pos < step3_start:
        print("✅ Step 2 正确路由到 project_director")
    else:
        print("⚠️  找到 project_director 但位置不在 step2 中")
else:
    print("❌ Step 2 未找到正确的路由")

if '"step": 3,' in content and '"interaction_type": "progressive_questionnaire_step2"' in content:
    print("✅ Step 2 payload 中 step=3")
else:
    print("❌ Step 2 payload 步骤编号不正确")

# 测试3: Step 3 路由和编号
if 'return Command(update=update_dict, goto="progressive_step2_radar")' in content:
    # 检查是否在 step3 中
    step3_start = content.find("def step3_gap_filling")

    step2_radar_pos = content.find('goto="progressive_step2_radar"')

    if step3_start < step2_radar_pos:
        print("✅ Step 3 正确路由到 progressive_step2_radar")
    else:
        print("⚠️  找到 progressive_step2_radar 但位置不正确")
else:
    print("❌ Step 3 未找到正确的路由")

if '"step": 2,' in content and '"interaction_type": "progressive_questionnaire_step3"' in content:
    print("✅ Step 3 payload 中 step=2")
else:
    print("❌ Step 3 payload 步骤编号不正确")

# 测试4: 智能默认值
if "gap_filling_answers = state.get" in content and "default_values" in content:
    print("✅ Step 2 包含智能默认值逻辑")
else:
    print("❌ Step 2 未包含智能默认值逻辑")

print()
print("[前端] UnifiedProgressiveQuestionnaireModal.tsx 检查:")
print()

# 读取前端文件
frontend_path = os.path.join("..", "frontend-nextjs", "components", "UnifiedProgressiveQuestionnaireModal.tsx")

try:
    with open(frontend_path, "r", encoding="utf-8") as f:
        frontend_content = f.read()

    # 检查步骤标签
    if "{ number: 2, label: '信息补全'" in frontend_content:
        print("✅ 步骤2标签为'信息补全'")
    else:
        print("❌ 步骤2标签不正确")

    if "{ number: 3, label: '偏好雷达图'" in frontend_content:
        print("✅ 步骤3标签为'偏好雷达图'")
    else:
        print("❌ 步骤3标签不正确")

    # 检查渲染逻辑
    if "case 2: return renderStep3Content();" in frontend_content:
        print("✅ case 2 渲染 Step3Content")
    else:
        print("❌ case 2 渲染逻辑不正确")

    if "case 3: return renderStep2Content();" in frontend_content:
        print("✅ case 3 渲染 Step2Content")
    else:
        print("❌ case 3 渲染逻辑不正确")

    # 检查验证逻辑
    if "currentStep === 2 && !validateStep3Required()" in frontend_content:
        print("✅ Step 2 验证逻辑正确")
    else:
        print("❌ Step 2 验证逻辑不正确")

except Exception as e:
    print(f"❌ 无法读取前端文件: {e}")

print()
print("=" * 80)
print("验证完成！")
print("=" * 80)
