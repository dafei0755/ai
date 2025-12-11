"""
检查当前 LLM 配置

运行: python check_llm_config.py
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# 加载 .env
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

print("=" * 60)
print("🔍 当前 LLM 配置")
print("=" * 60)

# 主要配置
provider = os.getenv("LLM_PROVIDER", "openai")
print(f"\n📌 当前提供商: {provider.upper()}")

# 根据提供商显示模型
if provider == "openai":
    model = os.getenv("OPENAI_MODEL", "gpt-4.1")
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    print(f"📦 模型: {model}")
    print(f"🔑 API Key: {api_key[:20]}...{api_key[-10:] if len(api_key) > 30 else ''}")
    print(f"🌐 Base URL: {base_url}")

elif provider == "deepseek":
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    print(f"📦 模型: {model}")
    print(f"🔑 API Key: {api_key[:20]}...{api_key[-10:] if len(api_key) > 30 else ''}")
    print(f"🌐 Base URL: {base_url}")

elif provider == "qwen":
    model = os.getenv("QWEN_MODEL", "qwen-max")
    api_key = os.getenv("QWEN_API_KEY", "")
    base_url = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    print(f"📦 模型: {model}")
    print(f"🔑 API Key: {api_key[:20]}...{api_key[-10:] if len(api_key) > 30 else ''}")
    print(f"🌐 Base URL: {base_url}")

elif provider == "anthropic":
    model = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    print(f"📦 模型: {model}")
    print(f"🔑 API Key: {api_key[:20]}...{api_key[-10:] if len(api_key) > 30 else ''}")

elif provider == "azure":
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    version = os.getenv("AZURE_API_VERSION", "2024-02-15-preview")
    print(f"📦 部署名称: {deployment}")
    print(f"🔑 API Key: {api_key[:20]}...{api_key[-10:] if len(api_key) > 30 else ''}")
    print(f"🌐 Endpoint: {endpoint}")
    print(f"📋 API Version: {version}")

# 通用参数
print(f"\n⚙️ 通用参数:")
print(f"   Max Tokens: {os.getenv('MAX_TOKENS', '32000')}")
print(f"   Temperature: {os.getenv('TEMPERATURE', '0.7')}")
print(f"   Timeout: {os.getenv('LLM_TIMEOUT', '600')}s")
print(f"   Max Retries: {os.getenv('MAX_RETRIES', '3')}")

# 自动降级
auto_fallback = os.getenv("LLM_AUTO_FALLBACK", "true").lower() == "true"
print(f"\n🔄 自动降级: {'✅ 启用' if auto_fallback else '❌ 禁用'}")
if auto_fallback:
    print(f"   策略: {provider.upper()} → Qwen → DeepSeek")

print("\n" + "=" * 60)
