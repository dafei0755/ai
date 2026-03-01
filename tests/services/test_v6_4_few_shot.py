"""
测试 V6_4 成本与价值工程师 Few-Shot Examples
"""

import pytest
from intelligent_project_analyzer.utils.few_shot_loader import FewShotExampleLoader
from intelligent_project_analyzer.core.prompt_templates import ExpertPromptTemplate


def test_load_v6_4_examples():
    """测试V6_4示例加载"""
    loader = FewShotExampleLoader()
    examples = loader.load_examples_for_role("V6_4")

    # 应该有3个示例
    assert len(examples) == 3, f"应加载3个V6_4示例,实际{len(examples)}个"

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


def test_targeted_estimation_relevance_matching():
    """测试成本估算类问题的示例匹配"""
    loader = FewShotExampleLoader()

    # 成本估算相关查询
    query = "办公楼项目大概需要多少投资?"
    matched = loader.get_relevant_examples(role_id="V6_4", user_request=query, category="targeted_mode", max_examples=2)

    print(f"\n成本估算查询匹配到: {[ex.example_id for ex in matched]}")
    assert len(matched) > 0, "应该匹配到成本估算类示例"
    # 应该匹配到估算示例
    matched_ids = [ex.example_id for ex in matched]
    assert any("estimation" in mid for mid in matched_ids), "应匹配到成本估算示例"


def test_targeted_ve_relevance_matching():
    """测试价值工程类问题的示例匹配"""
    loader = FewShotExampleLoader()

    # 价值工程相关查询
    query = "项目超支了,如何优化成本?"
    matched = loader.get_relevant_examples(role_id="V6_4", user_request=query, category="targeted_mode", max_examples=2)

    print(f"\n价值工程查询匹配到: {[ex.example_id for ex in matched]}")
    assert len(matched) > 0, "应该匹配到价值工程示例"
    # 应该匹配到VE示例
    matched_ids = [ex.example_id for ex in matched]
    assert any("ve" in mid for mid in matched_ids), "应匹配到价值工程示例"


def test_comprehensive_cost_relevance_matching():
    """测试完整成本分析问题的示例匹配"""
    loader = FewShotExampleLoader()

    # 完整方案查询
    query = "商业项目需要完整的成本与价值工程分析"
    matched = loader.get_relevant_examples(
        role_id="V6_4", user_request=query, category="comprehensive_mode", max_examples=2
    )

    print(f"\n完整成本方案查询匹配到: {matched[0].example_id if matched else 'None'}")
    assert len(matched) > 0, "应该匹配到完整成本分析示例"
    # 应该匹配到完整分析示例
    matched_ids = [ex.example_id for ex in matched]
    assert any("comprehensive" in mid or "commercial" in mid for mid in matched_ids), "应匹配到完整成本分析示例"


def test_prompt_integration():
    """测试Few-Shot示例集成到prompt"""
    FewShotExampleLoader()
    template = ExpertPromptTemplate(
        role_type="V6_4",
        base_system_prompt="你是一位成本与价值工程师...",
        autonomy_protocol={"version": "6.0", "level": "standard"},
    )

    # 模拟V6_4任务
    task = {
        "step": "step2_task_decomposition",
        "instruction": "分析项目造价和成本优化方案",
        "deliverables": [{"item": "成本估算", "description": "项目总投资估算"}],
    }

    context = {"project_type": "办公楼", "building_area": "2万㎡"}

    state = {"user_request": "办公楼造价估算", "current_step": "step2", "context": context}

    # 渲染prompt
    final_prompt = template.render(dynamic_role_name="成本与价值工程师", task_instruction=task, context=context, state=state)

    # 获取system prompt
    system_prompt = final_prompt.get("system_prompt", "")

    # 验证prompt包含Few-Shot示例
    print(f"\n最终prompt长度: {len(system_prompt)} chars")
    assert len(system_prompt) > 3000, "Prompt应该包含Few-Shot示例"

    # 验证包含V6_4关键词
    assert "成本" in system_prompt or "价值工程" in system_prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
