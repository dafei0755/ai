#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
V2系列模型测试套件 - 灵活输出架构验证

测试范围:
- V2-0: 项目设计总监
- V2-1: 居住空间设计总监
- V2-2: 商业空间设计总监
- V2-3: 办公空间设计总监
- V2-4: 酒店餐饮空间设计总监
- V2-5: 文化与公共建筑设计总监
- V2-6: 建筑及景观设计总监
"""

import pytest
from pydantic import ValidationError
from intelligent_project_analyzer.models.flexible_output import (
    V2_0_FlexibleOutput,
    V2_1_FlexibleOutput,
    V2_2_FlexibleOutput,
    V2_3_FlexibleOutput,
    V2_4_FlexibleOutput,
    V2_5_FlexibleOutput,
    V2_6_FlexibleOutput,
    SubprojectBrief,
    DesignChallenge
)


# ==================== V2-0: 项目设计总监 ====================

class TestV2_0_FlexibleOutput:
    """V2-0 项目设计总监 - 测试套件"""

    def test_subproject_brief_nested_model(self):
        """测试嵌套模型SubprojectBrief"""
        subproject = SubprojectBrief(
            subproject_name="办公区",
            area_sqm=1500.0,
            key_requirements=["开放工位", "会议室", "休息区"],
            design_priority="高"
        )

        assert subproject.subproject_name == "办公区"
        assert subproject.area_sqm == 1500.0
        assert len(subproject.key_requirements) == 3
        assert "开放工位" in subproject.key_requirements

    def test_targeted_mode_valid(self):
        """测试Targeted模式 - 有效输入"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何协调各子项目的设计？",
            "confidence": 0.88,
            "decision_rationale": "基于项目整体规划的协调策略",
            "targeted_analysis": {
                "coordination_strategy": {
                    "key_principle": "统一中有变化",
                    "approach": "建立设计语言体系，各子项目在此基础上适度变化"
                }
            }
        }

        output = V2_0_FlexibleOutput(**data)

        assert output.output_mode == "targeted"
        assert output.confidence == 0.88
        assert output.targeted_analysis is not None

    def test_comprehensive_mode_valid(self):
        """测试Comprehensive模式 - 有效输入"""
        data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整的项目设计策略",
            "confidence": 0.92,
            "decision_rationale": "系统性项目规划",
            "master_plan_strategy": "整体规划策略：功能分区+动线组织...",
            "spatial_zoning_concept": "空间分区概念：公共区-办公区-配套区...",
            "circulation_integration": "动线整合：水平动线+垂直交通系统...",
            "subproject_coordination": [
                {
                    "subproject_name": "办公区",
                    "area_sqm": 1500.0,
                    "key_requirements": ["开放工位", "会议室"],
                    "design_priority": "高"
                }
            ],
            "design_unity_and_variation": "设计统一性与变化：材料统一，色彩有变化..."
        }

        output = V2_0_FlexibleOutput(**data)

        assert output.output_mode == "comprehensive"
        assert output.master_plan_strategy is not None
        assert len(output.subproject_coordination) == 1


# ==================== V2-1: 居住空间设计总监 ====================

class TestV2_1_FlexibleOutput:
    """V2-1 居住空间设计总监 - 测试套件"""

    def test_targeted_mode_valid(self):
        """测试Targeted模式 - 有效输入"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何设计开放式厨房与客厅的关系？",
            "confidence": 0.89,
            "decision_rationale": "基于家庭互动需求的空间设计",
            "targeted_analysis": {
                "spatial_relationship": {
                    "concept": "半开放式设计",
                    "key_features": ["视觉通透", "功能独立", "互动友好"]
                }
            }
        }

        output = V2_1_FlexibleOutput(**data)

        assert output.output_mode == "targeted"
        assert output.confidence == 0.89
        assert output.targeted_analysis is not None

    def test_comprehensive_mode_valid(self):
        """测试Comprehensive模式 - 有效输入"""
        data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整的居住空间设计方案",
            "confidence": 0.91,
            "decision_rationale": "系统性空间设计",
            "project_vision_summary": "设计愿景：温馨舒适的三代同堂家居...",
            "spatial_concept": "空间概念：动静分离，公私有序...",
            "narrative_translation": "叙事转译：将家庭生活场景转化为空间语言...",
            "aesthetic_framework": "美学框架：现代简约风格，温暖色调...",
            "functional_planning": "功能规划：三房两厅布局，各功能区清晰...",
            "material_palette": "材料选择：木地板、乳胶漆、石材...",
            "implementation_guidance": "实施指导：施工图深化要点..."
        }

        output = V2_1_FlexibleOutput(**data)

        assert output.output_mode == "comprehensive"
        assert output.project_vision_summary is not None
        assert output.spatial_concept is not None
        assert output.functional_planning is not None
        assert output.material_palette is not None


# ==================== V2-2: 商业空间设计总监 ====================

class TestV2_2_FlexibleOutput:
    """V2-2 商业空间设计总监 - 测试套件"""

    def test_targeted_mode_valid(self):
        """测试Targeted模式 - 有效输入"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何优化商业动线以提升坪效？",
            "confidence": 0.87,
            "decision_rationale": "基于客流分析的动线优化策略",
            "targeted_analysis": {
                "circulation_optimization": {
                    "current_issue": "死角过多，客流覆盖不均",
                    "proposed_solution": "环形动线+节点吸引",
                    "expected_benefit": "坪效提升15%"
                }
            }
        }

        output = V2_2_FlexibleOutput(**data)

        assert output.output_mode == "targeted"
        assert output.confidence == 0.87


# ==================== V2-3/4/5/6: 其他设计总监 ====================

class TestV2_OtherDirectors:
    """V2-3/4/5/6其他设计总监 - 测试套件"""

    def test_v2_3_office_space(self):
        """测试V2-3办公空间设计总监"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何设计灵活办公空间？",
            "confidence": 0.88,
            "decision_rationale": "基于混合办公模式的空间策略",
            "targeted_analysis": {
                "flexibility_strategy": {
                    "key_concept": "模块化可变空间",
                    "design_elements": ["移动隔断", "多功能家具", "灵活布线"]
                }
            }
        }

        output = V2_3_FlexibleOutput(**data)
        assert output.output_mode == "targeted"

    def test_v2_4_hospitality_space(self):
        """测试V2-4酒店餐饮空间设计总监"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何营造高端餐厅氛围？",
            "confidence": 0.90,
            "decision_rationale": "基于感官体验的空间营造",
            "targeted_analysis": {
                "atmosphere_creation": {
                    "lighting": "低照度+重点照明",
                    "materials": "温暖质感材料",
                    "acoustics": "吸音处理，创造私密感"
                }
            }
        }

        output = V2_4_FlexibleOutput(**data)
        assert output.output_mode == "targeted"

    def test_v2_5_cultural_space(self):
        """测试V2-5文化与公共建筑设计总监"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何设计博物馆公共空间？",
            "confidence": 0.89,
            "decision_rationale": "基于参观体验的公共空间设计",
            "targeted_analysis": {
                "public_space_strategy": {
                    "circulation": "渐进式引导",
                    "rest_areas": "多层次休息节点",
                    "orientation": "清晰的导向系统"
                }
            }
        }

        output = V2_5_FlexibleOutput(**data)
        assert output.output_mode == "targeted"

    def test_v2_6_architectural_landscape(self):
        """测试V2-6建筑及景观设计总监"""
        data = {
            "output_mode": "targeted",
            "user_question_focus": "如何实现建筑与景观的融合？",
            "confidence": 0.91,
            "decision_rationale": "基于场地特质的建筑景观一体化设计",
            "targeted_analysis": {
                "integration_strategy": {
                    "concept": "建筑生长于景观",
                    "key_moves": ["延续地形", "引入绿化", "模糊边界"]
                }
            }
        }

        output = V2_6_FlexibleOutput(**data)
        assert output.output_mode == "targeted"


# ==================== 集成测试 ====================

class TestV2SeriesIntegration:
    """V2系列集成测试"""

    def test_all_v2_models_importable(self):
        """测试所有V2模型可导入"""
        models = [
            V2_0_FlexibleOutput,
            V2_1_FlexibleOutput,
            V2_2_FlexibleOutput,
            V2_3_FlexibleOutput,
            V2_4_FlexibleOutput,
            V2_5_FlexibleOutput,
            V2_6_FlexibleOutput
        ]

        for model in models:
            assert model is not None
            assert hasattr(model, '__name__')

    def test_all_v2_models_have_required_fields(self):
        """测试所有V2模型包含必需字段"""
        models = [
            V2_0_FlexibleOutput, V2_1_FlexibleOutput, V2_2_FlexibleOutput,
            V2_3_FlexibleOutput, V2_4_FlexibleOutput, V2_5_FlexibleOutput,
            V2_6_FlexibleOutput
        ]

        required_fields = [
            "output_mode",
            "user_question_focus",
            "confidence",
            "decision_rationale"  # V2使用decision_rationale而非design_rationale
        ]

        for model in models:
            model_fields = model.model_fields.keys()
            for field in required_fields:
                assert field in model_fields, \
                    f"{model.__name__} missing required field: {field}"

    def test_all_v2_models_use_decision_rationale(self):
        """测试所有V2模型使用decision_rationale而非design_rationale"""
        models = [
            V2_0_FlexibleOutput, V2_1_FlexibleOutput, V2_2_FlexibleOutput,
            V2_3_FlexibleOutput, V2_4_FlexibleOutput, V2_5_FlexibleOutput,
            V2_6_FlexibleOutput
        ]

        for model in models:
            model_fields = model.model_fields.keys()
            assert "decision_rationale" in model_fields, \
                f"{model.__name__} should use 'decision_rationale'"
            assert "design_rationale" not in model_fields, \
                f"{model.__name__} should NOT use 'design_rationale'"

    def test_comprehensive_mode_all_v2_models(self):
        """测试所有V2模型的Comprehensive模式（简化测试）"""
        # V2-0
        v2_0_data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整分析",
            "confidence": 0.9,
            "decision_rationale": "系统分析",
            "master_plan_strategy": "整体规划...",
            "spatial_zoning_concept": "空间分区...",
            "circulation_integration": "动线整合...",
            "subproject_coordination": [
                {
                    "subproject_name": "测试子项目",
                    "key_requirements": ["需求1"],
                    "design_priority": "高"
                }
            ],
            "design_unity_and_variation": "统一与变化..."
        }
        output = V2_0_FlexibleOutput(**v2_0_data)
        assert output.output_mode == "comprehensive"

        # V2-1
        v2_1_data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整分析",
            "confidence": 0.9,
            "decision_rationale": "系统分析",
            "project_vision_summary": "设计愿景...",
            "spatial_concept": "空间概念...",
            "narrative_translation": "叙事转译...",
            "aesthetic_framework": "美学框架...",
            "functional_planning": "功能规划...",
            "material_palette": "材料选择...",
            "implementation_guidance": "实施指导..."
        }
        output = V2_1_FlexibleOutput(**v2_1_data)
        assert output.output_mode == "comprehensive"

        # V2-2
        v2_2_data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整分析",
            "confidence": 0.9,
            "decision_rationale": "系统分析",
            "project_vision_summary": "设计愿景...",
            "spatial_concept": "空间概念...",
            "business_strategy_translation": "商业策略转译...",
            "aesthetic_framework": "美学框架...",
            "functional_planning": "功能规划...",
            "material_palette": "材料选择...",
            "implementation_guidance": "实施指导..."
        }
        output = V2_2_FlexibleOutput(**v2_2_data)
        assert output.output_mode == "comprehensive"

        # V2-3
        v2_3_data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整分析",
            "confidence": 0.9,
            "decision_rationale": "系统分析",
            "workspace_vision": "工作空间愿景...",
            "spatial_strategy": "空间策略...",
            "collaboration_and_focus_balance": "协作与专注平衡...",
            "brand_and_culture_expression": "品牌文化表达...",
            "implementation_guidance": "实施指导..."
        }
        output = V2_3_FlexibleOutput(**v2_3_data)
        assert output.output_mode == "comprehensive"

        # V2-4
        v2_4_data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整分析",
            "confidence": 0.9,
            "decision_rationale": "系统分析",
            "experiential_vision": "体验愿景...",
            "spatial_concept": "空间概念...",
            "sensory_design_framework": "感官设计框架...",
            "guest_journey_design": "客户旅程设计...",
            "implementation_guidance": "实施指导..."
        }
        output = V2_4_FlexibleOutput(**v2_4_data)
        assert output.output_mode == "comprehensive"

        # V2-5
        v2_5_data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整分析",
            "confidence": 0.9,
            "decision_rationale": "系统分析",
            "public_vision": "公共愿景...",
            "spatial_accessibility": "空间可达性...",
            "community_engagement": "社区参与...",
            "cultural_expression": "文化表达...",
            "implementation_guidance": "实施指导..."
        }
        output = V2_5_FlexibleOutput(**v2_5_data)
        assert output.output_mode == "comprehensive"

        # V2-6
        v2_6_data = {
            "output_mode": "comprehensive",
            "user_question_focus": "完整分析",
            "confidence": 0.9,
            "decision_rationale": "系统分析",
            "architectural_concept": "建筑概念...",
            "facade_and_envelope": "立面与围护...",
            "landscape_integration": "景观整合...",
            "indoor_outdoor_relationship": "内外关系...",
            "implementation_guidance": "实施指导..."
        }
        output = V2_6_FlexibleOutput(**v2_6_data)
        assert output.output_mode == "comprehensive"


# ==================== Pytest配置 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
