"""
验证动机标签修复
测试motivation_label字段是否正确添加到任务中
"""

import asyncio

import pytest

from intelligent_project_analyzer.services.core_task_decomposer import decompose_core_tasks


@pytest.mark.asyncio
async def test_motivation_label_fix():
    """测试动机标签是否正确添加"""

    print("\n" + "=" * 80)
    print("🧪 测试动机标签修复")
    print("=" * 80)

    # 测试用例1：文化保护项目
    user_input_1 = "深圳蛇口渔村改造项目，需要在现代化改造的同时保留渔民文化记忆"
    structured_data_1 = {
        "project_task": "蛇口渔村改造",
        "character_narrative": "保留渔民文化记忆",
        "project_type": "cultural_heritage",
    }

    print("\n\n📋 测试用例1：文化保护项目")
    print(f"输入: {user_input_1}")

    tasks_1 = await decompose_core_tasks(user_input_1, structured_data_1)

    # 🆕 v7.110.0: 验证任务数量是否在合理范围（3-12个）
    task_count = len(tasks_1)
    is_valid_count = 3 <= task_count <= 12
    count_status = "✅" if is_valid_count else "⚠️"
    print(f"\n{count_status} 拆解出 {task_count} 个任务（合理范围: 3-12）：")
    has_label = True
    for i, task in enumerate(tasks_1, 1):
        title = task.get("title", "未命名")
        motivation_type = task.get("motivation_type", "❌ 缺失")
        motivation_label = task.get("motivation_label", "❌ 缺失")
        confidence = task.get("confidence_score", 0)

        print(f"\n  {i}. {title}")
        print(f"     类型: {motivation_type}")
        print(f"     标签: {motivation_label}")
        print(f"     置信度: {confidence:.2f}")

        if not task.get("motivation_label"):
            has_label = False
            print(f"     ⚠️ 缺少 motivation_label 字段！")

    # 测试用例2：商业空间
    user_input_2 = "设计一个新零售咖啡店，提升品牌影响力和商业价值"
    structured_data_2 = {"project_task": "新零售咖啡店设计", "project_type": "commercial_space"}

    print("\n\n📋 测试用例2：商业空间设计")
    print(f"输入: {user_input_2}")

    tasks_2 = await decompose_core_tasks(user_input_2, structured_data_2)

    # 🆕 v7.110.0: 验证任务数量
    task_count_2 = len(tasks_2)
    is_valid_count_2 = 3 <= task_count_2 <= 12
    count_status_2 = "✅" if is_valid_count_2 else "⚠️"
    print(f"\n{count_status_2} 拆解出 {task_count_2} 个任务（合理范围: 3-12）：")
    for i, task in enumerate(tasks_2, 1):
        title = task.get("title", "未命名")
        motivation_type = task.get("motivation_type", "❌ 缺失")
        motivation_label = task.get("motivation_label", "❌ 缺失")
        confidence = task.get("confidence_score", 0)

        print(f"\n  {i}. {title}")
        print(f"     类型: {motivation_type}")
        print(f"     标签: {motivation_label}")
        print(f"     置信度: {confidence:.2f}")

        if not task.get("motivation_label"):
            has_label = False
            print(f"     ⚠️ 缺少 motivation_label 字段！")

    # 测试用例3：无障碍设计
    user_input_3 = "社区公园无障碍改造，让老人和轮椅使用者都能方便使用"
    structured_data_3 = {"project_task": "社区公园无障碍改造", "project_type": "public_space"}

    print("\n\n📋 测试用例3：无障碍设计")
    print(f"输入: {user_input_3}")

    tasks_3 = await decompose_core_tasks(user_input_3, structured_data_3)

    # 🆕 v7.110.0: 验证任务数量
    task_count_3 = len(tasks_3)
    is_valid_count_3 = 3 <= task_count_3 <= 12
    count_status_3 = "✅" if is_valid_count_3 else "⚠️"
    print(f"\n{count_status_3} 拆解出 {task_count_3} 个任务（合理范围: 3-12）：")
    for i, task in enumerate(tasks_3, 1):
        title = task.get("title", "未命名")
        motivation_type = task.get("motivation_type", "❌ 缺失")
        motivation_label = task.get("motivation_label", "❌ 缺失")
        confidence = task.get("confidence_score", 0)

        print(f"\n  {i}. {title}")
        print(f"     类型: {motivation_type}")
        print(f"     标签: {motivation_label}")
        print(f"     置信度: {confidence:.2f}")

        if not task.get("motivation_label"):
            has_label = False
            print(f"     ⚠️ 缺少 motivation_label 字段！")

    print("\n\n" + "=" * 80)
    if has_label:
        print("✅ 测试通过：所有任务都包含 motivation_label 字段")
    else:
        print("❌ 测试失败：部分任务缺少 motivation_label 字段")
    print("=" * 80 + "\n")

    return has_label


if __name__ == "__main__":
    success = asyncio.run(test_motivation_label_fix())
    exit(0 if success else 1)
