"""
测试 V2-2 商业零售设计总监 Few-Shot 示例库

验证内容:
1. 示例文件正确加载
2. 示例质量符合标准(字符数/结构完整性)
3. 相似度匹配逻辑正确性
4. Few-Shot 示例正确注入到prompt中
"""

import unittest
from intelligent_project_analyzer.utils.few_shot_loader import FewShotExampleLoader
from intelligent_project_analyzer.core.prompt_templates import ExpertPromptTemplate


class TestV2_2FewShotExamples(unittest.TestCase):
    """V2-2 商业零售设计总监示例库测试"""

    def setUp(self):
        """初始化测试环境"""
        self.role_id = "V2_2"  # 注意: 使用 V2_2 而非 2-2
        self.loader = FewShotExampleLoader()
        self.examples = self.loader.load_examples_for_role(self.role_id)

    def test_load_v2_2_examples(self):
        """测试 V2-2 示例文件加载"""
        # 应该加载3个示例
        self.assertEqual(len(self.examples), 3, "V2-2应该有3个示例")

        # 验证每个示例的基本结构
        for example in self.examples:
            self.assertTrue(hasattr(example, "example_id"), "示例缺少example_id属性")
            self.assertTrue(hasattr(example, "description"), "示例缺少description属性")
            self.assertTrue(hasattr(example, "category"), "示例缺少category属性")

        # 验证category类型
        categories = [ex.category for ex in self.examples]
        self.assertEqual(categories.count("targeted_mode"), 2, "应该有2个targeted_mode示例")
        self.assertEqual(categories.count("comprehensive_mode"), 1, "应该有1个comprehensive_mode示例")

        # 验证输出内容长度(精品级标准: 5000-8000+字符)
        for example in self.examples:
            output_length = len(example.correct_output)
            self.assertGreater(output_length, 5000, f"示例 {example.example_id} 输出过短: {output_length} chars")
            print(f"✓ {example.example_id}: {output_length} chars")

    def test_targeted_brand_relevance_matching(self):
        """测试针对性问答 - 品牌识别度场景匹配"""
        user_request = "我们的快时尚品牌店铺如何通过设计提升品牌识别度?"

        matched = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="targeted_mode", max_examples=2
        )

        # 应该匹配到品牌识别度相关示例
        matched_ids = [ex.example_id for ex in matched]
        print(f"品牌识别度场景匹配到: {matched_ids}")

        # 验证至少匹配到v2_2_targeted_brand_001
        self.assertTrue(any("brand" in ex_id for ex_id in matched_ids), f"应该匹配到品牌识别度示例,实际匹配: {matched_ids}")

    def test_targeted_balance_relevance_matching(self):
        """测试针对性问答 - 体验坪效平衡场景匹配"""
        user_request = "精品咖啡店如何平衡顾客体验和商业坪效?"

        matched = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="targeted_mode", max_examples=2
        )

        # 应该匹配到体验坪效平衡示例
        matched_ids = [ex.example_id for ex in matched]
        print(f"体验坪效平衡场景匹配到: {matched_ids}")

        # 验证至少匹配到v2_2_targeted_balance_002
        self.assertTrue(any("balance" in ex_id for ex_id in matched_ids), f"应该匹配到体验坪效平衡示例,实际匹配: {matched_ids}")

    def test_comprehensive_flagship_relevance_matching(self):
        """测试完整报告 - 旗舰店设计场景匹配"""
        user_request = "为运动品牌在上海淮海路设计300平米旗舰店,需要完整方案"

        matched = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="comprehensive_mode", max_examples=2
        )

        # 应该匹配到旗舰店完整设计示例
        matched_ids = [ex.example_id for ex in matched]
        print(f"旗舰店完整设计场景匹配到: {matched_ids}")

        # 验证至少匹配到v2_2_comprehensive_flagship_003
        self.assertTrue(any("flagship" in ex_id for ex_id in matched_ids), f"应该匹配到旗舰店设计示例,实际匹配: {matched_ids}")

    def test_prompt_integration(self):
        """测试Few-Shot示例正确注入到prompt中"""
        # 构造测试场景
        user_request = "咖啡店如何平衡体验与坪效?"

        # 获取匹配的示例
        self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="targeted_mode", max_examples=1
        )

        # 创建prompt模板
        template = ExpertPromptTemplate(
            role_type="V2_2", base_system_prompt="你是商业零售设计总监", autonomy_protocol={"version": "4.0", "level": "standard"}
        )

        # 渲染prompt (使用state字典而非DesignState对象)
        state = {
            "original_user_request": user_request,
            "project_context": user_request,
            "current_stage": "design_direction",
        }

        result = template.render(
            state=state,
            dynamic_role_name="商业零售设计总监",
            task_instruction={"task_type": "targeted_analysis", "focus": "体验与坪效平衡设计"},
            context=user_request,
        )

        # 获取system_prompt
        system_prompt = result.get("system_prompt", "")

        # 验证Few-Shot示例是否注入
        self.assertIn("Few-Shot", system_prompt, "Prompt中应包含Few-Shot示例")

        # 验证prompt长度合理(有Few-Shot注入应该较长)
        prompt_length = len(system_prompt)
        self.assertGreater(prompt_length, 5000, f"包含Few-Shot的prompt应该较长,当前长度: {prompt_length}")

        print(f"✅ Few-Shot注入成功, Prompt总长度: {prompt_length} chars")


if __name__ == "__main__":
    unittest.main()
