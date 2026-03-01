"""
本体论框架集成测试 (Ontology Workflow Integration Tests)

测试覆盖：
1. OntologyLoader与工作流的集成
2. 新框架在实际分析场景中的应用
3. 跨模块数据流验证
4. 性能和缓存测试
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


class TestRuralRegenerationIntegration:
    """测试新农村/城市更新框架的集成场景"""

    def test_rural_project_full_ontology_loading(self, ontology_loader):
        """场景1：加载新农村项目的完整本体论"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="rural_regeneration_urban_renewal", expert_role="design_director", include_base=True
        )

        # 验证三层都正确加载
        assert ontology is not None
        assert len(ontology) >= 4, "应包含meta + 3个新农村分类"

        # 验证基础层
        assert "universal_dimensions" in ontology

        # 验证项目类型层
        assert "place_identity" in ontology
        assert "livelihood_economy" in ontology
        assert "infrastructure_equity" in ontology

    def test_rural_project_with_different_experts(self, ontology_loader):
        """场景2：不同专家分析同一新农村项目"""
        experts = ["design_director", "narrative_expert", "capital_strategy_expert", "sustainability_expert"]

        base_ontology = ontology_loader.get_layered_ontology(
            project_type="rural_regeneration_urban_renewal", expert_role=None, include_base=True
        )
        base_dimension_count = sum(len(v) if isinstance(v, list) else 1 for v in base_ontology.values())

        for expert in experts:
            expert_ontology = ontology_loader.get_layered_ontology(
                project_type="rural_regeneration_urban_renewal", expert_role=expert, include_base=True
            )

            # 专家强化后的维度应该 >= 基础维度
            expert_dimension_count = sum(len(v) if isinstance(v, list) else 1 for v in expert_ontology.values())
            assert expert_dimension_count >= base_dimension_count, f"{expert} 的本体论应该包含所有基础维度"

    def test_rural_project_prompt_generation(self, ontology_loader):
        """场景3：为新农村项目生成专家提示"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="rural_regeneration_urban_renewal", expert_role="design_director", include_base=True
        )

        prompt = ontology_loader.format_as_prompt(ontology, expert_name="乡村规划师")

        # 验证提示文本质量
        assert len(prompt) > 1000, "提示文本应该有足够长度"

        # 验证包含关键概念（中英文）
        key_concepts = ["场所身份", "生计经济", "基础设施", "历史记忆", "产业植入", "原住民", "无障碍", "适老化"]
        found_concepts = sum(1 for concept in key_concepts if concept in prompt)
        assert found_concepts >= 5, f"应包含至少5个关键概念，实际: {found_concepts}"

        # 验证Markdown格式
        assert "##" in prompt
        assert "###" in prompt
        assert "####" in prompt

    def test_cross_framework_comparison(self, ontology_loader):
        """场景4：对比新农村与其他框架的维度差异"""
        rural = ontology_loader.get_ontology_by_type("rural_regeneration_urban_renewal")
        residential = ontology_loader.get_ontology_by_type("personal_residential")

        # 验证框架有明显差异
        rural_categories = set(rural.keys())
        residential_categories = set(residential.keys())

        # 不应完全相同
        assert rural_categories != residential_categories, "不同项目类型应有不同分类"

        # 新农村应该有独特的分类
        unique_rural = rural_categories - residential_categories
        assert len(unique_rural) > 0, "新农村应有独特分类"
        assert "place_identity" in rural_categories or "livelihood_economy" in rural_categories


class TestMultiFrameworkIntegration:
    """测试多个框架的集成场景"""

    def test_all_frameworks_loadable(self, ontology_loader):
        """场景5：验证所有13个框架都可正常加载"""
        frameworks = ontology_loader.ontology_data.get("ontology_frameworks", {})

        # 排除meta_framework
        project_types = [k for k in frameworks.keys() if k != "meta_framework"]

        for project_type in project_types:
            ontology = ontology_loader.get_ontology_by_type(project_type)
            assert ontology is not None, f"{project_type} 应该可加载"
            assert len(ontology) > 0, f"{project_type} 应该有维度"

    def test_all_frameworks_with_base_layer(self, ontology_loader):
        """场景6：验证所有框架都能正确与基础层合并"""
        frameworks = ontology_loader.ontology_data.get("ontology_frameworks", {})
        project_types = [k for k in frameworks.keys() if k != "meta_framework"]

        for project_type in project_types:
            layered = ontology_loader.get_layered_ontology(
                project_type=project_type, expert_role=None, include_base=True
            )

            # 应该包含基础层
            assert (
                "universal_dimensions" in layered or "contemporary_imperatives" in layered
            ), f"{project_type} 应包含基础层维度"

            # 应该包含项目特定维度
            project_specific = ontology_loader.get_ontology_by_type(project_type)
            for category in project_specific.keys():
                assert category in layered, f"{project_type} 应包含 {category}"

    def test_framework_formatted_output_consistency(self, ontology_loader):
        """场景7：验证所有框架格式化输出的一致性"""
        test_frameworks = [
            "personal_residential",
            "commercial_enterprise",
            "healthcare_wellness",
            "industrial_conversion",
            "educational_facility",
            "rural_regeneration_urban_renewal",
        ]

        for framework in test_frameworks:
            ontology = ontology_loader.get_layered_ontology(project_type=framework, expert_role=None, include_base=True)

            prompt = ontology_loader.format_as_prompt(ontology, expert_name="专家")

            # 验证基本格式一致性
            assert "##" in prompt, f"{framework} 应有二级标题"
            assert "####" in prompt, f"{framework} 应有四级标题（维度）"
            assert len(prompt) > 300, f"{framework} 提示文本应足够长"


class TestPerformanceAndCaching:
    """测试性能和缓存相关场景"""

    def test_repeated_loading_performance(self, ontology_loader):
        """场景8：测试重复加载的性能（验证缓存）"""
        import time

        # 第一次加载
        start1 = time.time()
        ontology1 = ontology_loader.get_layered_ontology(
            project_type="rural_regeneration_urban_renewal", expert_role="design_director", include_base=True
        )
        time1 = time.time() - start1

        # 第二次加载（应该从缓存）
        start2 = time.time()
        ontology2 = ontology_loader.get_layered_ontology(
            project_type="rural_regeneration_urban_renewal", expert_role="design_director", include_base=True
        )
        time2 = time.time() - start2

        # 验证结果一致
        assert ontology1.keys() == ontology2.keys()

        # 两次加载时间都应该很快（<1秒）
        assert time1 < 1.0, f"首次加载应该快速，实际: {time1:.3f}秒"
        assert time2 < 1.0, f"二次加载应该快速，实际: {time2:.3f}秒"

    def test_large_scale_loading(self, ontology_loader):
        """场景9：测试大规模加载所有框架的性能"""
        import time

        frameworks = ontology_loader.ontology_data.get("ontology_frameworks", {})
        project_types = [k for k in frameworks.keys() if k != "meta_framework"]

        start = time.time()

        for project_type in project_types:
            ontology = ontology_loader.get_layered_ontology(
                project_type=project_type, expert_role="design_director", include_base=True
            )
            assert ontology is not None

        elapsed = time.time() - start

        # 加载12个框架应该在5秒内完成
        assert elapsed < 5.0, f"加载所有框架耗时过长: {elapsed:.2f}秒"

        # 平均每个框架加载时间
        avg_time = elapsed / len(project_types)
        assert avg_time < 0.5, f"平均加载时间过长: {avg_time:.3f}秒"


class TestErrorHandling:
    """测试错误处理和边界情况"""

    def test_invalid_project_type(self, ontology_loader):
        """场景10：测试无效项目类型的处理"""
        ontology = ontology_loader.get_ontology_by_type("non_existent_type")

        # 应该返回空字典而不是报错
        assert ontology == {} or ontology is None

    def test_invalid_expert_role(self, ontology_loader):
        """场景11：测试无效专家角色的处理"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="rural_regeneration_urban_renewal", expert_role="non_existent_expert", include_base=True
        )

        # 应该返回基础层+项目类型层（忽略无效专家层）
        assert ontology is not None
        assert "place_identity" in ontology

    def test_missing_base_layer(self, ontology_loader):
        """场景12：测试不包含基础层的加载"""
        ontology = ontology_loader.get_layered_ontology(
            project_type="rural_regeneration_urban_renewal", expert_role=None, include_base=False
        )

        # 应该只包含项目类型层
        assert "universal_dimensions" not in ontology
        assert "place_identity" in ontology


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
