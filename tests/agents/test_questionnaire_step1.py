"""
测试问卷第一步的动机识别修复
验证是否正确使用12种动机类型 + LLM推理
"""
import asyncio

from loguru import logger

from intelligent_project_analyzer.services.core_task_decomposer import decompose_core_tasks

# 配置日志
logger.add("test_step1.log", rotation="10 MB", level="DEBUG")


async def test_step1_motivation():
    """测试问卷第一步的动机识别"""

    # 测试用例1: 文化保护（应识别为cultural）
    test_case_1 = {
        "user_input": "深圳蛇口渔村改造，保留渔民文化记忆",
        "structured_data": {"project_name": "蛇口渔村文化保护改造", "project_description": "保留渔民生活方式和历史建筑"},
    }

    # 测试用例2: 商业空间（应识别为commercial）
    test_case_2 = {
        "user_input": "设计一个新零售咖啡店，提升品牌影响力",
        "structured_data": {"project_name": "新零售咖啡店", "project_description": "增强品牌认知度和客流量"},
    }

    # 测试用例3: 无障碍设计（应识别为inclusive）
    test_case_3 = {
        "user_input": "社区公园无障碍改造，让老人和轮椅使用者都能方便使用",
        "structured_data": {"project_name": "社区公园无障碍改造", "project_description": "提升可达性和包容性"},
    }

    test_cases = [
        ("文化保护", test_case_1, "cultural"),
        ("商业空间", test_case_2, "commercial"),
        ("无障碍设计", test_case_3, "inclusive"),
    ]

    print("\n" + "=" * 60)
    print("[TEST] 开始测试问卷第一步动机识别修复")
    print("=" * 60 + "\n")

    all_passed = True

    for name, test_case, expected_type in test_cases:
        print(f"\n[TEST CASE] {name}")
        print(f"   输入: {test_case['user_input']}")
        print(f"   期望类型: {expected_type}")
        print("-" * 60)

        try:
            result = await decompose_core_tasks(
                user_input=test_case["user_input"], structured_data=test_case["structured_data"]
            )

            # decompose_core_tasks 返回列表，不是字典
            if result and isinstance(result, list):
                tasks = result
                # 🆕 v7.110.0: 自适应验证 - 任务数量应在3-12个合理范围内
                task_count = len(tasks)
                is_valid_count = 3 <= task_count <= 12
                count_status = "✅" if is_valid_count else "⚠️"
                print(f"   {count_status} 拆解任务数: {task_count} 个 (合理范围: 3-12)\n")

                for i, task in enumerate(tasks, 1):
                    motivation_type = task.get("motivation_type", "未识别")
                    motivation_label = task.get("motivation_label", "未知")
                    confidence = task.get("confidence_score", 0.0)
                    reasoning = task.get("ai_reasoning", "无")

                    print(f"      任务 {i}: {task['title']}")
                    print(f"      └─ 动机类型: {motivation_type} ({motivation_label})")
                    print(f"      └─ 置信度: {confidence:.2f}")
                    print(f"      └─ 推理依据: {reasoning[:80]}...")
                    print()

                    # 验证是否使用了新的动机类型
                    if motivation_type in [
                        "cultural",
                        "commercial",
                        "wellness",
                        "technical",
                        "sustainable",
                        "professional",
                        "inclusive",
                    ]:
                        print(f"      ✅ 识别出新动机类型: {motivation_type}")

                # 检查是否有任务匹配预期类型
                found_expected = any(t.get("motivation_type") == expected_type for t in tasks)
                if found_expected:
                    print(f"   ✅ 找到预期动机类型: {expected_type}\n")
                else:
                    print(f"   ⚠️ 未找到预期类型 {expected_type}，可能需要调整关键词或LLM提示\n")
                    all_passed = False

            else:
                print(f"   ❌ 拆解失败: 无任务返回\n")
                all_passed = False

        except Exception as e:
            print(f"   ❌ 测试失败: {e}\n")
            logger.exception(f"测试用例 {name} 失败")
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有测试通过！问卷第一步修复成功")
    else:
        print("⚠️ 部分测试未达预期，请检查日志: test_step1.log")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(test_step1_motivation())
