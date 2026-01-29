"""
测试 DeepSeek Reasoner 响应字段修复 (v7.215)

验证修复是否正确处理 reasoning_content 字段
"""

import asyncio
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intelligent_project_analyzer.services.ucppt_search_engine import DeepSeekAnalysisEngine


async def test_deepseek_reasoner_fix():
    """测试 DeepSeek Reasoner 响应字段修复"""
    print("=" * 60)
    print("测试 DeepSeek Reasoner 响应字段修复 (v7.215)")
    print("=" * 60)

    engine = DeepSeekAnalysisEngine()

    # 测试简单查询
    test_query = "简单测试"
    print(f"\n📝 测试查询: {test_query}")

    try:
        # 调用 _deepseek_call 方法
        print("\n🚀 调用 DeepSeek API...")
        result = await engine._deepseek_call(prompt=test_query, model="deepseek-reasoner", max_tokens=100)

        if result:
            print(f"✅ API调用成功")
            print(f"📊 响应长度: {len(result)} 字符")
            print(f"📄 响应内容预览: {result[:200]}...")

            # 验证内容非空
            if result.strip():
                print("✅ 响应内容非空")
            else:
                print("❌ 响应内容为空")
                return False

        else:
            print("❌ API调用失败，返回 None")
            return False

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("✅ 测试通过！DeepSeek Reasoner 响应字段修复成功")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_deepseek_reasoner_fix())
    sys.exit(0 if success else 1)
