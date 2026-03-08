"""
测试动态本体论分层注入机制 (Layered Injection Architecture Tests)

测试覆盖：
1. 三层架构的独立加载
2. 层级合并逻辑
3. 格式化输出
4. 边界情况处理
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


class TestLayeredArchitecture:
    """测试分层架构的基础功能"""

    def test_base_layer_loading(self, ontology_loader):
        """测试基础层（meta_framework）加载"""
        meta = ontology_loader.get_meta_framework()

        assert meta is not None, "基础层应该存在"
        assert isinstance(meta, dict), "基础层应该是字典"
        assert len(meta) > 0, "基础层应该包含维度"

        # 验证基础层包含通用维度
        assert "universal_dimensions" in meta, "基础层应包含 universal_dimensions"
        assert len(meta["universal_dimensions"]) >= 3, "通用维度应包含多个维度项"

    def test_project_type_layer_loading(self, ontology_loader):
        """测试项目类型层加载"""
        personal = ontology_loader.get_ontology_by_type("personal_residential")

        assert personal is not None, "个人住宅框架应该存在"
        assert isinstance(personal, dict), "项目类型层应该是字典"
        assert len(personal) > 0, "项目类型层应该包含维度"

        # 验证项目类型层包含特定维度
        expected_categories = ["spiritual_world", "social_coordinates", "material_life"]
        for category in expected_categories:
            assert category in personal, f"个人住宅框架应包含 {category}"

    def test_expert_enhancement_available(self, ontology_loader):
        """测试专家强化层可用性"""
        expert_roles = ontology_loader.get_available_expert_roles()

        assert len(expert_roles) > 0, "应该有可用的专家强化层"

        # 验证关键专家有强化层（键名对齐 V2-V7 role_id 提取结果）
        expected_experts = ["design_director", "narrative_expert", "capital_strategy_expert"]
        for expert in expected_experts:
            assert expert in expert_roles, f"专家 {expert} 应该有强化层"


class TestLayeredInjection:
    """测试分层注入的核心逻辑"""

    def test_single_layer_base_only(self, ontology_loader):
        """测试只注入基础层"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="meta_framework", expert_role=None, include_base=True
        )

        assert ontology is not None, "应该返回本体论"
        assert len(ontology) > 0, "应该包含维度"

        # 基础层应该被加载
        assert "universal_dimensions" in ontology, "应包含universal_dimensions"

    def test_two_layers_base_plus_type(self, ontology_loader):
        """测试基础层 + 项目类型层"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="personal_residential", expert_role=None, include_base=True
        )

        # 应该同时包含基础层和项目类型层的维度
        assert "universal_dimensions" in ontology, "应包含基础层维度"
        assert "spiritual_world" in ontology, "应包含项目类型层维度"

    def test_three_layers_full_injection(self, ontology_loader):
        """测试完整三层注入：基础层 + 项目类型层 + 专家强化层"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="personal_residential", expert_role="design_director", include_base=True
        )

        # 应该包含所有三层
        assert "universal_dimensions" in ontology, "应包含基础层"
        assert "spiritual_world" in ontology, "应包含项目类型层"
        assert "expert_enhancement" in ontology, "应包含专家强化层"

        # 验证专家强化层内容
        expert_dims = ontology["expert_enhancement"]
        assert len(expert_dims) > 0, "专家强化层应包含维度"

        # 验证设计总监(A1+A2)的特定维度
        dim_names = [d.get("name") for d in expert_dims]
        assert any("空间组织" in name or "设计概念" in name for name in dim_names), "应包含设计总监特定维度"

    def test_expert_without_enhancement(self, ontology_loader):
        """测试没有强化层的专家"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="personal_residential", expert_role="nonexistent_expert", include_base=True
        )

        # 应该正常返回基础层和项目类型层
        assert "universal_dimensions" in ontology
        assert "spiritual_world" in ontology

        # 不应该有专家强化层（或为空）
        assert "expert_enhancement" not in ontology or len(ontology.get("expert_enhancement", [])) == 0

    def test_skip_base_layer(self, ontology_loader):
        """测试跳过基础层"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="personal_residential", expert_role=None, include_base=False
        )

        # 不应包含基础层维度
        assert "universal_dimensions" not in ontology or len(ontology.get("universal_dimensions", [])) == 0

        # 应该包含项目类型层
        assert "spiritual_world" in ontology


class TestDimensionMerging:
    """测试维度合并的正确性"""

    def test_dimensions_not_duplicated(self, ontology_loader):
        """测试维度不会重复"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="personal_residential", expert_role="design_director", include_base=True
        )

        # 遍历每个分类，检查维度数量
        for category, dimensions in ontology.items():
            if isinstance(dimensions, list):
                dim_names = [d.get("name") for d in dimensions]
                # 不应有重复的维度名
                assert len(dim_names) == len(set(dim_names)), f"分类 {category} 中维度名不应重复"

    def test_dimension_structure_preserved(self, ontology_loader):
        """测试维度结构被正确保留"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="commercial_enterprise", expert_role="capital_strategy_expert", include_base=True
        )

        # 验证每个维度的结构
        for category, dimensions in ontology.items():
            if isinstance(dimensions, list):
                for dim in dimensions:
                    assert "name" in dim, "维度应包含 'name' 字段"
                    assert "description" in dim, "维度应包含 'description' 字段"
                    # ask_yourself 和 examples 是可选的，但如果存在应该是字符串
                    if "ask_yourself" in dim:
                        assert isinstance(dim["ask_yourself"], str)
                    if "examples" in dim:
                        assert isinstance(dim["examples"], str)


class TestPromptFormatting:
    """测试提示文本格式化"""

    def test_format_as_prompt_basic(self, ontology_loader):
        """测试基础格式化功能"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="personal_residential", expert_role=None, include_base=True
        )

        prompt_text = ontology_loader.format_as_prompt(ontology, expert_name="空间规划师")

        assert prompt_text is not None, "应该返回文本"
        assert len(prompt_text) > 0, "文本不应为空"
        assert "空间规划师" in prompt_text, "应包含专家名称"
        assert "##" in prompt_text, "应包含Markdown标题"

    def test_format_empty_ontology(self, ontology_loader):
        """测试空本体论的格式化"""
        prompt_text = ontology_loader.format_as_prompt({}, expert_name="测试专家")

        assert prompt_text == "", "空本体论应返回空字符串"

    def test_format_includes_all_categories(self, ontology_loader):
        """测试格式化包含所有分类"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="commercial_enterprise", expert_role=None, include_base=False
        )

        prompt_text = ontology_loader.format_as_prompt(ontology)

        # 验证关键分类出现在文本中
        for category in ontology.keys():
            # 分类名会被转换（下划线变空格，首字母大写）
            assert category.replace("_", " ").lower() in prompt_text.lower(), f"应包含分类 {category}"


class TestEdgeCases:
    """测试边界情况和错误处理"""

    def test_nonexistent_project_type(self, ontology_loader):
        """测试不存在的项目类型"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="nonexistent_type", expert_role=None, include_base=True
        )

        # 应该至少包含基础层
        assert "universal_dimensions" in ontology

    def test_multiple_project_types_loading(self, ontology_loader):
        """测试多个项目类型可用"""
        project_types = ontology_loader.get_available_project_types()

        assert len(project_types) >= 4, "应该有多个项目类型"
        assert "personal_residential" in project_types
        assert "commercial_enterprise" in project_types
        assert "meta_framework" not in project_types, "meta_framework不应出现在项目类型列表中"


class TestRealWorldScenarios:
    """测试真实世界场景"""

    def test_scenario_design_director(self, ontology_loader):
        """场景1：设计总监(V2)分析个人住宅 — 验证 A1+A2 维度注入"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="personal_residential", expert_role="design_director", include_base=True
        )

        assert len(ontology) > 0, "应该返回合并的本体论"

        # 应该有设计总监的 A1+A2 特定维度
        assert "expert_enhancement" in ontology, "design_director 应触发专家强化层"
        expert_dims = ontology["expert_enhancement"]
        dim_names = [d.get("name") for d in expert_dims]
        assert any("设计概念" in name or "空间组织" in name for name in dim_names), "应包含 A1 设计概念或 A2 空间组织维度"

    def test_scenario_chief_engineer(self, ontology_loader):
        """场景2：总工程师(V6)进行商业项目规划 — 验证 A2 实现侧维度注入"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="commercial_enterprise", expert_role="chief_engineer", include_base=True
        )

        # 应该同时有商业项目维度和空间规划维度
        assert "business_positioning" in ontology, "应包含商业定位维度"
        if "expert_enhancement" in ontology:
            expert_dims = ontology["expert_enhancement"]
            assert len(expert_dims) > 0, "总工程师应有强化维度"

    def test_scenario_generic_expert(self, ontology_loader):
        """场景3：通用专家（无强化层）"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="healthcare_wellness", expert_role=None, include_base=True
        )

        # 应该包含基础层和项目类型层
        assert "universal_dimensions" in ontology
        assert "care_philosophy" in ontology or len(ontology) > 1, "应包含医疗养老特定维度"

    def test_scenario_formatted_prompt_length(self, ontology_loader):
        """场景4：验证格式化后的提示文本长度合理"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="personal_residential", expert_role="narrative_expert", include_base=True
        )

        prompt_text = ontology_loader.format_as_prompt(ontology, expert_name="叙事专家")

        # 验证文本长度在合理范围（至少500字符，不超过50000字符）
        assert len(prompt_text) > 500, "提示文本应该包含足够内容"
        assert len(prompt_text) < 50000, "提示文本不应过长"

        # 验证包含关键Markdown格式
        assert prompt_text.count("##") >= 1, "应包含主标题"
        assert prompt_text.count("###") >= 1, "应包含分类标题"
        assert prompt_text.count("####") >= 3, "应包含多个维度"


class TestNewFrameworks:
    """测试新增项目类型框架（v3.1扩充）"""

    def test_rural_regeneration_framework_exists(self, ontology_loader):
        """测试新农村/美丽乡村/城市更新框架存在"""
        rural = ontology_loader.get_ontology_by_type("rural_regeneration_urban_renewal")

        assert rural is not None, "新农村/城市更新框架应该存在"
        assert isinstance(rural, dict), "框架应该是字典"
        assert len(rural) > 0, "框架应该包含维度"

    def test_rural_regeneration_structure(self, ontology_loader):
        """测试新农村框架结构完整性"""
        rural = ontology_loader.get_ontology_by_type("rural_regeneration_urban_renewal")

        # 验证包含3个主要分类
        expected_categories = ["place_identity", "livelihood_economy", "infrastructure_equity"]
        for category in expected_categories:
            assert category in rural, f"应包含分类: {category}"

        # 验证每个分类包含3个维度
        for category in expected_categories:
            dimensions = rural[category]
            assert isinstance(dimensions, list), f"{category} 应该是列表"
            assert len(dimensions) == 3, f"{category} 应该包含3个维度"

    def test_rural_regeneration_place_identity_dimensions(self, ontology_loader):
        """测试场所身份分类的维度"""
        rural = ontology_loader.get_ontology_by_type("rural_regeneration_urban_renewal")
        place_identity = rural.get("place_identity", [])

        # 验证维度名称
        dimension_names = [d["name"] for d in place_identity]
        assert "历史记忆保护 (Historical Memory Preservation)" in dimension_names
        assert "地域文化表达 (Regional Cultural Expression)" in dimension_names
        assert "社区认同建构 (Community Identity Building)" in dimension_names

        # 验证每个维度的完整性
        for dimension in place_identity:
            assert "name" in dimension, "维度必须有名称"
            assert "description" in dimension, "维度必须有描述"
            assert "ask_yourself" in dimension, "维度必须有引导问题"
            assert "examples" in dimension, "维度必须有示例"
            assert len(dimension["description"]) > 15, "描述应该足够详细"

    def test_rural_regeneration_livelihood_economy_dimensions(self, ontology_loader):
        """测试生计经济分类的维度"""
        rural = ontology_loader.get_ontology_by_type("rural_regeneration_urban_renewal")
        livelihood = rural.get("livelihood_economy", [])

        # 验证维度名称
        dimension_names = [d["name"] for d in livelihood]
        assert "产业植入策略 (Industry Implantation Strategy)" in dimension_names
        assert "原住民生计保障 (Indigenous Livelihood Security)" in dimension_names
        assert "公共空间经济价值 (Public Space Economic Value)" in dimension_names

        # 验证关键概念出现在示例中
        all_examples = " ".join([d["examples"] for d in livelihood])
        assert "民宿" in all_examples or "Guesthouse" in all_examples
        assert "就业" in all_examples or "Employment" in all_examples
        assert "集市" in all_examples or "Market" in all_examples

    def test_rural_regeneration_infrastructure_equity_dimensions(self, ontology_loader):
        """测试基础设施公平分类的维度"""
        rural = ontology_loader.get_ontology_by_type("rural_regeneration_urban_renewal")
        infrastructure = rural.get("infrastructure_equity", [])

        # 验证维度名称
        dimension_names = [d["name"] for d in infrastructure]
        assert "基础设施补齐 (Infrastructure Gap Closure)" in dimension_names
        assert "公共服务可达性 (Public Service Accessibility)" in dimension_names
        assert "无障碍与适老化 (Accessibility & Age-friendliness)" in dimension_names

        # 验证关键概念
        all_examples = " ".join([d["examples"] for d in infrastructure])
        assert "雨污分流" in all_examples or "Sewage Separation" in all_examples
        assert "无障碍" in all_examples or "Accessible" in all_examples

    def test_rural_regeneration_layered_injection(self, ontology_loader):
        """测试新农村框架的分层注入"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="rural_regeneration_urban_renewal", expert_role=None, include_base=True
        )

        # 应该包含基础层和新农村框架
        assert "universal_dimensions" in ontology, "应包含基础层"
        assert "place_identity" in ontology, "应包含场所身份维度"
        assert "livelihood_economy" in ontology, "应包含生计经济维度"
        assert "infrastructure_equity" in ontology, "应包含基础设施公平维度"

    def test_rural_regeneration_formatted_output(self, ontology_loader):
        """测试新农村框架的格式化输出"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="rural_regeneration_urban_renewal", expert_role=None, include_base=True
        )

        prompt_text = ontology_loader.format_as_prompt(ontology, expert_name="乡村规划师")

        # 验证文本包含关键内容
        assert "场所身份" in prompt_text or "Place Identity" in prompt_text
        assert "生计经济" in prompt_text or "Livelihood" in prompt_text
        assert "基础设施" in prompt_text or "Infrastructure" in prompt_text
        assert "历史记忆" in prompt_text or "Historical Memory" in prompt_text

        # 验证格式正确
        assert len(prompt_text) > 500, "提示文本应该包含足够内容"
        assert "####" in prompt_text, "应包含维度标题"

    def test_all_new_frameworks_count(self, ontology_loader):
        """测试项目类型总数（包含v3.2重命名+新增）"""
        frameworks = ontology_loader.ontology_data.get("ontology_frameworks", {})

        # v3.2应该有16个项目类型（meta + 15个项目类型）
        assert len(frameworks) == 16, f"应该有16个框架，实际: {len(frameworks)}"

        # 验证v3.2重命名后+新增的框架都存在
        expected_new = [
            "industrial_conversion",
            "educational_facility",
            "transportation_civic",
            "rural_regeneration_urban_renewal",
            "public_cultural",
            "commercial_office",
            "commercial_hospitality",
            "religious_spiritual",
            "landscape_outdoor",
            "commercial_retail",
        ]
        for framework in expected_new:
            assert framework in frameworks, f"新框架 {framework} 应该存在"

        # 验证旧名已不存在
        legacy_names = [
            "cultural_educational",
            "office_coworking",
            "hospitality_tourism",
            "industrial_manufacturing",
            "education_research",
            "transportation_infrastructure",
        ]
        for old_name in legacy_names:
            assert old_name not in frameworks, f"旧框架名 {old_name} 不应存在"


class TestOntologicalFoundations:
    """测试本体论基础层 (ontological_foundations) 的 E 维度体系"""

    def test_ontological_foundations_exists_in_meta(self, ontology_loader):
        """meta_framework 应包含 ontological_foundations 类别"""
        meta = ontology_loader.get_meta_framework()
        assert "ontological_foundations" in meta, "meta_framework 应包含 ontological_foundations"
        assert len(meta["ontological_foundations"]) == 7, "应有 7 个 E 维度"

    def test_issue_id_present_on_all_e_dimensions(self, ontology_loader):
        """所有 E 维度必须包含 issue_id 字段"""
        meta = ontology_loader.get_meta_framework()
        foundations = meta["ontological_foundations"]
        expected_ids = {"E1", "E2", "E3", "E4", "E5", "E8", "E9"}
        actual_ids = set()
        for dim in foundations:
            assert "issue_id" in dim, f"维度 '{dim['name']}' 缺少 issue_id"
            actual_ids.add(dim["issue_id"])
        assert actual_ids == expected_ids, f"issue_id 集合不匹配: {actual_ids} != {expected_ids}"

    def test_e_dimension_fields_complete(self, ontology_loader):
        """每个 E 维度必须包含全部 5 个字段"""
        meta = ontology_loader.get_meta_framework()
        required_fields = {"name", "issue_id", "description", "ask_yourself", "examples"}
        for dim in meta["ontological_foundations"]:
            missing = required_fields - set(dim.keys())
            assert not missing, f"维度 '{dim.get('name','')}' 缺少字段: {missing}"

    def test_e_dimensions_injected_into_layered_ontology(self, ontology_loader):
        """E 维度应通过三层注入被合并到任何业态的分析框架中"""
        for project_type in ["personal_residential", "commercial_enterprise", "healthcare_wellness"]:
            ontology = ontology_loader.get_layered_ontology(project_type=project_type, include_base=True)
            assert "ontological_foundations" in ontology, f"{project_type} 应包含 ontological_foundations"
            ids = [d.get("issue_id") for d in ontology["ontological_foundations"]]
            assert "E3" in ids, f"{project_type} 应包含 E3 (光)"

    def test_issue_id_rendered_in_prompt(self, ontology_loader):
        """format_as_prompt 输出中应渲染 [E*] 标识"""
        ontology = ontology_loader.get_layered_ontology(project_type="personal_residential", include_base=True)
        prompt = ontology_loader.format_as_prompt(ontology, expert_name="测试专家")
        assert "[E3]" in prompt, "提示文本中应包含 [E3] 标识"
        assert "[E1]" in prompt, "提示文本中应包含 [E1] 标识"


class TestCognitiveScaffolding:
    """测试认知脚手架 (cognitive_scaffolding) L0-L4 层级体系"""

    def test_scaffolding_exists(self, ontology_loader):
        """cognitive_scaffolding 顶层节应存在"""
        scaffolding = ontology_loader.get_cognitive_scaffolding()
        assert scaffolding, "cognitive_scaffolding 应存在"
        assert "levels" in scaffolding, "应包含 levels"
        assert "description" in scaffolding, "应包含 description"

    def test_five_levels_defined(self, ontology_loader):
        """应定义 L0-L4 共 5 个认知层级"""
        levels = ontology_loader.get_cognitive_scaffolding()["levels"]
        expected = {"L0_factual", "L1_functional", "L2_experiential", "L3_interpretive", "L4_dialectical"}
        assert set(levels.keys()) == expected, f"层级不匹配: {set(levels.keys())} != {expected}"

    def test_level_fields_complete(self, ontology_loader):
        """每个层级必须包含 name, prompt_pattern, description, typical_questions, risk_if_skipped"""
        levels = ontology_loader.get_cognitive_scaffolding()["levels"]
        required = {"name", "prompt_pattern", "description", "typical_questions", "risk_if_skipped"}
        for lid, ldata in levels.items():
            missing = required - set(ldata.keys())
            assert not missing, f"层级 {lid} 缺少字段: {missing}"

    def test_levels_have_increasing_depth(self, ontology_loader):
        """L0 是最浅层，L4 是最深层——验证名称序列正确"""
        levels = ontology_loader.get_cognitive_scaffolding()["levels"]
        names = [
            levels[
                f"L{i}_{'factual' if i==0 else 'functional' if i==1 else 'experiential' if i==2 else 'interpretive' if i==3 else 'dialectical'}"
            ]["name"]
            for i in range(5)
        ]
        assert "事实" in names[0], f"L0 应为事实层, got: {names[0]}"
        assert "张力" in names[4], f"L4 应为张力层, got: {names[4]}"


class TestActivationProfiles:
    """测试业态激活图谱 (activation_profiles)"""

    def test_activation_profiles_exist(self, ontology_loader):
        """activation_profiles 应存在"""
        available = ontology_loader.get_available_activation_profiles()
        assert len(available) > 0, "应有激活图谱定义"

    def test_all_project_types_covered(self, ontology_loader):
        """所有 12 种项目类型都应有激活图谱"""
        project_types = ontology_loader.get_available_project_types()
        profiles = ontology_loader.get_available_activation_profiles()
        missing = set(project_types) - set(profiles)
        assert not missing, f"以下项目类型缺少激活图谱: {missing}"

    def test_profile_fields_complete(self, ontology_loader):
        """每个激活图谱必须包含 elevated_topics, typical_depth, guidance, key_tensions"""
        required = {"elevated_topics", "typical_depth", "guidance", "key_tensions"}
        for pt in ontology_loader.get_available_activation_profiles():
            profile = ontology_loader.get_activation_profile(pt)
            missing = required - set(profile.keys())
            assert not missing, f"业态 '{pt}' 的激活图谱缺少: {missing}"

    def test_elevated_topics_reference_valid_e_ids(self, ontology_loader):
        """elevated_topics 中的 E-id 必须对应真实的 issue_id"""
        meta = ontology_loader.get_meta_framework()
        valid_ids = {d["issue_id"] for d in meta["ontological_foundations"]}

        for pt in ontology_loader.get_available_activation_profiles():
            profile = ontology_loader.get_activation_profile(pt)
            for eid in profile["elevated_topics"]:
                assert eid in valid_ids, f"业态 '{pt}' 引用了非法 issue_id: {eid}"

    def test_key_tensions_non_empty(self, ontology_loader):
        """每个业态至少有 2 条核心设计张力"""
        for pt in ontology_loader.get_available_activation_profiles():
            profile = ontology_loader.get_activation_profile(pt)
            tensions = profile["key_tensions"]
            assert len(tensions) >= 2, f"业态 '{pt}' 张力数不足: {len(tensions)}"

    def test_nonexistent_type_returns_empty(self, ontology_loader):
        """不存在的项目类型应返回空字典"""
        profile = ontology_loader.get_activation_profile("nonexistent_type")
        assert profile == {}, "不存在的项目类型应返回空字典"

    def test_typical_depth_format(self, ontology_loader):
        """typical_depth 应为 L*-L* 格式范围"""
        import re

        pattern = re.compile(r"^L\d-L\d$")
        for pt in ontology_loader.get_available_activation_profiles():
            profile = ontology_loader.get_activation_profile(pt)
            depth = profile["typical_depth"]
            assert pattern.match(depth), f"业态 '{pt}' 的 typical_depth 格式错误: {depth}"


class TestFormatAsPromptWithActivation:
    """测试 format_as_prompt 在传入 project_type 时的激活指导注入"""

    def test_prompt_without_project_type_no_activation(self, ontology_loader):
        """不传 project_type 时，不应注入激活指导"""
        ontology = ontology_loader.get_layered_ontology(project_type="personal_residential", include_base=True)
        prompt = ontology_loader.format_as_prompt(ontology, expert_name="测试")
        assert "本体论分析重心" not in prompt, "无 project_type 时不应有激活指导"

    def test_prompt_with_project_type_has_activation(self, ontology_loader):
        """传入 project_type 时，应注入激活指导"""
        ontology = ontology_loader.get_layered_ontology(project_type="personal_residential", include_base=True)
        prompt = ontology_loader.format_as_prompt(ontology, expert_name="测试", project_type="personal_residential")
        assert "本体论分析重心" in prompt, "应包含激活指导标题"
        assert "重点议题" in prompt, "应包含重点议题"
        assert "典型深度" in prompt, "应包含典型深度"
        assert "核心设计张力" in prompt, "应包含核心设计张力"

    def test_prompt_activation_before_dimensions(self, ontology_loader):
        """激活指导应出现在维度列表之前"""
        ontology = ontology_loader.get_layered_ontology(project_type="healthcare_wellness", include_base=True)
        prompt = ontology_loader.format_as_prompt(ontology, expert_name="医疗专家", project_type="healthcare_wellness")

        activation_pos = prompt.find("本体论分析重心")
        dimensions_pos = prompt.find("Universal Dimensions")
        assert activation_pos < dimensions_pos, "激活指导应在维度列表之前"

    def test_prompt_tensions_contain_e_cross_references(self, ontology_loader):
        """核心张力的描述应包含 E*×E* 交叉引用"""
        ontology = ontology_loader.get_layered_ontology(project_type="personal_residential", include_base=True)
        prompt = ontology_loader.format_as_prompt(ontology, expert_name="测试", project_type="personal_residential")
        # 住宅项目张力包含 E3×E2, E4×E9 等交叉引用
        assert "×" in prompt, "张力描述应包含 E*×E* 交叉引用符号"

    def test_prompt_with_unknown_type_graceful_fallback(self, ontology_loader):
        """未知项目类型应优雅回退——无激活指导但不报错"""
        ontology = ontology_loader.get_layered_ontology(project_type="meta_framework", include_base=True)
        prompt = ontology_loader.format_as_prompt(ontology, expert_name="测试", project_type="unknown_type")
        assert "分析维度" in prompt, "仍应包含基础维度头部"
        assert "本体论分析重心" not in prompt, "未知类型不应有激活指导"

    def test_all_project_types_prompt_generation(self, ontology_loader):
        """所有 15 种项目类型都能成功生成带激活指导的提示"""
        for pt in ontology_loader.get_available_project_types():
            ontology = ontology_loader.get_layered_ontology(project_type=pt, include_base=True)
            prompt = ontology_loader.format_as_prompt(ontology, expert_name="综合测试", project_type=pt)
            assert len(prompt) > 500, f"业态 '{pt}' 的提示太短: {len(prompt)} chars"
            assert "####" in prompt, f"业态 '{pt}' 的提示缺少维度标题"


class TestDetectorToOntologyMapping:
    """测试 DETECTOR_TO_ONTOLOGY 反向映射机制"""

    def test_mapped_detector_type_gets_framework(self, ontology_loader):
        """通过 DETECTOR_TO_ONTOLOGY 映射的 detector 类型应获得对应框架"""
        # rural_construction → rural_regeneration_urban_renewal
        ontology = ontology_loader.get_layered_ontology(project_type="rural_construction", include_base=True)
        assert "place_identity" in ontology, "rural_construction 应通过映射获得 rural_regeneration_urban_renewal 框架"

    def test_mapped_type_gets_activation_profile(self, ontology_loader):
        """映射类型的 activation_profile 也应能查到"""
        profile = ontology_loader.get_activation_profile("commercial_dining")
        assert profile, "commercial_dining 应通过映射获得 commercial_hospitality 的激活图谱"
        assert "elevated_topics" in profile

    def test_direct_match_takes_priority(self, ontology_loader):
        """直接匹配的 detector 类型不应走映射"""
        ontology = ontology_loader.get_layered_ontology(project_type="personal_residential", include_base=True)
        assert "spiritual_world" in ontology, "personal_residential 应直接匹配框架"

    def test_special_function_gets_meta_only(self, ontology_loader):
        """special_function 不在映射表中，应仅获得 meta_framework"""
        ontology = ontology_loader.get_layered_ontology(project_type="special_function", include_base=True)
        # meta_framework 有 universal_dimensions, contemporary_imperatives, ontological_foundations
        assert "universal_dimensions" in ontology
        # 不应有任何项目类型特定的类别
        project_specific_cats = {
            "spiritual_world",
            "dual_identity",
            "business_positioning",
            "sacred_space",
            "ecological_system",
            "customer_journey",
        }
        for cat in project_specific_cats:
            assert cat not in ontology, f"special_function 不应包含 {cat}"

    def test_all_mapping_targets_exist_in_ontology(self, ontology_loader):
        """DETECTOR_TO_ONTOLOGY 中的所有目标框架名必须在 ontology 中存在"""
        from intelligent_project_analyzer.utils.ontology_loader import DETECTOR_TO_ONTOLOGY

        frameworks = ontology_loader.ontology_data.get("ontology_frameworks", {})
        for detector_id, ontology_id in DETECTOR_TO_ONTOLOGY.items():
            assert ontology_id in frameworks, f"映射目标 '{ontology_id}' (来自 '{detector_id}') 不在 ontology_frameworks 中"

    def test_prompt_with_mapped_type_has_activation(self, ontology_loader):
        """映射类型生成的 prompt 应包含激活指导"""
        ontology = ontology_loader.get_layered_ontology(project_type="performing_arts", include_base=True)
        prompt = ontology_loader.format_as_prompt(ontology, expert_name="测试", project_type="performing_arts")
        assert "本体论分析重心" in prompt, "映射类型应获得激活指导"

    def test_new_frameworks_loadable(self, ontology_loader):
        """3 个 L3 新增框架 (religious_spiritual, landscape_outdoor, commercial_retail) 可正常加载"""
        for pt in ["religious_spiritual", "landscape_outdoor", "commercial_retail"]:
            ontology = ontology_loader.get_layered_ontology(project_type=pt, include_base=True)
            assert len(ontology) > 3, f"{pt} 应包含 meta + 项目类型维度"
            profile = ontology_loader.get_activation_profile(pt)
            assert profile, f"{pt} 应有激活图谱"
            assert "key_tensions" in profile


class TestV8NewTypeDetectorMapping:
    """v8.0 新增 8 个 detector type_id 的同步验证测试

    每次向 PROJECT_TYPE_REGISTRY 新增类型后，对应的 DETECTOR_TO_ONTOLOGY
    条目必须存在，且目标框架的一级维度 (category key) 必须可注入。
    """

    # ─── 参数化：type_id → (目标框架, 代表性 category key) ─────────────────
    _MAPPING = [
        ("leisure_entertainment", "commercial_hospitality", "guest_journey"),
        ("wedding_banquet", "commercial_hospitality", "guest_journey"),
        ("children_family", "educational_facility", "learning_paradigm"),
        ("residential_renovation", "personal_residential", "spiritual_world"),
        ("beauty_personal_care", "commercial_retail", "customer_journey"),
        ("automotive_showroom", "commercial_retail", "customer_journey"),
        ("digital_media_studio", "commercial_office", "work_culture"),
        ("popup_temporary", "commercial_retail", "customer_journey"),
    ]

    def test_v8_types_registered_in_detector_to_ontology(self):
        """所有 8 个 v8.0 类型必须存在于 DETECTOR_TO_ONTOLOGY"""
        from intelligent_project_analyzer.utils.ontology_loader import DETECTOR_TO_ONTOLOGY

        missing = {t for t, _, _ in self._MAPPING} - set(DETECTOR_TO_ONTOLOGY.keys())
        assert not missing, f"以下 v8.0 类型未在 DETECTOR_TO_ONTOLOGY 注册: {missing}"

    @pytest.mark.parametrize("detector_type,expected_framework,expected_cat", _MAPPING)
    def test_layered_ontology_gets_mapped_framework(
        self, ontology_loader, detector_type, expected_framework, expected_cat
    ):
        """各新类型通过映射获得目标框架的代表性 category key"""
        ontology = ontology_loader.get_layered_ontology(project_type=detector_type, include_base=True)
        assert expected_cat in ontology, (
            f"'{detector_type}' 应通过 DETECTOR_TO_ONTOLOGY 映射到 '{expected_framework}'，" f"并在注入结果中包含 '{expected_cat}'"
        )

    @pytest.mark.parametrize("detector_type,expected_framework,_", _MAPPING)
    def test_activation_profile_accessible_via_mapping(self, ontology_loader, detector_type, expected_framework, _):
        """各新类型能通过映射查到激活图谱，且图谱来自正确的目标框架"""
        profile = ontology_loader.get_activation_profile(detector_type)
        assert profile, f"'{detector_type}' 应通过映射获得 '{expected_framework}' 的激活图谱，但返回空"
        assert "elevated_topics" in profile, "激活图谱应包含 elevated_topics"
        assert "key_tensions" in profile, "激活图谱应包含 key_tensions"

    @pytest.mark.parametrize("detector_type,expected_framework,_", _MAPPING)
    def test_prompt_generated_successfully_for_new_types(self, ontology_loader, detector_type, expected_framework, _):
        """各新类型能生成含激活指导的完整 prompt（端到端同步验证）"""
        ontology = ontology_loader.get_layered_ontology(project_type=detector_type, include_base=True)
        prompt = ontology_loader.format_as_prompt(ontology, expert_name="同步验证专家", project_type=detector_type)
        assert len(prompt) > 500, f"'{detector_type}' 生成的 prompt 过短: {len(prompt)} 字符"
        assert "####" in prompt, f"'{detector_type}' 的 prompt 缺少维度标题"
        assert "本体论分析重心" in prompt, f"'{detector_type}' 的 prompt 缺少激活指导（映射到 '{expected_framework}'）"

    def test_v8_type_ids_detectable(self):
        """8 个新类型的代表性关键词能被 detect_project_type 正确识别"""
        from intelligent_project_analyzer.services.project_type_detector import detect_project_type

        cases = [
            ("水会洗浴中心设计", "leisure_entertainment"),
            ("婚宴厅室内设计", "wedding_banquet"),
            ("早教中心亲子空间", "children_family"),
            ("老房子翻新改造", "residential_renovation"),
            ("美发沙龙店面设计", "beauty_personal_care"),
            ("汽车4s店展厅设计", "automotive_showroom"),
            ("直播基地工作室", "digital_media_studio"),
            ("品牌快闪店设计", "popup_temporary"),
        ]
        for user_input, expected_type in cases:
            result = detect_project_type(user_input)
            assert result == expected_type, f"输入 '{user_input}' 期望识别为 '{expected_type}'，实际为 '{result}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
