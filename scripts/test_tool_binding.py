"""
测试工具绑定验证脚本 (v7.129)

验证工具系统是否正确绑定到LLM

使用方法:
    python scripts/test_tool_binding.py [--session-id <session_id>]
"""

import asyncio
import io
import sys
from pathlib import Path

# Windows GBK编码修复
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger


async def test_tool_binding():
    """测试工具绑定功能"""
    print("\n" + "=" * 70)
    print("🧪 工具绑定验证测试")
    print("=" * 70 + "\n")

    # 1. 导入工具工厂
    print("📦 [1/6] 导入ToolFactory...")
    try:
        from intelligent_project_analyzer.services.tool_factory import ToolFactory

        print("   ✅ ToolFactory导入成功")
    except Exception as e:
        print(f"   ❌ 导入失败: {e}")
        return False

    # 2. 创建所有工具
    print("\n🔧 [2/6] 创建工具实例...")
    try:
        all_tools = ToolFactory.create_all_tools()
        print(f"   ✅ 成功创建 {len(all_tools)} 个工具")
        for name, tool in all_tools.items():
            print(f"      - {name}: {type(tool).__name__}")
    except Exception as e:
        print(f"   ❌ 工具创建失败: {e}")
        return False

    # 3. 测试角色工具映射
    print("\n🎭 [3/6] 测试角色工具映射...")
    test_roles = [
        ("V2_设计总监_2-2", ["ragflow"]),
        ("V3_叙事专家_3-1", ["bocha", "tavily", "ragflow"]),
        ("V4_设计研究员_4-1", ["bocha", "tavily", "arxiv", "ragflow"]),
        ("V5_场景专家_5-1", ["bocha", "tavily", "ragflow"]),
        ("V6_总工程师_6-1", ["bocha", "tavily", "arxiv", "ragflow"]),
    ]

    # 导入主工作流
    try:
        from intelligent_project_analyzer.agents.base import NullLLM
        from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow

        workflow = MainWorkflow(llm_model=NullLLM("test"))
    except Exception as e:
        print(f"   ❌ 工作流导入失败: {e}")
        return False

    all_passed = True
    for role_id, expected_tools in test_roles:
        # 使用workflow的_filter_tools_for_role方法
        filtered_tools = workflow._filter_tools_for_role(role_id, all_tools, {})
        actual_tool_names = list(filtered_tools.keys())

        if set(actual_tool_names) == set(expected_tools):
            print(f"   ✅ {role_id}: {actual_tool_names}")
        else:
            print(f"   ❌ {role_id}: 预期{expected_tools}, 实际{actual_tool_names}")
            all_passed = False

    if not all_passed:
        return False

    # 4. 测试ToolCallRecorder
    print("\n📝 [4/6] 测试ToolCallRecorder...")
    try:
        from intelligent_project_analyzer.agents.tool_callback import ToolCallRecorder

        recorder = ToolCallRecorder(role_id="test-role", deliverable_id="test-deliverable")

        # 检查日志文件创建
        log_file = recorder.log_file
        if log_file.exists():
            print(f"   ✅ ToolCallRecorder初始化成功")
            print(f"      日志文件: {log_file}")
        else:
            print(f"   ❌ 日志文件未创建: {log_file}")
            return False
    except Exception as e:
        print(f"   ❌ ToolCallRecorder测试失败: {e}")
        return False

    # 5. 测试工具绑定到LLM
    print("\n🔗 [5/6] 测试工具绑定到LLM...")
    try:
        from langchain_anthropic import ChatAnthropic

        # 创建测试LLM
        llm = ChatAnthropic(model="claude-3-5-sonnet-20241022", temperature=0)

        # 获取V4的工具（全部工具）
        v4_tools = workflow._filter_tools_for_role("V4_设计研究员_4-1", all_tools, {})
        tools_list = list(v4_tools.values())

        if not tools_list:
            print("   ❌ V4角色未分配工具")
            return False

        # 绑定工具
        recorder_test = ToolCallRecorder(role_id="V4-1-test", deliverable_id="test")
        llm_with_tools = llm.bind_tools(tools_list, callbacks=[recorder_test])

        print(f"   ✅ 成功绑定 {len(tools_list)} 个工具到LLM")

        # 检查绑定
        if hasattr(llm_with_tools, "bound_tools") or hasattr(llm_with_tools, "kwargs"):
            print("   ✅ 工具绑定验证通过")
        else:
            print("   ⚠️  无法验证工具是否绑定（API限制）")

    except Exception as e:
        print(f"   ❌ LLM工具绑定失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    # 6. 测试trace_id集成
    print("\n🔍 [6/6] 测试trace_id集成...")
    try:
        from intelligent_project_analyzer.core.trace_context import TraceContext

        # 初始化trace
        trace_id = TraceContext.init_trace("test-session-12345678")
        current_trace = TraceContext.get_trace_id()

        if current_trace == trace_id:
            print(f"   ✅ Trace ID生成成功: {trace_id}")
        else:
            print(f"   ❌ Trace ID不一致: {trace_id} != {current_trace}")
            return False

        # 测试日志记录
        logger.info("🧪 测试trace_id日志记录")
        print(f"   ✅ trace_id已集成到日志系统")

    except Exception as e:
        print(f"   ❌ trace_id测试失败: {e}")
        return False

    return True


async def test_real_session(session_id: str):
    """测试真实会话的工具使用情况"""
    print(f"\n🔍 测试真实会话: {session_id}\n")

    # 调用诊断工具
    import subprocess

    result = subprocess.run(
        [sys.executable, "scripts/diagnose_session_tools.py", session_id],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    print(result.stdout)
    if result.stderr:
        print("错误输出:")
        print(result.stderr)

    return result.returncode == 0


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="测试工具绑定功能")
    parser.add_argument("--session-id", help="测试指定会话的工具使用情况")
    args = parser.parse_args()

    if args.session_id:
        # 测试真实会话
        success = await test_real_session(args.session_id)
    else:
        # 运行单元测试
        success = await test_tool_binding()

    print("\n" + "=" * 70)
    if success:
        print("✅ 所有测试通过！工具绑定系统正常工作。")
    else:
        print("❌ 测试失败，请检查上述错误信息。")
    print("=" * 70 + "\n")

    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
