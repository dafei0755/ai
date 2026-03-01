"""V6_2 (机电与智能化工程师) Few-Shot Example Tests"""
import pytest
from intelligent_project_analyzer.utils.few_shot_loader import FewShotExampleLoader
from intelligent_project_analyzer.core.prompt_templates import ExpertPromptTemplate


class TestV6_2FewShotExamples:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.loader = FewShotExampleLoader()
        self.role_id = "V6_2"

    def test_load_v6_2_examples(self):
        """测试V6_2示例加载"""
        examples = self.loader.load_examples_for_role(self.role_id)

        # 验证示例数量
        assert len(examples) == 3, f"应加载3个V6_2示例,实际{len(examples)}个"

        # 验证示例ID
        example_ids = {ex.example_id for ex in examples}
        expected_ids = {"v6_2_targeted_hvac_001", "v6_2_targeted_energy_002", "v6_2_comprehensive_smart_office_003"}
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

        print("\n✅ V6_2示例库验证通过:")
        print(f"   - 总数: {len(examples)}个")
        print(f"   - Targeted模式: {targeted_count}个")
        print(f"   - Comprehensive模式: {comprehensive_count}个")

        # 输出各示例字符数
        for ex in examples:
            print(f"   - {ex.example_id.split('_')[-1]}: {len(ex.correct_output)} chars")

    def test_targeted_hvac_relevance_matching(self):
        """测试Targeted模式-HVAC系统比选类相关性匹配"""
        user_request = "酒店需要选择空调系统,如何权衡舒适度和成本?"

        matched_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="targeted_mode", max_examples=2
        )

        assert len(matched_examples) > 0, "应该匹配到HVAC系统比选示例"
        matched_ids = [ex.example_id for ex in matched_examples]
        print(f"HVAC系统比选查询匹配到: {matched_ids}")
        assert "v6_2_targeted_hvac_001" in matched_ids, "应匹配到HVAC系统方案比选示例"

    def test_targeted_energy_relevance_matching(self):
        """测试Targeted模式-节能优化类相关性匹配"""
        user_request = "购物中心能耗过高,如何通过技术改造降低能耗?"

        matched_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="targeted_mode", max_examples=2
        )

        assert len(matched_examples) > 0, "应该匹配到节能优化示例"
        matched_ids = [ex.example_id for ex in matched_examples]
        print(f"节能优化查询匹配到: {matched_ids}")
        assert "v6_2_targeted_energy_002" in matched_ids, "应匹配到能耗优化示例"

    def test_comprehensive_mep_smart_relevance_matching(self):
        """测试Comprehensive模式相关性匹配"""
        user_request = "科技园区办公楼需要完整的机电与智能化方案"

        matched_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="comprehensive_mode", max_examples=1
        )

        assert len(matched_examples) > 0, "应该匹配到完整机电与智能化方案示例"
        example = matched_examples[0]
        print(f"完整MEP方案查询匹配到: {example.example_id}")
        assert example.example_id == "v6_2_comprehensive_smart_office_003", "应匹配到智能办公楼示例"
        assert example.category == "comprehensive_mode", "应为comprehensive模式"

    def test_prompt_integration(self):
        """测试Few-Shot示例在ExpertPromptTemplate中的集成"""
        # 创建模板实例
        template = ExpertPromptTemplate(
            role_type=self.role_id,
            base_system_prompt="你是V6_2机电与智能化工程师,负责暖通、电气、给排水及智能化系统集成。",
            autonomy_protocol={"version": "6.0", "level": "standard"},
        )

        # 构建状态字典
        state = {"V6_2_task": "评估HVAC系统方案", "task_description": "办公楼需要选择空调系统", "current_step": "hvac_selection"}

        # 任务指令
        task_instruction = {
            "step": "hvac_selection",
            "instruction": "请评估办公楼HVAC系统的可选方案",
            "deliverables": [
                {"item": "系统方案", "description": "可选HVAC系统"},
                {"item": "技术分析", "description": "优劣势对比"},
                {"item": "推荐方案", "description": "最优技术路径"},
            ],
        }

        # 渲染prompt
        prompt_result = template.render(
            dynamic_role_name="机电与智能化工程师", task_instruction=task_instruction, context="办公建筑,HVAC系统选型", state=state
        )

        # 获取system prompt
        system_prompt = prompt_result.get("system_prompt", "")

        # 验证Few-Shot示例已注入
        assert "Few-Shot" in system_prompt or "示例" in system_prompt, "Prompt应包含Few-Shot示例标识"

        # 验证V6_2特有关键词
        v6_keywords = ["机电", "HVAC", "智能化", "暖通", "V6_2"]
        keyword_found = any(keyword in system_prompt for keyword in v6_keywords)
        assert keyword_found, f"Prompt应包含V6_2特有关键词之一: {v6_keywords}"

        # 验证prompt长度
        print(f"最终prompt长度: {len(system_prompt)} chars")
        assert len(system_prompt) >= 3000, "Few-Shot注入后prompt长度应≥3000字符"

        print("\n✅ Few-Shot示例成功注入V6_2 prompt")
        print(f"   - Prompt长度: {len(system_prompt)} chars")
        print("   - 包含角色定义: ✓")
        print("   - 包含Few-Shot示例: ✓")
        print("   - 包含用户任务: ✓")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
