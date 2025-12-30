"""
LLM工厂模块 - 2025年工厂模式 + 自动降级

提供统一的LLM实例创建接口,支持依赖注入、配置管理和自动降级
"""

from typing import Optional
from langchain_openai import ChatOpenAI
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpcore
import openai

from intelligent_project_analyzer.settings import settings, LLMConfig


class LLMFactory:
    """
    LLM工厂 - 2025年依赖注入模式 + 自动降级
    
    优势:
    - 统一的LLM创建接口
    - 支持配置注入
    - 易于测试(可Mock)
    - 避免配置漂移
    - 🆕 自动降级: OpenAI失败时切换到Qwen
    """
    
    @staticmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpcore.ConnectError, openai.APIConnectionError, ConnectionError)),
        reraise=True
    )
    def create_llm(config: Optional[LLMConfig] = None, **kwargs) -> ChatOpenAI:
        """
        创建LLM实例 (支持 OpenRouter 多 Key 负载均衡 + SSL重试)

        🆕 v7.4.2: 优先使用 OpenRouter 多 Key 负载均衡
        - 如果配置了多个 OpenRouter Keys，自动启用负载均衡
        - 如果禁用自动降级，只使用配置的提供商
        - 重试策略: 指数退避,最多3次,针对网络连接错误

        Args:
            config: LLM配置对象,如果为None则使用全局settings
            **kwargs: 额外的LLM参数,会覆盖config中的值

        Returns:
            ChatOpenAI实例

        Example:
            # 使用默认配置 (OpenRouter 负载均衡)
            llm = LLMFactory.create_llm()

            # 使用自定义配置
            custom_config = LLMConfig(
                model="gpt-4.1",
                max_tokens=32000,
                api_key="..."
            )
            llm = LLMFactory.create_llm(config=custom_config)

            # 覆盖特定参数 (头脑风暴场景)
            llm = LLMFactory.create_llm(temperature=0.9, max_tokens=32000)
        """
        import os

        # 🆕 v7.4.2: 检查是否使用 OpenRouter 且配置了多个 Keys
        primary_provider = os.getenv("LLM_PROVIDER", "openai").lower()
        auto_fallback = os.getenv("LLM_AUTO_FALLBACK", "false").lower() == "true"

        # 如果是 OpenRouter 且配置了多个 Keys，使用负载均衡
        if primary_provider == "openrouter":
            openrouter_keys = os.getenv("OPENROUTER_API_KEYS", "")
            if openrouter_keys and "," in openrouter_keys:
                logger.info("🔄 检测到多个 OpenRouter Keys，启用负载均衡")
                try:
                    return LLMFactory.create_openrouter_balanced_llm(**kwargs)
                except Exception as e:
                    logger.warning(f"⚠️ OpenRouter 负载均衡创建失败: {e}")
                    # 继续使用原始方法

        # 全局捕获 LLM 连接异常，返回友好提示
        try:
            # ...existing code...
            # 如果禁用自动降级，直接使用原始方法
            if not auto_fallback:
                logger.info(f"📌 自动降级已禁用，只使用 {primary_provider}")
                return LLMFactory._create_llm_original(config, **kwargs)

            # 尝试使用多LLM工厂创建(支持自动降级)
            from intelligent_project_analyzer.services.multi_llm_factory import MultiLLMFactory, FallbackLLM
            fallback_chain = [primary_provider]
            if primary_provider == "openai":
                if os.getenv("OPENROUTER_API_KEY") and os.getenv("OPENROUTER_API_KEY") != "your_openrouter_api_key_here":
                    fallback_chain.append("openrouter")
                if os.getenv("DEEPSEEK_API_KEY") and os.getenv("DEEPSEEK_API_KEY") != "your_deepseek_api_key_here":
                    fallback_chain.append("deepseek")
            elif primary_provider == "openrouter":
                if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "your_openai_api_key_here":
                    fallback_chain.append("openai")
                if os.getenv("DEEPSEEK_API_KEY") and os.getenv("DEEPSEEK_API_KEY") != "your_deepseek_api_key_here":
                    fallback_chain.append("deepseek")
            elif primary_provider == "qwen":
                if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "your_openai_api_key_here":
                    fallback_chain.append("openai")
                if os.getenv("OPENROUTER_API_KEY") and os.getenv("OPENROUTER_API_KEY") != "your_openrouter_api_key_here":
                    fallback_chain.append("openrouter")
                if os.getenv("DEEPSEEK_API_KEY") and os.getenv("DEEPSEEK_API_KEY") != "your_deepseek_api_key_here":
                    fallback_chain.append("deepseek")
            elif primary_provider == "deepseek":
                if os.getenv("OPENROUTER_API_KEY") and os.getenv("OPENROUTER_API_KEY") != "your_openrouter_api_key_here":
                    fallback_chain.append("openrouter")
                if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "your_openai_api_key_here":
                    fallback_chain.append("openai")
            # 使用降级链创建LLM
            if len(fallback_chain) > 1:
                logger.info(f"🔄 启用自动降级: {' → '.join(fallback_chain)}")
                return FallbackLLM(
                    providers=fallback_chain,
                    temperature=kwargs.get("temperature", config.temperature if config else settings.llm.temperature),
                    max_tokens=kwargs.get("max_tokens", config.max_tokens if config else settings.llm.max_tokens),
                    timeout=kwargs.get("timeout", config.timeout if config else settings.llm.timeout),
                    max_retries=kwargs.get("max_retries", config.max_retries if config else settings.llm.max_retries),
                )
            else:
                return MultiLLMFactory.create_llm(
                    provider=primary_provider,
                    temperature=kwargs.get("temperature", config.temperature if config else settings.llm.temperature),
                    max_tokens=kwargs.get("max_tokens", config.max_tokens if config else settings.llm.max_tokens),
                    timeout=kwargs.get("timeout", config.timeout if config else settings.llm.timeout),
                    max_retries=kwargs.get("max_retries", config.max_retries if config else settings.llm.max_retries),
                    **kwargs
                )
        except (openai.APIConnectionError, httpcore.ConnectError, ConnectionError) as e:
            logger.error(f"❌ LLM服务连接异常: {e}")
            raise RuntimeError("LLM服务连接异常，请稍后重试。");
        except Exception as e:
            logger.error(f"❌ LLM实例创建异常: {e}")
            raise

        # 如果禁用自动降级，直接使用原始方法
        if not auto_fallback:
            logger.info(f"📌 自动降级已禁用，只使用 {primary_provider}")
            return LLMFactory._create_llm_original(config, **kwargs)

        # 尝试使用多LLM工厂创建(支持自动降级)
        try:
            from intelligent_project_analyzer.services.multi_llm_factory import MultiLLMFactory, FallbackLLM

            # 定义降级链
            fallback_chain = [primary_provider]

            # 根据主提供商添加备选
            if primary_provider == "openai":
                # OpenAI 官方 → OpenRouter (GPT) → DeepSeek
                if os.getenv("OPENROUTER_API_KEY") and os.getenv("OPENROUTER_API_KEY") != "your_openrouter_api_key_here":
                    fallback_chain.append("openrouter")
                if os.getenv("DEEPSEEK_API_KEY") and os.getenv("DEEPSEEK_API_KEY") != "your_deepseek_api_key_here":
                    fallback_chain.append("deepseek")
            elif primary_provider == "openrouter":
                # OpenRouter → OpenAI → DeepSeek
                if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "your_openai_api_key_here":
                    fallback_chain.append("openai")
                if os.getenv("DEEPSEEK_API_KEY") and os.getenv("DEEPSEEK_API_KEY") != "your_deepseek_api_key_here":
                    fallback_chain.append("deepseek")
            elif primary_provider == "qwen":
                # Qwen → OpenAI → OpenRouter → DeepSeek
                if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "your_openai_api_key_here":
                    fallback_chain.append("openai")
                if os.getenv("OPENROUTER_API_KEY") and os.getenv("OPENROUTER_API_KEY") != "your_openrouter_api_key_here":
                    fallback_chain.append("openrouter")
                if os.getenv("DEEPSEEK_API_KEY") and os.getenv("DEEPSEEK_API_KEY") != "your_deepseek_api_key_here":
                    fallback_chain.append("deepseek")
            elif primary_provider == "deepseek":
                # DeepSeek → OpenRouter → OpenAI
                if os.getenv("OPENROUTER_API_KEY") and os.getenv("OPENROUTER_API_KEY") != "your_openrouter_api_key_here":
                    fallback_chain.append("openrouter")
                if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "your_openai_api_key_here":
                    fallback_chain.append("openai")

            # 使用降级链创建LLM
            if len(fallback_chain) > 1:
                logger.info(f"🔄 启用自动降级: {' → '.join(fallback_chain)}")
                return FallbackLLM(
                    providers=fallback_chain,
                    temperature=kwargs.get("temperature", config.temperature if config else settings.llm.temperature),
                    max_tokens=kwargs.get("max_tokens", config.max_tokens if config else settings.llm.max_tokens),
                    timeout=kwargs.get("timeout", config.timeout if config else settings.llm.timeout),
                    max_retries=kwargs.get("max_retries", config.max_retries if config else settings.llm.max_retries),
                )
            else:
                # 没有备选,直接创建
                return MultiLLMFactory.create_llm(
                    provider=primary_provider,
                    temperature=kwargs.get("temperature", config.temperature if config else settings.llm.temperature),
                    max_tokens=kwargs.get("max_tokens", config.max_tokens if config else settings.llm.max_tokens),
                    timeout=kwargs.get("timeout", config.timeout if config else settings.llm.timeout),
                    max_retries=kwargs.get("max_retries", config.max_retries if config else settings.llm.max_retries),
                    **kwargs
                )
        except Exception as e:
            logger.warning(f"⚠️ MultiLLM降级失败,使用原始方法: {e}")
            # 降级到原始方法
            return LLMFactory._create_llm_original(config, **kwargs)
    
    @staticmethod
    def _create_llm_original(config: Optional[LLMConfig] = None, **kwargs) -> ChatOpenAI:
        """
        创建LLM实例 (原始方法,无降级)
        
        Args:
            config: LLM配置对象,如果为None则使用全局settings
            **kwargs: 额外的LLM参数,会覆盖config中的值
            
        Returns:
            ChatOpenAI实例
        """
        # 使用提供的配置或全局配置
        cfg = config or settings.llm
        
        # 构建LLM参数
        llm_params = {
            "model": cfg.model,
            "max_tokens": cfg.max_tokens,
            "timeout": cfg.timeout,
            "temperature": cfg.temperature,
            "api_key": cfg.api_key,
            "max_retries": cfg.max_retries,  # 应用重试配置
        }
        
        # 如果有自定义API Base
        if cfg.api_base:
            llm_params["base_url"] = cfg.api_base
        
        # 应用kwargs覆盖
        llm_params.update(kwargs)
        
        logger.info(
            f"创建LLM实例: model={llm_params['model']}, "
            f"max_tokens={llm_params['max_tokens']}, "
            f"max_retries={llm_params.get('max_retries', cfg.max_retries)}"
        )
        
        return ChatOpenAI(**llm_params)
    
    @staticmethod
    def create_streaming_llm(config: Optional[LLMConfig] = None, **kwargs) -> ChatOpenAI:
        """
        创建流式LLM实例
        
        Args:
            config: LLM配置对象
            **kwargs: 额外的LLM参数
            
        Returns:
            支持流式输出的ChatOpenAI实例
        """
        # 强制启用streaming
        kwargs["streaming"] = True
        
        llm = LLMFactory.create_llm(config=config, **kwargs)
        logger.info("创建流式LLM实例")
        
        return llm
    
    @staticmethod
    def create_structured_llm(
        config: Optional[LLMConfig] = None,
        schema: Optional[type] = None,
        **kwargs
    ) -> ChatOpenAI:
        """
        创建结构化输出LLM实例
        
        Args:
            config: LLM配置对象
            schema: Pydantic模型类,用于结构化输出
            **kwargs: 额外的LLM参数
            
        Returns:
            支持结构化输出的ChatOpenAI实例
        """
        llm = LLMFactory.create_llm(config=config, **kwargs)
        
        if schema:
            # 使用with_structured_output绑定schema
            llm = llm.with_structured_output(schema)
            logger.info(f"创建结构化输出LLM实例: schema={schema.__name__}")
        
        return llm
    
    @staticmethod
    def get_default_config() -> LLMConfig:
        """
        获取默认LLM配置
        
        Returns:
            全局settings中的LLM配置
        """
        return settings.llm
    
    @staticmethod
    def validate_config(config: LLMConfig) -> bool:
        """
        验证LLM配置
        
        Args:
            config: 要验证的配置
            
        Returns:
            配置是否有效
        """
        if not config.api_key:
            logger.error("LLM配置无效: 缺少API Key")
            return False
        
        if config.max_tokens < 100:
            logger.warning(f"max_tokens过小: {config.max_tokens}, 建议至少1000")
        
        if config.timeout < 10:
            logger.warning(f"timeout过短: {config.timeout}秒, 建议至少30秒")
        
        logger.info("LLM配置验证通过")
        return True

    @staticmethod
    def create_high_concurrency_llm(
        provider: str = "openai",
        enable_cache: bool = True,
        enable_fallback: bool = True,
        **kwargs
    ):
        """
        🆕 v3.9: 创建高并发 LLM 实例

        支持:
        - 多 Key 负载均衡
        - 多提供商故障转移
        - 请求限流
        - 结果缓存

        Args:
            provider: 首选提供商
            enable_cache: 是否启用缓存
            enable_fallback: 是否启用故障转移
            **kwargs: 其他 LLM 参数

        Returns:
            HighConcurrencyLLM 实例

        Example:
            llm = LLMFactory.create_high_concurrency_llm("openai")
            result = await llm.ainvoke("Hello")
        """
        try:
            from intelligent_project_analyzer.services.high_concurrency_llm import HighConcurrencyLLM

            return HighConcurrencyLLM(
                preferred_provider=provider,
                enable_cache=enable_cache,
                enable_fallback=enable_fallback,
                **kwargs
            )
        except Exception as e:
            logger.warning(f"⚠️ 高并发LLM创建失败,回退到普通LLM: {e}")
            return LLMFactory.create_llm(**kwargs)

    @staticmethod
    def create_openrouter_balanced_llm(
        model: str = "openai/gpt-4o-2024-11-20",
        strategy: str = "round_robin",
        **kwargs
    ):
        """
        🆕 v7.4.2: 创建 OpenRouter 负载均衡 LLM 实例

        使用多个 API Key 进行负载均衡，提高稳定性和吞吐量。

        特性:
        - 多 Key 轮询/随机/最少使用策略
        - 自动健康检查和故障转移
        - 速率限制保护
        - 使用统计和监控

        Args:
            model: OpenRouter 模型名称
            strategy: 负载均衡策略 (round_robin | random | least_used)
            **kwargs: 其他 LLM 参数

        Returns:
            ChatOpenAI 实例（通过负载均衡器）

        Example:
            # 在 .env 中配置多个 Keys:
            # OPENROUTER_API_KEYS=key1,key2,key3

            llm = LLMFactory.create_openrouter_balanced_llm()
            response = llm.invoke("Hello")
        """
        try:
            from intelligent_project_analyzer.services.openrouter_load_balancer import (
                get_global_balancer,
                LoadBalancerConfig
            )

            # 创建配置
            config = LoadBalancerConfig(strategy=strategy)

            # 获取全局负载均衡器
            balancer = get_global_balancer(
                config=config,
                model=model,
                **kwargs
            )

            # 返回 LLM 实例
            return balancer.get_llm()

        except Exception as e:
            logger.warning(f"⚠️ OpenRouter 负载均衡器创建失败，回退到普通 LLM: {e}")
            return LLMFactory.create_llm(**kwargs)

