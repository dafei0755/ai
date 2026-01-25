"""
v7.130 interaction_type 一致性验证测试

简化版测试：直接验证后端代码中的 interaction_type 与 step 数字一致
"""

import re


def test_step1_payload_consistency():
    """验证 Step 1 payload 中 interaction_type 与 step 一致"""
    with open(
        "intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py", "r", encoding="utf-8"
    ) as f:
        content = f.read()

    # 查找 Step 1 的 payload
    # 在 step1_core_task 方法中查找
    step1_pattern = r'"interaction_type":\s*"progressive_questionnaire_step1".*?"step":\s*1'
    match = re.search(step1_pattern, content, re.DOTALL)

    assert match is not None, "Step 1 的 interaction_type 应该是 'progressive_questionnaire_step1' 且 step=1"
    print("✅ Step 1: interaction_type='progressive_questionnaire_step1', step=1")


def test_step2_info_completion_payload_consistency():
    """验证 Step 2 (信息补全) payload 中 interaction_type 与 step 一致

    v7.130: step2 = 信息补全
    """
    with open(
        "intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py", "r", encoding="utf-8"
    ) as f:
        content = f.read()

    # 查找信息补全步骤的 payload（在 step3_gap_filling 方法中，但发送 step=2）
    step2_pattern = r'"interaction_type":\s*"progressive_questionnaire_step2".*?"step":\s*2'
    match = re.search(step2_pattern, content, re.DOTALL)

    assert match is not None, "信息补全的 interaction_type 应该是 'progressive_questionnaire_step2' 且 step=2"
    print("✅ Step 2 (信息补全): interaction_type='progressive_questionnaire_step2', step=2")


def test_step3_radar_payload_consistency():
    """验证 Step 3 (雷达图) payload 中 interaction_type 与 step 一致

    v7.130: step3 = 雷达图
    """
    with open(
        "intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py", "r", encoding="utf-8"
    ) as f:
        content = f.read()

    # 查找雷达图步骤的 payload（在 step2_radar 方法中，但发送 step=3）
    step3_pattern = r'"interaction_type":\s*"progressive_questionnaire_step3".*?"step":\s*3'
    match = re.search(step3_pattern, content, re.DOTALL)

    assert match is not None, "雷达图的 interaction_type 应该是 'progressive_questionnaire_step3' 且 step=3"
    print("✅ Step 3 (雷达图): interaction_type='progressive_questionnaire_step3', step=3")


def test_no_mismatched_interaction_types():
    """验证没有 interaction_type 与 step 不匹配的情况"""
    with open(
        "intelligent_project_analyzer/interaction/nodes/progressive_questionnaire.py", "r", encoding="utf-8"
    ) as f:
        content = f.read()

    # 查找所有 payload 定义块（从 payload = { 到 下一个 } 结束）
    # 检查每个 payload 块内部的 interaction_type 和 step 是否匹配

    # 使用更精确的匹配：只在同一个 payload 字典内查找
    # 查找紧邻的 interaction_type 和 step 定义（在10行内）
    lines = content.split("\n")

    errors = []
    for i, line in enumerate(lines):
        if '"interaction_type": "progressive_questionnaire_step' in line:
            # 提取 step 数字
            if "step1" in line:
                expected_step = 1
            elif "step2" in line:
                expected_step = 2
            elif "step3" in line:
                expected_step = 3
            else:
                continue

            # 在接下来的5行内查找 "step": 数字
            for j in range(i + 1, min(i + 6, len(lines))):
                if '"step":' in lines[j]:
                    # 提取实际的 step 数字
                    import re

                    step_match = re.search(r'"step":\s*(\d+)', lines[j])
                    if step_match:
                        actual_step = int(step_match.group(1))
                        if actual_step != expected_step:
                            errors.append(f"行{i+1}: interaction_type=step{expected_step} 但 step={actual_step}")
                    break

    assert len(errors) == 0, f"发现 {len(errors)} 处不匹配:\n" + "\n".join(errors)
    print("✅ 没有 interaction_type 与 step 不匹配的情况")


if __name__ == "__main__":
    test_step1_payload_consistency()
    test_step2_info_completion_payload_consistency()
    test_step3_radar_payload_consistency()
    test_no_mismatched_interaction_types()
    print("\n🎉 所有测试通过！v7.130 interaction_type 一致性验证成功")
