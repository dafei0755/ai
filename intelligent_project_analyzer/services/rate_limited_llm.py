# -*- coding: utf-8 -*-
"""
限流增强的 LLM 包装器

提供带限流功能的 LLM 调用接口
"""

from typing import Any, List, Optional, Dict
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult
from loguru import logger

from intelligent_project_analyzer.services.rate_limiter import (
    rate_limit_manager,
    RateLimitExceeded,
    RateLimitConfig
)


class RateLimitedLLM:
    """
    带限流的 LLM 包装器
    
    包装任意 LangChain LLM，添加限流控制
    
    Usage:
        from intelligent_project_analyzer.services.llm_factory import LLMFactory
        
        # 创建限流 LLM
        base_llm = LLMFactory.create_llm()
        llm = RateLimitedLLM(base_llm, provider="openai")
        
        # 使用（自动限流）
        result = llm.invoke("Hello")
        result = await llm.ainvoke("Hello")
    """
    
    def __init__(
        self,
        llm: BaseChatModel,
        provider: str = "openai",
        user_id: Optional[str] = None,
        custom_config: Optional[RateLimitConfig] = None
    ):
        """
        初始化限流 LLM
        
        Args:
            llm: 原始 LLM 实例
            provider: LLM 提供商（用于选择限流配置）
            user_id: 用户ID（用于用户级别限流）
            custom_config: 自定义限流配置
        """
        self._llm = llm
        self._provider = provider
        self._user_id = user_id
        
        # 获取或创建限流器
        if custom_config:
            from intelligent_project_analyzer.services.rate_limiter import LLMRateLimiter
            self._limiter = LLMRateLimiter(provider, custom_config)
        else:
            self._limiter = rate_limit_manager.get_limiter(provider, user_id)
        
        logger.info(f" 创建限流 LLM: provider={provider}, user_id={user_id}")
    
    def invoke(self, input: Any, **kwargs) -> Any:
        """
        同步调用（带限流）
        """
        if not self._limiter.acquire_sync():
            raise RateLimitExceeded(
                f"LLM API 限流: {self._provider}, "
                f"stats={self._limiter.stats}"
            )
        
        try:
            return self._llm.invoke(input, **kwargs)
        finally:
            self._limiter.release_sync()
    
    async def ainvoke(self, input: Any, **kwargs) -> Any:
        """
        异步调用（带限流）
        """
        if not await self._limiter.acquire_async():
            raise RateLimitExceeded(
                f"LLM API 限流: {self._provider}, "
                f"stats={self._limiter.stats}"
            )
        
        try:
            return await self._llm.ainvoke(input, **kwargs)
        finally:
            self._limiter.release_async()
    
    def batch(self, inputs: List[Any], **kwargs) -> List[Any]:
        """
        批量调用（带限流）
        """
        results = []
        for input in inputs:
            result = self.invoke(input, **kwargs)
            results.append(result)
        return results
    
    async def abatch(self, inputs: List[Any], **kwargs) -> List[Any]:
        """
        异步批量调用（带限流）
        """
        results = []
        for input in inputs:
            result = await self.ainvoke(input, **kwargs)
            results.append(result)
        return results
    
    def stream(self, input: Any, **kwargs):
        """
        流式调用（带限流）
        """
        if not self._limiter.acquire_sync():
            raise RateLimitExceeded(f"LLM API 限流: {self._provider}")
        
        try:
            for chunk in self._llm.stream(input, **kwargs):
                yield chunk
        finally:
            self._limiter.release_sync()
    
    async def astream(self, input: Any, **kwargs):
        """
        异步流式调用（带限流）
        """
        if not await self._limiter.acquire_async():
            raise RateLimitExceeded(f"LLM API 限流: {self._provider}")
        
        try:
            async for chunk in self._llm.astream(input, **kwargs):
                yield chunk
        finally:
            self._limiter.release_async()
    
    @property
    def stats(self) -> Dict[str, Any]:
        """获取限流统计"""
        return self._limiter.stats
    
    @property
    def model_name(self) -> str:
        """获取模型名称"""
        if hasattr(self._llm, 'model_name'):
            return self._llm.model_name
        elif hasattr(self._llm, 'model'):
            return self._llm.model
        return "unknown"
    
    def __getattr__(self, name):
        """代理其他属性到原始 LLM"""
        return getattr(self._llm, name)


def create_rate_limited_llm(
    provider: str = "openai",
    user_id: Optional[str] = None,
    **llm_kwargs
) -> RateLimitedLLM:
    """
    便捷函数：创建限流 LLM
    
    Args:
        provider: LLM 提供商
        user_id: 用户ID
        **llm_kwargs: 传递给 LLMFactory.create_llm 的参数
        
    Returns:
        带限流的 LLM 实例
        
    Usage:
        llm = create_rate_limited_llm("openai", user_id="user123")
        result = await llm.ainvoke("Hello")
    """
    from intelligent_project_analyzer.services.llm_factory import LLMFactory
    
    base_llm = LLMFactory.create_llm(**llm_kwargs)
    return RateLimitedLLM(base_llm, provider=provider, user_id=user_id)
