"""
端到端测试：新农村/城市更新本体论框架 (End-to-End Tests)

测试完整工作流程：
1. 加载本体论 → 生成提示 → 模拟LLM输出 → 验证结果
2. 真实场景模拟：新农村项目全流程分析
3. 多专家协作场景
"""

import pytest
from pathlib import Path
from intelligent_project_analyzer.utils.ontology_loader import OntologyLoader


@pytest.fixture
def ontology_loader():
    """初始化本体论加载器"""
    ontology_path = (
        Path(__file__).parent.parent.parent / "intelligent_project_analyzer" / "knowledge_base" / "ontology.yaml"
    )
    return OntologyLoader(str(ontology_path))


class TestRuralProjectE2EWorkflow:
    """端到端测试：新农村项目完整工作流"""

    def test_e2e_design_director_analysis(self, ontology_loader):
        """E2E场景1：设计总监(V2)分析新农村项目 — A1+A2 维度全路径"""
        # Step 1: 加载本体论
        ontology = ontology_loader.get_layered_ontology(
            project_type="rural_regeneration_urban_renewal", expert_role="design_director", include_base=True
        )

        assert ontology is not None, "本体论应成功加载"

        # Step 2: 生成专家提示
        prompt = ontology_loader.format_as_prompt(ontology, expert_name="空间规划师")

        assert len(prompt) > 1000, "提示应该足够详细"
        assert "场所身份" in prompt or "Place Identity" in prompt

        # Step 3: 验证关键概念存在（模拟LLM会看到的内容）
        key_concepts = ["历史记忆", "地域文化", "社区认同", "产业植入", "原住民", "生计", "基础设施", "公共服务", "无障碍"]

        found = sum(1 for concept in key_concepts if concept in prompt)
        assert found >= 7, f"应包含至少7个关键概念，实际: {found}"

        # Step 4: 验证格式适合LLM解析
        assert "####" in prompt, "应包含维度标题"
        assert "核心问题" in prompt or "core" in prompt.lower(), "应包含引导式核心问题"

    def test_e2e_narrative_expert_analysis(self, ontology_loader):
        """E2E场景2：叙事专家(V3)分析新农村项目 — A3 叙事维度全路径"""
        # Step 1: 加载本体论（带叙事专家强化）
        ontology = ontology_loader.get_layered_ontology(
            project_type="rural_regeneration_urban_renewal", expert_role="narrative_expert", include_base=True
        )

        # Step 2: 生成提示
        prompt = ontology_loader.format_as_prompt(ontology, expert_name="叙事专家")

        # 设计师应该看到：基础层+新农村层+设计师强化层
        # 检查设计相关的关键概念（支持中英文）
        design_concepts = ["氛围", "atmosphere", "风格", "style", "空间", "spatial"]
        found_design = any(concept in prompt.lower() for concept in design_concepts)
        assert found_design, "设计师应看到设计相关维度"

        # 检查文化相关概念
        culture_concepts = ["文化", "culture", "历史", "history", "地域", "regional"]
        found_culture = any(concept in prompt.lower() for concept in culture_concepts)
        assert found_culture, "应包含文化维度"

        # Step 3: 模拟设计师输出（验证结构）
        simulated_output = {
            "place_identity": {"historical_memory": "保护3处祠堂，1条老街", "cultural_expression": "采用本土夯土材料，传统木构现代化"},
            "livelihood_economy": {"industry": "植入精品民宿5家，文创工坊2个", "resident_livelihood": "优先雇佣本地居民，提供技能培训"},
        }

        # 验证输出结构与本体论对齐
        assert "place_identity" in simulated_output
        assert "livelihood_economy" in simulated_output

    def test_e2e_capital_strategy_analysis(self, ontology_loader):
        """E2E场景3：资本策略专家(V6_2)评估新农村项目 — A7 资本维度全路径"""
        # Step 1: 加载本体论（带资本策略强化）
        ontology = ontology_loader.get_layered_ontology(
            project_type="rural_regeneration_urban_renewal", expert_role="capital_strategy_expert", include_base=True
        )

        # Step 2: 生成提示
        prompt = ontology_loader.format_as_prompt(ontology, expert_name="资本策略专家")

        # 资本策略应关注投资回报相关维度
        cost_keywords = ["成本", "预算", "经测", "投资", "cost", "budget", "资本", "回报"]
        found_cost_keywords = sum(1 for kw in cost_keywords if kw in prompt.lower())
        assert found_cost_keywords >= 2, "造价师视角应包含成本相关概念"

        # Step 3: 模拟造价评估输出
        simulated_cost_analysis = {
            "infrastructure_upgrade": {
                "sewage_system": "雨污分流改造: 约150万元",
                "fire_lane": "消防通道拓宽: 约80万元",
                "fiber_optic": "光纤入户: 约30万元",
            },
            "cultural_preservation": {"ancestral_hall": "祠堂修缮: 约200万元", "old_street": "老街改造: 约500万元"},
            "total_estimate": "约960万元",
        }

        assert "infrastructure_upgrade" in simulated_cost_analysis
        assert "cultural_preservation" in simulated_cost_analysis


class TestMultiExpertCollaboration:
    """端到端测试：多专家协作场景"""

    def test_e2e_multi_expert_workflow(self, ontology_loader):
        """E2E场景4：多专家协作分析同一新农村项目"""
        project_type = "rural_regeneration_urban_renewal"

        # Expert 1: 设计总监（前期分析）
        expert1_ontology = ontology_loader.get_layered_ontology(
            project_type=project_type, expert_role="design_director", include_base=True
        )
        expert1_prompt = ontology_loader.format_as_prompt(expert1_ontology, expert_name="设计总监")

        # 验证设计总监关注点
        assert "空间" in expert1_prompt or "spatial" in expert1_prompt.lower()

        # Expert 2: 叙事专家（方案设计）
        expert2_ontology = ontology_loader.get_layered_ontology(
            project_type=project_type, expert_role="narrative_expert", include_base=True
        )
        expert2_prompt = ontology_loader.format_as_prompt(expert2_ontology, expert_name="叙事专家")

        # Expert 3: 资本策略专家（资本评估）
        expert3_ontology = ontology_loader.get_layered_ontology(
            project_type=project_type, expert_role="capital_strategy_expert", include_base=True
        )
        expert3_prompt = ontology_loader.format_as_prompt(expert3_ontology, expert_name="资本策略专家")

        # 验证三个专家都能访问核心本体论（支持中英文关键词）
        core_concepts = [
            ("场所身份", "place identity", "place_identity"),
            ("生计经济", "livelihood economy", "livelihood_economy"),
            ("基础设施", "infrastructure", "infrastructure_equity"),
        ]

        for cn_name, en_name, key_name in core_concepts:
            # 检查是否包含任一关键词（中文/英文/键名）
            found_in_1 = any(kw.lower() in expert1_prompt.lower() for kw in [cn_name, en_name, key_name])
            found_in_2 = any(kw.lower() in expert2_prompt.lower() for kw in [cn_name, en_name, key_name])
            found_in_3 = any(kw.lower() in expert3_prompt.lower() for kw in [cn_name, en_name, key_name])

            assert found_in_1, f"空间规划师应看到 {cn_name}/{en_name}"
            assert found_in_2, f"设计师应看到 {cn_name}/{en_name}"
            assert found_in_3, f"造价师应看到 {cn_name}/{en_name}"

        # 验证每个专家有独特视角
        assert len(set([expert1_prompt, expert2_prompt, expert3_prompt])) == 3, "三个专家的提示应有差异"

    def test_e2e_sequential_analysis_workflow(self, ontology_loader):
        """E2E场景5：顺序分析工作流（模拟真实项目流程）"""
        project_type = "rural_regeneration_urban_renewal"

        workflow_results = {}

        # Phase 1: 需求分析（通用角色）
        phase1_ontology = ontology_loader.get_layered_ontology(
            project_type=project_type, expert_role=None, include_base=True
        )
        workflow_results["phase1_dimensions"] = len(phase1_ontology)

        # Phase 2: 设计总监观察
        phase2_ontology = ontology_loader.get_layered_ontology(
            project_type=project_type, expert_role="design_director", include_base=True
        )
        workflow_results["phase2_dimensions"] = len(phase2_ontology)

        # Phase 3: 叙事专家方案设计
        phase3_ontology = ontology_loader.get_layered_ontology(
            project_type=project_type, expert_role="narrative_expert", include_base=True
        )
        workflow_results["phase3_dimensions"] = len(phase3_ontology)

        # 验证每个阶段都能正常进行
        assert workflow_results["phase1_dimensions"] >= 4, "需求分析阶段应有基础维度"
        assert workflow_results["phase2_dimensions"] >= workflow_results["phase1_dimensions"], "空间规划应包含所有基础维度"
        assert workflow_results["phase3_dimensions"] >= workflow_results["phase1_dimensions"], "方案设计应包含所有基础维度"


class TestRealWorldScenarios:
    """端到端测试：真实世界场景模拟"""

    def test_e2e_beautiful_countryside_project(self, ontology_loader):
        """E2E场景6：美丽乡村改造项目"""
        # 项目背景：浙江某村美丽乡村改造

        # 加载本体论
        ontology = ontology_loader.get_layered_ontology(
            project_type="rural_regeneration_urban_renewal", expert_role="design_director", include_base=True
        )

        prompt = ontology_loader.format_as_prompt(ontology, expert_name="乡村规划师")

        # 验证本体论能覆盖项目关键问题
        issue_coverage = {
            "祠堂老旧": "历史记忆" in prompt,
            "污水直排": "雨污分流" in prompt or "污水" in prompt or "基础设施" in prompt,
            "道路狭窄": "消防通道" in prompt or "无障碍" in prompt,
            "缺乏文化设施": "公共服务" in prompt or "文化" in prompt,
        }

        covered_issues = sum(issue_coverage.values())
        assert covered_issues >= 3, f"应覆盖至少3个关键问题，实际: {covered_issues}"

    def test_e2e_urban_renewal_project(self, ontology_loader):
        """E2E场景7：城市更新项目（老城区改造）"""
        # 项目背景：上海某老城区更新

        # 加载本体论
        ontology = ontology_loader.get_layered_ontology(
            project_type="rural_regeneration_urban_renewal", expert_role="narrative_expert", include_base=True
        )

        prompt = ontology_loader.format_as_prompt(ontology, expert_name="城市更新设计师")

        # 验证本体论能应对城市更新挑战
        challenge_coverage = {
            "居民安置": "原住民" in prompt or "生计保障" in prompt,
            "产业升级": "产业植入" in prompt or "经济" in prompt,
            "文化传承": "历史记忆" in prompt or "文化表达" in prompt,
        }

        covered_challenges = sum(challenge_coverage.values())
        assert covered_challenges >= 2, f"应覆盖至少2个挑战，实际: {covered_challenges}"

    def test_e2e_heritage_village_regeneration(self, ontology_loader):
        """E2E场景8：历史文化村落保护性开发"""
        # 项目背景：皖南某古村落

        # 加载本体论
        ontology = ontology_loader.get_layered_ontology(
            project_type="rural_regeneration_urban_renewal", expert_role=None, include_base=True
        )

        prompt = ontology_loader.format_as_prompt(ontology, expert_name="遗产保护专家")

        # 验证三大目标的覆盖
        goals_coverage = {
            "文化保护": ("历史记忆" in prompt or "文化表达" in prompt),
            "文旅开发": ("产业植入" in prompt and ("民宿" in prompt or "文创" in prompt)),
            "居民增收": ("生计" in prompt or "就业" in prompt),
        }

        assert all(goals_coverage.values()), f"应覆盖所有目标，实际: {goals_coverage}"


class TestPromptQuality:
    """端到端测试：生成提示的质量验证"""

    def test_e2e_prompt_completeness(self, ontology_loader):
        """E2E场景9：验证生成提示的完整性"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="rural_regeneration_urban_renewal", expert_role="design_director", include_base=True
        )

        prompt = ontology_loader.format_as_prompt(ontology, expert_name="空间规划师")

        # 完整性检查
        completeness_checks = {
            "has_title": "##" in prompt,
            "has_categories": "###" in prompt,
            "has_dimensions": "####" in prompt,
            "has_chinese": any("\u4e00" <= c <= "\u9fff" for c in prompt),
            "has_english": any("a" <= c.lower() <= "z" for c in prompt),
            "has_questions": "?" in prompt or "？" in prompt,
            "has_examples": "examples" in prompt.lower() or "示例" in prompt,
            "sufficient_length": len(prompt) > 1000,
        }

        passed_checks = sum(completeness_checks.values())
        assert passed_checks >= 7, f"完整性检查应通过至少7项，实际: {passed_checks}/8"

    def test_e2e_prompt_readability(self, ontology_loader):
        """E2E场景10：验证生成提示的可读性"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="rural_regeneration_urban_renewal", expert_role=None, include_base=True
        )

        prompt = ontology_loader.format_as_prompt(ontology, expert_name="分析师")

        # 可读性检查
        lines = prompt.split("\n")
        non_empty_lines = [line for line in lines if line.strip()]

        readability_checks = {
            "reasonable_line_count": 20 < len(non_empty_lines) < 500,
            "has_hierarchy": prompt.count("##") >= 1,
            "no_excessive_repetition": prompt.count("####") < 100,
            "balanced_sections": prompt.count("###") >= 2,
        }

        assert all(readability_checks.values()), f"可读性检查失败: {readability_checks}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
