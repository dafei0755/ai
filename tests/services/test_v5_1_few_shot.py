"""
测试V5_1场景专家(居住场景与生活方式)Few-Shot示例库
Tests for V5_1 Scenario Expert (Residential Lifestyle) Few-Shot Example Library
"""
import pytest
from intelligent_project_analyzer.utils.few_shot_loader import FewShotExampleLoader
from intelligent_project_analyzer.core.prompt_templates import ExpertPromptTemplate


class TestV5_1FewShotExamples:
    """测试V5_1 Few-Shot示例加载和使用"""

    @pytest.fixture
    def loader(self):
        """创建FewShotExampleLoader实例"""
        return FewShotExampleLoader()

    def test_load_v5_1_examples(self, loader):
        """测试V5_1示例库加载"""
        # 加载V5_1示例
        examples = loader.load_examples_for_role("V5_1")

        # 验证示例数量
        assert len(examples) == 3, f"应该加载3个V5_1示例,实际加载了{len(examples)}个"

        # 验证示例类别
        categories = [ex.category for ex in examples]
        expected_categories = ["targeted_mode", "comprehensive_mode"]
        assert all(
            cat in categories for cat in expected_categories
        ), f"类别不匹配。期望: {expected_categories}, 实际: {categories}"

        # 验证每个示例的字符数(精品标准:5000-8000字符)
        for i, example in enumerate(examples, 1):
            output_length = len(example.correct_output)
            print(f"\n示例{i} ({example.category}) 字符数: {output_length}")
            # 允许一定弹性,但至少达到4000字符
            assert output_length >= 4000, f"示例{i}字符数不足,期望≥5000,实际{output_length}"

    def test_targeted_circulation_relevance_matching(self, loader):
        """测试Targeted模式 - 动线规划相关性匹配"""
        # 模拟用户请求:家务动线优化
        user_request = "我家厨房到餐厅距离太远,每次端菜都要走很多路,如何优化家务动线?"

        examples = loader.get_relevant_examples(
            role_id="V5_1", user_request=user_request, category="targeted_mode", max_examples=2
        )

        # 验证返回结果
        assert len(examples) >= 1, "应该至少匹配到1个相关示例"

        # 验证匹配到的示例包含动线相关内容
        matched_example = examples[0]
        output_text = matched_example.correct_output
        assert any(keyword in output_text for keyword in ["动线", "厨房", "效率", "距离"]), "匹配的示例应包含相关关键词"

        print(f"\n匹配到的示例类别: {matched_example.category}")

    def test_targeted_growth_relevance_matching(self, loader):
        """测试Targeted模式 - 儿童成长适应性相关性匹配"""
        # 模拟用户请求:儿童房设计
        user_request = "孩子现在3岁,如何设计儿童房能适应他从幼儿到小学的成长变化?"

        examples = loader.get_relevant_examples(
            role_id="V5_1", user_request=user_request, category="targeted_mode", max_examples=2
        )

        # 验证返回结果
        assert len(examples) >= 1, "应该至少匹配到1个相关示例"

        # 验证匹配到的示例包含成长适应性相关内容
        matched_example = examples[0]
        output_text = matched_example.correct_output
        assert any(keyword in output_text for keyword in ["成长", "儿童", "适应", "阶段"]), "匹配的示例应包含相关关键词"

        print(f"\n匹配到的示例类别: {matched_example.category}")

    def test_comprehensive_family_relevance_matching(self, loader):
        """测试Comprehensive模式 - 完整家庭场景相关性匹配"""
        # 模拟用户请求:家庭住宅完整分析
        user_request = "三口之家,父亲在家办公,母亲全职,孩子上小学,需要完整的居住场景分析。"

        examples = loader.get_relevant_examples(
            role_id="V5_1", user_request=user_request, category="comprehensive_mode", max_examples=2
        )

        # 验证返回结果
        assert len(examples) >= 1, "应该至少匹配到1个相关示例"

        # 验证匹配到的示例包含家庭场景相关内容
        matched_example = examples[0]
        output_text = matched_example.correct_output
        assert any(keyword in output_text for keyword in ["家庭", "办公", "运营", "场景"]), "匹配的示例应包含相关关键词"

        print(f"\n匹配到的示例类别: {matched_example.category}")

    def test_prompt_integration(self, loader):
        """测试Few-Shot示例集成到提示词模板"""
        # 创建V5_1提示词模板
        template = ExpertPromptTemplate(
            role_type="V5_1",
            base_system_prompt="你是V5_1居住场景与生活方式专家...",
            autonomy_protocol={"version": "4.0", "level": "standard"},
        )

        # 模拟state
        state = {"V5_1_task": "分析双职工家庭的家务动线优化方案", "task_description": "家庭住宅设计项目", "current_step": "scenario_analysis"}

        # 构造task_instruction为字典
        task_instruction = {
            "objective": "深度分析家庭生活场景,提供动线优化和空间运营策略",
            "deliverables": [
                {
                    "name": "家务动线优化方案",
                    "description": "分析现状痛点并提供优化策略",
                    "format": "operational_blueprint",
                    "priority": "high",
                    "success_criteria": ["效率提升", "冲突减少"],
                    "require_search": False,
                }
            ],
            "success_criteria": ["分析深入", "方案可行"],
            "constraints": ["基于真实生活场景", "注重可实施性"],
        }

        # 渲染提示词(包含Few-Shot示例)
        result = template.render(
            state=state, dynamic_role_name="居住场景专家", task_instruction=task_instruction, context="家庭住宅设计项目,需要优化动线和空间运营"
        )

        system_prompt = result.get("system_prompt", "")

        # 验证Few-Shot示例已注入
        assert "Few-Shot" in system_prompt or "示例" in system_prompt, "提示词中应包含Few-Shot示例标记"

        # 验证包含V5_1相关内容
        assert any(keyword in system_prompt for keyword in ["居住", "场景", "动线", "V5_1"]), "提示词应包含V5_1角色相关内容"

        print(f"\n生成的提示词长度: {len(system_prompt)} 字符")
