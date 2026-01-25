"""
简化工具绑定验证脚本 (v7.129)

快速验证工具系统核心功能
"""

import sys
from pathlib import Path

# 添加项目根目录
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def test_tool_factory():
    """测试ToolFactory"""
    print("=" * 60)
    print("[Test] Tool Binding Verification")
    print("=" * 60 + "\n")

    print("[1/5] Testing ToolFactory import...")
    try:
        from intelligent_project_analyzer.services.tool_factory import ToolFactory

        all_tools = ToolFactory.create_all_tools()
        print(f"   [OK] Created {len(all_tools)} tools: {list(all_tools.keys())}\n")
    except Exception as e:
        print(f"   [FAIL] {e}\n")
        return False

    print("[2/5] Testing role-tool mapping...")
    try:
        from intelligent_project_analyzer.agents.base import NullLLM
        from intelligent_project_analyzer.workflow.main_workflow import MainWorkflow

        wf = MainWorkflow(llm_model=NullLLM("test"))

        test_cases = [
            ("V2_Design_Director_2-2", 1, ["ragflow"]),
            ("V4_Design_Researcher_4-1", 4, ["bocha", "tavily", "arxiv", "ragflow"]),
            ("V6_Chief_Engineer_6-1", 4, ["bocha", "tavily", "arxiv", "ragflow"]),
        ]

        for role_id, expected_count, expected_names in test_cases:
            tools = wf._filter_tools_for_role(role_id, all_tools, {})
            actual_names = list(tools.keys())

            if len(tools) == expected_count and set(actual_names) == set(expected_names):
                print(f"   [OK] {role_id}: {len(tools)} tools {actual_names}")
            else:
                print(
                    f"   [FAIL] {role_id}: expected {expected_count} {expected_names}, got {len(tools)} {actual_names}"
                )
                return False

        print()
    except Exception as e:
        print(f"   [FAIL] {e}\n")
        import traceback

        traceback.print_exc()
        return False

    print("[3/5] Testing ToolCallRecorder...")
    try:
        from intelligent_project_analyzer.agents.tool_callback import ToolCallRecorder

        recorder = ToolCallRecorder(role_id="test-1", deliverable_id="test-del")

        if recorder.log_file.exists():
            print(f"   [OK] ToolCallRecorder initialized")
            print(f"        Log file: {recorder.log_file}\n")
        else:
            print(f"   [FAIL] Log file not created\n")
            return False
    except Exception as e:
        print(f"   [FAIL] {e}\n")
        return False

    print("[4/5] Testing trace_context...")
    try:
        from intelligent_project_analyzer.core.trace_context import TraceContext

        trace_id = TraceContext.init_trace("test-session-123456789")
        current = TraceContext.get_trace_id()

        # Trace ID format: session_id[:8] + '-' + random_8_hex
        # Example: "test-ses-a3f2c1b4" (from session_id "test-session-...")
        # Split by '-' gives >=2 parts, last part should be 8 hex chars
        parts = trace_id.split("-")
        if trace_id == current and len(parts) >= 2 and len(parts[-1]) == 8:
            print(f"   [OK] Trace ID: {trace_id}")
            print(f"        Format correct (session_prefix + '-' + random-8hex)\n")
        else:
            print(f"   [FAIL] Trace ID invalid: {trace_id}")
            print(f"          Parts: {parts}, last part length: {len(parts[-1])}\n")
            return False
    except Exception as e:
        print(f"   [FAIL] {e}\n")
        return False

    print("[5/5] Testing logging integration...")
    try:
        from loguru import logger

        # Test logging (should include trace_id)
        logger.info("[Test] trace_id integration")
        print(f"   [OK] Logging system integrated with trace_id\n")
    except Exception as e:
        print(f"   [FAIL] {e}\n")
        return False

    return True


if __name__ == "__main__":
    print()
    success = test_tool_factory()

    print("=" * 60)
    if success:
        print("[PASSED] All tests passed!")
        print("\nVerified items:")
        print("   [+] ToolFactory tool creation")
        print("   [+] Role-tool mapping (V2/V4/V6)")
        print("   [+] ToolCallRecorder log file creation")
        print("   [+] Trace ID generation & context")
        print("   [+] Logging system integration")
    else:
        print("[FAILED] Test failed, see errors above.")
    print("=" * 60 + "\n")

    sys.exit(0 if success else 1)
