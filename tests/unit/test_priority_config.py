"""
验证优先级配置：OpenAI 官方 → OpenRouter → DeepSeek
"""
import os
from dotenv import load_dotenv

load_dotenv()


def check_priority_config():
    """检查优先级配置"""
    print("=" * 70)
    print("🔧 LLM 提供商优先级配置检查")
    print("=" * 70)

    # 获取配置
    provider = os.getenv("LLM_PROVIDER", "openai")
    auto_fallback = os.getenv("LLM_AUTO_FALLBACK", "false").lower() == "true"

    print(f"\n📋 当前配置:")
    print(f"  主提供商: {provider.upper()}")
    print(f"  自动降级: {'✅ 启用' if auto_fallback else '❌ 禁用'}")

    # 检查各提供商 API Key 状态
    providers_status = {
        "OpenAI 官方": {
            "key_env": "OPENAI_API_KEY",
            "key": os.getenv("OPENAI_API_KEY"),
            "model": os.getenv("OPENAI_MODEL", "gpt-4.1"),
        },
        "OpenRouter": {
            "key_env": "OPENROUTER_API_KEY",
            "key": os.getenv("OPENROUTER_API_KEY"),
            "model": os.getenv("OPENROUTER_MODEL", "openai/gpt-4o"),
        },
        "DeepSeek": {
            "key_env": "DEEPSEEK_API_KEY",
            "key": os.getenv("DEEPSEEK_API_KEY"),
            "model": os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        },
        "Qwen": {
            "key_env": "QWEN_API_KEY",
            "key": os.getenv("QWEN_API_KEY"),
            "model": os.getenv("QWEN_MODEL", "qwen-max"),
        },
    }

    print(f"\n📊 提供商状态:")
    for name, info in providers_status.items():
        key = info["key"]
        is_valid = key and key not in [
            "your_openai_api_key_here",
            "your_openrouter_api_key_here",
            "your_deepseek_api_key_here",
            "your_qwen_api_key_here",
        ]
        status = "✅ 已配置" if is_valid else "❌ 未配置"

        if is_valid:
            key_display = f"{key[:20]}...{key[-10:]}" if len(key) > 30 else key[:30]
            print(f"  {name:15} {status:10} | Key: {key_display} | Model: {info['model']}")
        else:
            print(f"  {name:15} {status:10}")

    # 显示降级策略
    print(f"\n🔄 降级策略:")
    if not auto_fallback:
        print(f"  ⚠️ 自动降级已禁用，仅使用主提供商：{provider.upper()}")
    else:
        if provider == "openai":
            chain = ["OpenAI 官方"]
            if (
                providers_status["OpenRouter"]["key"]
                and providers_status["OpenRouter"]["key"] != "your_openrouter_api_key_here"
            ):
                chain.append("OpenRouter (GPT)")
            if (
                providers_status["DeepSeek"]["key"]
                and providers_status["DeepSeek"]["key"] != "your_deepseek_api_key_here"
            ):
                chain.append("DeepSeek")

            print(f"  ✅ {' → '.join(chain)}")

            if len(chain) == 1:
                print(f"  ⚠️ 没有可用的备选提供商，建议配置 OpenRouter 或 DeepSeek")
            elif "OpenRouter (GPT)" in chain and "DeepSeek" in chain:
                print(f"  🏆 完美配置！三层降级保障最高可用性")
            else:
                print(f"  ✅ 可用，但建议配置所有三个提供商以获得最佳可用性")
        else:
            print(f"  ℹ️ 主提供商是 {provider.upper()}，降级链已自动生成")
    # 推荐配置
    print(f"\n💡 推荐配置:")
    print(f"  1. LLM_PROVIDER=openai")
    print(f"  2. LLM_AUTO_FALLBACK=true")
    print(f"  3. 配置三个 API Key:")
    print(f"     - OPENAI_API_KEY (官方，高质量但国内可能受限)")
    print(f"     - OPENROUTER_API_KEY (国内可用，价格同官方)")
    print(f"     - DEEPSEEK_API_KEY (国内最快，成本最低)")

    return provider, auto_fallback, providers_status


def test_fallback_chain():
    """测试降级链"""
    print(f"\n" + "=" * 70)
    print("🧪 测试降级链")
    print("=" * 70)

    try:
        from intelligent_project_analyzer.services.llm_factory import LLMFactory

        print(f"\n🔧 创建 LLM 实例（会自动应用降级链）...")
        llm = LLMFactory.create_llm(temperature=0.7, max_tokens=500)

        print(f"✅ LLM 实例创建成功！")

        # 尝试调用
        print(f"\n📡 测试调用...")
        response = llm.invoke("用一句话说明当前使用的是哪个 LLM 提供商。")

        print(f"\n✅ 调用成功！")
        print(f"💬 响应内容:")
        print(f"  {response.content}")

        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        print(f"\n可能的原因:")
        print(f"  1. 主提供商 API Key 无效")
        print(f"  2. 所有备选提供商都不可用")
        print(f"  3. 网络连接问题")
        return False


def show_quick_fix():
    """显示快速修复指南"""
    print(f"\n" + "=" * 70)
    print("🔧 快速修复指南")
    print("=" * 70)

    provider = os.getenv("LLM_PROVIDER", "openai")

    if provider == "openai":
        openai_key = os.getenv("OPENAI_API_KEY")
        openrouter_key = os.getenv("OPENROUTER_API_KEY")

        if not openai_key or openai_key.startswith("your_"):
            print(f"\n⚠️ OpenAI 官方 API Key 未配置")
            print(f"   如果你在国内且无法访问 OpenAI，建议改用 OpenRouter：")
            print(f"   1. 修改 .env: LLM_PROVIDER=openrouter")
            print(f"   2. 确保已配置: OPENROUTER_API_KEY=sk-or-v1-...")

        if not openrouter_key or openrouter_key.startswith("your_"):
            print(f"\n💡 建议配置 OpenRouter 作为备选:")
            print(f"   1. 访问 https://openrouter.ai/keys 获取 API Key")
            print(f"   2. 修改 .env: OPENROUTER_API_KEY=sk-or-v1-...")
            print(f"   3. 已为你配置: OPENROUTER_MODEL=openai/gpt-4o")
        else:
            print(f"\n✅ OpenRouter 已配置，降级链完整！")
            print(f"   当 OpenAI 官方 API 不可用时，会自动切换到 OpenRouter")


if __name__ == "__main__":
    print("\n🚀 LLM 优先级配置验证工具")
    print("   目标配置: OpenAI 官方 → OpenRouter (GPT) → DeepSeek")

    # 1. 检查配置
    provider, auto_fallback, providers = check_priority_config()

    # 2. 测试降级链
    if auto_fallback:
        success = test_fallback_chain()
    else:
        print(f"\n⚠️ 自动降级未启用，跳过降级链测试")
        print(f"   建议修改 .env: LLM_AUTO_FALLBACK=true")
        success = False

    # 3. 显示修复建议
    show_quick_fix()

    print(f"\n" + "=" * 70)
    if success:
        print("✅ 配置验证通过！降级链正常工作")
    else:
        print("⚠️ 配置需要调整，请参考上述建议")
    print("=" * 70)
