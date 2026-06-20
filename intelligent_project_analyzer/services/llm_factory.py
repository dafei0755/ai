"""
LLM工厂模块 - 2025年工厂模式 + 自动降级 + 系统级语义缓存

提供统一的LLM实例创建接口,支持依赖注入、配置管理、自动降级和透明缓存
"""

import os
from typing import Any, Dict, Optional

import httpcore
import openai
from langchain_openai import ChatOpenAI
from loguru import logger
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from intelligent_project_analyzer.settings import LLMConfig, settings

# P0-F2: 全局初始化LangChain缓存，使用官方API避免"no cache found"错误
try:
    from langchain.globals import set_llm_cache, get_llm_cache
    if get_llm_cache() is None:
        from langchain_community.cache import InMemoryCache
        set_llm_cache(InMemoryCache())
        logger.info("[LLMFactory] Initialized global LLM cache via set_llm_cache()")
except ImportError:
    try:
        import langchain
        if not hasattr(langchain, 'llm_cache') or langchain.llm_cache is None:
            from langchain_community.cache import InMemoryCache
            langchain.llm_cache = InMemoryCache()
            logger.info("[LLMFactory] Initialized langchain.llm_cache globally (legacy)")
    except Exception as e:
        logger.warning(f"[LLMFactory] Failed to init langchain.llm_cache: {e}")
except Exception as e:
    logger.warning(f"[LLMFactory] Failed to init global LLM cache: {e}")


class LLMFactory:
    """
    LLM工厂 - 2025年依赖注入模式 + 自动降级 + 系统级语义缓存

    优势:
    - 统一的LLM创建接口
    - 支持配置注入
    - 易于测试(可Mock)
    - 避免配置漂移
    - 自动降级: OpenAI失败时切换到Qwen
    - 系统级语义缓存: 所有LLM调用自动享受缓存（零侵入）
    """

    # 全局语义缓存实例（单例模式）
    _global_semantic_cache = None

    @classmethod
    def _get_semantic_cache(cls):
        """获取全局语义缓存实例（懒加载）"""
        if cls._global_semantic_cache is None:
            # 检查是否启用缓存
            enable_cache = os.getenv("SEMANTIC_CACHE_ENABLED", "true").lower() == "true"

            if enable_cache:
                try:
                    from intelligent_project_analyzer.services.semantic_cache import SemanticCache

                    # 从环境变量读取配置
                    similarity_threshold = float(os.getenv("SEMANTIC_CACHE_THRESHOLD", "0.90"))
                    ttl = int(os.getenv("SEMANTIC_CACHE_TTL", "604800"))  # 7天

                    cls._global_semantic_cache = SemanticCache(
                        similarity_threshold=similarity_threshold,
                        ttl=ttl,
                    )
                    logger.info(
                        f"[LLM Factory] Semantic cache initialized globally "
                        f"(threshold={similarity_threshold}, ttl={ttl}s)"
                    )
                except Exception as e:
                    logger.warning(f"[LLM Factory] Failed to initialize semantic cache: {e}")
                    cls._global_semantic_cache = None
            else:
                logger.info("[LLM Factory] Semantic cache disabled by config")

        return cls._global_semantic_cache

    @classmethod
    def _wrap_with_cache(cls, llm, cache_namespace: str = "default"):
        """
        包装LLM实例，添加语义缓存层

        Args:
            llm: 原始LLM实例
            cache_namespace: 缓存命名空间

        Returns:
            包装后的LLM实例（如果缓存未启用则返回原始实例）
        """
        cache = cls._get_semantic_cache()

        if cache is None:
            return llm

        try:
            from intelligent_project_analyzer.services.cached_llm_wrapper import wrap_llm_with_cache

            return wrap_llm_with_cache(
                llm=llm,
                cache=cache,
                cache_namespace=cache_namespace,
                enable_cache=True,
            )
        except Exception as e:
            logger.warning(f"[LLM Factory] Failed to wrap LLM with cache: {e}")
            return llm

    @staticmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpcore.ConnectError, openai.APIConnectionError, ConnectionError)),
        reraise=True,
    )
    def create_llm(config: Optional[LLMConfig] = None, **kwargs) -> ChatOpenAI:
        """
        创建LLM实例 (支持 OpenRouter 多 Key 负载均衡 + SSL重试)

         v7.4.2: 优先使用 OpenRouter 多 Key 负载均衡
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

        #  v7.4.2: 检查是否使用 OpenRouter 且配置了多个 Keys
        primary_provider = os.getenv("LLM_PROVIDER", "openai").lower()
        auto_fallback = os.getenv("LLM_AUTO_FALLBACK", "false").lower() == "true"

        # 如果是 OpenRouter 且配置了多个 Keys，使用负载均衡
        if primary_provider == "openrouter":
            openrouter_keys = os.getenv("OPENROUTER_API_KEYS", "")
            if openrouter_keys and "," in openrouter_keys:
                logger.info(" 检测到多个 OpenRouter Keys，启用负载均衡")
                try:
                    cfg = config or settings.llm
                    lb_kwargs = dict(kwargs)
                    lb_timeout = lb_kwargs.pop("timeout", cfg.timeout)
                    lb_retries = lb_kwargs.pop("max_retries", cfg.max_retries)
                    # 关键：显式传递 timeout / max_retries，避免负载均衡路径丢失超时控制
                    llm = LLMFactory.create_openrouter_balanced_llm(
                        timeout=lb_timeout,
                        max_retries=lb_retries,
                        **lb_kwargs,
                    )
                    return LLMFactory._wrap_with_cache(llm, cache_namespace="openrouter_balanced")
                except Exception as e:
                    logger.warning(f"️ OpenRouter 负载均衡创建失败: {e}")
                    # 继续使用原始方法

        # 全局捕获 LLM 连接异常，返回友好提示
        try:
            # ...existing code...
            # 如果禁用自动降级，直接使用原始方法
            if not auto_fallback:
                logger.info(f" 自动降级已禁用，只使用 {primary_provider}")

                #  关键修复：即使禁用自动降级，也必须尊重 LLM_PROVIDER。
                # 否则会走 _create_llm_original（仅绑定 OPENAI_API_KEY/OPENAI_*），
                # 导致在 openrouter/deepseek/qwen 等场景下 LLM 调用失败，进而触发问卷/维度的硬编码回退。
                if primary_provider == "openai":
                    llm = LLMFactory._create_llm_original(config, **kwargs)
                    return LLMFactory._wrap_with_cache(llm, cache_namespace="openai")

                from intelligent_project_analyzer.services.multi_llm_factory import MultiLLMFactory

                cfg = config or settings.llm
                extra_kwargs = dict(kwargs)
                extra_kwargs.pop("provider", None)
                extra_kwargs.pop("temperature", None)
                extra_kwargs.pop("max_tokens", None)
                extra_kwargs.pop("timeout", None)
                extra_kwargs.pop("max_retries", None)

                llm = MultiLLMFactory.create_llm(
                    provider=primary_provider,
                    temperature=kwargs.get("temperature", cfg.temperature),
                    max_tokens=kwargs.get("max_tokens", cfg.max_tokens),
                    timeout=kwargs.get("timeout", cfg.timeout),
                    max_retries=kwargs.get("max_retries", cfg.max_retries),
                    **extra_kwargs,
                )
                return LLMFactory._wrap_with_cache(llm, cache_namespace=primary_provider)

            # 尝试使用多LLM工厂创建(支持自动降级)
            from intelligent_project_analyzer.services.multi_llm_factory import (
                FallbackLLM,
                MultiLLMFactory,
                build_fallback_provider_chain,
            )

            fallback_chain = build_fallback_provider_chain(primary_provider)
            # 使用降级链创建LLM
            if len(fallback_chain) > 1:
                logger.info(f" 启用自动降级: {' → '.join(fallback_chain)}")
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
                    **kwargs,
                )
        except (openai.APIConnectionError, httpcore.ConnectError, ConnectionError) as e:
            logger.error(f" LLM服务连接异常: {e}")
            raise RuntimeError("LLM服务连接异常，请稍后重试。")
        except Exception as e:
            logger.error(f" LLM实例创建异常: {e}")
            raise

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
        config: Optional[LLMConfig] = None, schema: Optional[type] = None, **kwargs
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
    def _is_auth_401_error(error_text: str) -> bool:
        """是否为认证类 401 错误。"""
        lowered = (error_text or "").lower()
        return (
            "401" in lowered
            and (
                "authentication" in lowered
                or "invalid_api_key" in lowered
                or "incorrect api key" in lowered
                or "user not found" in lowered
                or "unauthorized" in lowered
            )
        )

    @classmethod
    def preflight_auth_check(cls) -> Dict[str, Any]:
        """
        启动前 LLM 凭证预检。

        Returns:
            {
                "ok": bool,
                "error_code": Optional[str],
                "message": str,
                "provider": str,
            }
        """
        import os
        from typing import Any, Dict

        provider = os.getenv("LLM_PROVIDER", "openai").lower()
        key_map = {
            "openai": "OPENAI_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "deepseek": "DEEPSEEK_API_KEY",
            "qwen": "QWEN_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
        }
        key_name = key_map.get(provider, "OPENAI_API_KEY")
        api_key = os.getenv(key_name, "")

        if not api_key or api_key.startswith("your_"):
            return {
                "ok": False,
                "error_code": "LLM_CREDENTIAL_MISSING",
                "message": f"未检测到有效凭证: {key_name}",
                "provider": provider,
            }

        enable_active_probe = os.getenv("LLM_PREFLIGHT_ACTIVE_PROBE", "true").lower() == "true"
        if not enable_active_probe:
            return {
                "ok": True,
                "error_code": None,
                "message": "凭证格式检查通过（未启用主动探测）",
                "provider": provider,
            }

        try:
            from langchain_core.messages import HumanMessage

            llm = cls.create_llm(temperature=0, max_tokens=8, timeout=15, max_retries=0)
            llm.invoke([HumanMessage(content="ping")])
            return {
                "ok": True,
                "error_code": None,
                "message": "LLM主动探测通过",
                "provider": provider,
            }
        except Exception as e:
            err = str(e)
            if cls._is_auth_401_error(err):
                return {
                    "ok": False,
                    "error_code": "LLM_AUTH_401",
                    "message": f"LLM认证失败（401）: {err}",
                    "provider": provider,
                }
            return {
                "ok": False,
                "error_code": "LLM_PREFLIGHT_FAILED",
                "message": f"LLM预检失败: {err}",
                "provider": provider,
            }

    @staticmethod
    def create_high_concurrency_llm(
        provider: str = "openai", enable_cache: bool = True, enable_fallback: bool = True, **kwargs
    ):
        """
         v3.9: 创建高并发 LLM 实例

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
                preferred_provider=provider, enable_cache=enable_cache, enable_fallback=enable_fallback, **kwargs
            )
        except Exception as e:
            logger.warning(f"️ 高并发LLM创建失败,回退到普通LLM: {e}")
            return LLMFactory.create_llm(**kwargs)

    @staticmethod
    def create_openrouter_balanced_llm(
        model: str = "openai/gpt-4o-2024-11-20", strategy: str = "round_robin", **kwargs
    ):
        """
         v7.4.2: 创建 OpenRouter 负载均衡 LLM 实例

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
                LoadBalancerConfig,
                get_global_balancer,
            )

            #  v7.153: 过滤掉 ChatOpenAI 不支持的参数
            # provider 是 MultiLLMFactory 的参数，不应传递给 ChatOpenAI
            filtered_kwargs = {k: v for k, v in kwargs.items() if k not in ["provider"]}

            # 创建配置
            config = LoadBalancerConfig(strategy=strategy)

            # 获取全局负载均衡器
            balancer = get_global_balancer(config=config, model=model, **filtered_kwargs)

            # 返回 LLM 实例
            return balancer.get_llm()

        except Exception as e:
            logger.warning(f"️ OpenRouter 负载均衡器创建失败，回退到普通 LLM: {e}")
            return LLMFactory.create_llm(**kwargs)


def get_llm(config: Optional[LLMConfig] = None, **kwargs) -> ChatOpenAI:
    """Backwards-compatible helper.

    Some legacy tests/scripts import `get_llm()` directly. Prefer using
    `LLMFactory.create_llm()` in new code.
    """
    return LLMFactory.create_llm(config=config, **kwargs)
