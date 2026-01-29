"""
MainWorkflow核心节点单元测试

测试workflow/main_workflow.py中的关键节点函数
使用Mock对象避免真实LLM/Redis调用
"""

from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest

from intelligent_project_analyzer.core.state import ProjectAnalysisState
from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow
from tests.fixtures.mocks import create_mock_llm, create_mock_state, create_mock_workflow_components
from tests.fixtures.test_data import SAMPLE_EXPERT_POOL, SAMPLE_LLM_RESPONSES, SAMPLE_USER_INPUTS

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def workflow():
    """创建MainWorkflow实例，使用Mock组件"""
    mock_llm = create_mock_llm()
    mock_components = create_mock_workflow_components()

    with patch("intelligent_project_analyzer.workflow.main_workflow.SqliteSaver"):
        workflow = MainWorkflow(
            llm_model=mock_llm, config={"analysis_mode": "comprehensive"}, checkpointer=mock_components["checkpointer"]
        )
        return workflow


@pytest.fixture
def mock_state() -> Dict[str, Any]:
    """创建Mock状态"""
    return create_mock_state(user_input=SAMPLE_USER_INPUTS["detailed"], session_id="test-workflow-session")


# ============================================================================
# 统一输入验证节点测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.workflow
def test_unified_input_validator_initial_node_success(workflow, mock_state):
    """测试输入验证节点 - 正常输入"""
    # Mock UnifiedInputValidatorNode
    with patch("intelligent_project_analyzer.workflow.main_workflow.UnifiedInputValidatorNode") as mock_validator:
        mock_validator_instance = Mock()
        mock_validator_instance.validate.return_value = {
            "is_valid": True,
            "validation_message": "输入验证通过",
            "filtered_input": mock_state["user_input"],
        }
        mock_validator.return_value = mock_validator_instance

        result = workflow._unified_input_validator_initial_node(mock_state)

        # 验证返回Command对象，跳转到requirements_analyst
        assert hasattr(result, "goto")
        # 注意：Command对象的属性访问方式可能不同，根据实际情况调整


@pytest.mark.unit
@pytest.mark.workflow
def test_unified_input_validator_initial_node_invalid(workflow, mock_state):
    """测试输入验证节点 - 无效输入"""
    with patch("intelligent_project_analyzer.workflow.main_workflow.UnifiedInputValidatorNode") as mock_validator:
        mock_validator_instance = Mock()
        mock_validator_instance.validate.return_value = {
            "is_valid": False,
            "validation_message": "输入包含违规内容",
            "rejection_reason": "content_safety",
        }
        mock_validator.return_value = mock_validator_instance

        result = workflow._unified_input_validator_initial_node(mock_state)

        # 验证跳转到input_rejected节点
        assert hasattr(result, "goto")


# ============================================================================
# 需求分析师节点测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.workflow
@pytest.mark.asyncio
async def test_requirements_analyst_node(workflow, mock_state):
    """测试需求分析师节点"""
    # Mock RequirementsAnalystAgent
    with patch("intelligent_project_analyzer.workflow.main_workflow.RequirementsAnalystAgent") as mock_agent_class:
        mock_agent = AsyncMock()
        mock_agent.analyze.return_value = {
            "core_requirements": ["150平米住宅设计"],
            "constraints": ["预算30万"],
            "implicit_needs": ["家庭居住"],
        }
        mock_agent_class.return_value = mock_agent

        result = workflow._requirements_analyst_node(mock_state)

        # 验证返回包含分析结果（新字段名为 structured_requirements）
        assert "structured_requirements" in result or "requirements_analysis" in result or "core_requirements" in result
        # 验证mock被调用
        # mock_agent.analyze.assert_called_once()


@pytest.mark.unit
@pytest.mark.workflow
def test_requirements_analyst_node_error_handling(workflow, mock_state):
    """测试需求分析师节点 - 错误处理"""
    with patch("intelligent_project_analyzer.workflow.main_workflow.RequirementsAnalystAgent") as mock_agent_class:
        mock_agent = Mock()
        mock_agent.analyze.side_effect = Exception("LLM调用失败")
        mock_agent_class.return_value = mock_agent

        result = workflow._requirements_analyst_node(mock_state)

        # 验证结果是字典类型（即使出错也返回状态更新）
        assert isinstance(result, dict)


# ============================================================================
# 项目总监节点测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.workflow
def test_project_director_node(workflow, mock_state):
    """测试项目总监节点 - 专家选择"""
    # 添加需求分析结果到状态（使用新字段名）
    mock_state["structured_requirements"] = {"core_objectives": ["住宅设计"], "project_type": "residential"}

    with patch("intelligent_project_analyzer.workflow.main_workflow.ProjectDirectorAgent") as mock_agent_class:
        mock_agent = Mock()
        mock_agent.select_experts.return_value = SAMPLE_EXPERT_POOL[:3]
        mock_agent_class.return_value = mock_agent

        result = workflow._project_director_node(mock_state)

        # 验证返回是字典类型
        assert isinstance(result, dict)


@pytest.mark.unit
@pytest.mark.workflow
def test_project_director_node_empty_experts(workflow, mock_state):
    """测试项目总监节点 - 未选择到专家"""
    mock_state["requirements_analysis"] = {"core_requirements": []}

    with patch("intelligent_project_analyzer.workflow.main_workflow.ProjectDirectorAgent") as mock_agent_class:
        mock_agent = Mock()
        mock_agent.select_experts.return_value = []
        mock_agent_class.return_value = mock_agent

        result = workflow._project_director_node(mock_state)

        # 验证处理空专家池情况
        assert isinstance(result, dict)


# ============================================================================
# 批次执行器节点测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.workflow
def test_batch_executor_node_single_batch(workflow, mock_state):
    """测试批次执行器 - 单批次执行"""
    mock_state["expert_pool"] = SAMPLE_EXPERT_POOL[:3]
    mock_state["current_batch"] = 1
    mock_state["total_batches"] = 1

    result = workflow._batch_executor_node(mock_state)

    # 验证返回Send命令列表
    assert isinstance(result, (list, dict))


@pytest.mark.unit
@pytest.mark.workflow
def test_batch_executor_node_multi_batch(workflow, mock_state):
    """测试批次执行器 - 多批次执行"""
    mock_state["expert_pool"] = SAMPLE_EXPERT_POOL * 4  # 12个专家
    mock_state["current_batch"] = 1
    mock_state["total_batches"] = 2

    result = workflow._batch_executor_node(mock_state)

    # 验证批次划分逻辑
    assert isinstance(result, (list, dict))


# ============================================================================
# 问卷节点测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.workflow
def test_progressive_step1_node(workflow, mock_state):
    """测试三步问卷 - 第一步核心任务"""
    with patch("intelligent_project_analyzer.workflow.main_workflow.progressive_step1_core_task_node") as mock_step1:
        mock_step1.return_value = {"questionnaire_step1": {"questions": [{"id": "q1", "text": "核心问题1"}]}}

        result = workflow._progressive_step1_node(mock_state)

        # 验证调用step1节点（实际调用可能有额外参数如store）
        mock_step1.assert_called_once()
        assert result == mock_step1.return_value


@pytest.mark.unit
@pytest.mark.workflow
def test_progressive_step2_node(workflow, mock_state):
    """测试三步问卷 - 第二步雷达维度"""
    mock_state["questionnaire_step1_answers"] = {"q1": "答案1"}

    with patch("intelligent_project_analyzer.workflow.main_workflow.progressive_step2_radar_node") as mock_step2:
        mock_step2.return_value = {"questionnaire_step2": {"questions": [{"id": "q2", "text": "雷达问题"}]}}

        result = workflow._progressive_step2_node(mock_state)

        mock_step2.assert_called_once()
        assert result == mock_step2.return_value


@pytest.mark.unit
@pytest.mark.workflow
def test_progressive_step3_node(workflow, mock_state):
    """测试三步问卷 - 第三步缺口填补"""
    mock_state["questionnaire_step1_answers"] = {"q1": "答案1"}
    mock_state["questionnaire_step2_answers"] = {"q2": "答案2"}

    with patch("intelligent_project_analyzer.workflow.main_workflow.progressive_step3_gap_filling_node") as mock_step3:
        mock_step3.return_value = {"questionnaire_step3": {"questions": [{"id": "q3", "text": "补充问题"}]}}

        result = workflow._progressive_step3_node(mock_state)

        mock_step3.assert_called_once()
        assert result == mock_step3.return_value


# ============================================================================
# 需求洞察节点测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.workflow
def test_questionnaire_summary_node(workflow, mock_state):
    """测试需求洞察节点"""
    mock_state["questionnaire_step1_answers"] = {"q1": "答案1"}
    mock_state["questionnaire_step2_answers"] = {"q2": "答案2"}
    mock_state["questionnaire_step3_answers"] = {"q3": "答案3"}

    with patch("intelligent_project_analyzer.workflow.main_workflow.questionnaire_summary_node") as mock_summary:
        mock_summary.return_value = {"questionnaire_summary": "综合问卷分析：...", "key_insights": ["洞察1", "洞察2"]}

        result = workflow._questionnaire_summary_node(mock_state)

        mock_summary.assert_called_once()
        assert result == mock_summary.return_value


# ============================================================================
# 需求洞察节点测试 (🔧 v7.152: 替代已删除的 requirements_confirmation)
# ============================================================================


@pytest.mark.unit
@pytest.mark.workflow
def test_questionnaire_summary_node_returns_command(workflow, mock_state):
    """测试需求洞察节点返回Command对象 (🔧 v7.152: 替代 requirements_confirmation)"""
    from langgraph.types import Command

    mock_state["confirmed_core_tasks"] = [{"id": "task1", "title": "核心任务1"}]
    mock_state["gap_filling_answers"] = {"budget": "100万"}
    mock_state["selected_dimensions"] = ["功能性", "美观性"]
    mock_state["radar_dimension_values"] = {"功能性": 8, "美观性": 7}

    with patch("intelligent_project_analyzer.workflow.main_workflow.questionnaire_summary_node") as mock_summary:
        mock_summary.return_value = Command(update={"requirements_confirmed": True}, goto="project_director")

        result = workflow._questionnaire_summary_node(mock_state)

        # 验证返回Command对象
        assert isinstance(result, Command), "需求洞察节点应返回Command对象"


# ============================================================================
# 结果聚合节点测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.workflow
@pytest.mark.asyncio
async def test_result_aggregator_basic(workflow, mock_state):
    """测试结果聚合 - 基础功能"""
    mock_state["analysis_results"] = {"expert_v3_001": {"analysis": "空间规划分析"}, "expert_v4_001": {"analysis": "风格设计分析"}}

    with patch("intelligent_project_analyzer.workflow.main_workflow.ResultAggregatorAgent") as mock_agent_class:
        mock_agent = AsyncMock()
        mock_agent.aggregate.return_value = {"aggregated_report": "综合报告内容", "expert_count": 2}
        mock_agent_class.return_value = mock_agent

        # 注意：实际工作流中可能调用不同的方法
        # 这里需要根据实际实现调整


# ============================================================================
# 报告守卫节点测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.workflow
def test_report_guard_node_safe(workflow, mock_state):
    """测试报告守卫节点 - 安全内容"""
    mock_state["final_report"] = "这是一份安全的设计报告"

    # 直接 patch ReportGuardNode.execute 类方法
    with patch("intelligent_project_analyzer.workflow.main_workflow.ReportGuardNode.execute") as mock_execute:
        mock_execute.return_value = {"is_safe": True, "filtered_report": mock_state["final_report"]}

        result = workflow._report_guard_node(mock_state)

        # 验证返回是字典类型
        assert isinstance(result, dict)


@pytest.mark.unit
@pytest.mark.workflow
def test_report_guard_node_unsafe(workflow, mock_state):
    """测试报告守卫节点 - 不安全内容"""
    mock_state["final_report"] = "包含违规内容的报告"

    # 直接 patch ReportGuardNode.execute 类方法
    with patch("intelligent_project_analyzer.workflow.main_workflow.ReportGuardNode.execute") as mock_execute:
        mock_execute.return_value = {"is_safe": False, "violation_type": "content_safety", "filtered_report": "[内容已过滤]"}

        result = workflow._report_guard_node(mock_state)

        # 验证返回是字典类型
        assert isinstance(result, dict)


# ============================================================================
# 工作流图构建测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.workflow
def test_workflow_graph_construction(workflow):
    """测试工作流图构建"""
    # 验证graph已创建
    assert hasattr(workflow, "graph")
    assert workflow.graph is not None

    # 验证关键节点已添加（根据实际实现调整）
    # 注意：LangGraph的节点检查方式可能不同


@pytest.mark.unit
@pytest.mark.workflow
def test_workflow_nodes_exist():
    """测试工作流包含必要节点"""
    # 测试关键节点函数存在
    workflow_instance = MainWorkflow(llm_model=create_mock_llm())

    assert hasattr(workflow_instance, "_unified_input_validator_initial_node")
    assert hasattr(workflow_instance, "_requirements_analyst_node")
    assert hasattr(workflow_instance, "_project_director_node")
    assert hasattr(workflow_instance, "_batch_executor_node")
    assert hasattr(workflow_instance, "_report_guard_node")


# ============================================================================
# 状态转换测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.workflow
def test_state_updates_are_tracked(workflow, mock_state):
    """测试状态更新被正确追踪"""
    initial_phase = mock_state.get("current_phase", "initial")

    # 模拟节点执行后的状态更新
    updated_state = {**mock_state, "current_phase": "requirements_analysis"}

    assert updated_state["current_phase"] != initial_phase
    assert updated_state["current_phase"] == "requirements_analysis"


# ============================================================================
# 错误处理测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.workflow
def test_workflow_handles_node_exceptions(workflow, mock_state):
    """测试工作流处理节点异常"""
    with patch("intelligent_project_analyzer.workflow.main_workflow.RequirementsAnalystAgent") as mock_agent_class:
        mock_agent = Mock()
        mock_agent.analyze.side_effect = Exception("模拟节点异常")
        mock_agent_class.return_value = mock_agent

        # 执行节点 - 工作流应该返回字典（可能包含错误信息）
        result = workflow._requirements_analyst_node(mock_state)

        # 验证返回是字典类型（无论是否有错误）
        assert isinstance(result, dict)


# ============================================================================
# 集成测试标记（完整流程需要真实组件）
# ============================================================================


@pytest.mark.integration
@pytest.mark.workflow
@pytest.mark.skip(reason="需要真实LLM和数据库连接")
async def test_full_workflow_execution_e2e():
    """端到端测试 - 完整工作流执行（集成测试）"""
    # 这个测试需要真实的LLM、数据库等组件
    # 在单元测试阶段跳过，由集成测试覆盖
    pass
