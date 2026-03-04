"""
语义缓存LLM包装器 - 系统级透明缓存层

对应用层完全透明，所有LLM调用自动享受语义缓存
"""

from typing import Any, Dict, List

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult
from loguru import logger

from intelligent_project_analyzer.services.semantic_cache import SemanticCache


class CachedLLMWrapper(BaseChatModel):
    """
    LLM包装器，自动添加语义缓存

    对应用层完全透明，所有LLM调用自动享受缓存

    特性:
    - 零侵入：应用层无需修改
    - 全覆盖：所有LLM调用自动缓存
    - 高性能：缓存命中<1s，未命中透传
    - 可观测：完整的缓存统计

    Example:
        # 在 llm_factory.py 中自动包装
        base_llm = ChatOpenAI(model="gpt-4")
        cached_llm = CachedLLMWrapper(base_llm, cache)

        # 应用层无感知，正常使用
        result = await cached_llm.ainvoke(messages)
    """

    llm: Any
    semantic_cache: Any = None
    cache_namespace: str = "default"

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        llm: BaseChatModel,
        cache: SemanticCache,
        cache_namespace: str = "default",
        **kwargs,
    ):
        """
        初始化缓存包装器

        Args:
            llm: 底层LLM实例
            cache: 语义缓存实例
            cache_namespace: 缓存命名空间（用于隔离不同类型的调用）
        """
        super().__init__(llm=llm, semantic_cache=cache, cache_namespace=cache_namespace, **kwargs)

        # P0-F2: 禁用底层LLM的LangChain内置缓存，避免"no cache found"错误
        # CachedLLMWrapper使用自己的semantic_cache，不需要LangChain的全局缓存
        if hasattr(self.llm, "cache"):
            self.llm.cache = False

        logger.info(
            f"[CachedLLM] Initialized with namespace={cache_namespace}, " f"threshold={cache.similarity_threshold}"
        )

    def _build_cache_key(self, messages: List[BaseMessage]) -> str:
        """
        构建缓存键

        基于所有消息内容生成缓存键，确保相同输入得到相同结果

        Args:
            messages: 消息列表

        Returns:
            缓存键字符串
        """
        # 提取所有消息内容
        content_parts = []
        for msg in messages:
            if hasattr(msg, "content"):
                content_parts.append(str(msg.content))

        # 拼接成完整文本
        full_text = "\n".join(content_parts)

        return full_text

    async def ainvoke(
        self,
        input: Any,
        config: Any | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        重写ainvoke方法，直接调用_agenerate，绕过BaseChatModel的缓存检查

        这是修复"Asked to cache, but no cache found"错误的关键
        """
        # 将input转换为messages格式
        if isinstance(input, list):
            messages = input
        else:
            from langchain_core.messages import HumanMessage

            messages = [HumanMessage(content=str(input))]

        # 直接调用我们的_agenerate（已经包含语义缓存逻辑）
        result = await self._agenerate(messages, **kwargs)

        # 返回第一个generation的message
        if result.generations and len(result.generations) > 0:
            generation = result.generations[0]
            if hasattr(generation, "message"):
                return generation.message
            elif isinstance(generation, dict) and "message" in generation:
                return generation["message"]

        # 降级：返回整个result
        return result

    def invoke(
        self,
        input: Any,
        config: Any | None = None,
        **kwargs: Any,
    ) -> Any:
        """
        Override synchronous invoke to bypass BaseChatModel's built-in cache mechanism.

        Prevents 'Asked to cache, but no cache found' error when called synchronously
        (e.g., from base.invoke_llm). Sync calls bypass semantic cache and delegate
        directly to the underlying LLM.
        """
        if isinstance(input, list):
            messages = input
        else:
            from langchain_core.messages import HumanMessage

            messages = [HumanMessage(content=str(input))]

        # Directly delegate to the underlying LLM (which has cache=False)
        return self.llm.invoke(messages, config=config, **kwargs)

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: List[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        异步生成（内部方法）

        LangChain的BaseChatModel要求实现此方法
        """
        # 1. 构建缓存键
        cache_key = self._build_cache_key(messages)

        # 2. 尝试从缓存获取（同步调用，不使用await）
        try:
            cached_result = self.semantic_cache.get(cache_key)

            if cached_result is not None:
                output_data, similarity = cached_result
                logger.info(
                    f"[CACHE HIT] namespace={self.cache_namespace}, " f"similarity={similarity:.4f}, saved ~60s"
                )

                # 从缓存数据重建ChatResult
                ai_message = AIMessage(content=output_data.get("content", ""))
                return ChatResult(generations=[{"message": ai_message}])

        except Exception as e:
            logger.warning(f"[CACHE ERROR] Failed to get from cache: {e}, fallback to LLM")

        # 3. 缓存未命中，调用实际LLM
        logger.info(f"[CACHE MISS] namespace={self.cache_namespace}, calling LLM...")

        # 🔧 修复：使用ainvoke而不是_agenerate，避免缓存检查问题
        try:
            response = await self.llm.ainvoke(messages, **kwargs)
            # 将response转换为ChatResult格式
            if hasattr(response, "content"):
                ai_message = AIMessage(content=response.content)
                result = ChatResult(generations=[{"message": ai_message}])
            else:
                # 如果已经是ChatResult，直接使用
                result = response
        except Exception as e:
            logger.error(f"[LLM ERROR] Failed to call LLM: {e}")
            raise

        # 4. 将结果存入缓存（同步调用，不使用await）
        try:
            # 提取结果内容
            if result.generations and len(result.generations) > 0:
                generation = result.generations[0]
                if hasattr(generation, "message"):
                    content = generation.message.content
                elif isinstance(generation, dict) and "message" in generation:
                    content = generation["message"].content
                else:
                    content = str(generation)

                output_data = {
                    "content": content,
                    "model": getattr(self.llm, "model_name", "unknown"),
                }

                self.semantic_cache.set(cache_key, output_data)
                logger.debug("[CACHE SET] Stored result for future use")

        except Exception as e:
            logger.warning(f"[CACHE ERROR] Failed to set cache: {e}")

        return result

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: List[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """
        同步生成（内部方法）

        LangChain的BaseChatModel要求实现此方法
        注意：同步方法不支持缓存，直接调用底层LLM
        """
        logger.warning("[CachedLLM] Sync call detected, cache not supported. " "Use async methods for caching.")
        return self.llm._generate(
            messages=messages,
            stop=stop,
            run_manager=run_manager,
            **kwargs,
        )

    @property
    def _llm_type(self) -> str:
        """返回LLM类型"""
        return f"cached_{self.llm._llm_type}"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        """返回识别参数"""
        return {
            "base_llm": self.llm._identifying_params,
            "cache_namespace": self.cache_namespace,
            "cache_threshold": self.semantic_cache.similarity_threshold,
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            缓存统计字典
        """
        return self.semantic_cache.get_stats()

    def with_structured_output(self, schema, **kwargs):
        """委托给底层LLM实现结构化输出（结构化输出不走缓存）"""
        return self.llm.with_structured_output(schema, **kwargs)


def wrap_llm_with_cache(
    llm: BaseChatModel,
    cache: SemanticCache | None = None,
    cache_namespace: str = "default",
    enable_cache: bool = True,
) -> BaseChatModel:
    """
    包装LLM实例，添加语义缓存层

    Args:
        llm: 原始LLM实例
        cache: 语义缓存实例（如果为None则创建新实例）
        cache_namespace: 缓存命名空间
        enable_cache: 是否启用缓存

    Returns:
        包装后的LLM实例（如果enable_cache=False则返回原始实例）
    """
    if not enable_cache:
        logger.info("[CachedLLM] Cache disabled, returning original LLM")
        return llm

    # 创建缓存实例（如果未提供）
    if cache is None:
        cache = SemanticCache(
            similarity_threshold=0.90,
            ttl=604800,  # 7天
        )

    # 包装LLM
    cached_llm = CachedLLMWrapper(
        llm=llm,
        cache=cache,
        cache_namespace=cache_namespace,
    )

    logger.info(f"[CachedLLM] Wrapped LLM with semantic cache, " f"namespace={cache_namespace}")

    return cached_llm
