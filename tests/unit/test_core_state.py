"""
core/state.py 单元测试

测试ProjectAnalysisState的TypedDict定义、reducer函数和状态管理逻辑
"""

from datetime import datetime
from typing import Any, Dict, List

import pytest

from intelligent_project_analyzer.core.state import (
    AnalysisStage,
    ProjectAnalysisState,
    StateManager,
    merge_agent_results,
    merge_lists,
    take_max_timestamp,
)

# ============================================================================
# AnalysisStage枚举测试
# ============================================================================


@pytest.mark.unit
def test_analysis_stage_enum():
    """测试分析阶段枚举"""
    assert AnalysisStage.INIT.value == "init"
    assert AnalysisStage.REQUIREMENT_COLLECTION.value == "requirement_collection"
    assert AnalysisStage.COMPLETED.value == "completed"
    assert AnalysisStage.ERROR.value == "error"


@pytest.mark.unit
def test_analysis_stage_enum_completeness():
    """测试分析阶段包含所有必要阶段"""
    required_stages = [
        "init",
        "requirement_collection",
        "strategic_analysis",
        "result_aggregation",
        "completed",
        "error",
    ]

    enum_values = [stage.value for stage in AnalysisStage]

    for stage in required_stages:
        assert stage in enum_values, f"缺少阶段: {stage}"


# ============================================================================
# Reducer函数测试 - merge_agent_results
# ============================================================================


@pytest.mark.unit
def test_merge_agent_results_both_dicts():
    """测试合并两个字典结果"""
    left = {"expert_v3_001": {"analysis": "分析1"}}
    right = {"expert_v4_001": {"analysis": "分析2"}}

    result = merge_agent_results(left, right)

    assert len(result) == 2
    assert "expert_v3_001" in result
    assert "expert_v4_001" in result


@pytest.mark.unit
def test_merge_agent_results_overlapping_keys():
    """测试合并时覆盖同名键"""
    left = {"expert_v3_001": {"analysis": "旧分析"}}
    right = {"expert_v3_001": {"analysis": "新分析"}}

    result = merge_agent_results(left, right)

    assert result["expert_v3_001"]["analysis"] == "新分析"


@pytest.mark.unit
def test_merge_agent_results_left_none():
    """测试左侧为None的情况"""
    right = {"expert_v3_001": {"analysis": "分析1"}}

    result = merge_agent_results(None, right)

    assert result == right


@pytest.mark.unit
def test_merge_agent_results_right_none():
    """测试右侧为None的情况"""
    left = {"expert_v3_001": {"analysis": "分析1"}}

    result = merge_agent_results(left, None)

    assert result == left


@pytest.mark.unit
def test_merge_agent_results_both_none():
    """测试两侧都为None的情况"""
    result = merge_agent_results(None, None)

    assert result == {}


# ============================================================================
# Reducer函数测试 - merge_lists
# ============================================================================


@pytest.mark.unit
def test_merge_lists_basic():
    """测试基本列表合并"""
    left = ["item1", "item2"]
    right = ["item3", "item4"]

    result = merge_lists(left, right)

    assert len(result) == 4
    assert result == ["item1", "item2", "item3", "item4"]


@pytest.mark.unit
def test_merge_lists_with_duplicates():
    """测试列表合并时去重"""
    left = ["item1", "item2"]
    right = ["item2", "item3"]

    result = merge_lists(left, right)

    assert len(result) == 3
    assert result == ["item1", "item2", "item3"]


@pytest.mark.unit
def test_merge_lists_maintains_order():
    """测试列表合并保持顺序"""
    left = ["item1", "item2"]
    right = ["item3", "item1"]

    result = merge_lists(left, right)

    # item1已存在，不重复添加，item3追加到末尾
    assert result == ["item1", "item2", "item3"]


@pytest.mark.unit
def test_merge_lists_left_none():
    """测试左侧为None的情况"""
    right = ["item1", "item2"]

    result = merge_lists(None, right)

    assert result == right


@pytest.mark.unit
def test_merge_lists_right_none():
    """测试右侧为None的情况"""
    left = ["item1", "item2"]

    result = merge_lists(left, None)

    assert result == left


@pytest.mark.unit
def test_merge_lists_both_none():
    """测试两侧都为None的情况"""
    result = merge_lists(None, None)

    assert result == []


# ============================================================================
# Reducer函数测试 - take_max_timestamp
# ============================================================================


@pytest.mark.unit
def test_take_max_timestamp_left_newer():
    """测试选择较新的时间戳 - 左侧更新"""
    left = "2026-01-06T12:00:00Z"
    right = "2026-01-06T11:00:00Z"

    result = take_max_timestamp(left, right)

    assert result == left


@pytest.mark.unit
def test_take_max_timestamp_right_newer():
    """测试选择较新的时间戳 - 右侧更新"""
    left = "2026-01-06T11:00:00Z"
    right = "2026-01-06T12:00:00Z"

    result = take_max_timestamp(left, right)

    assert result == right


@pytest.mark.unit
def test_take_max_timestamp_equal():
    """测试时间戳相同的情况"""
    timestamp = "2026-01-06T12:00:00Z"

    result = take_max_timestamp(timestamp, timestamp)

    assert result == timestamp


# ============================================================================
# StateManager测试
# ============================================================================


@pytest.mark.unit
def test_state_manager_create_initial_state():
    """测试创建初始状态"""
    session_id = "test-session-123"
    user_input = "设计一个咖啡店"

    state = StateManager.create_initial_state(session_id=session_id, user_input=user_input)

    assert state["session_id"] == session_id
    assert state["user_input"] == user_input
    assert state["current_stage"] == AnalysisStage.INIT.value  # 字符串值
    assert "created_at" in state
    assert "agent_results" in state  # agent_results而非analysis_results


@pytest.mark.unit
@pytest.mark.skip(reason="create_initial_state不接受metadata参数，元数据由metadata字段管理")
def test_state_manager_create_initial_state_with_metadata():
    """测试创建包含元数据的初始状态"""
    pass


@pytest.mark.unit
def test_state_manager_update_stage():
    """测试更新分析阶段"""
    initial_state = StateManager.create_initial_state(session_id="test-session", user_input="测试")

    update_dict = StateManager.update_stage(initial_state, AnalysisStage.REQUIREMENT_COLLECTION)

    # update_stage返回Dict更新，需要手动合并
    assert update_dict["current_stage"] == AnalysisStage.REQUIREMENT_COLLECTION.value
    assert "updated_at" in update_dict


@pytest.mark.unit
@pytest.mark.skip(reason="add_agent_result不直接更新agent_results，只更新completed_agents")
def test_state_manager_add_analysis_result():
    """测试添加分析结果"""
    # add_agent_result实际不直接操作agent_results
    # agent_results由LangGraph的reducer自动合并
    pass


@pytest.mark.unit
@pytest.mark.skip(reason="add_agent_result不直接更新agent_results")
def test_state_manager_add_multiple_results():
    """测试添加多个分析结果"""
    pass


@pytest.mark.unit
def test_state_manager_is_complete():
    """测试判断状态是否完成"""
    state = StateManager.create_initial_state(session_id="test-session", user_input="测试")

    # 使用is_analysis_complete方法
    assert not StateManager.is_analysis_complete(state)

    # 添加完成状态
    state["current_stage"] = AnalysisStage.COMPLETED.value
    state["subagents"] = {"expert_v3": {}}
    state["completed_agents"] = ["expert_v3"]

    assert StateManager.is_analysis_complete(state)


@pytest.mark.unit
@pytest.mark.skip(reason="StateManager没有has_error方法，使用errors列表检查")
def test_state_manager_has_error():
    """测试判断状态是否有错误"""
    pass


@pytest.mark.unit
@pytest.mark.skip(reason="StateManager没有get_expert_count方法，使用get_analysis_progress")
def test_state_manager_get_expert_count():
    """测试获取专家数量"""
    pass


# ============================================================================
# 状态序列化测试
# ============================================================================


@pytest.mark.unit
def test_state_serialization():
    """测试状态可以序列化为JSON"""
    import json

    state = StateManager.create_initial_state(session_id="test-session", user_input="测试")

    # 移除不可序列化的对象（如Enum）
    serializable_state = {
        k: v.value if isinstance(v, AnalysisStage) else v for k, v in state.items() if not k.startswith("_")  # 排除私有字段
    }

    # 尝试序列化
    try:
        json_str = json.dumps(serializable_state, ensure_ascii=False)
        assert json_str is not None

        # 尝试反序列化
        restored_state = json.loads(json_str)
        assert restored_state["session_id"] == "test-session"
    except (TypeError, ValueError) as e:
        pytest.fail(f"状态序列化失败: {e}")


# ============================================================================
# 状态一致性测试
# ============================================================================


@pytest.mark.unit
@pytest.mark.skip(reason="需要使用LangGraph工作流来正确测试状态更新")
def test_state_consistency_after_multiple_updates():
    """测试多次更新后状态一致性"""
    # update_stage和add_agent_result返回Dict，需要LangGraph自动合并
    # 单元测试不能直接模拟这个过程
    pass


@pytest.mark.unit
def test_state_required_fields():
    """测试状态包含所有必需字段"""
    state = StateManager.create_initial_state(session_id="test-session", user_input="测试")

    required_fields = [
        "session_id",
        "user_input",
        "current_stage",
        "agent_results",  # agent_results而非analysis_results
        "created_at",
    ]

    for field in required_fields:
        assert field in state, f"缺少必需字段: {field}"


# ============================================================================
# 边界情况测试
# ============================================================================


@pytest.mark.unit
def test_state_manager_empty_user_input():
    """测试空用户输入"""
    state = StateManager.create_initial_state(session_id="test-session", user_input="")

    assert state["user_input"] == ""


@pytest.mark.unit
def test_state_manager_long_user_input():
    """测试超长用户输入"""
    long_input = "测试" * 1000  # 4000字符

    state = StateManager.create_initial_state(session_id="test-session", user_input=long_input)

    assert state["user_input"] == long_input


@pytest.mark.unit
def test_state_manager_special_characters_in_input():
    """测试特殊字符输入"""
    special_input = "测试\n\t特殊字符!@#$%^&*(){}[]<>?/\\|"

    state = StateManager.create_initial_state(session_id="test-session", user_input=special_input)

    assert state["user_input"] == special_input
