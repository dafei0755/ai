"""
V3_1 个体叙事与心理洞察专家 - Few-Shot示例库测试
测试示例加载、匹配与提示词集成功能
"""
import pytest
from intelligent_project_analyzer.utils.few_shot_loader import get_few_shot_loader
from intelligent_project_analyzer.core.prompt_templates import ExpertPromptTemplate


class TestV3_1FewShotExamples:
    """测试V3_1示例库"""

    @pytest.fixture
    def loader(self):
        """获取FewShotLoader实例"""
        return get_few_shot_loader()

    def test_load_v3_1_examples(self, loader):
        """测试加载V3_1所有示例"""
        examples = loader.load_examples_for_role("V3_1")

        # 验证示例数量
        assert len(examples) == 3, f"应该有3个示例，实际加载了{len(examples)}个"

        # 验证示例类别
        categories = [ex.category for ex in examples]
        expected_categories = ["targeted_mode", "comprehensive_mode"]
        assert all(
            cat in categories for cat in expected_categories
        ), f"类别不匹配。期望: {expected_categories}, 实际: {categories}"

        # 验证示例字符数（精品标准: 5000-8000字符/示例）
        for idx, example in enumerate(examples, 1):
            output_str = example.correct_output
            char_count = len(output_str)
            print(f"\n示例{idx} ({example.category}) 字符数: {char_count}")
            assert char_count >= 3000, f"示例{idx}字符数过少（{char_count}），不符合精品标准"

    def test_targeted_psychological_relevance_matching(self, loader):
        """测试Targeted模式 - 心理洞察类的相关性匹配"""
        # 模拟用户请求：独居青年的空间需求
        user_request = "为一个30岁的独居女性设计50平米的小公寓，她是一名设计师。"

        examples = loader.get_relevant_examples(
            role_id="V3_1", user_request=user_request, category="targeted_mode", max_examples=2
        )

        # 验证返回结果
        assert len(examples) >= 1, "应该至少匹配到1个相关示例"

        # 验证匹配到的示例包含独居女性相关内容
        matched_example = examples[0]
        output_text = matched_example.correct_output
        assert any(keyword in output_text for keyword in ["独居", "女性", "设计师", "心理"]), "匹配的示例应包含相关关键词"

        print(f"\n匹配到的示例类别: {matched_example.category}")

    def test_targeted_lifestyle_relevance_matching(self, loader):
        """测试Targeted模式 - 生活方式类的相关性匹配"""
        # 模拟用户请求：三代同堂家庭空间
        user_request = "为一个三代同堂的家庭设计住宅，包括老人、中年夫妇和孩子。"

        examples = loader.get_relevant_examples(
            role_id="V3_1", user_request=user_request, category="targeted_mode", max_examples=2
        )

        # 验证返回结果
        assert len(examples) >= 1, "应该至少匹配到1个相关示例"

        # 验证匹配到的示例包含三代同堂相关内容
        matched_example = examples[0]
        output_text = matched_example.correct_output
        assert any(keyword in output_text for keyword in ["家庭", "父母", "儿童", "生活"]), "匹配的示例应包含相关关键词"

        print(f"\n匹配到的示例类别: {matched_example.category}")

    def test_comprehensive_narrative_relevance_matching(self, loader):
        """测试Comprehensive模式 - 完整叙事的相关性匹配"""
        # 模拟用户请求：咖啡馆业主的创业梦想
        user_request = "为一位想开咖啡馆的创业者设计40平米的独立咖啡馆，她希望体现慢生活理念。"

        examples = loader.get_relevant_examples(
            role_id="V3_1", user_request=user_request, category="comprehensive_mode", max_examples=2
        )

        # 验证返回结果
        assert len(examples) >= 1, "应该至少匹配到1个相关示例"

        # 验证匹配到的示例包含咖啡馆/创业相关内容
        matched_example = examples[0]
        output_text = matched_example.correct_output
        assert any(keyword in output_text for keyword in ["咖啡", "业主", "叙事", "慢"]), "匹配的示例应包含相关关键词"

        print(f"\n匹配到的示例类别: {matched_example.category}")

    def test_prompt_integration(self, loader):
        """测试Few-Shot示例集成到提示词模板"""
        # 创建V3_1提示词模板
        template = ExpertPromptTemplate(
            role_type="V3_1",
            base_system_prompt="你是V3_1个体叙事与心理洞察专家...",
            autonomy_protocol={"version": "4.0", "level": "standard"},
        )

        # 模拟state
        state = {"V3_1_task": "为一个28岁的独居女性设计心理画像", "task_description": "小公寓设计项目", "analysis_mode": "targeted"}

        # 构造task_instruction为字典
        task_instruction = {
            "objective": "深度分析目标用户的心理需求与空间期待",
            "deliverables": [
                {
                    "name": "人物画像分析",
                    "description": "构建目标用户的心理画像和生活方式叙事",
                    "format": "targeted_narrative",
                    "priority": "high",
                    "success_criteria": ["心理深度", "场景真实"],
                    "require_search": False,
                }
            ],
            "success_criteria": ["分析深入", "洞察准确"],
            "constraints": ["基于真实场景", "注重心理层面"],
        }

        # 渲染提示词（包含Few-Shot示例）
        result = template.render(
            state=state, dynamic_role_name="个体叙事专家", task_instruction=task_instruction, context="小公寓设计项目,用户为28岁独居女性"
        )

        system_prompt = result.get("system_prompt", "")

        # 验证Few-Shot示例已注入
        assert "Few-Shot" in system_prompt or "示例" in system_prompt, "提示词中应包含Few-Shot示例标记"

        # 验证包含V3_1相关内容
        assert any(keyword in system_prompt for keyword in ["心理", "叙事", "个体", "V3_1"]), "提示词应包含V3_1角色相关内容"

        print(f"\n生成的提示词长度: {len(system_prompt)} 字符")
        print("Few-Shot示例已成功集成到提示词中")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
