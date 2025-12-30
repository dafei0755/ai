#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V5系列模型测试套件 - 灵活输出架构验证

测试范围:
- V5-0: 通用场景策略师
- V5-1: 居住场景与生活方式专家
- V5-2: 商业零售运营专家
- V5-3: 企业办公策略专家
- V5-4: 酒店餐饮运营专家
- V5-5: 文化教育场景专家
- V5-6: 医疗康养场景专家
"""

import pytest
from pydantic import ValidationError
from intelligent_project_analyzer.models.flexible_output import (
    V5_0_FlexibleOutput,
    V5_1_FlexibleOutput,
    V5_2_FlexibleOutput,
    V5_3_FlexibleOutput,
    V5_4_FlexibleOutput,
    V5_5_FlexibleOutput,
    V5_6_FlexibleOutput,
    FamilyMemberProfile,
    DesignChallenge,
    RetailKPI
)


# ==================== V5-0: 通用场景策略师 ====================

class TestV5_0_FlexibleOutput:
    """V5-0 通用场景策略师 - 测试套件"""

    def test_targeted_mode_valid(self):
        """测试Targeted模式 - 有效输入"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何优化餐厅运营流程？",
            "confidence": 0.87,
            "design_rationale": "基于餐饮运营效率优化的分析",
            "targeted_analysis": {
                "operational_optimization": {
                    "current_issues": ["翻台率低", "人效不高"],
                    "proposed_solutions": ["优化动线", "增加自助点餐"],
                    "expected_improvement": "翻台率提升30%"
                }
            }
        }

        output = V5_0_FlexibleOutput(**data)

        assert output.output_mode == "targeted"
        assert output.confidence == 0.87
        assert output.targeted_analysis is not None

    def test_comprehensive_mode_valid(self):
        """测试Comprehensive模式 - 有效输入"""
        data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整的场景策略分析",
            "confidence": 0.9,
            "design_rationale": "系统性场景分析",
            "scenario_deconstruction": "场景拆解：前厅-后厨-客流动线...",
            "operational_logic": "运营逻辑：高峰期3小时，平均停留45分钟...",
            "stakeholder_analysis": "利益相关方：顾客、服务员、厨师、管理者...",
            "key_performance_indicators": ["翻台率", "人效", "满意度"],
            "design_challenges_for_v2": [
                {
                    "challenge": "高峰期客流拥挤",
                    "context": "午餐时段12-14点客流集中",
                    "constraints": ["面积有限", "无法大幅扩张", "预算受限"]
                }
            ]
        }

        output = V5_0_FlexibleOutput(**data)

        assert output.output_mode == "comprehensive"
        assert output.scenario_deconstruction is not None
        assert len(output.key_performance_indicators) == 3
        assert len(output.design_challenges_for_v2) == 1


# ==================== V5-1: 居住场景与生活方式专家 ====================

class TestV5_1_FlexibleOutput:
    """V5-1 居住场景与生活方式专家 - 测试套件"""

    def test_family_member_profile_nested_model(self):
        """测试嵌套模型FamilyMemberProfile"""
        member = FamilyMemberProfile(
            member="父亲（45岁，IT从业者）",
            daily_routine="早7点出门，晚8点到家，周末在家办公",
            spatial_needs=["独立书房", "隔音环境", "双显示器工位"],
            storage_needs=["大量技术书籍", "电子设备", "文件柜"]
        )

        assert member.member == "父亲（45岁，IT从业者）"
        assert "独立书房" in member.spatial_needs
        assert len(member.spatial_needs) == 3

    def test_targeted_mode_valid(self):
        """测试Targeted模式 - 有效输入"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何设计三代同堂的动线？",
            "confidence": 0.89,
            "design_rationale": "基于家庭成员作息差异的动线规划",
            "targeted_analysis": {
                "circulation_strategy": {
                    "key_principle": "动静分离，减少干扰",
                    "design_approach": "主卧套房化，老人房靠近客厅"
                }
            }
        }

        output = V5_1_FlexibleOutput(**data)

        assert output.output_mode == "targeted"
        assert output.targeted_analysis is not None

    def test_comprehensive_mode_with_nested_models(self):
        """测试Comprehensive模式 - 包含嵌套模型"""
        data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整的居住场景分析",
            "confidence": 0.92,
            "design_rationale": "系统性生活方式研究",
            "family_profile_and_needs": [
                {
                    "member": "父亲（45岁）",
                    "daily_routine": "早出晚归",
                    "spatial_needs": ["独立书房", "隔音环境"],
                    "storage_needs": ["书籍", "设备"]
                },
                {
                    "member": "母亲（42岁）",
                    "daily_routine": "在家工作",
                    "spatial_needs": ["开放工作区", "充足采光"],
                    "storage_needs": ["文件资料", "办公用品"]
                }
            ],
            "operational_blueprint": "生活蓝图：工作日和周末的时空分布...",
            "key_performance_indicators": ["家庭互动频率", "私密性满意度"],
            "design_challenges_for_v2": [
                {
                    "challenge": "三代作息冲突",
                    "context": "老人早睡，年轻人晚睡",
                    "constraints": ["面积有限", "隔音要求高"]
                }
            ]
        }

        output = V5_1_FlexibleOutput(**data)

        assert output.output_mode == "comprehensive"
        assert len(output.family_profile_and_needs) == 2
        assert output.family_profile_and_needs[0].member == "父亲（45岁）"


# ==================== V5-2: 商业零售运营专家 ====================

class TestV5_2_FlexibleOutput:
    """V5-2 商业零售运营专家 - 测试套件"""

    def test_retail_kpi_nested_model(self):
        """测试嵌套模型RetailKPI"""
        kpi = RetailKPI(
            metric="坪效",
            target="年坪效≥3万元/㎡",
            spatial_strategy="需优化商品陈列密度和动线效率"
        )

        assert kpi.metric == "坪效"
        assert "3万元" in kpi.target

    def test_targeted_mode_valid(self):
        """测试Targeted模式 - 有效输入"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何提升坪效？",
            "confidence": 0.86,
            "design_rationale": "基于零售运营效率的空间优化",
            "targeted_analysis": {
                "space_efficiency": {
                    "current_pinxiao": "2.5万元/㎡",
                    "target_pinxiao": "3.5万元/㎡",
                    "strategies": ["优化陈列", "增加体验区", "提升转化率"]
                }
            }
        }

        output = V5_2_FlexibleOutput(**data)

        assert output.output_mode == "targeted"
        assert output.confidence == 0.86


# ==================== V5-3/4/5/6: 其他场景专家 ====================

class TestV5_OtherScenarios:
    """V5-3/4/5/6其他场景专家 - 测试套件"""

    def test_v5_3_office_scenario(self):
        """测试V5-3企业办公策略专家"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何设计混合办公空间？",
            "confidence": 0.88,
            "design_rationale": "基于后疫情时代的办公模式变化",
            "targeted_analysis": {
                "hybrid_work_strategy": {
                    "flexible_workstations": "40%开放工位",
                    "collaboration_zones": "30%协作区",
                    "focus_areas": "30%专注区"
                }
            }
        }

        output = V5_3_FlexibleOutput(**data)
        assert output.output_mode == "targeted"

    def test_v5_4_hospitality_scenario(self):
        """测试V5-4酒店餐饮运营专家"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何优化客房服务流程？",
            "confidence": 0.87,
            "design_rationale": "基于客户体验和运营效率的双重优化",
            "targeted_analysis": {
                "service_optimization": {
                    "check_in_time": "从15分钟降至5分钟",
                    "room_turnover": "清洁效率提升20%"
                }
            }
        }

        output = V5_4_FlexibleOutput(**data)
        assert output.output_mode == "targeted"

    def test_v5_5_cultural_scenario(self):
        """测试V5-5文化教育场景专家"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何设计博物馆参观流线？",
            "confidence": 0.90,
            "design_rationale": "基于观众认知规律的展览叙事",
            "targeted_analysis": {
                "visitor_flow": {
                    "route_design": "线性叙事 + 主题跳转",
                    "dwell_time": "平均每展区15分钟"
                }
            }
        }

        output = V5_5_FlexibleOutput(**data)
        assert output.output_mode == "targeted"

    def test_v5_6_healthcare_scenario(self):
        """测试V5-6医疗康养场景专家"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何优化就诊流程？",
            "confidence": 0.89,
            "design_rationale": "基于患者体验和医疗效率的平衡",
            "targeted_analysis": {
                "clinical_flow": {
                    "registration_to_consultation": "从30分钟降至15分钟",
                    "privacy_zones": "设置独立问诊隔间"
                }
            }
        }

        output = V5_6_FlexibleOutput(**data)
        assert output.output_mode == "targeted"


# ==================== 集成测试 ====================

class TestV5SeriesIntegration:
    """V5系列集成测试"""

    def test_all_v5_models_importable(self):
        """测试所有V5模型可导入"""
        models = [
            V5_0_FlexibleOutput,
            V5_1_FlexibleOutput,
            V5_2_FlexibleOutput,
            V5_3_FlexibleOutput,
            V5_4_FlexibleOutput,
            V5_5_FlexibleOutput,
            V5_6_FlexibleOutput
        ]

        for model in models:
            assert model is not None
            assert hasattr(model, '__name__')

    def test_all_v5_models_have_required_fields(self):
        """测试所有V5模型包含必需字段"""
        models = [
            V5_0_FlexibleOutput, V5_1_FlexibleOutput, V5_2_FlexibleOutput,
            V5_3_FlexibleOutput, V5_4_FlexibleOutput, V5_5_FlexibleOutput,
            V5_6_FlexibleOutput
        ]

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

    def test_all_v5_models_have_design_challenges_for_v2(self):
        """测试所有V5模型包含design_challenges_for_v2字段"""
        models = [
            V5_0_FlexibleOutput, V5_1_FlexibleOutput, V5_2_FlexibleOutput,
            V5_3_FlexibleOutput, V5_4_FlexibleOutput, V5_5_FlexibleOutput,
            V5_6_FlexibleOutput
        ]

        for model in models:
            model_fields = model.model_fields.keys()
            assert "design_challenges_for_v2" in model_fields, \
                f"{model.__name__} missing design_challenges_for_v2 field"

    def test_comprehensive_mode_all_v5_models(self):
        """测试所有V5模型的Comprehensive模式（简化测试）"""
        # V5-0
        v5_0_data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整分析",
            "confidence": 0.9,
            "design_rationale": "系统分析",
            "scenario_deconstruction": "场景拆解...",
            "operational_logic": "运营逻辑...",
            "stakeholder_analysis": "利益相关方...",
            "key_performance_indicators": ["KPI1"],
            "design_challenges_for_v2": [
                {
                    "challenge": "测试挑战",
                    "context": "测试上下文",
                    "constraints": ["约束1"]
                }
            ]
        }
        output = V5_0_FlexibleOutput(**v5_0_data)
        assert output.output_mode == "comprehensive"

        # V5-1
        v5_1_data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整分析",
            "confidence": 0.9,
            "design_rationale": "系统分析",
            "family_profile_and_needs": [
                {
                    "member": "测试成员",
                    "daily_routine": "日常作息",
                    "spatial_needs": ["需求1"],
                    "storage_needs": ["储物1"]
                }
            ],
            "operational_blueprint": "运营蓝图...",
            "key_performance_indicators": ["KPI1"],
            "design_challenges_for_v2": [
                {
                    "challenge": "测试挑战",
                    "context": "测试上下文",
                    "constraints": ["约束1"]
                }
            ]
        }
        output = V5_1_FlexibleOutput(**v5_1_data)
        assert output.output_mode == "comprehensive"

        # V5-2
        v5_2_data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整分析",
            "confidence": 0.9,
            "design_rationale": "系统分析",
            "business_goal_analysis": "商业目标分析...",
            "operational_blueprint": "运营蓝图...",
            "key_performance_indicators": [
                {
                    "metric": "坪效",
                    "target": "年坪效≥3万元/㎡",
                    "spatial_strategy": "优化商品陈列密度和动线效率"
                }
            ],
            "design_challenges_for_v2": [
                {
                    "challenge": "测试挑战",
                    "context": "测试上下文",
                    "constraints": ["约束1"]
                }
            ]
        }
        output = V5_2_FlexibleOutput(**v5_2_data)
        assert output.output_mode == "comprehensive"


# ==================== Pytest配置 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
