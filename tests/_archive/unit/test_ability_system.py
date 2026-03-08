"""
Ability Core P1 单元测试
=======================

测试能力声明系统的核心功能：
1. 能力声明数据模型
2. 能力查询工具
3. 覆盖率分析
"""

import pytest

from intelligent_project_analyzer.utils.ability_schemas import (
    AbilityDeclaration,
    ExpertAbilityProfile,
    maturity_level_to_numeric,
    numeric_to_maturity_level,
    get_coverage_status,
    ABILITY_NAMES,
)

from intelligent_project_analyzer.utils.ability_query import (
    AbilityQueryTool,
    query_expert_abilities,
    find_experts_with_ability,
    generate_coverage_report,
)


# ============================================================================
# 测试能力声明数据模型
# ============================================================================


class TestAbilityDeclaration:
    """测试 AbilityDeclaration 数据模型"""

    def test_ability_declaration_creation(self):
        """测试创建能力声明"""
        ability = AbilityDeclaration(id="A9", name="Social Structure Modeling", maturity_level="L4", confidence=0.9)

        assert ability.id == "A9"
        assert ability.name == "Social Structure Modeling"
        assert ability.maturity_level == "L4"
        assert ability.confidence == 0.9

    def test_ability_with_sub_abilities(self):
        """测试包含子能力的声明"""
        ability = AbilityDeclaration(
            id="A9",
            name="Social Structure Modeling",
            maturity_level="L4",
            sub_abilities=["A9-1_power_distance", "A9-2_privacy_hierarchy"],
            confidence=0.9,
        )

        assert len(ability.sub_abilities) == 2
        assert "A9-1_power_distance" in ability.sub_abilities


class TestExpertAbilityProfile:
    """测试 ExpertAbilityProfile 数据模型"""

    def test_empty_profile(self):
        """测试空能力档案"""
        profile = ExpertAbilityProfile()

        assert len(profile.primary) == 0
        assert len(profile.secondary) == 0

    def test_profile_with_abilities(self):
        """测试包含能力的档案"""
        profile = ExpertAbilityProfile(
            primary=[
                AbilityDeclaration(id="A9", name="Social Structure Modeling", maturity_level="L4", confidence=0.9)
            ],
            secondary=[
                AbilityDeclaration(id="A3", name="Narrative Orchestration", maturity_level="L3", confidence=0.8)
            ],
        )

        assert len(profile.primary) == 1
        assert len(profile.secondary) == 1
        assert profile.primary[0].id == "A9"
        assert profile.secondary[0].id == "A3"


# ============================================================================
# 测试辅助函数
# ============================================================================


class TestUtilityFunctions:
    """测试辅助函数"""

    def test_maturity_level_to_numeric(self):
        """测试成熟度转数值"""
        assert maturity_level_to_numeric("L1") == 1.0
        assert maturity_level_to_numeric("L3") == 3.0
        assert maturity_level_to_numeric("L5") == 5.0

    def test_numeric_to_maturity_level(self):
        """测试数值转成熟度"""
        assert numeric_to_maturity_level(1.0) == "L1"
        assert numeric_to_maturity_level(3.5) == "L4"  # 四舍五入
        assert numeric_to_maturity_level(5.0) == "L5"

    def test_get_coverage_status(self):
        """测试覆盖状态评级"""
        assert get_coverage_status(0.95) == "excellent"
        assert get_coverage_status(0.85) == "good"
        assert get_coverage_status(0.75) == "fair"
        assert get_coverage_status(0.60) == "weak"
        assert get_coverage_status(0.30) == "critical"


# ============================================================================
# 测试能力查询工具
# ============================================================================


class TestAbilityQueryTool:
    """测试 AbilityQueryTool"""

    @pytest.fixture
    def query_tool(self):
        """创建查询工具实例"""
        return AbilityQueryTool()

    def test_tool_initialization(self, query_tool):
        """测试工具初始化"""
        assert query_tool is not None
        assert query_tool.config_dir.exists()

    def test_load_configs(self, query_tool):
        """测试加载配置文件"""
        # 应该加载至少7个专家配置
        assert len(query_tool._expert_configs) >= 7

    def test_get_v7_abilities(self, query_tool):
        """测试获取V7专家能力"""
        abilities = query_tool.get_expert_abilities("v7_emotional_insight_expert")

        assert abilities is not None
        assert len(abilities.primary) >= 1

        # V7的主能力应包含A9
        primary_ids = [a.id for a in abilities.primary]
        assert "A9" in primary_ids

    def test_find_experts_by_a9(self, query_tool):
        """测试查找A9能力专家"""
        experts = query_tool.find_experts_by_ability("A9", min_level="L3")

        # V7应该是A9的主要专家
        assert "v7_emotional_insight_expert" in experts["primary"]

    def test_coverage_report_generation(self, query_tool):
        """测试生成覆盖报告"""
        report = query_tool.get_ability_coverage_report()

        assert report is not None
        assert len(report.abilities) == 12  # 应该有12个能力
        assert report.overall_coverage_rate > 0.8  # 整体覆盖率应>80%

    def test_ability_names_complete(self):
        """测试能力名称定义完整"""
        assert len(ABILITY_NAMES) == 12
        assert "A1" in ABILITY_NAMES
        assert "A12" in ABILITY_NAMES


# ============================================================================
# 测试快捷函数
# ============================================================================


class TestShortcutFunctions:
    """测试快捷函数"""

    def test_query_expert_abilities_shortcut(self):
        """测试快捷查询函数"""
        abilities = query_expert_abilities("v7_emotional_insight_expert")

        assert abilities is not None
        assert len(abilities.primary) >= 1

    def test_find_experts_shortcut(self):
        """测试快捷查找函数"""
        experts = find_experts_with_ability("A9", min_level="L3")

        assert "primary" in experts
        assert "secondary" in experts
        assert len(experts["primary"]) > 0

    def test_generate_report_shortcut(self):
        """测试快捷生成报告函数"""
        report = generate_coverage_report()

        assert report is not None
        assert report.overall_coverage_rate > 0.0


# ============================================================================
# 测试覆盖率分析
# ============================================================================


class TestCoverageAnalysis:
    """测试覆盖率分析"""

    def test_a9_coverage(self):
        """测试A9社会关系建模覆盖情况"""
        report = generate_coverage_report()

        a9_report = next((a for a in report.abilities if a.ability_id == "A9"), None)

        assert a9_report is not None
        assert a9_report.expert_count >= 1  # 至少V7
        assert a9_report.coverage_rate >= 0.5  # 覆盖率应≥50%

    def test_a1_coverage(self):
        """测试A1概念建构覆盖情况"""
        report = generate_coverage_report()

        a1_report = next((a for a in report.abilities if a.ability_id == "A1"), None)

        assert a1_report is not None
        assert a1_report.expert_count >= 2  # V2, V3
        assert "v2_design_director" in a1_report.primary_experts or "v2_design_director" in a1_report.secondary_experts

    def test_weak_abilities_identified(self):
        """测试识别弱覆盖能力"""
        report = generate_coverage_report()

        # 应该有一些弱覆盖或严重缺口的能力
        assert len(report.weak_abilities) >= 0
        assert len(report.critical_abilities) <= 2  # 严重缺口应≤2


# ============================================================================
# 集成测试
# ============================================================================


class TestIntegration:
    """集成测试"""

    def test_full_workflow(self):
        """测试完整工作流程"""
        # 1. 创建查询工具
        tool = AbilityQueryTool()

        # 2. 查询V7能力
        v7_abilities = tool.get_expert_abilities("v7_emotional_insight_expert")
        assert v7_abilities is not None

        # 3. 查找A9专家
        a9_experts = tool.find_experts_by_ability("A9")
        assert len(a9_experts["primary"]) > 0

        # 4. 生成覆盖报告
        report = tool.get_ability_coverage_report()
        assert report.overall_coverage_rate > 0.8

        # 5. 验证关键指标
        assert len(report.abilities) == 12
        assert len(report.critical_abilities) <= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
