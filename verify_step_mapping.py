"""
验证渐进式问卷步骤映射修复 (v7.146)

检查前后端事件类型是否匹配
"""


def verify_step_mapping():
    print("=" * 80)
    print("🔍 渐进式问卷步骤映射验证 (v7.146)")
    print("=" * 80)

    # 读取后端代码
    backend_file = "intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py"
    try:
        with open(backend_file, "r", encoding="utf-8") as f:
            backend_content = f.read()
    except Exception as e:
        print(f"❌ 无法读取后端文件: {e}")
        return False

    # 读取前端代码
    frontend_file = "frontend-nextjs/app/analysis/[sessionId]/page.tsx"
    try:
        with open(frontend_file, "r", encoding="utf-8") as f:
            frontend_content = f.read()
    except Exception as e:
        print(f"❌ 无法读取前端文件: {e}")
        return False

    # 定义期望的映射关系
    expected_mapping = {
        "step1_core_task": {
            "function": "step1_core_task",
            "ui_step": 1,
            "ui_name": "任务梳理",
            "backend_event": "progressive_questionnaire_step1",
            "frontend_event": "progressive_questionnaire_step1",
        },
        "step3_gap_filling": {
            "function": "step3_gap_filling",
            "ui_step": 2,
            "ui_name": "信息补全",
            "backend_event": "progressive_questionnaire_step2",
            "frontend_event": "progressive_questionnaire_step2",
        },
        "step2_radar": {
            "function": "step2_radar",
            "ui_step": 3,
            "ui_name": "雷达图",
            "backend_event": "progressive_questionnaire_step3",
            "frontend_event": "progressive_questionnaire_step3",
        },
    }

    all_passed = True

    # 验证后端发送的事件类型
    print("\n📤 后端事件发送验证:")
    for step_key, config in expected_mapping.items():
        func_name = config["function"]
        expected_event = config["backend_event"]

        # 查找函数定义
        func_pos = backend_content.find(f"def {func_name}(")
        if func_pos == -1:
            print(f"  ❌ {func_name}: 函数未找到")
            all_passed = False
            continue

        # 在函数内查找 interaction_type
        next_func_pos = backend_content.find("def ", func_pos + 1)
        if next_func_pos == -1:
            next_func_pos = len(backend_content)

        func_content = backend_content[func_pos:next_func_pos]

        if f'"interaction_type": "{expected_event}"' in func_content:
            print(f"  ✅ {func_name} → {expected_event}")
        else:
            print(f'  ❌ {func_name}: 未找到 interaction_type="{expected_event}"')
            all_passed = False

    # 验证前端监听的事件类型
    print("\n📥 前端事件监听验证:")
    for step_key, config in expected_mapping.items():
        expected_event = config["frontend_event"]
        ui_step = config["ui_step"]
        ui_name = config["ui_name"]

        # 查找事件监听代码
        listener_pattern = f"interaction_type === '{expected_event}'"
        if listener_pattern in frontend_content:
            # 检查注释是否正确标注了UI步骤
            listener_pos = frontend_content.find(listener_pattern)
            context = frontend_content[max(0, listener_pos - 200) : listener_pos + 200]

            if f"第{ui_step}步" in context or f"step{ui_step}" in context.lower():
                print(f"  ✅ {expected_event} → 第{ui_step}步（{ui_name}）")
            else:
                print(f"  ⚠️  {expected_event} 已监听，但注释可能不正确")
        else:
            print(f"  ❌ 前端未监听 {expected_event}")
            all_passed = False

    # 验证前后端一致性
    print("\n🔗 前后端一致性验证:")
    for step_key, config in expected_mapping.items():
        backend_event = config["backend_event"]
        frontend_event = config["frontend_event"]
        func_name = config["function"]
        ui_name = config["ui_name"]

        if backend_event == frontend_event:
            print(f"  ✅ {func_name}（{ui_name}）: {backend_event} ↔ {frontend_event}")
        else:
            print(f"  ❌ {func_name}（{ui_name}）: {backend_event} ≠ {frontend_event}")
            all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("✅ 所有验证通过！前后端事件类型已正确匹配")
    else:
        print("❌ 存在不匹配问题，请检查上述错误")
    print("=" * 80)

    return all_passed


if __name__ == "__main__":
    verify_step_mapping()
