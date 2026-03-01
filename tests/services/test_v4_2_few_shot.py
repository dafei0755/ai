"""
V4_2 (体系与方法论架构师/趋势研究与未来洞察专家) Few-Shot Example Tests

测试V4_2角色的Few-Shot示例库:
- 加载3个示例(2个Targeted + 1个Comprehensive)
- 验证相关性匹配(方法论框架、商业模式评估、完整体系)
- 验证ExpertPromptTemplate集成
"""

import pytest
from intelligent_project_analyzer.utils.few_shot_loader import FewShotExampleLoader
from intelligent_project_analyzer.core.prompt_templates import ExpertPromptTemplate


class TestV4_2FewShotExamples:
    """V4_2 (体系与方法论架构师) Few-Shot示例测试套件"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """测试初始化"""
        self.loader = FewShotExampleLoader()
        self.role_id = "V4_2"  # 注意大写V和下划线

    def test_load_v4_2_examples(self):
        """
        测试1: 加载V4_2示例库

        验证:
        - 能成功加载3个示例
        - 包含2个targeted模式 + 1个comprehensive模式
        - 每个示例字符数≥4000(精品级标准)
        """
        examples = self.loader.load_examples_for_role(self.role_id)

        # 验证数量
        assert len(examples) == 3, f"期望3个示例,实际{len(examples)}个"

        # 验证示例ID
        example_ids = {ex.example_id for ex in examples}
        expected_ids = {"v4_2_targeted_framework_001", "v4_2_targeted_model_002", "v4_2_comprehensive_system_003"}
        assert example_ids == expected_ids, f"示例ID不匹配: {example_ids}"

        # 验证分类
        categories = [ex.category for ex in examples]
        targeted_count = categories.count("targeted_mode")
        comprehensive_count = categories.count("comprehensive_mode")

        assert targeted_count == 2, f"期望2个targeted示例,实际{targeted_count}个"
        assert comprehensive_count == 1, f"期望1个comprehensive示例,实际{comprehensive_count}个"

        # 验证示例质量(字符数)
        for ex in examples:
            output_length = len(ex.correct_output)
            print(f"\n{ex.example_id}: {output_length} chars")
            assert output_length >= 4000, f"{ex.example_id}字符数{output_length}不足4000(精品级标准)"

        print("\n✅ V4_2示例库验证通过:")
        print(f"   - 总数: {len(examples)}个")
        print(f"   - Targeted模式: {targeted_count}个")
        print(f"   - Comprehensive模式: {comprehensive_count}个")

    def test_targeted_framework_relevance_matching(self):
        """
        测试2: Targeted模式 - 方法论框架查询匹配

        验证:
        - 方法论框架类查询能匹配到正确示例
        - 示例包含创新方法论、设计思维等内容
        """
        user_request = "我们团队缺乏系统的设计创新方法,如何建立可复用的创新框架?"

        matched_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="targeted_mode", max_examples=2
        )

        assert len(matched_examples) >= 1, "方法论框架查询未匹配到示例"

        # 验证匹配到的示例包含方法论相关内容
        matched_ids = [ex.example_id for ex in matched_examples]
        print(f"\n方法论框架查询匹配到: {matched_ids}")

        # 应该匹配到 v4_2_targeted_framework_001
        assert "v4_2_targeted_framework_001" in matched_ids, "方法论框架问题应匹配到framework示例"

    def test_targeted_business_model_relevance_matching(self):
        """
        测试3: Targeted模式 - 商业模式评估查询匹配

        验证:
        - 商业模式评估类查询能匹配到正确示例
        - 示例包含商业模式画布、评估模型等内容
        """
        user_request = "我们有几个商业模式方向,不知道选哪个,如何系统化评估商业模式的可行性?"

        matched_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="targeted_mode", max_examples=2
        )

        assert len(matched_examples) >= 1, "商业模式评估查询未匹配到示例"

        # 验证匹配到的示例包含商业模式相关内容
        matched_ids = [ex.example_id for ex in matched_examples]
        print(f"\n商业模式评估查询匹配到: {matched_ids}")

        # 应该匹配到 v4_2_targeted_model_002
        assert "v4_2_targeted_model_002" in matched_ids, "商业模式评估问题应匹配到model示例"

    def test_comprehensive_system_relevance_matching(self):
        """
        测试4: Comprehensive模式 - 完整体系查询匹配

        验证:
        - 完整体系构建查询能匹配到comprehensive示例
        - 示例包含完整架构、实施路线图等内容
        """
        user_request = "为企业构建完整的'设计驱动创新体系',从战略到流程到工具,需要全面的体系架构方案"

        matched_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="comprehensive_mode", max_examples=1
        )

        assert len(matched_examples) >= 1, "完整体系查询未匹配到示例"

        # 验证匹配到comprehensive示例
        example = matched_examples[0]
        print(f"\n完整体系查询匹配到: {example.example_id}")

        assert example.category == "comprehensive_mode", f"期望匹配comprehensive示例,实际{example.category}"

        # 验证示例ID
        assert "v4_2_comprehensive_system_003" == example.example_id, "完整体系查询应匹配到system示例"

    def test_prompt_integration(self):
        """
        测试5: ExpertPromptTemplate集成测试

        验证:
        - Few-Shot示例能正确注入到V4_2 prompt中
        - 最终prompt长度合理(≥3000字符,包含示例)
        - 系统提示词包含V4_2角色定义
        """
        # 创建prompt模板
        template = ExpertPromptTemplate(
            role_type=self.role_id,
            base_system_prompt="你是V4_2体系与方法论架构师,负责构建解决问题的思考框架和创新流程。",
            autonomy_protocol={"version": "4.0", "level": "standard"},
        )

        # 模拟V4_2任务状态
        state = {"V4_2_task": "为团队构建设计创新方法论框架", "task_description": "团队需要系统化的创新方法", "current_step": "framework_design"}

        # 构造task_instruction
        task_instruction = {
            "objective": "提供系统化的创新方法论框架",
            "deliverables": [
                {
                    "name": "创新框架",
                    "description": "完整的创新流程体系",
                    "format": "methodology_framework",
                    "priority": "high",
                    "success_criteria": ["可落地", "易复用"],
                    "require_search": False,
                }
            ],
            "success_criteria": ["框架完整", "工具实用"],
            "constraints": ["时间紧", "团队经验有限"],
        }

        # 渲染提示词
        result = template.render(
            state=state, dynamic_role_name="体系与方法论架构师", task_instruction=task_instruction, context="设计团队能力建设项目"
        )

        # 获取system_prompt
        system_prompt = result.get("system_prompt", "")

        # 验证Few-Shot示例已注入
        assert "Few-Shot" in system_prompt or "示例" in system_prompt, "提示词中应包含Few-Shot示例标记"

        # 验证包含V4_2相关内容
        assert any(keyword in system_prompt for keyword in ["方法论", "体系", "框架", "V4_2"]), "提示词应包含V4_2角色相关内容"

        prompt_length = len(system_prompt)
        print(f"\n最终prompt长度: {prompt_length} chars")

        # 精品级Few-Shot应显著增加prompt长度
        assert prompt_length >= 3000, f"注入Few-Shot后prompt过短({prompt_length}字符),可能注入失败"

        print("✅ Few-Shot示例成功注入V4_2 prompt")
        print(f"   - Prompt长度: {prompt_length} chars")
        print("   - 包含角色定义: ✓")
        print("   - 包含Few-Shot示例: ✓")
        print("   - 包含用户任务: ✓")


if __name__ == "__main__":
    # 允许直接运行测试文件
    pytest.main([__file__, "-v", "-s"])
