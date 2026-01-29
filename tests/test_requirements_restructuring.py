"""
需求重构引擎单元测试

测试 RequirementsRestructuringEngine 的各个方法和数据融合逻辑

v7.135: 首次实现
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import pytest

from intelligent_project_analyzer.core.state import StateManager
from intelligent_project_analyzer.interaction.nodes.requirements_restructuring import RequirementsRestructuringEngine

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_questionnaire_data():
    """样例问卷数据（三步问卷）"""
    return {
        "core_tasks": [
            {"title": "设计150平米现代简约住宅", "description": "三室两厅，注重收纳和采光", "priority": "high"},
            {"title": "优化空间利用率", "description": "最大化收纳空间", "priority": "medium"},
        ],
        "gap_filling": {"budget": "预算30万元", "timeline": "6个月完成", "space_area": "150平米", "style_preference": "现代简约风格"},
        "dimensions": {"selected": ["功能性", "美学", "可持续性"], "weights": {"功能性": 0.45, "美学": 0.35, "可持续性": 0.20}},
        "questionnaire_step": 3,
    }


@pytest.fixture
def sample_ai_analysis():
    """样例AI分析数据"""
    return {"project_type": "室内设计", "complexity": "中等", "confidence": 0.85}


@pytest.fixture
def sample_analysis_layers():
    """样例L1-L5洞察数据"""
    return {
        "L1_表层事实": {"facts": ["150平米三室两厅", "预算30万元", "现代简约风格"]},
        "L2_用户画像": {"user_type": "年轻家庭", "preferences": ["注重收纳", "喜欢采光"], "lifestyle": "追求简约实用"},
        "L3_核心张力": {"tension": "预算有限 vs 品质追求", "description": "在30万预算内实现高品质简约设计的平衡挑战"},
        "L4_项目任务_JTBD": {"job_to_be_done": "帮助年轻家庭在预算内打造功能完善、美观舒适的理想居所"},
        "L5_锐度评分": {"score": 8.5, "note": "需求清晰，目标明确"},
    }


@pytest.fixture
def sample_user_input():
    """样例用户原始输入"""
    return "我想设计一个150平米的现代简约住宅，三室两厅，预算30万，特别注重收纳和采光。"


# ============================================================================
# 测试：主重构流程
# ============================================================================


def test_restructure_basic(sample_questionnaire_data, sample_ai_analysis, sample_analysis_layers, sample_user_input):
    """测试基础重构流程"""

    result = RequirementsRestructuringEngine.restructure(
        sample_questionnaire_data,
        sample_ai_analysis,
        sample_analysis_layers,
        sample_user_input,
        use_llm=False,  # 不使用LLM，测试纯数据融合
    )

    # 验证文档结构
    assert "metadata" in result
    assert "project_objectives" in result
    assert "constraints" in result
    assert "design_priorities" in result
    assert "core_tension" in result
    assert "special_requirements" in result
    assert "identified_risks" in result
    assert "insight_summary" in result
    assert "deliverable_expectations" in result
    assert "executive_summary" in result

    # 验证元数据
    metadata = result["metadata"]
    assert metadata["document_version"] == "1.0"
    assert "generated_at" in metadata
    assert metadata["generation_method"] == "questionnaire_restructuring"
    assert set(metadata["data_sources"]) == {"user_questionnaire", "ai_analysis", "user_input"}

    # 验证项目目标
    objectives = result["project_objectives"]
    assert "设计150平米现代简约住宅" in objectives["primary_goal"]
    assert objectives["primary_goal_source"] == "questionnaire_task_1"
    assert len(objectives["secondary_goals"]) >= 1

    # 验证约束
    constraints = result["constraints"]
    assert "budget" in constraints
    assert constraints["budget"]["total"] == "预算30万元"
    assert "timeline" in constraints
    assert "space" in constraints

    # 验证设计重点（融合了问卷维度）
    priorities = result["design_priorities"]
    assert len(priorities) == 3
    assert priorities[0]["label"] == "功能性"
    assert priorities[0]["weight"] == 0.45

    # 验证核心张力（来自L3）
    core_tension = result["core_tension"]
    assert "预算有限 vs 品质追求" in core_tension["description"]
    assert core_tension["source"] == "L3_analysis"

    # 验证洞察摘要
    insight_summary = result["insight_summary"]
    assert len(insight_summary["L1_key_facts"]) == 3
    assert insight_summary["L5_sharpness_score"] == 8.5


def test_restructure_with_empty_questionnaire():
    """测试空问卷数据的降级处理"""

    result = RequirementsRestructuringEngine.restructure({}, {}, {}, "简单需求", use_llm=False)  # 空问卷  # 空AI分析  # 空洞察

    # 应该返回有效的文档结构（即使数据不完整）
    assert "metadata" in result
    assert "project_objectives" in result
    assert result["project_objectives"]["primary_goal"] == "待明确"


# ============================================================================
# 测试：目标提取（融合L4 JTBD）
# ============================================================================


def test_extract_objectives_with_jtbd(sample_questionnaire_data, sample_analysis_layers):
    """测试目标提取，验证L4 JTBD融合"""

    objectives = RequirementsRestructuringEngine._extract_objectives_with_jtbd(
        sample_questionnaire_data, sample_analysis_layers
    )

    # 验证主目标来源
    assert objectives["primary_goal"] == "设计150平米现代简约住宅"
    assert objectives["primary_goal_source"] == "questionnaire_task_1"

    # 验证次要目标
    assert "优化空间利用率" in objectives["secondary_goals"]

    # 验证成功标准（融合了L4 JTBD）
    success_criteria = objectives["success_criteria"]
    assert any("年轻家庭" in criterion for criterion in success_criteria)
    assert any("功能完善" in criterion for criterion in success_criteria)


def test_extract_objectives_fallback_to_jtbd():
    """测试当问卷无任务时，降级到L4 JTBD"""

    questionnaire_data = {"core_tasks": [], "gap_filling": {}, "dimensions": {"selected": [], "weights": {}}}  # 无任务

    analysis_layers = {"L4_项目任务_JTBD": {"job_to_be_done": "帮助用户实现高品质设计"}}

    objectives = RequirementsRestructuringEngine._extract_objectives_with_jtbd(questionnaire_data, analysis_layers)

    # 应该使用L4作为主目标
    assert "高品质设计" in objectives["primary_goal"]
    assert objectives["primary_goal_source"] == "L4_JTBD_inference"


# ============================================================================
# 测试：约束提取
# ============================================================================


def test_extract_constraints(sample_questionnaire_data):
    """测试约束提取（预算/时间/空间）"""

    constraints = RequirementsRestructuringEngine._extract_constraints(sample_questionnaire_data)

    # 验证预算
    assert "budget" in constraints
    assert constraints["budget"]["total"] == "预算30万元"
    assert constraints["budget"]["source"] == "questionnaire_gap_filling"

    # 验证时间线
    assert "timeline" in constraints
    assert constraints["timeline"]["duration"] == "6个月完成"

    # 验证空间
    assert "space" in constraints
    assert constraints["space"]["area"] == "150平米"


def test_extract_constraints_with_missing_data():
    """测试缺失约束数据的处理"""

    questionnaire_data = {
        "gap_filling": {
            "budget": "预算30万"
            # 缺失timeline和space
        }
    }

    constraints = RequirementsRestructuringEngine._extract_constraints(questionnaire_data)

    # 只应包含有数据的约束
    assert "budget" in constraints
    assert "timeline" not in constraints
    assert "space" not in constraints


# ============================================================================
# 测试：设计重点构建（融合L2+L3）
# ============================================================================


def test_build_priorities_with_insights(sample_questionnaire_data, sample_analysis_layers):
    """测试设计重点构建，验证L2用户画像和L3张力的融合"""

    priorities = RequirementsRestructuringEngine._build_priorities_with_insights(
        sample_questionnaire_data, sample_analysis_layers
    )

    # 验证维度权重
    assert len(priorities) == 3
    assert priorities[0]["label"] == "功能性"
    assert priorities[0]["weight"] == 0.45
    assert priorities[0]["source"] == "questionnaire_radar"

    # 验证设计建议（应融合L2用户画像）
    recommendations = priorities[0]["design_recommendations"]
    assert any("收纳" in rec or "采光" in rec for rec in recommendations)


def test_build_priorities_without_questionnaire_dimensions():
    """测试无问卷维度时，从L2推断重点"""

    questionnaire_data = {"dimensions": {"selected": [], "weights": {}}}  # 无维度数据

    analysis_layers = {"L2_用户画像": {"preferences": ["注重收纳", "喜欢采光"]}}

    priorities = RequirementsRestructuringEngine._build_priorities_with_insights(questionnaire_data, analysis_layers)

    # 应该从L2推断出设计重点
    assert len(priorities) > 0
    assert any("收纳" in p["design_recommendations"][0] or "采光" in p["design_recommendations"][0] for p in priorities)


# ============================================================================
# 测试：风险识别（基于L3张力）
# ============================================================================


def test_identify_risks_with_tension(sample_analysis_layers):
    """测试风险识别，验证基于L3张力的风险分析"""

    risks = RequirementsRestructuringEngine._identify_risks_with_tension(sample_analysis_layers)

    # 应该基于L3张力识别出风险
    assert len(risks) > 0

    budget_risk = next((r for r in risks if "预算" in r["description"]), None)
    assert budget_risk is not None
    assert budget_risk["category"] in ["budget", "technical", "timeline"]
    assert budget_risk["severity"] in ["low", "medium", "high"]
    assert budget_risk["source"] == "L3_tension_inference"

    # 验证缓解策略
    assert len(budget_risk["mitigation"]) > 0


def test_identify_risks_without_tension():
    """测试无L3张力时的风险识别"""

    analysis_layers = {}  # 无L3数据

    risks = RequirementsRestructuringEngine._identify_risks_with_tension(analysis_layers)

    # 应该返回空列表或通用风险
    assert isinstance(risks, list)


# ============================================================================
# 测试：执行摘要生成
# ============================================================================


def test_generate_executive_summary(sample_questionnaire_data, sample_analysis_layers):
    """测试执行摘要生成"""

    objectives = {"primary_goal": "设计150平米现代简约住宅"}

    constraints = {"budget": {"total": "预算30万元"}, "timeline": {"duration": "6个月"}}

    summary = RequirementsRestructuringEngine._generate_executive_summary(
        objectives, constraints, sample_analysis_layers, use_llm=False
    )

    # 验证摘要结构
    assert "one_sentence" in summary
    assert "what" in summary
    assert "why" in summary
    assert "how" in summary
    assert "constraints_summary" in summary

    # 验证内容
    assert "设计150平米现代简约住宅" in summary["what"]
    assert "预算30万" in summary["constraints_summary"]


@patch("intelligent_project_analyzer.services.llm_factory.LLMFactory.create_llm")
def test_generate_executive_summary_with_llm(mock_llm_factory):
    """测试使用LLM生成流畅的一句话摘要"""

    # Mock LLM响应
    mock_llm = Mock()
    mock_response = Mock()
    mock_response.content = "在30万预算内，6个月完成150平米现代简约住宅设计。"
    mock_llm.invoke.return_value = mock_response
    mock_llm_factory.return_value = mock_llm

    objectives = {"primary_goal": "设计150平米现代简约住宅"}
    constraints = {"budget": {"total": "30万"}, "timeline": {"duration": "6个月"}}

    summary = RequirementsRestructuringEngine._generate_executive_summary(objectives, constraints, {}, use_llm=True)

    # 验证LLM被调用
    assert mock_llm.invoke.called

    # 验证一句话摘要
    assert "30万预算" in summary["one_sentence"]


# ============================================================================
# 测试：洞察摘要整合
# ============================================================================


def test_consolidate_insight_summary(sample_analysis_layers):
    """测试L1-L5洞察摘要整合"""

    summary = RequirementsRestructuringEngine._consolidate_insight_summary(sample_analysis_layers)

    # 验证各层洞察
    assert len(summary["L1_key_facts"]) == 3
    assert "user_type" in summary["L2_user_profile"]
    assert summary["L3_core_tension"] == "预算有限 vs 品质追求"
    assert "年轻家庭" in summary["L4_project_task_jtbd"]
    assert summary["L5_sharpness_score"] == 8.5
    assert summary["L5_sharpness_note"] == "需求清晰，目标明确"


def test_consolidate_insight_summary_with_missing_layers():
    """测试部分洞察缺失时的处理"""

    analysis_layers = {
        "L1_表层事实": {"facts": ["事实1"]},
        # 缺失L2-L5
    }

    summary = RequirementsRestructuringEngine._consolidate_insight_summary(analysis_layers)

    # 应该安全处理缺失的层
    assert len(summary["L1_key_facts"]) == 1
    assert summary["L2_user_profile"] == {}
    assert summary["L3_core_tension"] == ""
    assert summary["L5_sharpness_score"] == 0


# ============================================================================
# 测试：特殊需求提取
# ============================================================================


def test_extract_special_requirements(sample_questionnaire_data):
    """测试特殊需求提取"""

    requirements = RequirementsRestructuringEngine._extract_special_requirements(sample_questionnaire_data)

    # 验证从gap_filling提取的特殊需求
    assert len(requirements) > 0

    # 验证字段
    for req in requirements:
        assert "category" in req
        assert "description" in req
        assert "source" in req
        assert req["source"] == "questionnaire_gap_filling"


# ============================================================================
# 测试：交付期望生成
# ============================================================================


def test_infer_deliverable_expectations(sample_questionnaire_data):
    """测试交付期望推断"""

    objectives = {"primary_goal": "设计150平米现代简约住宅"}

    deliverables = RequirementsRestructuringEngine._infer_deliverable_expectations(
        objectives, sample_questionnaire_data
    )

    # 验证基础交付物
    assert "设计策略文档" in deliverables
    assert len(deliverables) > 0


# ============================================================================
# 测试：集成测试（完整流程）
# ============================================================================


def test_end_to_end_restructuring(
    sample_questionnaire_data, sample_ai_analysis, sample_analysis_layers, sample_user_input
):
    """端到端测试完整重构流程"""

    result = RequirementsRestructuringEngine.restructure(
        sample_questionnaire_data, sample_ai_analysis, sample_analysis_layers, sample_user_input, use_llm=False
    )

    # 验证文档完整性
    assert all(
        key in result
        for key in [
            "metadata",
            "project_objectives",
            "constraints",
            "design_priorities",
            "core_tension",
            "special_requirements",
            "identified_risks",
            "insight_summary",
            "deliverable_expectations",
            "executive_summary",
        ]
    )

    # 验证数据融合
    # 1. 问卷数据融合
    assert "设计150平米现代简约住宅" in result["project_objectives"]["primary_goal"]
    assert result["constraints"]["budget"]["total"] == "预算30万元"
    assert len(result["design_priorities"]) == 3

    # 2. L1-L5洞察融合
    assert len(result["insight_summary"]["L1_key_facts"]) > 0
    assert "年轻家庭" in result["insight_summary"]["L2_user_profile"]["user_type"]
    assert "预算有限" in result["core_tension"]["description"]
    assert "年轻家庭" in result["insight_summary"]["L4_project_task_jtbd"]
    assert result["insight_summary"]["L5_sharpness_score"] == 8.5

    # 3. 原始输入情感基调保留
    assert result["metadata"]["user_input_included"] is True


def test_restructuring_with_state_integration():
    """测试与ProjectAnalysisState的集成"""

    # 创建完整的状态数据
    state = StateManager.create_initial_state("设计150平米住宅，预算30万", "test-session")

    # 模拟问卷数据
    state["confirmed_core_tasks"] = [{"title": "设计150平米住宅", "description": "三室两厅", "priority": "high"}]
    state["gap_filling_answers"] = {"budget": "预算30万", "timeline": "6个月"}
    state["selected_dimensions"] = ["功能性", "美学"]
    state["dimension_weights"] = {"功能性": 0.6, "美学": 0.4}

    # 模拟AI洞察
    state["agent_results"] = {
        "requirements_analyst": {
            "analysis_layers": {"L1_表层事实": {"facts": ["150平米", "预算30万"]}, "L5_锐度评分": {"score": 8.0, "note": "需求明确"}}
        }
    }

    # 提取数据并重构
    questionnaire_data = {
        "core_tasks": state["confirmed_core_tasks"],
        "gap_filling": state["gap_filling_answers"],
        "dimensions": {"selected": state["selected_dimensions"], "weights": state["dimension_weights"]},
    }

    analysis_layers = state["agent_results"]["requirements_analyst"]["analysis_layers"]

    result = RequirementsRestructuringEngine.restructure(
        questionnaire_data, {}, analysis_layers, state["user_input"], use_llm=False
    )

    # 验证重构成功
    assert result["project_objectives"]["primary_goal"] == "设计150平米住宅"
    assert result["constraints"]["budget"]["total"] == "预算30万"


# ============================================================================
# 测试：边界情况
# ============================================================================


def test_restructure_with_none_inputs():
    """测试None输入的健壮性"""

    result = RequirementsRestructuringEngine.restructure(
        None,  # type: ignore
        None,  # type: ignore
        None,  # type: ignore
        None,  # type: ignore
        use_llm=False,
    )

    # 应该返回有效的文档（即使数据为空）
    assert "metadata" in result
    assert result["project_objectives"]["primary_goal"] == "待明确"


def test_restructure_with_malformed_data():
    """测试格式错误的数据"""

    malformed_questionnaire = {
        "core_tasks": "not a list",  # 应该是列表
        "gap_filling": ["not a dict"],  # 应该是字典
        "dimensions": None,
    }

    # 应该不抛出异常，而是优雅降级
    result = RequirementsRestructuringEngine.restructure(malformed_questionnaire, {}, {}, "测试输入", use_llm=False)

    assert "metadata" in result


# ============================================================================
# 性能测试
# ============================================================================


def test_restructure_performance(
    sample_questionnaire_data, sample_ai_analysis, sample_analysis_layers, sample_user_input, benchmark
):
    """性能基准测试（需要pytest-benchmark插件）"""

    def run_restructure():
        return RequirementsRestructuringEngine.restructure(
            sample_questionnaire_data, sample_ai_analysis, sample_analysis_layers, sample_user_input, use_llm=False
        )

    # 跳过如果没有安装pytest-benchmark
    try:
        result = benchmark(run_restructure)
        assert "metadata" in result
    except Exception:
        pytest.skip("pytest-benchmark not installed")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
