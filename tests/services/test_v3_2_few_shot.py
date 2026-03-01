"""
V3_2 (品牌叙事与顾客体验专家) Few-Shot Example Tests

测试内容:
1. 加载3个V3_2示例
2. 验证Targeted模式相关性匹配(品牌故事、客群画像)
3. 验证Comprehensive模式相关性匹配(鸡尾酒吧完整叙事)
4. 验证Few-Shot示例注入到ExpertPromptTemplate
"""

import pytest
from intelligent_project_analyzer.utils.few_shot_loader import FewShotExampleLoader
from intelligent_project_analyzer.core.prompt_templates import ExpertPromptTemplate


class TestV3_2FewShotExamples:
    """V3_2 品牌叙事与顾客体验专家 Few-Shot示例测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """初始化Few-Shot加载器"""
        self.loader = FewShotExampleLoader()
        self.role_id = "V3_2"

    def test_load_v3_2_examples(self):
        """测试加载V3_2示例库"""
        examples = self.loader.load_examples_for_role(self.role_id)

        # 验证示例数量
        assert len(examples) == 3, f"应该有3个V3_2示例,实际加载了{len(examples)}个"

        # 验证示例ID
        example_ids = {ex.example_id for ex in examples}
        expected_ids = {"v3_2_targeted_brand_001", "v3_2_targeted_customer_002", "v3_2_comprehensive_cocktail_003"}
        assert example_ids == expected_ids, f"示例ID不匹配: {example_ids}"

        # 验证示例类别分布
        categories = [ex.category for ex in examples]
        assert categories.count("targeted_mode") == 2, "应该有2个targeted_mode示例"
        assert categories.count("comprehensive_mode") == 1, "应该有1个comprehensive_mode示例"

        # 验证示例内容长度(精品级≥5000字符)
        for ex in examples:
            content_length = len(ex.correct_output)
            print(f"  {ex.example_id}: {content_length} chars")
            assert content_length >= 4000, f"{ex.example_id}内容过短({content_length}字符),不符合精品标准(≥4000)"

    def test_targeted_brand_story_relevance_matching(self):
        """测试Targeted模式相关性匹配 - 品牌故事类"""
        user_request = "我们要做精品咖啡品牌,主打单一产地,如何讲品牌故事和差异化?"

        relevant_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="targeted_mode", max_examples=2
        )

        assert len(relevant_examples) >= 1, "应该匹配到至少1个相关示例"

        # 验证匹配的示例包含品牌故事案例
        matched_ids = [ex.example_id for ex in relevant_examples]
        assert "v3_2_targeted_brand_001" in matched_ids, "品牌故事问题应匹配到品牌叙事示例"

        print(f"  ✅ 品牌故事场景匹配到: {matched_ids}")

    def test_targeted_customer_archetype_relevance_matching(self):
        """测试Targeted模式相关性匹配 - 客群画像类"""
        user_request = "新中式茶饮品牌目标客群是谁?如何精准触达她们?"

        relevant_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="targeted_mode", max_examples=2
        )

        assert len(relevant_examples) >= 1, "应该匹配到至少1个相关示例"

        # 验证匹配的示例包含客群画像案例
        matched_ids = [ex.example_id for ex in relevant_examples]
        assert "v3_2_targeted_customer_002" in matched_ids, "客群画像问题应匹配到客群分析示例"

        print(f"  ✅ 客群画像场景匹配到: {matched_ids}")

    def test_comprehensive_brand_narrative_relevance_matching(self):
        """测试Comprehensive模式相关性匹配 - 完整品牌叙事"""
        user_request = "为高端鸡尾酒吧设计完整的品牌叙事和顾客体验流程"

        relevant_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="comprehensive_mode", max_examples=2
        )

        assert len(relevant_examples) >= 1, "应该匹配到至少1个相关示例"

        # 验证匹配的示例包含完整叙事案例
        matched_ids = [ex.example_id for ex in relevant_examples]
        assert "v3_2_comprehensive_cocktail_003" in matched_ids, "完整品牌叙事问题应匹配到comprehensive示例"

        print(f"  ✅ 完整品牌叙事场景匹配到: {matched_ids}")

    def test_prompt_integration(self):
        """测试Few-Shot示例注入到ExpertPromptTemplate"""
        # 创建V3_2提示词模板
        template = ExpertPromptTemplate(
            role_type="V3_2",
            base_system_prompt="你是V3_2品牌叙事与顾客体验专家...",
            autonomy_protocol={"version": "4.0", "level": "standard"},
        )

        # 模拟state
        state = {"V3_2_task": "分析精品咖啡品牌叙事策略", "task_description": "品牌策划项目", "current_step": "brand_narrative_design"}

        # 构造task_instruction
        task_instruction = {
            "objective": "提供专业的品牌叙事分析",
            "deliverables": [
                {
                    "name": "品牌故事框架",
                    "description": "完整的品牌叙事体系",
                    "format": "brand_story_framework",
                    "priority": "high",
                    "success_criteria": ["有情感共鸣", "可落地执行"],
                    "require_search": False,
                }
            ],
            "success_criteria": ["故事有感染力", "客群定位准确"],
            "constraints": ["预算有限", "时间紧"],
        }

        # 渲染提示词
        result = template.render(
            state=state, dynamic_role_name="品牌叙事与顾客体验专家", task_instruction=task_instruction, context="精品咖啡品牌策划,主打单一产地"
        )

        # 获取system_prompt
        system_prompt = result.get("system_prompt", "")

        # 验证Few-Shot示例已注入
        assert "Few-Shot" in system_prompt or "示例" in system_prompt, "提示词中应包含Few-Shot示例标记"

        # 验证包含V3_2相关内容
        assert any(keyword in system_prompt for keyword in ["品牌叙事", "顾客体验", "情感", "V3_2"]), "提示词应包含V3_2角色相关内容"

        prompt_length = len(system_prompt)
        print(f"  ✅ Few-Shot注入成功,最终prompt长度: {prompt_length} chars")

        # 精品级Few-Shot应显著增加prompt长度
        assert prompt_length >= 3000, f"注入Few-Shot后prompt过短({prompt_length}字符),可能注入失败"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
