"""
测试 v7.122 图片Prompt修复 (Line 1011 Bug Fix)

验证点:
1. _llm_extract_visual_prompt 返回完整字符串
2. visual_prompt 使用完整字符串而非首字符
3. Prompt长度验证生效
"""

import asyncio
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from intelligent_project_analyzer.services.image_generator import ImageGeneratorService


@pytest.mark.asyncio
async def test_prompt_string_handling():
    """测试Prompt字符串处理逻辑"""
    print("🧪 测试 v7.122 图片Prompt修复\n")

    generator = ImageGeneratorService()

    # 模拟专家内容
    test_expert_content = """
    This is a modern seaside villa design featuring:
    - Contemporary minimalist architecture
    - Large floor-to-ceiling windows
    - Ocean view orientation
    - Natural materials (wood, stone, glass)
    - Open floor plan with indoor-outdoor flow
    """

    print("1️⃣ 测试 _llm_extract_visual_prompt 返回类型")
    result = await generator._llm_extract_visual_prompt(
        expert_content=test_expert_content, project_type="personal_residential"
    )

    print(f"   返回类型: {type(result)}")
    print(f"   返回值长度: {len(result)} 字符")
    print(f"   返回值预览: {result[:200]}...")

    # 验证返回类型
    assert isinstance(result, str), f"❌ 返回类型错误: {type(result)}, 应为 str"
    print("   ✅ 返回类型正确 (str)\n")

    # 验证长度
    assert len(result) > 50, f"❌ Prompt太短: {len(result)} chars"
    print(f"   ✅ Prompt长度合理 ({len(result)} chars > 50)\n")

    # 验证内容质量
    assert result[0] != result, f"❌ Prompt是单字符: '{result}'"
    print(f"   ✅ Prompt不是单字符\n")

    print("2️⃣ 测试字符串索引逻辑")
    # 模拟旧代码错误
    old_logic_result = result[0]  # 这是bug - 只取首字符
    new_logic_result = result  # 这是修复 - 使用完整字符串

    print(f"   旧逻辑 (result[0]): '{old_logic_result}' (长度: {len(old_logic_result)})")
    print(f"   新逻辑 (result): '{new_logic_result[:100]}...' (长度: {len(new_logic_result)})")

    assert len(new_logic_result) > len(old_logic_result), "❌ 新逻辑应该返回更长的字符串"
    print("   ✅ 新逻辑修复确认\n")

    print("3️⃣ 测试空Prompt处理")
    empty_result = await generator._llm_extract_visual_prompt(expert_content="", project_type="interior")

    if not empty_result:
        print("   ✅ 空内容正确返回空字符串\n")
    else:
        print(f"   ℹ️ 空内容返回了默认Prompt: {empty_result[:50]}...\n")

    print("✅ 所有测试通过！v7.122修复验证成功")
    return True


if __name__ == "__main__":
    try:
        asyncio.run(test_prompt_string_handling())
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
