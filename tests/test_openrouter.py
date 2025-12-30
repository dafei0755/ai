"""
测试 OpenRouter 连接和配置
验证：
1. OpenRouter API Key 有效性
2. 模型名称格式是否正确
3. 与官方 OpenAI API 的响应对比
"""
import os
import sys
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def test_openrouter_config():
    """检查 OpenRouter 配置"""
    print("="*60)
    print("OpenRouter 配置检查")
    print("="*60)
    
    # 检查必需的环境变量
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL")
    base_url = os.getenv("OPENROUTER_BASE_URL")
    app_name = os.getenv("OPENROUTER_APP_NAME")
    site_url = os.getenv("OPENROUTER_SITE_URL")
    
    print(f"\n📋 配置信息:")
    print(f"  API Key: {api_key[:20]}...{api_key[-10:] if api_key and len(api_key) > 30 else 'NOT SET'}")
    print(f"  Model: {model}")
    print(f"  Base URL: {base_url}")
    print(f"  App Name: {app_name}")
    print(f"  Site URL: {site_url}")
    
    # 检查 API Key
    if not api_key or api_key == "your_openrouter_api_key_here":
        print(f"\n❌ OpenRouter API Key 未配置!")
        print(f"   请访问 https://openrouter.ai/keys 获取 API Key")
        print(f"   然后修改 .env 文件: OPENROUTER_API_KEY=sk-or-v1-...")
        return False
    
    # 检查模型名称格式
    if model and not "/" in model:
        print(f"\n⚠️ 警告: 模型名称格式可能不正确")
        print(f"   当前: {model}")
        print(f"   推荐: openai/gpt-4o (需要加提供商前缀)")
    
    print(f"\n✅ 配置检查完成!")
    return True

def test_openrouter_connection():
    """测试 OpenRouter 连接"""
    print("\n" + "="*60)
    print("OpenRouter 连接测试")
    print("="*60)
    
    try:
        from intelligent_project_analyzer.services.multi_llm_factory import MultiLLMFactory
        
        print(f"\n🔧 创建 OpenRouter LLM 实例...")
        llm = MultiLLMFactory.create_llm(
            provider="openrouter",
            temperature=0.7,
            max_tokens=500
        )
        
        print(f"✅ LLM 实例创建成功!")
        
        print(f"\n📡 发送测试请求...")
        response = llm.invoke("请用一句话介绍 OpenRouter 是什么。")
        
        print(f"\n✅ OpenRouter 响应成功!")
        print(f"\n💬 回复内容:")
        print(f"  {response.content}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ OpenRouter 连接失败: {e}")
        print(f"\n可能的原因:")
        print(f"  1. API Key 无效或余额不足")
        print(f"  2. 模型名称格式错误 (需要加前缀,如 openai/gpt-4o)")
        print(f"  3. 网络连接问题")
        print(f"\n解决方法:")
        print(f"  1. 访问 https://openrouter.ai/credits 检查余额")
        print(f"  2. 访问 https://openrouter.ai/models 查看可用模型")
        print(f"  3. 检查模型名称格式: OPENROUTER_MODEL=openai/gpt-4o")
        return False
def compare_with_official_api():
    """对比 OpenRouter 与官方 API"""
    print("\n" + "="*60)
    print("OpenRouter vs 官方 API 对比")
    print("="*60)
    
    # 检查是否有官方 OpenAI API Key
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key or openai_key.startswith("your_"):
        print(f"\n⚠️ 未配置官方 OpenAI API Key，跳过对比测试")
        return
    
    try:
        from intelligent_project_analyzer.services.multi_llm_factory import MultiLLMFactory
        import time
        
        test_prompt = "1+1等于几？只回答数字。"
        
        # 测试 OpenRouter
        print(f"\n🔵 测试 OpenRouter...")
        start_time = time.time()
        try:
            llm_or = MultiLLMFactory.create_llm(provider="openrouter", max_tokens=50)
            response_or = llm_or.invoke(test_prompt)
            latency_or = time.time() - start_time
            print(f"  ✅ 响应: {response_or.content}")
            print(f"  ⏱️  延迟: {latency_or:.2f}s")
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            latency_or = None
        
        # 测试官方 API
        print(f"\n🟢 测试官方 OpenAI API...")
        start_time = time.time()
        try:
            llm_official = MultiLLMFactory.create_llm(provider="openai", max_tokens=50)
            response_official = llm_official.invoke(test_prompt)
            latency_official = time.time() - start_time
            print(f"  ✅ 响应: {response_official.content}")
            print(f"  ⏱️  延迟: {latency_official:.2f}s")
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            latency_official = None
        
        # 对比结果
        if latency_or and latency_official:
            print(f"\n📊 对比结果:")
            print(f"  OpenRouter: {latency_or:.2f}s")
            print(f"  官方 API: {latency_official:.2f}s")
            if latency_or < latency_official:
                print(f"  🏆 OpenRouter 更快 ({(latency_official/latency_or - 1)*100:.0f}%)")
            else:
                print(f"  ⚠️ 官方 API 更快 ({(latency_or/latency_official - 1)*100:.0f}%)")
        
    except Exception as e:
        print(f"\n❌ 对比测试失败: {e}")

def show_model_recommendations():
    """显示模型推荐"""
    print("\n" + "="*60)
    print("OpenRouter 模型推荐")
    print("="*60)
    
    recommendations = [
        {
            "name": "openai/gpt-4o",
            "desc": "GPT-4o 最新版",
            "use_case": "高质量项目分析",
            "cost": "$2.5/$10 (输入/输出 每百万tokens)"
        },
        {
            "name": "openai/gpt-4o-mini",
            "desc": "GPT-4o 经济版",
            "use_case": "日常对话和简单分析",
            "cost": "$0.15/$0.6"
        },
        {
            "name": "openai/o1-preview",
            "desc": "OpenAI 推理模型",
            "use_case": "复杂逻辑推理",
            "cost": "$15/$60"
        },
        {
            "name": "anthropic/claude-3.5-sonnet",
            "desc": "Claude 3.5 Sonnet",
            "use_case": "长文本分析",
            "cost": "$3/$15"
        },
        {
            "name": "meta-llama/llama-3.3-70b-instruct",
            "desc": "Llama 3.3 70B",
            "use_case": "开源替代（免费）",
            "cost": "免费"
        }
    ]
    
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec['name']}")
        print(f"   描述: {rec['desc']}")
        print(f"   适用: {rec['use_case']}")
        print(f"   成本: {rec['cost']}")
    
    print(f"\n💡 更多模型: https://openrouter.ai/models")

if __name__ == "__main__":
    print("\n🚀 OpenRouter 配置测试工具")
    print("   官网: https://openrouter.ai/")
    print("   文档: https://openrouter.ai/docs")
    
    # 1. 配置检查
    config_ok = test_openrouter_config()
    
    if not config_ok:
        print("\n⚠️ 请先配置 OpenRouter API Key")
        sys.exit(1)
    
    # 2. 连接测试
    connection_ok = test_openrouter_connection()
    
    if connection_ok:
        # 3. 对比测试
        compare_with_official_api()
    
    # 4. 模型推荐
    show_model_recommendations()
    
    print("\n" + "="*60)
    print("测试完成!")
    print("="*60)
    
    if connection_ok:
        print(f"\n✅ OpenRouter 配置成功!")
        print(f"\n📝 使用方法:")
        print(f"   1. 修改 .env: LLM_PROVIDER=openrouter")
        print(f"   2. 重启服务: python intelligent_project_analyzer/api/server.py")
        print(f"   3. 运行前端: python intelligent_project_analyzer/frontend/run_frontend.py")
    else:
        print(f"\n❌ OpenRouter 配置失败，请检查上述错误信息")
