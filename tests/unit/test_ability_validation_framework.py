"""
P2 能力验证框架单元测试

测试覆盖：
1. AbilityValidator - 能力验证器基础功能
2. ValidationReportGenerator - 报告生成器
3. TaskOrientedExpertFactory集成 - 验证流程集成

创建日期: 2026-02-12
版本: v1.0
"""

import pytest

#  导入需要测试的模块
from intelligent_project_analyzer.services.ability_validator import (
    AbilityValidator,
    ExpertValidationReport,
    AbilityValidationResult,
    ValidationCheck,
    validate_expert,
)
from intelligent_project_analyzer.services.validation_report_generator import (
    ValidationReportGenerator,
    generate_validation_report,
)
from intelligent_project_analyzer.utils.ability_query import AbilityQueryTool


class TestAbilityValidator:
    """测试AbilityValidator类"""

    def test_validator_initialization(self):
        """测试验证器初始化"""
        validator = AbilityValidator()
        assert validator is not None
        assert validator.rules is not None
        assert len(validator.rules) > 0
        print(f"✅ 验证器初始化成功，加载了 {len(validator.rules)} 个规则")

    def test_load_verification_rules(self):
        """测试验证规则加载"""
        validator = AbilityValidator()

        # 检查是否加载了12个核心能力的规则
        expected_abilities = [
            "A1_concept_architecture",
            "A2_spatial_structuring",
            "A3_narrative_orchestration",
            "A4_material_intelligence",
            "A5_lighting_architecture",
            "A6_functional_optimization",
            "A7_capital_strategy_intelligence",
            "A8_technology_integration",
            "A9_social_structure_modeling",
            "A10_environmental_adaptation",
            "A11_operation_productization",
            "A12_civilizational_expression",
        ]

        for ability in expected_abilities:
            assert ability in validator.rules, f"缺少能力规则: {ability}"

        print("✅ 验证规则完整性检查通过")

    def test_check_required_fields(self):
        """测试必需字段检查"""
        validator = AbilityValidator()

        # 测试数据：包含部分字段
        test_output = {
            "conceptual_foundation": {
                "core_concept": "现代简约",
                "philosophical_framework": "少即是多"
                # 缺少 spatial_interpretation 和 concept_structure
            }
        }

        # 定义验证规则
        required_fields = {
            "conceptual_foundation": [
                "core_concept",
                "philosophical_framework",
                "spatial_interpretation",
                "concept_structure",
            ]
        }

        result = validator._check_required_fields(test_output, required_fields)

        assert result.check_name == "required_fields"
        assert result.details["found_fields"] == 3  # 1父字段 + 2子字段
        assert result.details["total_fields"] == 5  # 1父字段 + 4子字段
        assert len(result.details["missing_fields"]) == 2  # 缺少2个子字段
        print("✅ 必需字段检查功能正常")

    def test_check_keywords(self):
        """测试关键词密度检查"""
        validator = AbilityValidator()

        # 测试数据：包含一些关键词
        test_output = {"analysis": "这是一个关于概念驱动型空间设计的分析。核心概念是现代简约，" * 5 + "通过空间哲学的转译，形成独特的精神主轴。整体思想是以材料和光线强化概念表达。"}

        keywords = ["概念", "哲学", "精神主轴", "思想", "理念"]

        result = validator._check_keywords(test_output, keywords, threshold=0.015)

        assert result.check_name == "keyword_density"
        assert "keyword_counts" in result.details
        assert result.details["density"] > 0
        print(f"✅ 关键词密度检查功能正常 (密度: {result.details['density']:.2%})")

    def test_validate_v7_emotional_expert(self):
        """测试V7情感洞察专家的能力验证"""
        # 模拟V7专家的输出
        v7_output = {
            "social_structure_analysis": {
                "power_distance_model": "低权力距离家庭结构分析",
                "privacy_hierarchy": "四级隐私模型：公共区、半公共区、半私密区、完全私密区",
                "conflict_buffer_design": "冲突缓冲空间设计",
                "evolution_adaptability": "家庭关系演化适配机制",
                "intergenerational_balance": "代际关系平衡策略",
            },
            "analysis_content": "基于Hofstede权力距离理论和Altman隐私调节理论，进行了家庭结构分析。" * 20,
        }

        # V7声明的能力
        v7_abilities = [{"id": "A9", "maturity_level": "L4", "confidence": 0.9}]

        # 执行验证
        report = validate_expert(
            expert_id="v7_emotional_insight_expert",
            output=v7_output,
            declared_abilities=v7_abilities,
            print_result=False,
        )

        assert report is not None
        assert report.expert_id == "v7_emotional_insight_expert"
        assert len(report.abilities_validated) > 0

        # 检查A9能力验证
        a9_result = next((a for a in report.abilities_validated if a.ability_id == "A9"), None)
        assert a9_result is not None
        print(f"✅ V7专家能力验证完成 (A9评分: {a9_result.overall_score:.1%})")

    def test_validate_v6_6_sustainability_expert(self):
        """测试V6-6可持续专家的能力验证"""
        # 模拟V6-6专家的输出
        v6_6_output = {
            "environmental_adaptation_analysis": {
                "climate_analysis": "西藏高海拔气候数据分析：年均温-2°C，日温差25°C",
                "structural_resistance": "抗震设计、抗风压结构系统",
                "material_adaptation": "低导热材料、三层中空玻璃、气密性强化",
                "energy_system": "太阳能光伏系统、地源热泵、被动式供暖",
                "comfort_assurance": "供氧系统、温湿度控制",
            },
            "analysis_content": "针对极端环境的适应性设计，气候数据显示需要强化结构抗性和材料适应性能。" * 30,
        }

        # V6-6声明的能力
        v6_6_abilities = [{"id": "A10", "maturity_level": "L5", "confidence": 0.95}]

        # 执行验证
        report = validate_expert(
            expert_id="v6_6_sustainability_expert",
            output=v6_6_output,
            declared_abilities=v6_6_abilities,
            print_result=False,
        )

        assert report is not None
        assert len(report.abilities_validated) > 0

        # 检查A10能力验证
        a10_result = next((a for a in report.abilities_validated if a.ability_id == "A10"), None)
        assert a10_result is not None
        print(f"✅ V6-6专家能力验证完成 (A10评分: {a10_result.overall_score:.1%})")

    def test_maturity_level_threshold_adjustment(self):
        """测试成熟度等级阈值调整"""
        validator = AbilityValidator()

        # 测试不同成熟度等级的阈值
        l5_thresholds = validator._get_adjusted_thresholds("L5")
        l3_thresholds = validator._get_adjusted_thresholds("L3")
        l1_thresholds = validator._get_adjusted_thresholds("L1")

        # L5应该有更高的阈值要求
        assert l5_thresholds["field_completeness"] > l3_thresholds["field_completeness"]
        assert l3_thresholds["field_completeness"] > l1_thresholds["field_completeness"]

        print("✅ 成熟度等级阈值调整正常")
        print(f"   L5阈值: {l5_thresholds}")
        print(f"   L3阈值: {l3_thresholds}")
        print(f"   L1阈值: {l1_thresholds}")


class TestValidationReportGenerator:
    """测试ValidationReportGenerator类"""

    def test_generator_initialization(self):
        """测试报告生成器初始化"""
        generator = ValidationReportGenerator()
        assert generator is not None
        assert generator.validator is not None
        assert generator.ability_tool is not None
        print("✅ 报告生成器初始化成功")

    def test_generate_session_report(self):
        """测试会话报告生成"""
        from datetime import datetime

        # 创建模拟验证报告
        mock_reports = [
            ExpertValidationReport(
                expert_id="v7_emotional_insight_expert",
                timestamp=datetime.now().isoformat(),
                overall_passed=True,
                overall_score=0.85,
                abilities_validated=[
                    AbilityValidationResult(
                        ability_id="A9",
                        ability_name="Social Structure Modeling",
                        passed=True,
                        overall_score=0.85,
                        checks=[ValidationCheck(check_name="required_fields", passed=True, score=0.9, threshold=0.8)],
                    )
                ],
            ),
            ExpertValidationReport(
                expert_id="v6_6_sustainability_expert",
                timestamp=datetime.now().isoformat(),
                overall_passed=True,
                overall_score=0.80,
                abilities_validated=[
                    AbilityValidationResult(
                        ability_id="A10",
                        ability_name="Environmental Adaptation",
                        passed=True,
                        overall_score=0.80,
                        checks=[ValidationCheck(check_name="required_fields", passed=True, score=0.85, threshold=0.8)],
                    )
                ],
            ),
        ]

        # 生成报告
        generator = ValidationReportGenerator()
        report = generator.generate_session_report(validation_reports=mock_reports, session_id="test_session_001")

        assert report is not None
        assert report["session_id"] == "test_session_001"
        assert report["experts_count"] == 2
        assert "overall_statistics" in report
        assert "ability_statistics" in report
        assert "expert_rankings" in report
        assert "recommendations" in report

        # 检查统计数据
        stats = report["overall_statistics"]
        assert stats["total_experts"] == 2
        assert stats["experts_passed"] == 2
        assert stats["expert_pass_rate"] == 1.0

        print("✅ 会话报告生成成功")
        print(f"   专家数量: {report['experts_count']}")
        print(f"   整体通过率: {stats['expert_pass_rate']:.1%}")
        print(f"   平均评分: {stats['average_expert_score']:.1%}")

    def test_identify_quality_issues(self):
        """测试质量问题识别"""
        from datetime import datetime

        # 创建包含低分的模拟报告
        mock_reports = [
            ExpertValidationReport(
                expert_id="low_score_expert",
                timestamp=datetime.now().isoformat(),
                overall_passed=False,
                overall_score=0.45,  # 低分
                abilities_validated=[
                    AbilityValidationResult(
                        ability_id="A1",
                        ability_name="Concept Architecture",
                        passed=False,
                        overall_score=0.45,
                        missing_keywords=["概念", "哲学"],
                        checks=[],
                    )
                ],
            )
        ]

        generator = ValidationReportGenerator()
        report = generator.generate_session_report(validation_reports=mock_reports, session_id="test_quality_issues")

        # 应该识别出质量问题
        assert len(report["quality_issues"]) > 0

        # 检查严重问题
        severe_issues = [i for i in report["quality_issues"] if i["severity"] == "严重"]
        assert len(severe_issues) > 0

        print("✅ 质量问题识别功能正常")
        print(f"   发现问题数: {len(report['quality_issues'])}")
        print(f"   严重问题数: {len(severe_issues)}")


class TestIntegration:
    """集成测试"""

    def test_end_to_end_validation_flow(self):
        """测试端到端验证流程"""
        # 1. 查询专家能力
        ability_tool = AbilityQueryTool()
        expert_profile = ability_tool.get_expert_abilities("v7_emotional_insight_expert")

        assert expert_profile is not None
        # 将ExpertAbilityProfile转换为abilities列表
        abilities = []
        for ability in expert_profile.primary + expert_profile.secondary:
            abilities.append(
                {"id": ability.id, "maturity_level": ability.maturity_level, "confidence": ability.confidence}
            )
        print("✅ 步骤1: 成功查询专家能力")

        # 2. 模拟专家输出
        expert_output = {
            "social_structure_analysis": {
                "power_distance_model": "测试内容",
                "privacy_hierarchy": "四级隐私模型",
                "conflict_buffer_design": "冲突缓冲设计",
                "evolution_adaptability": "演化适配",
                "intergenerational_balance": "代际平衡",
            },
            "analysis": "基于Hofstede权力距离理论进行家庭结构分析，考虑隐私调节和代际关系。" * 20,
        }

        # 3. 执行验证
        report = validate_expert(
            expert_id="v7_emotional_insight_expert",
            output=expert_output,
            declared_abilities=abilities,
            print_result=False,
        )

        assert report is not None
        assert len(report.abilities_validated) > 0
        print(f"✅ 步骤2: 能力验证完成 (评分: {report.overall_score:.1%})")

        # 4. 生成聚合报告
        aggregated_report = generate_validation_report(
            validation_reports=[report], session_id="integration_test", print_report=False
        )

        assert aggregated_report is not None
        assert "overall_statistics" in aggregated_report
        print("✅ 步骤3: 聚合报告生成成功")

        print("\n✅ 端到端验证流程测试通过")

    def test_multiple_experts_validation(self):
        """测试多个专家的批量验证"""
        ability_tool = AbilityQueryTool()
        validator = AbilityValidator()

        # 测试多个专家
        expert_ids = ["v2_design_director", "v3_narrative_expert", "v7_emotional_insight_expert"]

        validation_reports = []

        for expert_id in expert_ids:
            # 查询能力
            profile = ability_tool.get_expert_abilities(expert_id)
            if not profile or (not profile.primary and not profile.secondary):
                continue

            # 转换为abilities列表
            abilities = []
            for ability in profile.primary + profile.secondary:
                abilities.append(
                    {"id": ability.id, "maturity_level": ability.maturity_level, "confidence": ability.confidence}
                )

            # 模拟输出
            mock_output = {"analysis": f"{expert_id} 的分析内容，包含各种专业术语和关键概念。" * 30}

            # 验证
            report = validator.validate_expert_output(
                expert_id=expert_id, output=mock_output, declared_abilities=abilities
            )

            validation_reports.append(report)

        assert len(validation_reports) > 0
        print(f"✅ 批量验证完成: {len(validation_reports)} 个专家")

        # 生成聚合报告
        generator = ValidationReportGenerator()
        aggregated = generator.generate_session_report(validation_reports=validation_reports, session_id="batch_test")

        assert aggregated["experts_count"] == len(validation_reports)
        print("✅ 聚合报告生成成功")
        print(f"   整体通过率: {aggregated['overall_statistics']['expert_pass_rate']:.1%}")


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("🧪 P2 能力验证框架单元测试")
    print("=" * 80 + "\n")

    # 运行所有测试
    pytest.main([__file__, "-v", "--tb=short"])
