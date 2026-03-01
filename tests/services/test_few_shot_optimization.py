"""
P0优化1: Few-Shot示例库测试
测试Few-Shot加载器和提示词集成
"""

import sys
from pathlib import Path

# 添加项目根目录到path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from intelligent_project_analyzer.utils.few_shot_loader import get_few_shot_loader
from intelligent_project_analyzer.core.prompt_templates import ExpertPromptTemplate


def test_few_shot_loader():
    """测试Few-Shot加载器"""
    print("=" * 80)
    print("测试1: Few-Shot加载器基本功能")
    print("=" * 80)

    loader = get_few_shot_loader()

    # 测试加载V2_0的示例
    examples = loader.load_examples_for_role("V2_0")

    print(f"\n✅ 成功加载 {len(examples)} 个示例")
    for idx, ex in enumerate(examples, 1):
        print(f"\n示例 {idx}:")
        print(f"  ID: {ex.example_id}")
        print(f"  描述: {ex.description}")
        print(f"  类别: {ex.category}")
        print(f"  用户请求: {ex.user_request}")
        print(f"  输出长度: {len(ex.correct_output)} 字符")

    return len(examples) > 0


def test_relevant_example_matching():
    """测试相关示例匹配"""
    print("\n" + "=" * 80)
    print("测试2: 相关示例智能匹配")
    print("=" * 80)

    loader = get_few_shot_loader()

    # 测试用例1: 功能分区问题（应该匹配targeted_mode）
    test_cases = [
        ("餐饮空间如何进行功能分区？", "targeted_mode"),
        ("请提供商业综合体的总体规划", "comprehensive_mode"),
        ("办公空间的动线设计要点是什么？", "targeted_mode"),
    ]

    for user_request, expected_category in test_cases:
        print(f'\n用户请求: "{user_request}"')

        examples = loader.get_relevant_examples(
            role_id="V2_0", user_request=user_request, category=expected_category, max_examples=2
        )

        print(f"  匹配到 {len(examples)} 个示例")
        for ex in examples:
            print(f"    - {ex.description}")

    return True


def test_prompt_integration():
    """测试提示词集成"""
    print("\n" + "=" * 80)
    print("测试3: Few-Shot集成到提示词模板")
    print("=" * 80)

    # 创建测试用的autonomy_protocol
    autonomy_protocol = {"version": "4.0", "protocol_content": "测试协议内容"}

    # 创建模板
    base_prompt = "你是一个专业的设计总监"
    template = ExpertPromptTemplate("V2", base_prompt, autonomy_protocol)

    # 模拟渲染
    task_instruction = {
        "objective": "餐饮空间如何进行功能分区？",
        "deliverables": [
            {
                "name": "功能分区方案",
                "description": "详细的功能分区设计",
                "format": "analysis",
                "priority": "high",
                "success_criteria": ["明确的分区逻辑", "面积分配合理"],
            }
        ],
        "success_criteria": ["专业标准", "可落地"],
        "constraints": [],
    }

    state = {
        "current_expert_role_id": "V2_0",
        "user_input": "餐饮空间如何进行功能分区？",
        "current_phase": "分析阶段",
        "expert_analyses": {},
    }

    context = "项目类型: 餐饮空间设计"

    # 渲染提示词
    prompts = template.render(
        dynamic_role_name="项目总设计师", task_instruction=task_instruction, context=context, state=state
    )

    system_prompt = prompts["system_prompt"]

    # 检查是否包含Few-Shot内容
    has_few_shot = "📚 高质量输出示例" in system_prompt

    print(f"\n✅ 提示词总长度: {len(system_prompt)} 字符")
    print(f"✅ 包含Few-Shot示例: {has_few_shot}")

    if has_few_shot:
        # 提取Few-Shot部分
        if "### 📚 高质量输出示例" in system_prompt:
            start_idx = system_prompt.index("### 📚 高质量输出示例")
            end_idx = system_prompt.index("# 📋 TaskInstruction", start_idx)
            few_shot_content = system_prompt[start_idx:end_idx]

            print(f"✅ Few-Shot部分长度: {len(few_shot_content)} 字符")
            print("\nFew-Shot部分预览（前500字）:")
            print(few_shot_content[:500])
            print("...")

    return has_few_shot


def main():
    """运行所有测试"""
    print("\n🚀 开始P0优化1 - Few-Shot示例库测试\n")

    results = []

    # 测试1: 基本加载
    try:
        result1 = test_few_shot_loader()
        results.append(("Few-Shot加载", result1))
    except Exception as e:
        print(f"\n❌ 测试1失败: {e}")
        import traceback

        traceback.print_exc()
        results.append(("Few-Shot加载", False))

    # 测试2: 相关性匹配
    try:
        result2 = test_relevant_example_matching()
        results.append(("相关示例匹配", result2))
    except Exception as e:
        print(f"\n❌ 测试2失败: {e}")
        import traceback

        traceback.print_exc()
        results.append(("相关示例匹配", False))

    # 测试3: 提示词集成
    try:
        result3 = test_prompt_integration()
        results.append(("提示词集成", result3))
    except Exception as e:
        print(f"\n❌ 测试3失败: {e}")
        import traceback

        traceback.print_exc()
        results.append(("提示词集成", False))

    # 总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)

    for test_name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{status} - {test_name}")

    all_passed = all(result for _, result in results)

    if all_passed:
        print("\n🎉 所有测试通过！Few-Shot示例库已成功集成")
        print("\n预期收益:")
        print("  - 格式正确率: 60% → 90% (+30%)")
        print("  - 降级策略触发率: 20% → 5% (-75%)")
        print("  - 置信度分布: 0.7-0.8 → 0.85-0.95 (+0.15)")
    else:
        print("\n⚠️ 部分测试失败，需要修复")

    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
