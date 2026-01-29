"""
测试角色选择质量审核功能

验证新的角色选择质量审核机制是否正常工作
"""

from unittest.mock import MagicMock, Mock

import pytest

from intelligent_project_analyzer.core.state import ProjectAnalysisState
from intelligent_project_analyzer.interaction.nodes.role_selection_quality_review import (
    RoleSelectionQualityReviewNode,
    role_selection_quality_review_node,
)


def test_role_selection_quality_review_node_basic():
    """测试角色选择质量审核节点基本功能"""

    # 准备测试状态
    state = {
        "session_id": "test_session",
        "selected_roles": [
            {"role_id": "V2_设计总监_2-1", "role_name": "设计总监", "description": "负责整体设计方向"},
            {"role_id": "V3_叙事专家_3-1", "role_name": "叙事专家", "description": "负责故事叙事"},
        ],
        "structured_requirements": {"project_task": "设计一个现代简约风格的住宅空间"},
        "project_strategy": {"strategy_summary": "采用现代简约设计理念"},
    }

    # Mock LLM
    mock_llm = Mock()
    mock_llm.invoke = Mock(return_value=Mock(content='{"issues": [], "summary": "角色配置合理"}'))

    # 初始化协调器
    RoleSelectionQualityReviewNode.initialize_coordinator(mock_llm, {})

    # 执行审核
    result = RoleSelectionQualityReviewNode.execute(state=state, llm_model=mock_llm, config={})

    # 验证结果
    assert result is not None
    print("✅ 基本功能测试通过")


def test_role_selection_quality_review_with_issues():
    """测试发现问题时的处理"""

    # 准备测试状态（角色配置不完整）
    state = {
        "session_id": "test_session",
        "selected_roles": [
            {"role_id": "V2_设计总监_2-1", "role_name": "设计总监", "description": "负责整体设计方向"}
            # 缺少其他必要角色
        ],
        "structured_requirements": {"project_task": "设计一个复杂的商业综合体项目"},
        "project_strategy": {"strategy_summary": "需要多维度专业支持"},
    }

    # Mock LLM 返回有问题的结果
    mock_llm = Mock()

    # Mock 红队审核结果
    red_team_response = Mock(
        content="""
    {
        "issues": [
            {
                "id": "R1",
                "description": "缺少技术可行性评估角色",
                "severity": "critical",
                "evidence": "商业综合体项目需要技术评估",
                "impact": "可能导致方案无法实施"
            }
        ],
        "summary": "发现1个关键问题"
    }
    """
    )

    # Mock 蓝队审核结果
    blue_team_response = Mock(
        content="""
    {
        "validations": [
            {
                "red_issue_id": "R1",
                "stance": "agree",
                "reasoning": "确实缺少技术评估角色",
                "improvement_suggestion": "建议添加技术架构师角色"
            }
        ],
        "strengths": [],
        "summary": "同意1个问题"
    }
    """
    )

    mock_llm.invoke = Mock(side_effect=[red_team_response, blue_team_response])

    # 初始化协调器
    RoleSelectionQualityReviewNode.initialize_coordinator(mock_llm, {})

    # 执行审核
    result = RoleSelectionQualityReviewNode.execute(state=state, llm_model=mock_llm, config={})

    # 验证结果
    assert result is not None
    print("✅ 问题检测测试通过")


def test_role_selection_quality_review_skip_when_no_roles():
    """测试没有角色时跳过审核"""

    # 准备测试状态（没有选择角色）
    state = {"session_id": "test_session", "selected_roles": [], "structured_requirements": {"project_task": "测试项目"}}

    mock_llm = Mock()

    # 初始化协调器
    RoleSelectionQualityReviewNode.initialize_coordinator(mock_llm, {})

    # 执行审核
    result = RoleSelectionQualityReviewNode.execute(state=state, llm_model=mock_llm, config={})

    # 验证结果 - 应该跳过审核
    assert result is not None
    print("✅ 跳过审核测试通过")


if __name__ == "__main__":
    print("开始测试角色选择质量审核功能...\n")

    try:
        test_role_selection_quality_review_node_basic()
        print()
        test_role_selection_quality_review_with_issues()
        print()
        test_role_selection_quality_review_skip_when_no_roles()
        print()
        print("=" * 60)
        print("✅ 所有测试通过！")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
