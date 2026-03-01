"""
测试V7_0 (情感洞察专家) Few-Shot示例加载和应用
验证情感洞察相关示例的正确性和提示词注入效果
"""

import pytest
from intelligent_project_analyzer.utils.few_shot_loader import FewShotExampleLoader
from intelligent_project_analyzer.core.prompt_templates import ExpertPromptTemplate


def test_load_v7_0_examples():
    """测试V7_0示例文件加载"""
    loader = FewShotExampleLoader()
    examples = loader.load_examples_for_role("V7_0")

    print(f"\n✅ V7_0示例加载成功: {len(examples)}个示例")

    # 验证示例数量
    assert len(examples) == 3, "V7_0应包含3个精品示例"

    # 验证示例分类
    categories = [ex.category for ex in examples]
    assert categories.count("targeted_mode") == 2, "应包含2个针对性示例"
    assert categories.count("comprehensive_mode") == 1, "应包含1个完整报告示例"

    # 验证示例内容长度 (情感分析需要更丰富细节,建议≥7000字符)
    for example in examples:
        char_count = len(example.correct_output)
        print(f"  - {example.example_id}: {char_count} chars, category={example.category}")
        assert char_count >= 4000, f"{example.example_id} 长度不足4000字符 (实际:{char_count})"

    # 特别验证综合示例质量 (完整情感分析应≥7000字符,情感内容更深度)
    comprehensive_examples = [ex for ex in examples if ex.category == "comprehensive_mode"]
    for ex in comprehensive_examples:
        char_count = len(ex.correct_output)
        assert char_count >= 7000, f"完整报告示例 {ex.example_id} 应≥7000字符 (实际:{char_count})"


def test_targeted_emotional_journey_relevance_matching():
    """测试情绪旅程类查询的示例匹配"""
    loader = FewShotExampleLoader()

    # 模拟情绪旅程相关查询
    user_request = "职场压力大,希望家能帮助情绪调节,设计情绪旅程"
    matched_examples = loader.get_relevant_examples(
        role_id="V7_0", user_request=user_request, category="targeted_mode", max_examples=2
    )

    print(f"\n✅ 情绪旅程查询匹配到: {[ex.example_id for ex in matched_examples]}")
    assert len(matched_examples) > 0, "情绪旅程关键词应匹配到相关示例"


def test_targeted_psychological_safety_relevance_matching():
    """测试心理安全类查询的示例匹配"""
    loader = FewShotExampleLoader()

    # 模拟心理安全相关查询
    user_request = "独居女性,需要安全感,心理安全基地分析"
    matched_examples = loader.get_relevant_examples(
        role_id="V7_0", user_request=user_request, category="targeted_mode", max_examples=2
    )

    print(f"\n✅ 心理安全查询匹配到: {[ex.example_id for ex in matched_examples]}")
    assert len(matched_examples) > 0, "心理安全关键词应匹配到相关示例"


def test_comprehensive_emotional_insight_relevance_matching():
    """测试完整情感分析查询的示例匹配"""
    loader = FewShotExampleLoader()

    # 模拟完整情感分析查询
    user_request = "三代同堂家庭,希望做完整的情感洞察分析,包含情绪地图和心理安全"
    matched_examples = loader.get_relevant_examples(
        role_id="V7_0", user_request=user_request, category="comprehensive_mode", max_examples=1
    )

    print(f"\n✅ 完整情感分析查询匹配到: {[ex.example_id for ex in matched_examples]}")
    assert len(matched_examples) > 0, "完整关键词应匹配到comprehensive示例"

    # 验证匹配到的是综合示例
    for ex in matched_examples:
        assert ex.category == "comprehensive_mode", "应匹配综合模式示例"


def test_prompt_integration():
    """测试V7_0示例注入到提示词模板"""
    FewShotExampleLoader()
    template = ExpertPromptTemplate(
        role_type="V7_0",
        base_system_prompt="你是一位空间情感洞察专家...",
        autonomy_protocol={"version": "7.0", "level": "emotional_insight"},
    )

    # 模拟情感洞察任务
    task = {
        "step": "step2_task_decomposition",
        "instruction": "分析三代同堂家庭的情感需求",
        "deliverables": [{"item": "情绪地图", "description": "空间情绪旅程分析"}, {"item": "心理安全", "description": "心理安全基地设计"}],
    }

    context = {"family_structure": "三代同堂", "core_need": "情感归属"}

    state = {"user_request": "三代同堂家庭情感分析", "current_step": "step2", "context": context}

    # 渲染prompt
    final_prompt = template.render(dynamic_role_name="情感洞察专家", task_instruction=task, context=context, state=state)

    # 获取system prompt
    system_prompt = final_prompt.get("system_prompt", "")

    print("\n✅ [P2优化] 为 V7_0 注入Few-Shot示例")
    print(f"最终prompt长度: {len(system_prompt)} chars")

    # 验证prompt包含Few-Shot示例
    assert len(system_prompt) > 3000, "Prompt应该包含Few-Shot示例"

    # 验证包含V7_0关键词
    assert "情感" in system_prompt or "心理" in system_prompt or "V7" in system_prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
