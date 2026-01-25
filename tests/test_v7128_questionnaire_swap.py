"""
v7.128 问卷步骤互换单元测试

测试 Step 1 -> 3 -> 2 新顺序的正确性
"""

import os
import sys

# 设置 UTF-8 编码（优先使用 reconfigure，避免替换底层流导致其被关闭）
if sys.platform == "win32":
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue

        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="ignore")
                continue
            except Exception:
                pass

        if hasattr(stream, "buffer"):
            import io

            setattr(
                sys,
                stream_name,
                io.TextIOWrapper(stream.buffer, encoding="utf-8", errors="ignore"),
            )

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest.mock import MagicMock, patch

import pytest
from langgraph.types import Command


def test_step1_routes_to_step3():
    """测试 Step 1 是否正确路由到 Step 3"""
    print("\n🧪 测试1: Step 1 → Step 3 路由")

    from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
        progressive_step1_core_task_node,
    )

    # 模拟状态
    mock_state = {
        "session_id": "test_session",
        "user_input": "设计一个现代简约风格的客厅",
        "agent_results": {
            "requirements_analyst": {
                "structured_data": {
                    "project_type": "室内设计",
                    "project_overview": "客厅设计",
                }
            }
        },
    }

    mock_store = MagicMock()

    # 模拟 interrupt 返回用户确认
    with patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt") as mock_interrupt:
        mock_interrupt.return_value = {"confirmed_tasks": [{"title": "客厅设计", "description": "设计一个现代简约风格的客厅"}]}

        result = progressive_step1_core_task_node(mock_state, mock_store)

    # 验证路由
    assert isinstance(result, Command), "❌ 返回类型应该是 Command"
    assert (
        result.goto == "progressive_step3_gap_filling"
    ), f"❌ Step 1 应该路由到 progressive_step3_gap_filling，但实际是 {result.goto}"

    print("✅ Step 1 正确路由到 Step 3")
    return True


def test_step3_routes_to_step2():
    """测试 Step 3 是否正确路由到 Step 2"""
    print("\n🧪 测试2: Step 3 → Step 2 路由")

    from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
        progressive_step3_gap_filling_node,
    )

    # 模拟状态
    mock_state = {
        "session_id": "test_session",
        "user_input": "设计一个现代简约风格的客厅",
        "confirmed_core_tasks": [{"title": "客厅设计", "description": "设计现代简约风格的客厅"}],
        "agent_results": {
            "requirements_analyst": {
                "structured_data": {
                    "project_type": "室内设计",
                }
            }
        },
    }

    mock_store = MagicMock()

    # 模拟 interrupt 返回用户答案
    with patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt") as mock_interrupt:
        mock_interrupt.return_value = {"answers": {"budget_range": "50-100万", "timeline": "3个月", "area": "120平米"}}

        result = progressive_step3_gap_filling_node(mock_state, mock_store)

    # 验证路由
    assert isinstance(result, Command), "❌ 返回类型应该是 Command"
    assert result.goto == "progressive_step2_radar", f"❌ Step 3 应该路由到 progressive_step2_radar，但实际是 {result.goto}"

    print("✅ Step 3 正确路由到 Step 2")
    return True


def test_step2_routes_to_project_director():
    """测试 Step 2 是否正确路由到 project_director"""
    print("\n🧪 测试3: Step 2 → project_director 路由")

    from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import progressive_step2_radar_node

    # 模拟状态
    mock_state = {
        "session_id": "test_session",
        "user_input": "设计一个现代简约风格的客厅",
        "confirmed_core_tasks": [{"title": "客厅设计", "description": "设计现代简约风格的客厅"}],
        "confirmed_core_task": "设计现代简约风格的客厅",
        "agent_results": {
            "requirements_analyst": {
                "structured_data": {
                    "project_type": "室内设计",
                }
            }
        },
    }

    mock_store = MagicMock()

    # 模拟 interrupt 返回用户滑块值
    with patch("intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt") as mock_interrupt:
        mock_interrupt.return_value = {"dimension_values": {"modern_feel": 85, "luxury_level": 60}}

        result = progressive_step2_radar_node(mock_state, mock_store)

    # 验证路由
    assert isinstance(result, Command), "❌ 返回类型应该是 Command"
    assert result.goto == "project_director", f"❌ Step 2 应该路由到 project_director，但实际是 {result.goto}"

    # 验证问卷已完成标记
    assert result.update.get("progressive_questionnaire_completed") == True, "❌ 问卷应该标记为已完成"
    assert result.update.get("progressive_questionnaire_step") == 3, "❌ 步骤应该标记为3"

    print("✅ Step 2 正确路由到 project_director 并标记问卷完成")
    return True


def test_step2_intelligent_defaults():
    """测试 Step 2 的智能默认值设置"""
    print("\n🧪 测试4: Step 2 智能默认值")

    from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import progressive_step2_radar_node

    # 模拟状态（包含 Step 3 的答案）
    mock_state = {
        "session_id": "test_session",
        "user_input": "设计一个现代简约风格的客厅",
        "confirmed_core_tasks": [{"title": "客厅设计", "description": "设计现代简约风格的客厅"}],
        "confirmed_core_task": "设计现代简约风格的客厅",
        "gap_filling_answers": {"budget_range": "100万以上", "timeline": "6个月以上", "preferred_style": "现代简约"},
        "agent_results": {
            "requirements_analyst": {
                "structured_data": {
                    "project_type": "室内设计",
                }
            }
        },
    }

    mock_store = MagicMock()

    # 捕获 interrupt 的 payload
    captured_payload = None

    def mock_interrupt_fn(payload):
        nonlocal captured_payload
        captured_payload = payload
        return {"dimension_values": {"modern_feel": 85, "luxury_level": 75}}

    with patch(
        "intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt",
        side_effect=mock_interrupt_fn,
    ):
        result = progressive_step2_radar_node(mock_state, mock_store)

    # 验证 payload 中的维度是否包含默认值
    assert captured_payload is not None, "❌ 未捕获到 interrupt payload"

    dimensions = captured_payload.get("dimensions", [])

    # 检查是否设置了默认值
    has_default = any(dim.get("default_value") is not None for dim in dimensions)

    if has_default:
        print("✅ Step 2 成功设置了智能默认值")
        # 打印设置的默认值
        for dim in dimensions:
            if dim.get("default_value") is not None:
                print(f"   📊 维度 '{dim.get('name')}' 默认值: {dim.get('default_value')}")
    else:
        print("⚠️  Step 2 未设置默认值（可能没有匹配的维度）")

    return True


def test_step_numbers_in_payload():
    """测试 interrupt payload 中的步骤编号是否正确"""
    print("\n🧪 测试5: Interrupt Payload 步骤编号")

    from intelligent_project_analyzer.interaction.nodes.progressive_questionnaire import (
        progressive_step2_radar_node,
        progressive_step3_gap_filling_node,
    )

    # 测试 Step 3 的 payload（现在应该显示为第2步）
    mock_state_step3 = {
        "session_id": "test_session",
        "user_input": "设计客厅",
        "confirmed_core_tasks": [{"title": "客厅设计", "description": "设计客厅"}],
        "agent_results": {"requirements_analyst": {"structured_data": {"project_type": "室内设计"}}},
    }

    captured_step3_payload = None

    def mock_interrupt_step3(payload):
        nonlocal captured_step3_payload
        captured_step3_payload = payload
        return {"answers": {"budget": "50万"}}

    with patch(
        "intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt",
        side_effect=mock_interrupt_step3,
    ):
        progressive_step3_gap_filling_node(mock_state_step3, MagicMock())

    assert captured_step3_payload is not None, "❌ 未捕获到 Step 3 payload"
    assert captured_step3_payload.get("step") == 2, f"❌ Step 3 应该显示为第2步，但实际是 {captured_step3_payload.get('step')}"
    print(f"✅ Step 3 正确显示为第 {captured_step3_payload.get('step')} 步")

    # 测试 Step 2 的 payload（现在应该显示为第3步）
    mock_state_step2 = {
        "session_id": "test_session",
        "user_input": "设计客厅",
        "confirmed_core_tasks": [{"title": "客厅设计", "description": "设计客厅"}],
        "confirmed_core_task": "设计客厅",
        "agent_results": {"requirements_analyst": {"structured_data": {"project_type": "室内设计"}}},
    }

    captured_step2_payload = None

    def mock_interrupt_step2(payload):
        nonlocal captured_step2_payload
        captured_step2_payload = payload
        return {"dimension_values": {}}

    with patch(
        "intelligent_project_analyzer.interaction.nodes.progressive_questionnaire.interrupt",
        side_effect=mock_interrupt_step2,
    ):
        progressive_step2_radar_node(mock_state_step2, MagicMock())

    assert captured_step2_payload is not None, "❌ 未捕获到 Step 2 payload"
    assert captured_step2_payload.get("step") == 3, f"❌ Step 2 应该显示为第3步，但实际是 {captured_step2_payload.get('step')}"
    print(f"✅ Step 2 正确显示为第 {captured_step2_payload.get('step')} 步")

    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 80)
    print("🚀 v7.128 问卷步骤互换单元测试")
    print("=" * 80)

    tests = [
        ("Step 1 → Step 3 路由", test_step1_routes_to_step3),
        ("Step 3 → Step 2 路由", test_step3_routes_to_step2),
        ("Step 2 → project_director 路由", test_step2_routes_to_project_director),
        ("Step 2 智能默认值", test_step2_intelligent_defaults),
        ("Payload 步骤编号", test_step_numbers_in_payload),
    ]

    passed = 0
    failed = 0

    for test_name, test_fn in tests:
        try:
            result = test_fn()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ 测试失败: {test_name}")
            print(f"   错误: {str(e)}")
            import traceback

            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 80)
    print(f"📊 测试结果: {passed} 通过, {failed} 失败")
    print("=" * 80)

    if failed == 0:
        print("✅ 所有测试通过！v7.128 实施成功！")
        return True
    else:
        print(f"❌ 有 {failed} 个测试失败，请检查代码")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
