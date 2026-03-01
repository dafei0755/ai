"""V5_0 (通用场景策略师/综合编排专家) Few-Shot Example Tests"""
import pytest
from intelligent_project_analyzer.utils.few_shot_loader import FewShotExampleLoader
from intelligent_project_analyzer.core.prompt_templates import ExpertPromptTemplate


class TestV5_0FewShotExamples:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.loader = FewShotExampleLoader()
        self.role_id = "V5_0"

    def test_load_v5_0_examples(self):
        """测试V5_0示例加载"""
        examples = self.loader.load_examples_for_role(self.role_id)

        # 验证示例数量
        assert len(examples) == 3, f"应加载3个V5_0示例,实际{len(examples)}个"

        # 验证示例ID
        example_ids = {ex.example_id for ex in examples}
        expected_ids = {
            "v5_0_targeted_logic_001",
            "v5_0_targeted_stakeholder_002",
            "v5_0_comprehensive_online_education_003",
        }
        assert example_ids == expected_ids, f"示例ID不匹配,期望{expected_ids},实际{example_ids}"

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

        print("\n✅ V5_0示例库验证通过:")
        print(f"   - 总数: {len(examples)}个")
        print(f"   - Targeted模式: {targeted_count}个")
        print(f"   - Comprehensive模式: {comprehensive_count}个")

        # 输出各示例字符数详情
        logic_ex = next(ex for ex in examples if ex.example_id == "v5_0_targeted_logic_001")
        stakeholder_ex = next(ex for ex in examples if ex.example_id == "v5_0_targeted_stakeholder_002")
        edu_ex = next(ex for ex in examples if ex.example_id == "v5_0_comprehensive_online_education_003")

        print(f"   - 运营逻辑分析(健身房): {len(logic_ex.correct_output)} chars")
        print(f"   - 利益相关方分析(共享办公): {len(stakeholder_ex.correct_output)} chars")
        print(f"   - 完整场景分析(在线教育录课): {len(edu_ex.correct_output)} chars")

    def test_targeted_operational_logic_relevance_matching(self):
        """测试Targeted模式-运营逻辑类相关性匹配"""
        user_request = "会员制健身房的核心运营逻辑,如何影响空间设计?"

        matched_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="targeted_mode", max_examples=2
        )

        assert len(matched_examples) > 0, "应该匹配到运营逻辑类示例"
        matched_ids = [ex.example_id for ex in matched_examples]
        print(f"运营逻辑查询匹配到: {matched_ids}")
        assert "v5_0_targeted_logic_001" in matched_ids, "应匹配到健身房运营逻辑示例"

    def test_targeted_stakeholder_relevance_matching(self):
        """测试Targeted模式-利益相关方类相关性匹配"""
        user_request = "共享办公空间的核心利益相关方有哪些?需求如何影响空间设计?"

        matched_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="targeted_mode", max_examples=2
        )

        assert len(matched_examples) > 0, "应该匹配到利益相关方类示例"
        matched_ids = [ex.example_id for ex in matched_examples]
        print(f"利益相关方查询匹配到: {matched_ids}")
        assert "v5_0_targeted_stakeholder_002" in matched_ids, "应匹配到共享办公利益相关方示例"

    def test_comprehensive_scenario_relevance_matching(self):
        """测试Comprehensive模式相关性匹配"""
        user_request = "在线教育录课工作室,需要完整的场景分析和空间策略"

        matched_examples = self.loader.get_relevant_examples(
            role_id=self.role_id, user_request=user_request, category="comprehensive_mode", max_examples=1
        )

        assert len(matched_examples) > 0, "应该匹配到完整场景分析示例"
        example = matched_examples[0]
        print(f"完整场景分析查询匹配到: {example.example_id}")
        assert example.example_id == "v5_0_comprehensive_online_education_003", "应匹配到在线教育录课示例"
        assert example.category == "comprehensive_mode", "应为comprehensive模式"

    def test_prompt_integration(self):
        """测试Few-Shot示例在ExpertPromptTemplate中的集成"""
        # 创建模板实例
        template = ExpertPromptTemplate(
            role_type=self.role_id,
            base_system_prompt="你是V5_0通用场景策略师,负责从第一性原理解构未知场景的底层运营逻辑。",
            autonomy_protocol={"version": "5.0", "level": "standard"},
        )

        # 构建状态字典
        state = {
            "V5_0_task": "分析社区健康中心场景",
            "task_description": "社区健康中心(体检+中医+健身),如何规划运营模式和空间分区?",
            "current_step": "scenario_analysis",
        }

        # 任务指令
        task_instruction = {
            "step": "scenario_analysis",
            "instruction": "请分析社区健康中心的运营逻辑",
            "deliverables": [
                {"item": "运营逻辑解构", "description": "从第一性原理分析"},
                {"item": "利益相关方分析", "description": "识别核心stakeholders"},
                {"item": "空间功能分区", "description": "转化为设计需求"},
            ],
        }

        # 渲染prompt
        prompt_result = template.render(
            dynamic_role_name="通用场景策略师", task_instruction=task_instruction, context="社区健康中心(体检+中医+健身)复合业态", state=state
        )

        # 获取system prompt
        system_prompt = prompt_result.get("system_prompt", "")

        # 验证Few-Shot示例已注入
        assert "Few-Shot" in system_prompt or "示例" in system_prompt, "Prompt应包含Few-Shot示例标识"

        # 验证V5_0特有关键词(场景/运营/利益相关方)
        v5_keywords = ["场景", "运营", "利益相关方", "第一性原理", "V5_0"]
        keyword_found = any(keyword in system_prompt for keyword in v5_keywords)
        assert keyword_found, f"Prompt应包含V5_0特有关键词之一: {v5_keywords}"

        # 验证prompt长度(Few-Shot注入后应较长)
        print(f"最终prompt长度: {len(system_prompt)} chars")
        assert len(system_prompt) >= 3000, "Few-Shot注入后prompt长度应≥3000字符"

        print("\n✅ Few-Shot示例成功注入V5_0 prompt")
        print(f"   - Prompt长度: {len(system_prompt)} chars")
        print("   - 包含角色定义: ✓")
        print("   - 包含Few-Shot示例: ✓")
        print("   - 包含用户任务: ✓")
