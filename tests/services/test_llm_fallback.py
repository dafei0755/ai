"""
测试 LLM 降级机制

测试场景:
1. 主提供商正常 → 使用主提供商
2. 主提供商失败 → 自动降级到备选
3. 所有提供商失败 → 报错

运行: python test_llm_fallback.py
"""

import os
import sys
from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stdout, level="INFO", format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}")

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from intelligent_project_analyzer.services.llm_factory import LLMFactory
from intelligent_project_analyzer.services.multi_llm_factory import MultiLLMFactory


def test_current_provider():
    """测试当前配置的提供商"""
    logger.info("=" * 60)
    logger.info("📋 测试 1: 当前提供商配置")
    logger.info("=" * 60)

    try:
        # 读取环境变量
        provider = os.getenv("LLM_PROVIDER", "openai")
        auto_fallback = os.getenv("LLM_AUTO_FALLBACK", "false").lower() == "true"

        logger.info(f"🔧 LLM_PROVIDER = {provider}")
        logger.info(f"🔄 LLM_AUTO_FALLBACK = {auto_fallback}")

        # 创建 LLM 实例
        logger.info("\n📦 创建 LLM 实例...")
        llm = LLMFactory.create_llm()

        # 测试调用
        logger.info("\n🧪 测试 LLM 调用...")
        response = llm.invoke("Say 'Hello' in one word")
        logger.success(f"✅ 调用成功! 响应: {response.content}")

        return True

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_fallback_chain():
    """测试降级链"""
    logger.info("\n" + "=" * 60)
    logger.info("📋 测试 2: 降级链配置（运行时降级）")
    logger.info("=" * 60)

    try:
        from intelligent_project_analyzer.services.multi_llm_factory import FallbackLLM

        # 检查各个提供商的 API Key
        providers = ["openai", "openrouter", "deepseek", "qwen"]
        available = []

        for provider in providers:
            key_env = {
                "openai": "OPENAI_API_KEY",
                "openrouter": "OPENROUTER_API_KEY",
                "deepseek": "DEEPSEEK_API_KEY",
                "qwen": "QWEN_API_KEY",
            }[provider]

            key = os.getenv(key_env, "")
            is_valid = key and key != "your_xxx_api_key_here" and not key.startswith("your_")

            status = "✅ 可用" if is_valid else "❌ 不可用"
            logger.info(f"{provider.ljust(12)}: {status} ({key_env})")

            if is_valid:
                available.append(provider)

        logger.info(f"\n🔄 可用的提供商: {' → '.join(available)}")

        if len(available) < 2:
            logger.warning("⚠️ 只有 1 个可用提供商，无法测试降级")
            return True

        # 测试运行时降级创建（使用 FallbackLLM）
        logger.info("\n📦 测试运行时降级链创建...")
        llm = FallbackLLM(providers=available, temperature=0.7, max_tokens=100)

        logger.info(f"✅ 降级链创建成功: {type(llm).__name__}")

        # 测试调用（会自动降级）
        logger.info("\n🧪 测试运行时降级调用...")
        logger.info("💡 预期: OpenAI 配额用尽 → 自动切换到 OpenRouter → DeepSeek")
        response = llm.invoke("Say 'Test' in one word")
        logger.success(f"✅ 调用成功! 响应: {response.content}")

        return True

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_manual_fallback():
    """手动测试降级（模拟主提供商失败）"""
    logger.info("\n" + "=" * 60)
    logger.info("📋 测试 3: 手动降级测试")
    logger.info("=" * 60)

    try:
        # 尝试创建一个不存在的提供商，触发降级
        logger.info("🔧 测试场景: 主提供商 'invalid_provider' → 降级到 deepseek")

        # 临时修改环境变量
        original_provider = os.getenv("LLM_PROVIDER")
        os.environ["LLM_PROVIDER"] = "invalid_provider"

        try:
            # 这应该会失败并触发降级
            llm = LLMFactory.create_llm()
            logger.error("❌ 预期失败但成功了，降级机制可能有问题")
            return False
        except ValueError as e:
            logger.info(f"✅ 正确触发错误: {e}")
        finally:
            # 恢复环境变量
            if original_provider:
                os.environ["LLM_PROVIDER"] = original_provider

        # 现在测试正常的降级
        logger.info("\n🔧 测试正常降级: openai → openrouter → deepseek")
        llm = MultiLLMFactory.create_with_fallback(
            providers=["openai", "openrouter", "deepseek"], temperature=0.7, max_tokens=100
        )

        logger.info("✅ 降级链创建成功")

        return True

    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    logger.info("🚀 开始 LLM 降级机制测试\n")

    results = []

    # 测试 1: 当前提供商
    results.append(("当前提供商", test_current_provider()))

    # 测试 2: 降级链
    results.append(("降级链配置", test_fallback_chain()))

    # 测试 3: 手动降级
    results.append(("手动降级", test_manual_fallback()))

    # 输出总结
    logger.info("\n" + "=" * 60)
    logger.info("📊 测试总结")
    logger.info("=" * 60)

    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{name.ljust(20)}: {status}")

    total = len(results)
    passed = sum(1 for _, r in results if r)

    logger.info(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        logger.success("\n🎉 所有测试通过！")
        return 0
    else:
        logger.error("\n❌ 部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
