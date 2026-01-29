"""
V7情感洞察专家 - 端到端集成测试
测试完整数据流：需求分析 → 问卷生成 → V7选择 → V7执行 → 报告聚合
"""

import pytest

from intelligent_project_analyzer.models.flexible_output import V7_1_FlexibleOutput


def test_v7_flexible_output_model_comprehensive_mode():
    """测试V7_1_FlexibleOutput模型 - Comprehensive模式"""

    # 模拟V7专家的完整输出
    v7_output_data = {
        "output_mode": "comprehensive",
        "user_question_focus": "特殊人群（老年痴呆患者）的居住空间设计",
        "confidence": 0.85,
        "design_rationale": "基于创伤知情设计和依恋理论，分析老年痴呆患者的安全基地需求",
        # 5个情感字段
        "emotional_landscape": {
            "entry_emotion": "混乱/焦虑",
            "transition_path": "入口视线引导 → 公共区域熟悉线索 → 卧室安全撤退",
            "core_emotion": "安全感/稳定感",
            "design_triggers": ["恒定照明", "颜色区分", "触觉标识"],
        },
        "spiritual_aspirations": "维持自主性和尊严，从'被照顾者'向'有价值的家庭成员'转变",
        "psychological_safety_needs": {
            "fear_source": "认知衰退导致的失控感和迷失恐惧",
            "safety_strategy": "可见化动线+记忆锚点强化",
            "refuge_space": "卧室作为稳定的私人领地",
        },
        "ritual_behaviors": [
            {
                "behavior_name": "晨起例行路线",
                "psychological_meaning": "通过重复巩固记忆，减少认知负担",
                "space_requirements": "固定动线+触觉引导+颜色标识",
                "trigger_conditions": "每日早晨6:30-8:00",
            },
            {
                "behavior_name": "午后阳光区小憩",
                "psychological_meaning": "生物钟调节+情绪稳定",
                "space_requirements": "南向采光区+固定座椅+视野控制",
            },
        ],
        "memory_anchors": [
            {
                "item_name": "家族照片墙",
                "emotional_value": "身份认同+家庭连接",
                "memory_type": "长期记忆强化",
                "spatial_treatment": "卧室床头正对位置，触手可及",
            },
            {
                "item_name": "老式收音机",
                "emotional_value": "听觉记忆触发",
                "memory_type": "情景记忆激活",
                "spatial_treatment": "客厅固定角落，配合纹理标识",
            },
        ],
    }

    # 验证Pydantic模型能正确解析
    v7_output = V7_1_FlexibleOutput(**v7_output_data)

    # 断言必需字段
    assert v7_output.output_mode == "comprehensive"
    assert v7_output.confidence == 0.85
    assert v7_output.emotional_landscape is not None
    assert v7_output.spiritual_aspirations is not None
    assert v7_output.psychological_safety_needs is not None
    assert v7_output.ritual_behaviors is not None
    assert len(v7_output.ritual_behaviors) == 2
    assert v7_output.memory_anchors is not None
    assert len(v7_output.memory_anchors) == 2

    # 验证情绪地图结构
    assert v7_output.emotional_landscape["entry_emotion"] == "混乱/焦虑"
    assert "入口视线引导" in v7_output.emotional_landscape["transition_path"]

    # 验证心理安全需求
    assert "认知衰退" in v7_output.psychological_safety_needs["fear_source"]

    print("✅ V7_1_FlexibleOutput Comprehensive模式测试通过")


def test_v7_flexible_output_model_targeted_mode():
    """测试V7_1_FlexibleOutput模型 - Targeted模式"""

    # 模拟V7专家的针对性输出
    v7_output_data = {
        "output_mode": "targeted",
        "user_question_focus": "如何为职场焦虑的独居女性设计情绪释放空间？",
        "confidence": 0.90,
        "design_rationale": "基于Ulrich的恢复性环境理论和Plutchik情绪轮盘",
        # Targeted模式的核心输出
        "targeted_analysis": {
            "fear_diagnosis": "职场压力累积 + 社会角色冲突 → 慢性焦虑状态",
            "safety_base_design": "卧室内嵌独立'情绪舱'：2㎡软包区+可调光源+隔音",
            "sensory_calming": {
                "visual": "暖色调2700K光源，避免蓝光刺激",
                "auditory": "白噪音发生器 + 自然声景",
                "tactile": "羊毛质感抱枕 + 温控毛毯",
                "olfactory": "薰衣草/柑橘精油扩香",
            },
            "temporal_design": "下班后过渡仪式：换衣 → 情绪舱15分钟 → 晚餐准备",
        },
    }

    # 验证Pydantic模型能正确解析
    v7_output = V7_1_FlexibleOutput(**v7_output_data)

    # 断言必需字段
    assert v7_output.output_mode == "targeted"
    assert v7_output.confidence == 0.90
    assert v7_output.targeted_analysis is not None

    # 验证targeted_analysis结构
    assert "fear_diagnosis" in v7_output.targeted_analysis
    assert "safety_base_design" in v7_output.targeted_analysis
    assert "sensory_calming" in v7_output.targeted_analysis

    # Comprehensive字段应为空
    assert v7_output.emotional_landscape is None
    assert v7_output.spiritual_aspirations is None

    print("✅ V7_1_FlexibleOutput Targeted模式测试通过")


def test_v7_flexible_output_validation_error():
    """测试V7模型验证逻辑 - Comprehensive模式缺失字段"""

    # 模拟不完整的Comprehensive模式数据（缺少memory_anchors）
    incomplete_data = {
        "output_mode": "comprehensive",
        "user_question_focus": "测试项目",
        "confidence": 0.8,
        "design_rationale": "测试理论",
        "emotional_landscape": {"entry_emotion": "test"},
        "spiritual_aspirations": "test",
        "psychological_safety_needs": {"fear_source": "test"},
        "ritual_behaviors": [{"behavior_name": "test"}]
        # 缺少 memory_anchors
    }

    # 应该抛出ValidationError
    with pytest.raises(ValueError) as exc_info:
        V7_1_FlexibleOutput(**incomplete_data)

    assert "memory_anchors" in str(exc_info.value)
    print("✅ V7_1_FlexibleOutput 验证逻辑测试通过")


def test_v7_targeted_mode_validation():
    """测试V7模型验证逻辑 - Targeted模式缺失targeted_analysis"""

    # 模拟Targeted模式但缺少targeted_analysis
    incomplete_data = {
        "output_mode": "targeted",
        "user_question_focus": "测试问题",
        "confidence": 0.85,
        "design_rationale": "测试理论"
        # 缺少 targeted_analysis
    }

    # 应该抛出ValidationError
    with pytest.raises(ValueError) as exc_info:
        V7_1_FlexibleOutput(**incomplete_data)

    assert "targeted_analysis" in str(exc_info.value)
    print("✅ V7 Targeted模式验证逻辑测试通过")


# ==================== 集成测试标记 ====================


@pytest.mark.integration
def test_v7_role_registration_in_director():
    """测试V7角色是否在项目总监配置中正确注册"""

    from pathlib import Path

    import yaml

    config_path = (
        Path(__file__).parent.parent
        / "intelligent_project_analyzer"
        / "config"
        / "prompts"
        / "dynamic_project_director_v2.yaml"
    )

    with open(config_path, "r", encoding="utf-8") as f:
        director_config = yaml.safe_load(f)

    # 验证V7角色存在于role_characteristics
    role_characteristics = director_config.get("role_characteristics", {})
    assert "V7_情感洞察专家" in role_characteristics

    v7_char = role_characteristics["V7_情感洞察专家"]
    assert v7_char["temperature"] == 0.75
    assert "情绪地图构建" in v7_char["strength"]

    # 验证special_scenarios中的special_population场景使用V7
    special_scenarios = director_config.get("special_scenarios", {})
    special_pop = special_scenarios.get("special_population", {})
    assert special_pop.get("core_expert") == "V7_情感洞察专家"

    print("✅ V7角色在项目总监配置中注册正确")


@pytest.mark.integration
def test_v7_role_file_exists():
    """测试V7角色配置文件是否存在"""

    from pathlib import Path

    v7_config_path = (
        Path(__file__).parent.parent
        / "intelligent_project_analyzer"
        / "config"
        / "roles"
        / "v7_emotional_insight_expert.yaml"
    )

    assert v7_config_path.exists(), "V7角色配置文件不存在"

    import yaml

    with open(v7_config_path, "r", encoding="utf-8") as f:
        v7_config = yaml.safe_load(f)

    assert "V7_情感洞察专家" in v7_config
    v7_role = v7_config["V7_情感洞察专家"]

    # 验证核心字段
    assert "description" in v7_role
    assert "core_expertise" in v7_role
    assert "system_prompt" in v7_role

    # 验证理论框架（使用完整字符串匹配）
    core_expertise = v7_role["core_expertise"]
    assert any("马斯洛需求层次分析" in item for item in core_expertise), "马斯洛需求层次理论未找到"
    assert any("依恋理论" in item for item in core_expertise), "依恋理论未找到"

    print("✅ V7角色配置文件存在且结构正确")


if __name__ == "__main__":
    # 运行单元测试
    test_v7_flexible_output_model_comprehensive_mode()
    test_v7_flexible_output_model_targeted_mode()
    test_v7_flexible_output_validation_error()
    test_v7_targeted_mode_validation()

    # 运行集成测试
    test_v7_role_registration_in_director()
    test_v7_role_file_exists()

    print("\n🎉 所有V7集成测试通过！")
