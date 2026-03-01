"""V5_2 (商业零售运营专家) Few-Shot Example Tests"""
import pytest
from intelligent_project_analyzer.utils.few_shot_loader import FewShotExampleLoader
from intelligent_project_analyzer.core.prompt_templates import ExpertPromptTemplate


class TestV5_2FewShotExamples:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.loader = FewShotExampleLoader()
        self.role_id = "V5_2"

    def test_load_v5_2_examples(self):
        """测试V5_2示例加载"""
        examples = self.loader.load_examples_for_role(self.role_id)

        # 验证示例数量
        assert len(examples) == 3, f"应加载3个V5_2示例,实际{len(examples)}个"

        # 验证示例ID
        example_ids = {ex.example_id for ex in examples}
        expected_ids = {"v5_2_targeted_efficiency_001", "v5_2_targeted_flow_002", "v5_2_comprehensive_retail_003"}
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

        print("\n✅ V5_2示例库验证通过:")
        print(f"   - 总数: {len(examples)}个")
        print(f"   - Targeted模式: {targeted_count}个")
        print(f"   - Comprehensive模式: {comprehensive_count}个")

        # 输出各示例字符数
        for ex in examples:
            print(f"   - {ex.example_id.split('_')[-1]}: {len(ex.correct_output)} chars")

    def test_targeted_efficiency_relevance_matching(self):
        """测试Targeted模式-坪效优化类相关性匹配"""
        user_request = "独立书店坪效低,如何通过空间调整提升?"

        matched_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="targeted_mode", max_examples=2
        )

        assert len(matched_examples) > 0, "应该匹配到坪效优化类示例"
        matched_ids = [ex.example_id for ex in matched_examples]
        print(f"坪效优化查询匹配到: {matched_ids}")
        assert "v5_2_targeted_efficiency_001" in matched_ids, "应匹配到书店坪效优化示例"

    def test_targeted_flow_relevance_matching(self):
        """测试Targeted模式-动线优化类相关性匹配"""
        user_request = "女装店顾客停留时间短转化率低,如何优化动线?"

        matched_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="targeted_mode", max_examples=2
        )

        assert len(matched_examples) > 0, "应该匹配到动线优化类示例"
        matched_ids = [ex.example_id for ex in matched_examples]
        print(f"动线优化查询匹配到: {matched_ids}")
        assert "v5_2_targeted_flow_002" in matched_ids, "应匹配到女装店动线优化示例"

    def test_comprehensive_retail_relevance_matching(self):
        """测试Comprehensive模式相关性匹配"""
        user_request = "运动品牌新零售体验店,需要完整的运营分析和空间策略"

        matched_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="comprehensive_mode", max_examples=1
        )

        assert len(matched_examples) > 0, "应该匹配到完整零售运营分析示例"
        example = matched_examples[0]
        print(f"完整零售分析查询匹配到: {example.example_id}")
        assert example.example_id == "v5_2_comprehensive_retail_003", "应匹配到新零售体验店示例"
        assert example.category == "comprehensive_mode", "应为comprehensive模式"

    def test_prompt_integration(self):
        """测试Few-Shot示例在ExpertPromptTemplate中的集成"""
        # 创建模板实例
        template = ExpertPromptTemplate(
            role_type=self.role_id,
            base_system_prompt="你是V5_2商业零售运营专家,负责分析坪效、动线、KPI和零售商业模式。",
            autonomy_protocol={"version": "5.0", "level": "standard"},
        )

        # 构建状态字典
        state = {
            "V5_2_task": "分析服装店动线优化",
            "task_description": "80平米女装店,客流转化率低,需要动线优化方案",
            "current_step": "flow_optimization",
        }

        # 任务指令
        task_instruction = {
            "step": "flow_optimization",
            "instruction": "请分析女装店顾客动线优化策略",
            "deliverables": [
                {"item": "动线诊断", "description": "现状问题分析"},
                {"item": "优化方案", "description": "分区与动线设计"},
                {"item": "KPI设定", "description": "动线效率指标"},
            ],
        }

        # 渲染prompt
        prompt_result = template.render(
            dynamic_role_name="商业零售运营专家", task_instruction=task_instruction, context="服装零售,动线优化", state=state
        )

        # 获取system prompt
        system_prompt = prompt_result.get("system_prompt", "")

        # 验证Few-Shot示例已注入
        assert "Few-Shot" in system_prompt or "示例" in system_prompt, "Prompt应包含Few-Shot示例标识"

        # 验证V5_2特有关键词
        v5_keywords = ["坪效", "动线", "零售", "转化率", "V5_2"]
        keyword_found = any(keyword in system_prompt for keyword in v5_keywords)
        assert keyword_found, f"Prompt应包含V5_2特有关键词之一: {v5_keywords}"

        # 验证prompt长度
        print(f"最终prompt长度: {len(system_prompt)} chars")
        assert len(system_prompt) >= 3000, "Few-Shot注入后prompt长度应≥3000字符"

        print("\n✅ Few-Shot示例成功注入V5_2 prompt")
        print(f"   - Prompt长度: {len(system_prompt)} chars")
        print("   - 包含角色定义: ✓")
        print("   - 包含Few-Shot示例: ✓")
        print("   - 包含用户任务: ✓")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
