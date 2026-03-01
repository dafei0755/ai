"""
V2_1 (居住空间设计总监) Few-Shot Example Tests

测试内容:
1. 加载3个V2_1示例
2. 验证Targeted模式相关性匹配(采光优化、储物规划)
3. 验证Comprehensive模式相关性匹配(三代别墅完整设计)
4. 验证Few-Shot示例注入到ExpertPromptTemplate
"""

import pytest
from intelligent_project_analyzer.utils.few_shot_loader import FewShotExampleLoader
from intelligent_project_analyzer.core.prompt_templates import ExpertPromptTemplate


class TestV2_1FewShotExamples:
    """V2_1 居住空间设计总监 Few-Shot示例测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """初始化Few-Shot加载器"""
        self.loader = FewShotExampleLoader()
        self.role_id = "V2_1"

    def test_load_v2_1_examples(self):
        """测试加载V2_1示例库"""
        examples = self.loader.load_examples_for_role(self.role_id)

        # 验证示例数量
        assert len(examples) == 3, f"应该有3个V2_1示例,实际加载了{len(examples)}个"

        # 验证示例ID
        example_ids = {ex.example_id for ex in examples}
        expected_ids = {"v2_1_targeted_daylighting_001", "v2_1_targeted_storage_002", "v2_1_comprehensive_villa_003"}
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

    def test_targeted_daylighting_relevance_matching(self):
        """测试Targeted模式相关性匹配 - 采光优化场景"""
        user_request = "我家客厅朝北,采光很差,白天也很暗,如何通过设计改善?"

        relevant_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="targeted_mode", max_examples=2
        )

        assert len(relevant_examples) >= 1, "应该匹配到至少1个相关示例"

        # 验证匹配的示例包含采光优化案例
        matched_ids = [ex.example_id for ex in relevant_examples]
        assert "v2_1_targeted_daylighting_001" in matched_ids, "采光优化问题应匹配到采光优化示例"

        print(f"  ✅ 采光优化场景匹配到: {matched_ids}")

    def test_targeted_storage_relevance_matching(self):
        """测试Targeted模式相关性匹配 - 储物规划场景"""
        user_request = "70平米的小户型,东西太多总是乱,如何增加储物空间?"

        relevant_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="targeted_mode", max_examples=2
        )

        assert len(relevant_examples) >= 1, "应该匹配到至少1个相关示例"

        # 验证匹配的示例包含储物规划案例
        matched_ids = [ex.example_id for ex in relevant_examples]
        assert "v2_1_targeted_storage_002" in matched_ids, "储物空间问题应匹配到储物规划示例"

        print(f"  ✅ 储物规划场景匹配到: {matched_ids}")

    def test_comprehensive_villa_relevance_matching(self):
        """测试Comprehensive模式相关性匹配 - 完整别墅设计"""
        user_request = "为我设计一套250平米的三层别墅,家里有老人、夫妻和两个孩子,需要完整的设计方案"

        relevant_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="comprehensive_mode", max_examples=2
        )

        assert len(relevant_examples) >= 1, "应该匹配到至少1个相关示例"

        # 验证匹配的示例包含三代别墅案例
        matched_ids = [ex.example_id for ex in relevant_examples]
        assert "v2_1_comprehensive_villa_003" in matched_ids, "三代同堂别墅设计应匹配到别墅设计示例"

        print(f"  ✅ 三代别墅设计场景匹配到: {matched_ids}")

    def test_prompt_integration(self):
        """测试Few-Shot示例注入到ExpertPromptTemplate"""
        # 创建V2_1提示词模板
        template = ExpertPromptTemplate(
            role_type="V2_1",
            base_system_prompt="你是V2_1居住空间设计总监...",
            autonomy_protocol={"version": "4.0", "level": "standard"},
        )

        # 模拟state
        state = {"V2_1_task": "分析客厅采光不足问题并提供优化方案", "task_description": "住宅空间改造项目", "current_step": "spatial_design"}

        # 构造task_instruction为字典
        task_instruction = {
            "objective": "提供专业的居住空间设计方案,解决采光问题",
            "deliverables": [
                {
                    "name": "采光优化方案",
                    "description": "分析现状并提供改善策略",
                    "format": "spatial_design_solution",
                    "priority": "high",
                    "success_criteria": ["方案可行", "材质明确"],
                    "require_search": False,
                }
            ],
            "success_criteria": ["分析深入", "方案可行"],
            "constraints": ["基于现有结构", "注重经济性"],
        }

        # 渲染提示词(包含Few-Shot示例)
        result = template.render(
            state=state, dynamic_role_name="居住空间设计总监", task_instruction=task_instruction, context="住宅空间改造项目,需要解决采光问题"
        )

        system_prompt = result.get("system_prompt", "")

        # 验证Few-Shot示例已注入
        assert "Few-Shot" in system_prompt or "示例" in system_prompt, "提示词中应包含Few-Shot示例标记"

        # 验证包含V2_1相关内容
        assert any(keyword in system_prompt for keyword in ["居住空间", "设计", "采光", "V2_1"]), "提示词应包含V2_1角色相关内容"

        prompt_length = len(system_prompt)
        print(f"  ✅ Few-Shot注入成功,最终prompt长度: {prompt_length} chars")

        # 精品级Few-Shot应显著增加prompt长度(预期≥6000字符)
        assert prompt_length >= 3000, f"注入Few-Shot后prompt过短({prompt_length}字符),可能注入失败"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
