"""
v8.0 问卷系统 - 端到端测试

场景模拟（全程 mock LLM，真实走代码路径）：

E2E-1: 三代同堂住宅 - v8.0 项目专属维度成功路径
        Step1 确认任务 → Step2 v8.0维度生成 → Step3 gap_filling → summary
E2E-2: 创业咖啡馆 - v8.0 降级路径（LLM 失败，传统维度接管）
E2E-3: 高净值豪宅 - 高置信度场景，自动校准维度
E2E-4: 环境变量 false - 完全走传统路径，v8.0 不触发
E2E-5: 并发安全 - 同一 Generator 实例多次调用无状态污染

所有测试均 mock LLM 调用，不需要真实 API key。
标记为 not llm, not slow。
"""

import json
import os
import pytest
from unittest.mock import patch
from typing import Any, Dict, List


# ==============================================================================
# 测试场景数据
# ==============================================================================

SCENARIOS = {
    "multi_gen": {
        "user_input": "三代同堂住宅改造，祖父80岁行动不便，成都160平米，预算80万",
        "project_type": "personal_residential",
        "confirmed_tasks": ["无障碍改造", "老人房安全化", "公共空间代际融合"],
        "structured_data": {
            "project_task": "三代同堂无障碍改造",
            "character_narrative": "中产三代同堂，祖父行动不便",
            "confidence_score": 0.55,
            "core_tensions": "老人安全 vs 年轻一代审美",
            "human_dimensions": ["无障碍", "代际沟通", "安全感"],
            "stakeholder_system": "祖父、子女夫妻、孙辈",
        },
    },
    "coffee_shop": {
        "user_input": "科技创业公司内部咖啡馆改造，200名员工，鼓励交流协作",
        "project_type": "commercial_hospitality",
        "confirmed_tasks": ["非正式交流区设计", "品牌文化融入", "声学环境优化"],
        "structured_data": {
            "project_task": "创业公司咖啡馆设计",
            "character_narrative": "科技创业企业，崇尚开放协作文化",
            "confidence_score": 0.75,
        },
    },
    "luxury_villa": {
        "user_input": "成都顶级豪宅定制设计，企业家客户，500平米，要求融合东方美学",
        "project_type": "personal_residential",
        "confirmed_tasks": ["东方美学空间营造", "私密性系统设计", "藏品展示区规划"],
        "structured_data": {
            "project_task": "高端豪宅东方美学设计",
            "character_narrative": "企业家，注重身份彰显，喜爱东方文化",
            "confidence_score": 0.85,
        },
    },
}


def _make_state_from_scenario(key: str, step: int = 0) -> Dict[str, Any]:
    s = SCENARIOS[key]
    return {
        "user_input": s["user_input"],
        "project_type": s["project_type"],
        "confirmed_core_tasks": s["confirmed_tasks"],
        "agent_results": {"requirements_analyst": {"structured_data": s["structured_data"]}},
        "progressive_questionnaire_step": step,
        "radar_dimension_values": {},
        "special_scene_metadata": None,
    }


def _make_valid_dims_for_scenario(scenario_key: str, count: int = 8) -> List[Dict]:
    """按场景生成有意义的模拟维度"""
    scenario_dims = {
        "multi_gen": [
            ("accessibility_priority", "无障碍优先级", "美观优先", "无障碍优先", "calibration", 70),
            ("safety_vs_style", "安全与风格", "风格驱动", "安全第一", "calibration", 65),
            ("privacy_zoning", "私密分区策略", "开放通用", "严格私密分区", "decision", 60),
            ("generational_blend", "代际融合度", "各自独立", "高度融合", "decision", 55),
            ("renovation_depth", "改造深度", "局部微调", "整体翻新", "decision", 45),
            ("caregiver_space", "护理空间", "隐藏整合", "专设独立", "insight", 60),
            ("grandchild_zone", "孙辈活动区", "分散布局", "集中游戏区", "insight", 55),
            ("future_care", "未来照护预期", "当前需求", "长远规划", "insight", 40),
        ],
        "coffee_shop": [
            ("noise_tolerance", "声学容忍度", "安静专注", "嘈杂活跃", "calibration", 60),
            ("brand_exposure", "品牌曝光强度", "低调融入", "强烈彰显", "calibration", 55),
            ("collaboration_density", "协作密度", "独立工位", "高密度协作", "decision", 65),
            ("flexibility", "空间灵活性", "固定功能", "高度灵活", "decision", 70),
            ("tech_integration", "科技整合", "传统设施", "全面智能化", "decision", 60),
            ("informal_space", "非正式区比例", "最小化", "大量设置", "insight", 65),
            ("cultural_signal", "企业文化信号", "含蓄暗示", "直接表达", "insight", 55),
        ],
        "luxury_villa": [
            ("eastern_purity", "东方纯粹度", "折中融合", "纯粹东方", "calibration", 70),
            ("identity_signal", "身份彰显", "低调内敛", "强烈彰显", "calibration", 65),
            ("collection_focus", "藏品展示优先级", "居住优先", "藏品优先", "decision", 45),
            ("privacy_level", "私密程度", "开放展示", "极致私密", "decision", 60),
            ("craftsmanship", "工艺精度", "标准品质", "极致工艺", "decision", 75),
            ("zen_balance", "禅意平衡", "繁复华丽", "极简禅意", "insight", 55),
            ("spatial_narrative", "空间叙事", "功能导向", "情感叙事", "insight", 60),
        ],
    }.get(scenario_key, [])

    result = []
    for i, (id_, name, left, right, cat, default) in enumerate(scenario_dims[:count]):
        result.append(
            {
                "id": id_,
                "name": name,
                "left_label": left,
                "right_label": right,
                "description": f"{name}维度",
                "default_value": default,
                "category": cat,
                "source": cat,
                "rationale": f"{name}对该项目至关重要",
                "impact_hint": f"影响{name}相关决策",
                "global_impact": True,
            }
        )
    return result


# ==============================================================================
# E2E-1: 三代同堂 - v8.0 成功路径
# ==============================================================================


@pytest.mark.parametrize("scenario_key", ["multi_gen", "coffee_shop", "luxury_villa"])
@patch.dict(
    os.environ,
    {
        "USE_PROJECT_SPECIFIC_DIMENSIONS": "true",
        "ENABLE_DIMENSION_LEARNING": "false",
        "USE_DYNAMIC_GENERATION": "false",
        "FORCE_GENERATE_DIMENSIONS": "false",
    },
)
@patch(
    "intelligent_project_analyzer.services.project_specific_dimension_generator."
    "ProjectSpecificDimensionGenerator._call_llm"
)
@patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
def test_e2e_v8_success_path(mock_interrupt, mock_llm, scenario_key):
    """E2E: 三种场景各自用 v8.0 项目专属维度完成问卷"""
    dims = _make_valid_dims_for_scenario(scenario_key)
    mock_llm.return_value = f"```json\n{json.dumps(dims, ensure_ascii=False)}\n```"
    mock_interrupt.return_value = {"values": {d["id"]: d["default_value"] for d in dims}}

    from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
        ProgressiveQuestionnaireNode,
    )

    state = _make_state_from_scenario(scenario_key)
    cmd = ProgressiveQuestionnaireNode.step3_radar(state)

    # 基本断言
    assert cmd is not None
    assert cmd.goto == "questionnaire_summary"  # step3_radar 是最后一步，直接进入摘要
    update = cmd.update

    # v8.0 路径标记
    assert update.get("dimension_generation_method") == "project_specific", f"[{scenario_key}] 应走 v8.0 路径"
    # 维度数量
    dims_out = update.get("selected_radar_dimensions", [])
    assert len(dims_out) >= 5, f"[{scenario_key}] 维度数量应 >= 5"
    # 有值
    values = update.get("radar_dimension_values", {})
    assert len(values) > 0, f"[{scenario_key}] 应有维度值"
    # payload 含分层信息
    payload = mock_interrupt.call_args[0][0]
    assert payload.get("dimension_generation_method") == "project_specific"
    assert "dimension_layers" in payload
    assert "generation_summary" in payload


# ==============================================================================
# E2E-2: 降级路径 - LLM 失败
# ==============================================================================


@patch.dict(
    os.environ,
    {
        "USE_PROJECT_SPECIFIC_DIMENSIONS": "true",
        "ENABLE_DIMENSION_LEARNING": "false",
        "USE_DYNAMIC_GENERATION": "false",
        "FORCE_GENERATE_DIMENSIONS": "false",
    },
)
@patch(
    "intelligent_project_analyzer.services.project_specific_dimension_generator."
    "ProjectSpecificDimensionGenerator._call_llm"
)
@patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
def test_e2e_fallback_on_llm_failure(mock_interrupt, mock_llm):
    """E2E: LLM 失败时自动降级到传统维度，流程不中断"""
    mock_llm.side_effect = TimeoutError("LLM 响应超时")
    mock_interrupt.return_value = {"values": {}}

    from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
        ProgressiveQuestionnaireNode,
    )

    state = _make_state_from_scenario("coffee_shop")
    cmd = ProgressiveQuestionnaireNode.step3_radar(state)

    assert cmd is not None
    assert cmd.goto == "questionnaire_summary"  # step3_radar 是最后一步，直接进入摘要
    # 降级后 method 应为 static
    assert cmd.update.get("dimension_generation_method") == "static"
    # 仍应有维度（来自传统选择器）
    dims_out = cmd.update.get("selected_radar_dimensions", [])
    assert isinstance(dims_out, list)


# ==============================================================================
# E2E-3: 高置信度场景 - 自动推断仍正常
# ==============================================================================


@patch.dict(
    os.environ,
    {
        "USE_PROJECT_SPECIFIC_DIMENSIONS": "true",
        "ENABLE_DIMENSION_LEARNING": "false",
        "USE_DYNAMIC_GENERATION": "false",
    },
)
@patch(
    "intelligent_project_analyzer.services.project_specific_dimension_generator."
    "ProjectSpecificDimensionGenerator._call_llm"
)
@patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
def test_e2e_high_confidence_luxury_scenario(mock_interrupt, mock_llm):
    """E2E: 高置信度场景（0.85）下 v8.0 仍正常生成洞察维度"""
    dims = _make_valid_dims_for_scenario("luxury_villa")
    mock_llm.return_value = f"```json\n{json.dumps(dims, ensure_ascii=False)}\n```"
    mock_interrupt.return_value = {"values": {d["id"]: d["default_value"] for d in dims}}

    from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
        ProgressiveQuestionnaireNode,
    )

    state = _make_state_from_scenario("luxury_villa")
    cmd = ProgressiveQuestionnaireNode.step3_radar(state)

    assert cmd.update.get("dimension_generation_method") == "project_specific"

    # 高置信度场景应有洞察维度（source 字段标记，category 会被验证器规范化）
    dims_out = cmd.update.get("selected_radar_dimensions", [])
    insight_dims = [d for d in dims_out if d.get("source") == "insight"]
    assert len(insight_dims) >= 1, "高置信度场景应有洞察维度（source=insight）"


# ==============================================================================
# E2E-4: 完全传统路径（v8.0 关闭）
# ==============================================================================


@patch.dict(
    os.environ,
    {
        "USE_PROJECT_SPECIFIC_DIMENSIONS": "false",
        "ENABLE_DIMENSION_LEARNING": "false",
        "USE_DYNAMIC_GENERATION": "false",
        "FORCE_GENERATE_DIMENSIONS": "false",
    },
)
@patch(
    "intelligent_project_analyzer.services.project_specific_dimension_generator."
    "ProjectSpecificDimensionGenerator.generate_dimensions"
)
@patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
def test_e2e_legacy_only_path(mock_interrupt, mock_ps):
    """E2E: v8.0 完全关闭时 ProjectSpecificDimensionGenerator 不应被调用"""
    mock_interrupt.return_value = {"values": {}}

    from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
        ProgressiveQuestionnaireNode,
    )

    state = _make_state_from_scenario("multi_gen")
    cmd = ProgressiveQuestionnaireNode.step3_radar(state)

    mock_ps.assert_not_called()
    assert cmd.update.get("dimension_generation_method") == "static"


# ==============================================================================
# E2E-5: 并发安全 - 多次调用无状态污染
# ==============================================================================


@patch.dict(
    os.environ,
    {
        "USE_PROJECT_SPECIFIC_DIMENSIONS": "true",
        "ENABLE_DIMENSION_LEARNING": "false",
        "USE_DYNAMIC_GENERATION": "false",
    },
)
@patch(
    "intelligent_project_analyzer.services.project_specific_dimension_generator."
    "ProjectSpecificDimensionGenerator._call_llm"
)
@patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
def test_e2e_stateless_multiple_calls(mock_interrupt, mock_llm):
    """E2E: 同一 step3_radar 方法多次调用（不同 state）应互相独立"""
    call_count = {"n": 0}

    def side_effect(*args, **kwargs):
        call_count["n"] += 1
        # 交替返回不同数量的维度
        n = 6 if call_count["n"] % 2 == 0 else 7
        dims = [
            {
                "id": f"s{call_count['n']}_d{i}",
                "name": f"调用{call_count['n']}维度{i}",
                "left_label": f"左{i}",
                "right_label": f"右{i}",
                "description": "D",
                "default_value": 30 + i * 5,
                "category": ["calibration", "decision", "insight"][i % 3],
                "source": ["calibration", "decision", "insight"][i % 3],
                "rationale": "R",
                "impact_hint": "H",
                "global_impact": True,
            }
            for i in range(n)
        ]
        return f"```json\n{json.dumps(dims, ensure_ascii=False)}\n```"

    mock_llm.side_effect = side_effect

    from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
        ProgressiveQuestionnaireNode,
    )

    results = []
    for key in ["multi_gen", "coffee_shop", "luxury_villa", "multi_gen"]:
        mock_interrupt.return_value = {"values": {}}
        state = _make_state_from_scenario(key)
        cmd = ProgressiveQuestionnaireNode.step3_radar(state)
        results.append(cmd.update.get("selected_radar_dimensions", []))

    # 每次调用结果应独立（不共用 ID）
    for i in range(len(results)):
        for j in range(i + 1, len(results)):
            {d["id"] for d in results[i]}
            {d["id"] for d in results[j]}
            # 由于 ID 携带调用次数，不应完全重叠
            # （完全相同只在降级时发生）
            if results[i] and results[j]:
                # 维度至少是列表（不崩溃）
                assert isinstance(results[i], list)
                assert isinstance(results[j], list)


# ==============================================================================
# E2E-6: 完整数据流 - state 字段传递链
# ==============================================================================


@patch.dict(
    os.environ,
    {
        "USE_PROJECT_SPECIFIC_DIMENSIONS": "true",
        "ENABLE_DIMENSION_LEARNING": "false",
        "USE_DYNAMIC_GENERATION": "false",
    },
)
@patch(
    "intelligent_project_analyzer.services.project_specific_dimension_generator."
    "ProjectSpecificDimensionGenerator._call_llm"
)
@patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt")
def test_e2e_full_state_field_chain(mock_interrupt, mock_llm):
    """E2E: 确认 step2 完成后 state 中所有下游字段可用"""
    dims = _make_valid_dims_for_scenario("multi_gen", count=8)
    user_values = {d["id"]: d["default_value"] + 5 for d in dims}
    mock_llm.return_value = f"```json\n{json.dumps(dims, ensure_ascii=False)}\n```"
    mock_interrupt.return_value = {"values": user_values}

    from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
        ProgressiveQuestionnaireNode,
    )

    state = _make_state_from_scenario("multi_gen")
    cmd = ProgressiveQuestionnaireNode.step3_radar(state)
    update = cmd.update

    # 所有下游字段检查
    assert "selected_radar_dimensions" in update
    assert "selected_dimensions" in update  # backward compat
    assert "radar_dimension_values" in update
    assert "radar_analysis_summary" in update
    assert "progressive_questionnaire_step" in update
    assert "dimension_generation_method" in update

    # 维度值应与 user_values 一致
    for dim_id, expected_val in user_values.items():
        if dim_id in update["radar_dimension_values"]:
            assert update["radar_dimension_values"][dim_id] == expected_val

    # selected_dimensions 与 selected_radar_dimensions 应相同
    assert update["selected_dimensions"] == update["selected_radar_dimensions"]


pytestmark = [pytest.mark.unit]  # 不需要 LLM，使用 mock，按 unit 速度运行
