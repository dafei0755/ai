#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V6系列模型测试套件 - 灵活输出架构验证

测试范围:
- V6-1: 结构与幕墙工程师
- V6-2: 机电与智能化工程师
- V6-3: 室内工艺与材料专家
- V6-4: 成本与价值工程师
"""

import pytest
from pydantic import ValidationError
from intelligent_project_analyzer.models.flexible_output import (
    V6_1_FlexibleOutput,
    V6_2_FlexibleOutput,
    V6_3_FlexibleOutput,
    V6_4_FlexibleOutput,
    MaterialSpec,
    NodeDetail,
    CostBreakdown,
    VEOption
)


# ==================== V6-1: 结构与幕墙工程师 ====================

class TestV6_1_FlexibleOutput:
    """V6-1 结构与幕墙工程师 - 测试套件"""

    def test_targeted_mode_valid(self):
        """测试Targeted模式 - 有效输入"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何选择结构体系？",
            "confidence": 0.85,
            "design_rationale": "根据建筑功能和跨度要求，推荐框架结构体系",
            "targeted_analysis": {
                "structural_system_comparison": {
                    "options": ["框架结构", "剪力墙结构", "框剪结构"],
                    "recommendation": "框架结构",
                    "rationale": "适合大空间办公布局"
                }
            }
        }

        output = V6_1_FlexibleOutput(**data)

        assert output.output_mode == "targeted"
        assert output.user_question_focus == "如何选择结构体系？"
        assert output.confidence == 0.85
        assert output.targeted_analysis is not None
        assert "structural_system_comparison" in output.targeted_analysis

        # 验证标准字段为空（Targeted模式）
        assert output.feasibility_assessment is None
        assert output.structural_system_options is None

    def test_targeted_mode_missing_analysis(self):
        """测试Targeted模式 - 缺少targeted_analysis字段"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何选择结构体系？",
            "confidence": 0.85,
            "design_rationale": "根据建筑功能和跨度要求"
            # 缺少 targeted_analysis
        }

        with pytest.raises(ValidationError) as exc_info:
            V6_1_FlexibleOutput(**data)

        error_msg = str(exc_info.value)
        # 支持中英文错误信息
        assert ("targeted_analysis" in error_msg.lower() or "targeted" in error_msg or "针对性" in error_msg)

    def test_comprehensive_mode_valid(self):
        """测试Comprehensive模式 - 有效输入"""
        data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整的结构设计方案",
            "confidence": 0.9,
            "design_rationale": "综合考虑建筑功能、结构安全和经济性",
            "feasibility_assessment": "场地条件良好，地基承载力满足要求...",
            "structural_system_options": [
                {
                    "option_name": "框架结构",
                    "advantages": ["灵活性高", "施工方便"],
                    "disadvantages": ["抗侧刚度较小"],
                    "estimated_cost_level": "中"
                }
            ],
            "facade_system_options": [
                {
                    "option_name": "单元式幕墙",
                    "advantages": ["工期短", "质量稳定"],
                    "disadvantages": ["成本较高"],
                    "estimated_cost_level": "高"
                }
            ],
            "key_technical_nodes": [
                {
                    "node_name": "大跨度梁",
                    "challenge": "跨度过大，需要特殊设计",
                    "proposed_solution": "采用预应力混凝土梁"
                }
            ],
            "risk_analysis_and_recommendations": "结构安全性风险较低，施工难度中等..."
        }

        output = V6_1_FlexibleOutput(**data)

        assert output.output_mode == "comprehensive"
        assert output.confidence == 0.9
        assert output.feasibility_assessment is not None
        assert len(output.structural_system_options) == 1
        assert len(output.facade_system_options) == 1
        assert len(output.key_technical_nodes) == 1
        assert output.risk_analysis_and_recommendations is not None

        # 验证targeted_analysis为空（Comprehensive模式）
        assert output.targeted_analysis is None

    def test_comprehensive_mode_missing_fields(self):
        """测试Comprehensive模式 - 缺少必需字段"""
        data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整的结构设计方案",
            "confidence": 0.9,
            "design_rationale": "综合考虑建筑功能、结构安全和经济性",
            "feasibility_assessment": "场地条件良好...",
            "structural_system_options": [
                {
                    "option_name": "框架结构",
                    "advantages": ["灵活"],
                    "disadvantages": ["刚度小"],
                    "estimated_cost_level": "中"
                }
            ]
            # 缺少 facade_system_options, key_technical_nodes, risk_analysis_and_recommendations
        }

        with pytest.raises(ValidationError) as exc_info:
            V6_1_FlexibleOutput(**data)

        error_msg = str(exc_info.value)
        # 验证错误信息中包含必需字段的提示（支持中英文）
        assert ("必需字段缺失" in error_msg or "missing required fields" in error_msg.lower())
        assert ("facade_system_options" in error_msg or "幕墙" in error_msg)
        assert ("key_technical_nodes" in error_msg or "关键" in error_msg)
        assert ("risk_analysis" in error_msg or "风险" in error_msg)

    def test_confidence_range_validation(self):
        """测试confidence字段范围验证（0-1）"""
        # 测试超出范围的值
        data = {
            "output_mode": "targeted",
            "user_question_focus": "测试问题",
            "confidence": 1.5,  # 超出范围
            "design_rationale": "测试",
            "targeted_analysis": {"test": "data"}
        }

        with pytest.raises(ValidationError) as exc_info:
            V6_1_FlexibleOutput(**data)

        error_msg = str(exc_info.value)
        assert "less than or equal to 1" in error_msg

    def test_invalid_output_mode(self):
        """测试无效的output_mode值"""
        data = {
            "output_mode": "invalid_mode",  # 无效模式
            "user_question_focus": "测试问题",
            "confidence": 0.8,
            "design_rationale": "测试"
        }

        with pytest.raises(ValidationError) as exc_info:
            V6_1_FlexibleOutput(**data)

        error_msg = str(exc_info.value)
        assert "Input should be 'targeted' or 'comprehensive'" in error_msg

    def test_expert_handoff_response(self):
        """测试expert_handoff_response可选字段"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "测试问题",
            "confidence": 0.85,
            "design_rationale": "测试",
            "targeted_analysis": {"test": "data"},
            "expert_handoff_response": {
                "target_role": "V2-1",
                "handoff_content": "需要V2-1进一步细化空间设计"
            }
        }

        output = V6_1_FlexibleOutput(**data)
        assert output.expert_handoff_response is not None
        assert output.expert_handoff_response["target_role"] == "V2-1"

    def test_challenge_flags(self):
        """测试challenge_flags可选字段"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "测试问题",
            "confidence": 0.85,
            "design_rationale": "测试",
            "targeted_analysis": {"test": "data"},
            "challenge_flags": [
                {
                    "issue": "结构跨度过大",
                    "severity": "must-fix",
                    "suggestion": "建议增加中间支撑柱"
                }
            ]
        }

        output = V6_1_FlexibleOutput(**data)
        assert output.challenge_flags is not None
        assert len(output.challenge_flags) == 1
        assert output.challenge_flags[0]["severity"] == "must-fix"


# ==================== V6-2: 机电与智能化工程师 ====================

class TestV6_2_FlexibleOutput:
    """V6-2 机电与智能化工程师 - 测试套件"""

    def test_targeted_mode_valid(self):
        """测试Targeted模式 - 有效输入"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何优化暖通系统能耗？",
            "confidence": 0.88,
            "design_rationale": "采用VAV变风量系统可降低30%能耗",
            "targeted_analysis": {
                "hvac_optimization": {
                    "current_system": "定风量系统",
                    "proposed_system": "VAV变风量系统",
                    "energy_savings": "30%"
                }
            }
        }

        output = V6_2_FlexibleOutput(**data)

        assert output.output_mode == "targeted"
        assert output.confidence == 0.88
        assert output.targeted_analysis is not None

    def test_comprehensive_mode_valid(self):
        """测试Comprehensive模式 - 有效输入"""
        data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整的机电系统设计",
            "confidence": 0.92,
            "design_rationale": "集成化机电设计方案",
            "mep_overall_strategy": "机电系统整体集成方案...",
            "system_solutions": [
                {
                    "system_name": "暖通系统",
                    "recommended_solution": "VAV变风量系统",
                    "reasoning": "节能30%，提升舒适度",
                    "impact_on_architecture": "需在吊顶预留600mm空间"
                }
            ],
            "smart_building_scenarios": [
                {
                    "scenario_name": "智能照明系统",
                    "description": "自动调节，节能舒适",
                    "triggered_systems": ["照明系统", "传感器系统", "中控系统"]
                }
            ],
            "coordination_and_clash_points": "机电管线综合协调...",
            "sustainability_and_energy_saving": "节能分析报告..."
        }

        output = V6_2_FlexibleOutput(**data)

        assert output.output_mode == "comprehensive"
        assert output.mep_overall_strategy is not None
        assert output.system_solutions is not None
        assert output.smart_building_scenarios is not None
        assert output.coordination_and_clash_points is not None
        assert output.sustainability_and_energy_saving is not None

    def test_comprehensive_mode_missing_fields(self):
        """测试Comprehensive模式 - 缺少必需字段"""
        data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整的机电系统设计",
            "confidence": 0.92,
            "design_rationale": "集成化机电设计方案",
            "mep_overall_strategy": "机电系统整体集成方案..."
            # 缺少其他4个必需字段
        }

        with pytest.raises(ValidationError) as exc_info:
            V6_2_FlexibleOutput(**data)

        error_msg = str(exc_info.value)
        # 验证错误信息中包含必需字段的提示
        assert ("必需字段缺失" in error_msg or "missing required fields" in error_msg.lower())


# ==================== V6-3: 室内工艺与材料专家 ====================

class TestV6_3_FlexibleOutput:
    """V6-3 室内工艺与材料专家 - 测试套件"""

    def test_material_spec_nested_model(self):
        """测试嵌套模型MaterialSpec"""
        material = MaterialSpec(
            material_name="微水泥",
            application_area="地面及墙面",
            key_specifications=["厚度3-5mm", "耐磨等级T级", "防滑系数R10"],
            reasoning="适合高端商业空间，质感细腻"
        )

        assert material.material_name == "微水泥"
        assert len(material.key_specifications) == 3
        assert "耐磨等级T级" in material.key_specifications

    def test_node_detail_nested_model(self):
        """测试嵌套模型NodeDetail"""
        node = NodeDetail(
            node_name="石材干挂节点",
            challenge="大面积石材重量大，需确保连接强度",
            proposed_solution="采用不锈钢背栓+铝合金龙骨系统，单点承载≥300kg"
        )

        assert node.node_name == "石材干挂节点"
        assert "不锈钢背栓" in node.proposed_solution

    def test_targeted_mode_with_nested_models(self):
        """测试Targeted模式 - 包含嵌套模型"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "关键材料选型建议",
            "confidence": 0.87,
            "design_rationale": "根据预算和品质要求推荐材料",
            "targeted_analysis": {
                "material_recommendation": {
                    "primary_material": "微水泥",
                    "reason": "性价比高，施工周期短"
                }
            }
        }

        output = V6_3_FlexibleOutput(**data)
        assert output.output_mode == "targeted"

    def test_comprehensive_mode_with_lists(self):
        """测试Comprehensive模式 - 包含List字段"""
        data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整的工艺与材料方案",
            "confidence": 0.9,
            "design_rationale": "系统性材料选型与工艺设计",
            "craftsmanship_strategy": "整体工艺策略...",
            "key_material_specifications": [
                {
                    "material_name": "微水泥",
                    "application_area": "地面",
                    "key_specifications": ["厚度3-5mm"],
                    "reasoning": "质感好"
                }
            ],
            "critical_node_details": [
                {
                    "node_name": "石材节点",
                    "challenge": "重量大",
                    "proposed_solution": "背栓系统"
                }
            ],
            "quality_control_and_mockup": "质量控制方案...",
            "risk_analysis": "风险评估..."
        }

        output = V6_3_FlexibleOutput(**data)

        assert output.output_mode == "comprehensive"
        assert len(output.key_material_specifications) == 1
        assert output.key_material_specifications[0].material_name == "微水泥"
        assert len(output.critical_node_details) == 1
        assert output.critical_node_details[0].node_name == "石材节点"


# ==================== V6-4: 成本与价值工程师 ====================

class TestV6_4_FlexibleOutput:
    """V6-4 成本与价值工程师 - 测试套件"""

    def test_cost_breakdown_nested_model(self):
        """测试嵌套模型CostBreakdown"""
        cost = CostBreakdown(
            category="装修工程",
            percentage=45,
            cost_drivers=["材料费占60%", "人工费占30%", "其他10%"]
        )

        assert cost.category == "装修工程"
        assert cost.percentage == 45
        assert len(cost.cost_drivers) == 3

    def test_ve_option_nested_model(self):
        """测试嵌套模型VEOption"""
        ve = VEOption(
            area="地面材料",
            original_scheme="进口大理石",
            proposed_option="国产优质石材",
            impact_analysis="节省成本30%，品质相当"
        )

        assert ve.area == "地面材料"
        assert "节省成本30%" in ve.impact_analysis

    def test_targeted_mode_valid(self):
        """测试Targeted模式 - 有效输入"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何降低成本？",
            "confidence": 0.86,
            "design_rationale": "通过价值工程优化设计",
            "targeted_analysis": {
                "cost_reduction_strategy": {
                    "target_area": "装修材料",
                    "savings_potential": "15%",
                    "methods": ["材料替换", "工艺简化"]
                }
            }
        }

        output = V6_4_FlexibleOutput(**data)
        assert output.output_mode == "targeted"
        assert output.confidence == 0.86

    def test_comprehensive_mode_with_nested_lists(self):
        """测试Comprehensive模式 - 包含嵌套List"""
        data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整的成本与价值工程分析",
            "confidence": 0.91,
            "design_rationale": "全生命周期成本优化",
            "cost_estimation_summary": "总预算800万元，含设计、施工、家具...",
            "cost_breakdown_analysis": [
                {
                    "category": "装修工程",
                    "percentage": 45,
                    "cost_drivers": ["材料费60%", "人工费30%"]
                },
                {
                    "category": "机电工程",
                    "percentage": 30,
                    "cost_drivers": ["设备费70%", "安装费20%"]
                }
            ],
            "value_engineering_options": [
                {
                    "area": "地面材料",
                    "original_scheme": "进口大理石",
                    "proposed_option": "国产石材",
                    "impact_analysis": "节省30%"
                }
            ],
            "budget_control_strategy": "预算控制策略...",
            "cost_overrun_risk_analysis": "超支风险分析..."
        }

        output = V6_4_FlexibleOutput(**data)

        assert output.output_mode == "comprehensive"
        assert len(output.cost_breakdown_analysis) == 2
        assert output.cost_breakdown_analysis[0].category == "装修工程"
        assert output.cost_breakdown_analysis[0].percentage == 45
        assert len(output.value_engineering_options) == 1
        assert output.value_engineering_options[0].area == "地面材料"


# ==================== 集成测试 ====================

class TestV6SeriesIntegration:
    """V6系列集成测试"""

    def test_all_v6_models_importable(self):
        """测试所有V6模型可导入"""
        models = [
            V6_1_FlexibleOutput,
            V6_2_FlexibleOutput,
            V6_3_FlexibleOutput,
            V6_4_FlexibleOutput
        ]

        for model in models:
            assert model is not None
            assert hasattr(model, '__name__')

    def test_all_v6_models_have_required_fields(self):
        """测试所有V6模型包含必需字段"""
        models = [V6_1_FlexibleOutput, V6_2_FlexibleOutput,
                  V6_3_FlexibleOutput, V6_4_FlexibleOutput]

        required_fields = [
            "output_mode",
            "user_question_focus",
            "confidence",
            "design_rationale"
        ]

        for model in models:
            model_fields = model.model_fields.keys()
            for field in required_fields:
                assert field in model_fields, \
                    f"{model.__name__} missing required field: {field}"

    def test_all_v6_models_have_validator(self):
        """测试所有V6模型包含验证器"""
        models = [V6_1_FlexibleOutput, V6_2_FlexibleOutput,
                  V6_3_FlexibleOutput, V6_4_FlexibleOutput]

        for model in models:
            # 检查是否有model_validator装饰的方法
            validators = [v for v in dir(model) if not v.startswith('_')]
            assert 'validate_output_consistency' in validators or \
                   any('validat' in v.lower() for v in validators), \
                   f"{model.__name__} missing validator"


# ==================== Pytest配置 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
