"""
v7.128 核心路由测试

专注测试步骤路由和编号的正确性
"""

import os
import sys

if sys.platform == "win32":
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue

        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
                continue
            except Exception:
                pass

        if hasattr(stream, "buffer"):
            import io

            setattr(
                sys,
                stream_name,
                io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="replace"),
            )

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

print("=" * 80)
print("v7.128 问卷步骤互换核心路由测试")
print("=" * 80)
print()

# 测试1: 验证 Step 1 的路由目标
print("[测试1] Step 1 路由目标")
import inspect

from intelligent_project_analyzer.interaction.nodes import progressive_questionnaire

step1_source = inspect.getsource(progressive_questionnaire.ProgressiveQuestionnaireNode.step1_core_task)

if 'goto="progressive_step3_gap_filling"' in step1_source:
    print("✅ Step 1 正确路由到 progressive_step3_gap_filling")
else:
    print("❌ Step 1 路由目标不正确")
    if 'goto="progressive_step2_radar"' in step1_source:
        print("   错误: 仍然路由到 progressive_step2_radar (旧顺序)")

print()

# 测试2: 验证 Step 2 的路由目标和步骤编号
print("[测试2] Step 2 路由目标和步骤编号")
step2_source = inspect.getsource(progressive_questionnaire.ProgressiveQuestionnaireNode.step2_radar)

if 'goto="project_director"' in step2_source:
    print("✅ Step 2 正确路由到 project_director")
else:
    print("❌ Step 2 路由目标不正确")
    if 'goto="progressive_step3_gap_filling"' in step2_source:
        print("   错误: 仍然路由到 progressive_step3_gap_filling (旧顺序)")

if '"step": 3' in step2_source:
    print("✅ Step 2 payload 中 step=3 (显示为第3步)")
else:
    print("❌ Step 2 payload 中步骤编号不正确")
    if '"step": 2' in step2_source:
        print("   错误: step=2 (未修改)")

if 'progressive_questionnaire_step": 3' in step2_source or "progressive_questionnaire_step: 3" in step2_source:
    print("✅ Step 2 设置 progressive_questionnaire_step=3")
else:
    print("❌ Step 2 的 progressive_questionnaire_step 不正确")

print()

# 测试3: 验证 Step 3 的路由目标和步骤编号
print("[测试3] Step 3 路由目标和步骤编号")
step3_source = inspect.getsource(progressive_questionnaire.ProgressiveQuestionnaireNode.step3_gap_filling)

if 'goto="progressive_step2_radar"' in step3_source:
    print("✅ Step 3 正确路由到 progressive_step2_radar")
else:
    print("❌ Step 3 路由目标不正确")
    if 'goto="project_director"' in step3_source:
        print("   错误: 仍然路由到 project_director (旧顺序)")

if '"step": 2' in step3_source:
    print("✅ Step 3 payload 中 step=2 (显示为第2步)")
else:
    print("❌ Step 3 payload 中步骤编号不正确")
    if '"step": 3' in step3_source:
        print("   错误: step=3 (未修改)")

if 'progressive_questionnaire_step": 2' in step3_source or "progressive_questionnaire_step: 2" in step3_source:
    print("✅ Step 3 设置 progressive_questionnaire_step=2")
else:
    print("❌ Step 3 的 progressive_questionnaire_step 不正确")

print()

# 测试4: 验证智能默认值逻辑是否存在
print("[测试4] Step 2 智能默认值逻辑")
if "gap_filling_answers" in step2_source:
    print("✅ Step 2 包含 gap_filling_answers 读取逻辑")

    if "default_value" in step2_source or "default_values" in step2_source:
        print("✅ Step 2 包含默认值设置逻辑")
    else:
        print("⚠️  Step 2 读取了 gap_filling_answers 但未设置默认值")
else:
    print("❌ Step 2 未包含 gap_filling_answers 读取逻辑")

print()

# 测试5: 验证前端步骤标签
print("[测试5] 前端步骤指示器")
try:
    with open("../frontend-nextjs/components/UnifiedProgressiveQuestionnaireModal.tsx", "r", encoding="utf-8") as f:
        frontend_source = f.read()

    # 检查步骤标签顺序
    if "'任务梳理'" in frontend_source and "'信息补全'" in frontend_source and "'偏好雷达图'" in frontend_source:
        # 检查顺序：信息补全应该在偏好雷达图之前
        task_pos = frontend_source.find("'任务梳理'")
        info_pos = frontend_source.find("'信息补全'")
        radar_pos = frontend_source.find("'偏好雷达图'")

        if task_pos < info_pos < radar_pos:
            print("✅ 前端步骤标签顺序正确: 任务梳理 -> 信息补全 -> 偏好雷达图")
        else:
            print("❌ 前端步骤标签顺序不正确")
    else:
        print("⚠️  无法找到完整的步骤标签")

    # 检查渲染函数交换
    if "case 2: return renderStep3Content()" in frontend_source:
        print("✅ 前端 case 2 正确渲染 Step3Content (信息补全)")
    else:
        print("❌ 前端 case 2 未正确渲染")

    if "case 3: return renderStep2Content()" in frontend_source:
        print("✅ 前端 case 3 正确渲染 Step2Content (雷达图)")
    else:
        print("❌ 前端 case 3 未正确渲染")

except Exception as e:
    print(f"⚠️  无法检查前端文件: {e}")

print()
print("=" * 80)
print("测试完成")
print("=" * 80)
