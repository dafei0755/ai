"""
Comprehensive Test Suite for Requirements Analyst v7.270 Enhancements

Tests cover:
1. L6/L7 mandatory generation
2. Entity extraction (6 types)
3. Motivation identification (12 types)
4. Problem-solving approach generation
5. L2 perspective activation
6. Human dimension depth validation
7. HAY guesthouse example (user's test case)

Author: AI Assistant
Date: 2026-01-25
"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

# Import modules to test
from intelligent_project_analyzer.agents.requirements_analyst import RequirementsAnalystAgent
from intelligent_project_analyzer.services.entity_extractor import EntityExtractor, EntityExtractionResult
from intelligent_project_analyzer.services.requirements_validator import RequirementsValidator, ValidationResult
from intelligent_project_analyzer.services.l2_perspective_activator import L2PerspectiveActivator
from intelligent_project_analyzer.core.state import ProjectAnalysisState


class TestRequirementsAnalystComprehensive:
    """Comprehensive tests for v7.270 enhancements"""

    @pytest.fixture
    def mock_llm_model(self):
        """Create a mock LLM model"""
        mock = MagicMock()
        mock.invoke = MagicMock()
        return mock

    @pytest.fixture
    def requirements_analyst(self, mock_llm_model):
        """Create RequirementsAnalystAgent instance"""
        return RequirementsAnalystAgent(llm_model=mock_llm_model)

    @pytest.fixture
    def hay_guesthouse_input(self):
        """User's HAY guesthouse example"""
        return "以丹麦家居品牌HAY气质为基础的民宿室内设计概念，四川峨眉山七里坪"

    @pytest.fixture
    def sample_phase2_result(self):
        """Sample Phase 2 result for testing"""
        return {
            "phase": 2,
            "analysis_layers": {
                "L1_facts": [
                    "用户要求基于HAY品牌气质",
                    "项目类型为民宿室内设计",
                    "地点在四川峨眉山七里坪"
                ],
                "L2_user_model": {
                    "psychological": "追求简约美学与功能主义",
                    "sociological": "中高端游客群体",
                    "aesthetic": "北欧简约风格",
                    "emotional": "从都市压力到自然宁静的情绪转换",
                    "ritual": "晨间咖啡、下午阅读的生活仪式",
                    "cultural": "融合北欧设计与川西文化"
                },
                "L3_core_tension": "HAY的几何工业感 vs 峨眉山的有机自然感",
                "L4_project_task": "为追求设计感的中高端游客，打造融合HAY简约美学与峨眉山自然环境的民宿空间",
                "L5_sharpness": {
                    "score": 85,
                    "specificity": "高",
                    "actionability": "高",
                    "depth": "中高",
                    "tension": "高"
                },
                "L6_assumption_audit": {
                    "identified_assumptions": [
                        {
                            "assumption": "HAY风格适合峨眉山环境",
                            "counter_assumption": "北欧风格可能与川西文化冲突",
                            "challenge_question": "如何验证风格融合的可行性？",
                            "impact_if_wrong": "可能导致文化不协调",
                            "alternative_approach": "采用更本土化的设计语言"
                        },
                        {
                            "assumption": "中高端游客偏好简约设计",
                            "counter_assumption": "部分游客可能更喜欢传统装饰",
                            "challenge_question": "目标客群的真实偏好是什么？",
                            "impact_if_wrong": "可能错失部分市场",
                            "alternative_approach": "提供多样化的房型选择"
                        },
                        {
                            "assumption": "HAY产品适合高海拔湿润环境",
                            "counter_assumption": "某些材料可能不耐潮湿",
                            "challenge_question": "材料在当地气候下的耐久性如何？",
                            "impact_if_wrong": "维护成本增加",
                            "alternative_approach": "选择适应当地气候的替代材料"
                        }
                    ],
                    "unconventional_approaches": [
                        "完全开放式布局，用家具定义功能区",
                        "采用'舞台化'设计，空间可快速转换",
                        "引入'时间分区'概念"
                    ]
                },
                "L7_systemic_impact": {
                    "short_term": {
                        "social": "施工期间可能影响邻里关系",
                        "environmental": "施工噪音和扬尘持续6个月",
                        "economic": "初期投资约200万元",
                        "cultural": "引入新的设计理念"
                    },
                    "medium_term": {
                        "social": "可能成为社区文化活动节点",
                        "environmental": "节能设计预计3年回收成本",
                        "economic": "预计带动周边3-5家配套服务商",
                        "cultural": "可能影响区域审美认知"
                    },
                    "long_term": {
                        "social": "可能提升社区整体品质",
                        "environmental": "可持续技术可能影响周边建筑",
                        "economic": "可能推动区域房价上涨10-15%",
                        "cultural": "设计语言可能成为区域新标杆"
                    },
                    "unintended_consequences": [
                        "成功可能导致周边租金上涨，原住民被迫迁出",
                        "设计风格可能引发低质量模仿"
                    ],
                    "mitigation_strategies": [
                        "与社区建立长期对话机制",
                        "设计中融入难以复制的在地元素"
                    ]
                }
            },
            "structured_output": {
                "project_task": "为追求设计感的中高端游客，打造融合HAY简约美学与峨眉山自然环境的民宿空间",
                "character_narrative": "32-38岁都市白领，追求品质生活",
                "physical_context": "峨眉山七里坪，海拔1300米，湿润多雾",
                "resource_constraints": "预算200万元，工期6个月",
                "regulatory_requirements": "符合民宿建设规范",
                "inspiration_references": "HAY品牌、莫干山裸心谷",
                "experience_behavior": "晨间咖啡、下午阅读、夜晚观星",
                "design_challenge": "如何在保持HAY简约美学的同时融入峨眉山自然元素",
                "emotional_landscape": "从进门时的都市压力 → 客厅的放松感 → 卧室的绝对宁静",
                "spiritual_aspirations": "通过空间找到内心平静，重新连接自然",
                "psychological_safety_needs": "需要一个不被打扰的私密角落",
                "ritual_behaviors": "晨间手冲咖啡仪式、睡前阅读时光",
                "memory_anchors": "旅行纪念品展示空间、家人照片墙"
            },
            "expert_handoff": {
                "critical_questions_for_experts": {
                    "for_v2_design_director": ["如何平衡HAY工业感与自然感？"],
                    "for_v3_narrative_expert": ["空间叙事应该是线性还是多中心？"],
                    "for_v4_design_researcher": ["需要哪些HAY产品线？"],
                    "for_v5_scenario_expert": ["哪个场景是绝对核心？"]
                },
                "design_challenge_spectrum": {
                    "pole_a_embrace": {"stance": "强化对立"},
                    "pole_b_resolve": {"stance": "寻求平衡"},
                    "pole_c_transform": {"stance": "转化创新"}
                },
                "permission_to_diverge": {
                    "message": "以上分析是起点非终点",
                    "challenge_protocol": "发现更深洞察时，请挑战需求分析师判断"
                }
            }
        }

    # ==================== L6/L7 Mandatory Generation Tests ====================

    def test_l6_always_generated(self, sample_phase2_result):
        """Test that L6 assumption audit is always present"""
        validator = RequirementsValidator()
        result = validator.validate_phase2_output(sample_phase2_result)

        # Check L6 is present
        assert result.validation_details.get("l6_present") is True
        assert result.validation_details.get("l6_count", 0) >= 3

        # Check no L6-related errors
        l6_errors = [e for e in result.errors if "L6" in e]
        assert len(l6_errors) == 0

    def test_l6_missing_triggers_generation(self, requirements_analyst, hay_guesthouse_input):
        """Test that missing L6 triggers auto-generation"""
        # Create phase2_result without L6
        phase2_result = {
            "analysis_layers": {
                "L4_project_task": "Test project task",
                "L3_core_tension": "Test tension"
            }
        }

        # Mock LLM response for L6 generation
        mock_l6_response = Mock()
        mock_l6_response.content = json.dumps({
            "identified_assumptions": [
                {
                    "assumption": "Test assumption 1",
                    "counter_assumption": "Counter 1",
                    "challenge_question": "Question 1",
                    "impact_if_wrong": "Impact 1",
                    "alternative_approach": "Alternative 1"
                },
                {
                    "assumption": "Test assumption 2",
                    "counter_assumption": "Counter 2",
                    "challenge_question": "Question 2",
                    "impact_if_wrong": "Impact 2",
                    "alternative_approach": "Alternative 2"
                },
                {
                    "assumption": "Test assumption 3",
                    "counter_assumption": "Counter 3",
                    "challenge_question": "Question 3",
                    "impact_if_wrong": "Impact 3",
                    "alternative_approach": "Alternative 3"
                }
            ],
            "unconventional_approaches": ["Approach 1", "Approach 2"]
        })
        requirements_analyst.llm_model.invoke.return_value = mock_l6_response

        # Generate missing L6
        result = requirements_analyst._generate_missing_l6(phase2_result, hay_guesthouse_input)

        # Verify L6 was added
        assert "L6_assumption_audit" in result["analysis_layers"]
        assert len(result["analysis_layers"]["L6_assumption_audit"]["identified_assumptions"]) >= 3

    def test_l7_always_generated(self, sample_phase2_result):
        """Test that L7 systemic impact is always present"""
        validator = RequirementsValidator()
        result = validator.validate_phase2_output(sample_phase2_result)

        # Check L7 is present
        assert result.validation_details.get("l7_present") is True

        # Check time dimensions
        time_dimensions = result.validation_details.get("l7_time_dimensions", [])
        assert "short_term" in time_dimensions
        assert "medium_term" in time_dimensions
        assert "long_term" in time_dimensions

        # Check no L7-related errors
        l7_errors = [e for e in result.errors if "L7" in e]
        assert len(l7_errors) == 0

    def test_l7_missing_triggers_generation(self, requirements_analyst, hay_guesthouse_input):
        """Test that missing L7 triggers auto-generation"""
        # Create phase2_result without L7
        phase2_result = {
            "analysis_layers": {
                "L4_project_task": "Test project task"
            },
            "structured_output": {
                "project_task": "Test project"
            }
        }

        # Mock LLM response for L7 generation
        mock_l7_response = Mock()
        mock_l7_response.content = json.dumps({
            "short_term": {
                "social": "Short term social impact",
                "environmental": "Short term environmental impact",
                "economic": "Short term economic impact",
                "cultural": "Short term cultural impact"
            },
            "medium_term": {
                "social": "Medium term social impact",
                "environmental": "Medium term environmental impact",
                "economic": "Medium term economic impact",
                "cultural": "Medium term cultural impact"
            },
            "long_term": {
                "social": "Long term social impact",
                "environmental": "Long term environmental impact",
                "economic": "Long term economic impact",
                "cultural": "Long term cultural impact"
            },
            "unintended_consequences": ["Consequence 1", "Consequence 2"],
            "mitigation_strategies": ["Strategy 1", "Strategy 2"]
        })
        requirements_analyst.llm_model.invoke.return_value = mock_l7_response

        # Generate missing L7
        result = requirements_analyst._generate_missing_l7(phase2_result, hay_guesthouse_input)

        # Verify L7 was added
        assert "L7_systemic_impact" in result["analysis_layers"]
        l7 = result["analysis_layers"]["L7_systemic_impact"]
        assert "short_term" in l7
        assert "medium_term" in l7
        assert "long_term" in l7
        assert len(l7.get("unintended_consequences", [])) >= 2

    # ==================== Entity Extraction Tests ====================

    def test_entity_extraction_hay_example(self, hay_guesthouse_input):
        """Test entity extraction with HAY guesthouse example"""
        extractor = EntityExtractor(llm_model=None)  # Use rule-based

        structured_data = {
            "project_task": hay_guesthouse_input,
            "character_narrative": "中高端游客",
            "physical_context": "四川峨眉山七里坪，海拔1300米",
            "inspiration_references": "HAY品牌、莫干山裸心谷"
        }

        result = extractor.extract_entities(structured_data, hay_guesthouse_input)

        # Check brand entities
        brand_names = [e["name"] for e in result.brand_entities]
        assert "HAY" in brand_names

        # Check location entities
        location_names = [e["name"] for e in result.location_entities]
        assert any("峨眉山" in name or "七里坪" in name for name in location_names)

        # Check style entities
        style_names = [e["name"] for e in result.style_entities]
        # Should detect "北欧" or "简约" if present in context

        # Check scene entities
        scene_names = [e["name"] for e in result.scene_entities]
        assert "民宿" in scene_names

        # Total entities should be > 0
        assert result.total_entities() > 0

    def test_entity_extraction_result_structure(self):
        """Test EntityExtractionResult structure"""
        result = EntityExtractionResult(
            brand_entities=[{"name": "HAY", "description": "Danish brand"}],
            location_entities=[{"name": "峨眉山", "description": "Mountain"}],
            extraction_method="rule_based",
            confidence=0.8
        )

        # Test to_dict
        result_dict = result.to_dict()
        assert "brand" in result_dict
        assert "location" in result_dict
        assert result_dict["extraction_method"] == "rule_based"
        assert result_dict["confidence"] == 0.8

        # Test total_entities
        assert result.total_entities() == 2

    # ==================== Motivation Identification Tests ====================

    def test_motivation_identification_hay_example(self, hay_guesthouse_input):
        """Test motivation type identification for HAY example"""
        # Expected motivations: aesthetic (primary), cultural, commercial

        # This test would require MotivationEngine to be properly initialized
        # For now, we test the structure
        expected_primary = "aesthetic"
        expected_secondary = ["cultural", "commercial"]

        # Verify motivation types exist in config
        from intelligent_project_analyzer.config.motivation_types import MOTIVATION_TYPES
        assert expected_primary in [m["id"] for m in MOTIVATION_TYPES]
        for sec in expected_secondary:
            assert sec in [m["id"] for m in MOTIVATION_TYPES]

    # ==================== Problem-Solving Approach Tests ====================

    def test_problem_solving_approach_structure(self, requirements_analyst, hay_guesthouse_input, sample_phase2_result):
        """Test problem-solving approach has correct structure"""
        # Mock LLM response
        mock_response = Mock()
        mock_response.content = json.dumps({
            "task_type": "design",
            "task_type_description": "室内设计任务",
            "complexity_level": "complex",
            "required_expertise": ["室内设计", "品牌美学", "地域文化"],
            "solution_steps": [
                {
                    "step_id": "S1",
                    "action": "解析HAY品牌核心设计语言",
                    "purpose": "建立美学参照系",
                    "expected_output": "HAY设计哲学文档"
                },
                {
                    "step_id": "S2",
                    "action": "提取HAY色彩系统",
                    "purpose": "确定色彩方案",
                    "expected_output": "色彩板"
                }
            ],
            "breakthrough_points": [
                {
                    "point": "几何工业感与有机自然感的融合",
                    "why_key": "这是核心矛盾",
                    "how_to_leverage": "用HAY框架结合自然材料"
                }
            ],
            "expected_deliverable": {
                "format": "report",
                "sections": ["设计理念", "色彩方案", "材质选择"],
                "key_elements": ["视觉参考", "产品推荐"],
                "quality_criteria": ["可执行性", "协调性"]
            },
            "alternative_approaches": ["如果HAY产品不可用，使用类似品牌"],
            "confidence_score": 0.85
        })
        requirements_analyst.llm_model.invoke.return_value = mock_response

        # Generate problem-solving approach
        approach = requirements_analyst._generate_problem_solving_approach(
            hay_guesthouse_input,
            sample_phase2_result
        )

        # Verify structure
        assert approach is not None
        assert approach.task_type == "design"
        assert approach.complexity_level == "complex"
        assert len(approach.required_expertise) >= 3
        assert len(approach.solution_steps) >= 2
        assert len(approach.breakthrough_points) >= 1
        assert approach.expected_deliverable is not None
        assert approach.confidence_score > 0

    # ==================== L2 Perspective Activation Tests ====================

    def test_l2_perspective_activation_commercial(self):
        """Test L2 extended perspectives activate correctly for commercial projects"""
        activator = L2PerspectiveActivator()

        # Commercial project with business keywords
        user_input = "设计一个高端咖啡厅，需要考虑ROI和坪效"
        project_type = "commercial_enterprise"

        active = activator.determine_active_perspectives(
            project_type=project_type,
            user_input=user_input
        )

        # Should activate business perspective
        assert "business" in active
        # Base perspectives should always be present
        assert "psychological" in active
        assert "sociological" in active

    def test_l2_perspective_activation_cultural(self):
        """Test L2 cultural perspective activates for cultural projects"""
        activator = L2PerspectiveActivator()

        # Cultural project
        user_input = "设计一个传统文化展示空间，融合地域特色"
        project_type = "cultural_educational"

        active = activator.determine_active_perspectives(
            project_type=project_type,
            user_input=user_input
        )

        # Should activate cultural perspective
        assert "cultural" in active

    # ==================== Human Dimension Validation Tests ====================

    def test_human_dimension_depth_validation(self, sample_phase2_result):
        """Test human dimensions are specific, not generic"""
        validator = RequirementsValidator()
        result = validator.validate_phase2_output(sample_phase2_result)

        # Check human dimensions were validated
        assert "human_dimensions" in result.validation_details

        # Check for generic phrase detection
        dims = result.validation_details["human_dimensions"]
        for dim_name, dim_result in dims.items():
            # Should have quality assessment
            assert "quality" in dim_result
            # Should check for generic phrases
            assert "has_generic_phrases" in dim_result

    def test_human_dimension_rejects_generic_phrases(self):
        """Test that generic phrases are detected and flagged"""
        validator = RequirementsValidator()

        # Create phase2_result with generic phrases
        phase2_result = {
            "analysis_layers": {
                "L6_assumption_audit": {
                    "identified_assumptions": [
                        {"assumption": "a", "counter_assumption": "b", "challenge_question": "c"},
                        {"assumption": "d", "counter_assumption": "e", "challenge_question": "f"},
                        {"assumption": "g", "counter_assumption": "h", "challenge_question": "i"}
                    ]
                },
                "L7_systemic_impact": {
                    "short_term": {"social": "a"},
                    "medium_term": {"social": "b"},
                    "long_term": {"social": "c"}
                }
            },
            "structured_output": {
                "emotional_landscape": "温馨舒适的氛围",  # Generic!
                "spiritual_aspirations": "追求品质生活",  # Generic!
                "psychological_safety_needs": "需要安全感和归属感",  # Generic!
                "ritual_behaviors": "日常生活仪式",
                "memory_anchors": "家的记忆"
            },
            "expert_handoff": {}
        }

        result = validator.validate_phase2_output(phase2_result)

        # Should have warnings about generic phrases
        generic_warnings = [w for w in result.warnings if "generic" in w.lower()]
        assert len(generic_warnings) > 0

    # ==================== Integration Tests ====================

    def test_full_pipeline_hay_example(self, requirements_analyst, hay_guesthouse_input):
        """Test full pipeline with HAY guesthouse example"""
        # This would require full integration test setup
        # For now, verify components are initialized
        assert requirements_analyst.entity_extractor is not None
        assert requirements_analyst.requirements_validator is not None
        assert requirements_analyst.l2_activator is not None
        assert requirements_analyst.motivation_engine is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
