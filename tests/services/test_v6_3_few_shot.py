"""
测试 V6_3 室内工艺与材料专家 Few-Shot Examples
"""

import pytest
from intelligent_project_analyzer.utils.few_shot_loader import FewShotExampleLoader
from intelligent_project_analyzer.core.prompt_templates import ExpertPromptTemplate


def test_load_v6_3_examples():
    """测试V6_3示例加载"""
    loader = FewShotExampleLoader()
    examples = loader.load_examples_for_role("V6_3")

    # 应该有3个示例
    assert len(examples) == 3, f"应加载3个V6_3示例,实际{len(examples)}个"

    # 检查示例分类
    categories = [ex.category for ex in examples]
    assert categories.count("targeted_mode") == 2, f"应有2个targeted示例,实际{categories.count('targeted_mode')}个"
    assert (
        categories.count("comprehensive_mode") == 1
    ), f"应有1个comprehensive示例,实际{categories.count('comprehensive_mode')}个"

    # 检查示例长度(高质量标准)
    for example in examples:
        char_count = len(example.correct_output)
        print(f"\n✅ 示例 {example.example_id}: {char_count} chars")
        assert char_count >= 4000, f"示例{example.example_id}质量不达标: {char_count} < 4000 chars"


def test_targeted_material_relevance_matching():
    """测试材料选型类问题的示例匹配"""
    loader = FewShotExampleLoader()

    # 材料选型相关查询
    query = "民宿项目如何选择墙面材料体现侘寂美学?"
    matched = loader.get_relevant_examples(role_id="V6_3", user_request=query, category="targeted_mode", max_examples=2)

    print(f"\n材料选型查询匹配到: {[ex.example_id for ex in matched]}")
    assert len(matched) > 0, "应该匹配到材料选型类示例"
    # 应该匹配到材料选型示例
    matched_ids = [ex.example_id for ex in matched]
    assert any("material" in mid for mid in matched_ids), "应匹配到材料选型示例"


def test_targeted_craftsmanship_relevance_matching():
    """测试工艺节点类问题的示例匹配"""
    loader = FewShotExampleLoader()

    # 工艺节点相关查询
    query = "无踢脚线墙地收口怎么施工?"
    matched = loader.get_relevant_examples(role_id="V6_3", user_request=query, category="targeted_mode", max_examples=2)

    print(f"\n工艺节点查询匹配到: {[ex.example_id for ex in matched]}")
    assert len(matched) > 0, "应该匹配到工艺节点示例"
    # 应该匹配到工艺节点示例
    matched_ids = [ex.example_id for ex in matched]
    assert any("node" in mid for mid in matched_ids), "应匹配到工艺节点示例"


def test_comprehensive_interior_relevance_matching():
    """测试完整室内工艺分析问题的示例匹配"""
    loader = FewShotExampleLoader()

    # 完整方案查询
    query = "精品酒店需要完整的室内工艺与材料技术方案"
    matched = loader.get_relevant_examples(
        role_id="V6_3", user_request=query, category="comprehensive_mode", max_examples=2
    )

    print(f"\n完整工艺方案查询匹配到: {matched[0].example_id if matched else 'None'}")
    assert len(matched) > 0, "应该匹配到完整工艺分析示例"
    # 应该匹配到完整分析示例
    matched_ids = [ex.example_id for ex in matched]
    assert any("comprehensive" in mid or "boutique" in mid for mid in matched_ids), "应匹配到完整工艺分析示例"


def test_prompt_integration():
    """测试Few-Shot示例集成到prompt"""
    FewShotExampleLoader()
    template = ExpertPromptTemplate(
        role_type="V6_3",
        base_system_prompt="你是一位室内工艺与材料专家...",
        autonomy_protocol={"version": "6.0", "level": "standard"},
    )

    # 模拟V6_3任务
    task = {
        "step": "step2_task_decomposition",
        "instruction": "分析民宿项目的墙面材料选型",
        "deliverables": [{"item": "材料对比分析", "description": "对比不同墙面材料的优劣"}],
    }

    context = {"design_intent": "侘寂美学,追求自然手工感"}

    state = {"user_request": "民宿墙面材料选型", "current_step": "step2", "context": context}

    # 渲染prompt
    final_prompt = template.render(dynamic_role_name="室内工艺与材料专家", task_instruction=task, context=context, state=state)

    # 获取system prompt
    system_prompt = final_prompt.get("system_prompt", "")

    # 验证prompt包含Few-Shot示例
    print(f"\n最终prompt长度: {len(system_prompt)} chars")
    assert len(system_prompt) > 3000, "Prompt应该包含Few-Shot示例"

    # 验证包含V6_3关键词
    assert "室内工艺" in system_prompt or "材料选型" in system_prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
