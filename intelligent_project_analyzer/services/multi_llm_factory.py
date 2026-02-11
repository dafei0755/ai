"""
多LLM提供商工厂 - 支持多备选切换

支持的提供商:
- OpenAI (官方API)
- OpenRouter (国内可用的 OpenAI 代理)
- DeepSeek (国内快速)
- 阿里通义千问
- Anthropic Claude
- Azure OpenAI
"""

import os
from typing import Optional, Literal
from langchain_openai import ChatOpenAI, AzureChatOpenAI
from langchain_anthropic import ChatAnthropic
from loguru import logger
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 导入全局配置 (提供默认值)
try:
    from intelligent_project_analyzer.settings import settings
    DEFAULT_MAX_TOKENS = settings.llm.max_tokens
    DEFAULT_TEMPERATURE = settings.llm.temperature
    DEFAULT_TIMEOUT = settings.llm.timeout
except ImportError:
    # 降级默认值 (与.env配置保持一致)
    DEFAULT_MAX_TOKENS = 32000  # 支持完整结构化报告
    DEFAULT_TEMPERATURE = 0.7   # 设计行业创意与稳定平衡
    DEFAULT_TIMEOUT = 600       # 10分钟应对长输出

LLMProvider = Literal["openai", "deepseek", "qwen", "anthropic", "azure", "openrouter"]


class MultiLLMFactory:
    """
    多LLM提供商工厂
    
    使用方法:
        # 方式1: 从环境变量自动选择
        llm = MultiLLMFactory.create_llm()
        
        # 方式2: 手动指定提供商
        llm = MultiLLMFactory.create_llm(provider="deepseek")
        
        # 方式3: 使用备选链 (自动降级)
        llm = MultiLLMFactory.create_with_fallback(
            providers=["openai", "deepseek", "qwen"]
        )
    """
    
    # 提供商配置映射
    PROVIDER_CONFIGS = {
        "openai": {
            "api_key_env": "OPENAI_API_KEY",
            "model_env": "OPENAI_MODEL",
            "base_url_env": "OPENAI_BASE_URL",
            "default_model": "gpt-4.1",  # 与.env一致
            "class": ChatOpenAI
        },
        "deepseek": {
            "api_key_env": "DEEPSEEK_API_KEY",
            "model_env": "DEEPSEEK_MODEL",
            "base_url_env": "DEEPSEEK_BASE_URL",
            "default_model": "deepseek-chat",  # 与.env官方推荐一致
            "default_base_url": "https://api.deepseek.com",
            "class": ChatOpenAI
        },
        "qwen": {
            "api_key_env": "QWEN_API_KEY",  # 阿里云百炼API Key
            "model_env": "QWEN_MODEL",
            "base_url_env": "QWEN_BASE_URL",
            "default_model": "qwen-max",  # 与.env官方推荐一致
            "default_base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",  # 北京地域
            "class": ChatOpenAI
        },
        "anthropic": {
            "api_key_env": "ANTHROPIC_API_KEY",
            "model_env": "ANTHROPIC_MODEL",
            "default_model": "claude-3-5-sonnet-20241022",  # 与.env官方推荐一致
            "class": ChatAnthropic
        },
        "azure": {
            "api_key_env": "AZURE_OPENAI_API_KEY",
            "endpoint_env": "AZURE_OPENAI_ENDPOINT",
            "deployment_env": "AZURE_OPENAI_DEPLOYMENT",
            "version_env": "AZURE_API_VERSION",
            "default_version": "2024-02-15-preview",
            "class": AzureChatOpenAI
        },
        "openrouter": {
            "api_key_env": "OPENROUTER_API_KEY",
            "model_env": "OPENROUTER_MODEL",
            "base_url_env": "OPENROUTER_BASE_URL",
            "default_model": "openai/gpt-4o",  # OpenRouter 需要加提供商前缀
            "default_base_url": "https://openrouter.ai/api/v1",
            "class": ChatOpenAI,
            "extra_headers": True  # 标记需要添加自定义 headers
        }
    }
    
    @classmethod
    def create_llm(
        cls,
        provider: Optional[LLMProvider] = None,
        temperature: float = None,
        max_tokens: int = None,
        timeout: int = None,
        max_retries: int = None,
        **kwargs
    ):
        """
        创建LLM实例
        
        Args:
            provider: 提供商名称,如果为None则从环境变量LLM_PROVIDER读取
            temperature: 温度参数 (None时使用settings默认值)
            max_tokens: 最大token数 (None时使用settings默认值)
            timeout: 超时时间(秒) (None时使用settings默认值)
            max_retries: 重试次数 (None时使用settings默认值)
            **kwargs: 其他LLM参数
            
        Returns:
            LLM实例
        """
        # 应用默认值
        temperature = temperature if temperature is not None else DEFAULT_TEMPERATURE
        max_tokens = max_tokens if max_tokens is not None else DEFAULT_MAX_TOKENS
        timeout = timeout if timeout is not None else DEFAULT_TIMEOUT
        max_retries = max_retries if max_retries is not None else getattr(settings.llm, 'max_retries', 3)
        
        logger.debug(
            f" 使用配置: temperature={temperature}, max_tokens={max_tokens}, "
            f"timeout={timeout}s, max_retries={max_retries}"
        )
        
        # 确定使用的提供商
        if provider is None:
            provider = os.getenv("LLM_PROVIDER", "openai").lower()
        
        # 获取模型名称用于日志
        config = cls.PROVIDER_CONFIGS.get(provider, {})
        model_env = config.get("model_env", "")
        model_name = os.getenv(model_env, config.get("default_model", "unknown"))
        
        logger.info(f" Creating LLM instance: provider={provider}, model={model_name}, temperature={temperature}, max_tokens={max_tokens}")
        
        # 验证提供商
        if provider not in cls.PROVIDER_CONFIGS:
            logger.error(f" Unknown provider: {provider}")
            raise ValueError(f"Unknown LLM provider: {provider}")
        
        # 获取提供商配置
        config = cls.PROVIDER_CONFIGS[provider]
        
        # 根据提供商类型创建实例
        if provider == "azure":
            return cls._create_azure_llm(config, temperature, max_tokens, timeout, max_retries, **kwargs)
        elif provider == "anthropic":
            return cls._create_anthropic_llm(config, temperature, max_tokens, timeout, max_retries, **kwargs)
        else:
            return cls._create_openai_compatible_llm(config, temperature, max_tokens, timeout, max_retries, **kwargs)
    
    @classmethod
    def _create_openai_compatible_llm(
        cls, 
        config: dict, 
        temperature: float, 
        max_tokens: int, 
        timeout: int,
        max_retries: int,
        **kwargs
    ) -> ChatOpenAI:
        """创建OpenAI兼容的LLM (OpenAI/DeepSeek/Qwen/OpenRouter)"""
        
        # 获取API Key
        api_key = os.getenv(config["api_key_env"])
        if not api_key or api_key == "your_xxx_api_key_here":
            raise ValueError(f" Missing or invalid API key: {config['api_key_env']}")
        
        # 获取模型名称
        model = os.getenv(config["model_env"], config["default_model"])
        
        # 构建参数
        llm_params = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout,
            "max_retries": max_retries,
            "api_key": api_key,
            **kwargs
        }
        
        # 如果有base_url配置
        if "base_url_env" in config:
            base_url = os.getenv(config["base_url_env"], config.get("default_base_url"))
            if base_url:
                llm_params["base_url"] = base_url
        
        # OpenRouter 需要额外的 headers
        if config.get("extra_headers"):
            app_name = os.getenv("OPENROUTER_APP_NAME", "Intelligent Project Analyzer")
            site_url = os.getenv("OPENROUTER_SITE_URL", "https://github.com/your-repo")
            llm_params["default_headers"] = {
                "HTTP-Referer": site_url,
                "X-Title": app_name
            }
            logger.info(f" OpenRouter headers: referer={site_url}, title={app_name}")
        
        logger.info(f" Creating {model} (timeout={timeout}s, max_tokens={max_tokens})")
        
        return config["class"](**llm_params)
    
    @classmethod
    def _create_anthropic_llm(
        cls,
        config: dict,
        temperature: float,
        max_tokens: int,
        timeout: int,
        max_retries: int,
        **kwargs
    ) -> ChatAnthropic:
        """创建Anthropic Claude LLM"""
        
        api_key = os.getenv(config["api_key_env"])
        if not api_key or api_key == "your_anthropic_api_key_here":
            raise ValueError(f" Missing or invalid API key: {config['api_key_env']}")
        
        model = os.getenv(config["model_env"], config["default_model"])
        
        llm_params = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout,
            "max_retries": max_retries,
            "anthropic_api_key": api_key,
            **kwargs
        }
        
        logger.info(f" Creating {model} (Anthropic)")
        
        return config["class"](**llm_params)
    
    @classmethod
    def _create_azure_llm(
        cls,
        config: dict,
        temperature: float,
        max_tokens: int,
        timeout: int,
        max_retries: int,
        **kwargs
    ) -> AzureChatOpenAI:
        """创建Azure OpenAI LLM"""
        
        api_key = os.getenv(config["api_key_env"])
        endpoint = os.getenv(config["endpoint_env"])
        deployment = os.getenv(config["deployment_env"])
        api_version = os.getenv(config["version_env"], config["default_version"])
        
        if not all([api_key, endpoint, deployment]):
            raise ValueError(" Missing Azure OpenAI configuration")
        
        llm_params = {
            "azure_deployment": deployment,
            "azure_endpoint": endpoint,
            "api_key": api_key,
            "api_version": api_version,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout,
            "max_retries": max_retries,
            **kwargs
        }
        
        logger.info(f" Creating Azure OpenAI: {deployment}")
        
        return config["class"](**llm_params)
    
    @classmethod
    def create_with_fallback(
        cls,
        providers: list[LLMProvider],
        temperature: float = None,
        max_tokens: int = None,
        timeout: int = None,
        max_retries: int = None,
        **kwargs
    ):
        """
        使用降级链创建LLM实例
        
        Args:
            providers: 提供商列表,按优先级排序
            temperature: 温度参数
            max_tokens: 最大token数
            timeout: 超时时间(秒)
            max_retries: 重试次数
            **kwargs: 其他LLM参数
            
        Returns:
            成功创建的第一个LLM实例
            
        Example:
            # 推荐配置：OpenAI官方 → OpenRouter → DeepSeek
            llm = MultiLLMFactory.create_with_fallback(
                providers=["openai", "openrouter", "deepseek"]
            )
        """
        logger.info(f" Attempting to create LLM with fallback: {providers}")
        
        last_error = None
        for provider in providers:
            try:
                llm = cls.create_llm(
                    provider=provider,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                    max_retries=max_retries,
                    **kwargs
                )
                logger.info(f" Successfully created LLM with provider: {provider}")
                return llm
            except Exception as e:
                logger.warning(f"️ Failed to create {provider} LLM: {e}")
                last_error = e
                continue
        
        # 所有提供商都失败
        logger.error(f" All providers failed. Last error: {last_error}")
        raise RuntimeError(f"Failed to create LLM with any provider: {providers}")
    
    @classmethod
    def get_active_provider(cls) -> str:
        """获取当前激活的提供商"""
        return os.getenv("LLM_PROVIDER", "openai").lower()
    
    @classmethod
    def list_available_providers(cls) -> list[str]:
        """列出所有可用的提供商"""
        available = []
        for provider, config in cls.PROVIDER_CONFIGS.items():
            api_key = os.getenv(config.get("api_key_env", ""))
            if api_key and api_key != f"your_{provider}_api_key_here":
                available.append(provider)
        return available
    
    @classmethod
    def test_provider(cls, provider: LLMProvider) -> bool:
        """测试提供商是否可用"""
        try:
            llm = cls.create_llm(provider=provider, timeout=10)
            result = llm.invoke("Say hello")
            logger.info(f" Provider {provider} test passed: {result.content[:50]}")
            return True
        except Exception as e:
            logger.error(f" Provider {provider} test failed: {e}")
            return False


class FallbackLLM:
    """
    运行时降级 LLM 包装器
    
    当主 LLM 调用失败时，自动尝试备选 LLM
    
    Example:
        llm = FallbackLLM(providers=["openai", "openrouter", "deepseek"])
        response = llm.invoke("Hello")  # 自动降级
    """
    
    def __init__(
        self,
        providers: list[str],
        temperature: float = None,
        max_tokens: int = None,
        timeout: int = None,
        max_retries: int = None,
        **kwargs
    ):
        """初始化降级 LLM"""
        self.providers = providers
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.max_retries = max_retries
        self.kwargs = kwargs
        
        # 预创建所有 LLM 实例
        self.llm_instances = {}
        for provider in providers:
            try:
                llm = MultiLLMFactory.create_llm(
                    provider=provider,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                    max_retries=max_retries,
                    **kwargs
                )
                self.llm_instances[provider] = llm
                logger.info(f" 预创建 {provider} LLM 成功")
            except Exception as e:
                logger.warning(f"️ 预创建 {provider} LLM 失败: {e}")
        
        if not self.llm_instances:
            raise RuntimeError(f"无法创建任何 LLM 实例: {providers}")
        
        logger.info(f" 降级链就绪: {' → '.join(self.llm_instances.keys())}")
    
    def invoke(self, *args, **kwargs):
        """调用 LLM，支持自动降级"""
        last_error = None
        
        for provider, llm in self.llm_instances.items():
            try:
                logger.debug(f" 尝试使用 {provider} 调用 LLM...")
                response = llm.invoke(*args, **kwargs)
                logger.success(f" {provider} 调用成功")
                return response
                
            except Exception as e:
                error_msg = str(e)
                logger.warning(f"️ {provider} 调用失败: {error_msg[:100]}")
                last_error = e
                
                # 如果是配额问题，立即尝试下一个
                if "429" in error_msg or "quota" in error_msg.lower():
                    logger.info(f" 检测到配额问题，切换到下一个提供商...")
                    continue
                
                # 其他错误也尝试降级
                logger.info(f" 尝试降级到下一个提供商...")
                continue
        
        # 所有提供商都失败
        logger.error(f" 所有提供商调用失败")
        raise RuntimeError(f"所有 LLM 提供商调用失败: {list(self.llm_instances.keys())}") from last_error
    
    def __getattr__(self, name):
        """代理其他方法到第一个可用的 LLM"""
        if self.llm_instances:
            first_llm = next(iter(self.llm_instances.values()))
            return getattr(first_llm, name)
        raise AttributeError(f"FallbackLLM has no attribute '{name}'")
