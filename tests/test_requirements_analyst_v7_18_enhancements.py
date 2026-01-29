"""
测试需求分析师 v7.18.0 增强功能

测试内容：
1. L6 假设审计功能
2. L2 扩展域视角（商业/技术/生态/文化/政治）
3. 条件激活机制
4. 置信度计算更新

作者：Design Beyond Team
日期：2026-01-22
"""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest

from intelligent_project_analyzer.agents.requirements_analyst import RequirementsAnalystAgent
from intelligent_project_analyzer.core.state import AgentType, ProjectAnalysisState


@pytest.fixture
def mock_llm():
    """创建模拟的LLM实例"""
    llm = Mock()
    return llm


@pytest.fixture
def requirements_analyst(mock_llm):
    """创建需求分析师实例"""
    return RequirementsAnalystAgent(llm_model=mock_llm)


class TestL6AssumptionAudit:
    """测试L6假设审计功能"""

    def test_l6_assumption_audit_in_phase2_output(self, requirements_analyst, mock_llm):
        """测试Phase2输出包含L6假设审计"""

        # 模拟Phase2 LLM响应（包含L6）
        phase2_response = {
            "phase": 2,
            "analysis_layers": {
                "L1_facts": ["用户是35岁创业者", "需要家庭办公空间"],
                "L2_user_model": {
                    "psychological": "追求效率与平衡",
                    "sociological": "创业者身份",
                    "aesthetic": "现代简约",
                    "emotional": "工作压力→家庭放松",
                    "ritual": "晨间咖啡、晚间阅读",
                },
                "L3_core_tension": "工作效率 vs 家庭温馨",
                "L4_project_task": "为创业者打造兼顾工作与家庭的空间",
                "L5_sharpness": {"score": 75, "specificity": "高", "actionability": "高", "depth": "中", "tension": "高"},
                "L6_assumption_audit": {
                    "identified_assumptions": [
                        {
                            "assumption": "工作与家庭需要物理分隔",
                            "evidence": "基于'工作vs家庭'对立",
                            "counter_assumption": "可以通过时间分隔实现",
                            "challenge_question": "如果同一空间在不同时段承担不同功能？",
                            "impact_if_wrong": "过度分隔可能浪费空间",
                            "alternative_approach": "使用可变家具和灯光",
                        },
                        {
                            "assumption": "创业者需要独立办公室",
                            "evidence": "职业需求推断",
                            "counter_assumption": "开放式空间可能更激发创造力",
                            "challenge_question": "如果工作融入生活场景？",
                            "impact_if_wrong": "错失灵活性",
                            "alternative_approach": "多个工作角落而非单一办公室",
                        },
                        {
                            "assumption": "效率优先于舒适",
                            "evidence": "创业者标签",
                            "counter_assumption": "舒适可能提升长期效率",
                            "challenge_question": "如果舒适本身就是效率的一部分？",
                            "impact_if_wrong": "忽视长期健康和可持续性",
                            "alternative_approach": "设计支持长时间舒适工作的空间",
                        },
                    ],
                    "unconventional_approaches": ["完全开放式布局，用家具定义功能", "采用'游牧式'工作，多个工作点", "时间分区：同一空间不同时段不同功能"],
                },
            },
            "structured_output": {
                "project_task": "为创业者打造兼顾工作与家庭的空间",
                "character_narrative": "35岁创业者",
                "physical_context": "100㎡两居室",
                "resource_constraints": "预算50万",
                "regulatory_requirements": "住宅标准",
                "inspiration_references": "北欧简约",
                "experience_behavior": "工作-生活切换",
                "design_challenge": "工作效率 vs 家庭温馨",
                "emotional_landscape": "工作压力→家庭放松",
                "spiritual_aspirations": "追求工作生活平衡",
                "psychological_safety_needs": "需要专注空间",
                "ritual_behaviors": "晨间咖啡、晚间阅读",
                "memory_anchors": "创业纪念品",
            },
            "expert_handoff": {
                "critical_questions_for_experts": {},
                "design_challenge_spectrum": {},
                "permission_to_diverge": {},
            },
        }

        mock_llm.invoke.return_value = Mock(content=json.dumps(phase2_response, ensure_ascii=False))

        # 模拟Phase1结果
        phase1_result = {
            "phase": 1,
            "info_status": "sufficient",
            "primary_deliverables": [{"deliverable_id": "D1", "type": "design_strategy"}],
            "project_type_preliminary": "personal_residential",
        }

        # 执行Phase2
        user_input = "我是创业者，需要在家办公，但也要照顾家庭"
        phase2_result = requirements_analyst._execute_phase2(user_input, phase1_result)

        # 验证L6存在
        assert "L6_assumption_audit" in phase2_result["analysis_layers"]
        l6 = phase2_result["analysis_layers"]["L6_assumption_audit"]

        # 验证L6结构
        assert "identified_assumptions" in l6
        assert "unconventional_approaches" in l6

        # 验证至少3个假设
        assert len(l6["identified_assumptions"]) >= 3

        # 验证每个假设的结构
        for assumption in l6["identified_assumptions"]:
            assert "assumption" in assumption
            assert "counter_assumption" in assumption
            assert "challenge_question" in assumption
            assert "impact_if_wrong" in assumption
            assert "alternative_approach" in assumption

    def test_confidence_calculation_includes_l6(self, requirements_analyst):
        """测试置信度计算包含L6质量评估"""

        phase1 = {"info_status": "sufficient", "primary_deliverables": [{"deliverable_id": "D1"}]}

        # Phase2 有L6且质量合格（3个假设）
        phase2_with_l6 = {
            "analysis_layers": {
                "L5_sharpness": {"score": 80},
                "L6_assumption_audit": {
                    "identified_assumptions": [{"assumption": "A1"}, {"assumption": "A2"}, {"assumption": "A3"}]
                },
            },
            "expert_handoff": {"critical_questions_for_experts": {"v2": ["Q1"]}},
        }

        # Phase2 没有L6
        phase2_without_l6 = {
            "analysis_layers": {"L5_sharpness": {"score": 80}},
            "expert_handoff": {"critical_questions_for_experts": {"v2": ["Q1"]}},
        }

        confidence_with_l6 = requirements_analyst._calculate_two_phase_confidence(phase1, phase2_with_l6)
        confidence_without_l6 = requirements_analyst._calculate_two_phase_confidence(phase1, phase2_without_l6)

        # 有L6的置信度应该更高
        assert confidence_with_l6 > confidence_without_l6
        assert confidence_with_l6 - confidence_without_l6 == pytest.approx(0.05, abs=0.01)


class TestL2ExtendedPerspectives:
    """测试L2扩展域视角"""

    def test_l2_extended_perspectives_extraction(self, requirements_analyst):
        """测试从L2_user_model提取扩展视角"""

        analysis_layers = {
            "L2_user_model": {
                "psychological": "追求效率",
                "sociological": "创业者",
                "aesthetic": "现代简约",
                "emotional": "压力→放松",
                "ritual": "晨间咖啡",
                "business": "需要展示空间接待客户，预期18个月内实现盈利",
                "technical": "需要高速网络和视频会议设备",
                "ecological": "偏好可持续材料，关注能源效率",
                "cultural": "融合本地文化元素",
                "political": "需要符合商住两用政策",
            }
        }

        extended = requirements_analyst._extract_l2_extended_perspectives(analysis_layers)

        # 验证提取了所有扩展视角
        assert "business" in extended
        assert "technical" in extended
        assert "ecological" in extended
        assert "cultural" in extended
        assert "political" in extended

        # 验证内容正确
        assert "盈利" in extended["business"]
        assert "网络" in extended["technical"]
        assert "可持续" in extended["ecological"]

    def test_l2_extended_perspectives_in_merged_results(self, requirements_analyst):
        """测试合并结果包含扩展视角"""

        phase1 = {
            "info_status": "sufficient",
            "primary_deliverables": [],
            "project_type_preliminary": "commercial_enterprise",
        }

        phase2 = {
            "analysis_layers": {
                "L2_user_model": {"psychological": "追求效率", "business": "需要ROI分析", "technical": "需要智能系统"},
                "L5_sharpness": {"score": 75},
            },
            "structured_output": {"project_task": "商业空间设计"},
            "expert_handoff": {},
        }

        merged = requirements_analyst._merge_phase_results(phase1, phase2)

        # 验证顶层包含扩展视角
        assert "l2_extended_perspectives" in merged
        assert "business" in merged["l2_extended_perspectives"]
        assert "technical" in merged["l2_extended_perspectives"]

    def test_l2_extended_perspectives_filtering(self, requirements_analyst):
        """测试过滤未激活的扩展视角"""

        analysis_layers = {
            "L2_user_model": {
                "psychological": "追求效率",
                "business": "需要ROI分析",
                "technical": "（如激活）技术需求",  # 未激活
                "ecological": "",  # 空值
                "cultural": "   ",  # 空白
            }
        }

        extended = requirements_analyst._extract_l2_extended_perspectives(analysis_layers)

        # 只应包含已激活的视角
        assert "business" in extended
        assert "technical" not in extended  # 未激活
        assert "ecological" not in extended  # 空值
        assert "cultural" not in extended  # 空白


class TestConditionalActivation:
    """测试条件激活机制"""

    def test_commercial_project_activates_business_perspective(self):
        """测试商业项目激活商业视角"""
        # 这个测试需要实际运行LLM，这里只验证配置正确性

        # 读取配置文件验证激活规则
        from intelligent_project_analyzer.core.prompt_manager import PromptManager

        pm = PromptManager()
        config = pm.get_prompt("requirements_analyst_phase2", return_full_config=True)

        assert config is not None
        assert "l2_perspective_activation" in config

        activation_rules = config["l2_perspective_activation"]
        assert "conditional_perspectives" in activation_rules

        business_rules = activation_rules["conditional_perspectives"]["business"]
        assert "activate_when" in business_rules

        # 验证商业项目类型在激活条件中
        activate_conditions = business_rules["activate_when"]
        project_types = None
        for condition in activate_conditions:
            if "project_type" in condition:
                project_types = condition["project_type"]
                break

        assert project_types is not None
        assert "commercial_enterprise" in project_types


class TestBackwardCompatibility:
    """测试向后兼容性"""

    def test_works_without_l6(self, requirements_analyst):
        """测试没有L6时系统仍正常工作"""

        phase1 = {"info_status": "sufficient", "primary_deliverables": []}

        # Phase2 没有L6
        phase2 = {
            "analysis_layers": {
                "L1_facts": ["事实1"],
                "L2_user_model": {"psychological": "需求"},
                "L5_sharpness": {"score": 75},
            },
            "structured_output": {"project_task": "任务"},
            "expert_handoff": {},
        }

        # 应该不抛出异常
        merged = requirements_analyst._merge_phase_results(phase1, phase2)
        confidence = requirements_analyst._calculate_two_phase_confidence(phase1, phase2)

        assert merged is not None
        assert confidence > 0

    def test_works_without_extended_perspectives(self, requirements_analyst):
        """测试没有扩展视角时系统仍正常工作"""

        analysis_layers = {
            "L2_user_model": {
                "psychological": "需求",
                "sociological": "身份",
                "aesthetic": "风格"
                # 没有扩展视角
            }
        }

        extended = requirements_analyst._extract_l2_extended_perspectives(analysis_layers)

        # 应该返回空字典而不是报错
        assert extended == {}


class TestIntegration:
    """集成测试"""

    @pytest.mark.integration
    def test_full_two_phase_with_enhancements(self, requirements_analyst, mock_llm):
        """测试完整的两阶段流程（包含v7.18.0增强）"""

        # 模拟Phase1响应
        phase1_response = {
            "phase": 1,
            "info_status": "sufficient",
            "primary_deliverables": [{"deliverable_id": "D1", "type": "design_strategy"}],
            "project_type_preliminary": "commercial_enterprise",
        }

        # 模拟Phase2响应（包含L6和扩展L2）
        phase2_response = {
            "phase": 2,
            "analysis_layers": {
                "L1_facts": ["商业项目", "需要展示空间"],
                "L2_user_model": {
                    "psychological": "追求专业形象",
                    "sociological": "企业主",
                    "aesthetic": "现代商务",
                    "emotional": "自信→专业",
                    "ritual": "客户接待流程",
                    "business": "需要在12个月内实现盈利，定位高端市场",
                    "technical": "需要智能会议系统和展示设备",
                    "political": "需要符合商业用地规划",
                },
                "L3_core_tension": "专业形象 vs 成本控制",
                "L4_project_task": "为企业主打造高端商务空间",
                "L5_sharpness": {"score": 80},
                "L6_assumption_audit": {
                    "identified_assumptions": [
                        {"assumption": "高端必然高成本"},
                        {"assumption": "商务空间需要正式感"},
                        {"assumption": "展示优先于功能"},
                    ],
                    "unconventional_approaches": ["灵活空间", "模块化设计"],
                },
            },
            "structured_output": {
                "project_task": "高端商务空间",
                "character_narrative": "企业主",
                "physical_context": "200㎡",
                "resource_constraints": "预算100万",
                "regulatory_requirements": "商业标准",
                "inspiration_references": "国际案例",
                "experience_behavior": "客户接待",
                "design_challenge": "专业 vs 成本",
                "emotional_landscape": "自信专业",
                "spiritual_aspirations": "企业愿景",
                "psychological_safety_needs": "控制感",
                "ritual_behaviors": "接待流程",
                "memory_anchors": "品牌元素",
            },
            "expert_handoff": {
                "critical_questions_for_experts": {"v2": ["Q1"]},
                "design_challenge_spectrum": {},
                "permission_to_diverge": {},
            },
        }

        # 配置mock返回
        mock_llm.invoke.side_effect = [
            Mock(content=json.dumps(phase1_response, ensure_ascii=False)),
            Mock(content=json.dumps(phase2_response, ensure_ascii=False)),
        ]

        # 执行两阶段分析
        state = ProjectAnalysisState(session_id="test_session", user_input="我需要一个高端商务空间，用于接待客户")

        config = {"configurable": {}}

        with patch.object(requirements_analyst, "validate_input", return_value=True):
            with patch(
                "intelligent_project_analyzer.utils.capability_detector.check_capability",
                return_value={
                    "info_sufficiency": {"is_sufficient": True},
                    "deliverable_capability": {"capability_score": 0.9},
                    "capable_deliverables": [],
                    "transformations": [],
                    "recommended_action": "proceed_analysis",
                },
            ):
                result = requirements_analyst._execute_two_phase(state, config, None)

        # 验证结果包含所有增强功能
        structured_data = result.structured_data

        # 验证L6
        assert "assumption_audit" in structured_data
        assert len(structured_data["assumption_audit"]["identified_assumptions"]) >= 3

        # 验证扩展L2
        assert "l2_extended_perspectives" in structured_data
        assert "business" in structured_data["l2_extended_perspectives"]
        assert "technical" in structured_data["l2_extended_perspectives"]

        # 验证置信度
        assert result.confidence > 0.7  # 应该有较高置信度


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
