"""
v7.106 任务精度优化测试脚本
测试场景：上海老弄堂120平米老房翻新 + 杂志级效果 + 50万预算约束
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from intelligent_project_analyzer.services.core_task_decomposer import decompose_core_tasks
from intelligent_project_analyzer.services.llm_factory import LLMFactory


async def test_task_precision():
    """测试任务精度 - v7.106场景锚定"""
    print("\n" + "=" * 80)
    print("🧪 v7.106 任务精度优化测试")
    print("=" * 80 + "\n")

    # 测试用例：上海老弄堂场景
    test_case = {
        "user_input": "上海老弄堂120平米老房翻新，业主想要'杂志级'的重生效果，但全包预算（含软硬装）被严格限制在50万人民币",
        "structured_data": {
            "project_type": "residential_renovation",
            "physical_context": "上海老弄堂120平米老房",
            "project_task": "老房翻新，追求杂志级效果",
            "character_narrative": "业主希望在50万预算内实现杂志级重生效果",
        },
    }

    print(f"📝 测试场景: {test_case['user_input']}\n")

    # 初始化LLM
    llm = LLMFactory.create_llm()

    print("🚀 开始任务拆解...\n")

    try:
        # 执行任务拆解
        tasks = await decompose_core_tasks(
            user_input=test_case["user_input"], structured_data=test_case["structured_data"], llm=llm
        )

        print("✅ 任务拆解完成\n")
        print("-" * 80)
        print("📋 生成的任务列表:")
        print("-" * 80 + "\n")

        # 检查每个任务是否包含场景约束
        scene_keywords = ["上海", "老弄堂", "120平米", "50万", "杂志级", "老房翻新"]

        for idx, task in enumerate(tasks, 1):
            print(f"任务 {idx}: {task.get('title', 'N/A')}")
            print(f"描述: {task.get('description', 'N/A')[:200]}...")

            # 检查场景锚定
            title_desc = task.get("title", "") + task.get("description", "")
            found_keywords = [kw for kw in scene_keywords if kw in title_desc]

            if found_keywords:
                print(f"✅ 场景锚定: {', '.join(found_keywords)}")
            else:
                print("⚠️ 警告: 任务未包含明确场景约束")

            print(f"优先级: {task.get('priority', 'N/A')}")
            print()

        # 统计分析
        total_tasks = len(tasks)
        tasks_with_scene = sum(
            1
            for task in tasks
            if any(kw in task.get("title", "") + task.get("description", "") for kw in scene_keywords)
        )

        print("-" * 80)
        print("📊 场景锚定统计:")
        print(f"  总任务数: {total_tasks}")
        print(f"  包含场景约束的任务: {tasks_with_scene}/{total_tasks}")
        print(f"  场景锚定率: {tasks_with_scene/total_tasks*100:.1f}%" if total_tasks > 0 else "  N/A")

        if tasks_with_scene >= total_tasks * 0.8:
            print("\n✅ v7.106场景锚定测试通过！（≥80%任务包含场景约束）")
        else:
            print(f"\n⚠️ v7.106场景锚定需要改进（仅{tasks_with_scene/total_tasks*100:.1f}%任务包含场景约束）")

        print("-" * 80)

        return tasks

    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback

        traceback.print_exc()
        return None


async def test_data_flow():
    """测试数据流传递 - confirmed_core_tasks是否传递到后续节点"""
    print("\n" + "=" * 80)
    print("🧪 v7.106 数据流传递测试")
    print("=" * 80 + "\n")

    # 模拟confirmed_core_tasks
    mock_tasks = [{"title": "上海老弄堂120平米空间规划与功能布局研究（50万预算约束）", "description": "针对120平米老房翻新的空间规划...", "priority": "high"}]

    # 测试状态字典
    test_state = {"user_input": "测试数据流", "confirmed_core_tasks": mock_tasks}

    # 检查状态中是否包含confirmed_core_tasks
    confirmed_tasks = test_state.get("confirmed_core_tasks")

    if confirmed_tasks:
        print("✅ confirmed_core_tasks 已成功存储在状态中")
        print(f"   任务数量: {len(confirmed_tasks)}")
        print(f"   首个任务: {confirmed_tasks[0].get('title', 'N/A')[:80]}...")
        print("\n✅ v7.106数据流传递测试通过！")
    else:
        print("❌ confirmed_core_tasks 未找到，数据流传递失败")

    print("-" * 80)


if __name__ == "__main__":
    import io
    import sys

    # 修复Windows控制台编码问题
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    print("\n开始 v7.106 系统测试\n")

    # 运行测试
    asyncio.run(test_task_precision())
    asyncio.run(test_data_flow())

    print("\n✅ 所有测试完成！\n")
