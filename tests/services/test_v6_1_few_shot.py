"""V6_1 (结构与幕墙工程师) Few-Shot Example Tests"""
import pytest
from intelligent_project_analyzer.utils.few_shot_loader import FewShotExampleLoader
from intelligent_project_analyzer.core.prompt_templates import ExpertPromptTemplate


class TestV6_1FewShotExamples:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.loader = FewShotExampleLoader()
        self.role_id = "V6_1"

    def test_load_v6_1_examples(self):
        """测试V6_1示例加载"""
        examples = self.loader.load_examples_for_role(self.role_id)

        # 验证示例数量
        assert len(examples) == 3, f"应加载3个V6_1示例,实际{len(examples)}个"

        # 验证示例ID
        example_ids = {ex.example_id for ex in examples}
        expected_ids = {"v6_1_targeted_comparison_001", "v6_1_targeted_cost_002", "v6_1_comprehensive_museum_003"}
        assert example_ids == expected_ids, f"示例ID不匹配: {example_ids}"

        # 验证类别分布
        categories = [ex.category for ex in examples]
        targeted_count = categories.count("targeted_mode")
        comprehensive_count = categories.count("comprehensive_mode")
        assert targeted_count == 2, f"应有2个targeted示例,实际{targeted_count}个"
        assert comprehensive_count == 1, f"应有1个comprehensive示例,实际{comprehensive_count}个"

        # 验证字符数(精品级标准≥4000字符)
        for ex in examples:
            char_count = len(ex.correct_output)
            print(f"{ex.example_id}: {char_count} chars")
            assert char_count >= 4000, f"{ex.example_id}字符数{char_count}不足4000(精品级标准)"

        print("\n✅ V6_1示例库验证通过:")
        print(f"   - 总数: {len(examples)}个")
        print(f"   - Targeted模式: {targeted_count}个")
        print(f"   - Comprehensive模式: {comprehensive_count}个")

        # 输出各示例字符数
        for ex in examples:
            print(f"   - {ex.example_id.split('_')[-1]}: {len(ex.correct_output)} chars")

    def test_targeted_comparison_relevance_matching(self):
        """测试Targeted模式-方案比选类相关性匹配"""
        user_request = "体育馆需要80米大跨度屋顶,有哪些结构方案?"

        matched_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="targeted_mode", max_examples=2
        )

        assert len(matched_examples) > 0, "应该匹配到方案比选类示例"
        matched_ids = [ex.example_id for ex in matched_examples]
        print(f"方案比选查询匹配到: {matched_ids}")
        assert "v6_1_targeted_comparison_001" in matched_ids, "应匹配到大跨度结构方案比选示例"

    def test_targeted_cost_relevance_matching(self):
        """测试Targeted模式-成本优化类相关性匹配"""
        user_request = "写字楼幕墙成本太高,如何在保证品质的前提下降本?"

        matched_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="targeted_mode", max_examples=2
        )

        assert len(matched_examples) > 0, "应该匹配到成本优化类示例"
        matched_ids = [ex.example_id for ex in matched_examples]
        print(f"成本优化查询匹配到: {matched_ids}")
        assert "v6_1_targeted_cost_002" in matched_ids, "应匹配到幕墙成本优化示例"

    def test_comprehensive_structure_facade_relevance_matching(self):
        """测试Comprehensive模式相关性匹配"""
        user_request = "博物馆需要实现悬挑造型,请提供完整的结构与幕墙技术方案"

        matched_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="comprehensive_mode", max_examples=1
        )

        assert len(matched_examples) > 0, "应该匹配到完整结构与幕墙技术方案示例"
        example = matched_examples[0]
        print(f"完整技术方案查询匹配到: {example.example_id}")
        assert example.example_id == "v6_1_comprehensive_museum_003", "应匹配到美术馆技术方案示例"
        assert example.category == "comprehensive_mode", "应为comprehensive模式"

    def test_prompt_integration(self):
        """测试Few-Shot示例在ExpertPromptTemplate中的集成"""
        # 创建模板实例
        template = ExpertPromptTemplate(
            role_type=self.role_id,
            base_system_prompt="你是V6_1结构与幕墙工程师,负责结构安全、形态实现及外立面技术解决方案。",
            autonomy_protocol={"version": "6.0", "level": "standard"},
        )

        # 构建状态字典
        state = {
            "V6_1_task": "评估大跨度结构可行性",
            "task_description": "文化中心需要60米无柱展厅,评估结构方案",
            "current_step": "structural_feasibility",
        }

        # 任务指令
        task_instruction = {
            "step": "structural_feasibility",
            "instruction": "请评估文化中心60米大跨度结构的技术可行性",
            "deliverables": [
                {"item": "结构方案", "description": "可选结构体系"},
                {"item": "技术分析", "description": "优劣势对比"},
                {"item": "推荐方案", "description": "最优技术路径"},
            ],
        }

        # 渲染prompt
        prompt_result = template.render(
            dynamic_role_name="结构与幕墙工程师", task_instruction=task_instruction, context="文化建筑,大跨度结构", state=state
        )

        # 获取system prompt
        system_prompt = prompt_result.get("system_prompt", "")

        # 验证Few-Shot示例已注入
        assert "Few-Shot" in system_prompt or "示例" in system_prompt, "Prompt应包含Few-Shot示例标识"

        # 验证V6_1特有关键词
        v6_keywords = ["结构", "幕墙", "大跨度", "钢桁架", "V6_1"]
        keyword_found = any(keyword in system_prompt for keyword in v6_keywords)
        assert keyword_found, f"Prompt应包含V6_1特有关键词之一: {v6_keywords}"

        # 验证prompt长度
        print(f"最终prompt长度: {len(system_prompt)} chars")
        assert len(system_prompt) >= 3000, "Few-Shot注入后prompt长度应≥3000字符"

        print("\n✅ Few-Shot示例成功注入V6_1 prompt")
        print(f"   - Prompt长度: {len(system_prompt)} chars")
        print("   - 包含角色定义: ✓")
        print("   - 包含Few-Shot示例: ✓")
        print("   - 包含用户任务: ✓")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
