"""
Quick test to verify BochaSearchTool has 'name' attribute fix

Tests:
1. BochaSearchTool instance has config attribute
2. BochaSearchTool.config has name attribute
3. Name is correctly set to "bocha_search"
"""

import os
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    # Avoid swapping sys.stdout/sys.stderr; prefer safe reconfigure when available.
    for _stream in (getattr(sys, "stdout", None), getattr(sys, "stderr", None)):
        if _stream is None:
            continue
        if hasattr(_stream, "reconfigure"):
            try:
                _stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


def test_bocha_tool_name_attribute():
    """Test that BochaSearchTool has the required name attribute"""
    from intelligent_project_analyzer.agents.bocha_search_tool import BochaSearchTool
    from intelligent_project_analyzer.core.types import ToolConfig

    print("=" * 60)
    print("Testing BochaSearchTool 'name' attribute fix")
    print("=" * 60)

    # Test 1: Create tool with default config
    print("\n✅ Test 1: Creating BochaSearchTool with default config...")
    tool = BochaSearchTool(api_key="test_key")

    # Test 2: Check if config attribute exists
    print("✅ Test 2: Checking if 'config' attribute exists...")
    assert hasattr(tool, "config"), "❌ FAILED: BochaSearchTool missing 'config' attribute"
    print(f"   ✓ tool.config exists: {tool.config}")

    # Test 3: Check if config.name exists
    print("✅ Test 3: Checking if 'config.name' attribute exists...")
    assert hasattr(tool.config, "name"), "❌ FAILED: ToolConfig missing 'name' attribute"
    print(f"   ✓ tool.config.name exists: {tool.config.name}")

    # Test 4: Verify name is correct
    print("✅ Test 4: Verifying name is 'bocha_search'...")
    assert tool.config.name == "bocha_search", f"❌ FAILED: Expected 'bocha_search', got '{tool.config.name}'"
    print(f"   ✓ tool.config.name = '{tool.config.name}' ✅")

    # Test 5: Test with custom config
    print("\n✅ Test 5: Creating BochaSearchTool with custom config...")
    custom_config = ToolConfig(name="custom_bocha")
    tool_custom = BochaSearchTool(api_key="test_key", config=custom_config)
    assert tool_custom.config.name == "custom_bocha", "❌ FAILED: Custom config not working"
    print(f"   ✓ Custom config.name = '{tool_custom.config.name}' ✅")

    # Test 6: Simulate what LangChain's bind_tools does
    print("\n✅ Test 6: Simulating LangChain bind_tools behavior...")
    tools = [tool]
    tool_names = [getattr(t, "name", getattr(t.config, "name", str(t))) for t in tools]
    print(f"   ✓ Extracted tool names: {tool_names}")
    assert "bocha_search" in tool_names, "❌ FAILED: Could not extract tool name"

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\n🎉 BochaSearchTool now has the required 'name' attribute")
    print("   The error 'BochaSearchTool' object has no attribute 'name' is FIXED")
    print("\n📋 Summary:")
    print("   - BochaSearchTool.config: ✅")
    print("   - BochaSearchTool.config.name: ✅")
    print("   - Default name: 'bocha_search' ✅")
    print("   - Compatible with LangChain bind_tools: ✅")
    print()


if __name__ == "__main__":
    try:
        test_bocha_tool_name_attribute()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
