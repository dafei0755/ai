#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V3/V4系列模型测试套件 - 灵活输出架构验证

测试范围:
- V3-1: 个体叙事与心理洞察专家
- V3-2: 品牌叙事与顾客体验专家
- V3-3: 空间叙事与情感体验专家
- V4-1: 设计研究者
- V4-2: 趋势研究与未来洞察专家
"""

import pytest
from pydantic import ValidationError
from intelligent_project_analyzer.models.flexible_output import (
    V3_1_FlexibleOutput,
    V3_2_FlexibleOutput,
    V3_3_FlexibleOutput,
    V4_1_FlexibleOutput,
    V4_2_FlexibleOutput,
    TouchpointScript
)


# ==================== V3-1: 个体叙事与心理洞察专家 ====================

class TestV3_1_FlexibleOutput:
    """V3-1 个体叙事与心理洞察专家 - 测试套件"""

    def test_targeted_mode_valid(self):
        """测试Targeted模式 - 有效输入"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何理解居住者的心理需求？",
            "confidence": 0.89,
            "design_rationale": "基于心理学理论的空间需求分析",
            "targeted_analysis": {
                "psychological_insight": {
                    "key_trait": "内向型人格，需要私密空间",
                    "spatial_preference": "封闭式书房，柔和照明",
                    "design_recommendation": "独立隔音空间+可控光环境"
                }
            }
        }

        output = V3_1_FlexibleOutput(**data)

        assert output.output_mode == "targeted"
        assert output.confidence == 0.89
        assert output.targeted_analysis is not None

    def test_comprehensive_mode_valid(self):
        """测试Comprehensive模式 - 有效输入"""
        data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整的个体叙事分析",
            "confidence": 0.91,
            "design_rationale": "深度心理洞察",
            "individual_narrative_core": "核心叙事：追求工作生活平衡的职业人士...",
            "psychological_profile": "心理画像：理性、追求效率、重视家庭...",
            "lifestyle_blueprint": "生活方式蓝图：工作日快节奏，周末慢生活...",
            "key_spatial_moments": [
                {
                    "touchpoint_name": "早晨出门前",
                    "emotional_goal": "高效有序，减少焦虑",
                    "sensory_script": "充足储物，快速动线，柔和晨光"
                }
            ],
            "narrative_guidelines_for_v2": "设计指导：主卧套房化，提升早晨效率..."
        }

        output = V3_1_FlexibleOutput(**data)

        assert output.output_mode == "comprehensive"
        assert output.individual_narrative_core is not None
        assert len(output.key_spatial_moments) == 1


# ==================== V3-2: 品牌叙事与顾客体验专家 ====================

class TestV3_2_FlexibleOutput:
    """V3-2 品牌叙事与顾客体验专家 - 测试套件"""

    def test_touchpoint_script_nested_model(self):
        """测试嵌套模型TouchpointScript"""
        touchpoint = TouchpointScript(
            touchpoint_name="进入店铺",
            emotional_goal="让顾客感到受欢迎和期待",
            sensory_script="宽敞入口，柔和灯光，清晰导视，吸引力陈列"
        )

        assert touchpoint.touchpoint_name == "进入店铺"
        assert "受欢迎" in touchpoint.emotional_goal
        assert len(touchpoint.sensory_script) > 0

    def test_targeted_mode_valid(self):
        """测试Targeted模式 - 有效输入"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何强化品牌调性？",
            "confidence": 0.88,
            "design_rationale": "基于品牌DNA的空间体验设计",
            "targeted_analysis": {
                "brand_expression": {
                    "brand_essence": "轻奢、精致、有温度",
                    "spatial_translation": "高级材料+温暖色调+柔和灯光",
                    "key_touchpoints": ["入口", "收银", "试衣间"]
                }
            }
        }

        output = V3_2_FlexibleOutput(**data)

        assert output.output_mode == "targeted"
        assert output.confidence == 0.88


# ==================== V3-3: 空间叙事与情感体验专家 ====================

class TestV3_3_FlexibleOutput:
    """V3-3 空间叙事与情感体验专家 - 测试套件"""

    def test_targeted_mode_valid(self):
        """测试Targeted模式 - 有效输入"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何营造情感共鸣的空间？",
            "confidence": 0.90,
            "design_rationale": "基于情感体验的空间叙事设计",
            "targeted_analysis": {
                "emotional_journey": {
                    "entry_emotion": "好奇期待",
                    "peak_emotion": "惊喜感动",
                    "exit_emotion": "满足留恋",
                    "spatial_strategy": "渐进式揭示+高潮节点+回味空间"
                }
            }
        }

        output = V3_3_FlexibleOutput(**data)

        assert output.output_mode == "targeted"
        assert output.confidence == 0.90


# ==================== V4-1: 设计研究者 ====================

class TestV4_1_FlexibleOutput:
    """V4-1 设计研究者 - 测试套件"""

    def test_targeted_mode_valid(self):
        """测试Targeted模式 - 有效输入"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "目标用户的核心需求是什么？",
            "confidence": 0.87,
            "design_rationale": "基于用户研究的需求洞察",
            "targeted_analysis": {
                "user_insight": {
                    "target_user": "25-35岁都市白领",
                    "core_needs": ["效率", "社交", "放松"],
                    "pain_points": ["通勤时间长", "工作压力大"],
                    "opportunities": ["提供高效办公+社交空间"]
                }
            }
        }

        output = V4_1_FlexibleOutput(**data)

        assert output.output_mode == "targeted"
        assert output.confidence == 0.87


# ==================== V4-2: 趋势研究与未来洞察专家 ====================

class TestV4_2_FlexibleOutput:
    """V4-2 趋势研究与未来洞察专家 - 测试套件"""

    def test_targeted_mode_valid(self):
        """测试Targeted模式 - 有效输入"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "未来办公空间的趋势是什么？",
            "confidence": 0.86,
            "design_rationale": "基于趋势研究的前瞻洞察",
            "targeted_analysis": {
                "future_trend": {
                    "trend_name": "混合办公常态化",
                    "key_drivers": ["疫情影响", "Z世代价值观", "技术赋能"],
                    "design_implications": ["灵活工位", "协作空间", "远程会议设施"],
                    "adoption_timeline": "2-3年内成为主流"
                }
            }
        }

        output = V4_2_FlexibleOutput(**data)

        assert output.output_mode == "targeted"
        assert output.confidence == 0.86

    def test_comprehensive_mode_valid(self):
        """测试Comprehensive模式 - 有效输入"""
        data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整的趋势研究报告",
            "confidence": 0.90,
            "design_rationale": "系统性趋势分析",
            "trend_analysis": "趋势分析：混合办公、ESG可持续、健康建筑...",
            "future_scenarios": "未来场景：2030年的办公空间可能是...",
            "opportunity_identification": "机会识别：灵活空间需求增长200%...",
            "design_implications": "设计启示：模块化、可变、绿色...",
            "risk_assessment": "风险评估：技术迭代快，投资回报不确定..."
        }

        output = V4_2_FlexibleOutput(**data)

        assert output.output_mode == "comprehensive"
        assert output.trend_analysis is not None


# ==================== 集成测试 ====================

class TestV3V4SeriesIntegration:
    """V3/V4系列集成测试"""

    def test_all_v3_v4_models_importable(self):
        """测试所有V3/V4模型可导入"""
        models = [
            V3_1_FlexibleOutput,
            V3_2_FlexibleOutput,
            V3_3_FlexibleOutput,
            V4_1_FlexibleOutput,
            V4_2_FlexibleOutput
        ]

        for model in models:
            assert model is not None
            assert hasattr(model, '__name__')

    def test_all_v3_v4_models_have_required_fields(self):
        """测试所有V3/V4模型包含必需字段"""
        models = [
            V3_1_FlexibleOutput, V3_2_FlexibleOutput, V3_3_FlexibleOutput,
            V4_1_FlexibleOutput, V4_2_FlexibleOutput
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

    def test_v3_models_have_touchpoint_or_narrative_fields(self):
        """测试所有V3模型包含叙事相关字段"""
        v3_models = [V3_1_FlexibleOutput, V3_2_FlexibleOutput, V3_3_FlexibleOutput]

        for model in v3_models:
            model_fields = model.model_fields.keys()
            # V3系列应该有叙事相关的字段
            has_narrative_field = any(
                'narrative' in field.lower() or
                'touchpoint' in field.lower() or
                'spatial_moments' in field.lower()
                for field in model_fields
            )
            assert has_narrative_field, \
                f"{model.__name__} should have narrative-related fields"

    def test_comprehensive_mode_v3_models(self):
        """测试所有V3模型的Comprehensive模式"""
        # V3-1
        v3_1_data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整分析",
            "confidence": 0.9,
            "design_rationale": "系统分析",
            "individual_narrative_core": "核心叙事...",
            "psychological_profile": "心理画像...",
            "lifestyle_blueprint": "生活方式蓝图...",
            "key_spatial_moments": [
                {
                    "touchpoint_name": "早晨出门",
                    "emotional_goal": "高效有序",
                    "sensory_script": "快速动线，柔和光线"
                }
            ],
            "narrative_guidelines_for_v2": "设计指导..."
        }
        output = V3_1_FlexibleOutput(**v3_1_data)
        assert output.output_mode == "comprehensive"

        # V3-2
        v3_2_data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整分析",
            "confidence": 0.9,
            "design_rationale": "系统分析",
            "brand_narrative_core": "品牌叙事核心...",
            "customer_archetype": "顾客原型...",
            "emotional_journey_map": "情感旅程地图...",
            "key_touchpoint_scripts": [
                {
                    "touchpoint_name": "进店",
                    "emotional_goal": "感到欢迎",
                    "sensory_script": "宽敞入口，柔和灯光"
                }
            ],
            "narrative_guidelines_for_v2": "叙事指导..."
        }
        output = V3_2_FlexibleOutput(**v3_2_data)
        assert output.output_mode == "comprehensive"

        # V3-3
        v3_3_data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整分析",
            "confidence": 0.9,
            "design_rationale": "系统分析",
            "spatial_narrative_concept": "空间叙事概念...",
            "emotional_journey_map": "情感旅程地图...",
            "sensory_experience_design": "感官体验设计...",
            "key_spatial_moments": [
                {
                    "touchpoint_name": "入口体验",
                    "emotional_goal": "好奇期待",
                    "sensory_script": "开敞空间，迎宾氛围"
                }
            ],
            "narrative_guidelines_for_v2": "叙事指导..."
        }
        output = V3_3_FlexibleOutput(**v3_3_data)
        assert output.output_mode == "comprehensive"

    def test_comprehensive_mode_v4_models(self):
        """测试所有V4模型的Comprehensive模式"""
        # V4-1
        v4_1_data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整分析",
            "confidence": 0.9,
            "design_rationale": "系统分析",
            "research_focus": "研究焦点...",
            "methodology": "研究方法...",
            "key_findings": ["发现1", "发现2", "发现3"],
            "design_implications": "设计启示...",
            "evidence_base": "证据基础..."
        }
        output = V4_1_FlexibleOutput(**v4_1_data)
        assert output.output_mode == "comprehensive"

        # V4-2
        v4_2_data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整分析",
            "confidence": 0.9,
            "design_rationale": "系统分析",
            "trend_analysis": "趋势分析...",
            "future_scenarios": "未来场景...",
            "opportunity_identification": "机会识别...",
            "design_implications": "设计启示...",
            "risk_assessment": "风险评估..."
        }
        output = V4_2_FlexibleOutput(**v4_2_data)
        assert output.output_mode == "comprehensive"


# ==================== Pytest配置 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
