"""
集成测试：设计模式检测 + 能力注入系统
版本: v1.0
日期: 2026-02-12

测试范围：
1. RequirementsAnalyst中的模式检测集成
2. TaskOrientedExpertFactory中的能力注入集成
3. 端到端工作流验证
"""

import pytest
from unittest.mock import Mock
from intelligent_project_analyzer.services.mode_detector import detect_design_modes


class TestRequirementsAnalystIntegration:
    """测试RequirementsAnalyst中的模式检测集成"""

    def test_phase2_mode_detection_triggered(self):
        """验证Phase2节点触发模式检测"""
        from intelligent_project_analyzer.agents.requirements_analyst_agent import phase2_node

        # 模拟state
        mock_llm = Mock()
        mock_pm = Mock()
        mock_state = {
            "user_input": "西藏林芝海拔3000米悬崖酒店设计，需要供氧系统",
            "phase1_result": {"project_type": {"primary": "酒店"}, "primary_deliverables": []},
            "processing_log": [],
            "node_path": [],
        }

        # Mock LLM响应
        mock_llm_response = Mock()
        mock_llm_response.content = """
        {
            "phase": 2,
            "analysis_layers": {},
            "expert_handoff": {}
        }
        """
        mock_llm.invoke = Mock(return_value=mock_llm_response)

        # Mock prompt manager
        mock_pm.get_prompt = Mock(
            return_value={
                "system_prompt": "test",
                "task_description_template": "test {datetime_info} {user_input} {phase1_output}",
            }
        )

        # 执行phase2_node
        result = phase2_node(mock_state, mock_llm, mock_pm)

        # 验证模式检测结果存在
        assert "detected_design_modes" in result
        assert isinstance(result["detected_design_modes"], list)

        # 对于极端环境输入，应检测到M8
        if result["detected_design_modes"]:
            mode_ids = [m["mode"] for m in result["detected_design_modes"]]
            assert "M8_extreme_condition" in mode_ids

    def test_mode_detection_performance(self):
        """验证模式检测不影响Phase2性能"""
        from intelligent_project_analyzer.agents.requirements_analyst_agent import phase2_node

        mock_llm = Mock()
        mock_pm = Mock()
        mock_state = {
            "user_input": "办公空间设计",
            "phase1_result": {"project_type": {"primary": "办公"}, "primary_deliverables": []},
            "processing_log": [],
            "node_path": [],
        }

        mock_llm_response = Mock()
        mock_llm_response.content = '{"phase": 2, "analysis_layers": {}, "expert_handoff": {}}'
        mock_llm.invoke = Mock(return_value=mock_llm_response)
        mock_pm.get_prompt = Mock(
            return_value={
                "system_prompt": "test",
                "task_description_template": "test {datetime_info} {user_input} {phase1_output}",
            }
        )

        result = phase2_node(mock_state, mock_llm, mock_pm)

        # 验证检测耗时记录存在
        assert "mode_detection_elapsed_ms" in result

        # 应该很快（<100ms）
        assert result["mode_detection_elapsed_ms"] < 100


class TestTaskOrientedExpertFactoryIntegration:
    """测试TaskOrientedExpertFactory中的能力注入集成"""

    def test_inject_mode_capabilities_basic(self):
        """测试基本能力注入功能"""
        from intelligent_project_analyzer.agents.task_oriented_expert_factory import TaskOrientedExpertFactory

        factory = TaskOrientedExpertFactory(llm_factory=Mock(), prompt_manager=Mock())

        # 模拟state（包含M8检测结果）
        mock_state = {
            "detected_design_modes": [{"mode": "M8_extreme_condition", "confidence": 0.85, "reason": "高海拔环境"}]
        }

        base_prompt = "你是一位结构工程师。"

        # 调用注入方法
        enhanced_prompt = factory._inject_mode_capabilities(
            expert_id="V6-1", base_system_prompt=base_prompt, state=mock_state
        )

        # V6-1应获得M8注入
        assert enhanced_prompt is not None
        assert "M8极端环境模式激活" in enhanced_prompt
        assert "结构抗性系统" in enhanced_prompt
        assert base_prompt in enhanced_prompt

    def test_inject_mode_capabilities_v7_expert(self):
        """测试V7专家的M9能力注入"""
        from intelligent_project_analyzer.agents.task_oriented_expert_factory import TaskOrientedExpertFactory

        factory = TaskOrientedExpertFactory(llm_factory=Mock(), prompt_manager=Mock())

        mock_state = {"detected_design_modes": [{"mode": "M9_social_structure", "confidence": 0.9, "reason": "多代同堂家庭"}]}

        base_prompt = "你是社会关系与心理洞察专家。"

        enhanced_prompt = factory._inject_mode_capabilities(
            expert_id="V7", base_system_prompt=base_prompt, state=mock_state
        )

        # V7应获得M9注入
        assert enhanced_prompt is not None
        assert "M9社会结构模式激活" in enhanced_prompt
        assert "social_structure_analysis" in enhanced_prompt
        assert "power_distance_model" in enhanced_prompt

    def test_no_injection_when_no_modes(self):
        """测试无检测模式时不注入"""
        from intelligent_project_analyzer.agents.task_oriented_expert_factory import TaskOrientedExpertFactory

        factory = TaskOrientedExpertFactory(llm_factory=Mock(), prompt_manager=Mock())

        mock_state = {"detected_design_modes": []}

        base_prompt = "你是一位专家。"

        result = factory._inject_mode_capabilities(expert_id="V2", base_system_prompt=base_prompt, state=mock_state)

        # 应返回None（无需注入）
        assert result is None

    def test_no_injection_for_non_target_expert(self):
        """测试非目标专家不注入"""
        from intelligent_project_analyzer.agents.task_oriented_expert_factory import TaskOrientedExpertFactory

        factory = TaskOrientedExpertFactory(llm_factory=Mock(), prompt_manager=Mock())

        # M8只针对V6-1和V6-2
        mock_state = {"detected_design_modes": [{"mode": "M8_extreme_condition", "confidence": 0.8, "reason": "test"}]}

        base_prompt = "你是叙事专家。"

        result = factory._inject_mode_capabilities(
            expert_id="V3", base_system_prompt=base_prompt, state=mock_state  # V3不是M8的目标
        )

        # 应返回None
        assert result is None

    def test_multi_mode_injection(self):
        """测试多模式组合注入"""
        from intelligent_project_analyzer.agents.task_oriented_expert_factory import TaskOrientedExpertFactory

        factory = TaskOrientedExpertFactory(llm_factory=Mock(), prompt_manager=Mock())

        # V3是M1和M3的目标专家
        mock_state = {
            "detected_design_modes": [
                {"mode": "M1_concept_driven", "confidence": 0.85, "reason": "概念驱动"},
                {"mode": "M3_emotional_experience", "confidence": 0.75, "reason": "情绪体验"},
            ]
        }

        base_prompt = "你是叙事专家。"

        enhanced_prompt = factory._inject_mode_capabilities(
            expert_id="V3", base_system_prompt=base_prompt, state=mock_state
        )

        # V3应获得M1和M3的双重注入
        assert enhanced_prompt is not None
        assert "M1概念驱动模式激活" in enhanced_prompt
        assert "M3情绪体验模式激活" in enhanced_prompt


class TestEndToEndWorkflow:
    """端到端工作流测试"""

    @pytest.mark.integration
    def test_m8_extreme_environment_workflow(self):
        """
        测试M8极端环境项目的完整流程

        场景：西藏林芝海拔3000m悬崖酒店
        预期：
        1. RequirementsAnalyst检测到M8
        2. V6-1获得M8能力注入
        3. 输出包含4个维度分析
        """
        # 模拟用户输入
        user_input = """
        项目背景：西藏林芝海拔3000米悬崖酒店设计
        环境特点：高海拔、强紫外线、大温差、低氧
        核心需求：供氧系统、保温系统、抗风压结构
        """

        # 1. 模式检测阶段
        detected_modes = detect_design_modes(user_input)

        assert len(detected_modes) > 0
        assert detected_modes[0]["mode"] == "M8_extreme_condition"
        assert detected_modes[0]["confidence"] > 0.7

        # 2. 能力注入阶段（模拟）
        from intelligent_project_analyzer.agents.task_oriented_expert_factory import TaskOrientedExpertFactory

        factory = TaskOrientedExpertFactory(llm_factory=Mock(), prompt_manager=Mock())

        mock_state = {"detected_design_modes": detected_modes}

        # V6-1（结构工程师）获得注入
        enhanced_prompt = factory._inject_mode_capabilities(
            expert_id="V6-1", base_system_prompt="你是结构工程师。", state=mock_state
        )

        assert enhanced_prompt is not None

        # 验证注入内容包含4个维度
        assert "结构抗性系统" in enhanced_prompt
        assert "材料适应系统" in enhanced_prompt
        assert "能源与生存系统" in enhanced_prompt
        assert "生理舒适保障" in enhanced_prompt

    @pytest.mark.integration
    def test_m9_social_structure_workflow(self):
        """
        测试M9社会结构项目的完整流程

        场景：三代同堂+再婚家庭六口之家别墅
        预期：
        1. RequirementsAnalyst检测到M9
        2. V7获得M9能力注入
        3. 输出包含5个社会结构子字段
        """
        user_input = """
        项目类型：三代同堂别墅设计
        家庭结构：夫妻双方父母同住 + 一个孩子，共6口人
        核心矛盾：代际冲突、隐私需求、生活习惯差异
        设计目标：平衡独立性与连接性
        """

        # 1. 检测
        detected_modes = detect_design_modes(user_input)

        mode_ids = [m["mode"] for m in detected_modes]
        assert "M9_social_structure" in mode_ids

        # 2. 注入
        from intelligent_project_analyzer.agents.task_oriented_expert_factory import TaskOrientedExpertFactory

        factory = TaskOrientedExpertFactory(llm_factory=Mock(), prompt_manager=Mock())

        mock_state = {"detected_design_modes": detected_modes}

        # V7获得注入
        enhanced_prompt = factory._inject_mode_capabilities(
            expert_id="V7", base_system_prompt="你是社会关系专家。", state=mock_state
        )

        assert enhanced_prompt is not None

        # 验证5个核心字段
        assert "power_distance_model" in enhanced_prompt
        assert "privacy_hierarchy" in enhanced_prompt
        assert "conflict_buffer_design" in enhanced_prompt
        assert "evolution_adaptability" in enhanced_prompt
        assert "intergenerational_balance" in enhanced_prompt


class TestConfigurationLoading:
    """测试配置加载"""

    def test_ability_injections_yaml_exists(self):
        """验证ability_injections.yaml存在且可加载"""
        from pathlib import Path
        import yaml

        config_path = (
            Path(__file__).parent.parent.parent / "intelligent_project_analyzer" / "config" / "ability_injections.yaml"
        )

        assert config_path.exists(), "ability_injections.yaml不存在"

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        assert "mode_to_ability_injections" in config

        # 验证10个模式都有配置
        expected_modes = [
            "M1_concept_driven",
            "M2_function_efficiency",
            "M3_emotional_experience",
            "M4_capital_asset",
            "M5_rural_context",
            "M6_urban_regeneration",
            "M7_tech_integration",
            "M8_extreme_condition",
            "M9_social_structure",
            "M10_future_speculation",
        ]

        for mode in expected_modes:
            assert mode in config["mode_to_ability_injections"]

            mode_config = config["mode_to_ability_injections"][mode]
            assert "enabled" in mode_config
            assert "target_experts" in mode_config
            assert "inject_ability" in mode_config
            assert "prompt_injection" in mode_config

    def test_m8_m9_configuration_complete(self):
        """验证M8和M9的配置完整性（重点模式）"""
        from pathlib import Path
        import yaml

        config_path = (
            Path(__file__).parent.parent.parent / "intelligent_project_analyzer" / "config" / "ability_injections.yaml"
        )

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        mode_to_ability = config["mode_to_ability_injections"]

        # M8配置验证
        m8 = mode_to_ability["M8_extreme_condition"]
        assert m8["enabled"] is True
        assert "V6-1" in m8["target_experts"]
        assert "V6-2" in m8["target_experts"]
        assert m8["inject_ability"] == "A10_environmental_adaptation"

        # 验证M8注入内容包含4个维度
        m8_injection = m8["prompt_injection"]
        assert "结构抗性系统" in m8_injection
        assert "材料适应系统" in m8_injection
        assert "能源与生存系统" in m8_injection
        assert "生理舒适保障" in m8_injection

        # M9配置验证
        m9 = mode_to_ability["M9_social_structure"]
        assert m9["enabled"] is True
        assert "V7" in m9["target_experts"]
        assert m9["inject_ability"] == "A9_social_structure_modeling"

        # 验证M9注入内容包含5个字段
        m9_injection = m9["prompt_injection"]
        assert "power_distance_model" in m9_injection
        assert "privacy_hierarchy" in m9_injection
        assert "conflict_buffer_design" in m9_injection
        assert "evolution_adaptability" in m9_injection
        assert "intergenerational_balance" in m9_injection


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "-m", "not integration"])
